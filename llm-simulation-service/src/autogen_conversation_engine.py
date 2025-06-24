"""
AutoGen-based conversation engine for LLM simulation
Uses hybrid architecture: AutoGen Swarm for agents + traditional LLM for client simulation
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import TextMessage, HandoffMessage, ToolCallExecutionEvent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.webhook_manager import WebhookManager
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.tools_specification import ToolsSpecification
from src.autogen_tools import AutogenToolFactory


class AutoGenConversationEngine:
    """
    AutoGen-based conversation engine with hybrid architecture:
    - Agent Team: AutoGen Swarm for multi-agent coordination (internal handoffs/tools hidden)
    - Client Simulation: Traditional LLM calls for client responses
    - Conversation Loop: Manual orchestration between Agent MAS and Client LLM
    """
    
    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.logger = get_logger()
        
        # Load prompt specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        
        self.logger.log_info(f"AutoGenConversationEngine initialized with prompt specification: {prompt_spec_name}", extra_data={
            'spec_name': prompt_spec_name,
            'spec_version': self.prompt_specification.version,
            'agents': list(self.prompt_specification.agents.keys())
        })
    
    def _format_prompt(self, template: str, variables: Dict[str, Any], session_id: str) -> str:
        """Format prompt template with variables - reusing existing logic"""
        try:
            # Add session_id to variables
            variables = variables.copy()
            variables['session_id'] = session_id
            
            # Set default values for missing variables
            defaults = {
                'CURRENT_DATE': '2024-01-15',
                'current_date': '2024-01-15',
                'DELIVERY_DAY': 'завтра',
                'delivery_days': 'понедельник, среда, пятница',
                'PURCHASE_HISTORY': 'История покупок отсутствует',
                'purchase_history': 'История покупок отсутствует',
                'name': variables.get('CLIENT_NAME', 'Клиент'),
                'locations': variables.get('LOCATION', 'Адрес не указан')
            }
            
            # Add defaults for missing variables
            for key, default_value in defaults.items():
                if key not in variables:
                    variables[key] = default_value
            
            # Convert Jinja2-style {{variable}} to Python format {variable}
            import re
            formatted_template = re.sub(r'\{\{(\w+)\}\}', r'{\1}', template)
            
            return formatted_template.format(**variables)
        except KeyError as e:
            self.logger.log_error(f"Missing variable in prompt template: {e}")
            # Try to replace remaining variables with placeholders
            import re
            remaining_vars = re.findall(r'\{(\w+)\}', template)
            for var in remaining_vars:
                if var not in variables:
                    variables[var] = f"[{var}_NOT_SET]"
            try:
                formatted_template = re.sub(r'\{\{(\w+)\}\}', r'{\1}', template)
                return formatted_template.format(**variables)
            except:
                return template
    
    async def _enrich_variables_with_client_data(self, variables: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
        """Enrich variables with client data from webhook if client_id is provided - reusing existing logic"""
        variables = variables.copy()
        webhook_session_id = None
        
        # Check if client_id is provided
        client_id = variables.get('client_id')
        if client_id:
            self.logger.log_info(f"Found client_id in scenario: {client_id}")
            
            # Fetch client data from webhook (both variables and session_id)
            client_data = await self.webhook_manager.get_client_data(client_id)
            client_variables = client_data['variables']
            webhook_session_id = client_data['session_id']
            
            # Override the hardcoded variables with webhook data
            variables.update(client_variables)
            
            # Also set the lowercase versions for template compatibility
            variables['name'] = client_variables.get('NAME', '')
            variables['locations'] = client_variables.get('LOCATIONS', '')
            variables['delivery_days'] = client_variables.get('DELIVERY_DAYS', '')
            variables['purchase_history'] = client_variables.get('PURCHASE_HISTORY', '')
            variables['current_date'] = variables.get('CURRENT_DATE', '')
            if variables['current_date'] == '':
                variables['current_date'] = client_variables.get('CURRENT_DATE', '')
            
            self.logger.log_info(f"Enriched variables with client data", extra_data={
                'client_id': client_id,
                'has_dynamic_data': bool(client_variables.get('LOCATIONS')),
                'has_webhook_session_id': bool(webhook_session_id)
            })
        else:
            # No client_id provided, use existing variables or set defaults
            self.logger.log_info("No client_id provided, using existing variables")
            # Ensure lowercase versions exist for template compatibility
            if 'LOCATIONS' in variables and 'locations' not in variables:
                variables['locations'] = variables['LOCATIONS']
            if 'DELIVERY_DAYS' in variables and 'delivery_days' not in variables:
                variables['delivery_days'] = variables['DELIVERY_DAYS']  
            if 'PURCHASE_HISTORY' in variables and 'purchase_history' not in variables:
                variables['purchase_history'] = variables['PURCHASE_HISTORY']
            if 'NAME' in variables and 'name' not in variables:
                variables['name'] = variables['NAME']
                
        return variables, webhook_session_id
    
    def _extract_tool_names_from_agent_spec(self, agent_spec: SystemPromptSpecification) -> List[str]:
        """Extract tool names from agent specification"""
        tool_names = []
        
        # Get tool schemas and extract names
        tool_schemas = agent_spec.get_tool_schemas()
        for tool_schema in tool_schemas:
            tool_name = tool_schema.get('function', {}).get('name', '')
            if tool_name and not ToolsSpecification.is_handoff_tool(tool_name):
                # Only include non-handoff tools, handoffs will be handled by AutoGen's handoffs parameter
                tool_names.append(tool_name)
        
        return tool_names
    
    def _determine_handoffs_for_agent(self, agent_spec: SystemPromptSpecification) -> List[str]:
        """Determine handoff targets for an agent from its tool specifications"""
        handoffs = []
        
        # Check for handoff tools in agent's tool schemas
        tool_schemas = agent_spec.get_tool_schemas()
        for tool_schema in tool_schemas:
            tool_name = tool_schema.get('function', {}).get('name', '')
            if ToolsSpecification.is_handoff_tool(tool_name):
                target_agent = ToolsSpecification.get_handoff_target_agent(tool_name)
                if target_agent and target_agent in self.prompt_specification.agents:
                    handoffs.append(target_agent)
        
        # Always allow handoff to user (client) for ending conversations
        handoffs.append("user")
        
        return handoffs
    
    def _create_assistant_agent(self, agent_name: str, agent_spec: SystemPromptSpecification, 
                              variables: Dict[str, Any], session_id: str, 
                              model_client: OpenAIChatCompletionClient) -> AssistantAgent:
        """Create an AssistantAgent from prompt specification using the existing autogen_tools"""
        
        # Format system prompt
        system_prompt = self._format_prompt(agent_spec.prompt, variables, session_id)
        
        # Create tools for this agent using AutogenToolFactory
        tool_factory = AutogenToolFactory(session_id)
        tool_names = self._extract_tool_names_from_agent_spec(agent_spec)
        tools = tool_factory.get_tools_for_agent(tool_names)
        
        # Determine handoffs based on agent capabilities
        handoffs = self._determine_handoffs_for_agent(agent_spec)
        
        # Create the AssistantAgent
        agent = AssistantAgent(
            name=agent_name,
            model_client=model_client,
            tools=tools,
            handoffs=handoffs,
            system_message=system_prompt,
            description=f"Agent {agent_name} - {agent_spec.prompt[:100]}..."
        )
        
        self.logger.log_info(f"Created AutoGen AssistantAgent: {agent_name}", extra_data={
            'session_id': session_id,
            'tools_count': len(tools),
            'tool_names': tool_names,
            'handoffs': handoffs,
            'system_prompt_preview': system_prompt[:200]
        })
        
        return agent
    
    def _extract_final_agent_response(self, task_result) -> str:
        """Extract the final user-facing response from AutoGen Swarm task result"""
        if not hasattr(task_result, 'messages') or not task_result.messages:
            return ""
        
        # Look for the last TextMessage that's not a handoff or tool execution
        for message in reversed(task_result.messages):
            if isinstance(message, TextMessage):
                # This is a regular agent response to the user
                return message.content
        
        # Fallback: return empty string if no user-facing message found
        return ""
    
    def _extract_swarm_debug_info(self, task_result, session_id: str) -> Dict[str, Any]:
        """Extract debug information from AutoGen Swarm execution"""
        debug_info = {
            'internal_messages': [],
            'handoffs': [],
            'tool_executions': []
        }
        
        if not hasattr(task_result, 'messages') or not task_result.messages:
            return debug_info
        
        for message in task_result.messages:
            if isinstance(message, HandoffMessage):
                debug_info['handoffs'].append({
                    'from': message.source,
                    'to': message.target,
                    'content': message.content
                })
            elif isinstance(message, ToolCallExecutionEvent):
                debug_info['tool_executions'].append({
                    'source': message.source,
                    'tools': [{'name': exec.name, 'result': str(exec.content)} for exec in message.content]
                })
            elif isinstance(message, TextMessage):
                debug_info['internal_messages'].append({
                    'source': message.source,
                    'content': message.content
                })
        
        self.logger.log_info(f"Extracted Swarm debug info", extra_data={
            'session_id': session_id,
            'handoffs_count': len(debug_info['handoffs']),
            'tool_executions_count': len(debug_info['tool_executions']),
            'internal_messages_count': len(debug_info['internal_messages'])
        })
        
        return debug_info
    
    def _check_agent_termination(self, agent_response: str) -> bool:
        """Check if agent response indicates conversation termination"""
        termination_phrases = ["end_call"]
        return any(phrase in agent_response.lower() for phrase in termination_phrases)
    
    def _check_client_termination(self, client_response: str) -> bool:
        """Check if client response indicates conversation termination"""
        termination_phrases = ["до свидания", "спасибо", "всё", "хватит", "конец"]
        return any(phrase in client_response.lower() for phrase in termination_phrases)
    
    async def _handle_client_tool_calls(self, client_response, session_id: str) -> Tuple[bool, str]:
        """Handle client tool calls, particularly end_call. Returns (conversation_ended, tool_response_text)"""
        conversation_ended = False
        tool_response_text = ""
        
        if hasattr(client_response, 'tool_calls') and client_response.tool_calls:
            for tool_call in client_response.tool_calls:
                if tool_call.function.name == "end_call":
                    conversation_ended = True
                    
                    # Parse end call reason
                    try:
                        args = json.loads(tool_call.function.arguments)
                        end_reason = args.get("reason", "conversation completed")
                    except:
                        end_reason = "conversation completed"
                    
                    tool_response_text = f"[ЗАВЕРШИЛ ЗВОНОК: {end_reason}]"
                    
                    self.logger.log_info(f"Client ended call: {end_reason}", extra_data={'session_id': session_id})
                    break
        
        return conversation_ended, tool_response_text
    
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Run conversation with tools using hybrid architecture:
        AutoGen Swarm for agents + traditional LLM for client simulation
        """
        
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC
        
        scenario_name = scenario.get('name', 'unknown')
        variables = scenario.get('variables', {})
        seed = variables.get('SEED')
        
        # Enrich variables with client data if client_id is provided
        variables, webhook_session_id = await self._enrich_variables_with_client_data(variables)
        
        session_id = webhook_session_id or await self.webhook_manager.initialize_session()
        
        self.logger.log_info(f"Starting AutoGen hybrid conversation simulation", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'has_client_id': 'client_id' in scenario.get('variables', {}),
            'using_webhook_session': bool(webhook_session_id)
        })
        
        start_time = time.time()
        conversation_history = []
        turn_number = 0
        conversation_ended = False
        
        try:
            # Create OpenAI model client for AutoGen
            # Access API key from the AsyncOpenAI client
            api_key = self.openai.client.api_key
            model_client = OpenAIChatCompletionClient(
                model=self.openai.model,
                api_key=api_key,
                # TODO: Add seed support if available in AutoGen OpenAI client
            )
            
            # Get agent and client specifications
            agent_specs = self.prompt_specification.agents
            client_spec = self.prompt_specification.get_agent_prompt('client')
            
            if not client_spec:
                raise ValueError("Missing required client specification")
            
            # Create AutoGen Swarm for agents (excluding client)
            agents = []
            for agent_name, agent_spec in agent_specs.items():
                if agent_name != 'client':  # Client will be simulated separately
                    agent = self._create_assistant_agent(
                        agent_name=agent_name,
                        agent_spec=agent_spec,
                        variables=variables,
                        session_id=session_id,
                        model_client=model_client
                    )
                    agents.append(agent)
            
            if not agents:
                raise ValueError("No agents created from prompt specification")
            
            # Set up termination conditions for Swarm
            termination = (
                HandoffTermination(target="user") | 
                TextMentionTermination("TERMINATE") |
                TextMentionTermination("end_call")
            )
            
            # Create Swarm team
            agent_team = Swarm(participants=agents, termination_condition=termination)
            
            # Initialize client LLM context (traditional approach)
            client_system_prompt = self._format_prompt(client_spec.prompt, variables, session_id)
            client_messages = [{"role": "system", "content": client_system_prompt}]
            client_tools = client_spec.get_tool_schemas()
            
            self.logger.log_info(f"Initialized hybrid conversation components", extra_data={
                'session_id': session_id,
                'agent_count': len(agents),
                'client_system_prompt_preview': client_system_prompt[:200],
                'client_tools_count': len(client_tools)
            })
            
            # Start conversation with client greeting
            current_message = "Добрый день!"  # Initial client message
            
            # Main conversation loop
            while turn_number < max_turns and not conversation_ended:
                # Check timeout
                if time.time() - start_time > timeout_sec:
                    timeout_context = {
                        'session_id': session_id,
                        'timeout_sec': timeout_sec,
                        'actual_duration': time.time() - start_time,
                        'turn_number': turn_number,
                        'max_turns': max_turns,
                        'scenario_name': scenario_name
                    }
                    self.logger.log_error(f"AutoGen hybrid conversation timeout after {timeout_sec} seconds", extra_data=timeout_context)
                    break
                
                turn_number += 1
                
                # AGENT TURN: Send current message to Agent Swarm
                self.logger.log_info(f"Agent turn {turn_number}: sending message to Swarm", extra_data={
                    'session_id': session_id,
                    'message_preview': current_message[:100]
                })
                
                agent_task_result = await agent_team.run(task=current_message)
                
                # Extract final agent response (filter out internal handoffs/tools)
                agent_response = self._extract_final_agent_response(agent_task_result)
                
                # Extract debug info for conversation history
                swarm_debug = self._extract_swarm_debug_info(agent_task_result, session_id)
                
                # Ensure agent response is not empty
                if not agent_response:
                    agent_response = ""
                
                # Log agent turn
                self.logger.log_conversation_turn(
                    session_id=session_id,
                    turn_number=turn_number,
                    role="agent_swarm",
                    content=agent_response
                )
                
                # Add agent response to conversation history with debug info
                conversation_history.append({
                    "turn": turn_number,
                    "speaker": "agent",
                    "content": agent_response,
                    "timestamp": datetime.now().isoformat(),
                    "swarm_debug": swarm_debug  # Internal handoffs/tools for debugging
                })
                
                # Check if agent wants to end conversation
                if self._check_agent_termination(agent_response):
                    self.logger.log_info(f"Agent ended conversation at turn {turn_number}", extra_data={'session_id': session_id})
                    break
                
                # Check if we've reached max turns
                if turn_number >= max_turns:
                    break
                
                # CLIENT TURN: Send agent response to Client LLM
                client_messages.append({"role": "user", "content": agent_response})
                
                self.logger.log_info(f"Client turn {turn_number}: generating response", extra_data={
                    'session_id': session_id,
                    'agent_response_preview': agent_response[:100]
                })
                
                client_response, client_usage = await self.openai.chat_completion(
                    messages=client_messages,
                    session_id=session_id,
                    tools=client_tools,
                    seed=seed
                )
                
                # Handle client tool calls (particularly end_call)
                conversation_ended, tool_response_text = await self._handle_client_tool_calls(client_response, session_id)
                
                if conversation_ended:
                    # Log client turn with tool call
                    self.logger.log_conversation_turn(
                        session_id=session_id,
                        turn_number=turn_number,
                        role="client",
                        content=tool_response_text
                    )
                    
                    conversation_history.append({
                        "turn": turn_number,
                        "speaker": "client",
                        "content": tool_response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                
                # Extract client content
                client_content = client_response.content if hasattr(client_response, 'content') else str(client_response)
                
                # Ensure client content is not empty
                if not client_content:
                    client_content = ""
                
                # Log client turn
                self.logger.log_conversation_turn(
                    session_id=session_id,
                    turn_number=turn_number,
                    role="client",
                    content=client_content
                )
                
                conversation_history.append({
                    "turn": turn_number,
                    "speaker": "client",
                    "content": client_content,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add client response to client's context for next turn
                client_messages.append({"role": "assistant", "content": client_content})
                
                # Check if client wants to end conversation
                if self._check_client_termination(client_content):
                    self.logger.log_info(f"Client ended conversation at turn {turn_number}", extra_data={'session_id': session_id})
                    break
                
                # Set client response as next message for agent team
                current_message = client_content
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log conversation completion
            self.logger.log_conversation_complete(
                session_id=session_id,
                total_turns=turn_number,
                status='completed'
            )
            
            # Close model client
            await model_client.close()
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'completed',
                'total_turns': turn_number,
                'duration_seconds': duration,
                'conversation_history': conversation_history,  # Full history with debug info
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'tools_used': True,
                'autogen_engine': True  # Flag to indicate this was processed by AutoGen engine
            }
            
        except Exception as e:
            # Enhanced error logging with more context
            error_context = {
                'session_id': session_id,
                'scenario_name': scenario_name,
                'turn_number': turn_number,
                'duration_so_far': time.time() - start_time,
                'max_turns': max_turns,
                'timeout_sec': timeout_sec,
                'error_type': type(e).__name__,
                'conversation_ended': conversation_ended,
                'autogen_engine': True
            }
            
            self.logger.log_error(f"AutoGen hybrid conversation failed: {str(e)}", exception=e, extra_data=error_context)
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'total_turns': turn_number,
                'duration_seconds': time.time() - start_time,
                'conversation_history': conversation_history,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'tools_used': True,
                'autogen_engine': True,
                'error_context': error_context
            }
    
    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Run simple conversation without tools - delegates to tools version for now
        TODO: Implement separate non-tools version if needed for performance
        """
        return await self.run_conversation_with_tools(scenario, max_turns, timeout_sec)
"""
Core conversation engine for LLM simulation
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.webhook_manager import WebhookManager
from src.tool_emulator import ToolEmulator
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.tools_specification import ToolsSpecification

class ConversationEngine:
    """Core engine for managing conversations between Agent-LLM and Client-LLM with multi-agent support"""
    
    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.tool_emulator = ToolEmulator()
        self.logger = get_logger()
        
        # Load prompt specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        
        # Multi-agent state tracking
        self.current_agent = 'agent'  # Default starting agent
        self.agent_contexts = {}  # Track conversation context for each agent
        
        self.logger.log_info(f"ConversationEngine initialized with prompt specification: {prompt_spec_name}", extra_data={
            'spec_name': prompt_spec_name,
            'spec_version': self.prompt_specification.version,
            'agents': list(self.prompt_specification.agents.keys())
        })
    
    def _format_prompt(self, template: str, variables: Dict[str, Any], session_id: str) -> str:
        """Format prompt template with variables"""
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
        """
        Enrich variables with client data from webhook if client_id is provided.
        Falls back to existing values if client_id is not present.
        
        Returns:
            Tuple of (enriched_variables, session_id_from_webhook)
        """
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

    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Run a complete conversation simulation"""
        
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC
        
        scenario_name = scenario.get('name', 'unknown')
        variables = scenario.get('variables', {})
        seed = variables.get('SEED')
        
        # Enrich variables with client data if client_id is provided
        variables, webhook_session_id = await self._enrich_variables_with_client_data(variables)
        
        # Use webhook session_id if available, otherwise initialize a new session
        if webhook_session_id:
            session_id = webhook_session_id
            self.logger.log_info(f"Using session_id from webhook: {session_id}")
        else:
            session_id = await self.webhook_manager.initialize_session()
            self.logger.log_info(f"Using generated session_id: {session_id}")
        
        self.logger.log_info(f"Starting conversation simulation", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'has_client_id': 'client_id' in scenario.get('variables', {}),
            'using_webhook_session': bool(webhook_session_id)
        })
        
        start_time = time.time()
        
        try:
            # Get prompts from specification
            agent_spec = self.prompt_specification.get_agent_prompt('agent')
            client_spec = self.prompt_specification.get_agent_prompt('client')
            
            if not agent_spec or not client_spec:
                raise ValueError("Missing required agent or client specifications")
            
            # Format system prompts
            agent_system_prompt = self._format_prompt(agent_spec.prompt, variables, session_id)
            client_system_prompt = self._format_prompt(client_spec.prompt, variables, session_id)
            
            self.logger.log_info(f"Agent system prompt: {agent_system_prompt}")
            self.logger.log_info(f"Client system prompt: {client_system_prompt}")
            
            # Initialize conversation history
            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            client_messages = [{"role": "system", "content": client_system_prompt}]
            
            # Start conversation with client greeting
            # client_messages.append({"role": "user", "content": "Добрый день!"})
            
            conversation_history = []
            turn_number = 0
            
            # Run conversation loop
            while turn_number < max_turns:
                # Check timeout
                if time.time() - start_time > timeout_sec:
                    timeout_context = {
                        'session_id': session_id,
                        'timeout_sec': timeout_sec,
                        'actual_duration': time.time() - start_time,
                        'turn_number': turn_number,
                        'max_turns': max_turns,
                        'scenario_name': scenario.get('name', 'unknown')
                    }
                    self.logger.log_error(f"Conversation timeout after {timeout_sec} seconds (actual: {time.time() - start_time:.1f}s)", extra_data=timeout_context)
                    break
                
                turn_number += 1
                
                # Agent turn
                agent_response, agent_usage = await self.openai.chat_completion(
                    messages=agent_messages,
                    session_id=session_id,
                    seed=seed
                )
                
                # Log agent turn
                self.logger.log_conversation_turn(
                    session_id=session_id,
                    turn_number=turn_number,
                    role="agent",
                    content=agent_response
                )
                
                conversation_history.append({
                    "turn": turn_number,
                    "speaker": "agent",
                    "content": agent_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Check if agent wants to end call
                if "end_call" in agent_response.lower():
                    self.logger.log_info(f"Agent ended call at turn {turn_number}", extra_data={'session_id': session_id})
                    break
                
                # Add agent response to client's context
                client_messages.append({"role": "user", "content": agent_response})
                
                # Check if we've reached max turns
                if turn_number >= max_turns:
                    turn_limit_context = {
                        'session_id': session_id,
                        'max_turns': max_turns,
                        'turn_number': turn_number,
                        'duration': time.time() - start_time,
                        'scenario_name': scenario.get('name', 'unknown')
                    }
                    self.logger.log_info(f"Conversation reached max turns limit ({max_turns})", extra_data=turn_limit_context)
                    break
                
                # Client turn
                client_response, client_usage = await self.openai.chat_completion(
                    messages=client_messages,
                    session_id=session_id,
                    seed=seed
                )
                
                # Log client turn
                self.logger.log_conversation_turn(
                    session_id=session_id,
                    turn_number=turn_number,
                    role="client",
                    content=client_response
                )
                
                conversation_history.append({
                    "turn": turn_number,
                    "speaker": "client",
                    "content": client_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add client response to agent's context
                agent_messages.append({"role": "assistant", "content": agent_response})
                agent_messages.append({"role": "user", "content": client_response})
                
                # Add client response to client's context for next turn
                client_messages.append({"role": "assistant", "content": client_response})
                
                # Check if client wants to end conversation
                if any(phrase in client_response.lower() for phrase in ["до свидания", "спасибо", "всё", "хватит", "конец"]):
                    self.logger.log_info(f"Client ended conversation at turn {turn_number}", extra_data={'session_id': session_id})
                    break
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log conversation completion
            self.logger.log_conversation_complete(
                session_id=session_id,
                total_turns=turn_number,
                status='completed'
            )
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'completed',
                'total_turns': turn_number,
                'duration_seconds': duration,
                'conversation_history': conversation_history,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat()
            }
            
        except Exception as e:
            # Enhanced error logging with more context
            error_context = {
                'session_id': session_id,
                'scenario_name': scenario_name,
                'turn_number': turn_number if 'turn_number' in locals() else 0,
                'duration_so_far': time.time() - start_time,
                'max_turns': max_turns,
                'timeout_sec': timeout_sec,
                'error_type': type(e).__name__,
                'agent_messages_count': len(agent_messages) if 'agent_messages' in locals() else 0,
                'client_messages_count': len(client_messages) if 'client_messages' in locals() else 0
            }
            
            self.logger.log_error(f"Conversation failed: {str(e)}", exception=e, extra_data=error_context)
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'total_turns': turn_number if 'turn_number' in locals() else 0,
                'duration_seconds': time.time() - start_time,
                'error_context': error_context
            }

    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]], session_id: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Handle tool calls and return tool responses and optionally new current agent"""
        tool_responses = []
        new_current_agent = None
        
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            
            try:
                # Parse arguments
                arguments = json.loads(tool_call["function"]["arguments"])
                
                # Check if this is a handoff tool
                if ToolsSpecification.is_handoff_tool(tool_name):
                    target_agent = ToolsSpecification.get_handoff_target_agent(tool_name)
                    
                    if target_agent and target_agent in self.prompt_specification.agents:
                        new_current_agent = target_agent
                        
                        tool_response = {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": json.dumps({
                                "status": "handoff_completed",
                                "target_agent": target_agent,
                                "message": f"Successfully handed off conversation to {target_agent}"
                            })
                        }
                        
                        self.logger.log_info(f"Agent handoff executed: {self.current_agent} -> {target_agent}", extra_data={
                            'session_id': session_id,
                            'from_agent': self.current_agent,
                            'to_agent': target_agent,
                            'tool_name': tool_name
                        })
                    else:
                        tool_response = {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": json.dumps({
                                "error": f"Invalid handoff target: {target_agent}"
                            })
                        }
                        
                        self.logger.log_error(f"Invalid handoff target: {target_agent}", extra_data={
                            'session_id': session_id,
                            'tool_name': tool_name
                        })
                else:
                    # Filter out execution_message field before sending to tool API
                    # This field is used internally for conversation flow but shouldn't be sent to external APIs
                    filtered_arguments = {k: v for k, v in arguments.items() if k != "execution_message"}
                    
                    # Handle end_call specially
                    if tool_name == "end_call":
                        tool_response = {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": json.dumps({
                                "status": "call_ended",
                                "reason": filtered_arguments.get("reason", "conversation completed")
                            })
                        }
                    else:
                        # Call the tool emulator with filtered arguments
                        result = await self.tool_emulator.call_tool(tool_name, filtered_arguments, session_id)
                        tool_response = {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "content": json.dumps(result)
                        }
                
                tool_responses.append(tool_response)
                
                # Log tool usage (with original arguments for debugging, but filtered for tool call)
                self.logger.log_info(f"Tool executed: {tool_name}", extra_data={
                    'session_id': session_id,
                    'current_agent': self.current_agent,
                    'original_arguments': arguments,
                    'filtered_arguments': arguments if ToolsSpecification.is_handoff_tool(tool_name) else filtered_arguments,
                    'result': tool_response["content"]
                })
                
            except Exception as e:
                self.logger.log_error(f"Tool call failed: {tool_name}", exception=e, extra_data={
                    'session_id': session_id,
                    'current_agent': self.current_agent
                })
                tool_responses.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": json.dumps({"error": f"Tool execution failed: {str(e)}"})
                })
        
        return tool_responses, new_current_agent
    
    def _safe_parse_tool_result(self, content: str) -> Any:
        """Safely parse tool result content, returning original string if JSON parsing fails"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Return content as string if it's not valid JSON
            return content
        except Exception as e:
            self.logger.log_error(f"Unexpected error parsing tool result: {content}", exception=e)
            return content
    
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Run conversation with tool calling support"""
        
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC
        
        scenario_name = scenario.get('name', 'unknown')
        variables = scenario.get('variables', {})
        seed = variables.get('SEED')
        
        # Enrich variables with client data if client_id is provided
        variables, webhook_session_id = await self._enrich_variables_with_client_data(variables)

        if webhook_session_id:
            session_id = webhook_session_id
            self.logger.log_info(f"Using session_id from webhook: {session_id}")
        else:
            session_id = await self.webhook_manager.initialize_session()
            self.logger.log_info(f"Using generated session_id: {session_id}")

        
        self.logger.log_info(f"Starting conversation simulation with tools", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'has_client_id': 'client_id' in scenario.get('variables', {}),
            'using_webhook_session': bool(webhook_session_id)
        })
        
        start_time = time.time()
        
        try:
            # Get prompts and tools from specification
            agent_spec = self.prompt_specification.get_agent_prompt('agent')
            client_spec = self.prompt_specification.get_agent_prompt('client')
            
            if not agent_spec or not client_spec:
                raise ValueError("Missing required agent or client specifications")
            
            # Format system prompts
            agent_system_prompt = self._format_prompt(agent_spec.prompt, variables, session_id)
            client_system_prompt = self._format_prompt(client_spec.prompt, variables, session_id)
            
            self.logger.log_info(f"Agent system prompt: {agent_system_prompt}")
            self.logger.log_info(f"Client system prompt: {client_system_prompt}")
            
            # Initialize conversation history
            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            client_messages = [{"role": "system", "content": client_system_prompt}]
            
            # Get tools schemas from specification
            agent_tools = agent_spec.get_tool_schemas()
            client_tools = client_spec.get_tool_schemas()
            
            # Start conversation with client greeting
            # client_messages.append({"role": "assistant", "content": "Добрый день!"})
            # agent_messages.append({"role": "user", "content": "Добрый день!"})

            
            conversation_history = []
            turn_number = 0
            conversation_ended = False
            
            # Run conversation loop
            while turn_number < max_turns and not conversation_ended:
                # Check timeout
                if time.time() - start_time > timeout_sec:
                    timeout_context = {
                        'session_id': session_id,
                        'timeout_sec': timeout_sec,
                        'actual_duration': time.time() - start_time,
                        'turn_number': turn_number,
                        'max_turns': max_turns,
                        'scenario_name': scenario.get('name', 'unknown'),
                        'conversation_ended': conversation_ended
                    }
                    self.logger.log_error(f"Conversation with tools timeout after {timeout_sec} seconds (actual: {time.time() - start_time:.1f}s)", extra_data=timeout_context)
                    break
                
                turn_number += 1
                
                # Agent turn
                agent_response, agent_usage = await self.openai.chat_completion(
                    messages=agent_messages,
                    session_id=session_id,
                    tools=agent_tools,
                    seed=seed
                )
                
                # Check if agent made tool calls
                if hasattr(agent_response, 'tool_calls') and agent_response.tool_calls:
                    # Handle tool calls
                    tool_calls = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in agent_response.tool_calls
                    ]
                    
                    # Add assistant message with tool calls
                    agent_messages.append({
                        "role": "assistant",
                        "content": agent_response.content or "",
                        "tool_calls": tool_calls
                    })
                    
                    # Process tool calls
                    tool_responses, new_current_agent = await self._handle_tool_calls(tool_calls, session_id)
                    
                    # Handle agent handoff if needed
                    if new_current_agent and new_current_agent != self.current_agent:
                        self.logger.log_info(f"Switching active agent from {self.current_agent} to {new_current_agent}", extra_data={
                            'session_id': session_id,
                            'turn_number': turn_number,
                            'previous_agent': self.current_agent,
                            'new_agent': new_current_agent
                        })
                        
                        # IMPORTANT: Always add tool responses first to avoid OpenAI error
                        agent_messages.extend(tool_responses)
                        
                        # Save current agent context (including tool responses)
                        self.agent_contexts[self.current_agent] = agent_messages.copy()
                        
                        # Switch to new agent
                        self.current_agent = new_current_agent
                        
                        # Initialize new agent context if not exists
                        if new_current_agent not in self.agent_contexts:
                            new_agent_spec = self.prompt_specification.get_agent_prompt(new_current_agent)
                            if new_agent_spec:
                                new_agent_system_prompt = self._format_prompt(new_agent_spec.prompt, variables, session_id)
                                self.agent_contexts[new_current_agent] = [{"role": "system", "content": new_agent_system_prompt}]
                        
                        # Use new agent's context
                        agent_messages = self.agent_contexts[new_current_agent].copy()
                        
                        # Update tools for new agent
                        new_agent_spec = self.prompt_specification.get_agent_prompt(new_current_agent)
                        if new_agent_spec:
                            agent_tools = new_agent_spec.get_tool_schemas()
                        
                        # Add conversation history to new agent context
                        # Add the client's last message to provide context
                        if conversation_history:
                            last_client_message = None
                            for entry in reversed(conversation_history):
                                if entry['speaker'] == 'client':
                                    last_client_message = entry['content']
                                    break
                            
                            if last_client_message:
                                agent_messages.append({"role": "user", "content": last_client_message})
                        
                        # For handoff, add a user message explaining the handoff to the new agent
                        handoff_message = f"You are now taking over this conversation. The previous agent has transferred the customer to you."
                        if conversation_history:
                            # Add context about what has happened so far
                            context_summary = "Previous conversation context: "
                            for entry in conversation_history[-3:]:  # Last 3 turns for context
                                context_summary += f"{entry['speaker']}: {entry['content'][:100]}... "
                            handoff_message += f" {context_summary}"
                        
                        agent_messages.append({"role": "user", "content": handoff_message})
                    else:
                        # Add tool responses to agent messages (normal flow, no handoff)
                        agent_messages.extend(tool_responses)
                    
                    # Get agent response after tool calls
                    # Debug: Log the message structure before sending to OpenAI
                    self.logger.log_info(f"About to make second OpenAI call with messages", extra_data={
                        'session_id': session_id,
                        'message_count': len(agent_messages),
                        'last_3_messages': agent_messages[-3:] if len(agent_messages) >= 3 else agent_messages,
                        'handoff_occurred': new_current_agent is not None
                    })
                    
                    agent_final_response, agent_usage_2 = await self.openai.chat_completion(
                        messages=agent_messages,
                        session_id=session_id,
                        tools=agent_tools,
                        seed=seed
                    )
                    
                    agent_content = agent_final_response.content if hasattr(agent_final_response, 'content') else str(agent_final_response)
                    # Ensure agent_content is never null or empty
                    if not agent_content:
                        agent_content = ""
                    
                    # Log agent turn with tool calls and results
                    self.logger.log_conversation_turn(
                        session_id=session_id,
                        turn_number=turn_number,
                        role=f"agent_{self.current_agent}",
                        content=agent_content,
                        tool_calls=tool_calls,
                        tool_results=[self._safe_parse_tool_result(response["content"]) for response in tool_responses]
                    )
                    
                    # Add tool calls and results to conversation history
                    conversation_history.append({
                        "turn": turn_number,
                        "speaker": f"agent_{self.current_agent}",
                        "content": agent_content,
                        "tool_calls": tool_calls,
                        "tool_results": [self._safe_parse_tool_result(response["content"]) for response in tool_responses],
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    agent_content = agent_response.content if hasattr(agent_response, 'content') else str(agent_response)
                    # Ensure agent_content is never null or empty
                    if not agent_content:
                        agent_content = ""
                    
                    # Log agent turn without tool calls
                    self.logger.log_conversation_turn(
                        session_id=session_id,
                        turn_number=turn_number,
                        role=f"agent_{self.current_agent}",
                        content=agent_content
                    )
                    
                    conversation_history.append({
                        "turn": turn_number,
                        "speaker": f"agent_{self.current_agent}",
                        "content": agent_content,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Add agent response to client's context
                client_messages.append({"role": "user", "content": agent_content})
                
                # Check if we've reached max turns
                if turn_number >= max_turns:
                    break
                
                # Client turn
                client_response, client_usage = await self.openai.chat_completion(
                    messages=client_messages,
                    session_id=session_id,
                    tools=client_tools,
                    seed=seed
                )
                
                # Check if client made tool calls (end_call)
                if hasattr(client_response, 'tool_calls') and client_response.tool_calls:
                    client_tool_calls = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in client_response.tool_calls
                    ]
                    
                    for tool_call in client_response.tool_calls:
                        if tool_call.function.name == "end_call":
                            conversation_ended = True
                            
                            # Parse end call reason
                            try:
                                args = json.loads(tool_call.function.arguments)
                                end_reason = args.get("reason", "conversation completed")
                            except:
                                end_reason = "conversation completed"
                            
                            self.logger.log_info(f"Client ended call: {end_reason}", extra_data={'session_id': session_id})
                            
                            # Log client turn with tool call
                            self.logger.log_conversation_turn(
                                session_id=session_id,
                                turn_number=turn_number,
                                role="client",
                                content=f"[ЗАВЕРШИЛ ЗВОНОК: {end_reason}]",
                                tool_calls=client_tool_calls
                            )
                            
                            conversation_history.append({
                                "turn": turn_number,
                                "speaker": "client",
                                "content": f"[ЗАВЕРШИЛ ЗВОНОК: {end_reason}]",
                                "tool_calls": client_tool_calls,
                                "timestamp": datetime.now().isoformat()
                            })
                            break
                
                if conversation_ended:
                    break
                
                client_content = client_response.content if hasattr(client_response, 'content') else str(client_response)
                
                # Ensure client_content is never null or empty
                if not client_content:
                    client_content = ""
                
                # Log client turn (only if no tool calls were made)
                if not (hasattr(client_response, 'tool_calls') and client_response.tool_calls):
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
                
                # Add client response to agent's context
                agent_messages.append({"role": "assistant", "content": agent_content})
                agent_messages.append({"role": "user", "content": client_content})
                
                # Add client response to client's context for next turn
                client_messages.append({"role": "assistant", "content": client_content})
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log conversation completion
            self.logger.log_conversation_complete(
                session_id=session_id,
                total_turns=turn_number,
                status='completed'
            )
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'completed',
                'total_turns': turn_number,
                'duration_seconds': duration,
                'conversation_history': conversation_history,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'tools_used': True
            }
            
        except Exception as e:
            # Enhanced error logging with more context
            error_context = {
                'session_id': session_id,
                'scenario_name': scenario_name,
                'turn_number': turn_number if 'turn_number' in locals() else 0,
                'duration_so_far': time.time() - start_time,
                'max_turns': max_turns,
                'timeout_sec': timeout_sec,
                'error_type': type(e).__name__,
                'conversation_ended': conversation_ended if 'conversation_ended' in locals() else False,
                'agent_messages_count': len(agent_messages) if 'agent_messages' in locals() else 0,
                'client_messages_count': len(client_messages) if 'client_messages' in locals() else 0
            }
            
            # Check if this is a geographic restriction or persistent OpenAI API failure
            error_message = str(e).lower()
            is_api_blocked = ('geographic restriction' in error_message or 
                            'unsupported_country_region_territory' in error_message or
                            'blocked due to geographic' in error_message)
            
            if is_api_blocked:
                self.logger.log_error(f"OpenAI API blocked - attempting graceful degradation: {str(e)}", exception=e, extra_data=error_context)
                
                # Return a graceful failure with some useful information
                return {
                    'session_id': session_id,
                    'scenario': scenario_name,
                    'status': 'failed_api_blocked',
                    'error': 'OpenAI API blocked due to geographic restrictions',
                    'error_type': 'APIBlockedError',
                    'total_turns': error_context.get('turn_number', 0),
                    'duration_seconds': error_context.get('duration_so_far', 0),
                    'tools_used': True,
                    'conversation_history': conversation_history if 'conversation_history' in locals() else [],
                    'graceful_degradation': True,
                    'partial_completion': error_context.get('turn_number', 0) > 0
                }
            else:
                self.logger.log_error(f"Conversation with tools failed: {str(e)}", exception=e, extra_data=error_context)
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'total_turns': turn_number if 'turn_number' in locals() else 0,
                'duration_seconds': time.time() - start_time,
                'tools_used': True,
                'error_context': error_context
            }


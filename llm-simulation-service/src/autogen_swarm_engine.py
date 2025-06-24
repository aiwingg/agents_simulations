"""
Autogen-based multi-agent conversation engine
Replaces the broken custom multi-agent implementation with Microsoft Autogen's Swarm pattern
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import jinja2

# Autogen imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.messages import HandoffMessage, TextMessage
from autogen_agentchat.teams import Swarm
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.config import Config
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.webhook_manager import WebhookManager


class AutogenSwarmEngine:
    """
    New conversation engine using Microsoft Autogen's Swarm pattern
    Replaces broken custom multi-agent logic with robust Autogen implementation
    """
    
    def __init__(self, openai_api_key: str, prompt_spec_name: str = "file_based_prompts"):
        self.openai_api_key = openai_api_key
        self.logger = get_logger()
        self.webhook_manager = WebhookManager()
        
        # Load prompt specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        
        # Initialize OpenAI model client for Autogen
        self.model_client = OpenAIChatCompletionClient(
            model=Config.OPENAI_MODEL,
            api_key=openai_api_key
        )
        
        # Initialize Jinja2 environment for prompt templating
        self.jinja_env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            undefined=jinja2.StrictUndefined  # Raises error for missing variables
        )
        
        # Agent instances will be created per conversation
        self.agents: Dict[str, AssistantAgent] = {}
        self.swarm: Optional[Swarm] = None
        
        self.logger.log_info(f"AutogenSwarmEngine initialized", extra_data={
            'prompt_spec_name': prompt_spec_name,
            'model': Config.OPENAI_MODEL,
            'agents': list(self.prompt_specification.agents.keys())
        })
    
    def _create_agent_tools(self, agent_name: str, agent_spec, session_id: str) -> List[Any]:
        """
        Create Autogen-compatible Tool objects for an agent
        Uses Tool class instances with proper session isolation from ToolsSpecification
        """
        from src.autogen_tools import AutogenToolFactory
        
        # Create tool factory for this session
        tool_factory = AutogenToolFactory(session_id)
        
        # Get Tool instances for this agent
        tools = tool_factory.get_tools_for_agent(agent_spec.tools)
        
        self.logger.log_info(f"Created {len(tools)} Tool objects for agent '{agent_name}'", extra_data={
            'session_id': session_id,
            'tools': [tool.name for tool in tools]
        })
        
        return tools
    
    def _create_agents_from_config(self, variables: Dict[str, Any], session_id: str) -> Dict[str, AssistantAgent]:
        """
        Create Autogen agents from prompt specification configuration
        Each agent is configured with prompts, tools, and handoff capabilities
        """
        agents = {}
        
        # Skip client and evaluator agents for the MAS - they're handled separately
        mas_agents = {k: v for k, v in self.prompt_specification.agents.items() 
                     if k not in ['client', 'evaluator']}
        
        for agent_name, agent_spec in mas_agents.items():
            # Format the system message with variables using Jinja2
            try:
                system_message = self._format_prompt(agent_spec.prompt, variables, session_id)
            except jinja2.UndefinedError as e:
                raise ValueError(f"Missing variable in prompt for agent '{agent_name}': {e}")
            
            # Create tools for this agent
            tools = self._create_agent_tools(agent_name, agent_spec, session_id)
            
            # Determine handoff targets (exclude client/evaluator)
            handoffs = []
            if agent_spec.handoffs:
                handoffs = [target for target in agent_spec.handoffs.keys() 
                           if target in mas_agents]
            
            # Create Autogen AssistantAgent
            agent = AssistantAgent(
                name=agent_name,
                model_client=self.model_client,
                system_message=system_message,
                tools=tools,
                handoffs=handoffs
            )
            
            agents[agent_name] = agent
            
            self.logger.log_info(f"Created Autogen agent: {agent_name}", extra_data={
                'tools_count': len(tools),
                'handoffs': handoffs,
                'system_message_length': len(system_message)
            })
        
        return agents
    
    def _create_swarm(self, agents: Dict[str, AssistantAgent]) -> Swarm:
        """
        Create Autogen Swarm with termination conditions
        """
        # Create termination conditions
        # We'll terminate when conversation is handed off to "user" or when "TERMINATE" is mentioned
        termination_condition = (
            HandoffTermination(target="user") | 
            TextMentionTermination("TERMINATE") |
            TextMentionTermination("end_call")
        )
        
        # Create swarm with all MAS agents
        swarm = Swarm(
            participants=list(agents.values()),
            termination_condition=termination_condition
        )
        
        self.logger.log_info(f"Created Autogen swarm", extra_data={
            'participant_count': len(agents),
            'participants': list(agents.keys())
        })
        
        return swarm
    
    def _format_prompt(self, template: str, variables: Dict[str, Any], session_id: str) -> str:
        """
        Format prompt template with variables using Jinja2
        Raises error if any required variable is missing
        """
        # Add session_id to variables
        variables = variables.copy()
        variables['session_id'] = session_id
        
        try:
            # Create Jinja2 template and render
            jinja_template = self.jinja_env.from_string(template)
            return jinja_template.render(**variables)
        except jinja2.UndefinedError as e:
            self.logger.log_error(f"Missing variable in prompt template: {e}")
            raise
    
    async def _enrich_variables_with_client_data(self, variables: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Enrich variables with client data from webhook if client_id is provided
        """
        variables = variables.copy()
        webhook_session_id = None
        
        # Check if client_id is provided
        client_id = variables.get('client_id')
        if client_id:
            self.logger.log_info(f"Found client_id in scenario: {client_id}")
            
            # Fetch client data from webhook
            client_data = await self.webhook_manager.get_client_data(client_id)
            client_variables = client_data['variables']
            webhook_session_id = client_data['session_id']
            
            # Override the hardcoded variables with webhook data
            variables.update(client_variables)
            
            self.logger.log_info(f"Enriched variables with client data", extra_data={
                'client_id': client_id,
                'has_dynamic_data': bool(client_variables.get('LOCATIONS')),
                'has_webhook_session_id': bool(webhook_session_id)
            })
        else:
            self.logger.log_info("No client_id provided, using scenario variables as-is")
                
        return variables, webhook_session_id
    
    def _convert_autogen_messages_to_history(self, swarm_messages: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert Autogen's message format to our conversation history format
        Returns the whole history for simplicity
        """
        conversation_history = []
        
        for i, message in enumerate(swarm_messages):
            # Convert each Autogen message to our format
            history_entry = {
                "turn": i + 1,
                "speaker": getattr(message, 'source', 'unknown'),
                "content": getattr(message, 'content', str(message)),
                "timestamp": datetime.now().isoformat(),
                "message_type": type(message).__name__
            }
            
            # Add tool call information if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                history_entry["tool_calls"] = message.tool_calls
            
            conversation_history.append(history_entry)
        
        return conversation_history
    
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], 
                                        max_turns: Optional[int] = None, 
                                        timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Run conversation using Autogen Swarm pattern
        Replaces the old broken multi-agent conversation logic
        """
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
        else:
            session_id = await self.webhook_manager.initialize_session()
        
        self.logger.log_info(f"Starting Autogen swarm conversation", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'variables': list(variables.keys())
        })
        
        start_time = time.time()
        
        try:
            # Create agents for this conversation with session-isolated tools
            self.agents = self._create_agents_from_config(variables, session_id)
            
            # Create swarm
            self.swarm = self._create_swarm(self.agents)
            
            # Get client system prompt for simulation
            client_spec = self.prompt_specification.get_agent_prompt('client')
            if not client_spec:
                raise ValueError("Missing client specification")
            
            try:
                client_system_prompt = self._format_prompt(client_spec.prompt, variables, session_id)
            except jinja2.UndefinedError as e:
                raise ValueError(f"Missing variable in client prompt: {e}")
            
            # Simulate client greeting to start conversation
            initial_message = TextMessage(
                content="Добрый день! Хочу сделать заказ.",
                source="client"
            )
            
            # Run the swarm conversation
            # Note: This is a simplified version - actual implementation will need
            # to handle client-swarm interaction more sophisticatedly
            result = await self.swarm.run(task=initial_message.content)
            
            # Convert all messages to conversation history
            conversation_history = self._convert_autogen_messages_to_history(result.messages)
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.log_info(f"Autogen swarm conversation completed", extra_data={
                'session_id': session_id,
                'total_messages': len(result.messages),
                'duration': duration
            })
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'completed',
                'total_turns': len(conversation_history),
                'duration_seconds': duration,
                'conversation_history': conversation_history,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'tools_used': True
            }
            
        except Exception as e:
            error_context = {
                'session_id': session_id,
                'scenario_name': scenario_name,
                'duration_so_far': time.time() - start_time,
                'error_type': type(e).__name__,
                'variables_provided': list(variables.keys())
            }
            
            self.logger.log_error(f"Autogen swarm conversation failed: {str(e)}", 
                                exception=e, extra_data=error_context)
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'total_turns': 0,
                'duration_seconds': time.time() - start_time,
                'tools_used': True,
                'error_context': error_context
            }


class AutogenSwarmFactory:
    """
    Factory for creating isolated Autogen swarm instances per batch
    Ensures complete isolation between concurrent batch executions
    """
    
    @staticmethod
    def create_swarm_engine(openai_api_key: str, prompt_spec_name: str) -> AutogenSwarmEngine:
        """
        Create a new isolated AutogenSwarmEngine instance
        Each batch gets its own engine to prevent conversation bleed
        """
        return AutogenSwarmEngine(openai_api_key, prompt_spec_name)
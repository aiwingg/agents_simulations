"""
AutogenConversationEngine - Service Layer
Main engine implementing ConversationEngine contract using AutoGen Swarm pattern
Replaces the existing ConversationEngine with multi-agent orchestration capabilities
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# AutoGen imports
from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import HandoffMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Existing infrastructure
from src.openai_wrapper import OpenAIWrapper
from src.webhook_manager import WebhookManager
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.config import Config

# AutoGen infrastructure
from src.autogen_mas_factory import AutogenMASFactory
from src.conversation_adapter import ConversationAdapter
from src.autogen_tools import AutogenToolFactory

# Braintrust tracing import
from braintrust import traced


class AutogenConversationEngine:
    """
    Main engine implementing ConversationEngine contract using AutoGen Swarm pattern.
    Maintains exact same interface as existing ConversationEngine while leveraging
    AutoGen's multi-agent coordination, tool calling, and memory management.
    """
    
    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        """
        Initialize AutogenConversationEngine with OpenAIWrapper and prompt specification.
        
        Args:
            openai_wrapper: OpenAI API wrapper instance
            prompt_spec_name: Name of the prompt specification to use (defaults to "default_prompts")
        """
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.logger = get_logger()
        self.prompt_spec_name = prompt_spec_name
        
        # Load prompt specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        
        self.logger.log_info(f"AutogenConversationEngine initialized with prompt specification: {prompt_spec_name}", extra_data={
            'spec_name': prompt_spec_name,
            'spec_version': self.prompt_specification.version,
            'agents': list(self.prompt_specification.agents.keys()),
            'engine_type': 'AutoGen'
        })
    
    def _format_prompt(self, template: str, variables: Dict[str, Any], session_id: str) -> str:
        """
        Format prompt template with variables using Jinja2.
        Reuses existing formatting logic from ConversationEngine for compatibility.
        """
        try:
            # Reuse existing formatting logic from the original ConversationEngine
            from jinja2 import Environment, BaseLoader, Template, StrictUndefined, DebugUndefined, UndefinedError
            
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
                'locations': variables.get('LOCATION', 'Адрес не указан'),
                'CLIENT_NAME': variables.get('CLIENT_NAME', 'Клиент'),
                'LOCATION': variables.get('LOCATION', 'Адрес не указан')
            }
            
            # Add defaults for missing variables
            for key, default_value in defaults.items():
                if key not in variables:
                    variables[key] = default_value
            
            # Create Jinja2 environment with undefined handling
            jinja_env = Environment(
                loader=BaseLoader(),
                undefined=StrictUndefined
            )
            
            # Use Jinja2 to render the template with proper variable handling
            jinja_template = jinja_env.from_string(template)
            return jinja_template.render(**variables)
            
        except Exception as e:
            if isinstance(e, UndefinedError):
                self.logger.log_error(f"Missing variable in prompt template: {e}")
                # For missing variables, try with a more lenient approach
                try:
                    jinja_env_lenient = Environment(
                        loader=BaseLoader(),
                        undefined=DebugUndefined
                    )
                    jinja_template = jinja_env_lenient.from_string(template)
                    result = jinja_template.render(**variables)
                    self.logger.log_info(f"Template rendered with debug undefined variables")
                    return result
                except Exception as fallback_error:
                    self.logger.log_error(f"Template rendering failed even with lenient mode: {fallback_error}")
                    return template
            else:
                self.logger.log_error(f"Template rendering error: {e}")
                return template
    
    async def _enrich_variables_with_client_data(self, variables: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Enrich variables with client data from webhook if client_id is provided.
        Falls back to existing values if client_id is not present.
        Reuses existing logic from ConversationEngine for compatibility.
        
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

    @traced(name="autogen_run_conversation")
    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Run a basic conversation simulation without tools.
        Delegates to run_conversation_with_tools() with empty tools for consistency.
        
        Args:
            scenario: Dictionary containing scenario name and variables
            max_turns: Maximum number of conversation turns (optional)
            timeout_sec: Timeout in seconds (optional)
            
        Returns:
            Dictionary matching existing ConversationEngine output contract
        """
        self.logger.log_info(f"Running basic conversation via AutoGen Swarm", extra_data={
            'scenario': scenario.get('name', 'unknown'),
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'tools_enabled': False
        })
        
        # Delegate to run_conversation_with_tools() with tools disabled
        result = await self.run_conversation_with_tools(scenario, max_turns, timeout_sec)
        
        # Ensure tools_used is False for basic conversation
        if 'tools_used' in result:
            result['tools_used'] = False
            
        return result

    @traced(name="autogen_run_conversation_with_tools")
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Run conversation simulation with tool calling and multi-agent handoff support using AutoGen Swarm.
        
        Args:
            scenario: Dictionary containing scenario name and variables
            max_turns: Maximum number of conversation turns (optional)
            timeout_sec: Timeout in seconds (optional)
            
        Returns:
            Dictionary matching existing ConversationEngine output contract
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
            self.logger.log_info(f"Using session_id from webhook: {session_id}")
        else:
            session_id = await self.webhook_manager.initialize_session()
            self.logger.log_info(f"Using generated session_id: {session_id}")
        
        self.logger.log_info(f"Starting AutoGen conversation simulation with tools", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec,
            'has_client_id': 'client_id' in scenario.get('variables', {}),
            'using_webhook_session': bool(webhook_session_id),
            'spec_name': self.prompt_spec_name
        })
        
        start_time = time.time()
        
        try:
            # Create AutoGen model client from OpenAIWrapper
            model_client = self._create_autogen_client()
            
            # Create session-isolated tool factory
            tool_factory = AutogenToolFactory(session_id)
            
            # Collect all unique tool names from all agents
            all_tool_names = set()
            for agent_spec in self.prompt_specification.agents.values():
                all_tool_names.update(agent_spec.tools)
            
            # Create tools for all agents (session-isolated)
            tools = tool_factory.get_tools_for_agent(list(all_tool_names))
            
            # Create AutoGen Swarm team
            mas_factory = AutogenMASFactory(session_id)
            swarm = mas_factory.create_swarm_team(
                system_prompt_spec=self.prompt_specification,
                tools=tools,
                model_client=model_client,
                user_handoff_target="client"
            )
            
            # Prepare initial task based on system prompt spec
            # We simulate the client greeting to start the conversation
            initial_task = "Добрый день!" # Default greeting
            
            # If there's a specific client prompt or greeting in variables, use that
            if 'client_greeting' in variables:
                initial_task = variables['client_greeting']
            elif 'GREETING' in variables:
                initial_task = variables['GREETING']
            
            self.logger.log_info(f"Starting AutoGen Swarm conversation", extra_data={
                'session_id': session_id,
                'initial_task': initial_task,
                'agents_count': len(self.prompt_specification.agents),
                'tools_count': len(tools)
            })
            
            # Run conversation with timeout
            try:
                # Use asyncio.wait_for to enforce timeout_sec
                task_result = await asyncio.wait_for(
                    swarm.run_stream(task=initial_task),
                    timeout=timeout_sec
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                self.logger.log_info(f"AutoGen Swarm conversation completed", extra_data={
                    'session_id': session_id,
                    'duration': duration,
                    'stop_reason': task_result.stop_reason,
                    'messages_count': len(task_result.messages)
                })
                
                # Convert AutoGen TaskResult to contract format using ConversationAdapter
                result = ConversationAdapter.autogen_to_contract_format(
                    task_result=task_result,
                    session_id=session_id,
                    scenario_name=scenario_name,
                    duration=duration,
                    start_time=start_time
                )
                
                # Log conversation completion
                self.logger.log_conversation_complete(
                    session_id=session_id,
                    total_turns=result.get('total_turns', 0),
                    status=result.get('status', 'completed')
                )
                
                return result
                
            except asyncio.TimeoutError:
                end_time = time.time()
                duration = end_time - start_time
                
                self.logger.log_error(f"AutoGen conversation timeout after {timeout_sec} seconds", extra_data={
                    'session_id': session_id,
                    'timeout_sec': timeout_sec,
                    'actual_duration': duration,
                    'scenario_name': scenario_name
                })
                
                # Return timeout result in contract format
                return {
                    'session_id': session_id,
                    'scenario': scenario_name,
                    'status': 'failed',
                    'error': f'Conversation timeout after {timeout_sec} seconds',
                    'error_type': 'TimeoutError',
                    'total_turns': 0,
                    'duration_seconds': duration,
                    'conversation_history': [],
                    'start_time': datetime.fromtimestamp(start_time).isoformat(),
                    'end_time': datetime.fromtimestamp(end_time).isoformat(),
                    'tools_used': True
                }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            # Enhanced error logging with more context
            error_context = {
                'session_id': session_id,
                'scenario_name': scenario_name,
                'duration_so_far': duration,
                'max_turns': max_turns,
                'timeout_sec': timeout_sec,
                'error_type': type(e).__name__,
                'spec_name': self.prompt_spec_name
            }
            
            # Check if this is a geographic restriction or persistent OpenAI API failure
            error_message = str(e).lower()
            is_api_blocked = ('geographic restriction' in error_message or 
                            'unsupported_country_region_territory' in error_message or
                            'blocked due to geographic' in error_message)
            
            if is_api_blocked:
                self.logger.log_error(f"OpenAI API blocked in AutoGen engine - attempting graceful degradation: {str(e)}", 
                                    exception=e, extra_data=error_context)
                
                # Return a graceful failure with some useful information
                return {
                    'session_id': session_id,
                    'scenario': scenario_name,
                    'status': 'failed_api_blocked',
                    'error': 'OpenAI API blocked due to geographic restrictions',
                    'error_type': 'APIBlockedError',
                    'total_turns': 0,
                    'duration_seconds': duration,
                    'tools_used': True,
                    'conversation_history': [],
                    'start_time': datetime.fromtimestamp(start_time).isoformat(),
                    'end_time': datetime.fromtimestamp(end_time).isoformat(),
                    'graceful_degradation': True,
                    'partial_completion': False
                }
            else:
                self.logger.log_error(f"AutoGen conversation with tools failed: {str(e)}", 
                                    exception=e, extra_data=error_context)
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'total_turns': 0,
                'duration_seconds': duration,
                'tools_used': True,
                'conversation_history': [],
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'error_context': error_context
            }
    
    def _create_autogen_client(self) -> OpenAIChatCompletionClient:
        """
        Creates OpenAIChatCompletionClient from existing OpenAIWrapper config.
        
        Returns:
            Configured OpenAIChatCompletionClient for AutoGen usage
        """
        # Extract configuration from OpenAIWrapper
        api_key = self.openai.client.api_key
        model = self.openai.model
        
        # Create AutoGen-compatible client
        client = OpenAIChatCompletionClient(
            model=model,
            api_key=api_key
        )
        
        self.logger.log_info(f"Created AutoGen client", extra_data={
            'model': model,
            'engine_type': 'AutoGen'
        })
        
        return client
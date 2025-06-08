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

class ConversationEngine:
    """Core engine for managing conversations between Agent-LLM and Client-LLM"""
    
    def __init__(self, openai_wrapper: OpenAIWrapper):
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.tool_emulator = ToolEmulator()
        self.logger = get_logger()
        
        # Load prompt templates
        self.agent_prompt = self._load_prompt_template("agent_system")
        self.client_prompt = self._load_prompt_template("client_system")
    
    def _load_prompt_template(self, prompt_name: str) -> str:
        """Load prompt template from file"""
        try:
            prompt_path = Config.get_prompt_path(prompt_name)
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.log_error(f"Failed to load prompt template: {prompt_name}", exception=e)
            return f"You are a {prompt_name.replace('_', ' ')}."
    
    def _format_prompt(self, template: str, variables: Dict[str, Any], session_id: str) -> str:
        """Format prompt template with variables"""
        try:
            # Add session_id to variables
            variables = variables.copy()
            variables['session_id'] = session_id
            
            return template.format(**variables)
        except KeyError as e:
            self.logger.log_error(f"Missing variable in prompt template: {e}")
            return template
    
    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Run a complete conversation simulation"""
        
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC
        
        # Initialize session
        session_id = await self.webhook_manager.initialize_session()
        scenario_name = scenario.get('name', 'unknown')
        variables = scenario.get('variables', {})
        seed = variables.get('SEED')
        
        self.logger.log_info(f"Starting conversation simulation", extra_data={
            'session_id': session_id,
            'scenario': scenario_name,
            'max_turns': max_turns,
            'timeout_sec': timeout_sec
        })
        
        start_time = time.time()
        
        try:
            # Format system prompts
            agent_system_prompt = self._format_prompt(self.agent_prompt, variables, session_id)
            client_system_prompt = self._format_prompt(self.client_prompt, variables, session_id)
            
            # Initialize conversation history
            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            client_messages = [{"role": "system", "content": client_system_prompt}]
            
            # Start conversation with agent greeting
            agent_messages.append({"role": "user", "content": "Начните разговор с клиентом."})
            
            conversation_history = []
            turn_number = 0
            
            # Run conversation loop
            while turn_number < max_turns:
                # Check timeout
                if time.time() - start_time > timeout_sec:
                    self.logger.log_error(f"Conversation timeout after {timeout_sec} seconds", extra_data={'session_id': session_id})
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
                client_messages.append({"role": "assistant", "content": agent_response})
                
                # Check if we've reached max turns
                if turn_number >= max_turns:
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
                
                # Add agent response to client's context for next turn
                client_messages.append({"role": "user", "content": client_response})
                
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
            self.logger.log_error(f"Conversation failed", exception=e, extra_data={'session_id': session_id})
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'total_turns': turn_number if 'turn_number' in locals() else 0,
                'duration_seconds': time.time() - start_time
            }
    
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Run conversation with tool calling support (future enhancement)"""
        # This is a placeholder for future tool calling implementation
        # For now, just run regular conversation
        return await self.run_conversation(scenario, max_turns, timeout_sec)


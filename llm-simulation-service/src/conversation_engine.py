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
            # Format system prompts
            agent_system_prompt = self._format_prompt(self.agent_prompt, variables, session_id)
            client_system_prompt = self._format_prompt(self.client_prompt, variables, session_id)
            self.logger.log_info(f"Agent system prompt: {agent_system_prompt}")
            self.logger.log_info(f"Client system prompt: {client_system_prompt}")
            
            # Initialize conversation history
            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            client_messages = [{"role": "system", "content": client_system_prompt}]
            
            # Start conversation with client greeting
            client_messages.append({"role": "user", "content": "Добрый день!"})
            
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
                
                # Add client response to client's context for next turn
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
    
    def _get_agent_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools schema for agent (all available tools)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "rag_find_products",
                    "description": "Найти товары соответствующие описанию",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "title": "Message",
                                "type": "string",
                                "description": "Описание товаров для поиска. Описание может содержать\n- Специфичного производителя, например \"ООО Золотой Бык\"\n- Термическое состояние (охлажденное, замороженное, и тд)\n- Способ упаковки (пакет, поштучно, и тд)\n- Животное (курица, говядина, и тд)\n- Объект (курица, грудка, и тд)\n- Дополнительные указания, например \"в маринаде\"\n\nПример описания: \"курица замороженная, в маринаде, 100 кг, упаковка по 1 кг\"\n"
                            },
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["message", "execution_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_from_cart",
                    "description": "Вызывается только, когда известен товар, который необходо удалить! Для удаления товара из корзины. Принимает код товара.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "description": "Функция принимает список строк, где каждая строка должна быть равна коду продукта, который можно получить из инструмента rag_find_products\n",
                                "title": "Items",
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["items", "execution_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_current_location",
                    "description": "Устанавливает адрес, на который оформляется заказ",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location_id": {
                                "type": "integer",
                                "description": "Номер адреса, на который необходимо оформить заказ. Можно выбрать из списка доступных адресов. По умолчанию используется адрес с индексом 1."
                            },
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["location_id", "execution_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cart",
                    "description": "Для получения всех товаров из карзины.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["execution_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "change_delivery_date",
                    "description": "Изменяет дату доставки",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "delivery_date": {
                                "type": "string",
                                "description": "Дата доставки в формате YYYY-MM-DD"
                            },
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["delivery_date", "execution_message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_to_cart",
                    "description": "Вызывается только, когда известен товар, который необходо добавить! Для сохранения товара в корзину, когда пользователь точно уверен в своем выборе. Принимает код товара и кол-во, и номер способа упаковки в случае наличия нескольких вариантов",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "description": "Список продуктов с количеством. Каждый элемент содержит:\n- код продукта (можно получить через инструмент rag_find_products)\n- количество продукта (в штуках, кг и т.д.)",
                                "type": "array",
                                "title": "Items",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_code": {
                                            "type": "string",
                                            "description": "Код продукта из rag_find_products"
                                        },
                                        "quantity": {
                                            "type": "number",
                                            "description": "Количество продукта (шт, кг и т.п.)"
                                        },
                                        "packaging_type": {
                                            "type": "integer",
                                            "description": "Номер способа упаковки (опционально в случае нескольких способов)"
                                        }
                                    },
                                    "required": ["product_code", "quantity"]
                                }
                            },
                            "execution_message": {
                                "type": "string",
                                "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language."
                            }
                        },
                        "required": ["items", "execution_message"]
                    }
                }
            }
        ]
    
    def _get_client_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools schema for client (only end_call)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the conversation/call when satisfied or done",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for ending the call"}
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]
    
    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]], session_id: str) -> List[Dict[str, Any]]:
        """Handle tool calls and return tool responses"""
        tool_responses = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            
            try:
                # Parse arguments
                arguments = json.loads(tool_call["function"]["arguments"])
                
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
                    'original_arguments': arguments,
                    'filtered_arguments': filtered_arguments,
                    'result': tool_response["content"]
                })
                
            except Exception as e:
                self.logger.log_error(f"Tool call failed: {tool_name}", exception=e, extra_data={'session_id': session_id})
                tool_responses.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": json.dumps({"error": f"Tool execution failed: {str(e)}"})
                })
        
        return tool_responses
    
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
        
        # Use webhook session_id if available, otherwise initialize a new session
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
            # Format system prompts
            agent_system_prompt = self._format_prompt(self.agent_prompt, variables, session_id)
            client_system_prompt = self._format_prompt(self.client_prompt, variables, session_id)
            self.logger.log_info(f"Agent system prompt: {agent_system_prompt}")
            self.logger.log_info(f"Client system prompt: {client_system_prompt}")
            
            # Initialize conversation history
            agent_messages = [{"role": "system", "content": agent_system_prompt}]
            client_messages = [{"role": "system", "content": client_system_prompt}]
            
            # Get tools schemas
            agent_tools = self._get_agent_tools_schema()
            client_tools = self._get_client_tools_schema()
            
            # Start conversation with client greeting
            client_messages.append({"role": "user", "content": "Добрый день!"})
            
            conversation_history = []
            turn_number = 0
            conversation_ended = False
            
            # Run conversation loop
            while turn_number < max_turns and not conversation_ended:
                # Check timeout
                if time.time() - start_time > timeout_sec:
                    self.logger.log_error(f"Conversation timeout after {timeout_sec} seconds", extra_data={'session_id': session_id})
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
                        "content": agent_response.content,
                        "tool_calls": tool_calls
                    })
                    
                    # Process tool calls
                    tool_responses = await self._handle_tool_calls(tool_calls, session_id)
                    
                    # Add tool responses to agent messages
                    agent_messages.extend(tool_responses)
                    
                    # Get agent response after tool calls
                    agent_final_response, agent_usage_2 = await self.openai.chat_completion(
                        messages=agent_messages,
                        session_id=session_id,
                        tools=agent_tools,
                        seed=seed
                    )
                    
                    agent_content = agent_final_response.content if hasattr(agent_final_response, 'content') else str(agent_final_response)
                    
                    # Log agent turn with tool calls and results
                    self.logger.log_conversation_turn(
                        session_id=session_id,
                        turn_number=turn_number,
                        role="agent",
                        content=agent_content,
                        tool_calls=tool_calls,
                        tool_results=[self._safe_parse_tool_result(response["content"]) for response in tool_responses]
                    )
                    
                    # Add tool calls and results to conversation history
                    conversation_history.append({
                        "turn": turn_number,
                        "speaker": "agent",
                        "content": agent_content,
                        "tool_calls": tool_calls,
                        "tool_results": [self._safe_parse_tool_result(response["content"]) for response in tool_responses],
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    agent_content = agent_response.content if hasattr(agent_response, 'content') else str(agent_response)
                    
                    # Log agent turn without tool calls
                    self.logger.log_conversation_turn(
                        session_id=session_id,
                        turn_number=turn_number,
                        role="agent",
                        content=agent_content
                    )
                    
                    conversation_history.append({
                        "turn": turn_number,
                        "speaker": "agent",
                        "content": agent_content,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Add agent response to client's context
                client_messages.append({"role": "assistant", "content": agent_content})
                
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
                client_messages.append({"role": "user", "content": client_content})
            
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
            self.logger.log_error(f"Conversation with tools failed", exception=e, extra_data={'session_id': session_id})
            
            return {
                'session_id': session_id,
                'scenario': scenario_name,
                'status': 'failed',
                'error': str(e),
                'total_turns': turn_number if 'turn_number' in locals() else 0,
                'duration_seconds': time.time() - start_time,
                'tools_used': True
            }


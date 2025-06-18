"""
Tool emulation system for conversation simulation
"""
import json
import aiohttp
from typing import Dict, Any, List, Optional
from src.logging_utils import get_logger
import ssl
import certifi
import asyncio

ssl_context = ssl.create_default_context(cafile=certifi.where())

class ToolEmulator:
    """Emulates external tools/APIs for conversation simulation"""
    
    def __init__(self):
        self.logger = get_logger()
        
        # API base URL
        self.base_url = "https://aiwingg.com/rag"
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Simulate calling an external tool"""
        
        self.logger.log_info(f"🔧 TOOL CALL INITIATED", {
            "tool_name": tool_name,
            "session_id": session_id,
            "parameters": parameters
        })
        
        try:
            if tool_name == "rag_find_products":
                return await self._rag_find_products(parameters, session_id)
            elif tool_name == "remove_from_cart":
                return await self._remove_from_cart(parameters, session_id)
            elif tool_name == "set_current_location":
                return await self._set_current_location(parameters, session_id)
            elif tool_name == "get_cart":
                return await self._get_current_cart(parameters, session_id)
            elif tool_name == "change_delivery_date":
                return await self._change_delivery_date(parameters, session_id)
            elif tool_name == "add_to_cart":
                return await self._add_to_cart(parameters, session_id)
            else:
                error_msg = f"Unknown tool: {tool_name}"
                self.logger.log_error(f"❌ UNKNOWN TOOL", None, {
                    "tool_name": tool_name,
                    "session_id": session_id,
                    "error": error_msg
                })
                return {"result": f"Ошибка: неизвестный инструмент {tool_name}"}
                
        except Exception as e:
            self.logger.log_error(f"❌ TOOL CALL EXCEPTION", e, {
                "tool_name": tool_name,
                "session_id": session_id,
                "parameters": parameters
            })
            return {"result": "Ошибка при выполнении запроса"}
    
    async def _make_api_request(self, endpoint: str, payload: Dict[str, Any], session_id: str, tool_name: str, parameters: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Make HTTP request to external API with detailed logging and retry logic"""
        
        url = f"{self.base_url}{endpoint}"
        
        self.logger.log_info(f"🌐 HTTP REQUEST INITIATED", {
            "tool_name": tool_name,
            "session_id": session_id,
            "method": "POST",
            "url": url,
            "payload": payload
        })
        
        # Progressive timeout increases: 15s, 20s, 25s, 30s
        timeouts = [15, 20, 25, 30]
        
        for attempt in range(max_retries + 1):
            try:
                current_timeout = timeouts[min(attempt, len(timeouts) - 1)]
                timeout = aiohttp.ClientTimeout(total=current_timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload, ssl=ssl_context) as response:
                        response_status = response.status
                        response_headers = dict(response.headers)
                        
                        try:
                            response_data = await response.json()
                        except:
                            response_text = await response.text()
                            response_data = {"raw_text": response_text}
                        
                        self.logger.log_info(f"📡 HTTP RESPONSE RECEIVED", {
                            "tool_name": tool_name,
                            "session_id": session_id,
                            "status_code": response_status,
                            "headers": response_headers,
                            "response_data": response_data,
                            "attempt": attempt + 1,
                            "timeout_used": current_timeout
                        })
                        
                        if response_status == 200:
                            self.logger.log_info(f"✅ API CALL SUCCESS", {
                                "tool_name": tool_name,
                                "session_id": session_id,
                                "result": response_data,
                                "attempt": attempt + 1
                            })
                            return response_data
                        elif response_status in [503, 502, 504] and attempt < max_retries:
                            # Retry on service unavailable errors
                            wait_time = (attempt + 1) * 3  # 3, 6, 9 seconds
                            self.logger.log_info(f"⏳ RETRYING after {response_status} error", {
                                "tool_name": tool_name,
                                "session_id": session_id,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "wait_time": wait_time
                            })
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            self.logger.log_error(f"❌ API CALL HTTP ERROR", None, {
                                "tool_name": tool_name,
                                "session_id": session_id,
                                "status_code": response_status,
                                "response": response_data,
                                "attempt": attempt + 1
                            })
                            # Return enhanced fallback response
                            return self._get_fallback_response(tool_name, parameters, response_status, response_data)
                            
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 3
                    self.logger.log_info(f"⏳ RETRYING after timeout", {
                        "tool_name": tool_name,
                        "session_id": session_id,
                        "attempt": attempt + 1,
                        "timeout_used": current_timeout,
                        "wait_time": wait_time
                    })
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.log_error(f"❌ HTTP TIMEOUT ERROR", None, {
                        "tool_name": tool_name,
                        "session_id": session_id,
                        "url": url,
                        "final_attempt": True,
                        "total_timeout": current_timeout
                    })
                    return self._get_fallback_response(tool_name, parameters, "timeout", None)
            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 3
                    self.logger.log_info(f"⏳ RETRYING after client error", {
                        "tool_name": tool_name,
                        "session_id": session_id,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "wait_time": wait_time
                    })
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.log_error(f"❌ HTTP CLIENT ERROR", e, {
                        "tool_name": tool_name,
                        "session_id": session_id,
                        "url": url,
                        "payload": payload,
                        "final_attempt": True
                    })
                    return self._get_fallback_response(tool_name, parameters, "client_error", str(e))
            except Exception as e:
                self.logger.log_error(f"❌ UNEXPECTED API ERROR", e, {
                    "tool_name": tool_name,
                    "session_id": session_id,
                    "url": url,
                    "payload": payload,
                    "attempt": attempt + 1
                })
                return self._get_fallback_response(tool_name, parameters, "unexpected_error", str(e))
        
        # This should never be reached due to the logic above, but just in case
        return self._get_fallback_response(tool_name, parameters, "max_retries_exceeded", None)
    
    def _get_fallback_response(self, tool_name: str, parameters: Dict[str, Any], error_type: str, error_details: Any) -> Dict[str, Any]:
        """Generate appropriate fallback responses when external APIs fail"""
        
        if tool_name == "rag_find_products":
            # Enhanced fallback for product search - try to provide helpful responses
            query = parameters.get("message", "").lower()
            return {
                "result": f"Произошла ошибка поиска товаров. Ошибка: {error_type}, {error_details}"
            }
    
        elif tool_name == "add_to_cart":
            return {
                "result": f"Произошла ошибка при добавлении товара в корзину. Ошибка: {error_type}, {error_details}"
            }
        
        elif tool_name == "set_current_location":
            return {
                "result": f"Произошла ошибка при установке адреса доставки. Ошибка: {error_type}, {error_details}"
            }
        
        elif tool_name == "get_cart":
            return {
                "result": f"Произошла ошибка при получении корзины. Ошибка: {error_type}, {error_details}"
            }
        
        elif tool_name == "change_delivery_date":
            return {
                "result": f"Произошла ошибка при изменении даты доставки. Ошибка: {error_type}, {error_details}"
            }
        
        elif tool_name == "remove_from_cart":
            return {
                "result": f"Произошла ошибка при удалении товара из корзины. Ошибка: {error_type}, {error_details}"
            }
        
        else:
            return {
                "result": f"Сервис временно недоступен. Ошибка: {error_type}, {error_details}"
            }
    
    async def _set_current_location(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Set current location for delivery"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/set_current_location", payload, session_id, "set_current_location", parameters)
        
        self.logger.log_info(f"🏠 SET_CURRENT_LOCATION RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result
    
    async def _change_delivery_date(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Set current location for delivery"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                } 
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/set_current_location", payload, session_id, "add_to_cart", parameters)
        
        self.logger.log_info(f"🛒 ADD_TO_CART RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result
  
    async def _remove_from_cart(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Remove items from shopping cart"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/add_to_cart", payload, session_id, "add_to_cart", parameters)
        
        self.logger.log_info(f"🛒 ADD_TO_CART RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result

    async def _rag_find_products(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Find products using RAG search"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/rag_find_products", payload, session_id, "rag_find_products", parameters)
        
        self.logger.log_info(f"🔍 RAG_FIND_PRODUCTS RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result
    
    async def _add_to_cart(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Add items to shopping cart"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/add_to_cart", payload, session_id, "add_to_cart", parameters)
        
        self.logger.log_info(f"🛒 ADD_TO_CART RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result
    
    async def _get_current_cart(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Get current cart contents"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/get_cart", payload, session_id, "get_cart", parameters)
        
        self.logger.log_info(f"📋 GET_CURRENT_CART RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result
    
    async def _confirm_order(self, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Confirm and finalize order"""
        
        payload = {
            "call": {
                "retell_llm_dynamic_variables": {
                    "session_id": session_id
                }
            },
            "args": parameters
        }
        
        result = await self._make_api_request("/confirm_order", payload, session_id, "confirm_order", parameters)
        
        self.logger.log_info(f"✅ CONFIRM_ORDER RESULT", {
            "session_id": session_id,
            "parameters": parameters,
            "result": result
        })
        
        return result


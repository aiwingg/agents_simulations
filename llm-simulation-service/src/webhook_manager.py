"""
Webhook integration for session initialization and client data retrieval
"""
import aiohttp
import uuid
import json
import ssl
import certifi
from typing import Optional, Dict, Any
from src.config import Config
from src.logging_utils import get_logger

ssl_context = ssl.create_default_context(cafile=certifi.where())

class WebhookManager:
    """Manages webhook interactions for session initialization and client data retrieval"""
    
    def __init__(self):
        self.logger = get_logger()
        self.webhook_url = Config.WEBHOOK_URL
        self.rag_webhook_url = "https://aiwingg.com/rag/webhook"
    
    async def get_client_variables(self, client_id: str) -> Dict[str, str]:
        """
        Retrieve client variables from the RAG webhook using client_id
        
        Args:
            client_id: The client ID to fetch data for
            
        Returns:
            Dictionary containing location, delivery_days, and purchase_history
        """
        client_data = await self.get_client_data(client_id)
        return client_data['variables']
    
    async def get_client_data(self, client_id: str) -> Dict[str, Any]:
        """
        Retrieve client data including variables and session_id from the RAG webhook
        
        Args:
            client_id: The client ID to fetch data for
            
        Returns:
            Dictionary containing 'variables' and 'session_id'
        """
        try:
            payload = {
                "call_inbound": {
                    "from_number": client_id
                }
            }
            
            self.logger.log_info(f"Fetching client data for client_id: {client_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rag_webhook_url, 
                    json=payload,
                    timeout=30,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract dynamic variables from response
                        dynamic_variables = data.get("call_inbound", {}).get("dynamic_variables", {})
                        
                        if not dynamic_variables:
                            self.logger.log_error("Webhook response missing dynamic_variables")
                            return {
                                'variables': self._get_fallback_variables(),
                                'session_id': None
                            }
                        
                        # Extract session_id from dynamic variables
                        webhook_session_id = dynamic_variables.get("session_id")
                        
                        # Map the response variables to our expected format
                        client_variables = {
                            "LOCATIONS": dynamic_variables.get("locations", ""),
                            "DELIVERY_DAYS": dynamic_variables.get("delivery_days", ""),
                            "PURCHASE_HISTORY": dynamic_variables.get("purchase_history", ""),
                            "NAME": dynamic_variables.get("name", ""),
                            "CURRENT_DATE": dynamic_variables.get("current_date", ""),
                        }
                        
                        self.logger.log_info(f"Successfully retrieved client data", extra_data={
                            'client_id': client_id,
                            'has_location': bool(client_variables["LOCATIONS"]),
                            'has_delivery_days': bool(client_variables["DELIVERY_DAYS"]),
                            'has_purchase_history': bool(client_variables["PURCHASE_HISTORY"]),
                            'has_session_id': bool(webhook_session_id)
                        })
                        
                        return {
                            'variables': client_variables,
                            'session_id': webhook_session_id
                        }
                        
                    else:
                        self.logger.log_error(f"RAG webhook request failed with status: {response.status}")
                        response_text = await response.text()
                        self.logger.log_error(f"Response content: {response_text}")
                        
        except Exception as e:
            self.logger.log_error("Failed to retrieve client data from RAG webhook", exception=e)
        
        # Return fallback data if webhook fails
        return {
            'variables': self._get_fallback_variables(),
            'session_id': None
        }
    
    def _get_fallback_variables(self) -> Dict[str, str]:
        """Return fallback values when webhook fails"""
        return {
            "LOCATIONS": "Адрес не определен",
            "DELIVERY_DAYS": "По согласованию",
            "PURCHASE_HISTORY": "История покупок недоступна"
        }

    async def initialize_session(self) -> str:
        """Initialize a new session via webhook"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.webhook_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        session_id = data.get('session_id')
                        
                        if session_id:
                            self.logger.log_info(f"Retrieved session ID from webhook: {session_id}")
                            return session_id
                        else:
                            self.logger.log_error("Webhook response missing session_id field")
                    else:
                        self.logger.log_error(f"Webhook request failed with status: {response.status}")
                        
        except Exception as e:
            self.logger.log_error("Failed to initialize session via webhook", exception=e)
        
        # Fallback to UUID generation
        session_id = str(uuid.uuid4())
        self.logger.log_info(f"Generated fallback session ID: {session_id}")
        return session_id
    
    async def validate_webhook(self) -> bool:
        """Validate that webhook is accessible and returns expected format"""
        
        if not self.webhook_url:
            return True  # No webhook configured is valid
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.webhook_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'session_id' in data:
                            self.logger.log_info("Webhook validation successful")
                            return True
                        else:
                            self.logger.log_error("Webhook validation failed: missing session_id field")
                            return False
                    else:
                        self.logger.log_error(f"Webhook validation failed: status {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.log_error("Webhook validation failed", exception=e)
            return False


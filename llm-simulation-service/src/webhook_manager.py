"""
Webhook integration for session initialization
"""
import aiohttp
import uuid
import json
from typing import Optional, Dict, Any
from src.config import Config
from src.logging_utils import get_logger

class WebhookManager:
    """Manages webhook interactions for session initialization"""
    
    def __init__(self):
        self.logger = get_logger()
        self.webhook_url = Config.WEBHOOK_URL
    
    async def initialize_session(self) -> str:
        """Initialize a new session via webhook or generate UUID"""
        
        if not self.webhook_url:
            # If no webhook URL configured, generate a UUID
            session_id = str(uuid.uuid4())
            self.logger.log_info(f"Generated session ID (no webhook): {session_id}")
            return session_id
        
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


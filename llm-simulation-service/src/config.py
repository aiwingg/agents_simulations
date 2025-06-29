"""
Configuration management for LLM Simulation Service
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the LLM Simulation Service"""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Conversation Configuration
    MAX_TURNS: int = int(os.getenv('MAX_TURNS', '30'))
    TIMEOUT_SEC: int = int(os.getenv('TIMEOUT_SEC', '90'))
    CONCURRENCY: int = int(os.getenv('CONCURRENCY', '4'))
    USE_TOOLS: bool = os.getenv('USE_TOOLS', 'True').lower() == 'true'
    
    # AutoGen MAS Configuration - Internal message limit for agent conversations
    _MAX_INTERNAL_MESSAGES_ENV = os.getenv('MAX_INTERNAL_MESSAGES')
    if _MAX_INTERNAL_MESSAGES_ENV is not None:
        MAX_INTERNAL_MESSAGES: int = int(_MAX_INTERNAL_MESSAGES_ENV)
    else:
        MAX_INTERNAL_MESSAGES: int = 10
        # Note: Warning will be logged when first accessed via get_max_internal_messages()
    
    # Webhook Configuration
    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')
    
    # File Paths
    PROMPTS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')
    SCENARIOS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scenarios')
    LOGS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    RESULTS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
    
    # Flask Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return True
    
    @classmethod
    def get_prompt_path(cls, prompt_name: str) -> str:
        """Get full path to a prompt file"""
        return os.path.join(cls.PROMPTS_DIR, f"{prompt_name}.txt")
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist"""
        for directory in [cls.LOGS_DIR, cls.RESULTS_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod 
    def get_max_internal_messages(cls) -> int:
        """Get MAX_INTERNAL_MESSAGES with warning if using default value"""
        if cls._MAX_INTERNAL_MESSAGES_ENV is None:
            # Import here to avoid circular imports
            from src.logging_utils import get_logger
            logger = get_logger()
            logger.log_warning(
                f"MAX_INTERNAL_MESSAGES environment variable not set, using default value: {cls.MAX_INTERNAL_MESSAGES}. "
                "Set MAX_INTERNAL_MESSAGES=N to configure internal agent message limit.",
                extra_data={'default_value': cls.MAX_INTERNAL_MESSAGES}
            )
        return cls.MAX_INTERNAL_MESSAGES


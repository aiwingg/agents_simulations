"""
Logging infrastructure for LLM Simulation Service
"""
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from src.config import Config

class SimulationLogger:
    """Custom logger for simulation service"""
    
    def __init__(self, batch_id: Optional[str] = None):
        self.batch_id = batch_id
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        Config.ensure_directories()
        
        # Main application logger
        self.app_logger = logging.getLogger('simulation_app')
        self.app_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger('simulation_error')
        self.error_logger.setLevel(logging.ERROR)
        
        # Token usage logger
        self.token_logger = logging.getLogger('simulation_tokens')
        self.token_logger.setLevel(logging.INFO)
        
        # Conversation logger (detailed JSON logs)
        self.conversation_logger = logging.getLogger('simulation_conversations')
        self.conversation_logger.setLevel(logging.INFO)
        
        # Setup file handlers
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_suffix = f"_{self.batch_id}" if self.batch_id else ""
        
        # App log handler
        app_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f'app_{timestamp}{batch_suffix}.log')
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.app_logger.addHandler(app_handler)
        
        # Error log handler
        error_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f'error_{timestamp}{batch_suffix}.log')
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
        
        # Token log handler
        token_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f'tokens_{timestamp}{batch_suffix}.log')
        )
        token_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        self.token_logger.addHandler(token_handler)
        
        # Conversation log handler (JSON format)
        conversation_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f'conversations_{timestamp}{batch_suffix}.jsonl')
        )
        conversation_handler.setFormatter(logging.Formatter('%(message)s'))
        self.conversation_logger.addHandler(conversation_handler)
    
    def log_info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message"""
        if extra_data:
            message = f"{message} - {json.dumps(extra_data)}"
        self.app_logger.info(message)
    
    def log_error(self, message: str, exception: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None):
        """Log error message"""
        if extra_data:
            message = f"{message} - {json.dumps(extra_data)}"
        if exception:
            self.error_logger.error(message, exc_info=exception)
        else:
            self.error_logger.error(message)
    
    def log_token_usage(self, session_id: str, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost_estimate: float = 0.0):
        """Log token usage for cost tracking"""
        token_data = {
            'session_id': session_id,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'cost_estimate': cost_estimate,
            'timestamp': datetime.now().isoformat()
        }
        self.token_logger.info(json.dumps(token_data))
    
    def log_conversation_turn(self, session_id: str, turn_number: int, role: str, content: str, tool_calls: Optional[list] = None, tool_results: Optional[list] = None):
        """Log detailed conversation turn"""
        turn_data = {
            'session_id': session_id,
            'turn_number': turn_number,
            'role': role,
            'content': content,
            'tool_calls': tool_calls,
            'tool_results': tool_results,
            'timestamp': datetime.now().isoformat()
        }
        self.conversation_logger.info(json.dumps(turn_data))
    
    def log_conversation_complete(self, session_id: str, total_turns: int, final_score: Optional[int] = None, evaluator_comment: Optional[str] = None, status: str = 'completed'):
        """Log conversation completion"""
        completion_data = {
            'session_id': session_id,
            'total_turns': total_turns,
            'final_score': final_score,
            'evaluator_comment': evaluator_comment,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'event_type': 'conversation_complete'
        }
        self.conversation_logger.info(json.dumps(completion_data))

# Global logger instance
_global_logger: Optional[SimulationLogger] = None

def get_logger(batch_id: Optional[str] = None) -> SimulationLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None or (batch_id and _global_logger.batch_id != batch_id):
        _global_logger = SimulationLogger(batch_id)
    return _global_logger


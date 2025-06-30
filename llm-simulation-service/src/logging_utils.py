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
        self.app_logger = logging.getLogger("simulation_app")
        self.app_logger.setLevel(logging.INFO)

        # Error logger
        self.error_logger = logging.getLogger("simulation_error")
        self.error_logger.setLevel(logging.ERROR)

        # Token usage logger
        self.token_logger = logging.getLogger("simulation_tokens")
        self.token_logger.setLevel(logging.INFO)

        # Conversation logger (detailed JSON logs)
        self.conversation_logger = logging.getLogger("simulation_conversations")
        self.conversation_logger.setLevel(logging.INFO)

        # OpenAI API logger (requests and responses)
        self.openai_logger = logging.getLogger("simulation_openai")
        self.openai_logger.setLevel(logging.INFO)

        # Setup file handlers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_suffix = f"_{self.batch_id}" if self.batch_id else ""

        # App log handler with UTF-8 encoding
        app_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f"app_{timestamp}{batch_suffix}.log"), encoding="utf-8"
        )
        app_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.app_logger.addHandler(app_handler)

        # Error log handler with UTF-8 encoding
        error_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f"error_{timestamp}{batch_suffix}.log"), encoding="utf-8"
        )
        error_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.error_logger.addHandler(error_handler)

        # Token log handler with UTF-8 encoding
        token_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f"tokens_{timestamp}{batch_suffix}.log"), encoding="utf-8"
        )
        token_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.token_logger.addHandler(token_handler)

        # Conversation log handler (JSON format) with UTF-8 encoding
        conversation_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f"conversations_{timestamp}{batch_suffix}.jsonl"), encoding="utf-8"
        )
        conversation_handler.setFormatter(logging.Formatter("%(message)s"))
        self.conversation_logger.addHandler(conversation_handler)

        # OpenAI API log handler (JSON format) with UTF-8 encoding
        openai_handler = logging.FileHandler(
            os.path.join(Config.LOGS_DIR, f"openai_api_{timestamp}{batch_suffix}.jsonl"), encoding="utf-8"
        )
        openai_handler.setFormatter(logging.Formatter("%(message)s"))
        self.openai_logger.addHandler(openai_handler)

    def log_info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message"""
        if extra_data:
            message = f"{message} - {json.dumps(extra_data, ensure_ascii=False)}"
        self.app_logger.info(message)

    def log_warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        if extra_data:
            message = f"{message} - {json.dumps(extra_data, ensure_ascii=False)}"
        self.app_logger.warning(message)

    def log_error(
        self, message: str, exception: Optional[Exception] = None, extra_data: Optional[Dict[str, Any]] = None
    ):
        """Log error message"""
        if extra_data:
            message = f"{message} - {json.dumps(extra_data, ensure_ascii=False)}"
        if exception:
            self.error_logger.error(message, exc_info=exception)
        else:
            self.error_logger.error(message)

    def log_token_usage(
        self,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_estimate: float = 0.0,
    ):
        """Log token usage for cost tracking"""
        token_data = {
            "session_id": session_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_estimate": cost_estimate,
            "timestamp": datetime.now().isoformat(),
        }
        self.token_logger.info(json.dumps(token_data, ensure_ascii=False))

    def log_conversation_turn(
        self,
        session_id: str,
        turn_number: int,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None,
    ):
        """Log detailed conversation turn"""
        turn_data = {
            "session_id": session_id,
            "turn_number": turn_number,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "timestamp": datetime.now().isoformat(),
        }
        self.conversation_logger.info(json.dumps(turn_data, ensure_ascii=False))

    def log_conversation_complete(
        self,
        session_id: str,
        total_turns: int,
        final_score: Optional[int] = None,
        evaluator_comment: Optional[str] = None,
        status: str = "completed",
    ):
        """Log conversation completion"""
        completion_data = {
            "session_id": session_id,
            "total_turns": total_turns,
            "final_score": final_score,
            "evaluator_comment": evaluator_comment,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "event_type": "conversation_complete",
        }
        self.conversation_logger.info(json.dumps(completion_data, ensure_ascii=False))

    def log_openai_request(
        self,
        session_id: str,
        request_id: str,
        model: str,
        messages: list,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None,
    ):
        """Log OpenAI API request"""
        request_data = {
            "event_type": "openai_request",
            "request_id": request_id,
            "session_id": session_id,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
            "tools": tools,
            "response_format": response_format,
            "timestamp": datetime.now().isoformat(),
        }
        self.openai_logger.info(json.dumps(request_data, ensure_ascii=False))

    def log_openai_response(
        self,
        session_id: str,
        request_id: str,
        response_content: Any,
        usage: dict,
        cost_estimate: float,
        duration_ms: float,
        attempt: int = 1,
        error: Optional[str] = None,
    ):
        """Log OpenAI API response"""
        # Handle different response types
        if hasattr(response_content, "content"):
            content = response_content.content
            tool_calls = getattr(response_content, "tool_calls", None)
            if tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ]
        else:
            content = str(response_content) if response_content else None
            tool_calls = None

        response_data = {
            "event_type": "openai_response",
            "request_id": request_id,
            "session_id": session_id,
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage,
            "cost_estimate": cost_estimate,
            "duration_ms": duration_ms,
            "attempt": attempt,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self.openai_logger.info(json.dumps(response_data, ensure_ascii=False))


# Global logger instance
_global_logger: Optional[SimulationLogger] = None


def get_logger(batch_id: Optional[str] = None) -> SimulationLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None or (batch_id and _global_logger.batch_id != batch_id):
        _global_logger = SimulationLogger(batch_id)
    return _global_logger

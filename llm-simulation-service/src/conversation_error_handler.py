"""ConversationErrorHandler - Service Layer
Centralized error formatting utilities."""

from datetime import datetime
from typing import Dict, Any


class ConversationErrorHandler:
    """Provides helpers to build consistent error responses."""

    @staticmethod
    def handle_api_blocked_error(session_id: str, scenario: str, start_time: float, end_time: float, turn_count: int, **_: Any) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "scenario": scenario,
            "status": "failed_api_blocked",
            "error": "OpenAI API blocked due to geographic restrictions",
            "error_type": "APIBlockedError",
            "total_turns": turn_count,
            "duration_seconds": end_time - start_time,
            "conversation_history": [],
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "graceful_degradation": True,
            "partial_completion": turn_count > 0,
            "tools_used": True,
        }

    @staticmethod
    def handle_timeout_error(session_id: str, scenario: str, start_time: float, end_time: float, turn_count: int, timeout_sec: int, **_: Any) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "scenario": scenario,
            "status": "timeout",
            "error": f"Conversation timeout after {timeout_sec} seconds",
            "error_type": "TimeoutError",
            "total_turns": turn_count,
            "duration_seconds": end_time - start_time,
            "conversation_history": [],
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "tools_used": True,
        }

    @staticmethod
    def handle_general_error(session_id: str, scenario: str, start_time: float, end_time: float, turn_count: int, error: Exception, error_context: Dict[str, Any] | None = None, **_: Any) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "scenario": scenario,
            "status": "failed",
            "error": str(error),
            "error_type": type(error).__name__,
            "total_turns": turn_count,
            "duration_seconds": end_time - start_time,
            "conversation_history": [],
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "tools_used": True,
            **({"error_context": error_context} if error_context else {}),
        }

    @staticmethod
    def handle_error_by_type(error: Exception, **kwargs: Any) -> Dict[str, Any]:
        msg = str(error).lower()
        if any(term in msg for term in ["geographic restriction", "unsupported_country_region_territory", "blocked due to geographic"]):
            return ConversationErrorHandler.handle_api_blocked_error(**kwargs)
        if isinstance(error, TimeoutError):
            return ConversationErrorHandler.handle_timeout_error(**kwargs)
        return ConversationErrorHandler.handle_general_error(error=error, **kwargs)

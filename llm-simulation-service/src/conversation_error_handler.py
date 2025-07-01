"""Centralized error handling for conversation engine."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict
import asyncio

from src.conversation_context import ConversationContext
from src.conversation_adapter import ConversationAdapter
from src.logging_utils import SimulationLogger


class ConversationErrorHandler:
    """Handle errors for conversation execution."""

    def __init__(self, logger: SimulationLogger):
        self.logger = logger

    def handle_error_by_type(
        self, error: Exception, context: ConversationContext, scenario_name: str, spec_name: str
    ) -> Dict[str, Any]:
        """Route error to the appropriate handler based on type and message."""
        if isinstance(error, asyncio.TimeoutError):
            return self.handle_timeout_error(context, scenario_name, context.timeout_sec)

        msg = str(error).lower()
        if any(term in msg for term in ["geographic restriction", "unsupported_country_region_territory", "blocked due to geographic"]):
            return self.handle_api_blocked_error(error, context, scenario_name)

        return self.handle_general_error(error, context, scenario_name, spec_name)

    def handle_api_blocked_error(
        self, error: Exception, context: ConversationContext, scenario_name: str
    ) -> Dict[str, Any]:
        """Handle geographic restriction / API blocked errors."""
        self.logger.log_error(
            f"OpenAI API blocked in AutoGen engine - attempting graceful degradation: {str(error)}",
            exception=error,
            extra_data={
                "session_id": context.session_id,
                "scenario_name": scenario_name,
                "completed_turns": context.turn_count,
                "error_type": type(error).__name__,
            },
        )
        result = self._create_base_error_result(
            context,
            scenario_name,
            "failed_api_blocked",
            "OpenAI API blocked due to geographic restrictions",
            "APIBlockedError",
        )
        result.update({
            "conversation_history": [],
            "tools_used": True,
            "graceful_degradation": True,
            "partial_completion": context.turn_count > 0,
        })
        return result

    def handle_timeout_error(
        self, context: ConversationContext, scenario_name: str, timeout_sec: int
    ) -> Dict[str, Any]:
        """Handle overall conversation timeout errors."""
        self.logger.log_error(
            f"AutoGen conversation timeout after {timeout_sec} seconds",
            extra_data={
                "session_id": context.session_id,
                "timeout_sec": timeout_sec,
                "completed_turns": context.turn_count,
                "scenario_name": scenario_name,
            },
        )
        history = ConversationAdapter.extract_conversation_history(context.all_messages)
        result = self._create_base_error_result(
            context,
            scenario_name,
            "timeout",
            f"Conversation timeout after {timeout_sec} seconds",
            "TimeoutError",
        )
        result.update({"conversation_history": history, "tools_used": True})
        return result

    def handle_general_error(
        self, error: Exception, context: ConversationContext, scenario_name: str, spec_name: str
    ) -> Dict[str, Any]:
        """Handle any unexpected errors."""
        error_context = {
            "session_id": context.session_id,
            "scenario_name": scenario_name,
            "duration_so_far": time.time() - context.start_time,
            "max_turns": context.max_turns,
            "timeout_sec": context.timeout_sec,
            "completed_turns": context.turn_count,
            "error_type": type(error).__name__,
            "spec_name": spec_name,
        }
        self.logger.log_error(
            f"AutoGen conversation with tools failed: {str(error)}",
            exception=error,
            extra_data=error_context,
        )
        result = self._create_base_error_result(
            context,
            scenario_name,
            "failed",
            str(error),
            type(error).__name__,
        )
        result.update({"tools_used": True, "conversation_history": [], "error_context": error_context})
        return result

    def _create_base_error_result(
        self,
        context: ConversationContext,
        scenario_name: str,
        status: str,
        error_msg: str,
        error_type: str,
    ) -> Dict[str, Any]:
        """Create the base error result structure."""
        end_time = time.time()
        duration = end_time - context.start_time
        return {
            "session_id": context.session_id,
            "scenario": scenario_name,
            "status": status,
            "error": error_msg,
            "error_type": error_type,
            "total_turns": context.turn_count,
            "duration_seconds": duration,
            "start_time": datetime.fromtimestamp(context.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }

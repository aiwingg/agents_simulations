"""Message parsing utilities for ConversationAdapter."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from autogen_agentchat.messages import (
    BaseChatMessage,
    BaseAgentEvent,
    HandoffMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
)
from autogen_core._types import FunctionCall
from autogen_core.models import FunctionExecutionResult

from src.logging_utils import get_logger
from src.dtos.parsed_message import ParsedMessage


class AutogenMessageParser:
    """Parse AutoGen messages and extract tool information."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def parse_message(self, message: BaseChatMessage | BaseAgentEvent) -> ParsedMessage:
        """Parse a single AutoGen message."""
        parsed = ParsedMessage()
        parsed.timestamp = datetime.now().isoformat()
        parsed.should_skip = self._should_skip_message(message)
        parsed.speaker = self._extract_speaker(message)
        parsed.content = self._extract_content(message)
        parsed.is_tool_event = isinstance(message, (ToolCallRequestEvent, ToolCallExecutionEvent))
        if parsed.is_tool_event:
            parsed.tool_calls = self._extract_tool_calls(message)
            parsed.tool_results = self._extract_tool_results(message)
        return parsed

    @staticmethod
    def _should_skip_message(message: BaseChatMessage | BaseAgentEvent) -> bool:
        return (
            hasattr(message, "source")
            and message.source == "system"
        ) or isinstance(message, ToolCallSummaryMessage)

    @staticmethod
    def _extract_speaker(message: BaseChatMessage | BaseAgentEvent) -> str:
        if hasattr(message, "source"):
            source = message.source
            if source in {"client", "user"}:
                return "client"
            if source in {"tool", "tools"}:
                return "agent"
            if source and source != "system":
                return f"agent_{source}"
        return "agent"

    @staticmethod
    def _extract_content(message: BaseChatMessage | BaseAgentEvent) -> str:
        if isinstance(message, TextMessage):
            return message.content or ""
        if isinstance(message, ToolCallRequestEvent):
            return f"[TOOL CALL REQUEST: {len(message.content)} tools]"
        if isinstance(message, ToolCallExecutionEvent):
            return "[TOOL EXECUTION]"
        if isinstance(message, HandoffMessage):
            target = getattr(message, "target", "unknown")
            return f"[HANDOFF TO: {target}]"
        return getattr(message, "content", "") or ""

    @staticmethod
    def _extract_tool_calls(message: BaseChatMessage | BaseAgentEvent) -> Optional[List[Dict]]:
        if not isinstance(message, ToolCallRequestEvent):
            return None
        calls: List[Dict[str, Any]] = []
        for tool_call in message.content:
            if isinstance(tool_call, FunctionCall):
                calls.append(
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {"name": tool_call.name, "arguments": tool_call.arguments},
                    }
                )
        return calls if calls else None

    @staticmethod
    def _extract_tool_results(message: BaseChatMessage | BaseAgentEvent) -> Optional[List[Dict]]:
        if not isinstance(message, ToolCallExecutionEvent):
            return None
        results: List[Dict[str, Any]] = []
        for execution_result in message.content:
            if isinstance(execution_result, FunctionExecutionResult):
                result_content = execution_result.content
                try:
                    parsed = result_content if not isinstance(result_content, str) else __import__("json").loads(result_content)
                except Exception:
                    parsed = result_content
                results.append({"call_id": execution_result.call_id, "content": parsed})
        return results if results else None

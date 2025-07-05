"""
ConversationAdapter - Service Layer
Converts AutoGen TaskResult and message formats to existing ConversationEngine contract format
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# AutoGen imports
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.base import TaskResult

from src.autogen_message_parser import AutogenMessageParser
from src.speaker_display_name_resolver import SpeakerDisplayNameResolver
from src.tool_flush_state_machine import ToolFlushStateMachine

from src.logging_utils import get_logger


class ConversationAdapter:
    """
    Translator between AutoGen's conversation format and existing ConversationEngine contract.
    Maintains compatibility with existing BatchProcessor and evaluation systems.
    """

    @staticmethod
    def autogen_to_contract_format(
        task_result: TaskResult,
        session_id: str,
        scenario_name: str,
        duration: float,
        start_time: Optional[float] = None,
        prompt_spec: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Converts AutoGen TaskResult to ConversationEngine contract format

        Args:
            task_result: AutoGen TaskResult containing messages and stop reason
            session_id: Session identifier
            scenario_name: Name of the scenario
            duration: Conversation duration in seconds
            start_time: Start timestamp (optional, will generate if not provided)
            prompt_spec: Optional prompt specification used for display names

        Returns:
            Dictionary matching existing ConversationEngine output contract. The
            `conversation_history` field is a list of
            `ConversationHistoryItem` dictionaries defined in
            `docs/contracts/dto/conversation_history_item.md`.
        """
        logger = get_logger()

        try:
            # Calculate timestamps
            current_time = time.time()
            actual_start_time = start_time or (current_time - duration)
            end_time = current_time

            # Extract conversation history from AutoGen messages
            conversation_history = ConversationAdapter.extract_conversation_history(task_result.messages, prompt_spec)

            # Determine status based on stop reason and messages
            status = ConversationAdapter._determine_conversation_status(task_result.stop_reason, conversation_history)

            # Count total turns
            total_turns = len([entry for entry in conversation_history if entry.get("turn")])

            # Check if tools were used
            tools_used = any(entry.get("tool_calls") or entry.get("tool_results") for entry in conversation_history)

            result = {
                "session_id": session_id,
                "scenario": scenario_name,
                "status": status,
                "total_turns": total_turns,
                "duration_seconds": duration,
                "conversation_history": conversation_history,
                "start_time": datetime.fromtimestamp(actual_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "tools_used": tools_used,
            }

            logger.log_info(
                "Converted AutoGen TaskResult to contract format",
                extra_data={
                    "session_id": session_id,
                    "total_turns": total_turns,
                    "status": status,
                    "tools_used": tools_used,
                    "stop_reason": task_result.stop_reason,
                    "messages_count": len(task_result.messages),
                },
            )

            return result

        except Exception as e:
            logger.log_error(
                f"Failed to convert AutoGen TaskResult to contract format: {e}",
                exception=e,
                extra_data={"session_id": session_id},
            )

            # Return error format compatible with existing contract
            return {
                "session_id": session_id,
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "total_turns": 0,
                "duration_seconds": duration,
                "conversation_history": [],
                "start_time": datetime.fromtimestamp(actual_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "tools_used": False,
            }

    @staticmethod
    def extract_conversation_history(
        messages: List[BaseChatMessage | BaseAgentEvent],
        prompt_spec: Optional[Any] = None,
    ) -> List[Dict]:
        """Convert AutoGen messages to the ConversationHistoryItem structure."""
        logger = get_logger()
        parser = AutogenMessageParser()
        resolver = SpeakerDisplayNameResolver(prompt_spec)
        state_machine = ToolFlushStateMachine()
        history: List[Dict[str, Any]] = []
        turn_number = 0

        for message in messages:
            parsed = parser.parse_message(message)
            if parsed.should_skip:
                continue
            parsed.speaker_display = resolver.resolve_display_name(
                parsed.speaker, getattr(message, "source", None)
            )
            if parsed.is_tool_event:
                flush = state_machine.process_tool_event(parsed)
                if flush:
                    turn_number += 1
                    flush["turn"] = turn_number
                    history.append(flush)
                continue

            entry = state_machine.process_text_message(parsed)
            turn_number += 1
            entry["turn"] = turn_number
            history.append(entry)

        orphaned = state_machine.handle_orphaned_tools(turn_number + 1)
        if orphaned:
            history.append(orphaned)

        return history


    @staticmethod
    def _determine_conversation_status(stop_reason: str, conversation_history: List[Dict]) -> str:
        """
        Determine conversation status based on AutoGen stop reason and conversation content

        Args:
            stop_reason: AutoGen TaskResult stop reason
            conversation_history: Extracted conversation history

        Returns:
            Status string matching existing contract format
        """
        # Handle AutoGen stop reasons
        if stop_reason == "max_turns":
            return "completed"
        elif stop_reason == "timeout":
            return "failed"
        elif "handoff" in stop_reason.lower():
            return "completed"
        elif "terminate" in stop_reason.lower():
            return "completed"

        # Check conversation content for end indicators
        if conversation_history:
            last_entry = conversation_history[-1]
            content = last_entry.get("content", "").lower()

            # Check for conversation completion phrases
            if any(phrase in content for phrase in ["завершил звонок", "call ended"]):
                return "completed"

            # Check for tool calls that indicate completion
            if last_entry.get("tool_calls"):
                for tool_call in last_entry["tool_calls"]:
                    if tool_call.get("function", {}).get("name") == "call_transfer":
                        return "completed"

        # Default to completed for normal termination
        return "completed"

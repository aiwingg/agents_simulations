"""
ConversationAdapter - Service Layer
Converts AutoGen TaskResult and message formats to existing ConversationEngine contract format
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# AutoGen imports
from autogen_agentchat.messages import (
    BaseChatMessage,
    BaseAgentEvent,
    TextMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    ToolCallSummaryMessage,
    HandoffMessage,
)
from autogen_agentchat.base import TaskResult

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
            Dictionary matching existing ConversationEngine output contract
        """
        logger = get_logger()

        try:
            # Calculate timestamps
            current_time = time.time()
            actual_start_time = start_time or (current_time - duration)
            end_time = current_time

            # Extract conversation history from AutoGen messages
            conversation_history = ConversationAdapter.extract_conversation_history(
                task_result.messages, prompt_spec
            )

            # Determine status based on stop reason and messages
            status = ConversationAdapter._determine_conversation_status(
                task_result.stop_reason, conversation_history
            )

            # Count total turns
            total_turns = len(
                [entry for entry in conversation_history if entry.get("turn")]
            )

            # Check if tools were used
            tools_used = any(
                entry.get("tool_calls") or entry.get("tool_results")
                for entry in conversation_history
            )

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
        """
        Converts AutoGen messages to conversation_history format with tool_calls/tool_results

        Args:
            messages: List of AutoGen BaseChatMessage instances

        Returns:
            List of conversation history entries in existing contract format
        """
        logger = get_logger()
        conversation_history = []
        turn_number = 0
        display_name_map = {}

        if prompt_spec:
            try:
                agents = getattr(
                    prompt_spec, "agents", getattr(prompt_spec, "agents", {})
                )
                for agent_id, agent_spec in agents.items():
                    if hasattr(agent_spec, "name"):
                        display_name_map[agent_id] = agent_spec.name
                    elif isinstance(agent_spec, dict):
                        display_name_map[agent_id] = agent_spec.get("name", agent_id)
            except Exception as e:
                logger.log_error(f"Failed to build display name map: {e}", exception=e)

        try:
            pending_calls: List[Dict] = []
            pending_results: List[Any] = []
            pending_speaker: Optional[str] = None
            pending_display_name: Optional[str] = None

            for i, message in enumerate(messages):
                # Skip system messages as they're not part of conversation flow
                if hasattr(message, "source") and message.source == "system":
                    continue

                is_tool_event = isinstance(
                    message,
                    (
                        ToolCallRequestEvent,
                        ToolCallExecutionEvent,
                        ToolCallSummaryMessage,
                    ),
                )

                speaker = ConversationAdapter._extract_speaker(message)

                if is_tool_event:
                    tool_calls, tool_results = ConversationAdapter._extract_tools_info(
                        message
                    )
                    if tool_calls:
                        if pending_calls and speaker != pending_speaker:
                            # flush previous pending calls if speaker changed
                            turn_number += 1
                            conversation_history.append(
                                {
                                    "turn": turn_number,
                                    "speaker": pending_speaker or "agent",
                                    "content": "",
                                    "timestamp": datetime.now().isoformat(),
                                    "speaker_display": pending_display_name
                                    or (pending_speaker or "agent")
                                    .replace("agent_", "")
                                    .capitalize(),
                                    "tool_calls": pending_calls,
                                    "tool_results": (
                                        pending_results if pending_results else None
                                    ),
                                }
                            )
                            pending_calls = []
                            pending_results = []
                            pending_speaker = None
                            pending_display_name = None

                    if isinstance(message, ToolCallRequestEvent) or isinstance(
                        message, ToolCallSummaryMessage
                    ):
                        pending_speaker = speaker
                        agent_id = getattr(message, "source", None)
                        if agent_id and agent_id in display_name_map:
                            pending_display_name = display_name_map[agent_id]
                        else:
                            if speaker == "client":
                                pending_display_name = "Client"
                            elif speaker.startswith("agent_"):
                                agent_type = speaker.replace("agent_", "")
                                pending_display_name = (
                                    "Agent"
                                    if agent_type == "agent"
                                    else f"{agent_type.capitalize()} Agent"
                                )
                            else:
                                pending_display_name = (
                                    speaker.capitalize() if speaker else "Unknown"
                                )

                    if tool_calls:
                        pending_calls.extend(tool_calls)
                    if tool_results:
                        for result in tool_results:
                            if result not in pending_results:
                                pending_results.append(result)

                    continue

                # Non tool event -> flush pending info onto this message
                turn_number += 1
                content = ConversationAdapter._extract_content(message)
                history_entry = {
                    "turn": turn_number,
                    "speaker": speaker,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                }

                # Derive display name for speaker
                agent_id = getattr(message, "source", None)
                display_name = None
                if agent_id and agent_id in display_name_map:
                    display_name = display_name_map[agent_id]
                if not display_name:
                    if speaker == "client":
                        display_name = "Client"
                    elif speaker.startswith("agent_"):
                        agent_type = speaker.replace("agent_", "")
                        display_name = (
                            "Agent"
                            if agent_type == "agent"
                            else f"{agent_type.capitalize()} Agent"
                        )
                    else:
                        display_name = speaker.capitalize() if speaker else "Unknown"
                history_entry["speaker_display"] = display_name

                if pending_calls:
                    history_entry["tool_calls"] = pending_calls
                if pending_results:
                    history_entry["tool_results"] = pending_results

                conversation_history.append(history_entry)

                pending_calls = []
                pending_results = []
                pending_speaker = None
                pending_display_name = None

            if pending_calls or pending_results:
                turn_number += 1
                conversation_history.append(
                    {
                        "turn": turn_number,
                        "speaker": pending_speaker or "agent",
                        "content": "",
                        "timestamp": datetime.now().isoformat(),
                        "speaker_display": pending_display_name
                        or (pending_speaker or "agent")
                        .replace("agent_", "")
                        .capitalize(),
                        "tool_calls": pending_calls if pending_calls else None,
                        "tool_results": pending_results if pending_results else None,
                    }
                )

        except Exception as e:
            logger.log_error(
                f"Failed to extract conversation history: {e}", exception=e
            )

        return conversation_history

    @staticmethod
    def _extract_speaker(message: BaseChatMessage | BaseAgentEvent) -> str:
        """
        Extract speaker identifier from AutoGen message

        Args:
            message: AutoGen BaseChatMessage

        Returns:
            Speaker string in contract format ("agent_{name}" or "client")
        """
        if hasattr(message, "source"):
            source = message.source

            # Handle client messages
            if source == "client" or source == "user":
                return "client"

            # Handle tool execution results - use generic 'agent'
            if source == "tool" or source == "tools":
                return "agent"

            # Handle agent messages - preserve agent name
            if source and source != "system":
                return f"agent_{source}"

        # Default fallback
        return "agent"

    @staticmethod
    def _extract_content(message: BaseChatMessage | BaseAgentEvent) -> str:
        """
        Extract text content from AutoGen message

        Args:
            message: AutoGen BaseChatMessage

        Returns:
            String content of the message
        """
        if isinstance(message, TextMessage):
            return message.content or ""
        elif isinstance(message, ToolCallRequestEvent):
            # For tool call request events, return summary
            return f"[TOOL CALL REQUEST: {len(message.content)} tools]"
        elif isinstance(message, ToolCallExecutionEvent):
            # For tool execution events, return summary
            return "[TOOL EXECUTION]"
        elif isinstance(message, ToolCallSummaryMessage):
            # For tool summary messages, return the content
            return getattr(message, "content", "") or ""
        elif isinstance(message, HandoffMessage):
            # For handoff messages, return handoff info
            target = getattr(message, "target", "unknown")
            return f"[HANDOFF TO: {target}]"
        else:
            # Generic content extraction
            return getattr(message, "content", "") or ""

    @staticmethod
    def _extract_tools_info(
        message: BaseChatMessage | BaseAgentEvent,
    ) -> tuple[Optional[List[Dict]], Optional[List[Any]]]:
        """
        Extract tool calls and results from AutoGen message

        Args:
            message: AutoGen BaseChatMessage

        Returns:
            Tuple of (tool_calls, tool_results) or (None, None) if no tools
        """
        tool_calls = None
        tool_results = None

        if isinstance(message, ToolCallRequestEvent):
            # Extract tool calls from ToolCallRequestEvent
            if hasattr(message, "content") and message.content:
                tool_calls = []
                for tool_call in message.content:
                    tool_call_dict = {
                        "id": getattr(tool_call, "id", ""),
                        "type": "function",
                        "function": {
                            "name": getattr(tool_call, "name", ""),
                            "arguments": getattr(tool_call, "arguments", "{}"),
                        },
                    }
                    tool_calls.append(tool_call_dict)

        elif isinstance(message, ToolCallExecutionEvent):
            # Extract tool results from ToolCallExecutionEvent
            if hasattr(message, "content") and message.content:
                tool_results = []
                for execution_result in message.content:
                    # FunctionExecutionResult has a content field
                    result_content = execution_result.content
                    try:
                        # Try to parse as JSON first
                        if isinstance(result_content, str):
                            tool_results.append(json.loads(result_content))
                        else:
                            tool_results.append(result_content)
                    except json.JSONDecodeError:
                        # If not JSON, store as string
                        tool_results.append(result_content)
        elif isinstance(message, ToolCallSummaryMessage):
            # Extract tool results from ToolCallSummaryMessage
            if hasattr(message, "content"):
                try:
                    # Try to parse as JSON first
                    if isinstance(message.content, str):
                        tool_results = [json.loads(message.content)]
                    else:
                        tool_results = [message.content]
                except json.JSONDecodeError:
                    # If not JSON, store as string
                    tool_results = [message.content]

        return tool_calls, tool_results

    @staticmethod
    def _determine_conversation_status(
        stop_reason: str, conversation_history: List[Dict]
    ) -> str:
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

            # Check for call end indicators
            if any(
                phrase in content
                for phrase in ["end_call", "завершил звонок", "call ended"]
            ):
                return "completed"

            # Check for tool calls that indicate completion
            if last_entry.get("tool_calls"):
                for tool_call in last_entry["tool_calls"]:
                    if tool_call.get("function", {}).get("name") == "end_call":
                        return "completed"

        # Default to completed for normal termination
        return "completed"

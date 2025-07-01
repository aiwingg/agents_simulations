"""State machine handling tool call/result flushing."""

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.logging_utils import get_logger
from src.dtos.parsed_message import ParsedMessage


class ToolFlushStateMachine:
    """Match tool events and flush them when a text message arrives."""

    def __init__(self) -> None:
        self.logger = get_logger()
        self.pending: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.pending_speaker: Optional[str] = None
        self.pending_display_name: Optional[str] = None

    def process_tool_event(self, parsed_message: ParsedMessage) -> Optional[Dict]:
        if self.pending and parsed_message.speaker not in {self.pending_speaker, "agent"}:
            return self._create_orphaned_tools_entry()
        if parsed_message.tool_calls:
            for call in parsed_message.tool_calls:
                self.pending[call["id"]] = {"call": call, "result": None}
            self.pending_speaker = parsed_message.speaker
            self.pending_display_name = parsed_message.speaker_display
        if parsed_message.tool_results:
            for result in parsed_message.tool_results:
                cid = result.get("call_id")
                if cid in self.pending:
                    self.pending[cid]["result"] = result["content"]
                else:
                    self.logger.log_warning(
                        "Orphaned tool result", extra_data={"call_id": cid}
                    )
        return None

    def process_text_message(self, parsed_message: ParsedMessage) -> Dict:
        if self.pending:
            parsed_message.tool_calls = [v["call"] for v in self.pending.values()]
            results = [v["result"] for v in self.pending.values() if v["result"] is not None]
            parsed_message.tool_results = results or None
            parsed_message.speaker = self.pending_speaker or parsed_message.speaker
            parsed_message.speaker_display = (
                self.pending_display_name or parsed_message.speaker_display
            )
            self._validate_tool_call_completion()
            self.pending.clear()
            self.pending_speaker = None
            self.pending_display_name = None
        return parsed_message.__dict__

    def handle_orphaned_tools(self, turn_number: int) -> Optional[Dict]:
        if not self.pending:
            return None
        entry = self._create_orphaned_tools_entry()
        entry["turn"] = turn_number
        return entry

    def _validate_tool_call_completion(self) -> None:
        for cid, data in self.pending.items():
            if data["result"] is None:
                self.logger.log_warning(
                    "Missing tool execution result", extra_data={"call_id": cid}
                )

    def _create_orphaned_tools_entry(self) -> Dict:
        self.logger.log_error(
            "Tool events without following text message", extra_data={"calls": list(self.pending.keys())}
        )
        entry = {
            "speaker": "simulation_system",
            "speaker_display": "Simulation System",
            "content": "[ORPHANED TOOL EVENTS]",
            "timestamp": datetime.now().isoformat(),
            "tool_calls": [v["call"] for v in self.pending.values()],
            "tool_results": [v["result"] for v in self.pending.values() if v["result"] is not None] or None,
        }
        self.pending.clear()
        self.pending_speaker = None
        self.pending_display_name = None
        return entry

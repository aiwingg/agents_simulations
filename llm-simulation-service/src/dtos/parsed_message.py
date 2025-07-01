from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ParsedMessage:
    """DTO for parsed AutoGen message matching ConversationHistoryItem structure."""

    turn: Optional[int] = None
    speaker: str = ""
    speaker_display: Optional[str] = None
    content: str = ""
    timestamp: str = ""
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Any]] = None
    is_tool_event: bool = False
    should_skip: bool = False

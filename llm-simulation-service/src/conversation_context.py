from dataclasses import dataclass, field
from typing import List
from autogen_agentchat.messages import BaseChatMessage

@dataclass
class ConversationContext:
    """Encapsulates conversation state and configuration."""
    session_id: str
    scenario_name: str
    max_turns: int
    timeout_sec: int
    start_time: float
    turn_count: int = 0
    all_messages: List[BaseChatMessage] = field(default_factory=list)

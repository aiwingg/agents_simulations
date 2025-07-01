from dataclasses import dataclass
from typing import Optional
from autogen_agentchat.messages import BaseChatMessage
from autogen_agentchat.base import TaskResult

@dataclass
class TurnResult:
    """Represents the outcome of a single conversation turn."""
    task_result: TaskResult
    last_message: BaseChatMessage
    should_continue: bool
    termination_reason: Optional[str] = None

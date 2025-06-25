"""AutoGen-based conversation engine"""
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger

class AutoGenConversationEngine:
    """Simplified conversation engine using AutoGen"""

    def __init__(self, openai_wrapper: OpenAIWrapper):
        self.openai = openai_wrapper
        self.logger = get_logger()

    async def _run_autogen(self, messages: List[Dict[str, str]], max_turns: int) -> List[Dict[str, str]]:
        """Placeholder for AutoGen conversation execution"""
        history = []
        for idx, message in enumerate(messages):
            if idx >= max_turns:
                break
            history.append(message)
        return history

    async def run_conversation(
        self,
        scenario: Dict[str, Any],
        max_turns: Optional[int] = None,
        timeout_sec: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run conversation and return history in standard format"""
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC

        session_id = scenario.get("session_id", str(uuid4()))
        scenario_name = scenario.get("name", "unknown")
        messages = scenario.get("messages", [])

        start_time = time.time()
        raw_history = await self._run_autogen(messages, max_turns)

        conversation_history = []
        turn_number = 0
        for msg in raw_history:
            role = msg.get("role", "agent")
            if role not in ("agent", "client"):
                role = {"assistant": "agent", "user": "client"}.get(role, role)
            turn_number += 1
            conversation_history.append(
                {
                    "turn": turn_number,
                    "speaker": role,
                    "content": msg.get("content", ""),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        end_time = time.time()

        return {
            "session_id": session_id,
            "scenario": scenario_name,
            "status": "completed",
            "total_turns": turn_number,
            "duration_seconds": end_time - start_time,
            "conversation_history": conversation_history,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
        }

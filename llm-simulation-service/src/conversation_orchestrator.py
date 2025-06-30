"""ConversationOrchestrator - Service Layer
Runs conversation loops using AutoGen Swarm."""

import asyncio
import time
from typing import List
from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import HandoffMessage, TextMessage, BaseChatMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from src.logging_utils import get_logger


class TurnResult(TaskResult):
    """Lightweight alias to expose TaskResult in orchestrator."""


class ConversationOrchestrator:
    """Manage conversation loop and turn handling."""

    def __init__(self):
        self.logger = get_logger()

    async def run_conversation_loop(
        self,
        swarm: Swarm,
        user_agent: AssistantAgent,
        initial_message: str,
        max_turns: int,
        timeout_sec: int,
    ) -> List[BaseChatMessage]:
        """Execute conversation between swarm and simulated user."""
        start = time.time()
        turn_count = 0
        messages: List[BaseChatMessage] = []
        current_user_message = initial_message
        last_agent = "agent"

        while self._should_continue_conversation(turn_count, ""):
            if time.time() - start > timeout_sec:
                raise asyncio.TimeoutError(f"Conversation timeout after {timeout_sec} seconds")

            turn_count += 1
            task = HandoffMessage(source="client", target=last_agent, content=current_user_message)
            result = await swarm.run(task=task)
            messages.extend(result.messages)
            last_msg = result.messages[-1]
            if not isinstance(last_msg, TextMessage):
                raise ValueError(f"MAS terminated with non-text message ({type(last_msg).__name__})")

            last_agent = last_msg.source
            current_user_message = await self._process_user_response(user_agent, last_msg)

            if not self._should_continue_conversation(turn_count, result.stop_reason):
                break

        return messages

    async def _process_user_response(self, user_agent: AssistantAgent, agent_message: TextMessage) -> str:
        """Generate user response using the client simulation agent."""
        task = HandoffMessage(source="client", target=user_agent.name, content=agent_message.content)
        user_result = await user_agent.aask(task)
        return user_result.content if isinstance(user_result, TextMessage) else ""

    def _should_continue_conversation(self, turn_count: int, stop_reason: str) -> bool:
        if stop_reason and any(term in stop_reason.lower() for term in ["terminate", "end", "completed"]):
            return False
        return turn_count < 50

"""Conversation loop orchestration service."""
from typing import Optional
import asyncio
import time

from autogen_agentchat.teams import Swarm
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage

from src.conversation_turn_manager import ConversationTurnManager
from src.logging_utils import SimulationLogger
from src.conversation_context import ConversationContext
from src.turn_result import TurnResult


class ConversationLoopOrchestrator:
    """Manage overall conversation flow and timeouts."""

    def __init__(self, turn_manager: ConversationTurnManager, logger: SimulationLogger) -> None:
        self.turn_manager = turn_manager
        self.logger = logger

    async def run_conversation_loop(
        self,
        swarm: Swarm,
        user_agent: AssistantAgent,
        initial_message: str,
        context: ConversationContext,
    ) -> ConversationContext:
        current = initial_message
        last_agent: Optional[str] = "agent"
        while context.turn_count < context.max_turns:
            self._check_conversation_timeout(context)
            turn = await self.turn_manager.execute_turn(swarm, current, last_agent, context)
            if not self._should_continue_conversation(context, turn):
                break
            current = await self.turn_manager.generate_user_response(user_agent, turn.last_message)
            context.all_messages.append(TextMessage(content=current, source="client"))
            self.logger.log_info(
                "User simulation agent generated response",
                extra_data={"session_id": context.session_id, "user_response": current[:100]},
            )
            last_agent = turn.last_message.source
            self._update_conversation_context(context, turn)
        return context

    def _check_conversation_timeout(self, context: ConversationContext) -> None:
        if time.time() - context.start_time > context.timeout_sec:
            raise asyncio.TimeoutError(
                f"Conversation timeout after {context.timeout_sec} seconds"
            )

    def _should_continue_conversation(self, context: ConversationContext, turn_result: TurnResult) -> bool:
        return turn_result.should_continue and context.turn_count < context.max_turns

    def _update_conversation_context(self, context: ConversationContext, turn_result: TurnResult) -> None:
        # Placeholder for future context updates
        del turn_result
        del context
        return

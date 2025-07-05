"""Conversation loop orchestration service."""
from typing import Optional
import asyncio
import time

from autogen_agentchat.teams import Swarm
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, ToolCallRequestEvent, ToolCallExecutionEvent

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
            user_task_result = await self.turn_manager.generate_user_response(user_agent, turn.last_message)
            
            # Handle user response and determine if conversation should continue
            should_continue, next_content = self._handle_user_response(user_task_result, context)
            if not should_continue:
                break
                
            current = next_content
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

    def _handle_user_response(self, user_task_result, context: ConversationContext) -> tuple[bool, Optional[str]]:
        """
        Handle user agent response and determine if conversation should continue.
        
        Args:
            user_task_result: TaskResult from user agent
            context: Current conversation context
            
        Returns:
            Tuple of (should_continue, next_message_content)
            - should_continue: False if conversation should terminate, True to continue
            - next_message_content: Content for next turn (None if terminating)
        """
        # Similar to autogen_mas_factory.py, user agent can terminate with either tool call or TextMessage
        if not user_task_result.messages:
            return False, None
            
        last_user_message = user_task_result.messages[-1]
        
        # Always add user agent messages to conversation history
        context.all_messages.extend(user_task_result.messages)
        
        # Check if user agent made tool calls (indicating intent to end simulation)
        if isinstance(last_user_message, (ToolCallRequestEvent, ToolCallExecutionEvent)):
            self.logger.log_info(
                "User agent made tool calls, terminating conversation",
                extra_data={"session_id": context.session_id},
            )
            return False, None
        
        # If it's a TextMessage, extract content and continue
        if isinstance(last_user_message, TextMessage):
            current = last_user_message.content
            self.logger.log_info(
                "User simulation agent generated response",
                extra_data={"session_id": context.session_id, "user_response": current[:100]},
            )
            return True, current
        
        # Unexpected message type, log and terminate
        self.logger.log_warning(
            f"Unexpected message type from user agent: {type(last_user_message)}",
            extra_data={"session_id": context.session_id},
        )
        return False, None

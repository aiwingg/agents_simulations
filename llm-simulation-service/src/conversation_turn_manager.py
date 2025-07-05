"""Service for managing individual conversation turns."""
from typing import Optional, Tuple

from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import HandoffMessage, TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from src.logging_utils import SimulationLogger
from src.conversation_context import ConversationContext
from src.turn_result import TurnResult


class ConversationTurnManager:
    """Handle execution of a single conversation turn."""

    def __init__(self, logger: SimulationLogger) -> None:
        self.logger = logger

    async def execute_turn(
        self,
        swarm: Swarm,
        user_message: str,
        target_agent: str,
        context: ConversationContext,
    ) -> TurnResult:
        """Run a conversation turn and determine continuation."""
        context.turn_count += 1
        self.logger.log_info(
            f"Turn {context.turn_count}: User -> {target_agent}",
            extra_data={"session_id": context.session_id, "user_message": user_message[:100]},
        )

        task_result = await swarm.run(
            task=HandoffMessage(source="client", target=target_agent, content=user_message)
        )
        context.all_messages.extend(task_result.messages)

        last_message = self._validate_agent_response(task_result, context)

        self.logger.log_info(
            f"Turn {context.turn_count}: {last_message.source} -> User",
            extra_data={"session_id": context.session_id, "agent_response": last_message.content[:100]},
        )

        should_continue, reason = self._determine_continuation(task_result, context)

        return TurnResult(
            task_result=task_result,
            last_message=last_message,
            should_continue=should_continue,
            termination_reason=reason,
        )

    async def generate_user_response(
        self, user_agent: AssistantAgent, agent_message: TextMessage
    ) -> str:
        """Generate the next user message via user simulation agent."""
        response = await user_agent.on_messages([agent_message], None)
        return response.chat_message.content

    def _validate_agent_response(
        self, task_result: TaskResult, context: ConversationContext
    ) -> TextMessage:
        """Ensure the MAS returned a TextMessage."""
        last_message = task_result.messages[-1]
        if not isinstance(last_message, TextMessage):
            error = TypeError(
                f"MAS terminated with non-text message ({type(last_message).__name__})"
            )
            error.task_result = task_result
            raise error
        return last_message

    def _determine_continuation(
        self, task_result: TaskResult, context: ConversationContext
    ) -> Tuple[bool, Optional[str]]:
        """Decide whether the conversation should continue."""
        if task_result.stop_reason and any(
            term in task_result.stop_reason.lower()
            for term in ["terminate", "end", "finished", "completed"]
        ):
            self.logger.log_info(
                f"Conversation ended naturally: {task_result.stop_reason}",
                extra_data={"session_id": context.session_id},
            )
            return False, task_result.stop_reason

        if context.turn_count >= context.max_turns:
            self.logger.log_info(
                f"Reached max_turns ({context.max_turns})",
                extra_data={"session_id": context.session_id},
            )
            return False, "max_turns"

        return True, None

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult

from src.conversation_loop_orchestrator import ConversationLoopOrchestrator
from src.conversation_turn_manager import ConversationTurnManager
from src.conversation_context import ConversationContext
from src.logging_utils import SimulationLogger
from src.turn_result import TurnResult


@pytest.fixture
def context():
    return ConversationContext(
        session_id="sid",
        scenario_name="scenario",
        max_turns=3,
        timeout_sec=5,
        start_time=time.time(),
    )

@pytest.fixture
def logger():
    return Mock(spec=SimulationLogger)

@pytest.fixture
def turn_manager(logger):
    mgr = ConversationTurnManager(logger)
    mgr.execute_turn = AsyncMock()
    mgr.generate_user_response = AsyncMock(return_value="pong")
    return mgr


class TestConversationLoopOrchestrator:
    @pytest.mark.asyncio
    async def test_run_conversation_loop_success(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        msg = TextMessage(content="hi", source="agent")
        async def exec_turn(*args, **kwargs):
            context.turn_count += 1
            if context.turn_count == 1:
                return TurnResult(TaskResult(messages=[msg], stop_reason=None), msg, True, None)
            return TurnResult(TaskResult(messages=[msg], stop_reason="completed"), msg, False, "completed")

        turn_manager.execute_turn.side_effect = exec_turn
        await orchestrator.run_conversation_loop(Mock(), Mock(), "start", context)
        assert context.turn_count == 2
        turn_manager.generate_user_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_conversation_loop_timeout(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        context.timeout_sec = 0
        with pytest.raises(asyncio.TimeoutError):
            await orchestrator.run_conversation_loop(Mock(), Mock(), "start", context)

    @pytest.mark.asyncio
    async def test_run_conversation_loop_max_turns(self, logger):
        turn_manager = ConversationTurnManager(logger)
        async def exec_turn(*args, **kwargs):
            ctx = args[-1]
            ctx.turn_count += 1
            return TurnResult(TaskResult(messages=[TextMessage(content="hi", source="agent")], stop_reason=None), TextMessage(content="hi", source="agent"), True, None)

        turn_manager.execute_turn = AsyncMock(side_effect=exec_turn)
        turn_manager.generate_user_response = AsyncMock(return_value="next")
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        ctx = ConversationContext("sid", "scenario", 2, 5, time.time())
        await orchestrator.run_conversation_loop(Mock(), Mock(), "start", ctx)
        assert ctx.turn_count == 2

    @pytest.mark.asyncio
    async def test_run_conversation_loop_natural_termination(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        msg = TextMessage(content="hi", source="agent")
        async def exec_turn(*args, **kwargs):
            context.turn_count += 1
            return TurnResult(TaskResult(messages=[msg], stop_reason="done"), msg, False, "done")

        turn_manager.execute_turn = AsyncMock(side_effect=exec_turn)
        await orchestrator.run_conversation_loop(Mock(), Mock(), "start", context)
        assert context.turn_count == 1

    def test_check_conversation_timeout_within_limit(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        orchestrator._check_conversation_timeout(context)

    def test_check_conversation_timeout_exceeded(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        context.timeout_sec = -1
        with pytest.raises(asyncio.TimeoutError):
            orchestrator._check_conversation_timeout(context)

    def test_should_continue_conversation_yes(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        result = TurnResult(TaskResult(messages=[], stop_reason=None), TextMessage(content="hi", source="agent"), True, None)
        assert orchestrator._should_continue_conversation(context, result)

    def test_should_continue_conversation_no(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        context.max_turns = 0
        result = TurnResult(TaskResult(messages=[], stop_reason=None), TextMessage(content="hi", source="agent"), True, None)
        assert not orchestrator._should_continue_conversation(context, result)

    def test_update_conversation_context(self, context, turn_manager, logger):
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        result = TurnResult(TaskResult(messages=[], stop_reason=None), TextMessage(content="hi", source="agent"), True, None)
        orchestrator._update_conversation_context(context, result)

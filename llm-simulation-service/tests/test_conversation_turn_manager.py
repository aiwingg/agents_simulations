import pytest
from unittest.mock import AsyncMock, Mock

from autogen_agentchat.messages import TextMessage, HandoffMessage
from autogen_agentchat.base import TaskResult

from src.conversation_turn_manager import ConversationTurnManager
from src.conversation_context import ConversationContext
from src.turn_result import TurnResult
from src.logging_utils import SimulationLogger


@pytest.fixture
def context():
    return ConversationContext(
        session_id="sid",
        scenario_name="sc",
        max_turns=3,
        timeout_sec=10,
        start_time=0.0,
    )


@pytest.fixture
def logger():
    return Mock(spec=SimulationLogger)


class TestConversationTurnManager:
    @pytest.mark.asyncio
    async def test_execute_turn_success(self, context, logger):
        manager = ConversationTurnManager(logger)
        swarm = Mock()
        msg = TextMessage(content="hi", source="agent")
        swarm.run = AsyncMock(return_value=TaskResult(messages=[msg], stop_reason=None))

        result = await manager.execute_turn(swarm, "hello", "agent", context)

        assert isinstance(result, TurnResult)
        assert context.turn_count == 1
        assert context.all_messages == [msg]
        assert result.should_continue is True
        assert result.termination_reason is None

    @pytest.mark.asyncio
    async def test_execute_turn_non_text_message(self, context, logger):
        manager = ConversationTurnManager(logger)
        swarm = Mock()
        non_text = HandoffMessage(content="handoff", source="agent", target="user")
        swarm.run = AsyncMock(return_value=TaskResult(messages=[non_text], stop_reason=None))

        with pytest.raises(TypeError):
            await manager.execute_turn(swarm, "hello", "agent", context)

    @pytest.mark.asyncio
    async def test_generate_user_response_success(self, logger):
        manager = ConversationTurnManager(logger)
        agent = Mock()
        expected_task_result = TaskResult(messages=[TextMessage(content="pong", source="user")], stop_reason=None)
        agent.run = AsyncMock(return_value=expected_task_result)

        result = await manager.generate_user_response(agent, TextMessage(content="ping", source="agent"))

        assert result == expected_task_result
        agent.run.assert_called_once_with(task="ping")

    def test_validate_agent_response_text_message(self, context, logger):
        manager = ConversationTurnManager(logger)
        msg = TextMessage(content="hi", source="agent")
        task_result = TaskResult(messages=[msg], stop_reason=None)
        assert manager._validate_agent_response(task_result, context) is msg

    def test_validate_agent_response_non_text_message(self, context, logger):
        manager = ConversationTurnManager(logger)
        task_result = TaskResult(messages=[HandoffMessage(content="x", source="a", target="b")], stop_reason=None)
        with pytest.raises(TypeError):
            manager._validate_agent_response(task_result, context)

    def test_determine_continuation_natural_end(self, context, logger):
        manager = ConversationTurnManager(logger)
        context.turn_count = 1
        task_result = TaskResult(messages=[TextMessage(content="hi", source="agent")], stop_reason="finished")
        cont, reason = manager._determine_continuation(task_result, context)
        assert cont is False
        assert reason == "finished"

    def test_determine_continuation_max_turns(self, context, logger):
        manager = ConversationTurnManager(logger)
        context.turn_count = 3
        task_result = TaskResult(messages=[TextMessage(content="hi", source="agent")], stop_reason=None)
        cont, reason = manager._determine_continuation(task_result, context)
        assert cont is False
        assert reason == "max_turns"

    def test_determine_continuation_ongoing(self, context, logger):
        manager = ConversationTurnManager(logger)
        context.turn_count = 1
        task_result = TaskResult(messages=[TextMessage(content="hi", source="agent")], stop_reason=None)
        cont, reason = manager._determine_continuation(task_result, context)
        assert cont is True
        assert reason is None

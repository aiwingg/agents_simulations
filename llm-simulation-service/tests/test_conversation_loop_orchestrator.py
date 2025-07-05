import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from autogen_agentchat.messages import TextMessage, ToolCallRequestEvent
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
    # Mock generate_user_response to return a TaskResult instead of string
    mock_task_result = TaskResult(
        messages=[TextMessage(content="pong", source="user")], 
        stop_reason=None
    )
    mgr.generate_user_response = AsyncMock(return_value=mock_task_result)
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
        mock_task_result = TaskResult(
            messages=[TextMessage(content="next", source="user")], 
            stop_reason=None
        )
        turn_manager.generate_user_response = AsyncMock(return_value=mock_task_result)
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

    @pytest.mark.asyncio
    async def test_run_conversation_loop_user_tool_call_termination(self, context, turn_manager, logger):
        """Test that conversation terminates when user agent makes tool calls."""
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        msg = TextMessage(content="hi", source="agent")
        
        async def exec_turn(*args, **kwargs):
            context.turn_count += 1
            return TurnResult(TaskResult(messages=[msg], stop_reason=None), msg, True, None)

        # Mock user agent response with tool call message
        tool_call_message = ToolCallRequestEvent(content=[], source="user")
        tool_call_task_result = TaskResult(messages=[tool_call_message], stop_reason=None)
        
        turn_manager.execute_turn = AsyncMock(side_effect=exec_turn)
        turn_manager.generate_user_response = AsyncMock(return_value=tool_call_task_result)
        
        await orchestrator.run_conversation_loop(Mock(), Mock(), "start", context)
        
        # Should terminate after first turn due to tool call
        assert context.turn_count == 1
        turn_manager.generate_user_response.assert_called_once()
        
        # Verify that user agent messages are added to conversation history
        assert len(context.all_messages) >= 1  # At least the user tool call message
        # The last message should be the tool call message from user agent
        assert context.all_messages[-1] == tool_call_message

    def test_handle_user_response_with_tool_call(self, turn_manager, logger, context):
        """Test _handle_user_response method with tool call termination."""
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        
        # Create task result with tool call message
        tool_call_message = ToolCallRequestEvent(content=[], source="user")
        task_result = TaskResult(messages=[tool_call_message], stop_reason=None)
        
        should_continue, next_content = orchestrator._handle_user_response(task_result, context)
        
        # Should not continue and have no next content
        assert should_continue == False
        assert next_content is None
        
        # Verify message was added to conversation history
        assert len(context.all_messages) == 1
        assert context.all_messages[0] == tool_call_message

    def test_handle_user_response_with_text_message(self, turn_manager, logger, context):
        """Test _handle_user_response method with text message continuation."""
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        
        # Create task result with text message
        text_message = TextMessage(content="Hello world", source="user")
        task_result = TaskResult(messages=[text_message], stop_reason=None)
        
        should_continue, next_content = orchestrator._handle_user_response(task_result, context)
        
        # Should continue with extracted content
        assert should_continue == True
        assert next_content == "Hello world"
        
        # Verify message was added to conversation history
        assert len(context.all_messages) == 1
        assert context.all_messages[0] == text_message

    def test_handle_user_response_with_empty_messages(self, turn_manager, logger, context):
        """Test _handle_user_response method with empty messages."""
        orchestrator = ConversationLoopOrchestrator(turn_manager, logger)
        
        # Create task result with no messages
        task_result = TaskResult(messages=[], stop_reason=None)
        
        should_continue, next_content = orchestrator._handle_user_response(task_result, context)
        
        # Should not continue
        assert should_continue == False
        assert next_content is None
        
        # No messages should be added to history
        assert len(context.all_messages) == 0

import asyncio
from unittest.mock import Mock

from src.conversation_error_handler import ConversationErrorHandler
from src.conversation_context import ConversationContext
from src.logging_utils import SimulationLogger
from autogen_agentchat.messages import TextMessage


class TestConversationErrorHandler:
    def setup_method(self):
        self.logger = Mock(spec=SimulationLogger)
        self.handler = ConversationErrorHandler(self.logger)
        self.context = ConversationContext(
            session_id="sid",
            scenario_name="sc",
            max_turns=5,
            timeout_sec=10,
            start_time=0.0,
        )

    def test_handle_api_blocked_error(self):
        self.context.turn_count = 1
        err = Exception("geographic restriction detected")
        result = self.handler.handle_api_blocked_error(err, self.context, "scenario")
        assert result["status"] == "failed_api_blocked"
        assert result["error_type"] == "APIBlockedError"
        assert result["graceful_degradation"] is True
        assert result["partial_completion"] is True
        self.logger.log_error.assert_called_once()

    def test_handle_timeout_error(self):
        msg = TextMessage(content="hi", source="agent")
        self.context.all_messages.append(msg)
        self.context.turn_count = 2
        result = self.handler.handle_timeout_error(self.context, "scenario", 15)
        assert result["status"] == "timeout"
        assert result["error_type"] == "TimeoutError"
        assert isinstance(result["conversation_history"], list)
        assert result["tools_used"] is True
        self.logger.log_error.assert_called_once()

    def test_handle_general_error(self):
        err = ValueError("boom")
        result = self.handler.handle_general_error(err, self.context, "scenario", "spec")
        assert result["status"] == "failed"
        assert result["error"] == "boom"
        assert result["error_type"] == "ValueError"
        assert result["tools_used"] is True
        assert "error_context" in result
        self.logger.log_error.assert_called_once()

    def test_handle_error_by_type_api_blocked(self):
        err = Exception("Blocked due to geographic")
        result = self.handler.handle_error_by_type(err, self.context, "scenario", "spec")
        assert result["status"] == "failed_api_blocked"

    def test_handle_error_by_type_timeout(self):
        err = asyncio.TimeoutError()
        result = self.handler.handle_error_by_type(err, self.context, "scenario", "spec")
        assert result["status"] == "timeout"

    def test_handle_error_by_type_general(self):
        err = RuntimeError("oops")
        result = self.handler.handle_error_by_type(err, self.context, "scenario", "spec")
        assert result["status"] == "failed"

    def test_create_base_error_result(self):
        res = self.handler._create_base_error_result(
            self.context, "scenario", "failed", "msg", "Type"
        )
        assert res["status"] == "failed"
        assert res["error"] == "msg"
        assert res["error_type"] == "Type"
        assert res["total_turns"] == 0

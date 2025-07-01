from src.autogen_message_parser import AutogenMessageParser
from autogen_agentchat.messages import TextMessage, ToolCallRequestEvent, ToolCallExecutionEvent, ToolCallSummaryMessage
from autogen_core._types import FunctionCall
from autogen_core.models import FunctionExecutionResult


class TestAutogenMessageParser:
    def setup_method(self):
        self.parser = AutogenMessageParser()

    def test_parse_text_message(self):
        msg = TextMessage(source="agent", content="hi")
        parsed = self.parser.parse_message(msg)
        assert parsed.speaker == "agent_agent"
        assert parsed.content == "hi"
        assert not parsed.is_tool_event

    def test_parse_tool_call_request(self):
        fc = FunctionCall(id="c1", name="do", arguments="{}")
        msg = ToolCallRequestEvent(source="agent", content=[fc])
        parsed = self.parser.parse_message(msg)
        assert parsed.is_tool_event
        assert parsed.tool_calls[0]["id"] == "c1"

    def test_parse_tool_execution_event(self):
        res = FunctionExecutionResult(call_id="c1", name="do", content="{}", is_error=False)
        msg = ToolCallExecutionEvent(source="tool", content=[res])
        parsed = self.parser.parse_message(msg)
        assert parsed.is_tool_event
        assert parsed.tool_results[0]["call_id"] == "c1"

    def test_skip_system_messages(self):
        msg = TextMessage(source="system", content="sys")
        parsed = self.parser.parse_message(msg)
        assert parsed.should_skip

    def test_skip_tool_summary_messages(self):
        msg = ToolCallSummaryMessage(source="agent", content="done")
        parsed = self.parser.parse_message(msg)
        assert parsed.should_skip



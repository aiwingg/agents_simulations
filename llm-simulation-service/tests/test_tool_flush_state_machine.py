from src.tool_flush_state_machine import ToolFlushStateMachine
from src.dtos.parsed_message import ParsedMessage


class TestToolFlushStateMachine:
    def setup_method(self):
        self.machine = ToolFlushStateMachine()

    def test_normal_tool_flow(self):
        call_msg = ParsedMessage(speaker="agent_agent", speaker_display="Agent", is_tool_event=True, tool_calls=[{"id": "c1"}])
        exec_msg = ParsedMessage(speaker="agent_agent", is_tool_event=True, tool_results=[{"call_id": "c1", "content": {"ok": True}}])
        self.machine.process_tool_event(call_msg)
        self.machine.process_tool_event(exec_msg)
        text = ParsedMessage(speaker="agent_agent", content="done")
        entry = self.machine.process_text_message(text)
        assert entry["tool_calls"][0]["id"] == "c1"
        assert entry["tool_results"][0]["ok"] is True

    def test_orphaned_tools_edge_case(self):
        call_msg = ParsedMessage(speaker="agent_agent", is_tool_event=True, tool_calls=[{"id": "c1"}])
        self.machine.process_tool_event(call_msg)
        orphan = self.machine.handle_orphaned_tools(1)
        assert orphan is not None
        assert orphan["speaker"] == "simulation_system"

    def test_missing_execution_edge_case(self):
        call_msg = ParsedMessage(speaker="agent_agent", speaker_display="Agent", is_tool_event=True, tool_calls=[{"id": "c1"}])
        self.machine.process_tool_event(call_msg)
        text = ParsedMessage(speaker="agent_agent", content="done")
        entry = self.machine.process_text_message(text)
        assert entry["tool_calls"]
        assert entry["tool_results"] is None


"""
Tests for ConversationAdapter - validates conversion from AutoGen format to contract format
"""
import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import List, Dict, Any

# Import the module under test
from src.conversation_adapter import ConversationAdapter

# Import real AutoGen classes for testing
from autogen_agentchat.messages import (
    BaseChatMessage, 
    BaseAgentEvent,
    TextMessage, 
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    ToolCallSummaryMessage,
    HandoffMessage
)
from autogen_agentchat.base import TaskResult
from autogen_core._types import FunctionCall
from autogen_core.models import FunctionExecutionResult
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification

# Helper function to create FunctionCall objects
def create_function_call(id: str, name: str, arguments: str) -> FunctionCall:
    """Create a FunctionCall object for testing"""
    return FunctionCall(id=id, name=name, arguments=arguments)


class TestConversationAdapter:
    """Test suite for ConversationAdapter functionality"""
    
    def test_extract_speaker_agent(self):
        """Test speaker extraction for agent messages"""
        message = TextMessage(source="sales_agent", content="Hello")
        speaker = ConversationAdapter._extract_speaker(message)
        assert speaker == "agent_sales_agent"
    
    def test_extract_speaker_client(self):
        """Test speaker extraction for client messages"""
        message = TextMessage(source="client", content="Hi there")
        speaker = ConversationAdapter._extract_speaker(message)
        assert speaker == "client"
        
        # Test user source as well
        message_user = TextMessage(source="user", content="Hi there")
        speaker_user = ConversationAdapter._extract_speaker(message_user)
        assert speaker_user == "client"
    
    def test_extract_speaker_fallback(self):
        """Test speaker extraction fallback for unknown sources"""
        message = TextMessage(source="unknown_source", content="Unknown source")
        speaker = ConversationAdapter._extract_speaker(message)
        assert speaker == "agent_unknown_source"
    
    def test_extract_content_text_message(self):
        """Test content extraction from TextMessage"""
        message = TextMessage(source="agent", content="This is a text message")
        content = ConversationAdapter._extract_content(message)
        assert content == "This is a text message"
    
    def test_extract_content_tool_call_request_event(self):
        """Test content extraction from ToolCallRequestEvent"""
        tool_call = create_function_call("call_1", "rag_find_products", '{"message": "find beef"}')
        message = ToolCallRequestEvent(source="agent", content=[tool_call])
        content = ConversationAdapter._extract_content(message)
        assert content == "[TOOL CALL REQUEST: 1 tools]"
    
    def test_extract_content_handoff_message(self):
        """Test content extraction from HandoffMessage"""
        message = HandoffMessage(source="sales_agent", target="support_agent", content="Transferring to support")
        content = ConversationAdapter._extract_content(message)
        assert content == "[HANDOFF TO: support_agent]"
    
    def test_extract_tools_info_tool_call_request(self):
        """Test tool call extraction from ToolCallRequestEvent"""
        tool_call = create_function_call("call_1", "rag_find_products", '{"message": "find beef"}')
        message = ToolCallRequestEvent(source="agent", content=[tool_call])
        
        tool_calls, tool_results = ConversationAdapter._extract_tools_info(message)
        
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["function"]["name"] == "rag_find_products"
        assert tool_calls[0]["function"]["arguments"] == '{"message": "find beef"}'
        assert tool_results is None
    
    def test_extract_tools_info_tool_execution_event(self):
        """Test tool result extraction from ToolCallExecutionEvent"""
        result_data = {"products": [{"code": "BEEF001", "name": "Ground Beef"}]}
        # ToolCallExecutionEvent expects a list of FunctionExecutionResult objects
        execution_result = FunctionExecutionResult(
            call_id="call_1",
            content=json.dumps(result_data),
            is_error=False,
            name="rag_find_products"
        )
        message = ToolCallExecutionEvent(source="tool", content=[execution_result])
        
        tool_calls, tool_results = ConversationAdapter._extract_tools_info(message)
        
        assert tool_calls is None
        assert tool_results is not None
        assert len(tool_results) == 1
        assert tool_results[0] == result_data
    
    def test_extract_tools_info_no_tools(self):
        """Test tool extraction when no tools are present"""
        message = TextMessage(source="agent", content="Regular message")
        
        tool_calls, tool_results = ConversationAdapter._extract_tools_info(message)
        
        assert tool_calls is None
        assert tool_results is None
    
    def test_determine_conversation_status_max_turns(self):
        """Test status determination for max_turns stop reason"""
        status = ConversationAdapter._determine_conversation_status("max_turns", [])
        assert status == "completed"
    
    def test_determine_conversation_status_timeout(self):
        """Test status determination for timeout stop reason"""
        status = ConversationAdapter._determine_conversation_status("timeout", [])
        assert status == "failed"
    
    def test_determine_conversation_status_handoff(self):
        """Test status determination for handoff stop reason"""
        status = ConversationAdapter._determine_conversation_status("handoff_to_client", [])
        assert status == "completed"
    
    def test_determine_conversation_status_end_call(self):
        """Test status determination based on conversation content"""
        conversation_history = [
            {
                "turn": 1,
                "speaker": "client",
                "content": "[ЗАВЕРШИЛ ЗВОНОК: conversation completed]",
                "tool_calls": [{"function": {"name": "end_call"}}]
            }
        ]
        status = ConversationAdapter._determine_conversation_status("unknown", conversation_history)
        assert status == "completed"
    
    def test_extract_conversation_history_basic(self):
        """Test basic conversation history extraction"""
        messages = [
            TextMessage(source="system", content="System prompt"),  # Should be skipped
            TextMessage(source="sales_agent", content="Hello, how can I help you?"),
            TextMessage(source="client", content="I need some beef"),
        ]

        history = ConversationAdapter.extract_conversation_history(messages)
        
        assert len(history) == 2  # System message should be skipped
        
        # Check first entry (agent)
        assert history[0]["turn"] == 1
        assert history[0]["speaker"] == "agent_sales_agent"
        assert history[0]["content"] == "Hello, how can I help you?"
        assert "timestamp" in history[0]
        
        # Check second entry (client)
        assert history[1]["turn"] == 2
        assert history[1]["speaker"] == "client"
        assert history[1]["content"] == "I need some beef"

    def test_extract_conversation_history_display_names(self):
        """Verify speaker_display is derived from prompt specification"""
        messages = [
            TextMessage(source="sales_agent", content="Hello"),
            TextMessage(source="client", content="Hi")
        ]

        prompt_spec = SystemPromptSpecification(
            name="spec",
            version="1.0",
            description="",
            agents={
                "sales_agent": AgentPromptSpecification(name="Sales Agent", prompt="", tools=[]),
                "client": AgentPromptSpecification(name="Client", prompt="", tools=[])
            }
        )

        history = ConversationAdapter.extract_conversation_history(messages, prompt_spec)

        assert history[0]["speaker_display"] == "Sales Agent"
        assert history[1]["speaker_display"] == "Client"
    
    def test_extract_conversation_history_with_tools(self):
        """Test conversation history extraction with tool calls"""
        tool_call = create_function_call("call_1", "rag_find_products", '{"message": "beef"}')
        messages = [
            TextMessage(source="client", content="I need some beef"),
            ToolCallRequestEvent(source="sales_agent", content=[tool_call]),
            ToolCallExecutionEvent(source="tool", content=[
                FunctionExecutionResult(
                    call_id="call_1",
                    content='{"products": [{"code": "BEEF001"}]}',
                    is_error=False,
                    name="rag_find_products"
                )
            ]),
        ]
        
        history = ConversationAdapter.extract_conversation_history(messages)
        
        assert len(history) == 3
        
        # Check tool call entry
        tool_call_entry = history[1]
        assert tool_call_entry["speaker"] == "agent_sales_agent"
        assert "[TOOL CALL REQUEST: 1 tools]" in tool_call_entry["content"]
        assert "tool_calls" in tool_call_entry
        assert len(tool_call_entry["tool_calls"]) == 1
        assert tool_call_entry["tool_calls"][0]["function"]["name"] == "rag_find_products"
        
        # Check tool result entry
        tool_result_entry = history[2]
        assert "tool_results" in tool_result_entry
        assert len(tool_result_entry["tool_results"]) == 1
        assert tool_result_entry["tool_results"][0]["products"][0]["code"] == "BEEF001"
    
    @patch('src.conversation_adapter.get_logger')
    def test_autogen_to_contract_format_success(self, mock_logger):
        """Test successful conversion of AutoGen TaskResult to contract format"""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Create TaskResult
        messages = [
            TextMessage(source="sales_agent", content="Hello, how can I help?"),
            TextMessage(source="client", content="I need some products"),
            TextMessage(source="sales_agent", content="Great, let me help you find them"),
        ]
        task_result = TaskResult(messages=messages, stop_reason="max_turns")
        
        # Call the method
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=task_result,
            session_id="test_session_123",
            scenario_name="test_scenario",
            duration=45.5,
            start_time=1700000000.0
        )
        
        # Validate result structure
        assert result["session_id"] == "test_session_123"
        assert result["scenario"] == "test_scenario"
        assert result["status"] == "completed"
        assert result["total_turns"] == 3
        assert result["duration_seconds"] == 45.5
        assert result["tools_used"] is False
        assert len(result["conversation_history"]) == 3
        assert "start_time" in result
        assert "end_time" in result
        
        # Validate timestamps
        start_time = datetime.fromisoformat(result["start_time"])
        end_time = datetime.fromisoformat(result["end_time"])
        assert start_time < end_time
    
    @patch('src.conversation_adapter.get_logger')
    def test_autogen_to_contract_format_with_tools(self, mock_logger):
        """Test conversion with tool usage"""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Create TaskResult with tools
        tool_call = create_function_call("call_1", "rag_find_products", '{"message": "beef"}')
        messages = [
            TextMessage(source="client", content="I need beef"),
            ToolCallRequestEvent(source="sales_agent", content=[tool_call]),
        ]
        task_result = TaskResult(messages=messages, stop_reason="handoff_to_client")
        
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=task_result,
            session_id="test_session_456",
            scenario_name="tool_test",
            duration=30.0
        )
        
        assert result["tools_used"] is True
        assert result["status"] == "completed"
        assert len(result["conversation_history"]) == 2
        
        # Check that tool call is preserved
        tool_entry = result["conversation_history"][1]
        assert "tool_calls" in tool_entry
        assert tool_entry["tool_calls"][0]["function"]["name"] == "rag_find_products"
    
    @patch('src.conversation_adapter.get_logger')
    def test_autogen_to_contract_format_error_handling(self, mock_logger):
        """Test error handling in conversion"""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Create invalid TaskResult to trigger error
        task_result = None  # This should cause an error
        
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=task_result,
            session_id="error_session",
            scenario_name="error_test",
            duration=0.0
        )
        
        # Validate error result structure
        assert result["session_id"] == "error_session"
        assert result["scenario"] == "error_test"
        assert result["status"] == "failed"
        assert "error" in result
        assert "error_type" in result
        assert result["total_turns"] == 0
        assert result["tools_used"] is False
        assert result["conversation_history"] == []
    
    def test_conversation_adapter_integration(self):
        """Integration test simulating typical AutoGen conversation flow"""
        # Simulate a complete conversation with handoffs and tools
        tool_call = create_function_call("call_1", "rag_find_products", '{"message": "fresh beef"}')
        handoff_tool = create_function_call("call_2", "end_call", '{"reason": "order completed"}')
        
        messages = [
            TextMessage(source="system", content="You are a sales agent"),  # Should be skipped
            TextMessage(source="client", content="Hello, I need to order some meat"),
            TextMessage(source="sales_agent", content="I'll help you find the perfect meat products"),
            ToolCallRequestEvent(source="sales_agent", content=[tool_call]),
            ToolCallExecutionEvent(source="tool", content=[
                FunctionExecutionResult(
                    call_id="call_1",
                    content='{"products": [{"code": "BEEF001", "name": "Fresh Ground Beef", "price": 12.99}]}',
                    is_error=False,
                    name="rag_find_products"
                )
            ]),
            TextMessage(source="sales_agent", content="I found fresh ground beef for $12.99. Would you like to add it to your cart?"),
            TextMessage(source="client", content="Yes, please add 2 pounds to my cart"),
            ToolCallRequestEvent(source="client", content=[handoff_tool]),
        ]
        
        task_result = TaskResult(messages=messages, stop_reason="handoff_to_client")
        
        # Convert to contract format
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=task_result,
            session_id="integration_test_789",
            scenario_name="meat_ordering_scenario",
            duration=120.5
        )
        
        # Validate comprehensive result
        assert result["session_id"] == "integration_test_789"
        assert result["scenario"] == "meat_ordering_scenario"
        assert result["status"] == "completed"
        assert result["tools_used"] is True
        assert result["duration_seconds"] == 120.5
        
        # Should have 7 conversation entries (excluding system message)
        assert len(result["conversation_history"]) == 7
        
        # Validate conversation flow
        history = result["conversation_history"]
        
        # First message from client
        assert history[0]["speaker"] == "client"
        assert history[0]["content"] == "Hello, I need to order some meat"
        
        # Agent response
        assert history[1]["speaker"] == "agent_sales_agent"
        assert "help you find" in history[1]["content"]
        
        # Tool call from agent
        assert history[2]["speaker"] == "agent_sales_agent"
        assert "tool_calls" in history[2]
        assert history[2]["tool_calls"][0]["function"]["name"] == "rag_find_products"
        
        # Tool result
        assert history[3]["speaker"] == "agent"  # Default for tool results
        assert "tool_results" in history[3]
        assert "BEEF001" in str(history[3]["tool_results"][0])
        
        # Final client tool call (end_call)
        assert history[6]["speaker"] == "client"
        assert "tool_calls" in history[6]
        assert history[6]["tool_calls"][0]["function"]["name"] == "end_call"
        
        # Validate all entries have required fields
        for entry in history:
            assert "turn" in entry
            assert "speaker" in entry
            assert "content" in entry
            assert "timestamp" in entry
            assert entry["turn"] > 0
    
    def test_edge_case_empty_messages(self):
        """Test handling of empty message list"""
        task_result = TaskResult(messages=[], stop_reason="no_messages")
        
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=task_result,
            session_id="empty_test",
            scenario_name="empty_scenario",
            duration=0.0
        )
        
        assert result["total_turns"] == 0
        assert result["conversation_history"] == []
        assert result["tools_used"] is False
        assert result["status"] == "completed"
    
    def test_edge_case_malformed_tool_result(self):
        """Test handling of malformed tool result content"""
        # Create FunctionExecutionResult with malformed JSON content
        execution_result = FunctionExecutionResult(
            call_id="call_1",
            content="not valid json {}",
            is_error=False,
            name="test_tool"
        )
        message = ToolCallExecutionEvent(source="tool", content=[execution_result])
        
        tool_calls, tool_results = ConversationAdapter._extract_tools_info(message)
        
        assert tool_calls is None
        assert tool_results is not None
        assert len(tool_results) == 1
        assert tool_results[0] == "not valid json {}"  # Should be stored as string
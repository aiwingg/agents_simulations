"""
Tests for AutogenMASFactory
"""

import pytest
from unittest.mock import Mock, patch
from src.autogen_mas_factory import AutogenMASFactory
from src.prompt_specification import SystemPromptSpecification, AgentPromptSpecification
from src.openai_wrapper import OpenAIWrapper


class TestAutogenMASFactory:
    """Test AutogenMASFactory functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.session_id = "test_session_123"
        self.factory = AutogenMASFactory(self.session_id)

    def test_initialization(self):
        """Test AutogenMASFactory initialization"""
        assert self.factory.session_id == self.session_id
        assert self.factory.logger is not None

    def test_setup_agent_handoffs(self):
        """Test handoff configuration setup"""
        # Create test agent configurations
        agents_config = {
            "sales_agent": AgentPromptSpecification(
                name="sales_agent",
                prompt="You are a sales agent",
                tools=["rag_find_products"],
                handoffs={"support_agent": "For technical support"},
            ),
            "support_agent": AgentPromptSpecification(
                name="support_agent",
                prompt="You are a support agent",
                tools=["get_cart"],
                handoffs={"sales_agent": "For sales questions"},
            ),
        }

        # Test handoff setup
        handoff_config = self.factory._setup_agent_handoffs(agents_config)

        # Verify handoff configuration
        assert "sales_agent" in handoff_config
        assert "support_agent" in handoff_config

        # Each agent should have handoffs to other agents only (no client - user is external)
        assert "support_agent" in handoff_config["sales_agent"]
        assert "client" not in handoff_config["sales_agent"]  # User is external now
        assert "sales_agent" in handoff_config["support_agent"]
        assert "client" not in handoff_config["support_agent"]  # User is external now

    def test_create_termination_conditions(self):
        """Test termination conditions creation with max_internal_messages parameter"""
        max_internal_messages = 15
        termination = self.factory._create_termination_conditions(max_internal_messages)

        # Should create combined termination condition
        assert termination is not None

    @patch("src.autogen_mas_factory.AssistantAgent")
    def test_create_swarm_agents(self, mock_agent_class):
        """Test swarm agents creation"""
        # Create test configuration
        agents_config = {
            "test_agent": AgentPromptSpecification(
                name="test_agent",
                prompt="You are a test agent",
                tools=["rag_find_products"],
                description="Test agent description",
            )
        }

        # Mock tools
        mock_tool = Mock()
        mock_tool.name = "rag_find_products"
        tools = [mock_tool]

        # Mock model client
        mock_model_client = Mock()

        # Mock agent instance
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Test agent creation
        agents = self.factory._create_swarm_agents(agents_config, tools, mock_model_client)

        # Verify agent was created
        assert len(agents) == 1
        assert agents[0] == mock_agent_instance

        # Verify AssistantAgent was called with correct parameters
        mock_agent_class.assert_called_once_with(
            name="test_agent",
            model_client=mock_model_client,
            handoffs=[],  # No handoffs since no other agents and user is external
            tools=[mock_tool],
            system_message="You are a test agent",
            description="Test agent description",
        )

"""
Tests for AutogenConversationEngine
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.autogen_conversation_engine import AutogenConversationEngine
from src.openai_wrapper import OpenAIWrapper
from src.prompt_specification import SystemPromptSpecification, AgentPromptSpecification


# TODO: tests here are heavily mocked. I carried out a large refactor of the engine, but tests are not updated.
# We should update them to use the new engine architecture to reduce the amount of mocking.

class TestAutogenConversationEngine:
    """Test AutogenConversationEngine functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        # Mock OpenAIWrapper
        self.mock_openai_wrapper = Mock(spec=OpenAIWrapper)
        self.mock_openai_wrapper.client = Mock()
        self.mock_openai_wrapper.client.api_key = "test_api_key"
        self.mock_openai_wrapper.model = "gpt-4o-mini"

        # Mock system prompt specification
        self.mock_agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt="You are a test agent: {{ name }}",
            tools=["rag_find_products"],
            description="Test agent",
        )

        self.mock_client_spec = AgentPromptSpecification(
            name="client", prompt="You are a test client: {{ name }}", tools=["end_call"], description="Test client"
        )

        self.mock_system_prompt_spec = SystemPromptSpecification(
            name="test_spec",
            version="1.0",
            description="Test specification",
            agents={"test_agent": self.mock_agent_spec, "client": self.mock_client_spec},
        )

        # Create engine with mocked dependencies
        with patch("src.autogen_conversation_engine.PromptSpecificationManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load_specification.return_value = self.mock_system_prompt_spec
            mock_manager_class.return_value = mock_manager

            with patch("src.autogen_conversation_engine.WebhookManager") as mock_webhook_class:
                mock_webhook = Mock()
                mock_webhook.initialize_session = AsyncMock(return_value="test_session_123")
                mock_webhook_class.return_value = mock_webhook

                self.engine = AutogenConversationEngine(
                    openai_wrapper=self.mock_openai_wrapper, prompt_spec_name="test_prompts"
                )
                self.engine.webhook_manager = mock_webhook

    def test_initialization(self):
        """Test AutogenConversationEngine initialization"""
        assert self.engine.openai == self.mock_openai_wrapper
        assert self.engine.prompt_spec_name == "test_prompts"
        assert self.engine.prompt_specification == self.mock_system_prompt_spec
        assert self.engine.webhook_manager is not None
        assert self.engine.logger is not None

    @pytest.mark.asyncio
    async def test_enrich_variables_with_client_data_no_client_id(self):
        """Test variable enrichment when no client_id is provided"""
        variables = {"NAME": "John", "LOCATIONS": "Moscow"}
        test_session_id = "test_session_123"

        enriched_vars, session_id = await self.engine._enrich_variables_with_client_data(variables, test_session_id)

        # Should preserve original variables and add lowercase versions
        assert enriched_vars["NAME"] == "John"
        assert enriched_vars["name"] == "John"
        assert enriched_vars["LOCATIONS"] == "Moscow"
        assert enriched_vars["locations"] == "Moscow"
        # Should add session_id to variables
        assert enriched_vars["session_id"] == test_session_id
        # Should apply default values
        assert enriched_vars["CURRENT_DATE"] == "2024-01-15"
        assert session_id is None

    @pytest.mark.asyncio
    async def test_enrich_variables_with_client_data_with_client_id(self):
        """Test variable enrichment when client_id is provided"""
        variables = {"client_id": "client_123"}
        test_session_id = "test_session_123"

        # Mock webhook response
        mock_client_data = {
            "variables": {"NAME": "Alice", "LOCATIONS": "St. Petersburg", "CURRENT_DATE": "2024-06-27"},
            "session_id": "webhook_session_456",
        }
        self.engine.webhook_manager.get_client_data = AsyncMock(return_value=mock_client_data)

        enriched_vars, session_id = await self.engine._enrich_variables_with_client_data(variables, test_session_id)

        # Should use webhook data
        assert enriched_vars["NAME"] == "Alice"
        assert enriched_vars["name"] == "Alice"
        assert enriched_vars["LOCATIONS"] == "St. Petersburg"
        assert enriched_vars["locations"] == "St. Petersburg"
        assert enriched_vars["current_date"] == "2024-06-27"
        # Should add session_id to variables
        assert enriched_vars["session_id"] == test_session_id
        assert session_id == "webhook_session_456"

    def test_create_autogen_client(self):
        """Test AutoGen client creation via AutogenModelClientFactory"""
        with patch("src.autogen_model_client.AutogenModelClientFactory.create_from_openai_wrapper") as mock_factory:
            mock_client_instance = Mock()
            mock_factory.return_value = mock_client_instance

            from src.autogen_model_client import AutogenModelClientFactory

            result = AutogenModelClientFactory.create_from_openai_wrapper(self.engine.openai)

            # Verify factory was called with correct parameters
            mock_factory.assert_called_once_with(self.engine.openai)
            assert result == mock_client_instance

    @pytest.mark.asyncio
    async def test_run_conversation_delegates_to_tools_version(self):
        """Test that run_conversation delegates to run_conversation_with_tools"""
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        # Mock the tools version to return a specific result
        mock_result = {
            "session_id": "test_session",
            "status": "completed",
            "tools_used": True,  # This should be changed to False
        }

        with patch.object(self.engine, "run_conversation_with_tools", new_callable=AsyncMock) as mock_tools_method:
            mock_tools_method.return_value = mock_result

            result = await self.engine.run_conversation(scenario)

            # Verify delegation occurred
            mock_tools_method.assert_called_once_with(scenario, None, None)

            # Verify tools_used was set to False
            assert result["tools_used"] == False

    @pytest.mark.asyncio
    async def test_non_text_message_error_handling(self):
        """Test conversation engine handles non-text final messages gracefully"""
        # This is a simplified test that verifies the error path without complex mocking
        # In practice, the non-text message scenario would be tested via integration tests
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        # Test scenario: Create a mock that will trigger the non-text message path
        # We'll simulate this by making the last message not be a TextMessage instance
        from autogen_agentchat.messages import TextMessage

        # Create a real TextMessage for comparison
        text_msg = TextMessage(content="Hello", source="test_agent")

        # Create a non-text mock object
        non_text_msg = Mock()
        non_text_msg.__class__ = Mock  # This won't be a TextMessage

        # Mock TaskResult with mixed message types
        mock_task_result = Mock()
        mock_task_result.messages = [text_msg, non_text_msg]  # Last message is not TextMessage
        mock_task_result.stop_reason = "MaxMessageTermination reached"

        with (
            patch(
                "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
            ) as mock_create_client,
            patch.object(self.engine, "_create_user_agent") as mock_create_user_agent,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as mock_tool_factory_class,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mock_mas_factory_class,
            patch("src.autogen_conversation_engine.ConversationAdapter") as mock_adapter_class,
            patch.object(self.engine.prompt_specification, "format_with_variables") as mock_format_spec,
        ):
            # Setup mocks
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            mock_formatted_spec = Mock()
            mock_formatted_spec.agents = self.engine.prompt_specification.agents
            mock_format_spec.return_value = mock_formatted_spec

            mock_user_agent = Mock()
            mock_create_user_agent.return_value = mock_user_agent

            mock_tool_factory = Mock()
            mock_tools = [Mock()]
            mock_tool_factory.get_tools_for_agent.return_value = mock_tools
            mock_tool_factory_class.return_value = mock_tool_factory

            mock_mas_factory = Mock()
            mock_swarm = Mock()
            mock_swarm.run = AsyncMock(return_value=mock_task_result)
            mock_mas_factory.create_swarm_team.return_value = mock_swarm
            mock_mas_factory_class.return_value = mock_mas_factory

            mock_adapter_class.extract_conversation_history.return_value = []

            # Run conversation
            result = await self.engine.run_conversation_with_tools(scenario)

            # Verify graceful error handling
            assert result["status"] == "failed"
            assert result["error_type"] == "NonTextMessageError"
            assert "Mock" in result["error"]  # Mock class name will be in error
            assert result["mas_stop_reason"] == "MaxMessageTermination reached"
            assert result["mas_message_count"] == 2

    @pytest.mark.asyncio
    async def test_run_conversation_with_tools_success(self):
        """Test successful conversation with tools using AutoGen Swarm"""
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        # Mock all dependencies
        with (
            patch(
                "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
            ) as mock_create_client,
            patch.object(self.engine, "_create_user_agent") as mock_create_user_agent,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as mock_tool_factory_class,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mock_mas_factory_class,
            patch("src.autogen_conversation_engine.ConversationAdapter") as mock_adapter_class,
            patch.object(self.engine.prompt_specification, "format_with_variables") as mock_format_spec,
        ):
            # Setup mocks
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            # Mock formatted spec
            mock_formatted_spec = Mock()
            mock_formatted_spec.agents = self.engine.prompt_specification.agents
            mock_format_spec.return_value = mock_formatted_spec

            # Mock user agent
            mock_user_agent = Mock()
            mock_create_user_agent.return_value = mock_user_agent

            mock_tool_factory = Mock()
            mock_tools = [Mock()]
            mock_tool_factory.get_tools_for_agent.return_value = mock_tools
            mock_tool_factory_class.return_value = mock_tool_factory

            mock_mas_factory = Mock()
            mock_swarm = Mock()

            # Create mock messages for the conversation
            from autogen_agentchat.messages import TextMessage

            mock_agent_message = TextMessage(content="Hello! How can I help you?", source="agent_agent")

            mock_task_result = Mock()
            mock_task_result.stop_reason = "completed_1_turns"  # Natural completion after 1 turn
            mock_task_result.messages = [mock_agent_message]
            mock_swarm.run = AsyncMock(return_value=mock_task_result)
            mock_mas_factory.create_swarm_team.return_value = mock_swarm
            mock_mas_factory_class.return_value = mock_mas_factory

            mock_adapter_result = {
                "session_id": "test_session_123",
                "scenario": "test_scenario",
                "status": "completed",
                "total_turns": 3,
                "tools_used": True,
            }
            mock_adapter_class.autogen_to_contract_format.return_value = mock_adapter_result

            # Mock wait_for is not used in new implementation - remove this

            # Mock enrich_variables to return session_id
            with patch.object(self.engine, "_enrich_variables_with_client_data") as mock_enrich:
                mock_enrich.return_value = (
                    {"CLIENT_NAME": "John", "name": "John", "session_id": "test_session_123"},
                    None,
                )

                result = await self.engine.run_conversation_with_tools(scenario)

            # Verify all components were called correctly
            mock_create_client.assert_called_once()
            mock_tool_factory_class.assert_called_once_with("test_session_123")
            mock_mas_factory_class.assert_called_once_with("test_session_123")
            mock_mas_factory.create_swarm_team.assert_called_once()

            # Verify run was called with HandoffMessage (not string)
            assert mock_swarm.run.call_count >= 1
            call_args = mock_swarm.run.call_args_list[0]
            handoff_message = call_args[1]["task"]  # keyword argument
            assert handoff_message.source == "client"
            assert handoff_message.target == "agent"
            assert handoff_message.content == "Добрый день!"

            mock_adapter_class.autogen_to_contract_format.assert_called_once()

            # Verify result
            assert result == mock_adapter_result

    @pytest.mark.asyncio
    async def test_run_conversation_with_tools_timeout(self):
        """Test conversation timeout handling"""
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        with (
            patch(
                "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
            ) as mock_create_client,
            patch.object(self.engine, "_create_user_agent") as mock_create_user_agent,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as mock_tool_factory_class,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mock_mas_factory_class,
        ):
            # Setup mocks to simulate timeout
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            # Mock user agent
            mock_user_agent = Mock()
            mock_create_user_agent.return_value = mock_user_agent

            mock_tool_factory = Mock()
            mock_tools = [Mock()]
            mock_tool_factory.get_tools_for_agent.return_value = mock_tools
            mock_tool_factory_class.return_value = mock_tool_factory

            mock_mas_factory = Mock()
            mock_swarm = Mock()
            mock_swarm.run = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_mas_factory.create_swarm_team.return_value = mock_swarm
            mock_mas_factory_class.return_value = mock_mas_factory

            # Mock enrich_variables to return session_id and trigger timeout via swarm.run
            with patch.object(self.engine, "_enrich_variables_with_client_data") as mock_enrich:
                mock_enrich.return_value = (
                    {"CLIENT_NAME": "John", "name": "John", "session_id": "test_session_123"},
                    None,
                )

                result = await self.engine.run_conversation_with_tools(scenario, timeout_sec=10)

            # Verify timeout result
            assert result["status"] == "timeout"
            assert result["error_type"] == "TimeoutError"
            assert "timeout after 10 seconds" in result["error"]
            assert isinstance(result["conversation_history"], list)
            assert result["tools_used"] == True

    @pytest.mark.asyncio
    async def test_run_conversation_with_tools_api_blocked(self):
        """Test geographic restriction error handling"""
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        with patch(
            "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
        ) as mock_create_client:
            # Mock geographic restriction error
            mock_create_client.side_effect = Exception("geographic restriction detected")

            # Mock enrich_variables to return session_id
            with patch.object(self.engine, "_enrich_variables_with_client_data") as mock_enrich:
                mock_enrich.return_value = (
                    {"CLIENT_NAME": "John", "name": "John", "session_id": "test_session_123"},
                    None,
                )

                result = await self.engine.run_conversation_with_tools(scenario)

            # Verify graceful degradation
            assert result["status"] == "failed_api_blocked"
            assert result["error"] == "OpenAI API blocked due to geographic restrictions"
            assert result["error_type"] == "APIBlockedError"
            assert result["graceful_degradation"] == True
            assert result["tools_used"] == True

    @pytest.mark.asyncio
    async def test_run_conversation_with_tools_general_error(self):
        """Test general error handling"""
        scenario = {"name": "test_scenario", "variables": {"CLIENT_NAME": "John"}}

        with patch(
            "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
        ) as mock_create_client:
            # Mock general error
            mock_create_client.side_effect = ValueError("Something went wrong")

            # Mock enrich_variables to return session_id
            with patch.object(self.engine, "_enrich_variables_with_client_data") as mock_enrich:
                mock_enrich.return_value = (
                    {"CLIENT_NAME": "John", "name": "John", "session_id": "test_session_123"},
                    None,
                )

                result = await self.engine.run_conversation_with_tools(scenario)

            # Verify error result
            assert result["status"] == "failed"
            assert result["error"] == "Something went wrong"
            assert result["error_type"] == "ValueError"
            assert result["tools_used"] == True
            assert "error_context" in result

    @pytest.mark.asyncio
    async def test_run_conversation_with_tools_uses_webhook_session_id(self):
        """Test that webhook session_id is used when available"""
        scenario = {"name": "test_scenario", "variables": {"client_id": "client_123"}}

        with (
            patch(
                "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
            ) as mock_create_client,
            patch.object(self.engine, "_create_user_agent") as mock_create_user_agent,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as mock_tool_factory_class,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mock_mas_factory_class,
            patch("src.autogen_conversation_engine.ConversationAdapter") as mock_adapter_class,
            patch.object(
                self.engine.webhook_manager, "get_client_data", new_callable=AsyncMock
            ) as mock_get_client_data,
        ):
            # Setup mocks
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            # Mock user agent
            mock_user_agent = Mock()
            mock_create_user_agent.return_value = mock_user_agent

            mock_tool_factory = Mock()
            mock_tools = [Mock()]
            mock_tool_factory.get_tools_for_agent.return_value = mock_tools
            mock_tool_factory_class.return_value = mock_tool_factory

            mock_mas_factory = Mock()
            mock_swarm = Mock()

            # Create mock messages for the conversation
            from autogen_agentchat.messages import TextMessage

            mock_agent_message = TextMessage(content="Hello! How can I help you?", source="agent_agent")

            mock_task_result = Mock()
            mock_task_result.stop_reason = "completed_1_turns"  # Natural completion after 1 turn
            mock_task_result.messages = [mock_agent_message]
            mock_swarm.run = AsyncMock(return_value=mock_task_result)
            mock_mas_factory.create_swarm_team.return_value = mock_swarm
            mock_mas_factory_class.return_value = mock_mas_factory

            mock_adapter_result = {
                "session_id": "webhook_session_456",
                "scenario": "test_scenario",
                "status": "completed",
            }
            mock_adapter_class.autogen_to_contract_format.return_value = mock_adapter_result

            # Mock webhook client data
            mock_get_client_data.return_value = {"session_id": "webhook_session_456"}

            # Mock enrich_variables to return webhook session_id
            with patch.object(self.engine, "_enrich_variables_with_client_data") as mock_enrich:
                mock_enrich.return_value = (
                    {"client_id": "client_123", "name": "Client", "session_id": "webhook_session_456"},
                    "webhook_session_456",
                )

                result = await self.engine.run_conversation_with_tools(scenario)

            # Verify webhook session_id was used
            mock_tool_factory_class.assert_called_once_with("webhook_session_456")
            mock_mas_factory_class.assert_called_once_with("webhook_session_456")

            # Verify session_id in adapter call
            adapter_call_args = mock_adapter_class.autogen_to_contract_format.call_args
            assert adapter_call_args[1]["session_id"] == "webhook_session_456"

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.autogen_conversation_engine import AutogenConversationEngine
from src.openai_wrapper import OpenAIWrapper
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification


class TestAutogenConversationEnginePart3:
    def setup_method(self):
        self.mock_openai = Mock(spec=OpenAIWrapper)
        self.mock_openai.client = Mock()
        self.mock_openai.client.api_key = "k"
        self.mock_openai.model = "m"

        self.agent_spec = AgentPromptSpecification(
            name="agent",
            prompt="p",
            tools=[],
            description="d",
        )
        self.client_spec = AgentPromptSpecification(
            name="client",
            prompt="c",
            tools=[],
            description="cd",
        )
        self.system_spec = SystemPromptSpecification(
            name="spec",
            version="1",
            description="desc",
            agents={"agent": self.agent_spec, "client": self.client_spec},
        )
        with (
            patch("src.autogen_conversation_engine.PromptSpecificationManager") as mgr_cls,
            patch("src.autogen_conversation_engine.WebhookManager") as wh_cls,
        ):
            mgr = Mock()
            mgr.load_specification.return_value = self.system_spec
            mgr_cls.return_value = mgr
            wh = Mock()
            wh.initialize_session = AsyncMock(return_value="sid")
            wh_cls.return_value = wh
            self.engine = AutogenConversationEngine(self.mock_openai, "test")
            self.engine.webhook_manager = wh

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        scenario = {"name": "s", "variables": {"CLIENT_NAME": "John"}}
        with (
            patch(
                "src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper"
            ) as create_client,
            patch.object(self.engine, "_enrich_variables_with_client_data") as enrich,
            patch.object(self.engine.error_handler, "handle_error_by_type") as handle,
        ):
            create_client.side_effect = ValueError("boom")
            enrich.return_value = ({"CLIENT_NAME": "John", "name": "John", "session_id": "sid"}, None)
            handle.return_value = {"status": "failed"}
            result = await self.engine.run_conversation_with_tools(scenario)
            handle.assert_called_once()
            assert result == {"status": "failed"}

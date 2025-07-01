import pytest
from unittest.mock import ANY, AsyncMock, Mock, patch

from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult

from src.autogen_conversation_engine import AutogenConversationEngine
from src.openai_wrapper import OpenAIWrapper
from src.turn_result import TurnResult


class TestAutogenConversationEnginePart2:
    def setup_method(self):
        self.mock_openai_wrapper = Mock(spec=OpenAIWrapper)
        self.mock_openai_wrapper.client = Mock()
        self.mock_openai_wrapper.client.api_key = "key"
        with patch("src.autogen_conversation_engine.PromptSpecificationManager") as mgr, patch(
            "src.autogen_conversation_engine.WebhookManager"
        ) as wh:
            mgr.return_value.load_specification.return_value = Mock(agents={"agent": Mock()}, version="1.0")
            wh.return_value = Mock(initialize_session=AsyncMock(return_value="sid"))
            self.engine = AutogenConversationEngine(self.mock_openai_wrapper)
            self.engine.webhook_manager = wh.return_value

    @pytest.mark.asyncio
    async def test_turn_management_integration(self):
        scenario = {"name": "sc", "variables": {}}
        with (
            patch("src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper") as create_client,
            patch.object(self.engine, "_create_user_agent") as create_user_agent,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as tool_factory_cls,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mas_factory_cls,
            patch("src.autogen_conversation_engine.ConversationAdapter") as adapter_cls,
            patch.object(self.engine.prompt_specification, "format_with_variables") as format_spec,
            patch.object(self.engine, "_enrich_variables_with_client_data") as enrich,
            patch.object(self.engine.turn_manager, "execute_turn", new_callable=AsyncMock) as exec_turn,
            patch.object(self.engine.turn_manager, "generate_user_response", new_callable=AsyncMock) as gen_resp,
        ):
            create_client.return_value = Mock()
            create_user_agent.return_value = Mock()
            tool_factory_cls.return_value.get_tools_for_agent.return_value = []
            mock_swarm = Mock()
            mas_factory_cls.return_value.create_swarm_team.return_value = mock_swarm
            adapter_cls.autogen_to_contract_format.return_value = {"session_id": "sid", "status": "completed"}
            format_spec.return_value = Mock(agents={"agent": Mock(tools=[])})
            enrich.return_value = ({"session_id": "sid"}, None)
            msg = TextMessage(content="hi", source="agent")
            task_result = TaskResult(messages=[msg], stop_reason="completed")
            exec_turn.return_value = TurnResult(task_result, msg, False, "completed")
            gen_resp.return_value = "bye"

            result = await self.engine.run_conversation_with_tools(scenario, max_turns=1, timeout_sec=5)

            exec_turn.assert_called_once_with(mock_swarm, "Добрый день!", "agent", ANY)
            gen_resp.assert_not_called()
            assert result["status"] == "completed"

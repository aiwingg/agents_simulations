import pytest
from unittest.mock import AsyncMock, Mock, patch, ANY

from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
from src.turn_result import TurnResult

from src.autogen_conversation_engine import AutogenConversationEngine
from src.openai_wrapper import OpenAIWrapper
from src.conversation_context import ConversationContext


class TestAutogenConversationEngineIntegration:
    def setup_method(self):
        self.mock_openai = Mock(spec=OpenAIWrapper)
        self.mock_openai.client = Mock()
        self.mock_openai.client.api_key = "k"
        with patch("src.autogen_conversation_engine.PromptSpecificationManager") as mgr_cls, patch(
            "src.autogen_conversation_engine.WebhookManager"
        ) as wh_cls:
            mgr = Mock()
            mgr.load_specification.return_value = Mock(agents={"agent": Mock(tools=[])}, version="1")
            mgr_cls.return_value = mgr
            wh = Mock()
            wh.initialize_session = AsyncMock(return_value="sid")
            wh_cls.return_value = wh
            self.engine = AutogenConversationEngine(self.mock_openai)
            self.engine.webhook_manager = wh

    @pytest.mark.asyncio
    async def test_service_coordination_flow(self):
        scenario = {"name": "s", "variables": {}}
        with (
            patch("src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper") as create_client,
            patch.object(self.engine, "_create_user_agent") as create_user,
            patch("src.autogen_conversation_engine.AutogenToolFactory") as tool_cls,
            patch("src.autogen_conversation_engine.AutogenMASFactory") as mas_cls,
            patch("src.autogen_conversation_engine.ConversationAdapter") as adapter,
            patch.object(self.engine.prompt_specification, "format_with_variables") as format_spec,
            patch.object(self.engine.loop_orchestrator, "run_conversation_loop", new_callable=AsyncMock) as loop,
            patch.object(self.engine, "_enrich_variables_with_client_data") as enrich,
        ):
            create_client.return_value = Mock()
            create_user.return_value = Mock()
            tool_cls.return_value.get_tools_for_agent.return_value = []
            mas = Mock()
            mas_cls.return_value.create_swarm_team.return_value = Mock()
            mas_cls.return_value = mas
            adapter.autogen_to_contract_format.return_value = {"session_id": "sid", "status": "completed"}
            format_spec.return_value = Mock(agents={"agent": Mock(tools=[])})
            enrich.return_value = ({"session_id": "sid"}, None)
            loop.return_value = ConversationContext("sid", "s", 1, 5, 0.0)
            result = await self.engine.run_conversation_with_tools(scenario, max_turns=1)
            assert result["status"] == "completed"
            enrich.assert_called_once()
            loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_propagation(self):
        scenario = {"name": "s", "variables": {}}
        with (
            patch("src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper") as create_client,
            patch.object(self.engine, "_enrich_variables_with_client_data") as enrich,
            patch.object(self.engine.error_handler, "handle_error_by_type") as handle,
        ):
            create_client.side_effect = ValueError("boom")
            enrich.return_value = ({"session_id": "sid"}, None)
            handle.return_value = {"status": "failed"}
            result = await self.engine.run_conversation_with_tools(scenario)
            handle.assert_called_once()
            assert result == {"status": "failed"}

    @pytest.mark.asyncio
    async def test_public_interface_preservation(self):
        scenario = {"name": "s", "variables": {}}
        with patch.object(self.engine, "run_conversation_with_tools", new_callable=AsyncMock) as run_tools:
            run_tools.return_value = {"session_id": "sid", "status": "done", "tools_used": True}
            result = await self.engine.run_conversation(scenario)
            run_tools.assert_called_once_with(scenario, None, None)
            assert result["tools_used"] is False

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

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        scenario = {"name": "s", "variables": {"CLIENT_NAME": "John"}}
        with (
            patch("src.autogen_conversation_engine.AutogenModelClientFactory.create_from_openai_wrapper") as create_client,
            patch.object(self.engine, "_enrich_variables_with_client_data") as enrich,
            patch.object(self.engine.error_handler, "handle_error_by_type") as handle,
        ):
            create_client.side_effect = ValueError("boom")
            enrich.return_value = ({"CLIENT_NAME": "John", "name": "John", "session_id": "sid"}, None)
            handle.return_value = {"status": "failed"}
            result = await self.engine.run_conversation_with_tools(scenario)
            handle.assert_called_once()
            assert result == {"status": "failed"}

import pytest
from unittest.mock import AsyncMock, Mock

from src.scenario_variable_enricher import enrich_scenario_variables, DEFAULTS
from src.webhook_manager import WebhookManager
from src.logging_utils import SimulationLogger


class TestScenarioVariableEnricher:
    @pytest.mark.asyncio
    async def test_enrich_variables_no_client_id(self):
        variables = {"NAME": "John", "LOCATIONS": "Moscow"}
        webhook_manager = Mock(spec=WebhookManager)
        logger = Mock(spec=SimulationLogger)
        result, session = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["name"] == "John"
        assert result["locations"] == "Moscow"
        assert result["session_id"] == "sid"
        assert result["CURRENT_DATE"] == DEFAULTS["CURRENT_DATE"]
        assert session is None

    @pytest.mark.asyncio
    async def test_enrich_variables_with_client_id(self):
        variables = {"client_id": "c1"}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock(
            return_value={"variables": {"NAME": "Alice"}, "session_id": "web_sid"}
        )
        logger = Mock(spec=SimulationLogger)
        result, session = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["name"] == "Alice"
        assert result["session_id"] == "sid"
        assert session == "web_sid"

    @pytest.mark.asyncio
    async def test_webhook_failure_fallback(self):
        variables = {"client_id": "c1"}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock(side_effect=Exception("fail"))
        logger = Mock(spec=SimulationLogger)
        result, session = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["name"] == DEFAULTS["name"]
        assert session is None

    @pytest.mark.asyncio
    async def test_default_value_application(self):
        variables = {}
        webhook_manager = Mock(spec=WebhookManager)
        logger = Mock(spec=SimulationLogger)
        result, _ = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        for key, value in DEFAULTS.items():
            assert result[key] == value

    @pytest.mark.asyncio
    async def test_variable_override_priority(self):
        variables = {"client_id": "c1", "NAME": "John"}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock(
            return_value={"variables": {"NAME": "Alice"}, "session_id": None}
        )
        logger = Mock(spec=SimulationLogger)
        result, _ = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["NAME"] == "Alice"
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_session_id_integration(self):
        variables = {}
        webhook_manager = Mock(spec=WebhookManager)
        logger = Mock(spec=SimulationLogger)
        result, _ = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["session_id"] == "sid"

    @pytest.mark.asyncio
    async def test_lowercase_mapping_creation(self):
        variables = {
            "NAME": "JOHN",
            "LOCATIONS": "NY",
            "DELIVERY_DAYS": "Mon",
            "PURCHASE_HISTORY": "p",
            "CURRENT_DATE": "2025-06-01",
        }
        webhook_manager = Mock(spec=WebhookManager)
        logger = Mock(spec=SimulationLogger)
        result, _ = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        assert result["name"] == "JOHN"
        assert result["locations"] == "NY"
        assert result["delivery_days"] == "Mon"
        assert result["purchase_history"] == "p"
        assert result["current_date"] == "2025-06-01"

    @pytest.mark.asyncio
    async def test_fetch_client_data_success(self):
        variables = {"client_id": "c1"}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock(
            return_value={"variables": {"NAME": "Alice"}, "session_id": "s1"}
        )
        logger = Mock(spec=SimulationLogger)
        result, session = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        webhook_manager.get_client_data.assert_awaited_once_with("c1", None)
        assert session == "s1"
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_enrich_with_scenario_purchase_history(self):
        variables = {"client_id": "c1", "scenario_purchase_history": ["p1", "p2"]}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock(
            return_value={"variables": {}, "session_id": None}
        )
        logger = Mock(spec=SimulationLogger)
        await enrich_scenario_variables(variables, "sid", webhook_manager, logger)
        webhook_manager.get_client_data.assert_awaited_once_with("c1", ["p1", "p2"])

    @pytest.mark.asyncio
    async def test_fetch_client_data_no_client_id(self):
        variables = {}
        webhook_manager = Mock(spec=WebhookManager)
        webhook_manager.get_client_data = AsyncMock()
        logger = Mock(spec=SimulationLogger)
        result, session = await enrich_scenario_variables(
            variables, "sid", webhook_manager, logger
        )
        webhook_manager.get_client_data.assert_not_called()
        assert session is None

"""Tests for ScenarioVariableEnricher."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.scenario_variable_enricher import ScenarioVariableEnricher
from src.webhook_manager import WebhookManager


@pytest.mark.asyncio
async def test_enrich_without_client_id():
    webhook = Mock(spec=WebhookManager)
    enricher = ScenarioVariableEnricher(webhook_manager=webhook)
    variables = {"NAME": "John"}
    enriched, session = await enricher.enrich_scenario_variables(variables, "sid")
    assert enriched["name"] == "John"
    assert enriched["session_id"] == "sid"
    assert session is None


@pytest.mark.asyncio
async def test_enrich_with_client_id():
    webhook = Mock(spec=WebhookManager)
    webhook.get_client_data = AsyncMock(return_value={
        "variables": {"NAME": "Alice", "CURRENT_DATE": "2024-06-01"},
        "session_id": "webhook_sid",
    })
    enricher = ScenarioVariableEnricher(webhook_manager=webhook)
    variables = {"client_id": "c1"}
    enriched, session = await enricher.enrich_scenario_variables(variables, "sid")
    assert enriched["name"] == "Alice"
    assert session == "webhook_sid"

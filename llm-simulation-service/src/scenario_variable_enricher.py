"""ScenarioVariableEnricher - Service Layer
Handles variable enrichment using WebhookManager and applies defaults."""

from typing import Dict, Any, Tuple, Optional

from src.webhook_manager import WebhookManager
from src.logging_utils import get_logger


class ScenarioVariableEnricher:
    """Service for enriching scenario variables with client data."""

    def __init__(self, webhook_manager: Optional[WebhookManager] = None) -> None:
        self.webhook_manager = webhook_manager or WebhookManager()
        self.logger = get_logger()

    async def enrich_scenario_variables(
        self, variables: Dict[str, Any], session_id: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Enrich variables with webhook data and defaults.

        Args:
            variables: raw scenario variables
            session_id: session identifier

        Returns:
            Tuple of (enriched_variables, webhook_session_id)
        """
        variables = variables.copy()
        webhook_session_id = None

        client_id = variables.get("client_id")
        if client_id:
            self.logger.log_info(f"Found client_id in scenario: {client_id}")
            client_data = await self.webhook_manager.get_client_data(client_id)
            webhook_session_id = client_data["session_id"]
            variables = self._apply_client_data_overrides(variables, client_data["variables"])
        else:
            self.logger.log_info("No client_id provided, using existing variables")

        variables["session_id"] = session_id
        variables = self._apply_default_values(variables)
        return variables, webhook_session_id

    def _apply_client_data_overrides(self, variables: Dict[str, Any], client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply webhook variables to the scenario variables."""
        variables.update(client_data)
        variables["name"] = client_data.get("NAME", variables.get("name", ""))
        variables["locations"] = client_data.get("LOCATIONS", variables.get("locations", ""))
        variables["delivery_days"] = client_data.get("DELIVERY_DAYS", variables.get("delivery_days", ""))
        variables["purchase_history"] = client_data.get("PURCHASE_HISTORY", variables.get("purchase_history", ""))
        current_date = variables.get("CURRENT_DATE") or client_data.get("CURRENT_DATE")
        if current_date:
            variables["CURRENT_DATE"] = current_date
            variables["current_date"] = current_date
        return variables

    def _apply_default_values(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Fill in defaults required for template formatting."""
        defaults = {
            "CURRENT_DATE": "2024-01-15",
            "current_date": "2024-01-15",
            "DELIVERY_DAY": "завтра",
            "delivery_days": "понедельник, среда, пятница",
            "PURCHASE_HISTORY": "История покупок отсутствует",
            "purchase_history": "История покупок отсутствует",
            "name": variables.get("CLIENT_NAME") or variables.get("NAME", "Клиент"),
            "locations": variables.get("LOCATIONS") or variables.get("LOCATION", "Адрес не указан"),
            "CLIENT_NAME": variables.get("CLIENT_NAME", "Клиент"),
            "LOCATION": variables.get("LOCATION") or variables.get("LOCATIONS", "Адрес не указан"),
        }
        for key, value in defaults.items():
            variables.setdefault(key, value)
        return variables

"""Service for scenario variable enrichment."""
from typing import Any, Dict, Optional, Tuple

from src.webhook_manager import WebhookManager
from src.logging_utils import SimulationLogger

DEFAULTS = {
    "CURRENT_DATE": "2024-01-15",
    "current_date": "2024-01-15",
    "DELIVERY_DAY": "завтра",
    "delivery_days": "понедельник, среда, пятница",
    "PURCHASE_HISTORY": "История покупок отсутствует",
    "purchase_history": "История покупок отсутствует",
    "name": "Клиент",
    "locations": "Адрес не указан",
    "CLIENT_NAME": "Клиент",
    "LOCATION": "Адрес не указан",
}

GLOBAL_INSTRUCTIONS = """
###################  GLOBAL RULES  ###################
# (copy-pasted at the beginning of each speaking agent's prompt)
#
# – General "personality": friendly, polite voice of Anna the manager.
# – General communication channel: phone; responses should sound natural,
#   short, without markers and lists, numbers and units – spelled out.
# – We speak only in Russian. Transcriptional English words = noise, ignore them.
# – Don't reveal SKU codes, don't list > five items in one phrase,
#   generalize long lists ("turkey meat, chicken...").
# – Everything already known from history can be remembered, but:
#   • real cart state is checked via get_cart, not from text;
#   • don't announce item "as added" until add_to_cart / remove_from_cart
#     is called in the same response.
# – All handoff switches are made by calling the pseudo-tool
#        handoff_to_<TargetAgent>.
######################################################  
"""

DEFAULTS["GLOBAL_INSTRUCTIONS"] = GLOBAL_INSTRUCTIONS

async def enrich_scenario_variables(
    variables: Dict[str, Any], session_id: str, webhook_manager: WebhookManager, logger: SimulationLogger
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Enrich scenario variables with webhook data and defaults."""
    variables = variables.copy()
    webhook_session_id = None
    client_id = variables.get("client_id")
    client_data = None
    if client_id:
        logger.log_info(f"Found client_id in scenario: {client_id}")
        try:
            purchase_history_codes = variables.get("scenario_purchase_history")
            client_data = await webhook_manager.get_client_data(client_id, purchase_history_codes)
            webhook_session_id = client_data.get("session_id")
            variables.update(client_data.get("variables", {}))
        except Exception as exc:  # pragma: no cover - network failure
            logger.log_error("Failed to fetch client data", exception=exc)
    _create_lowercase_mappings(variables)
    variables["session_id"] = session_id
    _apply_default_values(variables)

    logger.log_info(f"Enriched variables: {variables}")
    
    return variables, webhook_session_id

def _create_lowercase_mappings(variables: Dict[str, Any]) -> None:
    if "LOCATIONS" in variables and "locations" not in variables:
        variables["locations"] = variables["LOCATIONS"]
    if "DELIVERY_DAYS" in variables and "delivery_days" not in variables:
        variables["delivery_days"] = variables["DELIVERY_DAYS"]
    if "PURCHASE_HISTORY" in variables and "purchase_history" not in variables:
        variables["purchase_history"] = variables["PURCHASE_HISTORY"]
    if "NAME" in variables and "name" not in variables:
        variables["name"] = variables["NAME"]
    if "CURRENT_DATE" in variables and "current_date" not in variables:
        variables["current_date"] = variables["CURRENT_DATE"]

def _apply_default_values(variables: Dict[str, Any]) -> None:
    for key, default in DEFAULTS.items():
        variables.setdefault(key, default)

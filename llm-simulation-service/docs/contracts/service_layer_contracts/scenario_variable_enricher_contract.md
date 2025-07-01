# ScenarioVariableEnricher Contract

Enriches scenario variables with webhook data and default values.

## Function
`async enrich_scenario_variables(variables: Dict[str, Any], session_id: str, webhook_manager: WebhookManager, logger: SimulationLogger) -> Tuple[Dict[str, Any], Optional[str]]`

- **Returns**: tuple of enriched variables and optional webhook-provided `session_id`.

# ConversationErrorHandler Contract

Centralizes error formatting for the conversation engine.

## Constructor
`ConversationErrorHandler(logger: SimulationLogger)`

## Public Methods
- `handle_error_by_type(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]`
- `handle_api_blocked_error(error: Exception, context: ConversationContext, scenario_name: str) -> Dict[str, Any]`
- `handle_timeout_error(context: ConversationContext, scenario_name: str, timeout_sec: int) -> Dict[str, Any]`
- `handle_general_error(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]`

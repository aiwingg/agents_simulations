# WebhookManager Contract

Handles session initialization and fetching client data from external webhook endpoints.

## Constructor
`WebhookManager()`

## Public Methods
- `async get_client_variables(client_id: str) -> Dict[str, str]` – return location, delivery days and purchase history.
- `async get_client_data(client_id: str, purchase_history_codes: Optional[list] = None) -> Dict[str, Any]` – return `{variables: Dict[str, str], session_id: str | None}`. If `purchase_history_codes` is provided, it sends `{"injected_purchase_history": [...]}` in the request payload.
- `async initialize_session() -> str` – start a session via webhook or generate a UUID.
- `async validate_webhook() -> bool` – verify webhook availability.

# ToolEmulator Contract

Simulates business tools by sending HTTP requests.

## Constructor
`ToolEmulator()`

## Public Methods
- `async call_tool(tool_name: str, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any>` – dispatch to a supported tool and return its response.

### Supported Tools
- **rag_find_products** – `{query: str}` → `{products: list}`
- **remove_from_cart** – `{items: list}` → `{result: str}`
- **set_current_location** – `{address: str}` → `{result: str}`
- **get_cart** – `{}` → `{cart: list}`
- **change_delivery_date** – `{date: str}` → `{result: str}`
- **add_to_cart** – `{item: str, quantity: int}` → `{result: str}`
- **confirm_order** – `{}` → `{result: str}`

Requests include retry logic and extensive logging.

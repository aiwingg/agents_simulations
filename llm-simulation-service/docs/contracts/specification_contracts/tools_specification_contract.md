# ToolsSpecification Contract

Provides JSON schemas for conversation tools and dynamic handoff tools.

## Public Methods
- `get_available_tool_names() -> List[str]`
- `get_tool_schema(name: str) -> dict | None`
- `get_tools_by_names(names: List[str], handoffs: dict | None) -> List[dict]`
- `is_handoff_tool(name: str) -> bool`
- `get_handoff_target_agent(name: str) -> str | None`

Handoff tools are generated on the fly with parameters `reason` and `context`.

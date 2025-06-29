# AutogenToolFactory Contract

Factory for session‑isolated tools used by AutoGen agents.

## Constructor
`AutogenToolFactory(session_id: str)`

## Public Methods
- `get_tools_for_agent(tool_names: List[str]) -> List[BaseTool]`
  - Returns tool instances bound to the factory's session.
  - Unknown tool names are ignored (except handoff tools which are handled by AutoGen).

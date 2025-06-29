# AutogenToolFactory Contract

Factory for session-isolated tools used by AutoGen agents.

## Constructor
`AutogenToolFactory(session_id: str)`

## Public Methods
- `get_tools_for_agent(tool_names: List[str]) -> List[BaseTool]`
  - Returns tool instances for the given names, each bound to the session.

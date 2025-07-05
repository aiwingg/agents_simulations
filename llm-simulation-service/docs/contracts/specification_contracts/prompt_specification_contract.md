# PromptSpecification Contract

Defines agent prompts and tool assignments stored as JSON files.

## Core Classes
### `AgentPromptSpecification`
Dataclass with fields `name`, `prompt`, `tools`, `description`, `handoffs`.
- `get_tool_schemas() -> List[dict]`
- `to_dict() -> Dict[str, Any]`

### `SystemPromptSpecification`
Dataclass containing overall configuration with fields `name`, `version`, `description`, `agents: Dict[str, AgentPromptSpecification]`.
- `get_agent_prompt(agent_name: str) -> AgentPromptSpecification | None`
- `get_agent_tools(agent_name: str) -> List[dict]`
- `to_dict() -> Dict[str, Any]`
- `from_dict(data: Dict[str, Any], prompts_dir: str = None) -> SystemPromptSpecification`
- `save_to_file(filepath: str)` / `load_from_file(filepath: str)`

### `PromptSpecificationManager`
- `get_specification_path(spec_name: str) -> str`
- `load_specification(spec_name: str) -> SystemPromptSpecification`
- `get_specification_contents(spec_name: str) -> Dict[str, Any]`
- `save_specification(spec_name: str, spec_data: Dict[str, Any])`
- `list_available_specifications() -> List[Dict[str, Any]]`
- `validate_specification(specification: SystemPromptSpecification) -> List[str]`
- `create_default_specification_file()`

## JSON Structure Example
```json
{
  "name": "string",
  "version": "string",
  "description": "string",
  "agents": {
    "agent": {"name": "str", "prompt": "str or file:path", "tools": ["str"], "description": "str", "handoffs": {"target_agent": "str"}},
    "client": {"name": "str", "prompt": "str or file:path", "tools": []},
    "evaluator": {"name": "str", "prompt": "str or file:path", "tools": []}
  }
}
```
Validation ensures required agents exist and referenced tools are available.

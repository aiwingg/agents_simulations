# AutogenMASFactory Contract

Creates AutoGen `Swarm` teams from a formatted `SystemPromptSpecification` and a pre-created model client.

## Constructor
`AutogenMASFactory(session_id: str)`

## Public Methods
- `create_swarm_team(system_prompt_spec: SystemPromptSpecification, tools: List[BaseTool], model_client) -> Swarm`
  - Builds `AssistantAgent` objects with their tool lists.
  - Configures agent-to-agent handoffs only (the user is external).
  - Applies `TextMessageTermination` combined with `MaxMessageTermination` using `Config.get_max_internal_messages()`.

The factory does **not** create OpenAI clients or tools itself; these are supplied by the service layer.

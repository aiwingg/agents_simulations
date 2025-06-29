# AutogenMASFactory Contract

Creates AutoGen `Swarm` teams from prompt specifications and pre-created tools.

## Constructor
`AutogenMASFactory(session_id: str)`

## Public Methods
- `create_swarm_team(system_prompt_spec: SystemPromptSpecification, tools: List[BaseTool], model_client) -> Swarm`
  - Builds agents with tool assignments and combined termination conditions.

# ConversationEngine Contract

Implemented via the `AutogenConversationEngine` class using AutoGen's Swarm pattern.
The engine composes several helper services:
`ScenarioVariableEnricher`, `ConversationOrchestrator`, and `ConversationErrorHandler`.
These services may be injected via the constructor for testing.

## Constructor
`AutogenConversationEngine(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = 'default_prompts', variable_enricher: ScenarioVariableEnricher | None = None, orchestrator: ConversationOrchestrator | None = None, error_handler: ConversationErrorHandler | None = None)`

## Public Methods
- `run_conversation(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`
- `run_conversation_with_tools(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`

Both methods return conversation results in the same format defined by the
`ConversationEngine` contract. The `conversation_history` field is a list of
[ConversationHistoryItem](../dto/conversation_history_item.md) dictionaries. In
each entry `tool_calls` objects use the `{id, type, function:{name, arguments}}`
structure.

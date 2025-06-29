# ConversationEngine Contract

Implemented via the `AutogenConversationEngine` class using AutoGen's Swarm pattern.

## Constructor
`AutogenConversationEngine(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = 'default_prompts')`

## Public Methods
- `run_conversation(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`
- `run_conversation_with_tools(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`

Both methods return conversation results in the same format defined by the `ConversationEngine` contract.

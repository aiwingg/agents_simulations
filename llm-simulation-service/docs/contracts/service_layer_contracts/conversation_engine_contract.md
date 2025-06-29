# ConversationEngine Contract

Implemented via the `AutogenConversationEngine` class using AutoGen's Swarm pattern.

## Constructor
`AutogenConversationEngine(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = 'default_prompts')`

## Public Methods
- `run_conversation(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`
- `run_conversation_with_tools(scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any>`

Both methods return conversation results in the same format defined by the `ConversationEngine` contract.

## Implementation Highlights
- **Prompt Formatting** – scenario variables are enriched with webhook data and defaults, then passed through `SystemPromptSpecification.format_with_variables`.
- **Model Client Creation** – `AutogenModelClientFactory.create_from_openai_wrapper` produces a Braintrust wrapped `OpenAIChatCompletionClient`.
- **Tool Setup** – `AutogenToolFactory(session_id)` creates session-scoped tools for all agents.
- **Swarm Creation** – `AutogenMASFactory.create_swarm_team` builds `AssistantAgent` objects from the formatted specification, configures agent-to-agent handoffs only, and applies `TextMessageTermination | MaxMessageTermination` using `Config.get_max_internal_messages()`.
- **External User Simulation** – a dedicated `AssistantAgent` is created from the `client` prompt and interacts with the Swarm in a turn based loop (`agent → user → agent`).
- **Conversation Loop** – the engine repeatedly calls `swarm.run()` with `HandoffMessage` until natural termination, a timeout or `max_turns` is reached.
- **Result Adaptation** – messages collected from the loop are converted to the contract format via `ConversationAdapter.autogen_to_contract_format`.
- **Non‑Text Termination Handling** – if the Swarm ends with a non‑`TextMessage`, a structured failure with context is returned.

## Behavior
- Maintains identical input and output contracts to `ConversationEngine`.
- Supports tool mode and basic mode via the two public methods (the basic version delegates to the tool-enabled implementation).
- Session IDs are taken from the webhook when available; otherwise a new session is initialized.
- Internal agent exchanges are limited by `MAX_INTERNAL_MESSAGES` for cost control.

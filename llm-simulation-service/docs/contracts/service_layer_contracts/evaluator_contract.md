# ConversationEvaluator Contract

Scores conversations using a prompt-based rubric.

## Constructor
`ConversationEvaluator(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = 'default_prompts')`

## Public Methods
- `async evaluate_conversation(conversation_data: dict) -> dict`
  - **conversation_data**: expects `{session_id, scenario, conversation_history}` where `conversation_history` is a list of `{turn, speaker, content, timestamp, tool_calls?, tool_results?}` entries.
  - **Returns**: `{session_id, scenario, score, comment, evaluation_status}`.
- `async batch_evaluate_conversations(conversations: List[dict]) -> List[dict]` – evaluate multiple conversations sequentially.

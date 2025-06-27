# ConversationEngine Contract

Manages multi‑agent conversations.

## Constructor
`ConversationEngine(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = 'default_prompts')`
- `openai_wrapper` – adapter for OpenAI API
- `prompt_spec_name` – specification file to load

## Public Methods
### `async run_conversation(scenario, max_turns=None, timeout_sec=None) -> dict`
Runs a scenario and returns a dictionary with fields:
- `session_id`: str
- `scenario`: str
- `status`: "completed" or "failed"
- `total_turns`: int
- `duration_seconds`: float
- `conversation_history`: list of `{turn, speaker, content}` entries


# OpenAIWrapper Contract

Async adapter around OpenAI chat API with throttling and retry logic.

## Constructor
`OpenAIWrapper(api_key: str, model: str = None, max_retries: int = 3)`

## Public Methods
- `async chat_completion(messages, session_id, temperature=0.7, seed=None, tools=None) -> (Any, usage)`
- `async json_completion(messages, session_id, temperature=0.3, seed=None) -> (dict, usage)`

`usage` contains `prompt_tokens`, `completion_tokens`, and `total_tokens`. The wrapper also calculates approximate cost.

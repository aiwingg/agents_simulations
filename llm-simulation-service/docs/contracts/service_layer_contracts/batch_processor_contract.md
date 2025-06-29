# BatchProcessor Contract

Coordinates concurrent conversation batches.

## Constructor
`BatchProcessor(openai_api_key: str, concurrency: int = Config.CONCURRENCY)`

## Public Methods
- `create_batch_job(scenarios: List[dict], prompt_version: str = 'v1.0', prompt_spec_name: str = 'default_prompts', use_tools: bool = True) -> str`
  - **Returns**: generated batch id.
- `async run_batch(batch_id: str, progress_callback: Callable | None = None) -> dict`
  - **Returns**: summary `{batch_id, status, total_scenarios, successful_scenarios, failed_scenarios, duration_seconds, results}` where each result includes a `conversation_history` list of [ConversationHistoryItem](../dto/conversation_history_item.md). `tool_calls` dictionaries use the `{id, type, function:{name, arguments}}` format.
- `get_batch_status(batch_id: str) -> dict | None` – current progress information or `None` if not found.
- `get_batch_results(batch_id: str) -> List[dict] | None` – final conversation results or `None`.
- `cancel_batch(batch_id: str) -> bool` – attempt to stop a running batch.
- `cleanup_completed_jobs(max_age_hours: int = 24) -> int` – remove finished jobs older than `max_age_hours` and return removed count.

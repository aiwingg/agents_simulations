# ConversationAdapter Contract

Converts AutoGen messages and task results to the existing conversation result format.

The adapter coordinates several helper components:
- **AutogenMessageParser** – parses raw AutoGen messages into a structured form.
- **SpeakerDisplayNameResolver** – maps agent identifiers to display names using the prompt specification.
- **ToolFlushStateMachine** – matches tool call requests to execution events and flushes them with the next text message.
- **ParsedMessage** – DTO describing the intermediate parsed message structure.

## Static Methods
- `autogen_to_contract_format(task_result: TaskResult, session_id: str, scenario_name: str, duration: float, start_time: float | None = None, prompt_spec: Any | None = None) -> Dict[str, Any]`
- `extract_conversation_history(messages: List[BaseChatMessage], prompt_spec: Any | None = None) -> List[Dict]`
  - **Returns**: List of [ConversationHistoryItem](../dto/conversation_history_item.md).
    `tool_calls` entries follow the `{id, type, function:{name, arguments}}`
    structure described in that DTO.

These helpers keep the AutoGen engine compatible with the original contracts.

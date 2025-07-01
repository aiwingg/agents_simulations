# ParsedMessage DTO

Represents a normalized AutoGen message used internally by `ConversationAdapter`.

## Fields
- `turn` (optional) – conversation turn number when assigned
- `speaker` – identifier of the message author
- `speaker_display` (optional) – human friendly name for the speaker
- `content` – text content or placeholder for tool events
- `timestamp` – ISO formatted time the parsing occurred
- `tool_calls` (optional) – list of tool call dictionaries
- `tool_results` (optional) – list of tool execution result objects
- `is_tool_event` – `True` for tool call/request/execution messages
- `should_skip` – `True` when the message should be ignored

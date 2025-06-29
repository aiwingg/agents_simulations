# ConversationHistoryItem DTO

Represents a single message exchange in a simulated conversation. Each item is a plain
Python `dict` with the following keys:

- `turn` – sequential turn number starting at `1`
- `speaker` – message author identifier such as `agent_sales_agent` or `client`
- `speaker_display` – human friendly display name for the speaker
- `content` – text content of the message
- `timestamp` – ISO formatted timestamp of when the message was generated
- `tool_calls` *(optional)* – list of tool call dictionaries if the speaker invoked tools
- `tool_results` *(optional)* – list of results returned from executed tools

### Tool Call Structure

When present, each `tool_calls` entry is an object matching OpenAI's function
call schema:

```json
{
  "id": "call_1",
  "type": "function",
  "function": {
    "name": "set_current_location",
    "arguments": "{\"location_id\":347881}"
  }
}
```

Tool call dictionaries always contain `id`, `type` and a nested `function`
object with `name` and stringified `arguments` fields. Tool results are simply a
`List[Any]` because the exact shape depends on the tool implementation.

Example entry:
```json
{
  "turn": 1,
  "speaker": "agent_sales_agent",
  "speaker_display": "Sales Agent",
  "content": "Hello",
  "timestamp": "2025-06-26T18:07:12.088764"
}
```

The conversation engine returns `conversation_history` as `List[Dict[str, Any]]` where each
entry follows this structure.

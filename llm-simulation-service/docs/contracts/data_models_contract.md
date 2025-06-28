# Data Models Contract

Defines structures used for persistence and API responses.

## User Model
Defined in `src/models/user.py` using SQLAlchemy.

## Batch Metadata
Stored by `PersistentBatchStorage` as JSON. Fields include `batch_id`, `scenarios`, `status`, timestamps, progress counters and summary data.

## Conversation Result
Produced by `ConversationEngine.run_conversation`.

Main keys include:
- `session_id` – unique ID for the run
- `scenario` – scenario name
- `status` – one of `completed`, `failed`, `failed_api_blocked`, `timeout`
- `total_turns` – number of conversation turns
- `duration_seconds` – execution time
- `conversation_history` – list of turn objects

#### Example Result
```json
{
    "session_id": "abc123",
    "scenario": "demo",
    "status": "failed_api_blocked",
    "total_turns": 0,
    "duration_seconds": 0.1,
    "conversation_history": []
}
```

### Conversation History Structure
Each turn dictionary contains at least the following fields:
- `turn` – turn number starting at `1`
- `speaker` – identifier such as `agent_sales_agent` or `client`
- `speaker_display` – human friendly display name for the speaker
- `content` – text content of the message
- `timestamp` – ISO formatted timestamp

#### Example Entry
```json
{
    "turn": 1,
    "speaker": "agent_sales_agent",
    "speaker_display": "Sales Agent",
    "content": "Hello",
    "timestamp": "2025-06-26T18:07:12.088764"
}
```

# Data Models Contract

Defines structures used for persistence and API responses.

## User Model
Defined in `src/models/user.py` using SQLAlchemy.

## Batch Metadata
Stored by `PersistentBatchStorage` as JSON. Fields include `batch_id`, `scenarios`, `status`, timestamps, progress counters and summary data.

## Conversation Result
Produced by `ConversationEngine.run_conversation` with keys such as `session_id`, `scenario`, `status`, `total_turns`, `duration_seconds` and `conversation_history`.

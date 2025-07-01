# ToolFlushStateMachine Contract

Manages pending tool events and ensures they are flushed to the next text message.

## Public Methods
- `process_tool_event(parsed: ParsedMessage) -> Optional[Dict]`
- `process_text_message(parsed: ParsedMessage) -> Dict`
- `handle_orphaned_tools(turn_number: int) -> Optional[Dict]`

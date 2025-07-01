# AutogenMessageParser Contract

Parses AutoGen chat messages and extracts tool information.

## Public Methods
- `parse_message(message: BaseChatMessage | BaseAgentEvent) -> ParsedMessage`
  - **Returns**: [`ParsedMessage`](../dto/parsed_message_dto.md) containing `speaker`, `content`, `timestamp`, optional `tool_calls` and `tool_results`.

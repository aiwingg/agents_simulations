# LoggingUtils Contract

Provides structured logging for application events, token usage and conversations.

## Public Functions
- `get_logger(batch_id=None) -> SimulationLogger` – returns a singleton logger instance.

## SimulationLogger Methods
- `log_info(message, extra_data=None)`
- `log_error(message, exception=None, extra_data=None)`
- `log_token_usage(session_id, model, prompt_tokens, completion_tokens, total_tokens, cost_estimate=0.0)`
- `log_conversation_turn(session_id, turn_number, role, content, tool_calls=None, tool_results=None)`
- `log_conversation_complete(session_id, total_turns, final_score=None, evaluator_comment=None, status='completed')`
- `log_openai_request(session_id, request_id, model, messages, temperature, seed, tools=None, response_format=None)`
- `log_openai_response(session_id, request_id, response_content, usage)`

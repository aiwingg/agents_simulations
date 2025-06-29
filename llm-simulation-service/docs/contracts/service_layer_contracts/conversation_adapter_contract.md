# ConversationAdapter Contract

Converts AutoGen messages and task results to the existing conversation result format.

## Static Methods
- `autogen_to_contract_format(task_result: TaskResult, session_id: str, scenario_name: str, duration: float, start_time: float | None = None, prompt_spec: Any | None = None) -> Dict[str, Any]`
- `extract_conversation_history(messages: List[BaseChatMessage], prompt_spec: Any | None = None) -> List[Dict]`

These helpers keep the AutoGen engine compatible with the original contracts.

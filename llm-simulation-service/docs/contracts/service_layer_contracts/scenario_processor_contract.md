# ScenarioProcessor Contract

Processes individual scenarios with engine isolation.

## Constructor
`ScenarioProcessor(openai_wrapper: OpenAIWrapper, progress_tracker: BatchProgressTracker)`

## Public Methods
- `async process_scenario(scenario: Dict[str, Any], scenario_index: int, batch_id: str, prompt_spec_name: str, use_tools: bool) -> Dict[str, Any]`
  - **Returns**: scenario result with conversation history, evaluation scores, and status
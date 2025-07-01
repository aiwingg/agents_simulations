# BatchOrchestrator Contract

Coordinates concurrent scenario execution and result aggregation.

## Constructor
`BatchOrchestrator(resource_manager: BatchResourceManager, scenario_processor: ScenarioProcessor, progress_tracker: BatchProgressTracker)`

## Public Methods
- `async execute_batch(batch_job: BatchJob, progress_callback: Optional[callable]) -> Dict[str, Any]`
  - **Returns**: batch summary `{batch_id, status, total_scenarios, successful_scenarios, failed_scenarios, duration_seconds, results}`
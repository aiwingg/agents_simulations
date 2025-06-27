# ResultStorage Contract

Handles exporting results and generating summaries.

## Constructor
`ResultStorage()`

## Public Methods
- `save_batch_results_ndjson(batch_id, results) -> str` – write NDJSON file.
- `save_batch_results_csv(batch_id, results, prompt_version='default') -> str` – export CSV.
- `generate_summary_report(batch_id, results) -> dict` – compute stats.
- `save_summary_report(summary) -> str` – persist summary JSON.
- `load_results_from_file(path) -> List[dict]` – read results file.
- `get_cost_estimate(batch_id) -> dict` – aggregated token usage and cost.
- `list_result_files(batch_id=None) -> List[dict]` – return available exports.

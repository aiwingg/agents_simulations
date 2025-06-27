# PersistentBatchStorage Contract

Stores batch job metadata on disk.

## Constructor
`PersistentBatchStorage()`

## Public Methods
- `save_batch_metadata(data: dict)` – write JSON file under `results/batches/`.
- `load_batch_metadata(batch_id: str) -> dict | None` – read metadata from disk.
- `load_all_batches() -> dict` – load all saved batches.
- `delete_batch_metadata(batch_id: str) -> bool` – remove metadata file.
- `list_batch_ids() -> List[str]` – return sorted IDs.
- `cleanup_old_batches(max_age_days=30)` – remove outdated files.

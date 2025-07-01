import pytest
from unittest.mock import AsyncMock, patch

from src.batch_processor import BatchProcessor


class DummyStorage:
    def load_all_batches(self):
        return {}

    def save_batch_metadata(self, batch_data):
        pass


@pytest.mark.asyncio
async def test_run_batch_end_to_end():
    with patch("src.batch_processor.PersistentBatchStorage", return_value=DummyStorage()):
        processor = BatchProcessor("k", concurrency=1)

    with patch(
        "src.batch_orchestrator.BatchOrchestrator.execute_batch",
        new=AsyncMock(return_value={
            "results": [],
            "failed_scenarios": 0,
            "duration_seconds": 0,
            "status": "completed",
            "total_scenarios": 1,
            "successful_scenarios": 1,
        }),
    ):  # noqa
        batch_id = processor.create_batch_job([{"name": "sc"}])
        result = await processor.run_batch(batch_id)
        assert result["status"] == "completed"
        assert processor.active_jobs[batch_id].status == processor.active_jobs[batch_id].status.COMPLETED

@pytest.mark.asyncio
async def test_batch_status_updates():
    with patch("src.batch_processor.PersistentBatchStorage", return_value=DummyStorage()):
        processor = BatchProcessor("k", concurrency=1)

    summary = {
        "results": [],
        "failed_scenarios": 0,
        "duration_seconds": 0,
        "status": "completed",
        "total_scenarios": 1,
        "successful_scenarios": 1,
    }
    with patch("src.batch_orchestrator.BatchOrchestrator.execute_batch", new=AsyncMock(return_value=summary)):
        batch_id = processor.create_batch_job([{"name": "sc"}])
        await processor.run_batch(batch_id)
        job = processor.active_jobs[batch_id]
        assert job.status == job.status.COMPLETED
        assert job.progress_percentage == 100
        assert job.current_stage == "completed"


@pytest.mark.asyncio
async def test_progress_callback_integration():
    with patch("src.batch_processor.PersistentBatchStorage", return_value=DummyStorage()):
        processor = BatchProcessor("k", concurrency=1)

    calls = []

    async def progress_cb(completed, total):
        calls.append((completed, total))

    async def execute(self, job, cb):
        await cb(1, 1)
        return {
            "results": [],
            "failed_scenarios": 0,
            "duration_seconds": 0,
            "status": "completed",
            "total_scenarios": 1,
            "successful_scenarios": 1,
        }

    with patch("src.batch_orchestrator.BatchOrchestrator.execute_batch", new=execute):
        batch_id = processor.create_batch_job([{"name": "sc"}])
        await processor.run_batch(batch_id, progress_callback=progress_cb)
        assert calls == [(1, 1)]

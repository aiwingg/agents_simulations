import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from src.batch_orchestrator import BatchOrchestrator
from src.batch_processor import BatchJob, BatchStatus
from src.batch_resource_manager import BatchResourceManager
from src.batch_progress_tracker import BatchProgressTracker


class DummyScenarioProcessor:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def process_scenario(self, *args, **kwargs):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.asyncio
async def test_execute_batch_success():
    job = BatchJob(batch_id="b", scenarios=[{"a": 1}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    processor = DummyScenarioProcessor({"ok": True})
    orchestrator = BatchOrchestrator(BatchResourceManager(1), processor, tracker)
    summary = await orchestrator.execute_batch(job, None)
    assert summary["failed_scenarios"] == 0
    assert processor.calls == 1

class MultiResultProcessor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def process_scenario(self, *args, **kwargs):
        self.calls += 1
        result = self.results[self.calls - 1]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_execute_batch_with_failures():
    job = BatchJob(batch_id="b2", scenarios=[{"a": 1}, {"b": 2}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    processor = MultiResultProcessor([Exception("boom"), {"ok": True}])
    orchestrator = BatchOrchestrator(BatchResourceManager(2), processor, tracker)
    summary = await orchestrator.execute_batch(job, None)
    assert summary["failed_scenarios"] == 1
    assert len(summary["results"]) == 2
    assert processor.calls == 2


@pytest.mark.asyncio
async def test_result_aggregation():
    job = BatchJob(batch_id="b3", scenarios=[{"a": 1}, {"b": 2}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    results = [{"scenario_index": 0, "status": "completed"}, Exception("err")]
    processor = MultiResultProcessor(results)
    orchestrator = BatchOrchestrator(BatchResourceManager(2), processor, tracker)
    summary = await orchestrator.execute_batch(job, None)
    assert summary["results"][0]["status"] == "completed"
    assert summary["results"][1]["status"] == "failed"

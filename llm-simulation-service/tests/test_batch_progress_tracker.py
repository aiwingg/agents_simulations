import pytest
from datetime import datetime
import asyncio

from src.batch_progress_tracker import BatchProgressTracker
from src.batch_processor import BatchJob, BatchStatus


@pytest.mark.asyncio
async def test_progress_updates():
    job = BatchJob(batch_id="b", scenarios=[{}, {}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    await tracker.complete_scenario()
    assert job.completed_scenarios == 1
    assert job.progress_percentage == 50
    await tracker.fail_scenario()
    assert job.completed_scenarios == 2
    assert job.failed_scenarios == 1
    assert job.current_stage == "completed"

@pytest.mark.asyncio
async def test_complete_scenario_updates_progress():
    job = BatchJob(batch_id="c", scenarios=[{}, {}, {}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    await tracker.complete_scenario()
    assert job.completed_scenarios == 1
    assert job.failed_scenarios == 0
    assert job.progress_percentage == pytest.approx(33.33, rel=0.01)
    assert job.current_stage == "processing"


@pytest.mark.asyncio
async def test_fail_scenario_updates_progress():
    job = BatchJob(batch_id="d", scenarios=[{}, {}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    await tracker.fail_scenario()
    assert job.completed_scenarios == 1
    assert job.failed_scenarios == 1
    assert job.progress_percentage == 50
    assert job.current_stage == "processing"


@pytest.mark.asyncio
async def test_progress_calculation_complete_batch():
    job = BatchJob(batch_id="e", scenarios=[{}, {}], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)
    await tracker.complete_scenario()
    await tracker.complete_scenario()
    assert job.completed_scenarios == 2
    assert job.failed_scenarios == 0
    assert job.progress_percentage == 100
    assert job.current_stage == "completed"


@pytest.mark.asyncio
async def test_thread_safety():
    job = BatchJob(batch_id="f", scenarios=[{} for _ in range(5)], status=BatchStatus.PENDING, created_at=datetime.now())
    tracker = BatchProgressTracker(job)

    async def worker():
        await tracker.complete_scenario()

    await asyncio.gather(*(worker() for _ in range(5)))
    assert job.completed_scenarios == 5
    assert job.progress_percentage == 100
    assert job.current_stage == "completed"

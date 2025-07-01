import asyncio
import pytest
from src.batch_resource_manager import BatchResourceManager


@pytest.mark.asyncio
async def test_semaphore_acquisition():
    manager = BatchResourceManager(1)
    order = []

    async def worker(i):
        async with manager.get_semaphore():
            order.append(i)
            await asyncio.sleep(0.01)

    await asyncio.gather(worker(1), worker(2))
    assert order == [1, 2]

@pytest.mark.asyncio
async def test_concurrency_limiting():
    manager = BatchResourceManager(2)
    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        async with manager.get_semaphore():
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1

    await asyncio.gather(worker(), worker(), worker())
    assert max_active <= 2

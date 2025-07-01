"""Concurrency control for batch scenario processing."""

import asyncio


class BatchResourceManager:
    """Manage semaphore for scenario concurrency."""

    def __init__(self, concurrency: int) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)

    async def acquire_scenario_slot(self) -> None:
        """Acquire a slot for scenario processing."""
        await self._semaphore.acquire()

    def release_scenario_slot(self) -> None:
        """Release a previously acquired slot."""
        self._semaphore.release()

    def get_semaphore(self) -> asyncio.Semaphore:
        """Return the semaphore instance."""
        return self._semaphore


"""Simplified progress tracking for batch jobs."""

from __future__ import annotations

from typing import Optional
from src.logging_utils import get_logger


class BatchProgressTracker:
    """Track progress of scenario processing in a batch."""

    def __init__(self, batch_job: "BatchJob") -> None:
        self.job = batch_job
        self.logger = get_logger()

    async def complete_scenario(self) -> None:
        """Mark a scenario as completed."""
        self.job.completed_scenarios += 1
        await self._update()

    async def fail_scenario(self) -> None:
        """Mark a scenario as failed."""
        self.job.completed_scenarios += 1
        self.job.failed_scenarios += 1
        await self._update()

    async def _update(self) -> None:
        """Recalculate progress and stage description."""
        self.job.progress_percentage = self._calculate_progress_percentage()
        self._update_stage_description()

    def _calculate_progress_percentage(self) -> float:
        if self.job.total_scenarios == 0:
            return 100.0
        return (self.job.completed_scenarios / self.job.total_scenarios) * 100

    def _update_stage_description(self) -> None:
        if self.job.completed_scenarios >= self.job.total_scenarios:
            self.job.current_stage = "completed"
        else:
            self.job.current_stage = "processing"


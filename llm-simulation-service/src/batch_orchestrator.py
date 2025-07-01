"""Batch execution orchestration."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from src.logging_utils import get_logger
from src.batch_resource_manager import BatchResourceManager
from src.scenario_processor import ScenarioProcessor
from src.batch_progress_tracker import BatchProgressTracker


class BatchOrchestrator:
    """Coordinate concurrent scenario execution."""

    def __init__(
        self,
        resource_manager: BatchResourceManager,
        scenario_processor: ScenarioProcessor,
        progress_tracker: BatchProgressTracker,
    ) -> None:
        self.resource_manager = resource_manager
        self.scenario_processor = scenario_processor
        self.progress_tracker = progress_tracker
        self.logger = get_logger()

    async def execute_batch(
        self, batch_job: "BatchJob", progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """Execute all scenarios in the batch."""
        start = time.time()
        tasks = self._create_scenario_tasks(batch_job, progress_callback)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start
        successful_results, failed_count = self._process_batch_results(results, batch_job)
        return self._create_batch_summary(batch_job, successful_results, failed_count, duration)

    def _create_scenario_tasks(
        self, batch_job: "BatchJob", progress_callback: Optional[callable]
    ) -> List[asyncio.Task]:
        tasks = []
        for i, scenario in enumerate(batch_job.scenarios):
            tasks.append(
                asyncio.create_task(
                    self._run_single_scenario(i, scenario, batch_job, progress_callback)
                )
            )
        return tasks

    async def _run_single_scenario(
        self,
        scenario_index: int,
        scenario: Dict[str, Any],
        batch_job: "BatchJob",
        progress_callback: Optional[callable],
    ) -> Dict[str, Any]:
        async with self.resource_manager.get_semaphore():
            result = await self.scenario_processor.process_scenario(
                scenario,
                scenario_index,
                batch_job.batch_id,
                batch_job.prompt_spec_name,
                batch_job.use_tools,
            )
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(self.progress_tracker.job.completed_scenarios, batch_job.total_scenarios)
                else:
                    progress_callback(self.progress_tracker.job.completed_scenarios, batch_job.total_scenarios)
            return result

    def _process_batch_results(
        self, results: List[Any], batch_job: "BatchJob"
    ) -> Tuple[List[Dict[str, Any]], int]:
        successful = []
        failed = 0
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.log_error(
                    f"Scenario {idx} failed",
                    exception=result,
                    extra_data={"batch_id": batch_job.batch_id},
                )
                failed += 1
                failed_result = {
                    "scenario_index": idx,
                    "scenario": batch_job.scenarios[idx].get("name", f"scenario_{idx}"),
                    "status": "failed",
                    "error": str(result),
                    "session_id": None,
                    "score": 1,
                    "comment": f"Ошибка обработки: {str(result)}",
                }
                successful.append(failed_result)
            else:
                successful.append(result)
        return successful, failed

    def _create_batch_summary(
        self,
        batch_job: "BatchJob",
        successful_results: List[Dict[str, Any]],
        failed_count: int,
        duration: float,
    ) -> Dict[str, Any]:
        return {
            "batch_id": batch_job.batch_id,
            "status": "completed",
            "total_scenarios": batch_job.total_scenarios,
            "successful_scenarios": batch_job.total_scenarios - failed_count,
            "failed_scenarios": failed_count,
            "duration_seconds": duration,
            "results": successful_results,
        }


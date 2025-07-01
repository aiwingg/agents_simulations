"""
Batch processing system for parallel conversation simulation
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger
from src.persistent_storage import PersistentBatchStorage
from src.batch_resource_manager import BatchResourceManager
from src.batch_progress_tracker import BatchProgressTracker
from src.scenario_processor import ScenarioProcessor
from src.batch_orchestrator import BatchOrchestrator


class BatchStatus(Enum):
    """Batch processing status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Batch job data structure"""

    batch_id: str
    scenarios: List[Dict[str, Any]]
    status: BatchStatus
    created_at: datetime
    prompt_version: str = "v1.0"
    prompt_spec_name: str = "default_prompts"
    use_tools: bool = True
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_scenarios: int = 0
    completed_scenarios: int = 0
    failed_scenarios: int = 0
    progress_percentage: float = 0.0
    results: List[Dict[str, Any]] = None
    error_message: Optional[str] = None
    current_stage: str = "pending"  # Track what's currently happening
    scenarios_in_progress: int = 0  # Track how many scenarios are actively processing

    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.total_scenarios == 0:
            self.total_scenarios = len(self.scenarios)


class BatchProcessor:
    """Manages batch processing of conversation simulations"""

    def __init__(self, openai_api_key: str, concurrency: Optional[int] = None):
        self.concurrency = concurrency or Config.CONCURRENCY
        self.logger = get_logger()

        # Resource manager for concurrency
        self.resource_manager = BatchResourceManager(self.concurrency)

        # Initialize components
        self.openai_wrapper = OpenAIWrapper(openai_api_key)

        # Initialize persistent storage
        self.persistent_storage = PersistentBatchStorage()

        # Active batch jobs
        self.active_jobs: Dict[str, BatchJob] = {}

        # Load existing batches from storage
        self._load_existing_batches()

        self.logger.log_info(f"BatchProcessor initialized with concurrency: {self.concurrency}")

    def _load_existing_batches(self):
        """Load existing batches from persistent storage"""
        try:
            stored_batches = self.persistent_storage.load_all_batches()

            for batch_id, batch_data in stored_batches.items():
                # Recreate BatchJob from stored data
                batch_job = BatchJob(
                    batch_id=batch_data["batch_id"],
                    scenarios=batch_data.get("scenarios", []),
                    status=BatchStatus(batch_data["status"]),
                    created_at=batch_data["created_at"],
                    prompt_version=batch_data.get("prompt_version", "v1.0"),
                    prompt_spec_name=batch_data.get("prompt_spec_name", "default_prompts"),
                    use_tools=batch_data.get("use_tools", True),
                    started_at=batch_data.get("started_at"),
                    completed_at=batch_data.get("completed_at"),
                    total_scenarios=batch_data.get("total_scenarios", 0),
                    completed_scenarios=batch_data.get("completed_scenarios", 0),
                    failed_scenarios=batch_data.get("failed_scenarios", 0),
                    progress_percentage=batch_data.get("progress_percentage", 0.0),
                    results=batch_data.get("results", []),
                    error_message=batch_data.get("error_message"),
                    current_stage=batch_data.get("current_stage", "pending"),
                    scenarios_in_progress=batch_data.get("scenarios_in_progress", 0),
                )

                self.active_jobs[batch_id] = batch_job

            if stored_batches:
                self.logger.log_info(f"Loaded {len(stored_batches)} existing batches from storage")

        except Exception as e:
            self.logger.log_error("Failed to load existing batches", exception=e)

    def _save_batch_to_storage(self, batch_job: BatchJob):
        """Save batch job to persistent storage"""
        try:
            # Convert to dict manually to handle enum serialization
            batch_data = {
                "batch_id": batch_job.batch_id,
                "scenarios": batch_job.scenarios,
                "status": batch_job.status.value,  # Convert enum to string
                "created_at": batch_job.created_at,
                "prompt_version": batch_job.prompt_version,
                "prompt_spec_name": batch_job.prompt_spec_name,
                "use_tools": batch_job.use_tools,
                "started_at": batch_job.started_at,
                "completed_at": batch_job.completed_at,
                "total_scenarios": batch_job.total_scenarios,
                "completed_scenarios": batch_job.completed_scenarios,
                "failed_scenarios": batch_job.failed_scenarios,
                "progress_percentage": batch_job.progress_percentage,
                "results": batch_job.results,
                "error_message": batch_job.error_message,
                "current_stage": batch_job.current_stage,
                "scenarios_in_progress": batch_job.scenarios_in_progress,
            }
            self.persistent_storage.save_batch_metadata(batch_data)
        except Exception as e:
            self.logger.log_error(
                f"Failed to save batch to storage", exception=e, extra_data={"batch_id": batch_job.batch_id}
            )

    def create_batch_job(
        self,
        scenarios: List[Dict[str, Any]],
        prompt_version: str = "v1.0",
        use_tools: bool = True,
        prompt_spec_name: str = "default_prompts",
    ) -> str:
        """Create a new batch job"""
        batch_id = str(uuid.uuid4())

        batch_job = BatchJob(
            batch_id=batch_id,
            scenarios=scenarios,
            status=BatchStatus.PENDING,
            created_at=datetime.now(),
            prompt_version=prompt_version,
            prompt_spec_name=prompt_spec_name,
            use_tools=use_tools,
            total_scenarios=len(scenarios),
        )

        self.active_jobs[batch_id] = batch_job

        # Save to persistent storage
        self._save_batch_to_storage(batch_job)

        self.logger.log_info(
            f"Created batch job",
            extra_data={"batch_id": batch_id, "total_scenarios": len(scenarios), "prompt_spec_name": prompt_spec_name},
        )

        return batch_id

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch job"""
        if batch_id not in self.active_jobs:
            return None

        job = self.active_jobs[batch_id]
        return {
            "batch_id": batch_id,
            "status": job.status.value,
            "prompt_version": job.prompt_version,
            "prompt_spec_name": job.prompt_spec_name,
            "use_tools": job.use_tools,
            "progress": job.progress_percentage,
            "total_scenarios": job.total_scenarios,
            "completed_scenarios": job.completed_scenarios,
            "failed_scenarios": job.failed_scenarios,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "current_stage": job.current_stage,
            "scenarios_in_progress": job.scenarios_in_progress,
        }

    def get_batch_results(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get results of a completed batch job"""
        if batch_id not in self.active_jobs:
            return None

        job = self.active_jobs[batch_id]
        return job.results

    async def run_batch(self, batch_id: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run a batch job using the new orchestrator."""

        job = self._validate_and_prepare_batch(batch_id)

        progress_tracker = BatchProgressTracker(job)
        scenario_processor = ScenarioProcessor(self.openai_wrapper, progress_tracker)
        orchestrator = BatchOrchestrator(self.resource_manager, scenario_processor, progress_tracker)

        try:
            result = await orchestrator.execute_batch(job, progress_callback)
            self._finalize_successful_batch(job, result)
            return result
        except Exception as exc:
            self._finalize_failed_batch(job, exc)
            raise

    def _validate_and_prepare_batch(self, batch_id: str) -> BatchJob:
        """Validate job existence and set initial running state."""
        if batch_id not in self.active_jobs:
            raise ValueError(f"Batch job {batch_id} not found")

        job = self.active_jobs[batch_id]
        if job.status != BatchStatus.PENDING:
            raise ValueError(f"Batch job {batch_id} is not in pending status")

        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now()
        job.current_stage = "processing"
        self._save_batch_to_storage(job)
        return job

    def _finalize_successful_batch(self, job: BatchJob, result: Dict[str, Any]) -> None:
        """Persist successful batch outcome."""
        job.results = result["results"]
        job.failed_scenarios = result["failed_scenarios"]
        job.completed_scenarios = job.total_scenarios
        job.progress_percentage = 100.0
        job.status = BatchStatus.COMPLETED
        job.completed_at = datetime.now()
        job.current_stage = "completed"
        self._save_batch_to_storage(job)

    def _finalize_failed_batch(self, job: BatchJob, exc: Exception) -> None:
        """Persist failure details."""
        job.status = BatchStatus.FAILED
        job.error_message = str(exc)
        job.completed_at = datetime.now()
        job.current_stage = "failed"
        self._save_batch_to_storage(job)


    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch job"""
        if batch_id not in self.active_jobs:
            return False

        job = self.active_jobs[batch_id]
        if job.status == BatchStatus.RUNNING:
            job.status = BatchStatus.CANCELLED
            job.completed_at = datetime.now()
            self.logger.log_info(f"Cancelled batch job", extra_data={"batch_id": batch_id})
            return True

        return False

    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        current_time = datetime.now()
        jobs_to_remove = []

        for batch_id, job in self.active_jobs.items():
            if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
                if job.completed_at and (current_time - job.completed_at).total_seconds() > max_age_hours * 3600:
                    jobs_to_remove.append(batch_id)

        for batch_id in jobs_to_remove:
            del self.active_jobs[batch_id]
            self.logger.log_info(f"Cleaned up old batch job", extra_data={"batch_id": batch_id})

        return len(jobs_to_remove)

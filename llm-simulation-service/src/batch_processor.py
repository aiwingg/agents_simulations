"""
Batch processing system for parallel conversation simulation
"""
import asyncio
import uuid
import json
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger
from src.persistent_storage import PersistentBatchStorage

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
        self._semaphore = None  # Changed from direct initialization
        self._semaphore_lock = threading.Lock()  # Thread-safe semaphore access
        self.logger = get_logger()
        
        # Initialize components
        self.openai_wrapper = OpenAIWrapper(openai_api_key)
        
        # Initialize persistent storage
        self.persistent_storage = PersistentBatchStorage()
        
        # Active batch jobs
        self.active_jobs: Dict[str, BatchJob] = {}
        
        # Load existing batches from storage
        self._load_existing_batches()
        
        self.logger.log_info(f"BatchProcessor initialized with concurrency: {self.concurrency}")
    
    @property
    def semaphore(self):
        """Thread-safe lazy initialization of semaphore to avoid event loop issues"""
        with self._semaphore_lock:
            try:
                # Try to get current event loop
                current_loop = asyncio.get_running_loop()
                
                # If we have a semaphore, check if it's bound to the current loop
                if self._semaphore is not None:
                    try:
                        # Try to access the semaphore's loop
                        # If it fails, we need to recreate it
                        self._semaphore._get_loop()
                        return self._semaphore
                    except RuntimeError:
                        # Semaphore is bound to a different loop, recreate it
                        self.logger.log_info("Recreating semaphore for new event loop")
                        self._semaphore = None
                
                # Create new semaphore for current loop
                if self._semaphore is None:
                    self._semaphore = asyncio.Semaphore(self.concurrency)
                    self.logger.log_info(f"Created new semaphore with concurrency: {self.concurrency}")
                
                return self._semaphore
                
            except RuntimeError:
                # No event loop running, create semaphore anyway (will be recreated if needed)
                if self._semaphore is None:
                    self._semaphore = asyncio.Semaphore(self.concurrency)
                return self._semaphore
    
    def _load_existing_batches(self):
        """Load existing batches from persistent storage"""
        try:
            stored_batches = self.persistent_storage.load_all_batches()
            
            for batch_id, batch_data in stored_batches.items():
                # Recreate BatchJob from stored data
                batch_job = BatchJob(
                    batch_id=batch_data['batch_id'],
                    scenarios=batch_data.get('scenarios', []),
                    status=BatchStatus(batch_data['status']),
                    created_at=batch_data['created_at'],
                    prompt_version=batch_data.get('prompt_version', 'v1.0'),
                    prompt_spec_name=batch_data.get('prompt_spec_name', 'default_prompts'),
                    use_tools=batch_data.get('use_tools', True),
                    started_at=batch_data.get('started_at'),
                    completed_at=batch_data.get('completed_at'),
                    total_scenarios=batch_data.get('total_scenarios', 0),
                    completed_scenarios=batch_data.get('completed_scenarios', 0),
                    failed_scenarios=batch_data.get('failed_scenarios', 0),
                    progress_percentage=batch_data.get('progress_percentage', 0.0),
                    results=batch_data.get('results', []),
                    error_message=batch_data.get('error_message'),
                    current_stage=batch_data.get('current_stage', "pending"),
                    scenarios_in_progress=batch_data.get('scenarios_in_progress', 0)
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
                'batch_id': batch_job.batch_id,
                'scenarios': batch_job.scenarios,
                'status': batch_job.status.value,  # Convert enum to string
                'created_at': batch_job.created_at,
                'prompt_version': batch_job.prompt_version,
                'prompt_spec_name': batch_job.prompt_spec_name,
                'use_tools': batch_job.use_tools,
                'started_at': batch_job.started_at,
                'completed_at': batch_job.completed_at,
                'total_scenarios': batch_job.total_scenarios,
                'completed_scenarios': batch_job.completed_scenarios,
                'failed_scenarios': batch_job.failed_scenarios,
                'progress_percentage': batch_job.progress_percentage,
                'results': batch_job.results,
                'error_message': batch_job.error_message,
                'current_stage': batch_job.current_stage,
                'scenarios_in_progress': batch_job.scenarios_in_progress
            }
            self.persistent_storage.save_batch_metadata(batch_data)
        except Exception as e:
            self.logger.log_error(f"Failed to save batch to storage", exception=e, extra_data={'batch_id': batch_job.batch_id})
    
    def create_batch_job(self, scenarios: List[Dict[str, Any]], prompt_version: str = "v1.0", 
                        use_tools: bool = True, prompt_spec_name: str = "default_prompts") -> str:
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
            total_scenarios=len(scenarios)
        )
        
        self.active_jobs[batch_id] = batch_job
        
        # Save to persistent storage
        self._save_batch_to_storage(batch_job)
        
        self.logger.log_info(f"Created batch job", extra_data={
            'batch_id': batch_id,
            'total_scenarios': len(scenarios),
            'prompt_spec_name': prompt_spec_name
        })
        
        return batch_id
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch job"""
        if batch_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[batch_id]
        return {
            'batch_id': batch_id,
            'status': job.status.value,
            'prompt_version': job.prompt_version,
            'prompt_spec_name': job.prompt_spec_name,
            'use_tools': job.use_tools,
            'progress': job.progress_percentage,
            'total_scenarios': job.total_scenarios,
            'completed_scenarios': job.completed_scenarios,
            'failed_scenarios': job.failed_scenarios,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message,
            'current_stage': job.current_stage,
            'scenarios_in_progress': job.scenarios_in_progress
        }
    
    def get_batch_results(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get results of a completed batch job"""
        if batch_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[batch_id]
        return job.results
    
    async def run_batch(self, batch_id: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run a batch job with parallel processing"""
        
        if batch_id not in self.active_jobs:
            raise ValueError(f"Batch job {batch_id} not found")
        
        job = self.active_jobs[batch_id]
        
        if job.status != BatchStatus.PENDING:
            raise ValueError(f"Batch job {batch_id} is not in pending status")
        
        # Load required classes lazily to avoid circular imports
        from src.autogen_conversation_engine import AutogenConversationEngine
        from src.evaluator import ConversationEvaluator

        self.logger.log_info(
            f"Using prompt specification {job.prompt_spec_name} for batch", extra_data={
                'batch_id': batch_id
            }
        )
        
        # Update job status
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now()
        job.current_stage = "initializing"
        job.scenarios_in_progress = 0
        
        # Create progress tracking lock for thread safety
        progress_lock = asyncio.Lock()
        
        # Save updated state to persistent storage
        self._save_batch_to_storage(job)
        
        self.logger.log_info(f"Starting batch processing", extra_data={
            'batch_id': batch_id,
            'total_scenarios': job.total_scenarios,
            'concurrency': self.concurrency,
            'prompt_spec_name': job.prompt_spec_name
        })
        
        try:
            # Update stage to processing
            job.current_stage = "processing_scenarios"
            self._save_batch_to_storage(job)
            
            # Create tasks for all scenarios
            tasks = []
            for i, scenario in enumerate(job.scenarios):
                task = self._process_single_scenario(
                    scenario=scenario,
                    scenario_index=i,
                    batch_id=batch_id,
                    progress_callback=progress_callback,
                    progress_lock=progress_lock
                )
                tasks.append(task)
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update stage to finalizing
            job.current_stage = "finalizing"
            job.scenarios_in_progress = 0
            self._save_batch_to_storage(job)
            
            # Process results
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.log_error(f"Scenario {i} failed", exception=result, extra_data={'batch_id': batch_id})
                    failed_count += 1
                    
                    # Add failed result
                    failed_result = {
                        'scenario_index': i,
                        'scenario': job.scenarios[i].get('name', f'scenario_{i}'),
                        'status': 'failed',
                        'error': str(result),
                        'session_id': None,
                        'score': 1,
                        'comment': f"Ошибка обработки: {str(result)}"
                    }
                    successful_results.append(failed_result)
                else:
                    successful_results.append(result)
            
            # Update job with results
            job.results = successful_results
            job.completed_scenarios = len(successful_results)
            job.failed_scenarios = failed_count
            job.progress_percentage = 100.0
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.now()
            job.current_stage = "completed"
            job.scenarios_in_progress = 0
            
            # Save updated state to persistent storage
            self._save_batch_to_storage(job)
            
            duration = (job.completed_at - job.started_at).total_seconds()
            
            self.logger.log_info(f"Batch processing completed", extra_data={
                'batch_id': batch_id,
                'total_scenarios': job.total_scenarios,
                'successful': job.completed_scenarios - failed_count,
                'failed': failed_count,
                'duration_seconds': duration
            })
            
            return {
                'batch_id': batch_id,
                'status': 'completed',
                'total_scenarios': job.total_scenarios,
                'successful_scenarios': job.completed_scenarios - failed_count,
                'failed_scenarios': failed_count,
                'duration_seconds': duration,
                'results': successful_results
            }
            
        except Exception as e:
            # Update job with error
            job.status = BatchStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            job.current_stage = "failed"
            job.scenarios_in_progress = 0
            
            self.logger.log_error(f"Batch processing failed", exception=e, extra_data={'batch_id': batch_id})
            
            raise e
    
    async def _process_single_scenario(self, scenario: Dict[str, Any], scenario_index: int,
                                     batch_id: str, progress_callback: Optional[Callable] = None,
                                     progress_lock: asyncio.Lock = None) -> Dict[str, Any]:
        """Process a single scenario with conversation and evaluation"""

        async with self.semaphore:  # Limit concurrency
            try:
                scenario_name = scenario.get('name', f'scenario_{scenario_index}')
                
                self.logger.log_info(f"Processing scenario {scenario_index}: {scenario_name}", extra_data={'batch_id': batch_id})
                
                # Update progress: Scenario started
                await self._update_sub_progress(batch_id, scenario_index, "started", progress_lock)
                
                # Run conversation (with or without tools based on batch setting)
                job = self.active_jobs[batch_id]

                # Create isolated conversation engine and evaluator per scenario
                from src.autogen_conversation_engine import AutogenConversationEngine
                from src.evaluator import ConversationEvaluator

                conversation_engine = AutogenConversationEngine(self.openai_wrapper, job.prompt_spec_name)
                evaluator = ConversationEvaluator(self.openai_wrapper, job.prompt_spec_name)

                self.logger.log_info(
                    "Initialized new ConversationEngine for scenario",
                    extra_data={'batch_id': batch_id, 'scenario_index': scenario_index}
                )

                # Update progress: Conversation in progress
                await self._update_sub_progress(batch_id, scenario_index, "conversation", progress_lock)

                if job.use_tools:
                    conversation_result = await conversation_engine.run_conversation_with_tools(scenario)
                else:
                    conversation_result = await conversation_engine.run_conversation(scenario)

                # Update progress: Evaluation in progress
                await self._update_sub_progress(batch_id, scenario_index, "evaluation", progress_lock)

                # Evaluate conversation if successful
                if conversation_result.get('status') == 'completed':
                    evaluation_result = await evaluator.evaluate_conversation(conversation_result)
                    
                    # Combine results
                    combined_result = {
                        'scenario_index': scenario_index,
                        'scenario': scenario_name,
                        'session_id': conversation_result.get('session_id'),
                        'status': 'completed',
                        'total_turns': conversation_result.get('total_turns'),
                        'duration_seconds': conversation_result.get('duration_seconds'),
                        'score': evaluation_result.get('score'),
                        'comment': evaluation_result.get('comment'),
                        'evaluation_status': evaluation_result.get('evaluation_status'),
                        'start_time': conversation_result.get('start_time'),
                        'end_time': conversation_result.get('end_time'),
                        'conversation_history': conversation_result.get('conversation_history')
                    }
                elif conversation_result.get('status') == 'failed_api_blocked':
                    # Special handling for API blocked scenarios - treat as partial success
                    combined_result = {
                        'scenario_index': scenario_index,
                        'scenario': scenario_name,
                        'session_id': conversation_result.get('session_id'),
                        'status': 'failed_api_blocked',
                        'error': conversation_result.get('error'),
                        'total_turns': conversation_result.get('total_turns', 0),
                        'duration_seconds': conversation_result.get('duration_seconds', 0),
                        'score': 2 if conversation_result.get('partial_completion') else 1,  # Better score if partially completed
                        'comment': f"API заблокирован (географические ограничения). Сделано ходов: {conversation_result.get('total_turns', 0)}",
                        'conversation_history': conversation_result.get('conversation_history', []),
                        'graceful_degradation': True,
                        'partial_completion': conversation_result.get('partial_completion', False)
                    }
                elif conversation_result.get('status') == 'timeout':
                    # Conversation timed out but may contain partial history
                    # Still run evaluation to score the partial conversation
                    evaluation_result = await evaluator.evaluate_conversation(conversation_result)

                    combined_result = {
                        'scenario_index': scenario_index,
                        'scenario': scenario_name,
                        'session_id': conversation_result.get('session_id'),
                        'status': 'timeout',
                        'error': conversation_result.get('error'),
                        'total_turns': conversation_result.get('total_turns', 0),
                        'duration_seconds': conversation_result.get('duration_seconds'),
                        'score': evaluation_result.get('score'),
                        'comment': evaluation_result.get('comment'),
                        'evaluation_status': evaluation_result.get('evaluation_status'),
                        'start_time': conversation_result.get('start_time'),
                        'end_time': conversation_result.get('end_time'),
                        'conversation_history': conversation_result.get('conversation_history', [])
                    }
                else:
                    # Conversation failed
                    combined_result = {
                        'scenario_index': scenario_index,
                        'scenario': scenario_name,
                        'session_id': conversation_result.get('session_id'),
                        'status': 'failed',
                        'error': conversation_result.get('error'),
                        'total_turns': conversation_result.get('total_turns', 0),
                        'score': 1,
                        'comment': f"Разговор не завершен: {conversation_result.get('error', 'неизвестная ошибка')}"
                    }
                
                # Update progress: Scenario completed
                await self._update_sub_progress(batch_id, scenario_index, "completed", progress_lock)
                
                # Update progress
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(scenario_index + 1, job.total_scenarios)
                    else:
                        progress_callback(scenario_index + 1, job.total_scenarios)
                
                # Update progress in batch job and save to storage (thread-safe)
                if progress_lock:
                    async with progress_lock:
                        await self._update_progress(batch_id)  # Increment by 1
                        self._save_batch_to_storage(self.active_jobs[batch_id])
                else:
                    await self._update_progress(batch_id)  # Increment by 1
                    self._save_batch_to_storage(self.active_jobs[batch_id])
                
                self.logger.log_info(f"Completed scenario {scenario_index}: {scenario_name}", extra_data={
                    'batch_id': batch_id,
                    'score': combined_result.get('score'),
                    'status': combined_result.get('status')
                })
                
                return combined_result
                
            except Exception as e:
                # Update progress: Scenario failed
                await self._update_sub_progress(batch_id, scenario_index, "failed", progress_lock)
                
                # Enhanced error logging with debug information
                error_context = {
                    'batch_id': batch_id,
                    'scenario_index': scenario_index,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'scenario_name': scenario.get('name', 'unknown'),
                    'conversation_engine_initialized': True,
                    'evaluator_initialized': True
                }
                self.logger.log_error(f"Failed to process scenario {scenario_index}", exception=e, extra_data=error_context)
                raise e
    
    async def _update_sub_progress(self, batch_id: str, scenario_index: int, stage: str, progress_lock: asyncio.Lock = None):
        """Update sub-progress for individual scenario stages"""
        stage_weights = {
            "started": 0.1,      # 10% of scenario completion
            "conversation": 0.4, # 40% of scenario completion  
            "evaluation": 0.8,   # 80% of scenario completion
            "completed": 1.0,    # 100% of scenario completion
            "failed": 1.0        # Count as completed for progress purposes
        }
        
        if batch_id not in self.active_jobs:
            return
            
        weight = stage_weights.get(stage, 0.0)
        
        # Calculate partial progress for this scenario
        scenario_progress = weight / self.active_jobs[batch_id].total_scenarios * 100.0
        
        # Use lock to prevent race conditions
        if progress_lock:
            async with progress_lock:
                await self._update_detailed_progress(batch_id, scenario_index, stage, scenario_progress)
        else:
            await self._update_detailed_progress(batch_id, scenario_index, stage, scenario_progress)
    
    async def _update_detailed_progress(self, batch_id: str, scenario_index: int, stage: str, additional_progress: float):
        """Thread-safe detailed progress update"""
        if batch_id in self.active_jobs:
            job = self.active_jobs[batch_id]
            old_progress = job.progress_percentage
            old_in_progress = job.scenarios_in_progress
            
            # Update scenarios in progress counter
            if stage == "started":
                job.scenarios_in_progress += 1
            elif stage in ["completed", "failed"]:
                job.scenarios_in_progress = max(0, job.scenarios_in_progress - 1)
            
            # Add the partial progress
            job.progress_percentage = min(job.progress_percentage + additional_progress, 100.0)
            
            # Update current stage description based on activity
            if job.scenarios_in_progress > 0:
                job.current_stage = f"processing ({job.scenarios_in_progress} active)"
            elif job.completed_scenarios == 0:
                job.current_stage = "starting"
            elif job.completed_scenarios == job.total_scenarios:
                job.current_stage = "completed"
            else:
                job.current_stage = "processing"
            
            # Log detailed progress for debugging
            self.logger.log_info(f"Sub-progress updated for batch {batch_id}", extra_data={
                'scenario_index': scenario_index,
                'stage': stage,
                'old_progress': old_progress,
                'new_progress': job.progress_percentage,
                'additional_progress': additional_progress,
                'completed_scenarios': job.completed_scenarios,
                'total_scenarios': job.total_scenarios,
                'scenarios_in_progress': job.scenarios_in_progress,
                'current_stage': job.current_stage
            })
            
            # Save state more frequently for progress visibility
            self._save_batch_to_storage(job)

    async def _update_progress(self, batch_id: str, completed_count: int = None):
        """Update batch job progress - now more reliable with detailed tracking"""
        if batch_id in self.active_jobs:
            job = self.active_jobs[batch_id]
            old_progress = job.progress_percentage
            old_completed = job.completed_scenarios
            
            if completed_count is not None:
                job.completed_scenarios = completed_count
            else:
                # If no count provided, increment by 1
                job.completed_scenarios += 1
            
            # Recalculate progress based on completed scenarios
            # This ensures progress is always accurate regardless of sub-progress
            base_progress = (job.completed_scenarios / job.total_scenarios) * 100.0
            
            # Keep the higher of the two (in case sub-progress is ahead)
            job.progress_percentage = max(base_progress, job.progress_percentage)
            
            # Log progress update for debugging
            self.logger.log_info(f"Progress updated for batch {batch_id}", extra_data={
                'old_progress': old_progress,
                'new_progress': job.progress_percentage,
                'old_completed_scenarios': old_completed,
                'new_completed_scenarios': job.completed_scenarios,
                'total_scenarios': job.total_scenarios,
                'base_progress': base_progress
            })
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch job"""
        if batch_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[batch_id]
        if job.status == BatchStatus.RUNNING:
            job.status = BatchStatus.CANCELLED
            job.completed_at = datetime.now()
            self.logger.log_info(f"Cancelled batch job", extra_data={'batch_id': batch_id})
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
            self.logger.log_info(f"Cleaned up old batch job", extra_data={'batch_id': batch_id})
        
        return len(jobs_to_remove)


"""Enhanced execution engine with full persistence support."""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy_execution import JobStatus
from app.services.persistence_service import PersistenceService
from biomapper.core.models import StrategyExecutionContext
from biomapper.core.strategy_actions.base import BaseStrategyAction

logger = logging.getLogger(__name__)


class PersistentExecutionEngine:
    """
    Execution engine with comprehensive persistence support.
    
    Features:
    - Automatic checkpointing
    - Job recovery from failures
    - Progress tracking
    - Resource monitoring
    - Event streaming
    """
    
    def __init__(
        self,
        persistence: PersistenceService,
        action_registry: Dict[str, type[BaseStrategyAction]]
    ):
        self.persistence = persistence
        self.action_registry = action_registry
        self.running_jobs: Dict[uuid.UUID, asyncio.Task] = {}
    
    async def execute_strategy(
        self,
        job_id: uuid.UUID,
        strategy: Dict[str, Any],
        context: Optional[StrategyExecutionContext] = None,
        resume_from_step: Optional[int] = None,
        resume_from_checkpoint: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute strategy with full persistence support.
        
        Args:
            job_id: Unique job identifier
            strategy: Strategy configuration
            context: Optional execution context
            resume_from_step: Step index to resume from
            resume_from_checkpoint: Checkpoint ID to resume from
        
        Returns:
            Execution results with context and metrics
        """
        try:
            # Load job
            job = await self.persistence.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Handle resume scenarios
            if resume_from_checkpoint:
                checkpoint_data = await self.persistence.restore_checkpoint(resume_from_checkpoint)
                context = checkpoint_data["context"]
                resume_from_step = checkpoint_data["step_index"] + 1
                logger.info(f"Resuming job {job_id} from checkpoint at step {resume_from_step}")
            elif resume_from_step is not None:
                # Try to find a checkpoint near the resume point
                checkpoints = await self.persistence.list_checkpoints(job_id)
                best_checkpoint = self._find_best_checkpoint(checkpoints, resume_from_step)
                if best_checkpoint:
                    checkpoint_data = await self.persistence.restore_checkpoint(best_checkpoint.id)
                    context = checkpoint_data["context"]
                    logger.info(f"Loaded checkpoint at step {best_checkpoint.step_index}")
            
            # Initialize context if new execution
            if not context:
                context = StrategyExecutionContext()
                context.custom_action_data["job_id"] = str(job_id)
                context.custom_action_data["strategy_name"] = strategy.get("name", "unknown")
            
            # Update job status to running
            await self.persistence.update_job_status(
                job_id,
                JobStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            
            # Execute steps
            steps = strategy.get("steps", [])
            start_index = resume_from_step or 0
            
            for i, step in enumerate(steps[start_index:], start=start_index):
                try:
                    # Check if job was cancelled
                    job = await self.persistence.get_job(job_id)
                    if job.status == JobStatus.CANCELLED:
                        logger.info(f"Job {job_id} was cancelled")
                        break
                    
                    # Record step start
                    await self.persistence.record_step_start(
                        job_id,
                        i,
                        step.get("name", f"Step {i}"),
                        step.get("action", {}).get("type", "unknown"),
                        step.get("action", {}).get("params", {})
                    )
                    
                    # Create checkpoint before critical steps
                    if self._should_checkpoint_before(step, strategy):
                        await self.persistence.create_checkpoint(
                            job_id, i, context, "before_step",
                            description=f"Before {step.get('name', f'Step {i}')}"
                        )
                    
                    # Execute action
                    action_type = step.get("action", {}).get("type")
                    if not action_type:
                        raise ValueError(f"No action type specified for step {i}")
                    
                    action_class = self.action_registry.get(action_type)
                    if not action_class:
                        raise ValueError(f"Unknown action type: {action_type}")
                    
                    action = action_class()
                    params = step.get("action", {}).get("params", {})
                    
                    # Monitor resources during execution
                    import psutil
                    process = psutil.Process()
                    memory_before = process.memory_info().rss / 1024 / 1024  # MB
                    
                    # Execute the action
                    result = await action.execute(params, context)
                    
                    # Calculate resource usage
                    memory_after = process.memory_info().rss / 1024 / 1024  # MB
                    memory_used = memory_after - memory_before
                    
                    # Extract metrics from result
                    metrics = {
                        "memory_used_mb": int(memory_used),
                        "records_processed": result.get("records_processed", 0),
                        "records_matched": result.get("records_matched", 0),
                        "confidence_score": result.get("confidence_score")
                    }
                    
                    # Handle large results
                    output_size = len(str(result))
                    if output_size > 1024 * 100:  # > 100KB
                        # Store externally and keep reference
                        await self.persistence.store_result(
                            job_id, i, "step_output", result
                        )
                        context.custom_action_data[f"step_{i}_output_ref"] = f"stored:{job_id}:{i}:step_output"
                        # Store summary in context
                        context.custom_action_data[f"step_{i}_output_summary"] = {
                            "stored": True,
                            "size_bytes": output_size,
                            "records": result.get("records_processed", 0)
                        }
                    else:
                        # Store in context
                        context.custom_action_data[f"step_{i}_output"] = result
                    
                    # Record completion
                    await self.persistence.record_step_completion(
                        job_id, i, result, metrics
                    )
                    
                    # Create checkpoint after important steps
                    if self._should_checkpoint_after(step, strategy):
                        await self.persistence.create_checkpoint(
                            job_id, i, context, "after_step",
                            description=f"After {step.get('name', f'Step {i}')}"
                        )
                    
                    # Update job progress
                    progress = ((i + 1) / len(steps)) * 100 if steps else 100
                    await self.persistence.update_job_status(
                        job_id,
                        JobStatus.RUNNING,
                        current_step_index=i + 1,
                        progress_percentage=progress
                    )
                    
                except Exception as e:
                    logger.error(f"Step {i} failed: {str(e)}", exc_info=True)
                    
                    # Record failure
                    await self.persistence.record_step_failure(
                        job_id, i, str(e),
                        error_traceback=traceback.format_exc()
                    )
                    
                    # Check retry policy
                    retry_policy = step.get("on_error", {})
                    if retry_policy.get("action") == "retry":
                        max_retries = retry_policy.get("max_attempts", 3)
                        retry_count = context.custom_action_data.get(f"step_{i}_retries", 0)
                        
                        if retry_count < max_retries:
                            # Increment retry count
                            context.custom_action_data[f"step_{i}_retries"] = retry_count + 1
                            
                            # Wait before retry
                            await asyncio.sleep(retry_policy.get("delay_seconds", 5))
                            
                            # Retry the step
                            logger.info(f"Retrying step {i} (attempt {retry_count + 1}/{max_retries})")
                            steps.insert(i + 1, step)  # Re-insert step for retry
                            continue
                    
                    # Check if we should continue or fail
                    if step.get("is_required", True):
                        # Required step failed - fail the job
                        await self.persistence.update_job_status(
                            job_id,
                            JobStatus.FAILED,
                            error_message=str(e),
                            error_details={"step": i, "step_name": step.get("name")}
                        )
                        raise
                    else:
                        # Optional step failed - continue
                        logger.warning(f"Optional step {i} failed, continuing...")
                        continue
            
            # Job completed successfully
            final_results = {
                "total_steps": len(steps),
                "completed_steps": len([
                    k for k in context.custom_action_data.keys()
                    if k.startswith("step_") and k.endswith("_output")
                ]),
                "context": context.custom_action_data
            }
            
            # Calculate total execution time
            job = await self.persistence.get_job(job_id)
            if job.started_at:
                execution_time_ms = int(
                    (datetime.utcnow() - job.started_at).total_seconds() * 1000
                )
            else:
                execution_time_ms = 0
            
            # Get resource metrics
            metrics = await self.persistence.get_job_metrics(job_id)
            
            await self.persistence.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                final_results=final_results,
                execution_time_ms=execution_time_ms,
                cpu_seconds=metrics.get("cpu_seconds"),
                memory_mb_peak=metrics.get("memory_mb_peak")
            )
            
            return {
                "success": True,
                "job_id": str(job_id),
                "results": final_results,
                "metrics": metrics,
                "context": context.custom_action_data
            }
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            
            # Update job status
            await self.persistence.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()}
            )
            
            return {
                "success": False,
                "job_id": str(job_id),
                "error": str(e),
                "context": context.custom_action_data if context else {}
            }
        finally:
            # Clean up running job reference
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    async def pause_job(self, job_id: uuid.UUID) -> bool:
        """Pause a running job."""
        job = await self.persistence.get_job(job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False
        
        # Create checkpoint at current state
        checkpoint = await self.persistence.get_latest_checkpoint(job_id)
        
        # Update status
        await self.persistence.update_job_status(
            job_id,
            JobStatus.PAUSED
        )
        
        # Cancel the running task
        if job_id in self.running_jobs:
            self.running_jobs[job_id].cancel()
            del self.running_jobs[job_id]
        
        return True
    
    async def resume_job(self, job_id: uuid.UUID) -> bool:
        """Resume a paused job."""
        job = await self.persistence.get_job(job_id)
        if not job or job.status != JobStatus.PAUSED:
            return False
        
        # Get latest checkpoint
        checkpoint = await self.persistence.get_latest_checkpoint(job_id)
        if not checkpoint:
            logger.error(f"No checkpoint found for job {job_id}")
            return False
        
        # Start execution from checkpoint
        task = asyncio.create_task(
            self.execute_strategy(
                job_id,
                job.strategy_config,
                resume_from_checkpoint=checkpoint.id
            )
        )
        
        self.running_jobs[job_id] = task
        return True
    
    async def cancel_job(self, job_id: uuid.UUID) -> bool:
        """Cancel a running or paused job."""
        job = await self.persistence.get_job(job_id)
        if not job:
            return False
        
        # Update status
        await self.persistence.update_job_status(
            job_id,
            JobStatus.CANCELLED,
            completed_at=datetime.utcnow()
        )
        
        # Cancel running task if exists
        if job_id in self.running_jobs:
            self.running_jobs[job_id].cancel()
            del self.running_jobs[job_id]
        
        return True
    
    def _find_best_checkpoint(
        self,
        checkpoints: List,
        target_step: int
    ) -> Optional[Any]:
        """Find the best checkpoint to resume from."""
        # Find the checkpoint closest to but not after the target step
        best = None
        for checkpoint in checkpoints:
            if checkpoint.step_index < target_step:
                if best is None or checkpoint.step_index > best.step_index:
                    best = checkpoint
        return best
    
    def _should_checkpoint_before(self, step: Dict, strategy: Dict) -> bool:
        """Determine if checkpoint should be created before step."""
        # Always checkpoint before critical or long-running steps
        if step.get("checkpoint_before", False):
            return True
        
        # Check strategy-level policy
        checkpoint_policy = strategy.get("checkpoint_policy", {})
        if checkpoint_policy.get("before_each_step", False):
            return True
        
        # Checkpoint before specific action types
        critical_actions = checkpoint_policy.get("before_actions", [
            "EXECUTE_MAPPING_PATH",
            "MERGE_DATASETS",
            "CALCULATE_THREE_WAY_OVERLAP"
        ])
        
        return step.get("action", {}).get("type") in critical_actions
    
    def _should_checkpoint_after(self, step: Dict, strategy: Dict) -> bool:
        """Determine if checkpoint should be created after step."""
        # Always checkpoint after critical steps
        if step.get("checkpoint_after", False):
            return True
        
        # Check strategy-level policy
        checkpoint_policy = strategy.get("checkpoint_policy", {})
        if checkpoint_policy.get("after_each_step", False):
            return True
        
        # Checkpoint after specific action types
        important_actions = checkpoint_policy.get("after_actions", [
            "LOAD_DATASET_IDENTIFIERS",
            "MERGE_WITH_UNIPROT_RESOLUTION",
            "EXPORT_DATASET"
        ])
        
        return step.get("action", {}).get("type") in important_actions
    
    async def get_job_status(self, job_id: uuid.UUID) -> Dict[str, Any]:
        """Get current job status with details."""
        job = await self.persistence.get_job(job_id)
        if not job:
            return {"error": "Job not found"}
        
        # Get metrics
        metrics = await self.persistence.get_job_metrics(job_id)
        
        # Get latest events
        events = await self.persistence.get_events(job_id, limit=10)
        
        return {
            "job_id": str(job_id),
            "status": job.status.value if job.status else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "progress": {
                "current_step": job.current_step_index,
                "total_steps": job.total_steps,
                "percentage": float(job.progress_percentage) if job.progress_percentage else 0
            },
            "metrics": metrics,
            "recent_events": [
                {
                    "type": e.event_type,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "message": e.message
                }
                for e in events
            ],
            "error": job.error_message if job.status == JobStatus.FAILED else None
        }
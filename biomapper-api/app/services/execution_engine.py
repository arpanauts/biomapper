"""Enhanced execution engine with checkpointing and error recovery."""

import asyncio
import json
import logging
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence import (
    ExecutionCheckpoint as Checkpoint,
    Job,
    ExecutionLog as JobLog,
    ExecutionStep as JobStep,
)
from app.models.strategy_execution import JobStatus
from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.models import StrategyExecutionContext

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoints for job execution."""

    def __init__(self, db: AsyncSession, job_id: str):
        self.db = db
        self.job_id = job_id
        self.checkpoint_dir = Path(f"/tmp/biomapper/checkpoints/{job_id}")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def create_checkpoint(
        self,
        step_name: str,
        step_index: int,
        context: StrategyExecutionContext,
        checkpoint_type: str = "automatic",
    ) -> str:
        """Create a checkpoint for the current execution state."""
        checkpoint_id = str(uuid.uuid4())

        # Serialize context to JSON
        context_snapshot = self._serialize_context(context)

        # Save to database
        checkpoint = Checkpoint(
            id=checkpoint_id,
            job_id=self.job_id,
            step_name=step_name,
            step_index=step_index,
            context_snapshot=context_snapshot,
            parameters_snapshot=context.get("parameters", {}),
            checkpoint_type=checkpoint_type,
            size_bytes=len(json.dumps(context_snapshot)),
        )

        self.db.add(checkpoint)
        await self.db.commit()

        # Also save to filesystem for large data
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(
                {
                    "context": context_snapshot,
                    "metadata": {
                        "step_name": step_name,
                        "step_index": step_index,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                },
                f,
            )

        logger.info(f"Created checkpoint {checkpoint_id} at step {step_name}")
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Restore execution state from a checkpoint."""
        # Load from database
        checkpoint = await self.db.get(Checkpoint, checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Load from filesystem if available
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, "r") as f:
                data = json.load(f)
                return {
                    "context": data["context"],
                    "step_name": checkpoint.step_name,
                    "step_index": checkpoint.step_index,
                }

        return {
            "context": checkpoint.context_snapshot,
            "step_name": checkpoint.step_name,
            "step_index": checkpoint.step_index,
        }

    async def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints for a job."""
        result = await self.db.execute(
            "SELECT * FROM checkpoints WHERE job_id = :job_id ORDER BY created_at DESC",
            {"job_id": self.job_id},
        )
        return result.scalars().all()

    async def cleanup_checkpoints(self):
        """Clean up checkpoint files after job completion."""
        import shutil

        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)

        # Mark checkpoints as non-resumable
        await self.db.execute(
            "UPDATE checkpoints SET can_resume = FALSE WHERE job_id = :job_id",
            {"job_id": self.job_id},
        )
        await self.db.commit()

    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize context for storage, handling non-JSON types."""
        # TODO: Implement proper serialization for DataFrames, numpy arrays, etc.
        # For now, just store basic types
        serializable = {}
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                serializable[key] = value
            else:
                serializable[key] = str(type(value))
        return serializable


class ProgressTracker:
    """Tracks and reports job progress."""

    def __init__(self, db: AsyncSession, job_id: str):
        self.db = db
        self.job_id = job_id
        self.start_time = time.time()
        self.step_times: List[float] = []
        self.callbacks: List[callable] = []

    def add_callback(self, callback: callable):
        """Add a progress callback function."""
        self.callbacks.append(callback)

    async def update_progress(
        self,
        current_step: str,
        step_index: int,
        total_steps: int,
        message: Optional[str] = None,
    ):
        """Update job progress."""
        # Update job in database
        job = await self.db.get(Job, self.job_id)
        if job:
            job.current_step = current_step
            job.current_step_index = step_index
            job.total_steps = total_steps
            await self.db.commit()

        # Calculate progress percentage
        progress_percentage = (step_index / total_steps * 100) if total_steps > 0 else 0

        # Estimate remaining time
        elapsed = time.time() - self.start_time
        if step_index > 0:
            avg_step_time = elapsed / step_index
            remaining_steps = total_steps - step_index
            estimated_remaining = avg_step_time * remaining_steps
        else:
            estimated_remaining = None

        # Call callbacks
        progress_data = {
            "job_id": self.job_id,
            "current_step": current_step,
            "step_index": step_index,
            "total_steps": total_steps,
            "progress_percentage": progress_percentage,
            "elapsed_seconds": int(elapsed),
            "estimated_remaining_seconds": int(estimated_remaining)
            if estimated_remaining
            else None,
            "message": message,
        }

        for callback in self.callbacks:
            try:
                await callback(progress_data)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    async def log_message(
        self,
        level: str,
        message: str,
        step_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log a message for the job."""
        log_entry = JobLog(
            job_id=self.job_id,
            level=level,
            message=message,
            step_name=step_name,
            details=details,
        )
        self.db.add(log_entry)
        await self.db.commit()


class EnhancedExecutionEngine:
    """Enhanced engine with full lifecycle management."""

    def __init__(
        self, db: AsyncSession, action_registry: Dict[str, Type[BaseStrategyAction]]
    ):
        self.db = db
        self.action_registry = action_registry
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.job_locks: Dict[str, asyncio.Lock] = {}

    async def execute_strategy(
        self,
        job: Job,
        strategy: Dict[str, Any],
        context: StrategyExecutionContext,
        checkpoint_manager: CheckpointManager,
        progress_tracker: ProgressTracker,
    ) -> Dict[str, Any]:
        """
        Execute strategy with full lifecycle management.

        Features:
        - Step-by-step execution with checkpointing
        - Error handling and retry logic
        - Progress reporting at each step
        - Context preservation between steps
        - Conditional execution support
        """
        try:
            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            await self.db.commit()

            # Get strategy steps
            steps = strategy.get("steps", [])
            total_steps = len(steps)

            # Initialize context with parameters
            context.update(job.parameters)

            # Check if resuming from checkpoint
            start_index = job.current_step_index or 0

            # Execute steps
            for index, step in enumerate(steps[start_index:], start=start_index):
                # Check if job was cancelled or paused
                await self.db.refresh(job)
                if job.status == JobStatus.CANCELLED:
                    await progress_tracker.log_message(
                        "INFO", "Job was cancelled", step.get("name")
                    )
                    break
                elif job.status == JobStatus.PAUSED:
                    await progress_tracker.log_message(
                        "INFO", "Job was paused", step.get("name")
                    )
                    # Create checkpoint before pausing
                    await checkpoint_manager.create_checkpoint(
                        step.get("name", f"step_{index}"),
                        index,
                        context,
                        checkpoint_type="manual",
                    )
                    break

                # Update progress
                step_name = step.get("name", f"step_{index}")
                await progress_tracker.update_progress(
                    step_name, index + 1, total_steps, f"Starting step: {step_name}"
                )

                # Check conditions
                if not await self.evaluate_condition(step.get("condition"), context):
                    await progress_tracker.log_message(
                        "INFO", f"Skipping step {step_name} due to condition", step_name
                    )
                    continue

                # Execute step with retry logic
                step_result = await self.execute_step_with_retry(
                    step, context, job, progress_tracker
                )

                if step_result.get("status") == "failed" and step.get(
                    "is_required", True
                ):
                    # Required step failed
                    error_msg = step_result.get("error", "Unknown error")
                    job.status = JobStatus.FAILED
                    job.error_message = f"Step {step_name} failed: {error_msg}"
                    await self.db.commit()
                    raise Exception(job.error_message)

                # Update context with step results
                if step_result.get("output"):
                    context[f"{step_name}_output"] = step_result["output"]

                # Create checkpoint if configured
                if job.options.get("checkpoint_interval") == "after_each_step":
                    await checkpoint_manager.create_checkpoint(
                        step_name, index + 1, context
                    )

                # Log step completion
                await progress_tracker.log_message(
                    "INFO",
                    f"Completed step {step_name}",
                    step_name,
                    {"duration_ms": step_result.get("duration_ms")},
                )

            # Mark job as completed
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.results = self._extract_results(context)
                execution_time = (
                    job.completed_at - job.started_at
                ).total_seconds() * 1000
                job.execution_time_ms = int(execution_time)
                await self.db.commit()

                await progress_tracker.log_message("INFO", "Job completed successfully")

            return job.results

        except Exception as e:
            logger.error(f"Error executing job {job.id}: {str(e)}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.error_details = {"traceback": traceback.format_exc()}
            job.completed_at = datetime.utcnow()
            await self.db.commit()

            await progress_tracker.log_message("ERROR", f"Job failed: {str(e)}")

            # Create error checkpoint for recovery
            if checkpoint_manager:
                await checkpoint_manager.create_checkpoint(
                    job.current_step or "error",
                    job.current_step_index or 0,
                    context,
                    checkpoint_type="pre_error",
                )

            raise

        finally:
            # Clean up running job reference
            if job.id in self.running_jobs:
                del self.running_jobs[job.id]

    async def execute_step_with_retry(
        self,
        step: Dict[str, Any],
        context: StrategyExecutionContext,
        job: Job,
        progress_tracker: ProgressTracker,
    ) -> Dict[str, Any]:
        """Execute a single step with retry logic."""
        step_name = step.get("name", "unnamed_step")
        action_type = step.get("action_type")
        params = step.get("params", {})
        max_retries = job.options.get("max_retries", 3)
        retry_count = 0

        # Create step record
        job_step = JobStep(
            job_id=job.id,
            name=step_name,
            action_type=action_type,
            step_index=job.current_step_index or 0,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.db.add(job_step)
        await self.db.commit()

        while retry_count <= max_retries:
            try:
                start_time = time.time()

                # Get action from registry
                action_class = self.action_registry.get(action_type)
                if not action_class:
                    raise ValueError(f"Unknown action type: {action_type}")

                # Execute action
                action = action_class()
                result = await action.execute(params, context)

                # Update step record
                duration_ms = int((time.time() - start_time) * 1000)
                job_step.status = JobStatus.COMPLETED
                job_step.completed_at = datetime.utcnow()
                job_step.duration_ms = duration_ms
                job_step.output_summary = self._summarize_output(result)
                await self.db.commit()

                return {
                    "status": "success",
                    "output": result,
                    "duration_ms": duration_ms,
                }

            except Exception as e:
                retry_count += 1
                error_msg = str(e)

                await progress_tracker.log_message(
                    "WARNING",
                    f"Step {step_name} failed (attempt {retry_count}/{max_retries + 1}): {error_msg}",
                    step_name,
                )

                if retry_count > max_retries or not job.options.get(
                    "retry_failed_steps", True
                ):
                    # Final failure
                    job_step.status = JobStatus.FAILED
                    job_step.error_message = error_msg
                    job_step.error_details = {"traceback": traceback.format_exc()}
                    job_step.retry_count = retry_count
                    await self.db.commit()

                    return {
                        "status": "failed",
                        "error": error_msg,
                        "retry_count": retry_count,
                    }

                # Wait before retry
                await asyncio.sleep(2**retry_count)  # Exponential backoff

    async def evaluate_condition(
        self, condition: Optional[str], context: StrategyExecutionContext
    ) -> bool:
        """Evaluate step conditions for conditional execution."""
        if not condition:
            return True

        try:
            # Simple evaluation - extend as needed
            # Examples: "has_results", "error_count < 5", etc.
            if condition == "has_results":
                return bool(context.get("results"))
            elif condition.startswith("exists:"):
                key = condition.split(":", 1)[1]
                return key in context
            else:
                # Use eval with restricted namespace for safety
                # TODO: Implement safer condition evaluation
                return True
        except Exception as e:
            logger.warning(f"Error evaluating condition '{condition}': {e}")
            return True

    async def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        job = await self.db.get(Job, job_id)
        if job and job.status == JobStatus.RUNNING:
            job.status = JobStatus.PAUSED
            await self.db.commit()
            return True
        return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = await self.db.get(Job, job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.RUNNING
            await self.db.commit()
            # TODO: Restart execution from checkpoint
            return True
        return False

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or paused job."""
        job = await self.db.get(Job, job_id)
        if job and job.status in [JobStatus.RUNNING, JobStatus.PAUSED]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            await self.db.commit()

            # Cancel asyncio task if running
            if job_id in self.running_jobs:
                self.running_jobs[job_id].cancel()
                del self.running_jobs[job_id]

            return True
        return False

    def _extract_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract final results from execution context."""
        # Extract meaningful results from context
        results = {}
        for key, value in context.items():
            if key.endswith("_output") or key in ["results", "final_data"]:
                results[key] = value
        return results

    def _summarize_output(self, output: Any) -> Dict[str, Any]:
        """Create a summary of step output for storage."""
        if isinstance(output, dict):
            return {"type": "dict", "keys": list(output.keys()), "size": len(output)}
        elif isinstance(output, list):
            return {"type": "list", "length": len(output)}
        elif hasattr(output, "shape"):  # DataFrame or numpy array
            return {"type": type(output).__name__, "shape": str(output.shape)}
        else:
            return {"type": type(output).__name__}

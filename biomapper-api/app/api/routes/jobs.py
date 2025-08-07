"""API endpoints for job management with persistence."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.strategy_execution import (
    CancelResponse,
    JobResults,
    JobStatus,
    PauseResponse,
    ProgressInfo,
    RestoreResponse,
    ResumeResponse,
    StrategyExecutionRequest,
    StrategyExecutionResponse,
)
from app.services.action_registry import get_action_registry
from app.services.persistence_service import PersistenceService
from app.services.persistent_execution_engine import PersistentExecutionEngine
from biomapper.core.minimal_strategy_service import MinimalStrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# === Job Creation and Execution ===


@router.post("/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    request: StrategyExecutionRequest, db: AsyncSession = Depends(get_db)
) -> StrategyExecutionResponse:
    """
    Execute a strategy with full persistence support.

    Creates a job record and starts asynchronous execution with:
    - Automatic checkpointing
    - Progress tracking
    - Error recovery
    - Resource monitoring
    """
    try:
        # Load strategy if path provided
        if isinstance(request.strategy, str):
            strategy_service = MinimalStrategyService()
            strategy = strategy_service.load_strategy(request.strategy)
            strategy_name = request.strategy
        else:
            strategy = request.strategy
            strategy_name = strategy.get("name", "inline_strategy")

        # Create persistence service
        persistence = PersistenceService(db)

        # Create job record
        job = await persistence.create_job(
            strategy_name=strategy_name,
            strategy_config=strategy,
            parameters=request.parameters,
            options=request.options.model_dump(),
            tags=request.tags,
            description=request.description,
        )

        # Get action registry
        action_registry = get_action_registry()

        # Create execution engine
        engine = PersistentExecutionEngine(persistence, action_registry)

        # Start asynchronous execution
        import asyncio

        task = asyncio.create_task(
            engine.execute_strategy(job.id, strategy, context=None)
        )

        # Store task reference
        engine.running_jobs[job.id] = task

        return StrategyExecutionResponse(
            job_id=str(job.id),
            status=job.status,
            created_at=job.created_at,
            strategy_name=strategy_name,
            message=f"Job {job.id} created and execution started",
            websocket_url=f"/api/jobs/{job.id}/ws",
            sse_url=f"/api/jobs/{job.id}/events",
        )

    except Exception as e:
        logger.error(f"Failed to execute strategy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute strategy: {str(e)}",
        )


# === Job Status and Progress ===


@router.get("/{job_id}/status", response_model=ProgressInfo)
async def get_job_status(
    job_id: str, db: AsyncSession = Depends(get_db)
) -> ProgressInfo:
    """Get current status and progress of a job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)

        job = await persistence.get_job(job_uuid)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Get step information
        steps = []
        for step in job.steps:
            steps.append(
                {
                    "name": step.step_name,
                    "action_type": step.action_type,
                    "status": step.status,
                    "started_at": step.started_at,
                    "completed_at": step.completed_at,
                    "duration_ms": step.duration_ms,
                    "error_message": step.error_message,
                    "retry_count": step.retry_count,
                }
            )

        # Calculate elapsed time
        if job.started_at:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        else:
            elapsed = 0

        # Get recent logs
        logs = await persistence.get_logs(job_uuid, limit=10)
        messages = [log.message for log in logs]

        return ProgressInfo(
            job_id=job_id,
            status=job.status,
            current_step=f"Step {job.current_step_index}",
            current_step_index=job.current_step_index,
            total_steps=job.total_steps,
            progress_percentage=float(job.progress_percentage)
            if job.progress_percentage
            else 0,
            steps=steps,
            elapsed_seconds=int(elapsed),
            messages=messages,
            last_updated=job.last_updated,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        )


@router.get("/{job_id}/results", response_model=JobResults)
async def get_job_results(
    job_id: str, db: AsyncSession = Depends(get_db)
) -> JobResults:
    """Get complete results from a job execution."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)

        job = await persistence.get_job(job_uuid)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Get metrics
        metrics = await persistence.get_job_metrics(job_uuid)

        # Get step information
        steps = []
        for step in job.steps:
            steps.append(
                {
                    "name": step.step_name,
                    "action_type": step.action_type,
                    "status": step.status,
                    "started_at": step.started_at,
                    "completed_at": step.completed_at,
                    "duration_ms": step.duration_ms,
                    "error_message": step.error_message,
                    "retry_count": step.retry_count,
                    "output_summary": step.output_results
                    if step.output_results
                    else None,
                }
            )

        # Calculate duration
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
        else:
            duration = None

        return JobResults(
            job_id=job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration_seconds=duration,
            strategy_name=job.strategy_name,
            parameters=job.input_parameters,
            steps=steps,
            final_context=job.final_results or {},
            error_message=job.error_message,
            error_details=job.error_details,
            metrics=metrics,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get job results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job results: {str(e)}",
        )


# === Job Control ===


@router.post("/{job_id}/pause", response_model=PauseResponse)
async def pause_job(job_id: str, db: AsyncSession = Depends(get_db)) -> PauseResponse:
    """Pause a running job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)
        engine = PersistentExecutionEngine(persistence, get_action_registry())

        success = await engine.pause_job(job_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be paused (not running or not found)",
            )

        job = await persistence.get_job(job_uuid)
        checkpoint = await persistence.get_latest_checkpoint(job_uuid)

        return PauseResponse(
            job_id=job_id,
            status=JobStatus.PAUSED,
            message="Job paused successfully",
            paused_at=datetime.utcnow(),
            current_step=f"Step {job.current_step_index}",
            checkpoint_created=checkpoint is not None,
            checkpoint_id=str(checkpoint.id) if checkpoint else None,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to pause job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause job: {str(e)}",
        )


@router.post("/{job_id}/resume", response_model=ResumeResponse)
async def resume_job(job_id: str, db: AsyncSession = Depends(get_db)) -> ResumeResponse:
    """Resume a paused job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)
        engine = PersistentExecutionEngine(persistence, get_action_registry())

        success = await engine.resume_job(job_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be resumed (not paused or no checkpoint found)",
            )

        job = await persistence.get_job(job_uuid)

        return ResumeResponse(
            job_id=job_id,
            status=JobStatus.RUNNING,
            message="Job resumed successfully",
            resumed_at=datetime.utcnow(),
            resuming_from_step=f"Step {job.current_step_index}",
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to resume job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume job: {str(e)}",
        )


@router.post("/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)) -> CancelResponse:
    """Cancel a running or paused job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)
        engine = PersistentExecutionEngine(persistence, get_action_registry())

        success = await engine.cancel_job(job_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Job not found"
            )

        return CancelResponse(
            job_id=job_id,
            status=JobStatus.CANCELLED,
            message="Job cancelled successfully",
            cancelled_at=datetime.utcnow(),
            cleanup_performed=True,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to cancel job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        )


# === Checkpoint Management ===


@router.get("/{job_id}/checkpoints")
async def list_checkpoints(
    job_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List available checkpoints for a job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)

        checkpoints = await persistence.list_checkpoints(job_uuid, limit=limit)

        return [
            {
                "id": str(cp.id),
                "step_index": cp.step_index,
                "step_name": cp.step_name,
                "created_at": cp.created_at.isoformat() if cp.created_at else None,
                "type": cp.checkpoint_type,
                "is_resumable": cp.is_resumable,
                "size_bytes": cp.size_bytes,
                "description": cp.description,
            }
            for cp in checkpoints
        ]

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to list checkpoints: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list checkpoints: {str(e)}",
        )


@router.post("/{job_id}/restore/{checkpoint_id}", response_model=RestoreResponse)
async def restore_from_checkpoint(
    job_id: str, checkpoint_id: str, db: AsyncSession = Depends(get_db)
) -> RestoreResponse:
    """Create a new job from a checkpoint."""
    try:
        job_uuid = uuid.UUID(job_id)
        checkpoint_uuid = uuid.UUID(checkpoint_id)
        persistence = PersistenceService(db)

        # Get original job
        original_job = await persistence.get_job(job_uuid)
        if not original_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Restore checkpoint
        checkpoint_data = await persistence.restore_checkpoint(checkpoint_uuid)

        # Create new job from checkpoint
        new_job = await persistence.create_job(
            strategy_name=original_job.strategy_name,
            strategy_config=original_job.strategy_config,
            parameters=original_job.input_parameters,
            options=original_job.execution_options,
            tags=original_job.tags + ["restored"],
            description=f"Restored from checkpoint {checkpoint_id} of job {job_id}",
        )

        # Start execution from checkpoint
        engine = PersistentExecutionEngine(persistence, get_action_registry())
        import asyncio

        task = asyncio.create_task(
            engine.execute_strategy(
                new_job.id,
                original_job.strategy_config,
                context=checkpoint_data["context"],
                resume_from_step=checkpoint_data["step_index"] + 1,
            )
        )
        engine.running_jobs[new_job.id] = task

        return RestoreResponse(
            job_id=str(new_job.id),
            original_job_id=job_id,
            checkpoint_id=checkpoint_id,
            status=JobStatus.RUNNING,
            message="New job created from checkpoint and started",
            resumed_at_step=f"Step {checkpoint_data['step_index'] + 1}",
            remaining_steps=original_job.total_steps
            - checkpoint_data["step_index"]
            - 1,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
        )
    except Exception as e:
        logger.error(f"Failed to restore from checkpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore from checkpoint: {str(e)}",
        )


# === Job Listing and History ===


@router.get("/", response_model=List[Dict[str, Any]])
async def list_jobs(
    status: Optional[JobStatus] = Query(None),
    strategy_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List jobs with optional filtering."""
    try:
        persistence = PersistenceService(db)

        jobs = await persistence.list_jobs(
            status=status, strategy_name=strategy_name, limit=limit, offset=offset
        )

        return [
            {
                "id": str(job.id),
                "strategy_name": job.strategy_name,
                "status": job.status.value if job.status else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "progress_percentage": float(job.progress_percentage)
                if job.progress_percentage
                else 0,
                "tags": job.tags,
                "description": job.description,
                "error_message": job.error_message,
            }
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        )


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    level: Optional[str] = Query(None),
    step_index: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get execution logs for a job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)

        logs = await persistence.get_logs(
            job_uuid, limit=limit, level=level, step_index=step_index
        )

        return [
            {
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "level": log.log_level,
                "message": log.message,
                "step_index": log.step_index,
                "category": log.category,
                "component": log.component,
                "details": log.details,
            }
            for log in logs
        ]

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get job logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job logs: {str(e)}",
        )


@router.get("/{job_id}/metrics")
async def get_job_metrics(
    job_id: str, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed metrics for a job."""
    try:
        job_uuid = uuid.UUID(job_id)
        persistence = PersistenceService(db)

        metrics = await persistence.get_job_metrics(job_uuid)

        return metrics

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get job metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job metrics: {str(e)}",
        )


# === Cleanup Operations ===


@router.delete("/cleanup")
async def cleanup_old_jobs(
    days_old: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Clean up old job data."""
    try:
        persistence = PersistenceService(db)
        await persistence.cleanup_old_data(days=days_old)

        return {"message": f"Cleaned up jobs older than {days_old} days"}

    except Exception as e:
        logger.error(f"Failed to cleanup old jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup old jobs: {str(e)}",
        )

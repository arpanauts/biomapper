"""Enhanced strategy execution routes with full job management."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_session_service
from app.core.config import settings
from app.models.job import Job, JobEvent, JobLog, JobStep, Checkpoint
from app.models.strategy_execution import (
    ActionInfo,
    CancelResponse,
    JobResults,
    JobStatus,
    LogEntry,
    PauseResponse,
    PrerequisiteReport,
    ProgressInfo,
    RestoreResponse,
    ResumeResponse,
    StepInfo,
    StepResults,
    StrategyExecutionRequest,
    StrategyExecutionResponse,
)
from app.services.action_registry import get_action_registry
from app.services.execution_engine import CheckpointManager, EnhancedExecutionEngine, ProgressTracker
from app.services.prerequisites import PrerequisiteChecker
from biomapper.core.minimal_strategy_service import MinimalStrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies/v2", tags=["Enhanced Strategy Execution"])


# Initialize services
action_registry = get_action_registry()
execution_engine = None  # Will be initialized per request with DB session
prerequisite_checker = PrerequisiteChecker()

# WebSocket connections for real-time updates
active_websockets: Dict[str, List[WebSocket]] = {}


async def get_execution_engine(db: AsyncSession = Depends(get_db)) -> EnhancedExecutionEngine:
    """Get execution engine with database session."""
    return EnhancedExecutionEngine(db, action_registry._registry)


@router.post("/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    request: StrategyExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    engine: EnhancedExecutionEngine = Depends(get_execution_engine)
) -> StrategyExecutionResponse:
    """
    Execute a strategy with full lifecycle management.
    
    Features:
    - Async execution with job ID
    - Progress tracking via WebSocket/SSE
    - Checkpoint support
    - Error recovery
    - Parameter validation
    - Result streaming for large outputs
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Load strategy
        if isinstance(request.strategy, str):
            # Load from file
            strategy_service = MinimalStrategyService()
            strategies = strategy_service.get_available_strategies()
            
            if request.strategy not in strategies:
                raise HTTPException(status_code=404, detail=f"Strategy '{request.strategy}' not found")
            
            strategy_config = strategies[request.strategy]
            strategy_name = request.strategy
        else:
            # Inline strategy
            strategy_config = request.strategy
            strategy_name = strategy_config.get("name", "inline_strategy")
        
        # Validate prerequisites if enabled
        if request.options.validate_prerequisites:
            prereq_report = await prerequisite_checker.check_all(strategy_config)
            if not prereq_report.can_proceed:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Prerequisites not met",
                        "report": prereq_report.dict()
                    }
                )
        
        # Create job record
        job = Job(
            id=job_id,
            strategy_name=strategy_name,
            strategy_config=strategy_config,
            status=JobStatus.PENDING,
            parameters=request.parameters,
            options=request.options.dict(),
            tags=request.tags,
            description=request.description,
            total_steps=len(strategy_config.get("steps", []))
        )
        db.add(job)
        await db.commit()
        
        # Initialize managers
        checkpoint_manager = CheckpointManager(db, job_id)
        progress_tracker = ProgressTracker(db, job_id)
        
        # Add WebSocket callback if connections exist
        async def websocket_progress_callback(data: Dict[str, Any]):
            await broadcast_job_event(job_id, "progress", data)
        
        progress_tracker.add_callback(websocket_progress_callback)
        
        # Start background execution
        background_tasks.add_task(
            execute_strategy_background,
            job_id,
            strategy_config,
            request.parameters,
            db,
            engine,
            checkpoint_manager,
            progress_tracker
        )
        
        # Prepare response
        response = StrategyExecutionResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=job.created_at,
            strategy_name=strategy_name,
            message="Strategy execution started",
            estimated_duration=estimate_execution_time(strategy_config),
            websocket_url=f"ws://{settings.API_HOST}:{settings.API_PORT}/api/strategies/v2/jobs/{job_id}/stream",
            sse_url=f"http://{settings.API_HOST}:{settings.API_PORT}/api/strategies/v2/jobs/{job_id}/events"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error starting strategy execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_strategy_background(
    job_id: str,
    strategy_config: Dict[str, Any],
    parameters: Dict[str, Any],
    db: AsyncSession,
    engine: EnhancedExecutionEngine,
    checkpoint_manager: CheckpointManager,
    progress_tracker: ProgressTracker
):
    """Background task to execute strategy."""
    try:
        # Get job from database
        job = await db.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Update status to validating
        job.status = JobStatus.VALIDATING
        await db.commit()
        
        # Validate strategy steps
        for step in strategy_config.get("steps", []):
            action_type = step.get("action_type")
            if action_type:
                try:
                    params = step.get("params", {})
                    validated_params = action_registry.validate_action_params(action_type, params)
                    step["params"] = validated_params
                except ValueError as e:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Validation error: {str(e)}"
                    await db.commit()
                    return
        
        # Execute strategy
        context = {"job_id": job_id}
        result = await engine.execute_strategy(
            job,
            strategy_config,
            context,
            checkpoint_manager,
            progress_tracker
        )
        
        # Broadcast completion
        await broadcast_job_event(job_id, "complete", {"result": result})
        
    except Exception as e:
        logger.error(f"Background execution error for job {job_id}: {str(e)}")
        await broadcast_job_event(job_id, "error", {"error": str(e)})


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get the current status of a job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "current_step": job.current_step,
        "progress": {
            "current": job.current_step_index,
            "total": job.total_steps,
            "percentage": (job.current_step_index / job.total_steps * 100) if job.total_steps > 0 else 0
        },
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    engine: EnhancedExecutionEngine = Depends(get_execution_engine)
) -> CancelResponse:
    """Cancel a running or paused job."""
    success = await engine.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    
    # Perform cleanup
    checkpoint_manager = CheckpointManager(db, job_id)
    await checkpoint_manager.cleanup_checkpoints()
    
    return CancelResponse(
        job_id=job_id,
        status=JobStatus.CANCELLED,
        message="Job cancelled successfully",
        cancelled_at=datetime.utcnow(),
        cleanup_performed=True
    )


@router.post("/jobs/{job_id}/pause", response_model=PauseResponse)
async def pause_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    engine: EnhancedExecutionEngine = Depends(get_execution_engine)
) -> PauseResponse:
    """Pause a running job."""
    success = await engine.pause_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be paused")
    
    job = await db.get(Job, job_id)
    
    # Create checkpoint
    checkpoint_manager = CheckpointManager(db, job_id)
    checkpoint_id = await checkpoint_manager.create_checkpoint(
        job.current_step or "pause",
        job.current_step_index or 0,
        job.context,
        checkpoint_type="manual"
    )
    
    return PauseResponse(
        job_id=job_id,
        status=JobStatus.PAUSED,
        message="Job paused successfully",
        paused_at=datetime.utcnow(),
        current_step=job.current_step,
        checkpoint_created=True,
        checkpoint_id=checkpoint_id
    )


@router.post("/jobs/{job_id}/resume", response_model=ResumeResponse)
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    engine: EnhancedExecutionEngine = Depends(get_execution_engine)
) -> ResumeResponse:
    """Resume a paused job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Job is not paused")
    
    # Find latest checkpoint
    checkpoints = await db.execute(
        select(Checkpoint)
        .where(Checkpoint.job_id == job_id)
        .order_by(Checkpoint.created_at.desc())
        .limit(1)
    )
    checkpoint = checkpoints.scalar_one_or_none()
    
    if not checkpoint:
        raise HTTPException(status_code=400, detail="No checkpoint found for resuming")
    
    # Resume execution
    job.status = JobStatus.RUNNING
    await db.commit()
    
    # Restart background execution from checkpoint
    checkpoint_manager = CheckpointManager(db, job_id)
    progress_tracker = ProgressTracker(db, job_id)
    
    background_tasks.add_task(
        resume_strategy_execution,
        job,
        checkpoint,
        db,
        engine,
        checkpoint_manager,
        progress_tracker
    )
    
    return ResumeResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        message="Job resumed successfully",
        resumed_at=datetime.utcnow(),
        resuming_from_step=checkpoint.step_name
    )


@router.get("/jobs/{job_id}/progress", response_model=ProgressInfo)
async def get_job_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> ProgressInfo:
    """Get detailed progress information for a job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get step information
    steps_result = await db.execute(
        select(JobStep).where(JobStep.job_id == job_id).order_by(JobStep.step_index)
    )
    steps = steps_result.scalars().all()
    
    step_infos = [
        StepInfo(
            name=step.name,
            action_type=step.action_type,
            status=step.status,
            started_at=step.started_at,
            completed_at=step.completed_at,
            duration_ms=step.duration_ms,
            error_message=step.error_message,
            retry_count=step.retry_count,
            output_summary=step.output_summary
        )
        for step in steps
    ]
    
    # Calculate elapsed time
    if job.started_at:
        if job.completed_at:
            elapsed = (job.completed_at - job.started_at).total_seconds()
        else:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds()
    else:
        elapsed = 0
    
    # Get recent log messages
    logs_result = await db.execute(
        select(JobLog)
        .where(JobLog.job_id == job_id)
        .order_by(JobLog.timestamp.desc())
        .limit(10)
    )
    logs = logs_result.scalars().all()
    messages = [log.message for log in reversed(logs)]
    
    return ProgressInfo(
        job_id=job_id,
        status=job.status,
        current_step=job.current_step,
        current_step_index=job.current_step_index or 0,
        total_steps=job.total_steps or 0,
        progress_percentage=(job.current_step_index / job.total_steps * 100) if job.total_steps > 0 else 0,
        steps=step_infos,
        elapsed_seconds=int(elapsed),
        estimated_remaining_seconds=None,  # TODO: Implement estimation
        messages=messages,
        last_updated=job.last_updated or datetime.utcnow()
    )


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    tail: int = 100,
    level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> List[LogEntry]:
    """Get logs for a job."""
    query = select(JobLog).where(JobLog.job_id == job_id)
    
    if level:
        query = query.where(JobLog.level == level.upper())
    
    query = query.order_by(JobLog.timestamp.desc()).limit(tail)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        LogEntry(
            timestamp=log.timestamp,
            level=log.level,
            step_name=log.step_name,
            message=log.message,
            details=log.details
        )
        for log in reversed(logs)
    ]


@router.get("/jobs/{job_id}/results", response_model=JobResults)
async def get_job_results(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> JobResults:
    """Get complete results from a job execution."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get steps
    steps_result = await db.execute(
        select(JobStep).where(JobStep.job_id == job_id).order_by(JobStep.step_index)
    )
    steps = steps_result.scalars().all()
    
    step_infos = [
        StepInfo(
            name=step.name,
            action_type=step.action_type,
            status=step.status,
            started_at=step.started_at,
            completed_at=step.completed_at,
            duration_ms=step.duration_ms,
            error_message=step.error_message,
            retry_count=step.retry_count,
            output_summary=step.output_summary
        )
        for step in steps
    ]
    
    # Calculate duration
    duration = None
    if job.started_at and job.completed_at:
        duration = (job.completed_at - job.started_at).total_seconds()
    
    return JobResults(
        job_id=job_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=duration,
        strategy_name=job.strategy_name,
        parameters=job.parameters,
        steps=step_infos,
        final_context=job.context or {},
        output_files=[],  # TODO: Track output files
        error_message=job.error_message,
        error_details=job.error_details,
        metrics={}  # TODO: Collect metrics
    )


@router.get("/jobs/{job_id}/steps/{step_name}/results", response_model=StepResults)
async def get_step_results(
    job_id: str,
    step_name: str,
    db: AsyncSession = Depends(get_db)
) -> StepResults:
    """Get results from a specific step."""
    result = await db.execute(
        select(JobStep)
        .where(JobStep.job_id == job_id, JobStep.name == step_name)
        .limit(1)
    )
    step = result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Get logs for this step
    logs_result = await db.execute(
        select(JobLog)
        .where(JobLog.job_id == job_id, JobLog.step_name == step_name)
        .order_by(JobLog.timestamp)
    )
    logs = logs_result.scalars().all()
    
    log_entries = [
        LogEntry(
            timestamp=log.timestamp,
            level=log.level,
            step_name=log.step_name,
            message=log.message,
            details=log.details
        )
        for log in logs
    ]
    
    return StepResults(
        job_id=job_id,
        step_name=step_name,
        action_type=step.action_type,
        status=step.status,
        input_data=step.input_summary,
        output_data=step.output_summary,
        error_message=step.error_message,
        logs=log_entries,
        metrics={"duration_ms": step.duration_ms, "retry_count": step.retry_count}
    )


@router.get("/jobs/{job_id}/checkpoints")
async def list_checkpoints(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """List all checkpoints for a job."""
    result = await db.execute(
        select(Checkpoint)
        .where(Checkpoint.job_id == job_id)
        .order_by(Checkpoint.created_at.desc())
    )
    checkpoints = result.scalars().all()
    
    return [checkpoint.to_dict() for checkpoint in checkpoints]


@router.post("/jobs/{job_id}/restore", response_model=RestoreResponse)
async def restore_from_checkpoint(
    job_id: str,
    checkpoint_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    engine: EnhancedExecutionEngine = Depends(get_execution_engine)
) -> RestoreResponse:
    """Restore job execution from a checkpoint."""
    # Get checkpoint
    checkpoint = await db.get(Checkpoint, checkpoint_id)
    if not checkpoint or checkpoint.job_id != job_id:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    if not checkpoint.can_resume:
        raise HTTPException(status_code=400, detail="Checkpoint cannot be resumed")
    
    # Get original job
    original_job = await db.get(Job, job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail="Original job not found")
    
    # Create new job from checkpoint
    new_job_id = str(uuid.uuid4())
    new_job = Job(
        id=new_job_id,
        strategy_name=original_job.strategy_name,
        strategy_config=original_job.strategy_config,
        status=JobStatus.PENDING,
        parameters=checkpoint.parameters_snapshot,
        context=checkpoint.context_snapshot,
        options=original_job.options,
        tags=original_job.tags + ["restored"],
        description=f"Restored from checkpoint {checkpoint_id}",
        current_step_index=checkpoint.step_index,
        total_steps=original_job.total_steps
    )
    db.add(new_job)
    await db.commit()
    
    # Start execution from checkpoint
    checkpoint_manager = CheckpointManager(db, new_job_id)
    progress_tracker = ProgressTracker(db, new_job_id)
    
    background_tasks.add_task(
        resume_strategy_execution,
        new_job,
        checkpoint,
        db,
        engine,
        checkpoint_manager,
        progress_tracker
    )
    
    return RestoreResponse(
        job_id=new_job_id,
        original_job_id=job_id,
        checkpoint_id=checkpoint_id,
        status=JobStatus.RUNNING,
        message="Job restored from checkpoint",
        resumed_at_step=checkpoint.step_name,
        remaining_steps=original_job.total_steps - checkpoint.step_index
    )


@router.websocket("/jobs/{job_id}/stream")
async def stream_job_updates(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()
    
    # Add to active connections
    if job_id not in active_websockets:
        active_websockets[job_id] = []
    active_websockets[job_id].append(websocket)
    
    try:
        # Send initial status
        job = await db.get(Job, job_id)
        if job:
            await websocket.send_json({
                "type": "status",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "status": job.status.value,
                    "current_step": job.current_step,
                    "progress": job.current_step_index / job.total_steps * 100 if job.total_steps > 0 else 0
                }
            })
        
        # Keep connection alive
        while True:
            # Wait for messages (or connection close)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        # Remove from active connections
        if job_id in active_websockets:
            active_websockets[job_id].remove(websocket)
            if not active_websockets[job_id]:
                del active_websockets[job_id]


@router.get("/jobs/{job_id}/events")
async def stream_job_events(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Server-Sent Events endpoint for job updates."""
    async def event_generator():
        """Generate SSE events."""
        last_event_id = 0
        
        while True:
            # Get new events
            result = await db.execute(
                select(JobEvent)
                .where(JobEvent.job_id == job_id, JobEvent.id > last_event_id)
                .order_by(JobEvent.id)
            )
            events = result.scalars().all()
            
            for event in events:
                yield f"data: {json.dumps(event.to_dict())}\n\n"
                last_event_id = event.id
            
            # Mark events as delivered
            if events:
                await db.execute(
                    "UPDATE job_events SET delivered = TRUE WHERE job_id = :job_id AND id <= :last_id",
                    {"job_id": job_id, "last_id": last_event_id}
                )
                await db.commit()
            
            # Wait before checking for new events
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/actions", response_model=List[ActionInfo])
async def list_available_actions():
    """List all available actions with metadata."""
    return action_registry.list_available_actions()


@router.get("/actions/{action_name}", response_model=ActionInfo)
async def get_action_info(action_name: str):
    """Get detailed information about a specific action."""
    info = action_registry.get_action_info(action_name)
    if not info:
        raise HTTPException(status_code=404, detail="Action not found")
    return info


@router.post("/actions/reload")
async def reload_actions():
    """Reload the action registry (development endpoint)."""
    action_registry.reload_actions()
    stats = action_registry.get_registry_stats()
    return {
        "message": "Actions reloaded successfully",
        "stats": stats
    }


@router.post("/prerequisites/check")
async def check_prerequisites(
    strategy: Dict[str, Any]
) -> PrerequisiteReport:
    """Check prerequisites for a strategy without executing it."""
    return await prerequisite_checker.check_all(strategy)


# Helper functions

async def broadcast_job_event(job_id: str, event_type: str, data: Dict[str, Any]):
    """Broadcast event to all connected WebSocket clients."""
    if job_id in active_websockets:
        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        disconnected = []
        for websocket in active_websockets[job_id]:
            try:
                await websocket.send_json(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            active_websockets[job_id].remove(ws)


def estimate_execution_time(strategy: Dict[str, Any]) -> Optional[int]:
    """Estimate execution time for a strategy in seconds."""
    # Simple estimation based on number of steps
    # TODO: Implement more sophisticated estimation based on action types
    steps = strategy.get("steps", [])
    return len(steps) * 30  # Assume 30 seconds per step as baseline


async def resume_strategy_execution(
    job: Job,
    checkpoint: Checkpoint,
    db: AsyncSession,
    engine: EnhancedExecutionEngine,
    checkpoint_manager: CheckpointManager,
    progress_tracker: ProgressTracker
):
    """Resume strategy execution from a checkpoint."""
    try:
        # Restore context from checkpoint
        checkpoint_data = await checkpoint_manager.restore_checkpoint(checkpoint.id)
        context = checkpoint_data["context"]
        
        # Update job to start from checkpoint
        job.current_step_index = checkpoint.step_index
        job.context = context
        
        # Continue execution
        await engine.execute_strategy(
            job,
            job.strategy_config,
            context,
            checkpoint_manager,
            progress_tracker
        )
        
    except Exception as e:
        logger.error(f"Error resuming job {job.id}: {str(e)}")
        job.status = JobStatus.FAILED
        job.error_message = f"Resume failed: {str(e)}"
        await db.commit()
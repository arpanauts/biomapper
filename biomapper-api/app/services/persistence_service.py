"""Comprehensive persistence service for job execution state management."""

import json
import pickle
import uuid
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.persistence import (
    ExecutionCheckpoint,
    ExecutionLog,
    ExecutionStep,
    Job,
    JobEvent,
    ResultStorage,
)
from app.models.strategy_execution import JobStatus
from biomapper.core.models import StrategyExecutionContext


class PersistenceService:
    """
    Manages state persistence for job execution.
    
    Features:
    - Automatic state snapshots
    - Checkpoint creation and restoration
    - Result streaming for large datasets
    - Execution history and audit trail
    - External storage for large data
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        storage_backend: Optional['StorageBackend'] = None
    ):
        self.db = db_session
        self.storage = storage_backend or FileSystemStorageBackend()
        
    # === Job Lifecycle ===
    
    async def create_job(
        self,
        strategy_name: str,
        strategy_config: Dict[str, Any],
        parameters: Dict[str, Any],
        options: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: List[str] = None,
        description: Optional[str] = None
    ) -> Job:
        """Create a new job record."""
        job = Job(
            id=uuid.uuid4(),
            strategy_name=strategy_name,
            strategy_config=strategy_config,
            status=JobStatus.PENDING,
            created_by=user_id,
            session_id=session_id,
            input_parameters=parameters,
            execution_options=options,
            total_steps=len(strategy_config.get("steps", [])),
            tags=tags or [],
            description=description
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        await self.log(job.id, "INFO", f"Job created: {strategy_name}")
        await self.emit_event(job.id, "job_created", {"strategy": strategy_name})
        
        return job
    
    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: JobStatus,
        **kwargs
    ) -> Job:
        """Update job status and metadata."""
        # Handle status-specific updates
        if status == JobStatus.RUNNING and "started_at" not in kwargs:
            kwargs["started_at"] = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            if "completed_at" not in kwargs:
                kwargs["completed_at"] = datetime.utcnow()
            if "execution_time_ms" not in kwargs and "started_at" in kwargs:
                started = kwargs.get("started_at")
                if started:
                    kwargs["execution_time_ms"] = int(
                        (datetime.utcnow() - started).total_seconds() * 1000
                    )
        
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status=status, last_updated=datetime.utcnow(), **kwargs)
            .returning(Job)
        )
        
        result = await self.db.execute(stmt)
        job = result.scalar_one()
        await self.db.commit()
        
        await self.emit_event(
            job_id, 
            "status_change", 
            {"old_status": job.status.value if job.status else None, "new_status": status.value}
        )
        
        return job
    
    async def get_job(self, job_id: uuid.UUID) -> Optional[Job]:
        """Retrieve job by ID."""
        stmt = select(Job).where(Job.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        strategy_name: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """List jobs with optional filtering."""
        stmt = select(Job)
        
        if status:
            stmt = stmt.where(Job.status == status)
        if strategy_name:
            stmt = stmt.where(Job.strategy_name == strategy_name)
        if user_id:
            stmt = stmt.where(Job.created_by == user_id)
        
        stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    # === Step Management ===
    
    async def record_step_start(
        self,
        job_id: uuid.UUID,
        step_index: int,
        step_name: str,
        action_type: str,
        params: Dict[str, Any]
    ) -> ExecutionStep:
        """Record the start of a step execution."""
        step = ExecutionStep(
            id=uuid.uuid4(),
            job_id=job_id,
            step_index=step_index,
            step_name=step_name,
            action_type=action_type,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
            input_params=params
        )
        
        self.db.add(step)
        
        # Update job progress
        job = await self.get_job(job_id)
        if job:
            progress = (step_index / job.total_steps * 100) if job.total_steps > 0 else 0
            await self.update_job_status(
                job_id,
                JobStatus.RUNNING,
                current_step_index=step_index,
                progress_percentage=progress
            )
        
        await self.db.commit()
        await self.log(job_id, "INFO", f"Step {step_name} started", step_index=step_index)
        await self.emit_event(
            job_id, 
            "step_started", 
            {"step_name": step_name, "step_index": step_index}
        )
        
        return step
    
    async def record_step_completion(
        self,
        job_id: uuid.UUID,
        step_index: int,
        results: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None
    ) -> ExecutionStep:
        """Record successful step completion."""
        # Get the step to calculate duration
        stmt_select = select(ExecutionStep).where(
            ExecutionStep.job_id == job_id,
            ExecutionStep.step_index == step_index
        )
        result = await self.db.execute(stmt_select)
        step = result.scalar_one_or_none()
        
        if step and step.started_at:
            duration_ms = int((datetime.utcnow() - step.started_at).total_seconds() * 1000)
        else:
            duration_ms = None
        
        stmt = (
            update(ExecutionStep)
            .where(
                ExecutionStep.job_id == job_id,
                ExecutionStep.step_index == step_index
            )
            .values(
                status=JobStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                output_results=results if len(json.dumps(results)) < settings.MAX_INLINE_STORAGE_SIZE else None,
                duration_ms=duration_ms,
                records_processed=metrics.get("records_processed") if metrics else None,
                records_matched=metrics.get("records_matched") if metrics else None,
                records_failed=metrics.get("records_failed") if metrics else None,
                confidence_score=metrics.get("confidence_score") if metrics else None,
                memory_used_mb=metrics.get("memory_used_mb") if metrics else None
            )
            .returning(ExecutionStep)
        )
        
        result = await self.db.execute(stmt)
        step = result.scalar_one()
        
        # Store large results externally
        if len(json.dumps(results)) >= settings.MAX_INLINE_STORAGE_SIZE:
            await self.store_result(
                job_id, step_index, "step_output", results
            )
        
        await self.db.commit()
        await self.log(job_id, "INFO", f"Step {step.step_name} completed", step_index=step_index)
        await self.emit_event(
            job_id,
            "step_completed",
            {"step_name": step.step_name, "step_index": step_index, "metrics": metrics}
        )
        
        return step
    
    async def record_step_failure(
        self,
        job_id: uuid.UUID,
        step_index: int,
        error_message: str,
        error_traceback: Optional[str] = None,
        retry_count: int = 0,
        can_retry: bool = True
    ) -> ExecutionStep:
        """Record step failure."""
        stmt = (
            update(ExecutionStep)
            .where(
                ExecutionStep.job_id == job_id,
                ExecutionStep.step_index == step_index
            )
            .values(
                status=JobStatus.FAILED,
                completed_at=datetime.utcnow(),
                error_message=error_message,
                error_traceback=error_traceback,
                retry_count=retry_count,
                can_retry=can_retry
            )
            .returning(ExecutionStep)
        )
        
        result = await self.db.execute(stmt)
        step = result.scalar_one()
        
        await self.db.commit()
        await self.log(
            job_id, 
            "ERROR", 
            f"Step {step.step_name} failed: {error_message}", 
            step_index=step_index
        )
        await self.emit_event(
            job_id,
            "step_failed",
            {
                "step_name": step.step_name,
                "step_index": step_index,
                "error": error_message,
                "can_retry": can_retry
            }
        )
        
        return step
    
    # === Checkpoint Management ===
    
    async def create_checkpoint(
        self,
        job_id: uuid.UUID,
        step_index: int,
        context: StrategyExecutionContext,
        checkpoint_type: str = "automatic",
        description: Optional[str] = None
    ) -> ExecutionCheckpoint:
        """Create execution checkpoint."""
        
        # Serialize context
        serialized_context = await self._serialize_context(context)
        
        # Compress if large
        size = len(serialized_context)
        compressed = size > 1024 * 100  # Compress if > 100KB
        
        if compressed:
            serialized_context = zlib.compress(serialized_context)
            size = len(serialized_context)
        
        # Determine storage location
        use_external = size >= settings.MAX_INLINE_STORAGE_SIZE
        
        # Create checkpoint record
        checkpoint = ExecutionCheckpoint(
            id=uuid.uuid4(),
            job_id=job_id,
            step_index=step_index,
            checkpoint_type=checkpoint_type,
            context_data=json.loads(serialized_context.decode()) if not use_external and not compressed else None,
            storage_type="filesystem" if use_external else "database",
            size_bytes=size,
            compressed=compressed,
            expires_at=datetime.utcnow() + timedelta(days=7),
            description=description
        )
        
        # Store externally if too large
        if use_external:
            storage_path = await self.storage.store_checkpoint(
                job_id, step_index, serialized_context
            )
            checkpoint.storage_path = storage_path
        
        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)
        
        await self.log(
            job_id, 
            "DEBUG", 
            f"Checkpoint created at step {step_index}", 
            step_index=step_index,
            details={"checkpoint_id": str(checkpoint.id), "type": checkpoint_type}
        )
        await self.emit_event(
            job_id,
            "checkpoint_created",
            {"checkpoint_id": str(checkpoint.id), "step_index": step_index}
        )
        
        return checkpoint
    
    async def restore_checkpoint(
        self,
        checkpoint_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Restore execution context from checkpoint."""
        stmt = select(ExecutionCheckpoint).where(ExecutionCheckpoint.id == checkpoint_id)
        result = await self.db.execute(stmt)
        checkpoint = result.scalar_one_or_none()
        
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        if not checkpoint.is_resumable:
            raise ValueError(f"Checkpoint {checkpoint_id} is not resumable")
        
        # Retrieve context data
        if checkpoint.storage_type == "database":
            context_data = checkpoint.context_data
            if checkpoint.compressed:
                context_data = zlib.decompress(context_data.encode())
            else:
                context_data = json.dumps(context_data).encode()
        else:
            context_data = await self.storage.retrieve_checkpoint(
                checkpoint.storage_path
            )
            if checkpoint.compressed:
                context_data = zlib.decompress(context_data)
        
        # Deserialize context
        context = await self._deserialize_context(context_data)
        
        await self.log(
            checkpoint.job_id,
            "INFO",
            f"Restored from checkpoint at step {checkpoint.step_index}",
            details={"checkpoint_id": str(checkpoint_id)}
        )
        
        return {
            "context": context,
            "step_index": checkpoint.step_index,
            "job_id": checkpoint.job_id
        }
    
    async def list_checkpoints(
        self,
        job_id: uuid.UUID,
        limit: int = 10
    ) -> List[ExecutionCheckpoint]:
        """List available checkpoints for a job."""
        stmt = (
            select(ExecutionCheckpoint)
            .where(ExecutionCheckpoint.job_id == job_id)
            .order_by(ExecutionCheckpoint.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_latest_checkpoint(
        self,
        job_id: uuid.UUID
    ) -> Optional[ExecutionCheckpoint]:
        """Get the most recent checkpoint for a job."""
        stmt = (
            select(ExecutionCheckpoint)
            .where(
                ExecutionCheckpoint.job_id == job_id,
                ExecutionCheckpoint.is_resumable == True
            )
            .order_by(ExecutionCheckpoint.created_at.desc())
            .limit(1)
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    # === Result Management ===
    
    async def store_result(
        self,
        job_id: uuid.UUID,
        step_index: int,
        result_key: str,
        data: Any,
        content_type: str = "application/json",
        expires_in_days: int = 30
    ) -> ResultStorage:
        """Store execution results."""
        
        # Serialize data
        if content_type == "application/json":
            serialized = json.dumps(data).encode()
        else:
            serialized = pickle.dumps(data)
        
        size = len(serialized)
        
        # Compress large data
        if size > 1024 * 100:  # > 100KB
            serialized = zlib.compress(serialized)
            encoding = "gzip"
            size = len(serialized)
        else:
            encoding = None
        
        # Decide storage location
        if size < settings.MAX_INLINE_STORAGE_SIZE:
            result = ResultStorage(
                id=uuid.uuid4(),
                job_id=job_id,
                step_index=step_index,
                result_key=result_key,
                storage_type="inline",
                inline_data=data if content_type == "application/json" else None,
                size_bytes=size,
                content_type=content_type,
                encoding=encoding,
                expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
            )
        else:
            # Store externally
            path = await self.storage.store_result(
                job_id, step_index, result_key, serialized
            )
            result = ResultStorage(
                id=uuid.uuid4(),
                job_id=job_id,
                step_index=step_index,
                result_key=result_key,
                storage_type="filesystem",
                external_path=path,
                size_bytes=size,
                content_type=content_type,
                encoding=encoding,
                expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
            )
        
        self.db.add(result)
        await self.db.commit()
        
        return result
    
    async def retrieve_result(
        self,
        job_id: uuid.UUID,
        step_index: int,
        result_key: str
    ) -> Any:
        """Retrieve stored results."""
        stmt = select(ResultStorage).where(
            ResultStorage.job_id == job_id,
            ResultStorage.step_index == step_index,
            ResultStorage.result_key == result_key
        )
        
        result = await self.db.execute(stmt)
        storage = result.scalar_one_or_none()
        
        if not storage:
            return None
        
        # Update access tracking
        stmt_update = (
            update(ResultStorage)
            .where(ResultStorage.id == storage.id)
            .values(
                accessed_count=storage.accessed_count + 1,
                last_accessed=datetime.utcnow()
            )
        )
        await self.db.execute(stmt_update)
        await self.db.commit()
        
        if storage.storage_type == "inline":
            return storage.inline_data
        else:
            data = await self.storage.retrieve_result(storage.external_path)
            
            # Decompress if needed
            if storage.encoding == "gzip":
                data = zlib.decompress(data)
            
            # Deserialize
            if storage.content_type == "application/json":
                return json.loads(data.decode())
            else:
                return pickle.loads(data)
    
    # === Logging ===
    
    async def log(
        self,
        job_id: uuid.UUID,
        level: str,
        message: str,
        step_index: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        component: Optional[str] = None
    ):
        """Add execution log entry."""
        # Don't convert details - SQLAlchemy JSON type handles this
        log = ExecutionLog(
            # Don't set id - let database auto-generate it
            job_id=job_id,
            step_index=step_index,
            log_level=level,
            message=message,
            details=details,  # Keep as dict/None
            category=category,
            component=component
        )
        
        self.db.add(log)
        await self.db.commit()  # Commit immediately for logs
        
    async def get_logs(
        self,
        job_id: uuid.UUID,
        limit: int = 100,
        level: Optional[str] = None,
        step_index: Optional[int] = None
    ) -> List[ExecutionLog]:
        """Retrieve execution logs."""
        stmt = select(ExecutionLog).where(ExecutionLog.job_id == job_id)
        
        if level:
            stmt = stmt.where(ExecutionLog.log_level == level)
        if step_index is not None:
            stmt = stmt.where(ExecutionLog.step_index == step_index)
        
        stmt = stmt.order_by(ExecutionLog.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    # === Events ===
    
    async def emit_event(
        self,
        job_id: uuid.UUID,
        event_type: str,
        data: Dict[str, Any],
        message: Optional[str] = None,
        severity: str = "info"
    ):
        """Emit a job event for real-time monitoring."""
        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            data=data,
            message=message,
            severity=severity
        )
        
        self.db.add(event)
        # Events are committed separately for real-time delivery
        
    async def get_events(
        self,
        job_id: uuid.UUID,
        since: Optional[datetime] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[JobEvent]:
        """Retrieve job events."""
        stmt = select(JobEvent).where(JobEvent.job_id == job_id)
        
        if since:
            stmt = stmt.where(JobEvent.timestamp > since)
        if event_type:
            stmt = stmt.where(JobEvent.event_type == event_type)
        
        stmt = stmt.order_by(JobEvent.timestamp.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    # === Utilities ===
    
    async def _serialize_context(
        self,
        context: StrategyExecutionContext
    ) -> bytes:
        """Serialize execution context for storage."""
        # Convert to dict representation
        context_dict = {
            "input_identifiers": context.input_identifiers,
            "output_identifiers": context.output_identifiers,
            "output_ontology_type": context.output_ontology_type,
            "custom_action_data": context.custom_action_data,
            "provenance": context.provenance,
            "details": context.details
        }
        
        return json.dumps(context_dict).encode()
    
    async def _deserialize_context(
        self,
        data: bytes
    ) -> StrategyExecutionContext:
        """Deserialize execution context from storage."""
        context_dict = json.loads(data.decode())
        
        return StrategyExecutionContext(
            input_identifiers=context_dict.get("input_identifiers", []),
            output_identifiers=context_dict.get("output_identifiers", []),
            output_ontology_type=context_dict.get("output_ontology_type"),
            custom_action_data=context_dict.get("custom_action_data", {}),
            provenance=context_dict.get("provenance", []),
            details=context_dict.get("details", {})
        )
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old execution data."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Delete old completed jobs
        stmt = delete(Job).where(
            Job.completed_at < cutoff,
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
        )
        await self.db.execute(stmt)
        
        # Delete expired checkpoints
        stmt = delete(ExecutionCheckpoint).where(
            ExecutionCheckpoint.expires_at < datetime.utcnow()
        )
        await self.db.execute(stmt)
        
        # Delete expired results
        stmt = delete(ResultStorage).where(
            ResultStorage.expires_at < datetime.utcnow()
        )
        await self.db.execute(stmt)
        
        await self.db.commit()
    
    async def get_job_metrics(self, job_id: uuid.UUID) -> Dict[str, Any]:
        """Get comprehensive metrics for a job."""
        job = await self.get_job(job_id)
        if not job:
            return {}
        
        # Get step statistics
        stmt = select(ExecutionStep).where(ExecutionStep.job_id == job_id)
        result = await self.db.execute(stmt)
        steps = result.scalars().all()
        
        completed_steps = [s for s in steps if s.status == JobStatus.COMPLETED]
        failed_steps = [s for s in steps if s.status == JobStatus.FAILED]
        
        total_duration = sum(s.duration_ms or 0 for s in steps)
        total_records = sum(s.records_processed or 0 for s in steps)
        total_matches = sum(s.records_matched or 0 for s in steps)
        
        return {
            "job_id": str(job_id),
            "status": job.status.value if job.status else None,
            "total_steps": job.total_steps,
            "completed_steps": len(completed_steps),
            "failed_steps": len(failed_steps),
            "progress_percentage": job.progress_percentage,
            "total_duration_ms": total_duration,
            "total_records_processed": total_records,
            "total_records_matched": total_matches,
            "cpu_seconds": job.cpu_seconds,
            "memory_mb_peak": job.memory_mb_peak,
            "retry_count": job.retry_count
        }


# Storage Backend Implementation

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract storage backend for large data."""
    
    @abstractmethod
    async def store_checkpoint(
        self, job_id: uuid.UUID, step_index: int, data: bytes
    ) -> str:
        """Store checkpoint data, return path."""
        pass
    
    @abstractmethod
    async def retrieve_checkpoint(self, path: str) -> bytes:
        """Retrieve checkpoint data."""
        pass
    
    @abstractmethod
    async def store_result(
        self, job_id: uuid.UUID, step_index: int, key: str, data: bytes
    ) -> str:
        """Store result data."""
        pass
    
    @abstractmethod
    async def retrieve_result(self, path: str) -> bytes:
        """Retrieve result data."""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete stored data."""
        pass


class FileSystemStorageBackend(StorageBackend):
    """Local filesystem storage for large data."""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or settings.EXTERNAL_STORAGE_DIR
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def store_checkpoint(
        self, job_id: uuid.UUID, step_index: int, data: bytes
    ) -> str:
        """Store checkpoint data to filesystem."""
        path = self.base_path / "checkpoints" / str(job_id) / f"{step_index}.checkpoint"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)
    
    async def retrieve_checkpoint(self, path: str) -> bytes:
        """Retrieve checkpoint data from filesystem."""
        return Path(path).read_bytes()
    
    async def store_result(
        self, job_id: uuid.UUID, step_index: int, key: str, data: bytes
    ) -> str:
        """Store result data to filesystem."""
        path = self.base_path / "results" / str(job_id) / f"{step_index}_{key}.result"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)
    
    async def retrieve_result(self, path: str) -> bytes:
        """Retrieve result data from filesystem."""
        return Path(path).read_bytes()
    
    async def delete(self, path: str) -> bool:
        """Delete stored data."""
        try:
            Path(path).unlink()
            return True
        except FileNotFoundError:
            return False
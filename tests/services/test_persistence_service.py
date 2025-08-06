"""Comprehensive tests for PersistenceService."""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.persistence import (
    ExecutionCheckpoint,
    ExecutionLog,
    ExecutionStep,
    Job,
    JobEvent,
    ResultStorage,
)
from app.models.strategy_execution import JobStatus
from app.services.persistence_service import FileSystemStorageBackend, PersistenceService
from biomapper.core.models import StrategyExecutionContext


@pytest.fixture
async def test_db():
    """Create test database."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def test_storage(tmp_path):
    """Create test storage backend."""
    return FileSystemStorageBackend(tmp_path)


@pytest.fixture
async def persistence_service(test_db, test_storage):
    """Create persistence service with test database."""
    return PersistenceService(test_db, test_storage)


class TestJobLifecycle:
    """Test job creation and lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_create_job(self, persistence_service):
        """Test job creation."""
        strategy = {
            "name": "test_strategy",
            "steps": [
                {"name": "step1", "action": {"type": "TEST_ACTION"}},
                {"name": "step2", "action": {"type": "TEST_ACTION"}}
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="test_strategy",
            strategy_config=strategy,
            parameters={"param1": "value1"},
            options={"option1": "value1"},
            user_id="test_user",
            tags=["test", "integration"],
            description="Test job description"
        )
        
        assert job.id is not None
        assert job.strategy_name == "test_strategy"
        assert job.status == JobStatus.PENDING
        assert job.total_steps == 2
        assert job.input_parameters == {"param1": "value1"}
        assert job.tags == ["test", "integration"]
        assert job.description == "Test job description"
        assert job.created_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_update_job_status(self, persistence_service):
        """Test job status updates."""
        # Create job
        job = await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Update to running
        updated_job = await persistence_service.update_job_status(
            job.id,
            JobStatus.RUNNING
        )
        
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.started_at is not None
        
        # Update to completed
        updated_job = await persistence_service.update_job_status(
            job.id,
            JobStatus.COMPLETED,
            final_results={"success": True}
        )
        
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert updated_job.final_results == {"success": True}
        assert updated_job.execution_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_get_job(self, persistence_service):
        """Test job retrieval."""
        # Create job
        job = await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Retrieve job
        retrieved = await persistence_service.get_job(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.strategy_name == "test"
        
        # Test non-existent job
        fake_id = uuid.uuid4()
        not_found = await persistence_service.get_job(fake_id)
        assert not_found is None
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, persistence_service):
        """Test job listing with filters."""
        # Create multiple jobs
        for i in range(5):
            await persistence_service.create_job(
                strategy_name=f"strategy_{i}",
                strategy_config={"steps": []},
                parameters={},
                options={},
                user_id="user1" if i < 3 else "user2"
            )
        
        # List all jobs
        all_jobs = await persistence_service.list_jobs()
        assert len(all_jobs) == 5
        
        # Filter by user
        user1_jobs = await persistence_service.list_jobs(user_id="user1")
        assert len(user1_jobs) == 3
        
        user2_jobs = await persistence_service.list_jobs(user_id="user2")
        assert len(user2_jobs) == 2
        
        # Test pagination
        page1 = await persistence_service.list_jobs(limit=2, offset=0)
        assert len(page1) == 2
        
        page2 = await persistence_service.list_jobs(limit=2, offset=2)
        assert len(page2) == 2


class TestStepManagement:
    """Test execution step tracking."""
    
    @pytest.fixture
    async def test_job(self, persistence_service):
        """Create a test job."""
        return await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": [{"name": "step1"}]},
            parameters={},
            options={}
        )
    
    @pytest.mark.asyncio
    async def test_record_step_lifecycle(self, persistence_service, test_job):
        """Test complete step execution lifecycle."""
        job_id = test_job.id
        
        # Start step
        step = await persistence_service.record_step_start(
            job_id,
            0,
            "test_step",
            "TEST_ACTION",
            {"param": "value"}
        )
        
        assert step.job_id == job_id
        assert step.step_index == 0
        assert step.step_name == "test_step"
        assert step.action_type == "TEST_ACTION"
        assert step.status == JobStatus.RUNNING
        assert step.input_params == {"param": "value"}
        assert step.started_at is not None
        
        # Complete step successfully
        completed_step = await persistence_service.record_step_completion(
            job_id,
            0,
            {"output": "success"},
            {"records_processed": 100, "records_matched": 95}
        )
        
        assert completed_step.status == JobStatus.COMPLETED
        assert completed_step.output_results == {"output": "success"}
        assert completed_step.records_processed == 100
        assert completed_step.records_matched == 95
        assert completed_step.duration_ms is not None
        assert completed_step.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_record_step_failure(self, persistence_service, test_job):
        """Test step failure recording."""
        job_id = test_job.id
        
        # Start step
        await persistence_service.record_step_start(
            job_id,
            0,
            "failing_step",
            "FAIL_ACTION",
            {}
        )
        
        # Fail step
        failed_step = await persistence_service.record_step_failure(
            job_id,
            0,
            "Test error message",
            error_traceback="Traceback...",
            retry_count=1,
            can_retry=False
        )
        
        assert failed_step.status == JobStatus.FAILED
        assert failed_step.error_message == "Test error message"
        assert failed_step.error_traceback == "Traceback..."
        assert failed_step.retry_count == 1
        assert failed_step.can_retry == False
        assert failed_step.completed_at is not None


class TestCheckpointManagement:
    """Test checkpoint creation and restoration."""
    
    @pytest.fixture
    async def test_job_and_context(self, persistence_service):
        """Create test job and context."""
        job = await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        context = StrategyExecutionContext()
        context.input_identifiers = ["id1", "id2", "id3"]
        context.output_identifiers = ["out1", "out2"]
        context.custom_action_data = {"step_0": {"result": "data"}}
        
        return job, context
    
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, persistence_service, test_job_and_context):
        """Test checkpoint creation."""
        job, context = test_job_and_context
        
        checkpoint = await persistence_service.create_checkpoint(
            job.id,
            0,
            context,
            checkpoint_type="manual",
            description="Test checkpoint"
        )
        
        assert checkpoint.job_id == job.id
        assert checkpoint.step_index == 0
        assert checkpoint.checkpoint_type == "manual"
        assert checkpoint.description == "Test checkpoint"
        assert checkpoint.is_resumable == True
        assert checkpoint.size_bytes > 0
        assert checkpoint.context_data is not None or checkpoint.storage_path is not None
    
    @pytest.mark.asyncio
    async def test_restore_checkpoint(self, persistence_service, test_job_and_context):
        """Test checkpoint restoration."""
        job, original_context = test_job_and_context
        
        # Create checkpoint
        checkpoint = await persistence_service.create_checkpoint(
            job.id,
            0,
            original_context
        )
        
        # Restore checkpoint
        restored_data = await persistence_service.restore_checkpoint(checkpoint.id)
        
        assert "context" in restored_data
        assert "step_index" in restored_data
        assert "job_id" in restored_data
        
        restored_context = restored_data["context"]
        assert restored_context.input_identifiers == original_context.input_identifiers
        assert restored_context.output_identifiers == original_context.output_identifiers
        assert restored_context.custom_action_data == original_context.custom_action_data
    
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, persistence_service, test_job_and_context):
        """Test checkpoint listing."""
        job, context = test_job_and_context
        
        # Create multiple checkpoints
        checkpoints = []
        for i in range(3):
            cp = await persistence_service.create_checkpoint(
                job.id,
                i,
                context,
                checkpoint_type=f"type_{i}"
            )
            checkpoints.append(cp)
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        # List checkpoints
        listed = await persistence_service.list_checkpoints(job.id)
        assert len(listed) == 3
        
        # Should be ordered by creation time (most recent first)
        assert listed[0].step_index == 2
        assert listed[1].step_index == 1
        assert listed[2].step_index == 0
        
        # Test with limit
        limited = await persistence_service.list_checkpoints(job.id, limit=2)
        assert len(limited) == 2
    
    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, persistence_service, test_job_and_context):
        """Test getting latest checkpoint."""
        job, context = test_job_and_context
        
        # No checkpoints initially
        latest = await persistence_service.get_latest_checkpoint(job.id)
        assert latest is None
        
        # Create checkpoints
        cp1 = await persistence_service.create_checkpoint(job.id, 0, context)
        await asyncio.sleep(0.01)
        cp2 = await persistence_service.create_checkpoint(job.id, 1, context)
        
        # Get latest
        latest = await persistence_service.get_latest_checkpoint(job.id)
        assert latest.id == cp2.id
        assert latest.step_index == 1


class TestResultStorage:
    """Test result storage and retrieval."""
    
    @pytest.fixture
    async def test_job(self, persistence_service):
        """Create test job."""
        return await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_small_result(self, persistence_service, test_job):
        """Test storing and retrieving small results (inline)."""
        job_id = test_job.id
        data = {"result": "small data", "count": 42}
        
        # Store result
        storage = await persistence_service.store_result(
            job_id,
            0,
            "test_result",
            data
        )
        
        assert storage.job_id == job_id
        assert storage.step_index == 0
        assert storage.result_key == "test_result"
        assert storage.storage_type == "inline"
        assert storage.inline_data == data
        
        # Retrieve result
        retrieved = await persistence_service.retrieve_result(
            job_id,
            0,
            "test_result"
        )
        
        assert retrieved == data
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_large_result(self, persistence_service, test_job):
        """Test storing and retrieving large results (external)."""
        job_id = test_job.id
        
        # Create large data (> 100KB)
        large_data = {"data": "x" * 200000, "metadata": {"size": "large"}}
        
        # Store result
        storage = await persistence_service.store_result(
            job_id,
            0,
            "large_result",
            large_data
        )
        
        assert storage.storage_type == "filesystem"
        assert storage.external_path is not None
        assert storage.size_bytes > 100000
        
        # Retrieve result
        retrieved = await persistence_service.retrieve_result(
            job_id,
            0,
            "large_result"
        )
        
        assert retrieved == large_data
    
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_result(self, persistence_service, test_job):
        """Test retrieving non-existent result."""
        result = await persistence_service.retrieve_result(
            test_job.id,
            99,
            "nonexistent"
        )
        assert result is None


class TestLoggingAndEvents:
    """Test logging and event systems."""
    
    @pytest.fixture
    async def test_job(self, persistence_service):
        """Create test job."""
        return await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
    
    @pytest.mark.asyncio
    async def test_logging(self, persistence_service, test_job):
        """Test execution logging."""
        job_id = test_job.id
        
        # Add logs
        await persistence_service.log(
            job_id,
            "INFO",
            "Test info message",
            step_index=0,
            details={"key": "value"},
            category="test",
            component="test_component"
        )
        
        await persistence_service.log(
            job_id,
            "ERROR",
            "Test error message",
            step_index=1
        )
        
        # Commit logs
        await persistence_service.db.commit()
        
        # Retrieve logs
        all_logs = await persistence_service.get_logs(job_id)
        assert len(all_logs) == 2
        
        # Filter by level
        error_logs = await persistence_service.get_logs(job_id, level="ERROR")
        assert len(error_logs) == 1
        assert error_logs[0].message == "Test error message"
        
        # Filter by step
        step_logs = await persistence_service.get_logs(job_id, step_index=0)
        assert len(step_logs) == 1
        assert step_logs[0].details == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_events(self, persistence_service, test_job):
        """Test event emission and retrieval."""
        job_id = test_job.id
        
        # Emit events
        await persistence_service.emit_event(
            job_id,
            "step_started",
            {"step": "test_step"},
            message="Step started",
            severity="info"
        )
        
        await persistence_service.emit_event(
            job_id,
            "error",
            {"error": "test error"},
            severity="error"
        )
        
        # Commit events
        await persistence_service.db.commit()
        
        # Retrieve events
        all_events = await persistence_service.get_events(job_id)
        assert len(all_events) == 2
        
        # Filter by type
        error_events = await persistence_service.get_events(job_id, event_type="error")
        assert len(error_events) == 1
        assert error_events[0].data == {"error": "test error"}
        assert error_events[0].severity == "error"


class TestMetricsAndCleanup:
    """Test metrics calculation and data cleanup."""
    
    @pytest.mark.asyncio
    async def test_get_job_metrics(self, persistence_service):
        """Test job metrics calculation."""
        # Create job with steps
        job = await persistence_service.create_job(
            strategy_name="test",
            strategy_config={"steps": [{"name": "step1"}, {"name": "step2"}]},
            parameters={},
            options={}
        )
        
        # Add completed step
        await persistence_service.record_step_start(
            job.id, 0, "step1", "TEST_ACTION", {}
        )
        await persistence_service.record_step_completion(
            job.id, 0, {"output": "result"},
            {"records_processed": 100, "records_matched": 95}
        )
        
        # Add failed step
        await persistence_service.record_step_start(
            job.id, 1, "step2", "TEST_ACTION", {}
        )
        await persistence_service.record_step_failure(
            job.id, 1, "Test failure"
        )
        
        # Get metrics
        metrics = await persistence_service.get_job_metrics(job.id)
        
        assert metrics["job_id"] == str(job.id)
        assert metrics["total_steps"] == 2
        assert metrics["completed_steps"] == 1
        assert metrics["failed_steps"] == 1
        assert metrics["total_records_processed"] == 100
        assert metrics["total_records_matched"] == 95
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, persistence_service):
        """Test cleanup of old data."""
        # Create old job (simulate by backdating)
        old_job = await persistence_service.create_job(
            strategy_name="old_job",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Update to be completed and old
        old_date = datetime.utcnow() - timedelta(days=35)
        await persistence_service.update_job_status(
            old_job.id,
            JobStatus.COMPLETED,
            completed_at=old_date
        )
        
        # Create recent job
        recent_job = await persistence_service.create_job(
            strategy_name="recent_job",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Cleanup old data (30 days)
        await persistence_service.cleanup_old_data(days=30)
        
        # Check that recent job exists but old job is gone
        recent_exists = await persistence_service.get_job(recent_job.id)
        old_exists = await persistence_service.get_job(old_job.id)
        
        assert recent_exists is not None
        assert old_exists is None


class TestStorageBackend:
    """Test storage backend functionality."""
    
    @pytest.mark.asyncio
    async def test_filesystem_storage_checkpoint(self, test_storage):
        """Test filesystem storage for checkpoints."""
        job_id = uuid.uuid4()
        step_index = 0
        data = b"test checkpoint data"
        
        # Store checkpoint
        path = await test_storage.store_checkpoint(job_id, step_index, data)
        assert path is not None
        
        # Retrieve checkpoint
        retrieved = await test_storage.retrieve_checkpoint(path)
        assert retrieved == data
    
    @pytest.mark.asyncio
    async def test_filesystem_storage_result(self, test_storage):
        """Test filesystem storage for results."""
        job_id = uuid.uuid4()
        step_index = 1
        key = "test_result"
        data = b"test result data"
        
        # Store result
        path = await test_storage.store_result(job_id, step_index, key, data)
        assert path is not None
        
        # Retrieve result
        retrieved = await test_storage.retrieve_result(path)
        assert retrieved == data
    
    @pytest.mark.asyncio
    async def test_filesystem_storage_delete(self, test_storage):
        """Test deletion from filesystem storage."""
        job_id = uuid.uuid4()
        data = b"test data"
        
        # Store data
        path = await test_storage.store_checkpoint(job_id, 0, data)
        
        # Delete data
        success = await test_storage.delete(path)
        assert success == True
        
        # Try to delete again (should return False)
        success_again = await test_storage.delete(path)
        assert success_again == False


# Integration Tests

class TestPersistenceIntegration:
    """Integration tests combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_full_job_execution_simulation(self, persistence_service):
        """Simulate a complete job execution with persistence."""
        # Create job
        strategy = {
            "name": "integration_test",
            "steps": [
                {"name": "load_data", "action": {"type": "LOAD_ACTION"}},
                {"name": "process_data", "action": {"type": "PROCESS_ACTION"}},
                {"name": "save_results", "action": {"type": "SAVE_ACTION"}}
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="integration_test",
            strategy_config=strategy,
            parameters={"input_file": "test.csv"},
            options={"checkpoint_interval": "after_each_step"},
            user_id="test_user"
        )
        
        # Start job
        await persistence_service.update_job_status(job.id, JobStatus.RUNNING)
        
        # Simulate step execution
        context = StrategyExecutionContext()
        context.input_identifiers = ["id1", "id2", "id3"]
        
        for i, step in enumerate(strategy["steps"]):
            # Start step
            await persistence_service.record_step_start(
                job.id,
                i,
                step["name"],
                step["action"]["type"],
                step["action"].get("params", {})
            )
            
            # Log progress
            await persistence_service.log(
                job.id,
                "INFO",
                f"Starting {step['name']}",
                step_index=i
            )
            
            # Create checkpoint before important steps
            if step["name"] in ["load_data", "process_data"]:
                await persistence_service.create_checkpoint(
                    job.id,
                    i,
                    context,
                    checkpoint_type="before_step"
                )
            
            # Simulate step execution
            step_result = {
                "step": step["name"],
                "records_processed": 100 * (i + 1),
                "success": True
            }
            
            # Update context
            context.custom_action_data[f"step_{i}"] = step_result
            
            # Complete step
            await persistence_service.record_step_completion(
                job.id,
                i,
                step_result,
                {"records_processed": step_result["records_processed"]}
            )
            
            # Create checkpoint after step
            await persistence_service.create_checkpoint(
                job.id,
                i,
                context,
                checkpoint_type="after_step"
            )
            
            # Emit progress event
            await persistence_service.emit_event(
                job.id,
                "step_completed",
                {"step": step["name"], "index": i}
            )
        
        # Complete job
        final_results = {
            "total_records": 300,
            "success": True,
            "output_files": ["results.csv"]
        }
        
        await persistence_service.update_job_status(
            job.id,
            JobStatus.COMPLETED,
            final_results=final_results
        )
        
        # Verify job state
        completed_job = await persistence_service.get_job(job.id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.final_results == final_results
        
        # Verify checkpoints
        checkpoints = await persistence_service.list_checkpoints(job.id)
        assert len(checkpoints) >= 5  # before/after each critical step
        
        # Verify logs
        logs = await persistence_service.get_logs(job.id)
        assert len(logs) >= 3  # At least one per step
        
        # Verify events
        events = await persistence_service.get_events(job.id)
        assert len(events) >= 4  # job_created + 3 step_completed
        
        # Verify metrics
        metrics = await persistence_service.get_job_metrics(job.id)
        assert metrics["completed_steps"] == 3
        assert metrics["failed_steps"] == 0
        assert metrics["total_records_processed"] == 600  # 100+200+300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
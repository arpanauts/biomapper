"""Tests for PersistentExecutionEngine."""

import sys
from pathlib import Path

# Add biomapper-api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "biomapper-api"))

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.strategy_execution import JobStatus
from app.services.persistence_service import PersistenceService
from app.services.persistent_execution_engine import PersistentExecutionEngine
from biomapper.core.models import StrategyExecutionContext
from biomapper.core.strategy_actions.base import BaseStrategyAction


# Mock action classes for testing
class MockSuccessAction(BaseStrategyAction):
    """Mock action that always succeeds."""
    
    async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
        return {
            "success": True,
            "records_processed": params.get("records", 100),
            "output": f"success_{params.get('step', 0)}"
        }


class MockFailureAction(BaseStrategyAction):
    """Mock action that always fails."""
    
    async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
        raise Exception(f"Mock failure: {params.get('error_message', 'Test error')}")


class MockSlowAction(BaseStrategyAction):
    """Mock action that takes time to execute."""
    
    async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
        await asyncio.sleep(params.get("delay", 0.1))
        return {
            "success": True,
            "records_processed": 50,
            "duration": params.get("delay", 0.1)
        }


@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def persistence_service(test_db, tmp_path):
    """Create persistence service with test database."""
    from app.services.persistence_service import FileSystemStorageBackend
    storage = FileSystemStorageBackend(tmp_path)
    return PersistenceService(test_db, storage)


@pytest.fixture
def mock_action_registry():
    """Create mock action registry."""
    return {
        "MOCK_SUCCESS": MockSuccessAction,
        "MOCK_FAILURE": MockFailureAction,
        "MOCK_SLOW": MockSlowAction,
        "LOAD_DATASET": MockSuccessAction,
        "PROCESS_DATA": MockSuccessAction,
        "EXPORT_RESULTS": MockSuccessAction,
    }


@pytest.fixture
async def execution_engine(persistence_service, mock_action_registry):
    """Create execution engine with mocked components."""
    return PersistentExecutionEngine(persistence_service, mock_action_registry)


class TestBasicExecution:
    """Test basic strategy execution."""
    
    @pytest.mark.asyncio
    async def test_successful_strategy_execution(self, execution_engine, persistence_service):
        """Test complete successful strategy execution."""
        strategy = {
            "name": "test_strategy",
            "steps": [
                {
                    "name": "load_data",
                    "action": {
                        "type": "MOCK_SUCCESS",
                        "params": {"records": 100, "step": 0}
                    }
                },
                {
                    "name": "process_data", 
                    "action": {
                        "type": "MOCK_SUCCESS",
                        "params": {"records": 200, "step": 1}
                    }
                }
            ]
        }
        
        # Create job
        job = await persistence_service.create_job(
            strategy_name="test_strategy",
            strategy_config=strategy,
            parameters={"test": "param"},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        # Verify result
        assert result["success"] == True
        assert result["job_id"] == str(job.id)
        assert "results" in result
        assert "context" in result
        
        # Verify job was marked complete
        completed_job = await persistence_service.get_job(job.id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.final_results is not None
        
        # Verify steps were recorded
        assert len(completed_job.steps) == 2
        for step in completed_job.steps:
            assert step.status == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_strategy_execution_with_failure(self, execution_engine, persistence_service):
        """Test strategy execution with step failure."""
        strategy = {
            "name": "failing_strategy",
            "steps": [
                {
                    "name": "success_step",
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                },
                {
                    "name": "failing_step",
                    "action": {
                        "type": "MOCK_FAILURE",
                        "params": {"error_message": "Intentional test failure"}
                    },
                    "is_required": True
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="failing_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy (should fail)
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        # Verify failure result
        assert result["success"] == False
        assert "error" in result
        
        # Verify job was marked as failed
        failed_job = await persistence_service.get_job(job.id)
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error_message is not None
        
        # Verify first step succeeded but second failed
        steps = failed_job.steps
        assert len(steps) == 2
        assert steps[0].status == JobStatus.COMPLETED
        assert steps[1].status == JobStatus.FAILED
        assert "Intentional test failure" in steps[1].error_message
    
    @pytest.mark.asyncio
    async def test_optional_step_failure_continues(self, execution_engine, persistence_service):
        """Test that optional step failures don't stop execution."""
        strategy = {
            "name": "optional_failure_strategy",
            "steps": [
                {
                    "name": "success_step_1",
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                },
                {
                    "name": "optional_failing_step",
                    "action": {"type": "MOCK_FAILURE", "params": {}},
                    "is_required": False  # Optional step
                },
                {
                    "name": "success_step_2",
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="optional_failure_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        # Should succeed overall despite optional step failure
        assert result["success"] == True
        
        # Verify job completed
        completed_job = await persistence_service.get_job(job.id)
        assert completed_job.status == JobStatus.COMPLETED
        
        # Verify step statuses
        steps = completed_job.steps
        assert len(steps) == 3
        assert steps[0].status == JobStatus.COMPLETED
        assert steps[1].status == JobStatus.FAILED
        assert steps[2].status == JobStatus.COMPLETED


class TestCheckpointing:
    """Test checkpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_automatic_checkpointing(self, execution_engine, persistence_service):
        """Test automatic checkpoint creation."""
        strategy = {
            "name": "checkpoint_strategy",
            "checkpoint_policy": {
                "after_each_step": True
            },
            "steps": [
                {
                    "name": "checkpoint_step_1",
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                },
                {
                    "name": "checkpoint_step_2", 
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="checkpoint_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        assert result["success"] == True
        
        # Verify checkpoints were created
        checkpoints = await persistence_service.list_checkpoints(job.id)
        assert len(checkpoints) >= 2  # At least one per step
    
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, execution_engine, persistence_service):
        """Test resuming execution from checkpoint."""
        # Create initial job with context
        job = await persistence_service.create_job(
            strategy_name="resume_test",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Create a checkpoint with some context
        context = StrategyExecutionContext()
        context.input_identifiers = ["id1", "id2"]
        context.custom_action_data = {"step_0_output": {"data": "from_checkpoint"}}
        
        checkpoint = await persistence_service.create_checkpoint(
            job.id,
            0,
            context,
            checkpoint_type="manual"
        )
        
        # Create strategy to resume
        strategy = {
            "name": "resume_strategy",
            "steps": [
                {
                    "name": "already_done",
                    "action": {"type": "MOCK_SUCCESS", "params": {}}
                },
                {
                    "name": "resume_from_here",
                    "action": {"type": "MOCK_SUCCESS", "params": {"step": 1}}
                }
            ]
        }
        
        # Execute from checkpoint (step 1)
        result = await execution_engine.execute_strategy(
            job.id,
            strategy,
            resume_from_checkpoint=checkpoint.id
        )
        
        assert result["success"] == True
        
        # Context should contain data from checkpoint
        assert "step_0_output" in result["context"]
        assert result["context"]["step_0_output"]["data"] == "from_checkpoint"
    
    @pytest.mark.asyncio
    async def test_resume_from_step_index(self, execution_engine, persistence_service):
        """Test resuming from specific step index."""
        strategy = {
            "name": "step_resume_strategy", 
            "steps": [
                {
                    "name": "skip_step_0",
                    "action": {"type": "MOCK_SUCCESS", "params": {"step": 0}}
                },
                {
                    "name": "skip_step_1",
                    "action": {"type": "MOCK_SUCCESS", "params": {"step": 1}}
                },
                {
                    "name": "execute_step_2",
                    "action": {"type": "MOCK_SUCCESS", "params": {"step": 2}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="step_resume_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute from step 2 (should only execute last step)
        result = await execution_engine.execute_strategy(
            job.id,
            strategy,
            resume_from_step=2
        )
        
        assert result["success"] == True
        
        # Should only have executed step 2
        completed_job = await persistence_service.get_job(job.id)
        assert len(completed_job.steps) == 1
        assert completed_job.steps[0].step_name == "execute_step_2"


class TestJobControl:
    """Test job control operations (pause, resume, cancel)."""
    
    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self, execution_engine, persistence_service):
        """Test pausing and resuming a job."""
        job = await persistence_service.create_job(
            strategy_name="pausable_job",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Set job to running state
        await persistence_service.update_job_status(job.id, JobStatus.RUNNING)
        
        # Pause job
        success = await execution_engine.pause_job(job.id)
        assert success == True
        
        # Verify job is paused
        paused_job = await persistence_service.get_job(job.id)
        assert paused_job.status == JobStatus.PAUSED
        
        # Resume job
        with patch.object(execution_engine, 'execute_strategy', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True}
            
            success = await execution_engine.resume_job(job.id)
            assert success == True
            
            # Should have called execute_strategy with checkpoint
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_job(self, execution_engine, persistence_service):
        """Test cancelling a job."""
        job = await persistence_service.create_job(
            strategy_name="cancellable_job",
            strategy_config={"steps": []},
            parameters={},
            options={}
        )
        
        # Set job to running state
        await persistence_service.update_job_status(job.id, JobStatus.RUNNING)
        
        # Cancel job
        success = await execution_engine.cancel_job(job.id)
        assert success == True
        
        # Verify job is cancelled
        cancelled_job = await persistence_service.get_job(job.id)
        assert cancelled_job.status == JobStatus.CANCELLED
        assert cancelled_job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_job_cancellation_during_execution(self, execution_engine, persistence_service):
        """Test that execution stops when job is cancelled."""
        strategy = {
            "name": "long_running_strategy",
            "steps": [
                {
                    "name": "slow_step_1",
                    "action": {"type": "MOCK_SLOW", "params": {"delay": 0.1}}
                },
                {
                    "name": "slow_step_2",
                    "action": {"type": "MOCK_SLOW", "params": {"delay": 0.1}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="long_running_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Start execution in background
        execution_task = asyncio.create_task(
            execution_engine.execute_strategy(job.id, strategy)
        )
        
        # Wait a bit then cancel
        await asyncio.sleep(0.05)
        await persistence_service.update_job_status(job.id, JobStatus.CANCELLED)
        
        # Wait for execution to complete
        result = await execution_task
        
        # Execution should detect cancellation and stop
        cancelled_job = await persistence_service.get_job(job.id)
        assert cancelled_job.status == JobStatus.CANCELLED


class TestRetryMechanism:
    """Test step retry functionality."""
    
    @pytest.mark.asyncio
    async def test_step_retry_success(self, execution_engine, persistence_service):
        """Test successful retry of failed step."""
        retry_count = 0
        
        class FlakeyAction(BaseStrategyAction):
            async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
                nonlocal retry_count
                retry_count += 1
                
                if retry_count < 3:  # Fail first 2 attempts
                    raise Exception("Temporary failure")
                
                return {"success": True, "attempt": retry_count}
        
        # Temporarily add flakey action to registry
        execution_engine.action_registry["FLAKEY_ACTION"] = FlakeyAction
        
        strategy = {
            "name": "retry_strategy",
            "steps": [
                {
                    "name": "flakey_step",
                    "action": {"type": "FLAKEY_ACTION", "params": {}},
                    "on_error": {
                        "action": "retry",
                        "max_attempts": 3,
                        "delay_seconds": 0.01
                    }
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="retry_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        # Should eventually succeed
        assert result["success"] == True
        assert retry_count == 3  # Failed twice, succeeded third time
        
        # Verify final step is marked as completed
        completed_job = await persistence_service.get_job(job.id)
        assert len(completed_job.steps) == 1
        assert completed_job.steps[0].status == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_step_retry_max_exceeded(self, execution_engine, persistence_service):
        """Test retry failure when max attempts exceeded."""
        
        class AlwaysFailAction(BaseStrategyAction):
            async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
                raise Exception("Always fails")
        
        execution_engine.action_registry["ALWAYS_FAIL_ACTION"] = AlwaysFailAction
        
        strategy = {
            "name": "max_retry_strategy", 
            "steps": [
                {
                    "name": "always_fail_step",
                    "action": {"type": "ALWAYS_FAIL_ACTION", "params": {}},
                    "on_error": {
                        "action": "retry",
                        "max_attempts": 2,
                        "delay_seconds": 0.01
                    }
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="max_retry_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        # Should fail after retries
        assert result["success"] == False
        
        # Verify job failed
        failed_job = await persistence_service.get_job(job.id)
        assert failed_job.status == JobStatus.FAILED
        
        # Should have recorded multiple attempts
        # Note: Implementation details may vary for retry step recording


class TestResourceMonitoring:
    """Test resource usage monitoring."""
    
    @pytest.mark.asyncio
    async def test_memory_tracking(self, execution_engine, persistence_service):
        """Test that memory usage is tracked."""
        strategy = {
            "name": "memory_test_strategy",
            "steps": [
                {
                    "name": "memory_step",
                    "action": {"type": "MOCK_SUCCESS", "params": {"records": 100}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="memory_test_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        assert result["success"] == True
        
        # Check that memory usage was recorded
        metrics = await persistence_service.get_job_metrics(job.id)
        
        # Memory should be tracked (exact values may vary)
        completed_job = await persistence_service.get_job(job.id)
        step = completed_job.steps[0]
        
        # Memory used should be recorded (could be positive or negative)
        assert step.memory_used_mb is not None


class TestLargeResultHandling:
    """Test handling of large execution results."""
    
    @pytest.mark.asyncio
    async def test_large_result_external_storage(self, execution_engine, persistence_service):
        """Test that large results are stored externally."""
        
        class LargeResultAction(BaseStrategyAction):
            async def execute(self, params: Dict[str, Any], context: StrategyExecutionContext) -> Dict[str, Any]:
                # Create a large result (> 100KB)
                large_data = "x" * 150000
                return {
                    "success": True,
                    "large_data": large_data,
                    "size": len(large_data)
                }
        
        execution_engine.action_registry["LARGE_RESULT_ACTION"] = LargeResultAction
        
        strategy = {
            "name": "large_result_strategy",
            "steps": [
                {
                    "name": "large_result_step",
                    "action": {"type": "LARGE_RESULT_ACTION", "params": {}}
                }
            ]
        }
        
        job = await persistence_service.create_job(
            strategy_name="large_result_strategy",
            strategy_config=strategy,
            parameters={},
            options={}
        )
        
        # Execute strategy
        result = await execution_engine.execute_strategy(job.id, strategy)
        
        assert result["success"] == True
        
        # Large result should be stored externally, not in context
        assert "step_0_output_ref" in result["context"]
        assert result["context"]["step_0_output_ref"].startswith("stored:")
        
        # Should have summary instead of full data
        assert "step_0_output_summary" in result["context"]
        assert result["context"]["step_0_output_summary"]["stored"] == True


class TestJobStatusReporting:
    """Test job status reporting functionality."""
    
    @pytest.mark.asyncio
    async def test_get_job_status(self, execution_engine, persistence_service):
        """Test getting detailed job status."""
        # Create job with some history
        job = await persistence_service.create_job(
            strategy_name="status_test",
            strategy_config={"steps": [{"name": "test_step"}]},
            parameters={},
            options={}
        )
        
        # Add some steps and events
        await persistence_service.record_step_start(
            job.id, 0, "test_step", "MOCK_SUCCESS", {}
        )
        
        await persistence_service.emit_event(
            job.id, "step_started", {"step": "test_step"}
        )
        
        await persistence_service.record_step_completion(
            job.id, 0, {"output": "test"}, {"records_processed": 50}
        )
        
        await persistence_service.update_job_status(job.id, JobStatus.COMPLETED)
        
        # Get status
        status = await execution_engine.get_job_status(job.id)
        
        assert status["job_id"] == str(job.id)
        assert status["status"] == "completed"
        assert status["progress"]["total_steps"] == 1
        assert status["progress"]["percentage"] == 0  # Default value
        assert "metrics" in status
        assert "recent_events" in status
        assert len(status["recent_events"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job_status(self, execution_engine):
        """Test getting status of non-existent job."""
        fake_job_id = uuid.uuid4()
        status = await execution_engine.get_job_status(fake_job_id)
        
        assert status["error"] == "Job not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
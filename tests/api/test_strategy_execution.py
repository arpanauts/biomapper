"""Unit tests for enhanced strategy execution."""

import sys
from pathlib import Path

# Add biomapper-api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "biomapper-api"))

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Checkpoint, Job, JobLog, JobStep
from app.models.strategy_execution import (
    ExecutionOptions,
    JobStatus,
    PrerequisiteCheck,
    PrerequisiteReport,
    StrategyExecutionRequest,
)
from app.services.action_registry import ActionRegistryService
from app.services.execution_engine import CheckpointManager, EnhancedExecutionEngine, ProgressTracker
from app.services.prerequisites import PrerequisiteChecker


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_action_registry():
    """Mock action registry."""
    registry = MagicMock(spec=ActionRegistryService)
    registry._registry = {
        "TEST_ACTION": MagicMock(),
        "LOAD_DATASET_IDENTIFIERS": MagicMock(),
    }
    registry.validate_action_params.return_value = {}
    registry.get_action.return_value = MagicMock()
    return registry


@pytest.fixture
def sample_strategy():
    """Sample strategy for testing."""
    return {
        "name": "test_strategy",
        "description": "Test strategy",
        "steps": [
            {
                "name": "load_data",
                "action_type": "LOAD_DATASET_IDENTIFIERS",
                "params": {
                    "file_path": "/tmp/test.csv"
                },
                "is_required": True
            },
            {
                "name": "process_data",
                "action_type": "TEST_ACTION",
                "params": {},
                "condition": "has_results"
            }
        ]
    }


@pytest.fixture
def sample_job(mock_db):
    """Sample job for testing."""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        strategy_name="test_strategy",
        strategy_config={},
        status=JobStatus.PENDING,
        parameters={},
        options={},
        total_steps=2
    )
    return job


class TestCheckpointManager:
    """Test checkpoint manager functionality."""
    
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, mock_db):
        """Test creating a checkpoint."""
        job_id = str(uuid.uuid4())
        manager = CheckpointManager(mock_db, job_id)
        
        context = {"test_key": "test_value", "step_1_output": [1, 2, 3]}
        checkpoint_id = await manager.create_checkpoint(
            "test_step",
            1,
            context,
            checkpoint_type="automatic"
        )
        
        assert checkpoint_id
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_restore_checkpoint(self, mock_db):
        """Test restoring from checkpoint."""
        job_id = str(uuid.uuid4())
        checkpoint_id = str(uuid.uuid4())
        
        mock_checkpoint = Checkpoint(
            id=checkpoint_id,
            job_id=job_id,
            step_name="test_step",
            step_index=1,
            context_snapshot={"test_key": "test_value"}
        )
        mock_db.get.return_value = mock_checkpoint
        
        manager = CheckpointManager(mock_db, job_id)
        restored = await manager.restore_checkpoint(checkpoint_id)
        
        assert restored["step_name"] == "test_step"
        assert restored["step_index"] == 1
        assert "context" in restored
    
    @pytest.mark.asyncio
    async def test_cleanup_checkpoints(self, mock_db):
        """Test checkpoint cleanup."""
        job_id = str(uuid.uuid4())
        manager = CheckpointManager(mock_db, job_id)
        
        await manager.cleanup_checkpoints()
        
        assert mock_db.execute.called
        assert mock_db.commit.called


class TestProgressTracker:
    """Test progress tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_update_progress(self, mock_db, sample_job):
        """Test progress updates."""
        mock_db.get.return_value = sample_job
        
        tracker = ProgressTracker(mock_db, sample_job.id)
        
        await tracker.update_progress(
            "test_step",
            1,
            2,
            "Processing..."
        )
        
        assert sample_job.current_step == "test_step"
        assert sample_job.current_step_index == 1
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_log_message(self, mock_db):
        """Test logging messages."""
        job_id = str(uuid.uuid4())
        tracker = ProgressTracker(mock_db, job_id)
        
        await tracker.log_message(
            "INFO",
            "Test message",
            step_name="test_step",
            details={"key": "value"}
        )
        
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Check the log entry was created correctly
        log_entry = mock_db.add.call_args[0][0]
        assert isinstance(log_entry, JobLog)
        assert log_entry.level == "INFO"
        assert log_entry.message == "Test message"
    
    @pytest.mark.asyncio
    async def test_progress_callbacks(self, mock_db, sample_job):
        """Test progress callbacks are called."""
        mock_db.get.return_value = sample_job
        
        tracker = ProgressTracker(mock_db, sample_job.id)
        
        callback = AsyncMock()
        tracker.add_callback(callback)
        
        await tracker.update_progress("test_step", 1, 2)
        
        assert callback.called
        progress_data = callback.call_args[0][0]
        assert progress_data["current_step"] == "test_step"
        assert progress_data["progress_percentage"] == 50.0


class TestEnhancedExecutionEngine:
    """Test enhanced execution engine."""
    
    @pytest.mark.asyncio
    async def test_execute_strategy_success(self, mock_db, mock_action_registry, sample_job, sample_strategy):
        """Test successful strategy execution."""
        engine = EnhancedExecutionEngine(mock_db, mock_action_registry._registry)
        
        # Mock action execution
        mock_action = MagicMock()
        mock_action.execute = AsyncMock(return_value={"result": "success"})
        mock_action_registry._registry["LOAD_DATASET_IDENTIFIERS"] = lambda: mock_action
        mock_action_registry._registry["TEST_ACTION"] = lambda: mock_action
        
        checkpoint_manager = AsyncMock(spec=CheckpointManager)
        progress_tracker = AsyncMock(spec=ProgressTracker)
        
        context = {}
        result = await engine.execute_strategy(
            sample_job,
            sample_strategy,
            context,
            checkpoint_manager,
            progress_tracker
        )
        
        assert sample_job.status == JobStatus.COMPLETED
        assert sample_job.completed_at is not None
        assert progress_tracker.update_progress.called
        assert progress_tracker.log_message.called
    
    @pytest.mark.asyncio
    async def test_execute_strategy_with_failure(self, mock_db, mock_action_registry, sample_job, sample_strategy):
        """Test strategy execution with step failure."""
        engine = EnhancedExecutionEngine(mock_db, mock_action_registry._registry)
        
        # Mock action that fails
        mock_action = MagicMock()
        mock_action.execute = AsyncMock(side_effect=Exception("Test error"))
        mock_action_registry._registry["LOAD_DATASET_IDENTIFIERS"] = lambda: mock_action
        
        checkpoint_manager = AsyncMock(spec=CheckpointManager)
        progress_tracker = AsyncMock(spec=ProgressTracker)
        
        context = {}
        
        with pytest.raises(Exception) as exc_info:
            await engine.execute_strategy(
                sample_job,
                sample_strategy,
                context,
                checkpoint_manager,
                progress_tracker
            )
        
        assert "Test error" in str(exc_info.value)
        assert sample_job.status == JobStatus.FAILED
        assert sample_job.error_message is not None
    
    @pytest.mark.asyncio
    async def test_execute_step_with_retry(self, mock_db, mock_action_registry, sample_job):
        """Test step execution with retry logic."""
        engine = EnhancedExecutionEngine(mock_db, mock_action_registry._registry)
        
        # Mock action that fails first then succeeds
        mock_action = MagicMock()
        mock_action.execute = AsyncMock(
            side_effect=[Exception("Temporary error"), {"result": "success"}]
        )
        mock_action_registry._registry["TEST_ACTION"] = lambda: mock_action
        
        progress_tracker = AsyncMock(spec=ProgressTracker)
        sample_job.options = {"retry_failed_steps": True, "max_retries": 3}
        
        step = {
            "name": "test_step",
            "action_type": "TEST_ACTION",
            "params": {}
        }
        
        result = await engine.execute_step_with_retry(
            step,
            {},
            sample_job,
            progress_tracker
        )
        
        assert result["status"] == "success"
        assert mock_action.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self, mock_db):
        """Test pausing and resuming a job."""
        engine = EnhancedExecutionEngine(mock_db, {})
        
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, status=JobStatus.RUNNING)
        mock_db.get.return_value = job
        
        # Test pause
        success = await engine.pause_job(job_id)
        assert success
        assert job.status == JobStatus.PAUSED
        
        # Test resume
        job.status = JobStatus.PAUSED
        success = await engine.resume_job(job_id)
        assert success
        assert job.status == JobStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_cancel_job(self, mock_db):
        """Test cancelling a job."""
        engine = EnhancedExecutionEngine(mock_db, {})
        
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, status=JobStatus.RUNNING)
        mock_db.get.return_value = job
        
        success = await engine.cancel_job(job_id)
        assert success
        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_evaluate_condition(self, mock_db):
        """Test condition evaluation."""
        engine = EnhancedExecutionEngine(mock_db, {})
        
        context = {"results": [1, 2, 3], "error_count": 2}
        
        # Test has_results condition
        assert await engine.evaluate_condition("has_results", context) is True
        assert await engine.evaluate_condition("has_results", {}) is False
        
        # Test exists condition
        assert await engine.evaluate_condition("exists:results", context) is True
        assert await engine.evaluate_condition("exists:missing", context) is False
        
        # Test no condition
        assert await engine.evaluate_condition(None, context) is True


class TestPrerequisiteChecker:
    """Test prerequisite checking."""
    
    @pytest.mark.asyncio
    async def test_check_input_files(self):
        """Test checking input file prerequisites."""
        checker = PrerequisiteChecker()
        
        strategy = {
            "steps": [
                {
                    "name": "load",
                    "params": {
                        "file_path": "/tmp/test_file.csv"
                    },
                    "is_required": True
                }
            ]
        }
        
        checks = await checker._check_input_files(strategy)
        assert len(checks) == 1
        assert checks[0].category == "file"
        assert checks[0].required is True
    
    @pytest.mark.asyncio
    async def test_check_output_dirs(self):
        """Test checking output directory prerequisites."""
        checker = PrerequisiteChecker()
        
        strategy = {
            "steps": [
                {
                    "name": "export",
                    "params": {
                        "output_dir": "/tmp/results"
                    }
                }
            ],
            "config": {
                "output_dir": "/tmp/biomapper/results"
            }
        }
        
        checks = await checker._check_output_dirs(strategy)
        assert len(checks) >= 1
        assert any(c.category == "directory" for c in checks)
    
    @pytest.mark.asyncio
    async def test_check_system_resources(self):
        """Test checking system resource prerequisites."""
        checker = PrerequisiteChecker()
        
        checks = await checker._check_system_resources({})
        assert len(checks) >= 2
        
        # Check disk space
        disk_check = next(c for c in checks if c.name == "Disk Space")
        assert disk_check.category == "resource"
        assert disk_check.required is True
        
        # Check memory
        mem_check = next(c for c in checks if c.name == "Memory")
        assert mem_check.category == "resource"
        assert mem_check.required is True
    
    @pytest.mark.asyncio
    async def test_check_all_prerequisites(self):
        """Test complete prerequisite checking."""
        checker = PrerequisiteChecker()
        
        strategy = {
            "name": "test_strategy",
            "steps": [
                {
                    "name": "load",
                    "action_type": "LOAD_DATASET_IDENTIFIERS",
                    "params": {
                        "file_path": "/tmp/test.csv"
                    }
                }
            ]
        }
        
        report = await checker.check_all(strategy)
        
        assert isinstance(report, PrerequisiteReport)
        assert report.total_checks > 0
        assert isinstance(report.checks, list)
        assert isinstance(report.can_proceed, bool)
        
        if not report.all_passed:
            assert len(report.recommendations) > 0


class TestActionRegistry:
    """Test action registry functionality."""
    
    def test_register_and_get_action(self):
        """Test registering and retrieving actions."""
        registry = ActionRegistryService()
        
        # Mock action class
        class TestAction:
            """Test action for unit tests."""
            pass
        
        registry.register_action("TEST_ACTION", TestAction)
        
        retrieved = registry.get_action("TEST_ACTION")
        assert retrieved == TestAction
    
    def test_validate_action_params(self):
        """Test parameter validation."""
        registry = ActionRegistryService()
        
        # Mock action with params model
        class TestAction:
            def get_params_model(self):
                from pydantic import BaseModel
                class Params(BaseModel):
                    required_field: str
                    optional_field: int = 10
                return Params
        
        registry.register_action("TEST_ACTION", TestAction)
        
        # Valid params
        valid_params = {"required_field": "test"}
        validated = registry.validate_action_params("TEST_ACTION", valid_params)
        assert validated["required_field"] == "test"
        assert validated["optional_field"] == 10
        
        # Invalid params
        with pytest.raises(ValueError):
            registry.validate_action_params("TEST_ACTION", {})
    
    def test_list_available_actions(self):
        """Test listing available actions."""
        registry = ActionRegistryService()
        
        actions = registry.list_available_actions()
        assert isinstance(actions, list)
        
        # Should have loaded built-in actions
        assert len(actions) > 0
    
    def test_search_actions(self):
        """Test searching actions."""
        registry = ActionRegistryService()
        
        # Search for load actions
        results = registry.search_actions("load")
        assert isinstance(results, list)
        
        # Check if LOAD_DATASET_IDENTIFIERS is in results
        action_names = [r.name for r in results]
        assert any("LOAD" in name for name in action_names)
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        registry = ActionRegistryService()
        
        stats = registry.get_registry_stats()
        assert "total_actions" in stats
        assert "categories" in stats
        assert stats["total_actions"] > 0


@pytest.mark.asyncio
async def test_execute_strategy_with_progress():
    """Test strategy execution with progress tracking."""
    # This would be an integration test with the API
    pass


@pytest.mark.asyncio
async def test_job_cancellation():
    """Test job can be cancelled mid-execution."""
    # This would be an integration test with the API
    pass


@pytest.mark.asyncio
async def test_checkpoint_resume():
    """Test resuming from checkpoint after failure."""
    # This would be an integration test with the API
    pass


@pytest.mark.asyncio
async def test_conditional_step_execution():
    """Test conditional steps are properly evaluated."""
    # This would be an integration test with the API
    pass
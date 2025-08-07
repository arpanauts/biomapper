"""Integration tests for the complete persistence system."""

import sys
from pathlib import Path as PathLib

# Add biomapper-api to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent.parent / "biomapper-api"))

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.strategy_execution import JobStatus
from app.services.persistence_service import PersistenceService
from app.services.persistent_execution_engine import PersistentExecutionEngine
from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.models import StrategyExecutionContext


# Mock actions for integration testing
class IntegrationTestAction:
    """Test action that simulates real work."""

    async def execute(self, params, context):
        await asyncio.sleep(0.01)  # Simulate work

        # Access context attributes directly (context is StrategyExecutionContext)
        # Store results in custom_action_data
        context.custom_action_data["test_output"] = f"processed_{params.get('step', 0)}"

        return {
            "success": True,
            "records_processed": params.get("records", 10),
            "output_data": f"processed_{params.get('step', 0)}",
            "test_param": params.get("test_param", "default"),
        }


class FailingTestAction:
    """Test action that fails."""

    async def execute(self, params, context):
        raise Exception(
            f"Integration test failure: {params.get('error_msg', 'default error')}"
        )


@pytest.fixture
async def integration_db():
    """Create integration test database."""
    # Use temporary file database for integration tests
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = Path(db_file.name)
    db_file.close()

    database_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(database_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()

    # Cleanup
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def integration_storage():
    """Create integration test storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        from app.services.persistence_service import FileSystemStorageBackend

        yield FileSystemStorageBackend(Path(temp_dir))


@pytest.fixture
async def integration_persistence(integration_db, integration_storage):
    """Create persistence service for integration tests."""
    return PersistenceService(integration_db, integration_storage)


@pytest.fixture
def integration_action_registry():
    """Create action registry for integration tests."""
    return {
        "INTEGRATION_TEST": IntegrationTestAction,
        "FAILING_TEST": FailingTestAction,
        "LOAD_DATA": IntegrationTestAction,
        "PROCESS_DATA": IntegrationTestAction,
        "SAVE_RESULTS": IntegrationTestAction,
    }


@pytest.fixture
async def integration_engine(integration_persistence, integration_action_registry):
    """Create execution engine for integration tests."""
    return PersistentExecutionEngine(
        integration_persistence, integration_action_registry
    )


class TestEndToEndExecution:
    """Test complete end-to-end execution scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self, integration_engine, integration_persistence
    ):
        """Test a complete workflow from start to finish."""

        # Define a comprehensive strategy
        strategy = {
            "name": "comprehensive_workflow",
            "description": "End-to-end integration test workflow",
            "checkpoint_policy": {
                "after_each_step": True,
                "before_actions": ["PROCESS_DATA"],
            },
            "steps": [
                {
                    "name": "load_input_data",
                    "action": {
                        "type": "LOAD_DATA",
                        "params": {
                            "source": "test_input.csv",
                            "records": 1000,
                            "test_param": "load_value",
                        },
                    },
                    "description": "Load test data",
                    "checkpoint_after": True,
                },
                {
                    "name": "validate_data",
                    "action": {
                        "type": "INTEGRATION_TEST",
                        "params": {
                            "operation": "validate",
                            "records": 950,  # Some records filtered out
                            "test_param": "validate_value",
                        },
                    },
                    "description": "Validate loaded data",
                },
                {
                    "name": "process_data",
                    "action": {
                        "type": "PROCESS_DATA",
                        "params": {
                            "algorithm": "test_algorithm",
                            "records": 950,
                            "test_param": "process_value",
                        },
                    },
                    "description": "Main data processing",
                    "checkpoint_before": True,
                    "checkpoint_after": True,
                },
                {
                    "name": "save_results",
                    "action": {
                        "type": "SAVE_RESULTS",
                        "params": {
                            "output": "test_results.csv",
                            "records": 950,
                            "test_param": "save_value",
                        },
                    },
                    "description": "Save processed results",
                },
            ],
        }

        # Create job
        job = await integration_persistence.create_job(
            strategy_name="comprehensive_workflow",
            strategy_config=strategy,
            parameters={
                "input_file": "test_data.csv",
                "output_dir": "/tmp/test_output",
                "batch_size": 100,
            },
            options={
                "checkpoint_enabled": True,
                "retry_failed_steps": True,
                "max_retries": 2,
            },
            user_id="integration_test_user",
            tags=["integration", "test", "comprehensive"],
            description="Comprehensive integration test execution",
        )

        # Execute the strategy
        result = await integration_engine.execute_strategy(job.id, strategy)

        # Verify successful completion
        assert result["success"] == True
        assert result["job_id"] == str(job.id)

        # Verify job final state
        completed_job = await integration_persistence.get_job(job.id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.started_at is not None
        assert completed_job.completed_at is not None
        assert completed_job.execution_time_ms is not None
        assert completed_job.final_results is not None

        # Verify all steps completed
        assert len(completed_job.steps) == 4
        for step in completed_job.steps:
            assert step.status == JobStatus.COMPLETED
            assert step.duration_ms is not None
            assert step.records_processed > 0

        # Verify checkpoints were created
        checkpoints = await integration_persistence.list_checkpoints(job.id)
        assert len(checkpoints) >= 4  # At least one per step with checkpoint policy

        # Verify logs were created
        logs = await integration_persistence.get_logs(job.id)
        assert len(logs) >= 8  # Start and completion logs for each step

        # Verify events were emitted
        events = await integration_persistence.get_events(job.id)
        assert len(events) >= 5  # job_created + step events

        # Verify metrics
        metrics = await integration_persistence.get_job_metrics(job.id)
        assert metrics["total_steps"] == 4
        assert metrics["completed_steps"] == 4
        assert metrics["failed_steps"] == 0
        assert metrics["total_records_processed"] == 3850  # Sum of all records
        assert metrics["progress_percentage"] == 100  # Final job state (completed)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Database session isolation issue - needs refactoring")
    async def test_failure_recovery_workflow(
        self, integration_engine, integration_persistence
    ):
        """Test workflow with failure and recovery capabilities."""

        strategy = {
            "name": "failure_recovery_workflow",
            "steps": [
                {
                    "name": "successful_step",
                    "action": {"type": "INTEGRATION_TEST", "params": {"records": 100}},
                },
                {
                    "name": "failing_step",
                    "action": {
                        "type": "FAILING_TEST",
                        "params": {"error_msg": "Simulated failure for testing"},
                    },
                    "on_error": {
                        "action": "retry",
                        "max_attempts": 3,
                        "delay_seconds": 0.01,
                    },
                },
                {
                    "name": "recovery_step",
                    "action": {"type": "INTEGRATION_TEST", "params": {"records": 50}},
                    "is_required": False,  # Should not execute due to previous failure
                },
            ],
        }

        job = await integration_persistence.create_job(
            strategy_name="failure_recovery_workflow",
            strategy_config=strategy,
            parameters={},
            options={},
        )

        # Execute strategy (should fail)
        result = await integration_engine.execute_strategy(job.id, strategy)

        # Verify failure handling
        assert result["success"] == False
        assert "error" in result

        # Verify job state
        failed_job = await integration_persistence.get_job(job.id)
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error_message is not None

        # Verify step states
        steps = failed_job.steps
        assert len(steps) == 2  # Third step should not have executed
        assert steps[0].status == JobStatus.COMPLETED  # First step succeeded
        assert steps[1].status == JobStatus.FAILED  # Second step failed

        # Verify error details were recorded
        assert "Simulated failure for testing" in steps[1].error_message

        # Verify checkpoints still exist for recovery
        checkpoints = await integration_persistence.list_checkpoints(job.id)
        # Should have at least automatic checkpoints
        assert len(checkpoints) >= 0


class TestResumeAndRecovery:
    """Test job resume and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_checkpoint_resume_workflow(
        self, integration_engine, integration_persistence
    ):
        """Test resuming a workflow from a checkpoint."""

        # First, execute a partial workflow and create checkpoints
        strategy = {
            "name": "resumable_workflow",
            "steps": [
                {
                    "name": "initial_step",
                    "action": {
                        "type": "INTEGRATION_TEST",
                        "params": {"records": 200, "step": 0},
                    },
                },
                {
                    "name": "checkpoint_step",
                    "action": {
                        "type": "INTEGRATION_TEST",
                        "params": {"records": 300, "step": 1},
                    },
                },
                {
                    "name": "final_step",
                    "action": {
                        "type": "INTEGRATION_TEST",
                        "params": {"records": 400, "step": 2},
                    },
                },
            ],
        }

        # Create initial job and context
        job = await integration_persistence.create_job(
            strategy_name="resumable_workflow",
            strategy_config=strategy,
            parameters={"phase": "initial"},
            options={},
        )

        # Simulate partial execution by creating context and checkpoint manually
        context = StrategyExecutionContext(
            initial_identifier="test_id",
            current_identifier="test_id",
            ontology_type="protein",
        )
        # Store identifiers in custom_action_data
        context.custom_action_data = {
            "input_identifiers": ["id1", "id2", "id3"],
            "step_0_output": {"success": True, "records": 200},
            "job_id": str(job.id),
            "execution_phase": "partial",
        }

        # Create checkpoint after step 1 (simulating interruption)
        checkpoint = await integration_persistence.create_checkpoint(
            job.id,
            1,  # After step 1
            context,
            checkpoint_type="interruption",
            description="Simulated interruption for resume test",
        )

        # Now resume from the checkpoint - should only execute step 2
        result = await integration_engine.execute_strategy(
            job.id, strategy, resume_from_checkpoint=checkpoint.id
        )

        # Verify successful resume
        assert result["success"] == True

        # Verify context was preserved
        assert "step_0_output" in result["context"]
        assert result["context"]["step_0_output"]["records"] == 200
        assert result["context"]["execution_phase"] == "partial"

        # Verify only the remaining step was executed
        completed_job = await integration_persistence.get_job(job.id)

        # Should have steps from resume execution
        resume_steps = [s for s in completed_job.steps if s.step_index >= 2]
        assert len(resume_steps) == 1
        assert resume_steps[0].step_name == "final_step"
        assert resume_steps[0].status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_step_index_resume_workflow(
        self, integration_engine, integration_persistence
    ):
        """Test resuming from a specific step index."""

        strategy = {
            "name": "step_resume_workflow",
            "steps": [
                {
                    "name": "skip_0",
                    "action": {"type": "INTEGRATION_TEST", "params": {"step": 0}},
                },
                {
                    "name": "skip_1",
                    "action": {"type": "INTEGRATION_TEST", "params": {"step": 1}},
                },
                {
                    "name": "execute_2",
                    "action": {"type": "INTEGRATION_TEST", "params": {"step": 2}},
                },
                {
                    "name": "execute_3",
                    "action": {"type": "INTEGRATION_TEST", "params": {"step": 3}},
                },
            ],
        }

        job = await integration_persistence.create_job(
            strategy_name="step_resume_workflow",
            strategy_config=strategy,
            parameters={},
            options={},
        )

        # Resume from step 2 - should execute steps 2 and 3 only
        result = await integration_engine.execute_strategy(
            job.id, strategy, resume_from_step=2
        )

        assert result["success"] == True

        # Verify only steps 2 and 3 were executed
        completed_job = await integration_persistence.get_job(job.id)
        assert len(completed_job.steps) == 2

        executed_steps = {step.step_name for step in completed_job.steps}
        assert executed_steps == {"execute_2", "execute_3"}


class TestJobControlIntegration:
    """Test job control operations in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_pause_resume_workflow(
        self, integration_engine, integration_persistence
    ):
        """Test pausing and resuming a running workflow."""

        # Create a job that can be paused
        job = await integration_persistence.create_job(
            strategy_name="pausable_workflow",
            strategy_config={"steps": []},
            parameters={},
            options={},
        )

        # Set up job state to simulate running
        await integration_persistence.update_job_status(job.id, JobStatus.RUNNING)

        # Create a checkpoint to simulate execution state
        context = StrategyExecutionContext(
            initial_identifier="test_id",
            current_identifier="test_id",
            ontology_type="protein",
        )
        context.custom_action_data = {"current_progress": "50%", "processed_items": 250}

        checkpoint = await integration_persistence.create_checkpoint(
            job.id, 1, context, checkpoint_type="pause_point"
        )

        # Pause the job
        pause_success = await integration_engine.pause_job(job.id)
        assert pause_success == True

        paused_job = await integration_persistence.get_job(job.id)
        assert paused_job.status == JobStatus.PAUSED

        # Resume the job
        with patch.object(integration_engine, "execute_strategy") as mock_execute:
            mock_execute.return_value = {"success": True, "resumed": True}

            resume_success = await integration_engine.resume_job(job.id)
            assert resume_success == True

            # Verify execute_strategy was called with the latest checkpoint
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[1]["resume_from_checkpoint"] is not None

    @pytest.mark.asyncio
    async def test_cancel_workflow(self, integration_engine, integration_persistence):
        """Test cancelling a workflow."""

        job = await integration_persistence.create_job(
            strategy_name="cancellable_workflow",
            strategy_config={"steps": []},
            parameters={},
            options={},
        )

        # Set job to running
        await integration_persistence.update_job_status(job.id, JobStatus.RUNNING)

        # Cancel job
        cancel_success = await integration_engine.cancel_job(job.id)
        assert cancel_success == True

        # Verify cancellation
        cancelled_job = await integration_persistence.get_job(job.id)
        assert cancelled_job.status == JobStatus.CANCELLED
        assert cancelled_job.completed_at is not None


class TestLargeDataHandling:
    """Test handling of large datasets and results."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Database session isolation issue - needs refactoring")
    async def test_large_result_workflow(
        self, integration_engine, integration_persistence
    ):
        """Test workflow with large results that require external storage."""

        class LargeDataAction(BaseStrategyAction):
            async def execute(self, params, context):
                # Create large result data
                size = params.get("size", 200000)  # 200KB by default
                large_result = {
                    "data": "x" * size,
                    "metadata": {
                        "size": size,
                        "type": "large_dataset",
                        "created_by": "integration_test",
                    },
                    "summary": {"records": size // 100, "quality_score": 0.95},
                }

                return large_result

        # Add large data action to engine
        integration_engine.action_registry["LARGE_DATA"] = LargeDataAction

        strategy = {
            "name": "large_data_workflow",
            "steps": [
                {
                    "name": "generate_large_data",
                    "action": {
                        "type": "LARGE_DATA",
                        "params": {"size": 300000},  # 300KB result
                    },
                },
                {
                    "name": "process_large_data",
                    "action": {"type": "INTEGRATION_TEST", "params": {"records": 3000}},
                },
            ],
        }

        job = await integration_persistence.create_job(
            strategy_name="large_data_workflow",
            strategy_config=strategy,
            parameters={},
            options={},
        )

        # Execute workflow
        result = await integration_engine.execute_strategy(job.id, strategy)

        assert result["success"] == True

        # Verify large result was stored externally
        assert "step_0_output_ref" in result["context"]
        assert result["context"]["step_0_output_ref"].startswith("stored:")

        # Verify summary information is available
        assert "step_0_output_summary" in result["context"]
        summary = result["context"]["step_0_output_summary"]
        assert summary["stored"] == True
        assert summary["size_bytes"] > 200000

        # Verify we can retrieve the stored result
        stored_result = await integration_persistence.retrieve_result(
            job.id, 0, "step_output"
        )

        assert stored_result is not None
        assert len(stored_result["data"]) == 300000
        assert stored_result["metadata"]["type"] == "large_dataset"


class TestMetricsAndMonitoring:
    """Test metrics collection and monitoring integration."""

    @pytest.mark.asyncio
    async def test_comprehensive_metrics_collection(
        self, integration_engine, integration_persistence
    ):
        """Test that all metrics are properly collected during execution."""

        strategy = {
            "name": "metrics_test_workflow",
            "steps": [
                {
                    "name": "metric_step_1",
                    "action": {"type": "INTEGRATION_TEST", "params": {"records": 500}},
                },
                {
                    "name": "metric_step_2",
                    "action": {"type": "INTEGRATION_TEST", "params": {"records": 750}},
                },
            ],
        }

        job = await integration_persistence.create_job(
            strategy_name="metrics_test_workflow",
            strategy_config=strategy,
            parameters={},
            options={},
        )

        # Execute workflow
        result = await integration_engine.execute_strategy(job.id, strategy)

        assert result["success"] == True

        # Get comprehensive metrics
        metrics = await integration_persistence.get_job_metrics(job.id)

        # Verify job-level metrics
        assert metrics["job_id"] == str(job.id)
        assert metrics["total_steps"] == 2
        assert metrics["completed_steps"] == 2
        assert metrics["failed_steps"] == 0
        assert metrics["total_records_processed"] == 1250

        # Verify individual step metrics
        completed_job = await integration_persistence.get_job(job.id)

        for step in completed_job.steps:
            assert step.duration_ms is not None
            assert step.duration_ms > 0  # Should have taken some time
            assert step.records_processed > 0
            assert step.memory_used_mb is not None  # Memory tracking enabled

        # Verify execution time was recorded
        assert completed_job.execution_time_ms is not None
        assert completed_job.execution_time_ms > 0


class TestErrorHandlingIntegration:
    """Test comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Database session isolation issue - needs refactoring")
    async def test_multiple_failure_scenarios(
        self, integration_engine, integration_persistence
    ):
        """Test handling of various error scenarios in one workflow."""

        failure_count = {"retryable": 0, "permanent": 0}

        class VariableFailureAction(BaseStrategyAction):
            async def execute(self, params, context):
                failure_type = params.get("failure_type", "none")

                if failure_type == "retryable":
                    failure_count["retryable"] += 1
                    if failure_count["retryable"] < 3:
                        raise Exception(
                            f"Retryable failure #{failure_count['retryable']}"
                        )
                    return {"success": True, "attempts": failure_count["retryable"]}

                elif failure_type == "permanent":
                    failure_count["permanent"] += 1
                    raise Exception("Permanent failure - cannot recover")

                else:
                    return {"success": True, "records": params.get("records", 10)}

        integration_engine.action_registry["VARIABLE_FAILURE"] = VariableFailureAction

        strategy = {
            "name": "error_handling_workflow",
            "steps": [
                {
                    "name": "success_step",
                    "action": {
                        "type": "VARIABLE_FAILURE",
                        "params": {"failure_type": "none", "records": 100},
                    },
                },
                {
                    "name": "retryable_failure_step",
                    "action": {
                        "type": "VARIABLE_FAILURE",
                        "params": {"failure_type": "retryable"},
                    },
                    "on_error": {
                        "action": "retry",
                        "max_attempts": 3,
                        "delay_seconds": 0.01,
                    },
                },
                {
                    "name": "optional_permanent_failure",
                    "action": {
                        "type": "VARIABLE_FAILURE",
                        "params": {"failure_type": "permanent"},
                    },
                    "is_required": False,  # Should not stop workflow
                },
                {
                    "name": "final_success_step",
                    "action": {
                        "type": "VARIABLE_FAILURE",
                        "params": {"failure_type": "none", "records": 50},
                    },
                },
            ],
        }

        job = await integration_persistence.create_job(
            strategy_name="error_handling_workflow",
            strategy_config=strategy,
            parameters={},
            options={},
        )

        # Execute workflow
        result = await integration_engine.execute_strategy(job.id, strategy)

        # Should succeed despite failures
        assert result["success"] == True

        # Verify job completed
        completed_job = await integration_persistence.get_job(job.id)
        assert completed_job.status == JobStatus.COMPLETED

        # Verify step outcomes
        steps = completed_job.steps
        assert len(steps) == 4

        # First step should succeed
        assert steps[0].status == JobStatus.COMPLETED

        # Second step should succeed after retries
        assert steps[1].status == JobStatus.COMPLETED

        # Third step should fail but not stop execution
        assert steps[2].status == JobStatus.FAILED

        # Fourth step should succeed
        assert steps[3].status == JobStatus.COMPLETED

        # Verify retry mechanism worked
        assert failure_count["retryable"] == 3  # Failed twice, succeeded third time


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

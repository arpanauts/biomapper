"""Tests for ExecutionLifecycleService."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path

from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService


@pytest.fixture
def mock_checkpoint_manager():
    """Create a mock checkpoint manager."""
    manager = Mock()
    manager.save_checkpoint = AsyncMock()
    manager.load_checkpoint = AsyncMock(return_value={"test": "data"})
    manager.checkpoint_directory = Path("/tmp/checkpoints")
    return manager


@pytest.fixture
def mock_progress_reporter():
    """Create a mock progress reporter."""
    reporter = Mock()
    reporter.report = Mock()
    return reporter


@pytest.fixture
def mock_metrics_manager():
    """Create a mock metrics manager."""
    manager = Mock()
    # Don't set log_metrics so it will use trace instead
    manager.trace = Mock()
    # Delete log_metrics attribute if it exists
    if hasattr(manager, 'log_metrics'):
        delattr(manager, 'log_metrics')
    return manager


@pytest.fixture
def lifecycle_service(mock_checkpoint_manager, mock_progress_reporter, mock_metrics_manager):
    """Create an ExecutionLifecycleService instance."""
    return ExecutionLifecycleService(
        checkpoint_manager=mock_checkpoint_manager,
        progress_reporter=mock_progress_reporter,
        metrics_manager=mock_metrics_manager
    )


@pytest.mark.asyncio
async def test_save_checkpoint(lifecycle_service, mock_checkpoint_manager):
    """Test saving a checkpoint."""
    execution_id = "test-exec-123"
    checkpoint_data = {"state": "test", "progress": 50}
    
    await lifecycle_service.save_checkpoint(execution_id, checkpoint_data)
    
    # Verify checkpoint manager was called
    mock_checkpoint_manager.save_checkpoint.assert_called_once_with(
        execution_id, checkpoint_data
    )


@pytest.mark.asyncio
async def test_load_checkpoint(lifecycle_service, mock_checkpoint_manager):
    """Test loading a checkpoint."""
    execution_id = "test-exec-123"
    
    result = await lifecycle_service.load_checkpoint(execution_id)
    
    # Verify checkpoint manager was called
    mock_checkpoint_manager.load_checkpoint.assert_called_once_with(execution_id)
    assert result == {"test": "data"}


@pytest.mark.asyncio
async def test_report_progress(lifecycle_service, mock_progress_reporter):
    """Test reporting progress."""
    progress_data = {"type": "batch_start", "batch": 1, "total": 10}
    
    await lifecycle_service.report_progress(progress_data)
    
    # Verify progress reporter was called
    mock_progress_reporter.report.assert_called_once_with(progress_data)


@pytest.mark.asyncio
async def test_report_progress_with_metrics(lifecycle_service, mock_metrics_manager, mock_progress_reporter):
    """Test reporting progress with metrics."""
    # Ensure the lifecycle service has the mock metrics manager
    assert lifecycle_service.metrics_manager == mock_metrics_manager
    
    # Ensure log_metrics doesn't exist so trace will be used
    assert not hasattr(mock_metrics_manager, 'log_metrics')
    assert hasattr(mock_metrics_manager, 'trace')
    
    progress_data = {
        "type": "batch_complete",
        "metrics": {"items_processed": 100, "duration": 5.2}
    }
    
    await lifecycle_service.report_progress(progress_data)
    
    # Verify progress reporter was called
    mock_progress_reporter.report.assert_called_once_with(progress_data)
    
    # Verify metrics were logged via trace
    mock_metrics_manager.trace.assert_called_once_with(
        name="execution_metrics",
        input={"items_processed": 100, "duration": 5.2},
        metadata={"source": "lifecycle_service"}
    )


def test_add_progress_callback(lifecycle_service):
    """Test adding a progress callback."""
    callback = Mock()
    
    lifecycle_service.add_progress_callback(callback)
    
    assert callback in lifecycle_service._progress_callbacks


def test_remove_progress_callback(lifecycle_service):
    """Test removing a progress callback."""
    callback = Mock()
    lifecycle_service.add_progress_callback(callback)
    
    lifecycle_service.remove_progress_callback(callback)
    
    assert callback not in lifecycle_service._progress_callbacks


@pytest.mark.asyncio
async def test_report_progress_with_callbacks(lifecycle_service, mock_progress_reporter):
    """Test that progress callbacks are called."""
    callback1 = Mock()
    callback2 = Mock()
    
    lifecycle_service.add_progress_callback(callback1)
    lifecycle_service.add_progress_callback(callback2)
    
    progress_data = {"type": "test", "value": 42}
    await lifecycle_service.report_progress(progress_data)
    
    # Verify callbacks were called
    callback1.assert_called_once_with(progress_data)
    callback2.assert_called_once_with(progress_data)


@pytest.mark.asyncio
async def test_start_execution(lifecycle_service, mock_progress_reporter):
    """Test starting an execution."""
    execution_id = "test-exec-456"
    metadata = {"user": "test", "source": "api"}
    
    await lifecycle_service.start_execution(execution_id, metadata)
    
    # Verify progress was reported
    call_args = mock_progress_reporter.report.call_args[0][0]
    assert call_args["event"] == "execution_started"
    assert call_args["execution_id"] == execution_id
    assert call_args["metadata"] == metadata


@pytest.mark.asyncio
async def test_complete_execution(lifecycle_service, mock_progress_reporter):
    """Test completing an execution."""
    execution_id = "test-exec-789"
    result = {"total_processed": 1000, "success": True}
    
    await lifecycle_service.complete_execution(execution_id, result)
    
    # Verify progress was reported
    call_args = mock_progress_reporter.report.call_args[0][0]
    assert call_args["event"] == "execution_completed"
    assert call_args["execution_id"] == execution_id
    assert call_args["result"] == result


@pytest.mark.asyncio
async def test_fail_execution(lifecycle_service, mock_progress_reporter):
    """Test failing an execution."""
    execution_id = "test-exec-999"
    error = ValueError("Test error")
    
    await lifecycle_service.fail_execution(execution_id, error)
    
    # Verify progress was reported
    call_args = mock_progress_reporter.report.call_args[0][0]
    assert call_args["event"] == "execution_failed"
    assert call_args["execution_id"] == execution_id
    assert call_args["error"] == "Test error"
    assert call_args["error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_report_batch_progress(lifecycle_service, mock_progress_reporter):
    """Test reporting batch progress."""
    await lifecycle_service.report_batch_progress(
        batch_number=5,
        total_batches=10,
        items_processed=250,
        total_items=500,
        batch_metadata={"processor": "test"}
    )
    
    # Verify progress was reported
    call_args = mock_progress_reporter.report.call_args[0][0]
    assert call_args["event"] == "batch_progress"
    assert call_args["batch_number"] == 5
    assert call_args["total_batches"] == 10
    assert call_args["progress_percentage"] == 50.0


@pytest.mark.asyncio
async def test_save_batch_checkpoint(lifecycle_service, mock_checkpoint_manager):
    """Test saving a batch checkpoint."""
    execution_id = "test-exec-batch"
    batch_number = 3
    batch_state = {"processed": [1, 2, 3], "remaining": [4, 5, 6]}
    
    await lifecycle_service.save_batch_checkpoint(
        execution_id=execution_id,
        batch_number=batch_number,
        batch_state=batch_state,
        checkpoint_metadata={"processor": "batch_test"}
    )
    
    # Verify checkpoint was saved
    mock_checkpoint_manager.save_checkpoint.assert_called_once()
    call_args = mock_checkpoint_manager.save_checkpoint.call_args[0]
    assert call_args[0] == execution_id
    assert call_args[1]["batch_number"] == batch_number
    assert call_args[1]["batch_state"] == batch_state


def test_get_checkpoint_directory(lifecycle_service, mock_checkpoint_manager):
    """Test getting checkpoint directory."""
    result = lifecycle_service.get_checkpoint_directory()
    assert result == Path("/tmp/checkpoints")


def test_set_checkpoint_directory(lifecycle_service, mock_checkpoint_manager):
    """Test setting checkpoint directory."""
    new_dir = Path("/new/checkpoint/dir")
    lifecycle_service.set_checkpoint_directory(new_dir)
    
    mock_checkpoint_manager.checkpoint_directory = new_dir
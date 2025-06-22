"""
Unit tests for LifecycleCoordinator.

Tests the coordination and delegation of lifecycle operations to the 
specialized services (ExecutionSessionService, CheckpointService, ResourceDisposalService).
"""

import pytest
from unittest.mock import Mock, AsyncMock, PropertyMock, call
from pathlib import Path
import logging

from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.services.execution_session_service import ExecutionSessionService
from biomapper.core.services.checkpoint_service import CheckpointService
from biomapper.core.services.resource_disposal_service import ResourceDisposalService


@pytest.fixture
def mock_session_service():
    """Create a mock ExecutionSessionService."""
    mock = Mock(spec=ExecutionSessionService)
    mock.start_session = AsyncMock()
    mock.complete_session = AsyncMock()
    mock.fail_session = AsyncMock()
    mock.report_progress = AsyncMock()
    mock.report_batch_progress = AsyncMock()
    mock.add_progress_callback = Mock()
    mock.remove_progress_callback = Mock()
    return mock


@pytest.fixture
def mock_checkpoint_service():
    """Create a mock CheckpointService."""
    mock = Mock(spec=CheckpointService)
    mock.save_checkpoint = AsyncMock()
    mock.load_checkpoint = AsyncMock()
    mock.save_batch_checkpoint = AsyncMock()
    mock.set_checkpoint_directory = Mock()
    
    # Mock properties
    type(mock).checkpoint_directory = PropertyMock(return_value=None)
    type(mock).is_enabled = PropertyMock(return_value=False)
    
    return mock


@pytest.fixture
def mock_disposal_service():
    """Create a mock ResourceDisposalService."""
    mock = Mock(spec=ResourceDisposalService)
    mock.dispose_all = AsyncMock()
    return mock


@pytest.fixture
def coordinator(mock_session_service, mock_checkpoint_service, mock_disposal_service):
    """Create a LifecycleCoordinator instance."""
    return LifecycleCoordinator(
        execution_session_service=mock_session_service,
        checkpoint_service=mock_checkpoint_service,
        resource_disposal_service=mock_disposal_service
    )


class TestLifecycleCoordinator:
    """Test cases for LifecycleCoordinator."""
    
    def test_initialization(self, coordinator, mock_session_service, mock_checkpoint_service, mock_disposal_service):
        """Test coordinator initialization."""
        assert coordinator.session_service == mock_session_service
        assert coordinator.checkpoint_service == mock_checkpoint_service
        assert coordinator.disposal_service == mock_disposal_service
        assert coordinator.logger is not None
    
    def test_initialization_with_custom_logger(self, mock_session_service, mock_checkpoint_service, mock_disposal_service):
        """Test coordinator initialization with custom logger."""
        custom_logger = logging.getLogger("test.coordinator")
        
        coordinator = LifecycleCoordinator(
            execution_session_service=mock_session_service,
            checkpoint_service=mock_checkpoint_service,
            resource_disposal_service=mock_disposal_service,
            logger=custom_logger
        )
        
        assert coordinator.logger == custom_logger
    
    # Resource Disposal Tests
    
    async def test_async_dispose(self, coordinator, mock_disposal_service):
        """Test async disposal delegates to disposal service."""
        await coordinator.async_dispose()
        
        mock_disposal_service.dispose_all.assert_called_once()
    
    async def test_async_dispose_with_error(self, coordinator, mock_disposal_service):
        """Test async disposal when disposal service raises error."""
        mock_disposal_service.dispose_all.side_effect = Exception("Disposal failed")
        
        with pytest.raises(Exception, match="Disposal failed"):
            await coordinator.async_dispose()
    
    # Checkpoint Management Tests
    
    def test_checkpoint_dir_getter(self, coordinator, mock_checkpoint_service):
        """Test getting checkpoint directory."""
        test_path = Path("/test/checkpoints")
        type(mock_checkpoint_service).checkpoint_directory = PropertyMock(return_value=test_path)
        
        assert coordinator.checkpoint_dir == test_path
    
    def test_checkpoint_dir_setter(self, coordinator, mock_checkpoint_service):
        """Test setting checkpoint directory."""
        test_path = "/test/new/checkpoints"
        
        coordinator.checkpoint_dir = test_path
        
        mock_checkpoint_service.set_checkpoint_directory.assert_called_once_with(test_path)
    
    def test_checkpoint_dir_setter_none(self, coordinator, mock_checkpoint_service):
        """Test disabling checkpoints by setting directory to None."""
        coordinator.checkpoint_dir = None
        
        mock_checkpoint_service.set_checkpoint_directory.assert_called_once_with(None)
    
    def test_checkpoint_enabled_property(self, coordinator, mock_checkpoint_service):
        """Test checkpoint enabled property."""
        # Test when disabled
        type(mock_checkpoint_service).is_enabled = PropertyMock(return_value=False)
        assert coordinator.checkpoint_enabled is False
        
        # Test when enabled
        type(mock_checkpoint_service).is_enabled = PropertyMock(return_value=True)
        assert coordinator.checkpoint_enabled is True
    
    async def test_save_checkpoint(self, coordinator, mock_checkpoint_service):
        """Test saving checkpoint delegates to checkpoint service."""
        execution_id = "test-exec-123"
        checkpoint_data = {"state": "processing", "progress": 50}
        
        await coordinator.save_checkpoint(execution_id, checkpoint_data)
        
        mock_checkpoint_service.save_checkpoint.assert_called_once_with(execution_id, checkpoint_data)
    
    async def test_save_checkpoint_with_complex_data(self, coordinator, mock_checkpoint_service):
        """Test saving checkpoint with complex nested data."""
        execution_id = "complex-exec"
        checkpoint_data = {
            "state": "processing",
            "nested": {
                "level1": {
                    "level2": ["item1", "item2"]
                }
            },
            "metadata": {"timestamp": "2024-01-01T00:00:00"}
        }
        
        await coordinator.save_checkpoint(execution_id, checkpoint_data)
        
        mock_checkpoint_service.save_checkpoint.assert_called_once_with(execution_id, checkpoint_data)
    
    async def test_load_checkpoint(self, coordinator, mock_checkpoint_service):
        """Test loading checkpoint delegates to checkpoint service."""
        execution_id = "test-exec-123"
        expected_data = {"state": "processing", "progress": 50}
        mock_checkpoint_service.load_checkpoint.return_value = expected_data
        
        result = await coordinator.load_checkpoint(execution_id)
        
        assert result == expected_data
        mock_checkpoint_service.load_checkpoint.assert_called_once_with(execution_id)
    
    async def test_load_checkpoint_not_found(self, coordinator, mock_checkpoint_service):
        """Test loading checkpoint when not found."""
        mock_checkpoint_service.load_checkpoint.return_value = None
        
        result = await coordinator.load_checkpoint("nonexistent")
        
        assert result is None
    
    # Progress Reporting Tests
    
    async def test_report_progress(self, coordinator, mock_session_service):
        """Test reporting progress delegates to session service."""
        progress_data = {
            "event": "processing",
            "message": "Processing items",
            "count": 100
        }
        
        await coordinator.report_progress(progress_data)
        
        mock_session_service.report_progress.assert_called_once_with(progress_data)
    
    # Callback Management Tests
    
    def test_add_progress_callback(self, coordinator, mock_session_service):
        """Test adding progress callback delegates to session service."""
        callback = Mock()
        
        coordinator.add_progress_callback(callback)
        
        mock_session_service.add_progress_callback.assert_called_once_with(callback)
    
    def test_remove_progress_callback(self, coordinator, mock_session_service):
        """Test removing progress callback delegates to session service."""
        callback = Mock()
        
        coordinator.remove_progress_callback(callback)
        
        mock_session_service.remove_progress_callback.assert_called_once_with(callback)
    
    def test_multiple_callbacks(self, coordinator, mock_session_service):
        """Test managing multiple callbacks."""
        callbacks = [Mock() for _ in range(3)]
        
        # Add all callbacks
        for cb in callbacks:
            coordinator.add_progress_callback(cb)
        
        # Remove one
        coordinator.remove_progress_callback(callbacks[1])
        
        # Verify all operations were delegated
        assert mock_session_service.add_progress_callback.call_count == 3
        assert mock_session_service.remove_progress_callback.call_count == 1
    
    # Execution Lifecycle Tests
    
    async def test_start_execution(self, coordinator, mock_session_service):
        """Test starting execution delegates to session service."""
        execution_id = "test-exec-123"
        execution_type = "mapping"
        metadata = {"source": "test", "target": "demo"}
        
        await coordinator.start_execution(execution_id, execution_type, metadata)
        
        mock_session_service.start_session.assert_called_once_with(
            execution_id, execution_type, metadata
        )
    
    async def test_start_execution_without_metadata(self, coordinator, mock_session_service):
        """Test starting execution without metadata."""
        await coordinator.start_execution("exec-1", "validation")
        
        mock_session_service.start_session.assert_called_once_with(
            "exec-1", "validation", None
        )
    
    async def test_complete_execution(self, coordinator, mock_session_service):
        """Test completing execution delegates to session service."""
        execution_id = "test-exec-123"
        execution_type = "mapping"  # This parameter is ignored
        result_summary = {"total": 100, "success": 95, "failed": 5}
        
        await coordinator.complete_execution(execution_id, execution_type, result_summary)
        
        mock_session_service.complete_session.assert_called_once_with(
            execution_id, result_summary
        )
    
    async def test_complete_execution_without_summary(self, coordinator, mock_session_service):
        """Test completing execution without result summary."""
        await coordinator.complete_execution("exec-1", "validation")
        
        mock_session_service.complete_session.assert_called_once_with(
            "exec-1", None
        )
    
    async def test_fail_execution(self, coordinator, mock_session_service):
        """Test failing execution delegates to session service."""
        execution_id = "test-exec-123"
        execution_type = "mapping"  # This parameter is ignored
        error = ValueError("Test error")
        error_context = {"step": "validation", "item": 42}
        
        await coordinator.fail_execution(execution_id, execution_type, error, error_context)
        
        mock_session_service.fail_session.assert_called_once_with(
            execution_id, error, error_context
        )
    
    async def test_fail_execution_without_context(self, coordinator, mock_session_service):
        """Test failing execution without error context."""
        error = RuntimeError("Critical failure")
        
        await coordinator.fail_execution("exec-1", "processing", error)
        
        mock_session_service.fail_session.assert_called_once_with(
            "exec-1", error, None
        )
    
    # Batch Processing Tests
    
    async def test_report_batch_progress(self, coordinator, mock_session_service):
        """Test reporting batch progress delegates to session service."""
        await coordinator.report_batch_progress(
            batch_number=5,
            total_batches=10,
            items_processed=250,
            total_items=500,
            batch_metadata={"batch_size": 50}
        )
        
        mock_session_service.report_batch_progress.assert_called_once_with(
            batch_number=5,
            total_batches=10,
            items_processed=250,
            total_items=500,
            batch_metadata={"batch_size": 50}
        )
    
    async def test_report_batch_progress_without_metadata(self, coordinator, mock_session_service):
        """Test reporting batch progress without metadata."""
        await coordinator.report_batch_progress(
            batch_number=1,
            total_batches=1,
            items_processed=100,
            total_items=100
        )
        
        mock_session_service.report_batch_progress.assert_called_once_with(
            batch_number=1,
            total_batches=1,
            items_processed=100,
            total_items=100,
            batch_metadata=None
        )
    
    async def test_save_batch_checkpoint(self, coordinator, mock_checkpoint_service):
        """Test saving batch checkpoint delegates to checkpoint service."""
        execution_id = "batch-exec-123"
        batch_number = 5
        batch_state = {"processed": 250, "failed": 2}
        checkpoint_metadata = {"batch_size": 50, "retry_count": 0}
        
        await coordinator.save_batch_checkpoint(
            execution_id, batch_number, batch_state, checkpoint_metadata
        )
        
        mock_checkpoint_service.save_batch_checkpoint.assert_called_once_with(
            execution_id=execution_id,
            batch_number=batch_number,
            batch_state=batch_state,
            checkpoint_metadata=checkpoint_metadata
        )
    
    async def test_save_batch_checkpoint_without_metadata(self, coordinator, mock_checkpoint_service):
        """Test saving batch checkpoint without metadata."""
        await coordinator.save_batch_checkpoint(
            "exec-1", 1, {"state": "partial"}
        )
        
        mock_checkpoint_service.save_batch_checkpoint.assert_called_once_with(
            execution_id="exec-1",
            batch_number=1,
            batch_state={"state": "partial"},
            checkpoint_metadata=None
        )
    
    # Integration Tests
    
    async def test_full_execution_lifecycle(self, coordinator, mock_session_service, mock_checkpoint_service):
        """Test a complete execution lifecycle through the coordinator."""
        execution_id = "full-lifecycle-test"
        execution_type = "integration"
        
        # Start execution
        await coordinator.start_execution(execution_id, execution_type, {"test": True})
        
        # Report some progress
        await coordinator.report_progress({"event": "started", "progress": 0})
        
        # Save a checkpoint
        await coordinator.save_checkpoint(execution_id, {"state": "running"})
        
        # Report batch progress
        await coordinator.report_batch_progress(1, 5, 20, 100)
        
        # Save batch checkpoint
        await coordinator.save_batch_checkpoint(execution_id, 1, {"batch": "completed"})
        
        # Complete execution
        await coordinator.complete_execution(execution_id, execution_type, {"success": True})
        
        # Verify all delegations
        mock_session_service.start_session.assert_called_once()
        mock_session_service.report_progress.assert_called()
        mock_checkpoint_service.save_checkpoint.assert_called_once()
        mock_session_service.report_batch_progress.assert_called_once()
        mock_checkpoint_service.save_batch_checkpoint.assert_called_once()
        mock_session_service.complete_session.assert_called_once()
    
    async def test_execution_with_error_handling(self, coordinator, mock_session_service, mock_disposal_service):
        """Test execution lifecycle with error and disposal."""
        execution_id = "error-test"
        
        # Start execution
        await coordinator.start_execution(execution_id, "error_test")
        
        # Simulate error
        error = RuntimeError("Processing failed")
        await coordinator.fail_execution(execution_id, "error_test", error)
        
        # Dispose resources
        await coordinator.async_dispose()
        
        # Verify proper delegation
        mock_session_service.start_session.assert_called_once()
        mock_session_service.fail_session.assert_called_once_with(execution_id, error, None)
        mock_disposal_service.dispose_all.assert_called_once()
    
    async def test_concurrent_operations(self, coordinator, mock_session_service, mock_checkpoint_service):
        """Test concurrent operations through the coordinator."""
        import asyncio
        
        # Define concurrent tasks
        async def task1():
            await coordinator.start_execution("exec-1", "concurrent")
            await coordinator.save_checkpoint("exec-1", {"task": 1})
        
        async def task2():
            await coordinator.start_execution("exec-2", "concurrent")
            await coordinator.save_checkpoint("exec-2", {"task": 2})
        
        async def task3():
            await coordinator.report_progress({"event": "concurrent", "task": 3})
        
        # Run concurrently
        await asyncio.gather(task1(), task2(), task3())
        
        # Verify all operations were delegated
        assert mock_session_service.start_session.call_count == 2
        assert mock_checkpoint_service.save_checkpoint.call_count == 2
        assert mock_session_service.report_progress.call_count == 1
    
    def test_backward_compatibility_interface(self, coordinator):
        """Test that coordinator provides backward compatible interface."""
        # These attributes/methods should exist for backward compatibility
        assert hasattr(coordinator, 'checkpoint_dir')
        assert hasattr(coordinator, 'checkpoint_enabled')
        assert hasattr(coordinator, 'async_dispose')
        assert hasattr(coordinator, 'save_checkpoint')
        assert hasattr(coordinator, 'load_checkpoint')
        assert hasattr(coordinator, 'report_progress')
        assert hasattr(coordinator, 'add_progress_callback')
        assert hasattr(coordinator, 'remove_progress_callback')
        assert hasattr(coordinator, 'start_execution')
        assert hasattr(coordinator, 'complete_execution')
        assert hasattr(coordinator, 'fail_execution')
        assert hasattr(coordinator, 'report_batch_progress')
        assert hasattr(coordinator, 'save_batch_checkpoint')
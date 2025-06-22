"""
Unit tests for ExecutionSessionService.

Tests the execution session management and progress reporting functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, call
from datetime import datetime
import asyncio

from biomapper.core.services.execution_session_service import ExecutionSessionService
from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock ExecutionLifecycleService."""
    mock = Mock(spec=ExecutionLifecycleService)
    mock.report_progress = AsyncMock()
    mock.report_batch_progress = AsyncMock()
    mock.add_progress_callback = Mock()
    mock.remove_progress_callback = Mock()
    return mock


@pytest.fixture
def session_service(mock_lifecycle_service):
    """Create an ExecutionSessionService instance."""
    return ExecutionSessionService(
        execution_lifecycle_service=mock_lifecycle_service
    )


class TestExecutionSessionService:
    """Test cases for ExecutionSessionService."""
    
    async def test_start_session(self, session_service, mock_lifecycle_service):
        """Test starting a new execution session."""
        execution_id = "test-exec-123"
        execution_type = "mapping"
        metadata = {"source": "test", "target": "demo"}
        
        await session_service.start_session(execution_id, execution_type, metadata)
        
        # Verify session is tracked
        assert execution_id in session_service._active_sessions
        session = session_service._active_sessions[execution_id]
        assert session['execution_type'] == execution_type
        assert session['metadata'] == metadata
        assert session['status'] == 'active'
        assert 'started_at' in session
        
        # Verify progress was reported
        mock_lifecycle_service.report_progress.assert_called_once()
        progress_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert progress_data['event'] == 'execution_started'
        assert progress_data['execution_id'] == execution_id
        assert progress_data['execution_type'] == execution_type
    
    async def test_complete_session(self, session_service, mock_lifecycle_service):
        """Test completing an execution session."""
        execution_id = "test-exec-123"
        execution_type = "mapping"
        
        # Start session first
        await session_service.start_session(execution_id, execution_type)
        mock_lifecycle_service.reset_mock()
        
        # Complete session
        result_summary = {"total": 100, "success": 95, "failed": 5}
        await session_service.complete_session(execution_id, result_summary)
        
        # Verify session is removed
        assert execution_id not in session_service._active_sessions
        
        # Verify progress was reported
        mock_lifecycle_service.report_progress.assert_called_once()
        progress_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert progress_data['event'] == 'execution_completed'
        assert progress_data['execution_id'] == execution_id
        assert progress_data['result_summary'] == result_summary
    
    async def test_fail_session(self, session_service, mock_lifecycle_service):
        """Test failing an execution session."""
        execution_id = "test-exec-123"
        execution_type = "mapping"
        
        # Start session first
        await session_service.start_session(execution_id, execution_type)
        mock_lifecycle_service.reset_mock()
        
        # Fail session
        error = ValueError("Test error")
        error_context = {"step": "validation", "item": 42}
        await session_service.fail_session(execution_id, error, error_context)
        
        # Verify session is removed
        assert execution_id not in session_service._active_sessions
        
        # Verify progress was reported
        mock_lifecycle_service.report_progress.assert_called_once()
        progress_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert progress_data['event'] == 'execution_failed'
        assert progress_data['error'] == "Test error"
        assert progress_data['error_type'] == "ValueError"
        assert progress_data['error_context'] == error_context
    
    async def test_complete_unknown_session(self, session_service, mock_lifecycle_service):
        """Test completing a session that wasn't started."""
        execution_id = "unknown-exec"
        
        # Should not raise error
        await session_service.complete_session(execution_id)
        
        # Should still report progress
        mock_lifecycle_service.report_progress.assert_called_once()
        progress_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert progress_data['execution_type'] == 'unknown'
    
    async def test_report_progress(self, session_service, mock_lifecycle_service):
        """Test reporting progress."""
        progress_data = {
            'event': 'custom_event',
            'message': 'Processing items'
        }
        
        await session_service.report_progress(progress_data)
        
        # Verify timestamp was added
        mock_lifecycle_service.report_progress.assert_called_once()
        reported_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert 'timestamp' in reported_data
        assert reported_data['event'] == 'custom_event'
    
    async def test_report_batch_progress(self, session_service, mock_lifecycle_service):
        """Test reporting batch progress."""
        await session_service.report_batch_progress(
            batch_number=5,
            total_batches=10,
            items_processed=250,
            total_items=500,
            batch_metadata={'batch_size': 50}
        )
        
        mock_lifecycle_service.report_batch_progress.assert_called_once_with(
            batch_number=5,
            total_batches=10,
            items_processed=250,
            total_items=500,
            batch_metadata={'batch_size': 50}
        )
    
    def test_add_progress_callback(self, session_service, mock_lifecycle_service):
        """Test adding a progress callback."""
        callback = Mock()
        session_service.add_progress_callback(callback)
        
        mock_lifecycle_service.add_progress_callback.assert_called_once_with(callback)
    
    def test_remove_progress_callback(self, session_service, mock_lifecycle_service):
        """Test removing a progress callback."""
        callback = Mock()
        session_service.remove_progress_callback(callback)
        
        mock_lifecycle_service.remove_progress_callback.assert_called_once_with(callback)
    
    def test_get_active_sessions(self, session_service):
        """Test getting list of active sessions."""
        # Add some sessions directly
        session_service._active_sessions = {
            'exec-1': {'status': 'active'},
            'exec-2': {'status': 'active'},
            'exec-3': {'status': 'active'}
        }
        
        active = session_service.get_active_sessions()
        assert len(active) == 3
        assert set(active) == {'exec-1', 'exec-2', 'exec-3'}
    
    def test_get_session_info(self, session_service):
        """Test getting session information."""
        session_data = {
            'execution_type': 'mapping',
            'status': 'active',
            'metadata': {'test': True}
        }
        session_service._active_sessions['exec-1'] = session_data
        
        info = session_service.get_session_info('exec-1')
        assert info == session_data
        
        # Test unknown session
        assert session_service.get_session_info('unknown') is None
    
    def test_is_session_active(self, session_service):
        """Test checking if session is active."""
        session_service._active_sessions['active-exec'] = {'status': 'active'}
        
        assert session_service.is_session_active('active-exec') is True
        assert session_service.is_session_active('unknown-exec') is False
    
    async def test_start_session_with_empty_metadata(self, session_service, mock_lifecycle_service):
        """Test starting a session with empty metadata."""
        execution_id = "test-exec-empty"
        execution_type = "validation"
        
        await session_service.start_session(execution_id, execution_type, {})
        
        assert execution_id in session_service._active_sessions
        session = session_service._active_sessions[execution_id]
        assert session['metadata'] == {}
    
    async def test_multiple_session_lifecycle(self, session_service, mock_lifecycle_service):
        """Test managing multiple concurrent sessions."""
        # Start multiple sessions
        session_ids = [f"exec-{i}" for i in range(5)]
        
        for sid in session_ids:
            await session_service.start_session(sid, "batch", {"index": sid})
        
        # Verify all are active
        assert len(session_service.get_active_sessions()) == 5
        
        # Complete some sessions
        await session_service.complete_session(session_ids[0])
        await session_service.complete_session(session_ids[2])
        
        # Fail one session
        await session_service.fail_session(session_ids[1], RuntimeError("Test error"))
        
        # Check remaining active sessions
        active = session_service.get_active_sessions()
        assert len(active) == 2
        assert session_ids[3] in active
        assert session_ids[4] in active
    
    async def test_report_progress_with_complex_data(self, session_service, mock_lifecycle_service):
        """Test reporting progress with complex nested data."""
        complex_data = {
            'event': 'processing_batch',
            'metrics': {
                'processed': 1000,
                'failed': 5,
                'skipped': 10
            },
            'nested': {
                'level1': {
                    'level2': {
                        'deep_value': 'test'
                    }
                }
            },
            'arrays': [1, 2, 3, {'inner': 'value'}]
        }
        
        await session_service.report_progress(complex_data)
        
        # Verify timestamp was added and data preserved
        call_args = mock_lifecycle_service.report_progress.call_args[0][0]
        assert 'timestamp' in call_args
        assert call_args['metrics'] == complex_data['metrics']
        assert call_args['nested']['level1']['level2']['deep_value'] == 'test'
    
    async def test_fail_session_with_custom_exception(self, session_service, mock_lifecycle_service):
        """Test failing session with custom exception types."""
        execution_id = "test-custom-error"
        
        await session_service.start_session(execution_id, "custom")
        mock_lifecycle_service.reset_mock()
        
        # Custom exception class
        class CustomProcessingError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code
        
        error = CustomProcessingError("Processing failed", 42)
        await session_service.fail_session(execution_id, error, {"stage": "validation"})
        
        progress_data = mock_lifecycle_service.report_progress.call_args[0][0]
        assert progress_data['error_type'] == "CustomProcessingError"
        assert progress_data['error'] == "Processing failed"
    
    async def test_report_batch_progress_edge_cases(self, session_service, mock_lifecycle_service):
        """Test batch progress reporting with edge cases."""
        # Test with zero items
        await session_service.report_batch_progress(
            batch_number=1,
            total_batches=1,
            items_processed=0,
            total_items=0
        )
        
        # Test with batch number exceeding total
        await session_service.report_batch_progress(
            batch_number=10,
            total_batches=5,
            items_processed=500,
            total_items=500
        )
        
        assert mock_lifecycle_service.report_batch_progress.call_count == 2
    
    def test_session_service_callbacks_propagation(self, session_service, mock_lifecycle_service):
        """Test that callbacks are properly propagated to lifecycle service."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add multiple callbacks
        session_service.add_progress_callback(callback1)
        session_service.add_progress_callback(callback2)
        
        # Remove one
        session_service.remove_progress_callback(callback1)
        
        # Verify proper delegation
        assert mock_lifecycle_service.add_progress_callback.call_count == 2
        assert mock_lifecycle_service.remove_progress_callback.call_count == 1
    
    async def test_session_concurrent_operations(self, session_service, mock_lifecycle_service):
        """Test concurrent operations on the same session."""
        execution_id = "concurrent-test"
        
        # Start session
        await session_service.start_session(execution_id, "concurrent")
        
        # Simulate concurrent progress reports
        tasks = []
        for i in range(10):
            task = session_service.report_progress({
                'event': 'progress',
                'iteration': i
            })
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Session should still be active
        assert session_service.is_session_active(execution_id)
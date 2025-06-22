"""
Unit tests for CheckpointService.

Tests the checkpoint management functionality including save/load operations
and directory management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile
import shutil

from biomapper.core.services.checkpoint_service import CheckpointService
from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock ExecutionLifecycleService."""
    mock = Mock(spec=ExecutionLifecycleService)
    mock.save_checkpoint = AsyncMock()
    mock.load_checkpoint = AsyncMock()
    mock.save_batch_checkpoint = AsyncMock()
    mock.set_checkpoint_directory = Mock()
    return mock


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary checkpoint directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def checkpoint_service(mock_lifecycle_service):
    """Create a CheckpointService instance."""
    return CheckpointService(
        execution_lifecycle_service=mock_lifecycle_service
    )


class TestCheckpointService:
    """Test cases for CheckpointService."""
    
    def test_initialization_without_checkpoint_dir(self, checkpoint_service):
        """Test initialization without checkpoint directory."""
        assert checkpoint_service.checkpoint_directory is None
        assert checkpoint_service.is_enabled is False
    
    def test_initialization_with_checkpoint_dir(self, mock_lifecycle_service, temp_checkpoint_dir):
        """Test initialization with checkpoint directory."""
        service = CheckpointService(
            execution_lifecycle_service=mock_lifecycle_service,
            checkpoint_dir=temp_checkpoint_dir
        )
        
        assert service.checkpoint_directory == Path(temp_checkpoint_dir)
        assert service.is_enabled is True
        mock_lifecycle_service.set_checkpoint_directory.assert_called_once()
    
    def test_set_checkpoint_directory(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test setting checkpoint directory."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        assert checkpoint_service.checkpoint_directory == Path(temp_checkpoint_dir)
        assert checkpoint_service.is_enabled is True
        mock_lifecycle_service.set_checkpoint_directory.assert_called_with(Path(temp_checkpoint_dir))
    
    def test_disable_checkpointing(self, checkpoint_service, mock_lifecycle_service):
        """Test disabling checkpointing."""
        # First enable it
        checkpoint_service.set_checkpoint_directory("/tmp/test")
        mock_lifecycle_service.reset_mock()
        
        # Then disable it
        checkpoint_service.set_checkpoint_directory(None)
        
        assert checkpoint_service.checkpoint_directory is None
        assert checkpoint_service.is_enabled is False
        mock_lifecycle_service.set_checkpoint_directory.assert_called_with(None)
    
    async def test_save_checkpoint_enabled(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test saving checkpoint when enabled."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        mock_lifecycle_service.reset_mock()
        
        execution_id = "test-exec-123"
        checkpoint_data = {"state": "processing", "progress": 50}
        
        result = await checkpoint_service.save_checkpoint(execution_id, checkpoint_data)
        
        assert result is True
        mock_lifecycle_service.save_checkpoint.assert_called_once_with(execution_id, checkpoint_data)
    
    async def test_save_checkpoint_disabled(self, checkpoint_service, mock_lifecycle_service):
        """Test saving checkpoint when disabled."""
        # Ensure checkpointing is disabled
        assert checkpoint_service.is_enabled is False
        
        execution_id = "test-exec-123"
        checkpoint_data = {"state": "processing", "progress": 50}
        
        result = await checkpoint_service.save_checkpoint(execution_id, checkpoint_data)
        
        assert result is False
        mock_lifecycle_service.save_checkpoint.assert_not_called()
    
    async def test_save_checkpoint_error(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test saving checkpoint with error."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        mock_lifecycle_service.save_checkpoint.side_effect = Exception("Save failed")
        
        with pytest.raises(Exception, match="Save failed"):
            await checkpoint_service.save_checkpoint("test-exec", {})
    
    async def test_load_checkpoint_enabled(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test loading checkpoint when enabled."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        mock_lifecycle_service.reset_mock()
        
        execution_id = "test-exec-123"
        expected_data = {"state": "processing", "progress": 50}
        mock_lifecycle_service.load_checkpoint.return_value = expected_data
        
        result = await checkpoint_service.load_checkpoint(execution_id)
        
        assert result == expected_data
        mock_lifecycle_service.load_checkpoint.assert_called_once_with(execution_id)
    
    async def test_load_checkpoint_disabled(self, checkpoint_service, mock_lifecycle_service):
        """Test loading checkpoint when disabled."""
        assert checkpoint_service.is_enabled is False
        
        result = await checkpoint_service.load_checkpoint("test-exec-123")
        
        assert result is None
        mock_lifecycle_service.load_checkpoint.assert_not_called()
    
    async def test_load_checkpoint_not_found(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test loading checkpoint that doesn't exist."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        mock_lifecycle_service.load_checkpoint.return_value = None
        
        result = await checkpoint_service.load_checkpoint("nonexistent")
        
        assert result is None
    
    async def test_checkpoint_exists(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test checking if checkpoint exists."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        # Test existing checkpoint
        mock_lifecycle_service.load_checkpoint.return_value = {"data": "exists"}
        assert await checkpoint_service.checkpoint_exists("existing") is True
        
        # Test non-existing checkpoint
        mock_lifecycle_service.load_checkpoint.return_value = None
        assert await checkpoint_service.checkpoint_exists("nonexistent") is False
        
        # Test when disabled
        checkpoint_service.set_checkpoint_directory(None)
        assert await checkpoint_service.checkpoint_exists("any") is False
    
    async def test_delete_checkpoint(self, checkpoint_service, temp_checkpoint_dir):
        """Test deleting checkpoint."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        # Currently just logs intent
        result = await checkpoint_service.delete_checkpoint("test-exec")
        assert result is True
        
        # Test when disabled
        checkpoint_service.set_checkpoint_directory(None)
        result = await checkpoint_service.delete_checkpoint("test-exec")
        assert result is False
    
    async def test_save_batch_checkpoint_enabled(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test saving batch checkpoint when enabled."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        mock_lifecycle_service.reset_mock()
        
        execution_id = "test-exec-123"
        batch_number = 5
        batch_state = {"processed": 250, "failed": 2}
        metadata = {"batch_size": 50}
        
        result = await checkpoint_service.save_batch_checkpoint(
            execution_id, batch_number, batch_state, metadata
        )
        
        assert result is True
        mock_lifecycle_service.save_batch_checkpoint.assert_called_once_with(
            execution_id=execution_id,
            batch_number=batch_number,
            batch_state=batch_state,
            checkpoint_metadata=metadata
        )
    
    async def test_save_batch_checkpoint_disabled(self, checkpoint_service, mock_lifecycle_service):
        """Test saving batch checkpoint when disabled."""
        assert checkpoint_service.is_enabled is False
        
        result = await checkpoint_service.save_batch_checkpoint(
            "test-exec", 1, {"state": "data"}, None
        )
        
        assert result is False
        mock_lifecycle_service.save_batch_checkpoint.assert_not_called()
    
    async def test_load_batch_checkpoint(self, checkpoint_service, mock_lifecycle_service, temp_checkpoint_dir):
        """Test loading batch checkpoint."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        execution_id = "test-exec-123"
        batch_number = 5
        
        # Test with batch-specific key
        mock_lifecycle_service.load_checkpoint.return_value = {
            "batch_5": {"processed": 250, "state": "partial"}
        }
        result = await checkpoint_service.load_batch_checkpoint(execution_id, batch_number)
        assert result == {"processed": 250, "state": "partial"}
        
        # Test with batch_number in data
        mock_lifecycle_service.load_checkpoint.return_value = {
            "batch_number": 5,
            "processed": 250,
            "state": "partial"
        }
        result = await checkpoint_service.load_batch_checkpoint(execution_id, batch_number)
        assert result["batch_number"] == 5
        
        # Test batch not found
        mock_lifecycle_service.load_checkpoint.return_value = {"batch_3": {"data": "other"}}
        result = await checkpoint_service.load_batch_checkpoint(execution_id, batch_number)
        assert result is None
        
        # Test when disabled
        checkpoint_service.set_checkpoint_directory(None)
        result = await checkpoint_service.load_batch_checkpoint(execution_id, batch_number)
        assert result is None
    
    def test_get_checkpoint_path(self, checkpoint_service, temp_checkpoint_dir):
        """Test getting checkpoint file path."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        path = checkpoint_service.get_checkpoint_path("test-exec-123")
        expected = Path(temp_checkpoint_dir) / "test-exec-123.checkpoint"
        assert path == expected
        
        # Test when disabled
        checkpoint_service.set_checkpoint_directory(None)
        assert checkpoint_service.get_checkpoint_path("test-exec-123") is None
    
    async def test_cleanup_old_checkpoints(self, checkpoint_service, temp_checkpoint_dir):
        """Test cleanup of old checkpoints."""
        checkpoint_service.set_checkpoint_directory(temp_checkpoint_dir)
        
        # Currently just logs intent
        deleted = await checkpoint_service.cleanup_old_checkpoints(days_to_keep=7)
        assert deleted == 0
        
        # Test when disabled
        checkpoint_service.set_checkpoint_directory(None)
        deleted = await checkpoint_service.cleanup_old_checkpoints()
        assert deleted == 0
    
    def test_validate_checkpoint_data(self, checkpoint_service):
        """Test checkpoint data validation."""
        # Valid data
        assert checkpoint_service.validate_checkpoint_data({"key": "value"}) is True
        assert checkpoint_service.validate_checkpoint_data({}) is True
        
        # Invalid data
        assert checkpoint_service.validate_checkpoint_data("not a dict") is False
        assert checkpoint_service.validate_checkpoint_data(None) is False
        assert checkpoint_service.validate_checkpoint_data([1, 2, 3]) is False
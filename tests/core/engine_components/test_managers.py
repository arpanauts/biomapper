import pytest
import pickle
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.exceptions import BiomapperError


class TestCheckpointManager:
    """Test suite for CheckpointManager class."""
    
    @pytest.fixture
    def temp_checkpoint_dir(self, tmp_path):
        """Create a temporary checkpoint directory."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        return checkpoint_dir
    
    @pytest.fixture
    def checkpoint_manager(self, temp_checkpoint_dir):
        """Create a CheckpointManager instance with temp directory."""
        return CheckpointManager(checkpoint_dir=str(temp_checkpoint_dir))
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()
    
    @pytest.fixture
    def checkpoint_manager_with_logger(self, temp_checkpoint_dir, mock_logger):
        """Create a CheckpointManager instance with logger."""
        return CheckpointManager(
            checkpoint_dir=str(temp_checkpoint_dir),
            logger=mock_logger
        )
    
    @pytest.fixture
    def sample_state(self):
        """Create sample state data for testing."""
        return {
            'processed_count': 42,
            'total_count': 100,
            'current_item': 'test_item',
            'results': ['result1', 'result2'],
            'metadata': {'key': 'value'}
        }
    
    @pytest.mark.asyncio
    async def test_save_checkpoint(self, checkpoint_manager, sample_state):
        """Test that save_checkpoint correctly creates a JSON file with expected content."""
        execution_id = "test_execution_123"
        
        # Save checkpoint
        await checkpoint_manager.save_checkpoint(execution_id, sample_state)
        
        # Verify file was created
        checkpoint_file = checkpoint_manager._get_checkpoint_file(execution_id)
        assert checkpoint_file.exists()
        
        # Verify content
        with open(checkpoint_file, 'rb') as f:
            saved_data = pickle.load(f)
        
        # Check original data is preserved
        assert saved_data['processed_count'] == sample_state['processed_count']
        assert saved_data['total_count'] == sample_state['total_count']
        assert saved_data['current_item'] == sample_state['current_item']
        assert saved_data['results'] == sample_state['results']
        assert saved_data['metadata'] == sample_state['metadata']
        
        # Check timestamp was added
        assert 'checkpoint_time' in saved_data
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(saved_data['checkpoint_time'])
    
    @pytest.mark.asyncio
    async def test_load_checkpoint(self, checkpoint_manager, sample_state):
        """Test that load_checkpoint reads back data correctly."""
        execution_id = "test_execution_456"
        
        # Save checkpoint first
        await checkpoint_manager.save_checkpoint(execution_id, sample_state)
        
        # Load it back
        loaded_state = await checkpoint_manager.load_checkpoint(execution_id)
        
        # Verify loaded data matches original (except timestamp)
        assert loaded_state is not None
        assert loaded_state['processed_count'] == sample_state['processed_count']
        assert loaded_state['total_count'] == sample_state['total_count']
        assert loaded_state['current_item'] == sample_state['current_item']
        assert loaded_state['results'] == sample_state['results']
        assert loaded_state['metadata'] == sample_state['metadata']
        assert 'checkpoint_time' in loaded_state
    
    @pytest.mark.asyncio
    async def test_clear_checkpoint(self, checkpoint_manager, sample_state):
        """Test that clear_checkpoint successfully deletes the checkpoint file."""
        execution_id = "test_execution_789"
        
        # Save checkpoint
        await checkpoint_manager.save_checkpoint(execution_id, sample_state)
        
        # Verify file exists
        checkpoint_file = checkpoint_manager._get_checkpoint_file(execution_id)
        assert checkpoint_file.exists()
        
        # Clear checkpoint
        await checkpoint_manager.clear_checkpoint(execution_id)
        
        # Verify file was deleted
        assert not checkpoint_file.exists()
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test that load_checkpoint returns None for non-existent checkpoint."""
        execution_id = "nonexistent_execution"
        
        # Try to load non-existent checkpoint
        loaded_state = await checkpoint_manager.load_checkpoint(execution_id)
        
        # Should return None
        assert loaded_state is None
    
    def test_checkpoint_directory_creation(self, tmp_path):
        """Test that CheckpointManager creates checkpoint directory if it doesn't exist."""
        # Create path that doesn't exist
        new_checkpoint_dir = tmp_path / "new_checkpoints"
        assert not new_checkpoint_dir.exists()
        
        # Create CheckpointManager with non-existent directory
        manager = CheckpointManager(checkpoint_dir=str(new_checkpoint_dir))
        
        # Directory should now exist
        assert new_checkpoint_dir.exists()
        assert new_checkpoint_dir.is_dir()
    
    def test_default_checkpoint_directory(self):
        """Test default checkpoint directory creation."""
        # Create manager without specifying directory (but enabled)
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            # Need to pass a truthy value but not a specific path to trigger default
            manager = CheckpointManager(checkpoint_dir="")
            manager.checkpoint_enabled = True
            
            # Should use default path
            expected_path = Path.home() / '.biomapper' / 'checkpoints'
            assert manager.checkpoint_dir == expected_path
    
    @pytest.mark.asyncio
    async def test_checkpoint_disabled(self):
        """Test behavior when checkpointing is disabled."""
        # Create manager with checkpointing disabled
        manager = CheckpointManager(checkpoint_dir=None)
        
        assert not manager.checkpoint_enabled
        assert manager.checkpoint_dir is None
        
        # These operations should not raise errors but should do nothing
        await manager.save_checkpoint("test_id", {"data": "test"})
        result = await manager.load_checkpoint("test_id")
        assert result is None
        
        await manager.clear_checkpoint("test_id")
    
    @pytest.mark.asyncio
    async def test_save_checkpoint_with_error(self, checkpoint_manager_with_logger, sample_state):
        """Test error handling in save_checkpoint."""
        execution_id = "test_error"
        
        # Mock file operations to raise error
        with patch('builtins.open', side_effect=IOError("Disk full")):
            with pytest.raises(BiomapperError) as exc_info:
                await checkpoint_manager_with_logger.save_checkpoint(execution_id, sample_state)
            
            assert "Checkpoint save failed" in str(exc_info.value)
            checkpoint_manager_with_logger.logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_load_checkpoint_with_corrupt_file(self, checkpoint_manager_with_logger, temp_checkpoint_dir):
        """Test handling of corrupted checkpoint file."""
        execution_id = "corrupt_checkpoint"
        
        # Create a corrupt checkpoint file
        checkpoint_file = checkpoint_manager_with_logger._get_checkpoint_file(execution_id)
        with open(checkpoint_file, 'w') as f:
            f.write("This is not valid pickle data")
        
        # Try to load it
        result = await checkpoint_manager_with_logger.load_checkpoint(execution_id)
        
        # Should return None and log error
        assert result is None
        checkpoint_manager_with_logger.logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_atomic_save(self, checkpoint_manager, sample_state):
        """Test that save uses atomic write (temp file + rename)."""
        execution_id = "atomic_test"
        
        with patch('pathlib.Path.replace') as mock_replace:
            await checkpoint_manager.save_checkpoint(execution_id, sample_state)
            
            # Verify atomic rename was called
            mock_replace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_progress_callbacks(self, checkpoint_manager, sample_state):
        """Test progress callback functionality."""
        execution_id = "callback_test"
        callback_data = []
        
        # Add progress callback
        def progress_callback(data):
            callback_data.append(data)
        
        checkpoint_manager.add_progress_callback(progress_callback)
        
        # Save checkpoint
        await checkpoint_manager.save_checkpoint(execution_id, sample_state)
        
        # Check callback was called with correct data
        assert len(callback_data) == 1
        assert callback_data[0]['type'] == 'checkpoint_saved'
        assert callback_data[0]['execution_id'] == execution_id
        assert callback_data[0]['state_summary']['processed_count'] == 42
        assert callback_data[0]['state_summary']['total_count'] == 100
        
        # Load checkpoint
        await checkpoint_manager.load_checkpoint(execution_id)
        
        # Check callback was called again
        assert len(callback_data) == 2
        assert callback_data[1]['type'] == 'checkpoint_loaded'
        assert callback_data[1]['execution_id'] == execution_id
    
    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, checkpoint_manager_with_logger, sample_state):
        """Test that callback errors don't break checkpoint operations."""
        execution_id = "callback_error_test"
        
        # Add callback that raises error
        def bad_callback(data):
            raise RuntimeError("Callback error")
        
        checkpoint_manager_with_logger.add_progress_callback(bad_callback)
        
        # Should not raise error
        await checkpoint_manager_with_logger.save_checkpoint(execution_id, sample_state)
        
        # Should log warning
        checkpoint_manager_with_logger.logger.warning.assert_called()
    
    def test_current_checkpoint_file_property(self, checkpoint_manager):
        """Test current_checkpoint_file property."""
        # Initially None
        assert checkpoint_manager.current_checkpoint_file is None
        
        # Set after save or load
        execution_id = "property_test"
        asyncio.run(checkpoint_manager.save_checkpoint(execution_id, {"test": "data"}))
        
        expected_file = checkpoint_manager._get_checkpoint_file(execution_id)
        assert checkpoint_manager.current_checkpoint_file == expected_file
    
    @pytest.mark.asyncio
    async def test_clear_nonexistent_checkpoint(self, checkpoint_manager_with_logger):
        """Test clearing a checkpoint that doesn't exist."""
        execution_id = "nonexistent"
        
        # Should not raise error
        await checkpoint_manager_with_logger.clear_checkpoint(execution_id)
        
        # Should not log anything since file doesn't exist
        checkpoint_manager_with_logger.logger.info.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_clear_checkpoint_with_error(self, checkpoint_manager_with_logger, sample_state):
        """Test error handling when clearing checkpoint fails."""
        execution_id = "clear_error"
        
        # Save checkpoint first
        await checkpoint_manager_with_logger.save_checkpoint(execution_id, sample_state)
        
        # Mock unlink to raise error
        with patch('pathlib.Path.unlink', side_effect=PermissionError("Access denied")):
            await checkpoint_manager_with_logger.clear_checkpoint(execution_id)
            
            # Should log warning, not error
            checkpoint_manager_with_logger.logger.warning.assert_called()
    
    def test_get_checkpoint_file_without_dir(self):
        """Test _get_checkpoint_file raises error when checkpoint_dir is None."""
        manager = CheckpointManager(checkpoint_dir=None)
        
        with pytest.raises(BiomapperError) as exc_info:
            manager._get_checkpoint_file("test_id")
        
        assert "Checkpoint directory not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_multiple_checkpoints(self, checkpoint_manager):
        """Test managing multiple checkpoints simultaneously."""
        states = {
            "exec1": {"data": "first", "count": 1},
            "exec2": {"data": "second", "count": 2},
            "exec3": {"data": "third", "count": 3}
        }
        
        # Save all checkpoints
        for exec_id, state in states.items():
            await checkpoint_manager.save_checkpoint(exec_id, state)
        
        # Load and verify all checkpoints
        for exec_id, expected_state in states.items():
            loaded = await checkpoint_manager.load_checkpoint(exec_id)
            assert loaded is not None
            assert loaded['data'] == expected_state['data']
            assert loaded['count'] == expected_state['count']
        
        # Clear one checkpoint
        await checkpoint_manager.clear_checkpoint("exec2")
        
        # Verify others still exist
        assert await checkpoint_manager.load_checkpoint("exec1") is not None
        assert await checkpoint_manager.load_checkpoint("exec2") is None
        assert await checkpoint_manager.load_checkpoint("exec3") is not None
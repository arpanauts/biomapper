import pytest
import pickle
import asyncio
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.engine_components.client_manager import ClientManager
from biomapper.core.exceptions import BiomapperError, ClientInitializationError
from biomapper.db.models import MappingResource


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


class TestClientManager:
    """Test suite for ClientManager class."""
    
    @pytest.fixture
    def client_manager(self):
        """Create a ClientManager instance."""
        return ClientManager()
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()
    
    @pytest.fixture
    def client_manager_with_logger(self, mock_logger):
        """Create a ClientManager instance with logger."""
        return ClientManager(logger=mock_logger)
    
    @pytest.fixture
    def sample_resource(self):
        """Create a sample MappingResource for testing."""
        resource = MappingResource()
        resource.name = "test_resource"
        resource.client_class_path = "test.module.TestClient"
        resource.config_template = json.dumps({"api_key": "test123", "timeout": 30})
        return resource
    
    @pytest.fixture
    def sample_resource_no_config(self):
        """Create a sample MappingResource without config."""
        resource = MappingResource()
        resource.name = "test_resource_no_config"
        resource.client_class_path = "test.module.TestClient"
        resource.config_template = None
        return resource
    
    @pytest.mark.asyncio
    async def test_client_instantiation(self, client_manager, sample_resource):
        """Test that get_client_instance correctly instantiates a client."""
        # Mock the client class
        mock_client_class = Mock(return_value="mock_client_instance")
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = mock_client_class
            mock_import.return_value = mock_module
            
            # Get client instance
            client = await client_manager.get_client_instance(sample_resource)
            
            # Verify
            assert client == "mock_client_instance"
            mock_import.assert_called_once_with("test.module")
            mock_client_class.assert_called_once_with(
                config={"api_key": "test123", "timeout": 30}
            )
    
    @pytest.mark.asyncio
    async def test_client_caching(self, client_manager, sample_resource):
        """Test that multiple calls return the same cached instance."""
        # Mock the client class
        mock_client_instance = Mock()
        mock_client_class = Mock(return_value=mock_client_instance)
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = mock_client_class
            mock_import.return_value = mock_module
            
            # Get client instance multiple times
            client1 = await client_manager.get_client_instance(sample_resource)
            client2 = await client_manager.get_client_instance(sample_resource)
            client3 = await client_manager.get_client_instance(sample_resource)
            
            # Verify same instance returned
            assert client1 is client2
            assert client2 is client3
            
            # Verify client class only instantiated once
            mock_client_class.assert_called_once()
            mock_import.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_different_configurations(self, client_manager):
        """Test that different configurations return different instances."""
        # Create two resources with different configs
        resource1 = MappingResource()
        resource1.name = "resource1"
        resource1.client_class_path = "test.module.TestClient"
        resource1.config_template = json.dumps({"api_key": "key1"})
        
        resource2 = MappingResource()
        resource2.name = "resource2"
        resource2.client_class_path = "test.module.TestClient"
        resource2.config_template = json.dumps({"api_key": "key2"})
        
        # Mock the client class
        mock_client_class = Mock(side_effect=["client1", "client2"])
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = mock_client_class
            mock_import.return_value = mock_module
            
            # Get client instances
            client1 = await client_manager.get_client_instance(resource1)
            client2 = await client_manager.get_client_instance(resource2)
            
            # Verify different instances
            assert client1 != client2
            assert client1 == "client1"
            assert client2 == "client2"
            
            # Verify client class instantiated twice with different configs
            assert mock_client_class.call_count == 2
            mock_client_class.assert_any_call(config={"api_key": "key1"})
            mock_client_class.assert_any_call(config={"api_key": "key2"})
    
    @pytest.mark.asyncio
    async def test_invalid_class_path(self, client_manager_with_logger, sample_resource):
        """Test that invalid client_class_path raises ClientInitializationError."""
        sample_resource.client_class_path = "invalid.module.NonExistentClient"
        
        with patch('importlib.import_module', side_effect=ImportError("Module not found")):
            with pytest.raises(ClientInitializationError) as exc_info:
                await client_manager_with_logger.get_client_instance(sample_resource)
            
            assert "Could not load client class" in str(exc_info.value)
            assert "NonExistentClient" in str(exc_info.value)
            client_manager_with_logger.logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_missing_class_in_module(self, client_manager_with_logger, sample_resource):
        """Test error when class doesn't exist in module."""
        # Create a mock module without the TestClient attribute
        mock_module = MagicMock(spec=[])  # Empty spec means no attributes
        
        with patch('importlib.import_module', return_value=mock_module):
            with pytest.raises(ClientInitializationError) as exc_info:
                await client_manager_with_logger.get_client_instance(sample_resource)
            
            assert "Could not load client class" in str(exc_info.value)
            client_manager_with_logger.logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_missing_configuration(self, client_manager):
        """Test graceful handling of missing configuration."""
        resource = MappingResource()
        resource.name = "test_resource"
        # Missing client_class_path
        resource.client_class_path = None
        resource.config_template = None
        
        with pytest.raises(ClientInitializationError) as exc_info:
            await client_manager.get_client_instance(resource)
        
        # The error should indicate the issue with None client_class_path
        assert "Unexpected error initializing client" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalid_json_config(self, client_manager_with_logger):
        """Test error handling for invalid JSON in config_template."""
        resource = MappingResource()
        resource.name = "test_resource"
        resource.client_class_path = "test.module.TestClient"
        resource.config_template = "invalid json {"
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = Mock()
            mock_import.return_value = mock_module
            
            with pytest.raises(ClientInitializationError) as exc_info:
                await client_manager_with_logger.get_client_instance(resource)
            
            assert "Invalid configuration template JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_client_initialization_error(self, client_manager_with_logger, sample_resource):
        """Test handling of errors during client initialization."""
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            # Client class raises error on instantiation
            mock_module.TestClient = Mock(side_effect=Exception("Client init failed"))
            mock_import.return_value = mock_module
            
            with pytest.raises(ClientInitializationError) as exc_info:
                await client_manager_with_logger.get_client_instance(sample_resource)
            
            assert "Unexpected error initializing client" in str(exc_info.value)
            client_manager_with_logger.logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_client_without_config(self, client_manager, sample_resource_no_config):
        """Test client instantiation without config template."""
        mock_client_class = Mock(return_value="mock_client_instance")
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = mock_client_class
            mock_import.return_value = mock_module
            
            # Get client instance
            client = await client_manager.get_client_instance(sample_resource_no_config)
            
            # Verify client created with empty config
            assert client == "mock_client_instance"
            mock_client_class.assert_called_once_with(config={})
    
    def test_get_client_cache(self, client_manager):
        """Test get_client_cache returns the cache dictionary."""
        # Initially empty
        cache = client_manager.get_client_cache()
        assert cache == {}
        assert cache is client_manager._client_cache
        
        # Add to cache and verify
        client_manager._client_cache["test_key"] = "test_value"
        cache = client_manager.get_client_cache()
        assert cache == {"test_key": "test_value"}
    
    def test_clear_cache(self, client_manager_with_logger):
        """Test clear_cache empties the cache."""
        # Add some items to cache
        client_manager_with_logger._client_cache = {
            "client1": Mock(),
            "client2": Mock(),
            "client3": Mock()
        }
        
        # Clear cache
        client_manager_with_logger.clear_cache()
        
        # Verify cache is empty
        assert client_manager_with_logger._client_cache == {}
        client_manager_with_logger.logger.debug.assert_called_with("Client cache cleared")
    
    def test_get_cache_size(self, client_manager):
        """Test get_cache_size returns correct count."""
        # Initially zero
        assert client_manager.get_cache_size() == 0
        
        # Add items and check size
        client_manager._client_cache["client1"] = Mock()
        assert client_manager.get_cache_size() == 1
        
        client_manager._client_cache["client2"] = Mock()
        client_manager._client_cache["client3"] = Mock()
        assert client_manager.get_cache_size() == 3
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, client_manager):
        """Test that cache keys are properly generated for different resources."""
        # Resource with config
        resource1 = MappingResource()
        resource1.name = "resource1"
        resource1.client_class_path = "test.module.Client1"
        resource1.config_template = json.dumps({"key": "value1"})
        
        # Same resource with different config
        resource2 = MappingResource()
        resource2.name = "resource1"  # Same name
        resource2.client_class_path = "test.module.Client1"  # Same path
        resource2.config_template = json.dumps({"key": "value2"})  # Different config
        
        mock_client_class = Mock(side_effect=["client1", "client2"])
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.Client1 = mock_client_class
            mock_import.return_value = mock_module
            
            # Get both clients
            client1 = await client_manager.get_client_instance(resource1)
            client2 = await client_manager.get_client_instance(resource2)
            
            # Should be different instances due to different configs
            assert client1 != client2
            assert mock_client_class.call_count == 2
    
    @pytest.mark.asyncio
    async def test_logging_optimization_messages(self, client_manager_with_logger, sample_resource):
        """Test that optimization debug messages are logged."""
        mock_client_class = Mock(return_value="mock_client")
        
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.TestClient = mock_client_class
            mock_import.return_value = mock_module
            
            # First call - should create new instance
            await client_manager_with_logger.get_client_instance(sample_resource)
            client_manager_with_logger.logger.debug.assert_any_call(
                "OPTIMIZATION: Creating new client instance for test_resource"
            )
            client_manager_with_logger.logger.debug.assert_any_call(
                "OPTIMIZATION: Cached client for test_resource"
            )
            
            # Second call - should use cache
            await client_manager_with_logger.get_client_instance(sample_resource)
            client_manager_with_logger.logger.debug.assert_any_call(
                "OPTIMIZATION: Using cached client for test_resource"
            )
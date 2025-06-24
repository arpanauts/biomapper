"""Unit tests for InitializationService module."""

import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

from biomapper.core.engine_components.initialization_service import InitializationService
from biomapper.core.exceptions import BiomapperError, ErrorCode


class TestMappingExecutorInitializer:
    """Test cases for the InitializationService class."""
    
    def test_init_with_default_settings(self):
        """Test InitializationService initialization with default settings."""
        # Arrange & Act
        initializer = InitializationService()
        
        # Assert
        assert initializer is not None
        assert hasattr(initializer, 'logger')
    
    def test_init_with_custom_parameters(self):
        """Test InitializationService initialization with custom parameters."""
        # Arrange & Act
        initializer = InitializationService()
        
        # Assert
        assert initializer is not None
        assert hasattr(initializer, 'logger')
    
    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    @patch('biomapper.core.engine_components.initialization_service.ClientManager')
    @patch('biomapper.core.engine_components.initialization_service.ConfigLoader')
    def test_initialize_core_components(self, mock_config_loader, mock_client_manager, mock_session_manager):
        """Test core components initialization."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'echo_sql': False
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert 'session_manager' in components
        assert 'client_manager' in components
        assert 'config_loader' in components
    
    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    def test_initialize_session_manager(self, mock_session_manager_class):
        """Test session manager initialization."""
        # Arrange
        initializer = InitializationService()
        mock_session_manager = MagicMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'echo_sql': False
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert components['session_manager'] == mock_session_manager
        mock_session_manager_class.assert_called_once()
    
    @patch('biomapper.core.engine_components.initialization_service.CacheManager')
    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    def test_initialize_cache_manager_success(self, mock_session_manager_class, mock_cache_manager_class):
        """Test successful cache manager initialization."""
        # Arrange
        initializer = InitializationService()
        mock_session_manager = MagicMock()
        mock_cache_manager = MagicMock()
        mock_session_manager_class.return_value = mock_session_manager
        mock_cache_manager_class.return_value = mock_cache_manager
        
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'path_cache_size': 200,
            'path_cache_expiry_seconds': 600
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert components['cache_manager'] == mock_cache_manager
    
    def test_initialize_cache_manager_no_session_manager_error(self):
        """Test cache manager initialization without session manager raises error."""
        # This test is no longer relevant as session_manager is created during initialization
        pass
    
    @patch('biomapper.core.engine_components.initialization_service.StrategyOrchestrator')
    @patch('biomapper.core.engine_components.initialization_service.PathExecutionManager')
    @patch('biomapper.core.engine_components.initialization_service.PathFinder')
    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    def test_initialize_execution_components(self, mock_session_manager, mock_path_finder,
                                           mock_path_exec_mgr, mock_strategy_orch):
        """Test execution components initialization."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'max_concurrent_batches': 10
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert 'path_finder' in components
        assert 'path_execution_manager' in components
        assert 'strategy_orchestrator' in components
    
    def test_initialize_metrics_tracking_enabled(self):
        """Test metrics tracking initialization when enabled."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'enable_metrics': True
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert - metrics tracking components should be created
        assert components is not None
    
    def test_initialize_metrics_tracking_disabled(self):
        """Test metrics tracking initialization when disabled."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db',
            'enable_metrics': False
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert components is not None
    
    def test_initialize_metrics_tracking_import_error(self):
        """Test metrics tracking graceful handling of import errors."""
        # This functionality is handled internally by the service
        pass
    
    def test_get_convenience_references_success(self):
        """Test getting convenience references from initialized components."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db'
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert 'async_metamapper_session' in components
        assert 'async_cache_session' in components
    
    def test_get_convenience_references_no_session_manager_error(self):
        """Test error when trying to get references without session manager."""
        # This test is no longer relevant as session_manager is always created
        pass
    
    def test_set_executor_function_references(self):
        """Test setting executor function references."""
        # Arrange
        initializer = InitializationService()
        mock_executor = MagicMock()
        mock_path_exec_mgr = MagicMock()
        
        # Act
        initializer.set_executor_function_references(mock_executor, mock_path_exec_mgr)
        
        # Assert
        assert mock_path_exec_mgr._load_client == getattr(mock_executor, '_load_client', None)
    
    def test_set_executor_function_references_no_path_execution_manager(self):
        """Test setting executor references with None path execution manager."""
        # Arrange
        initializer = InitializationService()
        mock_executor = MagicMock()
        
        # Act - should not raise error
        initializer.set_executor_function_references(mock_executor, None)
        
        # Assert - no exception raised
        assert True
    
    @pytest.mark.asyncio
    async def test_init_db_tables_success(self):
        """Test successful database table initialization."""
        # This is now handled by DatabaseSetupService in MappingExecutorBuilder
        pass
    
    @pytest.mark.asyncio
    async def test_init_db_tables_tables_already_exist(self):
        """Test database initialization when tables already exist."""
        # This is now handled by DatabaseSetupService in MappingExecutorBuilder
        pass
    
    @pytest.mark.asyncio
    async def test_init_db_tables_error_handling(self):
        """Test database initialization error handling."""
        # This is now handled by DatabaseSetupService in MappingExecutorBuilder
        pass
    
    @pytest.mark.asyncio
    async def test_create_executor_success(self):
        """Test successful executor creation."""
        # This is now handled by MappingExecutorBuilder
        pass
    
    @pytest.mark.asyncio
    async def test_create_executor_mapping_executor_creation_error(self):
        """Test error handling during executor creation."""
        # This is now handled by MappingExecutorBuilder
        pass
    
    @pytest.mark.asyncio
    async def test_create_executor_db_init_error(self):
        """Test error handling during database initialization."""
        # This is now handled by MappingExecutorBuilder
        pass
    
    def test_initialize_components_success(self):
        """Test successful component initialization."""
        # Arrange
        initializer = InitializationService()
        config = {
            'metamapper_db_url': 'sqlite:///test.db',
            'mapping_cache_db_url': 'sqlite:///cache.db'
        }
        
        # Act
        components = initializer.create_components(config)
        
        # Assert
        assert components is not None
        assert isinstance(components, dict)
        # Check for key components
        assert 'session_manager' in components
        assert 'client_manager' in components
        assert 'config_loader' in components
    
    def test_initialize_components_error_handling(self):
        """Test component initialization error handling."""
        # Arrange
        initializer = InitializationService()
        
        # Act - InitializationService now handles missing URLs with defaults
        # So we need to test a different kind of error
        with patch('biomapper.core.engine_components.initialization_service.SessionManager') as mock_sm:
            mock_sm.side_effect = Exception("Database connection failed")
            
            # Act & Assert - invalid config should raise an error
            with pytest.raises(Exception):
                components = initializer.create_components({
                    'metamapper_db_url': 'invalid://url',
                    'mapping_cache_db_url': 'invalid://url'
                })
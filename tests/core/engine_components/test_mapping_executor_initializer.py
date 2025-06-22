"""Unit tests for MappingExecutorInitializer module."""

import os
from unittest.mock import Mock, patch, AsyncMock
import pytest

from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder as MappingExecutorInitializer
from biomapper.core.exceptions import BiomapperError, ErrorCode


class TestMappingExecutorInitializer:
    """Test cases for the MappingExecutorInitializer class."""
    
    def test_init_with_default_settings(self):
        """Test MappingExecutorInitializer initialization with default settings."""
        # Arrange & Act
        with patch('biomapper.core.engine_components.mapping_executor_initializer.settings') as mock_settings:
            mock_settings.metamapper_db_url = "sqlite:///default_metamapper.db"
            mock_settings.cache_db_url = "sqlite:///default_cache.db"
            
            initializer = MappingExecutorInitializer()
        
        # Assert
        assert initializer.metamapper_db_url == "sqlite:///default_metamapper.db"
        assert initializer.mapping_cache_db_url == "sqlite:///default_cache.db"
        assert initializer.echo_sql is False
        assert initializer.path_cache_size == 100
        assert initializer.path_cache_expiry_seconds == 300
        assert initializer.max_concurrent_batches == 5
        assert initializer.enable_metrics is True
        assert initializer.checkpoint_enabled is False
        assert initializer.checkpoint_dir is None
        assert initializer.batch_size == 100
        assert initializer.max_retries == 3
        assert initializer.retry_delay == 5
        
        # Verify component references are initialized to None
        assert initializer.session_manager is None
        assert initializer.client_manager is None
        assert initializer.config_loader is None
        assert initializer.strategy_handler is None
        assert initializer.path_finder is None
        assert initializer.path_execution_manager is None
        assert initializer.cache_manager is None
        assert initializer.identifier_loader is None
        assert initializer.strategy_orchestrator is None
        assert initializer.checkpoint_manager is None
        assert initializer.progress_reporter is None
        assert initializer._langfuse_tracker is None
    
    def test_init_with_custom_parameters(self):
        """Test MappingExecutorInitializer initialization with custom parameters."""
        # Arrange
        custom_params = {
            'metamapper_db_url': 'sqlite:///custom_metamapper.db',
            'mapping_cache_db_url': 'sqlite:///custom_cache.db',
            'echo_sql': True,
            'path_cache_size': 200,
            'path_cache_expiry_seconds': 600,
            'max_concurrent_batches': 10,
            'enable_metrics': False,
            'checkpoint_enabled': True,
            'checkpoint_dir': '/tmp/checkpoints',
            'batch_size': 50,
            'max_retries': 5,
            'retry_delay': 10,
        }
        
        # Act
        initializer = MappingExecutorInitializer(**custom_params)
        
        # Assert
        assert initializer.metamapper_db_url == custom_params['metamapper_db_url']
        assert initializer.mapping_cache_db_url == custom_params['mapping_cache_db_url']
        assert initializer.echo_sql == custom_params['echo_sql']
        assert initializer.path_cache_size == custom_params['path_cache_size']
        assert initializer.path_cache_expiry_seconds == custom_params['path_cache_expiry_seconds']
        assert initializer.max_concurrent_batches == custom_params['max_concurrent_batches']
        assert initializer.enable_metrics == custom_params['enable_metrics']
        assert initializer.checkpoint_enabled == custom_params['checkpoint_enabled']
        assert initializer.checkpoint_dir == custom_params['checkpoint_dir']
        assert initializer.batch_size == custom_params['batch_size']
        assert initializer.max_retries == custom_params['max_retries']
        assert initializer.retry_delay == custom_params['retry_delay']
    
    @patch('biomapper.core.engine_components.mapping_executor_initializer.CheckpointManager')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.ProgressReporter')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.ClientManager')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.ConfigLoader')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.PathFinder')
    def test_initialize_core_components(self, mock_path_finder, mock_config_loader, 
                                      mock_client_manager, mock_progress_reporter, 
                                      mock_checkpoint_manager):
        """Test initialization of core components."""
        # Arrange
        initializer = MappingExecutorInitializer(
            checkpoint_enabled=True,
            checkpoint_dir='/tmp/test',
            path_cache_size=150,
            path_cache_expiry_seconds=400
        )
        
        # Act
        initializer._initialize_core_components()
        
        # Assert
        mock_checkpoint_manager.assert_called_once_with(
            checkpoint_dir='/tmp/test',
            logger=initializer.logger
        )
        mock_progress_reporter.assert_called_once()
        mock_client_manager.assert_called_once_with(logger=initializer.logger)
        mock_config_loader.assert_called_once_with(logger=initializer.logger)
        mock_path_finder.assert_called_once_with(
            cache_size=150,
            cache_expiry_seconds=400
        )
        
        # Verify components are assigned
        assert initializer.checkpoint_manager == mock_checkpoint_manager.return_value
        assert initializer.progress_reporter == mock_progress_reporter.return_value
        assert initializer.client_manager == mock_client_manager.return_value
        assert initializer.config_loader == mock_config_loader.return_value
        assert initializer.path_finder == mock_path_finder.return_value
    
    @patch('biomapper.core.engine_components.mapping_executor_initializer.SessionManager')
    def test_initialize_session_manager(self, mock_session_manager):
        """Test initialization of SessionManager."""
        # Arrange
        initializer = MappingExecutorInitializer(
            metamapper_db_url='sqlite:///test_meta.db',
            mapping_cache_db_url='sqlite:///test_cache.db',
            echo_sql=True
        )
        
        # Act
        initializer._initialize_session_manager()
        
        # Assert
        mock_session_manager.assert_called_once_with(
            metamapper_db_url='sqlite:///test_meta.db',
            mapping_cache_db_url='sqlite:///test_cache.db',
            echo_sql=True
        )
        assert initializer.session_manager == mock_session_manager.return_value
    
    @patch('biomapper.core.engine_components.mapping_executor_initializer.CacheManager')
    def test_initialize_cache_manager_success(self, mock_cache_manager):
        """Test successful initialization of CacheManager."""
        # Arrange
        initializer = MappingExecutorInitializer()
        mock_session_manager = Mock()
        mock_session_manager.CacheSessionFactory = Mock()
        initializer.session_manager = mock_session_manager
        
        # Act
        initializer._initialize_cache_manager()
        
        # Assert
        mock_cache_manager.assert_called_once_with(
            cache_sessionmaker=mock_session_manager.CacheSessionFactory,
            logger=initializer.logger
        )
        assert initializer.cache_manager == mock_cache_manager.return_value
    
    def test_initialize_cache_manager_no_session_manager_error(self):
        """Test CacheManager initialization fails when SessionManager is not initialized."""
        # Arrange
        initializer = MappingExecutorInitializer()
        # session_manager is None by default
        
        # Act & Assert
        with pytest.raises(BiomapperError) as exc_info:
            initializer._initialize_cache_manager()
        
        assert exc_info.value.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "SessionManager must be initialized before CacheManager" in str(exc_info.value)
    
    @patch('biomapper.core.engine_components.mapping_executor_initializer.StrategyOrchestrator')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.PathExecutionManager')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.IdentifierLoader')
    @patch('biomapper.core.engine_components.mapping_executor_initializer.StrategyHandler')
    def test_initialize_execution_components(self, mock_strategy_handler, mock_identifier_loader,
                                          mock_path_execution_manager, mock_strategy_orchestrator):
        """Test initialization of execution components."""
        # Arrange
        initializer = MappingExecutorInitializer(
            max_retries=5,
            retry_delay=10,
            batch_size=25,
            max_concurrent_batches=8,
            enable_metrics=True
        )
        
        # Mock session manager and cache manager
        mock_session_manager = Mock()
        mock_session_manager.MetamapperSessionFactory = Mock()
        initializer.session_manager = mock_session_manager
        initializer.cache_manager = Mock()
        
        mock_mapping_executor = Mock()
        
        # Act
        initializer._initialize_execution_components(mock_mapping_executor)
        
        # Assert
        mock_strategy_handler.assert_called_once_with(mapping_executor=mock_mapping_executor)
        mock_identifier_loader.assert_called_once_with(
            metamapper_session_factory=mock_session_manager.MetamapperSessionFactory
        )
        mock_path_execution_manager.assert_called_once_with(
            metamapper_session_factory=mock_session_manager.MetamapperSessionFactory,
            cache_manager=None,  # MappingExecutor handles caching directly
            logger=initializer.logger,
            semaphore=None,  # Will create semaphore as needed
            max_retries=5,
            retry_delay=10,
            batch_size=25,
            max_concurrent_batches=8,
            enable_metrics=True,
            load_client_func=None,
            execute_mapping_step_func=None,
            calculate_confidence_score_func=None,
            create_mapping_path_details_func=None,
            determine_mapping_source_func=None,
            track_mapping_metrics_func=None
        )
        mock_strategy_orchestrator.assert_called_once_with(
            metamapper_session_factory=mock_session_manager.MetamapperSessionFactory,
            cache_manager=initializer.cache_manager,
            strategy_handler=mock_strategy_handler.return_value,
            mapping_executor=mock_mapping_executor,
            logger=initializer.logger
        )
        
        # Verify components are assigned
        assert initializer.strategy_handler == mock_strategy_handler.return_value
        assert initializer.identifier_loader == mock_identifier_loader.return_value
        assert initializer.path_execution_manager == mock_path_execution_manager.return_value
        assert initializer.strategy_orchestrator == mock_strategy_orchestrator.return_value
    
    @patch.dict(os.environ, {
        'LANGFUSE_HOST': 'https://test.langfuse.com',
        'LANGFUSE_PUBLIC_KEY': 'test_public_key',
        'LANGFUSE_SECRET_KEY': 'test_secret_key'
    })
    def test_initialize_metrics_tracking_enabled(self):
        """Test metrics tracking initialization when enabled and available."""
        # Arrange
        initializer = MappingExecutorInitializer(enable_metrics=True)
        mock_langfuse_instance = Mock()
        
        with patch('builtins.__import__') as mock_import:
            mock_langfuse_module = Mock()
            mock_langfuse_module.Langfuse.return_value = mock_langfuse_instance
            mock_import.return_value = mock_langfuse_module
            
            # Act
            initializer._initialize_metrics_tracking()
        
        # Assert
        assert initializer._langfuse_tracker == mock_langfuse_instance
    
    def test_initialize_metrics_tracking_disabled(self):
        """Test metrics tracking when disabled."""
        # Arrange
        initializer = MappingExecutorInitializer(enable_metrics=False)
        
        # Act
        initializer._initialize_metrics_tracking()
        
        # Assert
        assert initializer._langfuse_tracker is None
    
    def test_initialize_metrics_tracking_import_error(self):
        """Test metrics tracking handles import error gracefully."""
        # Arrange
        initializer = MappingExecutorInitializer(enable_metrics=True)
        
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("langfuse not available")
            
            # Act
            initializer._initialize_metrics_tracking()
        
        # Assert
        assert initializer._langfuse_tracker is None
    
    def test_get_convenience_references_success(self):
        """Test getting convenience references when SessionManager is initialized."""
        # Arrange
        initializer = MappingExecutorInitializer()
        mock_session_manager = Mock()
        mock_session_manager.async_metamapper_engine = Mock()
        mock_session_manager.MetamapperSessionFactory = Mock()
        mock_session_manager.async_metamapper_session = Mock()
        mock_session_manager.async_cache_engine = Mock()
        mock_session_manager.CacheSessionFactory = Mock()
        mock_session_manager.async_cache_session = Mock()
        initializer.session_manager = mock_session_manager
        
        # Act
        references = initializer.get_convenience_references()
        
        # Assert
        expected_keys = [
            'async_metamapper_engine',
            'MetamapperSessionFactory',
            'async_metamapper_session',
            'async_cache_engine',
            'CacheSessionFactory',
            'async_cache_session'
        ]
        assert all(key in references for key in expected_keys)
        assert references['async_metamapper_engine'] == mock_session_manager.async_metamapper_engine
        assert references['MetamapperSessionFactory'] == mock_session_manager.MetamapperSessionFactory
        assert references['async_metamapper_session'] == mock_session_manager.async_metamapper_session
        assert references['async_cache_engine'] == mock_session_manager.async_cache_engine
        assert references['CacheSessionFactory'] == mock_session_manager.CacheSessionFactory
        assert references['async_cache_session'] == mock_session_manager.async_cache_session
    
    def test_get_convenience_references_no_session_manager_error(self):
        """Test getting convenience references fails when SessionManager is not initialized."""
        # Arrange
        initializer = MappingExecutorInitializer()
        # session_manager is None by default
        
        # Act & Assert
        with pytest.raises(BiomapperError) as exc_info:
            initializer.get_convenience_references()
        
        assert exc_info.value.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "SessionManager must be initialized before getting convenience references" in str(exc_info.value)
    
    def test_set_executor_function_references(self):
        """Test setting function references on PathExecutionManager."""
        # Arrange
        initializer = MappingExecutorInitializer(enable_metrics=True)
        mock_path_execution_manager = Mock()
        initializer.path_execution_manager = mock_path_execution_manager
        
        mock_mapping_executor = Mock()
        mock_mapping_executor._load_client = Mock()
        mock_mapping_executor._execute_mapping_step = Mock()
        mock_mapping_executor._calculate_confidence_score = Mock()
        mock_mapping_executor._create_mapping_path_details = Mock()
        mock_mapping_executor._determine_mapping_source = Mock()
        mock_mapping_executor.track_mapping_metrics = Mock()
        
        # Act
        initializer.set_executor_function_references(mock_mapping_executor)
        
        # Assert
        assert mock_path_execution_manager._load_client == mock_mapping_executor._load_client
        assert mock_path_execution_manager._execute_mapping_step == mock_mapping_executor._execute_mapping_step
        assert mock_path_execution_manager._calculate_confidence_score == mock_mapping_executor._calculate_confidence_score
        assert mock_path_execution_manager._create_mapping_path_details == mock_mapping_executor._create_mapping_path_details
        assert mock_path_execution_manager._determine_mapping_source == mock_mapping_executor._determine_mapping_source
        assert mock_path_execution_manager.track_mapping_metrics == mock_mapping_executor.track_mapping_metrics
    
    def test_set_executor_function_references_no_path_execution_manager(self):
        """Test setting function references when PathExecutionManager is None."""
        # Arrange
        initializer = MappingExecutorInitializer()
        # path_execution_manager is None by default
        mock_mapping_executor = Mock()
        
        # Act (should not raise error)
        initializer.set_executor_function_references(mock_mapping_executor)
        
        # Assert - no error should occur
        assert True  # Test passes if no exception is raised
    
    @pytest.mark.asyncio
    async def test_init_db_tables_success(self):
        """Test successful database table initialization."""
        # Arrange
        initializer = MappingExecutorInitializer()
        
        mock_engine = Mock()
        mock_engine.url = "sqlite:///test.db"
        
        mock_connection = AsyncMock()
        mock_connection.run_sync = AsyncMock()
        mock_connection.run_sync.return_value = False  # Tables don't exist
        
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_begin_connection = AsyncMock()
        mock_begin_connection.run_sync = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_begin_connection)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_metadata = Mock()
        
        # Act
        await initializer._init_db_tables(mock_engine, mock_metadata)
        
        # Assert
        mock_connection.run_sync.assert_called_once()
        mock_begin_connection.run_sync.assert_called_once_with(mock_metadata.create_all)
    
    @pytest.mark.asyncio
    async def test_init_db_tables_tables_already_exist(self):
        """Test database table initialization when tables already exist."""
        # Arrange
        initializer = MappingExecutorInitializer()
        
        mock_engine = Mock()
        mock_engine.url = "sqlite:///test.db"
        
        mock_connection = AsyncMock()
        mock_connection.run_sync = AsyncMock()
        mock_connection.run_sync.return_value = True  # Tables exist
        
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_metadata = Mock()
        
        # Act
        await initializer._init_db_tables(mock_engine, mock_metadata)
        
        # Assert
        mock_connection.run_sync.assert_called_once()
        # begin() should not be called since tables already exist
        assert not hasattr(mock_engine, 'begin') or not mock_engine.begin.called
    
    @pytest.mark.asyncio
    async def test_init_db_tables_error_handling(self):
        """Test database table initialization error handling."""
        # Arrange
        initializer = MappingExecutorInitializer()
        
        mock_engine = Mock()
        mock_engine.url = "sqlite:///test.db"
        
        mock_connection = AsyncMock()
        mock_connection.run_sync = AsyncMock()
        mock_connection.run_sync.side_effect = Exception("Database connection failed")
        
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_metadata = Mock()
        
        # Act & Assert
        with pytest.raises(BiomapperError) as exc_info:
            await initializer._init_db_tables(mock_engine, mock_metadata)
        
        assert exc_info.value.error_code == ErrorCode.DATABASE_INITIALIZATION_ERROR
        assert "Failed to initialize database tables" in str(exc_info.value)
        assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('biomapper.core.engine_components.mapping_executor_initializer.CacheBase')
    async def test_create_executor_success(self, mock_cache_base):
        """Test successful MappingExecutor creation."""
        # Arrange
        initializer = MappingExecutorInitializer(
            metamapper_db_url='sqlite:///test_meta.db',
            mapping_cache_db_url='sqlite:///test_cache.db',
            echo_sql=True,
            batch_size=25
        )
        
        # Mock MappingExecutor
        mock_executor = Mock()
        mock_executor.async_cache_engine = Mock()
        mock_executor.logger = Mock()
        
        mock_cache_base.metadata = Mock()
        
        with patch('biomapper.core.mapping_executor.MappingExecutor') as mock_executor_class:
            mock_executor_class.return_value = mock_executor
            
            with patch.object(initializer, '_init_db_tables', new_callable=AsyncMock) as mock_init_db:
                # Act
                result = await initializer.create_executor()
        
        # Assert
        mock_executor_class.assert_called_once_with(
            metamapper_db_url='sqlite:///test_meta.db',
            mapping_cache_db_url='sqlite:///test_cache.db',
            echo_sql=True,
            path_cache_size=100,
            path_cache_expiry_seconds=300,
            max_concurrent_batches=5,
            enable_metrics=True,
            checkpoint_enabled=False,
            checkpoint_dir=None,
            batch_size=25,
            max_retries=3,
            retry_delay=5,
        )
        
        mock_init_db.assert_called_once_with(mock_executor.async_cache_engine, mock_cache_base.metadata)
        assert result == mock_executor
    
    @pytest.mark.asyncio
    @patch('biomapper.core.engine_components.mapping_executor_initializer.CacheBase')
    async def test_create_executor_mapping_executor_creation_error(self, mock_cache_base):
        """Test MappingExecutor creation handles errors during MappingExecutor instantiation."""
        # Arrange
        initializer = MappingExecutorInitializer()
        
        with patch('biomapper.core.mapping_executor.MappingExecutor') as mock_executor_class:
            mock_executor_class.side_effect = Exception("MappingExecutor creation failed")
            
            # Act & Assert
            with pytest.raises(BiomapperError) as exc_info:
                await initializer.create_executor()
        
        assert exc_info.value.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "MappingExecutor creation failed" in str(exc_info.value)
        assert "MappingExecutor creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('biomapper.core.engine_components.mapping_executor_initializer.CacheBase')
    async def test_create_executor_db_init_error(self, mock_cache_base):
        """Test MappingExecutor creation handles errors during database initialization."""
        # Arrange
        initializer = MappingExecutorInitializer()
        
        mock_executor = Mock()
        mock_executor.async_cache_engine = Mock()
        mock_executor.logger = Mock()
        
        mock_cache_base.metadata = Mock()
        
        with patch('biomapper.core.mapping_executor.MappingExecutor') as mock_executor_class:
            mock_executor_class.return_value = mock_executor
            
            with patch.object(initializer, '_init_db_tables', new_callable=AsyncMock) as mock_init_db:
                mock_init_db.side_effect = BiomapperError(
                    "DB init failed", 
                    error_code=ErrorCode.DATABASE_INITIALIZATION_ERROR
                )
                
                # Act & Assert
                with pytest.raises(BiomapperError) as exc_info:
                    await initializer.create_executor()
        
        assert exc_info.value.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "MappingExecutor creation failed" in str(exc_info.value)
    
    @patch('biomapper.core.engine_components.mapping_executor_initializer.settings')
    def test_initialize_components_success(self, mock_settings):
        """Test successful component initialization."""
        # Arrange
        mock_settings.metamapper_db_url = "sqlite:///test_meta.db"
        mock_settings.cache_db_url = "sqlite:///test_cache.db"
        
        initializer = MappingExecutorInitializer()
        mock_mapping_executor = Mock()
        
        # Mock all initialization methods
        with patch.object(initializer, '_initialize_core_components') as mock_init_core, \
             patch.object(initializer, '_initialize_session_manager') as mock_init_session, \
             patch.object(initializer, '_initialize_cache_manager') as mock_init_cache, \
             patch.object(initializer, '_initialize_execution_components') as mock_init_execution, \
             patch.object(initializer, '_initialize_metrics_tracking') as mock_init_metrics:
            
            # Set up mock components
            initializer.session_manager = Mock()
            initializer.client_manager = Mock()
            initializer.config_loader = Mock()
            initializer.strategy_handler = Mock()
            initializer.path_finder = Mock()
            initializer.path_execution_manager = Mock()
            initializer.cache_manager = Mock()
            initializer.identifier_loader = Mock()
            initializer.strategy_orchestrator = Mock()
            initializer.checkpoint_manager = Mock()
            initializer.progress_reporter = Mock()
            initializer._langfuse_tracker = Mock()
            
            # Act
            result = initializer.initialize_components(mock_mapping_executor)
        
        # Assert
        mock_init_core.assert_called_once()
        mock_init_session.assert_called_once()
        mock_init_cache.assert_called_once()
        mock_init_execution.assert_called_once_with(mock_mapping_executor)
        mock_init_metrics.assert_called_once()
        
        # Verify returned components
        expected_keys = [
            'session_manager', 'client_manager', 'config_loader', 'strategy_handler',
            'path_finder', 'path_execution_manager', 'cache_manager', 'identifier_loader',
            'strategy_orchestrator', 'checkpoint_manager', 'progress_reporter', 'langfuse_tracker'
        ]
        assert all(key in result for key in expected_keys)
    
    def test_initialize_components_error_handling(self):
        """Test component initialization error handling."""
        # Arrange
        initializer = MappingExecutorInitializer()
        mock_mapping_executor = Mock()
        
        with patch.object(initializer, '_initialize_core_components') as mock_init_core:
            mock_init_core.side_effect = Exception("Core component initialization failed")
            
            # Act & Assert
            with pytest.raises(BiomapperError) as exc_info:
                initializer.initialize_components(mock_mapping_executor)
        
        assert exc_info.value.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "MappingExecutor initialization failed" in str(exc_info.value)
        assert "Core component initialization failed" in str(exc_info.value)
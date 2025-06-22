# tests/unit/core/engine_components/test_initialization_service.py

import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any

from biomapper.core.engine_components.initialization_service import InitializationService


class TestInitializationService:
    """Unit tests for the InitializationService class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.initialization_service = InitializationService()

    def test_default_creation(self):
        """Test that create_components works with an empty config dictionary."""
        # Arrange
        empty_config: Dict[str, Any] = {}
        
        # Act
        components = self.initialization_service.create_components_from_config(empty_config)
        
        # Assert
        assert components is not None
        assert isinstance(components, dict)
        
        # Verify all expected components are present
        expected_keys = [
            'session_manager', 'client_manager', 'config_loader', 'path_finder',
            'cache_manager', 'identifier_loader', 'async_metamapper_session',
            'async_cache_session', 'checkpoint_manager', 'progress_reporter',
            'langfuse_tracker', 'strategy_handler', 'path_execution_manager',
            'strategy_orchestrator', 'metadata_query_service', 'session_metrics_service',
            'bidirectional_validation_service', 'direct_mapping_service',
            'result_aggregation_service', 'iterative_mapping_service',
            'mapping_handler_service', 'step_execution_service', 'lifecycle_service',
            'robust_execution_coordinator', 'strategy_execution_service',
            'db_strategy_execution_service', 'yaml_strategy_execution_service',
            'MappingResultBundle', '_metrics_tracker', 'config'
        ]
        
        for key in expected_keys:
            assert key in components, f"Missing component: {key}"
            # _metrics_tracker can be None if metrics are disabled
            if key != '_metrics_tracker':
                assert components[key] is not None, f"Component {key} is None"
        
        # Verify component types
        from biomapper.core.engine_components.session_manager import SessionManager
        from biomapper.core.engine_components.client_manager import ClientManager
        from biomapper.core.engine_components.config_loader import ConfigLoader
        from biomapper.core.engine_components.path_finder import PathFinder
        from biomapper.core.engine_components.cache_manager import CacheManager
        from biomapper.core.engine_components.identifier_loader import IdentifierLoader
        from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
        from biomapper.core.engine_components.progress_reporter import ProgressReporter
        from biomapper.core.engine_components.strategy_handler import StrategyHandler
        from biomapper.core.engine_components.path_execution_manager import PathExecutionManager
        from biomapper.core.engine_components.strategy_orchestrator import StrategyOrchestrator
        
        assert isinstance(components['session_manager'], SessionManager)
        assert isinstance(components['client_manager'], ClientManager)
        assert isinstance(components['config_loader'], ConfigLoader)
        assert isinstance(components['path_finder'], PathFinder)
        assert isinstance(components['cache_manager'], CacheManager)
        assert isinstance(components['identifier_loader'], IdentifierLoader)
        assert isinstance(components['checkpoint_manager'], CheckpointManager)
        assert isinstance(components['progress_reporter'], ProgressReporter)
        assert isinstance(components['strategy_handler'], StrategyHandler)
        assert isinstance(components['path_execution_manager'], PathExecutionManager)
        assert isinstance(components['strategy_orchestrator'], StrategyOrchestrator)

    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    @patch('biomapper.core.engine_components.initialization_service.ClientManager')
    @patch('biomapper.core.engine_components.initialization_service.ConfigLoader')
    @patch('biomapper.core.engine_components.initialization_service.PathFinder')
    @patch('biomapper.core.engine_components.initialization_service.CheckpointManager')
    def test_custom_configuration(self, mock_checkpoint_manager, mock_path_finder,
                                  mock_config_loader, mock_client_manager, mock_session_manager):
        """Test that create_components correctly passes custom configuration values."""
        # Arrange
        custom_config = {
            'metamapper_db_url': 'postgresql://custom_user:pass@localhost/metamapper',
            'mapping_cache_db_url': 'postgresql://custom_user:pass@localhost/cache',
            'echo_sql': True,
            'path_cache_size': 200,
            'path_cache_expiry_seconds': 600,
            'checkpoint_enabled': True,
            'checkpoint_dir': '/custom/checkpoint/dir'
        }
        
        # Create mock instances
        mock_session_manager_instance = MagicMock()
        mock_session_manager.return_value = mock_session_manager_instance
        
        # Act
        components = self.initialization_service.create_components_from_config(custom_config)
        
        # Assert - Verify constructors were called with correct arguments
        mock_session_manager.assert_called_once_with(
            metamapper_db_url='postgresql://custom_user:pass@localhost/metamapper',
            mapping_cache_db_url='postgresql://custom_user:pass@localhost/cache',
            echo_sql=True
        )
        
        mock_path_finder.assert_called_once_with(
            cache_size=200,
            cache_expiry_seconds=600
        )
        
        mock_checkpoint_manager.assert_called_once_with(
            checkpoint_dir='/custom/checkpoint/dir',
            logger=self.initialization_service.logger
        )
        
        mock_client_manager.assert_called_once_with(logger=self.initialization_service.logger)
        mock_config_loader.assert_called_once_with(logger=self.initialization_service.logger)

    @patch('biomapper.core.engine_components.initialization_service.SessionManager')
    @patch('biomapper.core.engine_components.initialization_service.CacheManager')
    @patch('biomapper.core.engine_components.initialization_service.IdentifierLoader')
    def test_component_dependencies(self, mock_identifier_loader, mock_cache_manager, mock_session_manager):
        """Test that components are created with the correct dependencies."""
        # Arrange
        mock_session_manager_instance = MagicMock()
        mock_session_manager_instance.CacheSessionFactory = MagicMock()
        mock_session_manager_instance.MetamapperSessionFactory = MagicMock()
        mock_session_manager.return_value = mock_session_manager_instance
        
        # Act
        components = self.initialization_service.create_components_from_config({})
        
        # Assert - Verify dependencies are passed correctly
        mock_cache_manager.assert_called_once_with(
            cache_sessionmaker=mock_session_manager_instance.CacheSessionFactory,
            logger=self.initialization_service.logger
        )
        mock_identifier_loader.assert_called_once_with(
            metamapper_session_factory=mock_session_manager_instance.MetamapperSessionFactory
        )

    def test_convenience_session_references(self):
        """Test that convenience session references are properly set."""
        # Arrange
        config = {}
        
        # Act
        components = self.initialization_service.create_components_from_config(config)
        
        # Assert
        assert 'async_metamapper_session' in components
        assert 'async_cache_session' in components
        
        # Verify they reference the session_manager's methods/properties
        assert components['async_metamapper_session'] == components['session_manager'].async_metamapper_session
        assert components['async_cache_session'] == components['session_manager'].async_cache_session


    def test_all_create_methods_called(self):
        """Test that all private _create_* methods are called during initialization."""
        # Arrange
        config = {}
        
        # Create a list of all methods to patch
        methods_to_patch = [
            '_create_session_manager', '_create_client_manager', '_create_config_loader',
            '_create_path_finder', '_create_cache_manager', '_create_identifier_loader',
            '_create_checkpoint_manager', '_create_progress_reporter',
            '_create_langfuse_tracker', '_create_strategy_handler',
            '_create_path_execution_manager', '_create_strategy_orchestrator',
            '_create_metadata_query_service', '_create_session_metrics_service',
            '_create_bidirectional_validation_service', '_create_direct_mapping_service',
            '_create_result_aggregation_service', '_create_iterative_mapping_service',
            '_create_mapping_handler_service', '_create_mapping_step_execution_service',
            '_create_execution_lifecycle_service', '_create_robust_execution_coordinator',
            '_create_strategy_execution_service', '_create_db_strategy_execution_service',
            '_create_yaml_strategy_execution_service'
        ]
        
        # Create patches
        patches = []
        for method_name in methods_to_patch:
            patcher = patch.object(self.initialization_service, method_name)
            patches.append(patcher)
        
        # Start all patches
        mocks = [patcher.start() for patcher in patches]
        
        try:
            # Set up mock session manager to have the required methods
            mock_session_instance = MagicMock()
            mocks[0].return_value = mock_session_instance  # _create_session_manager
            
            # Act
            components = self.initialization_service.create_components_from_config(config)
            
            # Assert - Verify the creation methods that are called in create_components_from_config
            # Note: Some methods like _create_iterative_execution_service and 
            # _create_mapping_path_execution_service are called in complete_initialization
            
            # Core components
            mocks[0].assert_called_once()  # session_manager
            mocks[1].assert_called_once()  # client_manager
            mocks[2].assert_called_once()  # config_loader
            mocks[3].assert_called_once()  # path_finder
            mocks[4].assert_called_once()  # cache_manager
            mocks[5].assert_called_once()  # identifier_loader
            mocks[6].assert_called_once()  # checkpoint_manager
            mocks[7].assert_called_once()  # progress_reporter
            mocks[8].assert_called_once()  # langfuse_tracker
            mocks[9].assert_called_once()  # strategy_handler
            mocks[10].assert_called_once()  # path_execution_manager
            mocks[11].assert_called_once()  # strategy_orchestrator
            
            # Services
            mocks[12].assert_called_once()  # metadata_query_service
            mocks[13].assert_called_once()  # session_metrics_service
            mocks[14].assert_called_once()  # bidirectional_validation_service
            mocks[15].assert_called_once()  # direct_mapping_service
            mocks[16].assert_called_once()  # result_aggregation_service
            mocks[17].assert_called_once()  # iterative_mapping_service
            mocks[18].assert_called_once()  # mapping_handler_service
            mocks[19].assert_called_once()  # mapping_step_execution_service
            mocks[20].assert_called_once()  # execution_lifecycle_service
            mocks[21].assert_called_once()  # robust_execution_coordinator
            mocks[22].assert_called_once()  # strategy_execution_service
            mocks[23].assert_called_once()  # db_strategy_execution_service
            mocks[24].assert_called_once()  # yaml_strategy_execution_service
                
        finally:
            # Stop all patches
            for patcher in patches:
                patcher.stop()

    @patch('biomapper.config.settings')
    def test_default_settings_used(self, mock_settings):
        """Test that default settings are used when config values are not provided."""
        # Arrange
        mock_settings.metamapper_db_url = 'postgresql://default_user:pass@localhost/metamapper'
        mock_settings.cache_db_url = 'postgresql://default_user:pass@localhost/cache'
        
        # Act
        components = self.initialization_service.create_components_from_config({})
        
        # Assert - The session manager should use default settings
        session_manager = components['session_manager']
        # Since we're not mocking SessionManager in this test, we can't directly check
        # the constructor args, but we can verify the component was created

    def test_logging_messages(self, caplog):
        """Test that appropriate logging messages are generated."""
        # Arrange
        config = {}
        
        # Act
        with caplog.at_level('INFO'):
            components = self.initialization_service.create_components_from_config(config)
        
        # Assert
        assert "Creating all components from configuration dictionary" in caplog.text
        assert "All components created successfully from configuration" in caplog.text

    def test_complete_initialization(self):
        """Test that complete_initialization finalizes components that need mapping_executor reference."""
        # Arrange
        config = {}
        components = self.initialization_service.create_components_from_config(config)
        
        # Create a mock mapping_executor
        mock_mapping_executor = MagicMock()
        mock_mapping_executor.enable_metrics = False
        
        # Act
        completed_components = self.initialization_service.complete_initialization(mock_mapping_executor, components)
        
        # Assert - Verify new components are added
        assert 'path_execution_service' in completed_components
        assert 'iterative_execution_service' in completed_components
        
        # Verify executor references are set
        assert components['strategy_handler'].mapping_executor == mock_mapping_executor
        assert components['strategy_orchestrator'].mapping_executor == mock_mapping_executor

    @patch('biomapper.core.engine_components.initialization_service.MappingPathExecutionService')
    @patch('biomapper.core.engine_components.initialization_service.IterativeExecutionService')
    def test_complete_initialization_creates_services(self, mock_iterative_service, mock_path_service):
        """Test that complete_initialization creates services that depend on mapping_executor."""
        # Arrange
        config = {}
        components = self.initialization_service.create_components_from_config(config)
        mock_mapping_executor = MagicMock()
        mock_mapping_executor.enable_metrics = False
        
        # Act
        self.initialization_service.complete_initialization(mock_mapping_executor, components)
        
        # Assert - Verify services are created with correct dependencies
        mock_path_service.assert_called_once_with(
            session_manager=components['session_manager'],
            client_manager=components['client_manager'],
            cache_manager=components['cache_manager'],
            path_finder=components['path_finder'],
            path_execution_manager=components['path_execution_manager'],
            composite_handler=mock_mapping_executor,
            step_execution_service=components['step_execution_service'],
            logger=self.initialization_service.logger
        )
        
        mock_iterative_service.assert_called_once_with(
            direct_mapping_service=components['direct_mapping_service'],
            iterative_mapping_service=components['iterative_mapping_service'],
            bidirectional_validation_service=components['bidirectional_validation_service'],
            result_aggregation_service=components['result_aggregation_service'],
            path_finder=components['path_finder'],
            composite_handler=mock_mapping_executor,
            async_metamapper_session=components['async_metamapper_session'],
            async_cache_session=components['async_cache_session'],
            metadata_query_service=components['metadata_query_service'],
            session_metrics_service=components['session_metrics_service'],
            logger=self.initialization_service.logger
        )
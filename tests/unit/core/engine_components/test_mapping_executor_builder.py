# tests/unit/core/engine_components/test_mapping_executor_builder.py

import pytest
from unittest.mock import Mock, patch, AsyncMock, call, ANY
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder


class TestMappingExecutorBuilder:
    """Test suite for MappingExecutorBuilder"""

    @pytest.fixture
    def builder(self):
        """Create a MappingExecutorBuilder instance for testing"""
        config = {"test_config": "value"}
        return MappingExecutorBuilder(config)

    @pytest.fixture
    def mock_components(self):
        """Create mock components returned by InitializationService"""
        return {
            'session_manager': Mock(),
            'metadata_query_service': Mock(),
            'execution_session_service': Mock(),
            'checkpoint_service': Mock(),
            'resource_disposal_service': Mock(),
            'iterative_execution_service': Mock(set_composite_handler=Mock()),
            'path_execution_service': Mock(set_composite_handler=Mock()),
            'db_strategy_execution_service': Mock(),
            'yaml_strategy_execution_service': Mock(),
            'robust_execution_coordinator': Mock(),
            'strategy_orchestrator': Mock(set_composite_handler=Mock())
        }

    @patch('biomapper.core.engine_components.mapping_executor_builder.MappingExecutor')
    @patch('biomapper.core.engine_components.mapping_executor_builder.StrategyCoordinatorService')
    @patch('biomapper.core.engine_components.mapping_executor_builder.MappingCoordinatorService')
    @patch('biomapper.core.engine_components.mapping_executor_builder.LifecycleCoordinator')
    def test_build_orchestration(
        self,
        mock_lifecycle_coordinator_class,
        mock_mapping_coordinator_class,
        mock_strategy_coordinator_class,
        mock_mapping_executor_class,
        builder,
        mock_components
    ):
        """Test that build method orchestrates component creation correctly"""
        # Arrange
        builder.initialization_service.create_components = Mock(return_value=mock_components)
        
        mock_lifecycle_coordinator = Mock()
        mock_mapping_coordinator = Mock()
        mock_strategy_coordinator = Mock()
        mock_executor = Mock()
        
        mock_lifecycle_coordinator_class.return_value = mock_lifecycle_coordinator
        mock_mapping_coordinator_class.return_value = mock_mapping_coordinator
        mock_strategy_coordinator_class.return_value = mock_strategy_coordinator
        mock_mapping_executor_class.return_value = mock_executor

        # Act
        result = builder.build()

        # Assert - verify InitializationService was called
        builder.initialization_service.create_components.assert_called_once_with(builder.config)

        # Assert - verify coordinators were instantiated correctly
        mock_lifecycle_coordinator_class.assert_called_once_with(
            execution_session_service=mock_components['execution_session_service'],
            checkpoint_service=mock_components['checkpoint_service'],
            resource_disposal_service=mock_components['resource_disposal_service']
        )

        mock_mapping_coordinator_class.assert_called_once_with(
            iterative_execution_service=mock_components['iterative_execution_service'],
            path_execution_service=mock_components['path_execution_service']
        )

        mock_strategy_coordinator_class.assert_called_once_with(
            db_strategy_execution_service=mock_components['db_strategy_execution_service'],
            yaml_strategy_execution_service=mock_components['yaml_strategy_execution_service'],
            robust_execution_coordinator=mock_components['robust_execution_coordinator']
        )

        # Assert - verify MappingExecutor was instantiated correctly
        mock_mapping_executor_class.assert_called_once_with(
            lifecycle_coordinator=mock_lifecycle_coordinator,
            mapping_coordinator=mock_mapping_coordinator,
            strategy_coordinator=mock_strategy_coordinator,
            session_manager=mock_components['session_manager'],
            metadata_query_service=mock_components['metadata_query_service']
        )

        # Assert - verify result
        assert result == mock_executor

    def test_post_build_reference_setting(self, builder, mock_components):
        """Test that _set_composite_handler_references is called correctly"""
        # Arrange
        builder.initialization_service.create_components = Mock(return_value=mock_components)
        mock_executor = Mock()
        
        # We need to spy on the _set_composite_handler_references method
        original_method = builder._set_composite_handler_references
        builder._set_composite_handler_references = Mock(wraps=original_method)

        # Mock the coordinator creation methods to avoid real instantiation
        builder._create_lifecycle_coordinator = Mock()
        builder._create_mapping_coordinator = Mock()
        builder._create_strategy_coordinator = Mock()

        with patch('biomapper.core.engine_components.mapping_executor_builder.MappingExecutor', return_value=mock_executor):
            # Act
            builder.build()

            # Assert - verify the method was called
            builder._set_composite_handler_references.assert_called_once_with(mock_executor, mock_components)

        # Also verify that set_composite_handler was called on the appropriate services
        mock_components['strategy_orchestrator'].set_composite_handler.assert_called_once_with(mock_executor)
        mock_components['iterative_execution_service'].set_composite_handler.assert_called_once_with(mock_executor)
        mock_components['path_execution_service'].set_composite_handler.assert_called_once_with(mock_executor)

    @pytest.mark.asyncio
    @patch('biomapper.core.engine_components.mapping_executor_builder.DatabaseSetupService')
    async def test_build_async(self, mock_db_setup_service_class, builder):
        """Test that build_async method correctly builds and initializes database"""
        # Arrange
        mock_executor = Mock()
        mock_executor.session_manager.async_metamapper_engine = Mock()
        mock_executor.session_manager.async_cache_engine = Mock()
        
        builder.build = Mock(return_value=mock_executor)
        
        mock_db_setup_service = AsyncMock()
        mock_db_setup_service_class.return_value = mock_db_setup_service

        # Act
        result = await builder.build_async()

        # Assert - verify build was called
        builder.build.assert_called_once()

        # Assert - verify database initialization
        mock_db_setup_service_class.assert_called_once()
        
        # Verify initialize_tables was called twice with correct arguments
        assert mock_db_setup_service.initialize_tables.call_count == 2
        
        # Check the calls were made with the correct engines and metadata
        calls = mock_db_setup_service.initialize_tables.call_args_list
        
        # First call should be for metamapper
        assert calls[0] == call(
            mock_executor.session_manager.async_metamapper_engine,
            ANY  # We use ANY because we can't easily mock MetamapperBase.metadata
        )
        
        # Second call should be for cache
        assert calls[1] == call(
            mock_executor.session_manager.async_cache_engine,
            ANY  # We use ANY because we can't easily mock CacheBase.metadata
        )

        # Assert - verify return value
        assert result == mock_executor

    def test_create_lifecycle_coordinator(self, builder, mock_components):
        """Test _create_lifecycle_coordinator method"""
        # Act
        with patch('biomapper.core.engine_components.mapping_executor_builder.LifecycleCoordinator') as mock_class:
            result = builder._create_lifecycle_coordinator(mock_components)

            # Assert
            mock_class.assert_called_once_with(
                execution_session_service=mock_components['execution_session_service'],
                checkpoint_service=mock_components['checkpoint_service'],
                resource_disposal_service=mock_components['resource_disposal_service']
            )
            assert result == mock_class.return_value

    def test_create_mapping_coordinator(self, builder, mock_components):
        """Test _create_mapping_coordinator method"""
        # Act
        with patch('biomapper.core.engine_components.mapping_executor_builder.MappingCoordinatorService') as mock_class:
            result = builder._create_mapping_coordinator(mock_components)

            # Assert
            mock_class.assert_called_once_with(
                iterative_execution_service=mock_components['iterative_execution_service'],
                path_execution_service=mock_components['path_execution_service']
            )
            assert result == mock_class.return_value

    def test_create_strategy_coordinator(self, builder, mock_components):
        """Test _create_strategy_coordinator method"""
        # Act
        with patch('biomapper.core.engine_components.mapping_executor_builder.StrategyCoordinatorService') as mock_class:
            result = builder._create_strategy_coordinator(mock_components)

            # Assert
            mock_class.assert_called_once_with(
                db_strategy_execution_service=mock_components['db_strategy_execution_service'],
                yaml_strategy_execution_service=mock_components['yaml_strategy_execution_service'],
                robust_execution_coordinator=mock_components['robust_execution_coordinator']
            )
            assert result == mock_class.return_value

    def test_initialization_with_empty_config(self):
        """Test that builder can be initialized with empty config"""
        # Act
        builder = MappingExecutorBuilder()

        # Assert
        assert builder.config == {}
        assert builder.initialization_service is not None

    def test_initialization_with_config(self):
        """Test that builder initializes with provided config"""
        # Arrange
        config = {"key1": "value1", "key2": "value2"}

        # Act
        builder = MappingExecutorBuilder(config)

        # Assert
        assert builder.config == config
        assert builder.initialization_service is not None
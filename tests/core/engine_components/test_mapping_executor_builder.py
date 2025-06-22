"""Tests for the MappingExecutorBuilder."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.core.mapping_executor import MappingExecutor


class TestMappingExecutorBuilder:
    """Test suite for MappingExecutorBuilder."""
    
    def test_builder_initialization(self):
        """Test that builder can be initialized with configuration parameters."""
        builder = MappingExecutorBuilder(
            metamapper_db_url="sqlite+aiosqlite:///:memory:",
            mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
            echo_sql=False,
            path_cache_size=100,
            path_cache_expiry_seconds=300,
            max_concurrent_batches=5,
            enable_metrics=True,
            checkpoint_enabled=False,
            checkpoint_dir=None,
            batch_size=100,
            max_retries=3,
            retry_delay=5,
        )
        
        assert builder.metamapper_db_url == "sqlite+aiosqlite:///:memory:"
        assert builder.mapping_cache_db_url == "sqlite+aiosqlite:///:memory:"
        assert builder.batch_size == 100
        assert builder.max_retries == 3
        
    @patch('biomapper.core.engine_components.mapping_executor_builder.InitializationService')
    @patch('biomapper.core.engine_components.mapping_executor_builder.StrategyCoordinatorService')
    @patch('biomapper.core.engine_components.mapping_executor_builder.MappingCoordinatorService')
    @patch('biomapper.core.engine_components.mapping_executor_builder.LifecycleManager')
    def test_build_creates_executor(
        self,
        mock_lifecycle_manager_class,
        mock_mapping_coordinator_class,
        mock_strategy_coordinator_class,
        mock_init_service_class
    ):
        """Test that build() method creates a MappingExecutor instance."""
        # Setup mocks
        mock_init_service = MagicMock()
        mock_init_service_class.return_value = mock_init_service
        
        # Mock the components returned by initialization service
        mock_components = {
            'result_aggregation_service': MagicMock(),
            'iterative_execution_service': MagicMock(),
            'db_strategy_execution_service': MagicMock(),
            'yaml_strategy_execution_service': MagicMock(),
            'robust_execution_coordinator': MagicMock(),
            'path_execution_service': MagicMock(),
            'session_manager': MagicMock(),
            'lifecycle_service': MagicMock(),
            'client_manager': MagicMock(),
            'cache_manager': MagicMock(),
            'path_finder': MagicMock(),
            'path_execution_manager': MagicMock(),
            'step_execution_service': MagicMock(),
            'metadata_query_service': MagicMock(),
            'identifier_loader': MagicMock(),
            'config_loader': MagicMock(),
            'async_metamapper_session': MagicMock(),
            'async_cache_session': MagicMock(),
        }
        
        mock_init_service.initialize_components.return_value = mock_components
        
        # Mock the coordinators
        mock_strategy_coordinator = MagicMock()
        mock_mapping_coordinator = MagicMock()
        mock_lifecycle_manager = MagicMock()
        
        mock_strategy_coordinator_class.return_value = mock_strategy_coordinator
        mock_mapping_coordinator_class.return_value = mock_mapping_coordinator
        mock_lifecycle_manager_class.return_value = mock_lifecycle_manager
        
        # Create builder and build
        builder = MappingExecutorBuilder()
        executor = builder.build()
        
        # Verify executor was created
        assert isinstance(executor, MappingExecutor)
        assert executor.strategy_coordinator == mock_strategy_coordinator
        assert executor.mapping_coordinator == mock_mapping_coordinator
        assert executor.lifecycle_manager == mock_lifecycle_manager
        
        # Verify initialization service was called
        mock_init_service.initialize_components.assert_called_once()
        
        # Verify coordinators were created with correct dependencies
        mock_strategy_coordinator_class.assert_called_once_with(
            db_strategy_execution_service=mock_components['db_strategy_execution_service'],
            yaml_strategy_execution_service=mock_components['yaml_strategy_execution_service'],
            robust_execution_coordinator=mock_components['robust_execution_coordinator'],
            logger=builder.logger
        )
        
        mock_mapping_coordinator_class.assert_called_once_with(
            iterative_execution_service=mock_components['iterative_execution_service'],
            path_execution_service=mock_components['path_execution_service'],
            logger=builder.logger
        )
        
    @pytest.mark.asyncio
    @patch('biomapper.core.engine_components.mapping_executor_builder.DatabaseSetupService')
    async def test_build_async_initializes_database(self, mock_db_setup_class):
        """Test that build_async() initializes database tables."""
        # Mock the database setup service
        mock_db_setup = AsyncMock()
        mock_db_setup_class.return_value = mock_db_setup
        
        # Create a builder
        builder = MappingExecutorBuilder(
            metamapper_db_url="sqlite+aiosqlite:///:memory:",
            mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
        )
        
        # Mock the build method
        mock_executor = MagicMock()
        mock_executor.session_manager = MagicMock()
        mock_executor.session_manager.async_metamapper_engine = MagicMock()
        
        with patch.object(builder, 'build', return_value=mock_executor):
            # Call build_async
            executor = await builder.build_async()
            
            # Verify executor was returned
            assert executor == mock_executor
            
            # Verify database setup was called
            mock_db_setup.initialize_tables.assert_called_once()
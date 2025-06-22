"""
Unit tests for the MappingExecutor facade.

These tests verify that the MappingExecutor correctly delegates calls to its
underlying coordinators and services. No business logic is tested here - only
the proper wiring and delegation of method calls.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, create_autospec, patch
from typing import Dict, Any, List, Optional

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.models.result_bundle import MappingResultBundle


@pytest.fixture
def mock_initialization_service():
    """Mock InitializationService that returns mocked components."""
    mock_service = Mock()
    mock_service.initialize_components = Mock()
    return mock_service


@pytest.fixture
def mock_lifecycle_coordinator():
    """Mock LifecycleCoordinator with all required methods."""
    mock = Mock()
    mock.async_dispose = AsyncMock()
    mock.add_progress_callback = Mock()
    mock.report_progress = AsyncMock()
    mock.report_batch_progress = AsyncMock()
    mock.save_checkpoint = AsyncMock()
    mock.load_checkpoint = AsyncMock(return_value=None)
    mock.save_batch_checkpoint = AsyncMock()
    mock.checkpoint_dir = "/tmp/checkpoints"
    mock.checkpoint_enabled = False
    return mock


@pytest.fixture
def mock_mapping_coordinator():
    """Mock MappingCoordinatorService with all required methods."""
    mock = Mock()
    mock.execute_mapping = AsyncMock(return_value={"results": {}, "metadata": {}})
    mock.execute_path = AsyncMock(return_value={})
    return mock


@pytest.fixture
def mock_strategy_coordinator():
    """Mock StrategyCoordinatorService with all required methods."""
    mock = Mock()
    mock.execute_strategy = AsyncMock(return_value=MappingResultBundle())
    mock.execute_yaml_strategy = AsyncMock(return_value={"results": {}, "metadata": {}})
    mock.execute_robust_yaml_strategy = AsyncMock(return_value={"results": {}, "metadata": {}})
    return mock


@pytest.fixture
def mock_metadata_query_service():
    """Mock MetadataQueryService with all required methods."""
    mock = Mock()
    mock.get_endpoint = AsyncMock(return_value=None)
    mock.get_strategy = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_identifier_loader():
    """Mock IdentifierLoader with all required methods."""
    mock = Mock()
    mock.get_ontology_column = AsyncMock(return_value="column_name")
    mock.load_endpoint_identifiers = AsyncMock(return_value=["id1", "id2"])
    return mock


@pytest.fixture
def mock_client_manager():
    """Mock ClientManager with all required methods."""
    mock = Mock()
    mock.get_client_instance = Mock(return_value=Mock())
    return mock


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for database sessions."""
    mock = Mock()
    mock.async_metamapper_session = Mock()
    mock.async_cache_session = Mock()
    return mock


@pytest.fixture
def mock_components():
    """Create a dictionary of all mocked components."""
    return {
        # Core services
        "lifecycle_service": Mock(),
        "lifecycle_manager": Mock(
            async_dispose=AsyncMock(),
            add_progress_callback=Mock(),
            report_progress=AsyncMock(),
            report_batch_progress=AsyncMock(),
            save_checkpoint=AsyncMock(),
            load_checkpoint=AsyncMock(return_value=None),
            save_batch_checkpoint=AsyncMock(),
            checkpoint_dir="/tmp/checkpoints",
            checkpoint_enabled=False
        ),
        "mapping_coordinator": Mock(
            execute_mapping=AsyncMock(return_value={"results": {}, "metadata": {}}),
            execute_path=AsyncMock(return_value={})
        ),
        "strategy_coordinator": Mock(
            execute_strategy=AsyncMock(return_value=MappingResultBundle(
                strategy_name="test_strategy",
                initial_identifiers=[]
            )),
            execute_yaml_strategy=AsyncMock(return_value={"results": {}, "metadata": {}}),
            execute_robust_yaml_strategy=AsyncMock(return_value={"results": {}, "metadata": {}})
        ),
        
        # Supporting services
        "metadata_query_service": Mock(
            get_endpoint=AsyncMock(return_value=None),
            get_strategy=AsyncMock(return_value=None)
        ),
        "identifier_loader": Mock(
            get_ontology_column=AsyncMock(return_value="column_name"),
            load_endpoint_identifiers=AsyncMock(return_value=["id1", "id2"])
        ),
        "client_manager": Mock(get_client_instance=Mock(return_value=Mock())),
        "session_manager": Mock(),
        
        # Execution services (needed for initialization)
        "direct_mapping_service": Mock(),
        "iterative_mapping_service": Mock(),
        "bidirectional_validation_service": Mock(),
        "path_finder": Mock(),
        "_composite_handler": Mock(),
        "async_metamapper_session": Mock(),
        "async_cache_session": Mock(),
        "strategy_execution_service": Mock(),
        "strategy_orchestrator": Mock(),
        "robust_execution_coordinator": Mock(),
        "path_execution_service": Mock(set_executor=Mock()),
        "session_metrics_service": Mock(),
        
        # Other required attributes
        "batch_size": 100,
        "max_retries": 3,
        "retry_delay": 5,
        "checkpoint_enabled": False,
    }


@pytest.mark.asyncio
class TestMappingExecutorDelegation:
    """Test that MappingExecutor correctly delegates to underlying services."""
    
    @pytest.fixture
    def executor(self, mock_components, monkeypatch):
        """Create a MappingExecutor with mocked components."""
        # Mock the InitializationService to return our mock components
        with patch('biomapper.core.mapping_executor.InitializationService') as mock_init_service_class:
            mock_init_service = mock_init_service_class.return_value
            mock_init_service.initialize_components.return_value = mock_components
            
            # Create the executor
            executor = MappingExecutor()
            
            # Manually assign coordinators since they're created after initialization
            executor.lifecycle_manager = mock_components["lifecycle_manager"]
            executor.mapping_coordinator = mock_components["mapping_coordinator"]
            executor.strategy_coordinator = mock_components["strategy_coordinator"]
            executor.metadata_query_service = mock_components["metadata_query_service"]
            executor.identifier_loader = mock_components["identifier_loader"]
            executor.client_manager = mock_components["client_manager"]
            executor.async_metamapper_session = mock_components["async_metamapper_session"]
            
            return executor
    
    async def test_execute_mapping_delegates_to_mapping_coordinator(self, executor):
        """Test that execute_mapping delegates to MappingCoordinatorService."""
        # Arrange
        source_name = "test_source"
        target_name = "test_target"
        input_ids = ["id1", "id2"]
        source_prop = "test_prop"
        target_prop = "target_prop"
        
        # Act
        result = await executor.execute_mapping(
            source_endpoint_name=source_name,
            target_endpoint_name=target_name,
            input_identifiers=input_ids,
            source_property_name=source_prop,
            target_property_name=target_prop,
            use_cache=True,
            max_cache_age_days=7,
            mapping_direction="forward",
            try_reverse_mapping=True,
            validate_bidirectional=False,
            batch_size=100,
            max_concurrent_batches=5,
            max_hop_count=5,
            min_confidence=0.5,
            enable_metrics=True
        )
        
        # Assert
        executor.mapping_coordinator.execute_mapping.assert_called_once_with(
            source_endpoint_name=source_name,
            target_endpoint_name=target_name,
            input_identifiers=input_ids,
            input_data=None,
            source_property_name=source_prop,
            target_property_name=target_prop,
            source_ontology_type=None,
            target_ontology_type=None,
            use_cache=True,
            max_cache_age_days=7,
            mapping_direction="forward",
            try_reverse_mapping=True,
            validate_bidirectional=False,
            progress_callback=None,
            batch_size=100,
            max_concurrent_batches=5,
            max_hop_count=5,
            min_confidence=0.5,
            enable_metrics=True
        )
        assert result == {"results": {}, "metadata": {}}
    
    async def test_execute_path_delegates_to_mapping_coordinator(self, executor):
        """Test that _execute_path delegates to MappingCoordinatorService."""
        # Arrange
        mock_session = Mock()
        mock_path = Mock()
        input_ids = ["id1", "id2", "id3"]
        source_ontology = "UniProt"
        target_ontology = "Gene"
        mapping_session_id = 123
        
        # Act
        result = await executor._execute_path(
            session=mock_session,
            path=mock_path,
            input_identifiers=input_ids,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=mapping_session_id,
            batch_size=250,
            max_hop_count=10,
            filter_confidence=0.8,
            max_concurrent_batches=3
        )
        
        # Assert
        executor.mapping_coordinator.execute_path.assert_called_once_with(
            session=mock_session,
            path=mock_path,
            input_identifiers=input_ids,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=mapping_session_id,
            batch_size=250,
            max_hop_count=10,
            filter_confidence=0.8,
            max_concurrent_batches=3
        )
        assert result == {}
    
    async def test_execute_strategy_delegates_to_strategy_coordinator(self, executor):
        """Test that execute_strategy delegates to StrategyCoordinatorService."""
        # Arrange
        strategy_name = "test_strategy"
        initial_ids = ["id1", "id2"]
        source_ontology = "UniProt"
        target_ontology = "Gene"
        entity_type = "protein"
        
        # Act
        result = await executor.execute_strategy(
            strategy_name=strategy_name,
            initial_identifiers=initial_ids,
            source_ontology_type=source_ontology,
            target_ontology_type=target_ontology,
            entity_type=entity_type
        )
        
        # Assert
        executor.strategy_coordinator.execute_strategy.assert_called_once_with(
            strategy_name=strategy_name,
            initial_identifiers=initial_ids,
            source_ontology_type=source_ontology,
            target_ontology_type=target_ontology,
            entity_type=entity_type
        )
        assert isinstance(result, MappingResultBundle)
    
    async def test_execute_yaml_strategy_delegates_to_strategy_coordinator(self, executor):
        """Test that execute_yaml_strategy delegates to StrategyCoordinatorService."""
        # Arrange
        strategy_name = "yaml_strategy"
        source_endpoint = "source_ep"
        target_endpoint = "target_ep"
        input_ids = ["id1", "id2", "id3"]
        initial_context = {"key": "value"}
        
        # Act
        result = await executor.execute_yaml_strategy(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint,
            target_endpoint_name=target_endpoint,
            input_identifiers=input_ids,
            source_ontology_type="UniProt",
            target_ontology_type="Gene",
            use_cache=False,
            max_cache_age_days=30,
            progress_callback=None,
            batch_size=100,
            min_confidence=0.7,
            initial_context=initial_context
        )
        
        # Assert
        executor.strategy_coordinator.execute_yaml_strategy.assert_called_once_with(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint,
            target_endpoint_name=target_endpoint,
            input_identifiers=input_ids,
            source_ontology_type="UniProt",
            target_ontology_type="Gene",
            use_cache=False,
            max_cache_age_days=30,
            progress_callback=None,
            batch_size=100,
            min_confidence=0.7,
            initial_context=initial_context
        )
        assert result == {"results": {}, "metadata": {}}
    
    async def test_execute_yaml_strategy_robust_delegates_to_strategy_coordinator(self, executor):
        """Test that execute_yaml_strategy_robust delegates to StrategyCoordinatorService."""
        # Arrange
        strategy_name = "robust_strategy"
        input_ids = ["id1", "id2"]
        execution_id = "exec_123"
        
        # Act
        result = await executor.execute_yaml_strategy_robust(
            strategy_name=strategy_name,
            input_identifiers=input_ids,
            source_endpoint_name="source",
            target_endpoint_name="target",
            execution_id=execution_id,
            resume_from_checkpoint=True,
            custom_param="value"
        )
        
        # Assert
        executor.strategy_coordinator.execute_robust_yaml_strategy.assert_called_once_with(
            strategy_name=strategy_name,
            input_identifiers=input_ids,
            source_endpoint_name="source",
            target_endpoint_name="target",
            execution_id=execution_id,
            resume_from_checkpoint=True,
            custom_param="value"
        )
        assert result == {"results": {}, "metadata": {}}
    
    async def test_async_dispose_delegates_to_lifecycle_manager(self, executor):
        """Test that async_dispose delegates to LifecycleCoordinator."""
        # Act
        await executor.async_dispose()
        
        # Assert
        executor.lifecycle_manager.async_dispose.assert_called_once()
    
    async def test_save_checkpoint_delegates_to_lifecycle_manager(self, executor):
        """Test that save_checkpoint delegates to LifecycleCoordinator."""
        # Arrange
        execution_id = "exec_456"
        checkpoint_data = {"state": "in_progress", "processed": 100}
        
        # Act
        await executor.save_checkpoint(execution_id, checkpoint_data)
        
        # Assert
        executor.lifecycle_manager.save_checkpoint.assert_called_once_with(
            execution_id, checkpoint_data
        )
    
    async def test_load_checkpoint_delegates_to_lifecycle_manager(self, executor):
        """Test that load_checkpoint delegates to LifecycleCoordinator."""
        # Arrange
        execution_id = "exec_789"
        
        # Act
        result = await executor.load_checkpoint(execution_id)
        
        # Assert
        executor.lifecycle_manager.load_checkpoint.assert_called_once_with(execution_id)
        assert result is None  # As per mock return value
    
    def test_add_progress_callback_delegates_to_lifecycle_manager(self, executor):
        """Test that add_progress_callback delegates to LifecycleCoordinator."""
        # Arrange
        callback = Mock()
        
        # Act
        executor.add_progress_callback(callback)
        
        # Assert
        executor.lifecycle_manager.add_progress_callback.assert_called_once_with(callback)
    
    async def test_get_endpoint_by_name_delegates_to_metadata_query_service(self, executor):
        """Test that _get_endpoint_by_name delegates to MetadataQueryService."""
        # Arrange
        mock_session = Mock()
        endpoint_name = "test_endpoint"
        
        # Act
        result = await executor._get_endpoint_by_name(mock_session, endpoint_name)
        
        # Assert
        executor.metadata_query_service.get_endpoint.assert_called_once_with(
            mock_session, endpoint_name
        )
        assert result is None  # As per mock return value
    
    async def test_get_ontology_column_delegates_to_identifier_loader(self, executor):
        """Test that get_ontology_column delegates to IdentifierLoader."""
        # Arrange
        endpoint_name = "test_endpoint"
        ontology_type = "UniProt"
        
        # Act
        result = await executor.get_ontology_column(endpoint_name, ontology_type)
        
        # Assert
        executor.identifier_loader.get_ontology_column.assert_called_once_with(
            endpoint_name, ontology_type
        )
        assert result == "column_name"
    
    async def test_load_endpoint_identifiers_delegates_to_identifier_loader(self, executor):
        """Test that load_endpoint_identifiers delegates to IdentifierLoader."""
        # Arrange
        endpoint_name = "test_endpoint"
        ontology_type = "Gene"
        
        # Act
        result = await executor.load_endpoint_identifiers(
            endpoint_name=endpoint_name,
            ontology_type=ontology_type,
            return_dataframe=False
        )
        
        # Assert
        executor.identifier_loader.load_endpoint_identifiers.assert_called_once_with(
            endpoint_name=endpoint_name,
            ontology_type=ontology_type,
            return_dataframe=False
        )
        assert result == ["id1", "id2"]
    
    def test_load_client_delegates_to_client_manager(self, executor):
        """Test that _load_client delegates to ClientManager."""
        # Arrange
        client_path = "biomapper.clients.test_client"
        kwargs = {"param1": "value1", "param2": "value2"}
        
        # Act
        result = executor._load_client(client_path, **kwargs)
        
        # Assert
        executor.client_manager.get_client_instance.assert_called_once_with(
            client_path, **kwargs
        )
        assert result is not None
    
    async def test_get_strategy_delegates_to_metadata_query_service(self, executor):
        """Test that get_strategy delegates to MetadataQueryService."""
        # Arrange
        strategy_name = "test_strategy"
        
        # Mock the context manager for async_metamapper_session
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        executor.async_metamapper_session.return_value = mock_context
        
        # Act
        result = await executor.get_strategy(strategy_name)
        
        # Assert
        executor.metadata_query_service.get_strategy.assert_called_once_with(
            mock_session, strategy_name
        )
        assert result is None  # As per mock return value
    
    async def test_report_progress_delegates_to_lifecycle_manager(self, executor):
        """Test that _report_progress delegates to LifecycleCoordinator."""
        # Arrange
        progress_data = {
            "type": "batch_progress",
            "processed": 50,
            "total": 100
        }
        
        # Act
        await executor._report_progress(progress_data)
        
        # Assert
        executor.lifecycle_manager.report_progress.assert_called_once_with(progress_data)
    
    def test_checkpoint_dir_property_delegates_to_lifecycle_manager(self, executor):
        """Test that checkpoint_dir property delegates to LifecycleCoordinator."""
        # Test getter
        result = executor.checkpoint_dir
        assert result == "/tmp/checkpoints"
        
        # Test setter
        new_dir = "/new/checkpoint/dir"
        executor.checkpoint_dir = new_dir
        assert executor.lifecycle_manager.checkpoint_dir == new_dir
        assert executor.checkpoint_enabled == executor.lifecycle_manager.checkpoint_enabled


@pytest.mark.asyncio
class TestMappingExecutorInitialization:
    """Test MappingExecutor initialization and factory methods."""
    
    async def test_create_factory_method_delegates_to_initializer(self):
        """Test that the create factory method uses MappingExecutorInitializer."""
        # Arrange
        with patch('biomapper.core.mapping_executor.MappingExecutorInitializer') as mock_initializer_class:
            mock_initializer = mock_initializer_class.return_value
            mock_executor = Mock()
            mock_initializer.create_executor = AsyncMock(return_value=mock_executor)
            
            # Act
            result = await MappingExecutor.create(
                metamapper_db_url="sqlite:///:memory:",
                mapping_cache_db_url="sqlite:///:memory:",
                echo_sql=True,
                path_cache_size=200,
                path_cache_expiry_seconds=600,
                max_concurrent_batches=10,
                enable_metrics=False,
                checkpoint_enabled=True,
                checkpoint_dir="/checkpoints",
                batch_size=50,
                max_retries=5,
                retry_delay=10
            )
            
            # Assert
            mock_initializer_class.assert_called_once_with(
                metamapper_db_url="sqlite:///:memory:",
                mapping_cache_db_url="sqlite:///:memory:",
                echo_sql=True,
                path_cache_size=200,
                path_cache_expiry_seconds=600,
                max_concurrent_batches=10,
                enable_metrics=False,
                checkpoint_enabled=True,
                checkpoint_dir="/checkpoints",
                batch_size=50,
                max_retries=5,
                retry_delay=10
            )
            mock_initializer.create_executor.assert_called_once()
            assert result == mock_executor


@pytest.mark.asyncio
class TestMappingExecutorComplexMethods:
    """Test more complex methods that perform additional logic beyond simple delegation."""
    
    @pytest.fixture
    def executor(self, mock_components, monkeypatch):
        """Create a MappingExecutor with mocked components."""
        with patch('biomapper.core.mapping_executor.InitializationService') as mock_init_service_class:
            mock_init_service = mock_init_service_class.return_value
            mock_init_service.initialize_components.return_value = mock_components
            
            executor = MappingExecutor()
            
            # Manually assign coordinators
            executor.lifecycle_manager = mock_components["lifecycle_manager"]
            executor.mapping_coordinator = mock_components["mapping_coordinator"]
            executor.strategy_coordinator = mock_components["strategy_coordinator"]
            executor.metadata_query_service = mock_components["metadata_query_service"]
            executor.identifier_loader = mock_components["identifier_loader"]
            executor.client_manager = mock_components["client_manager"]
            executor.async_metamapper_session = mock_components["async_metamapper_session"]
            executor.batch_size = mock_components["batch_size"]
            executor.max_retries = mock_components["max_retries"]
            executor.retry_delay = mock_components["retry_delay"]
            executor.checkpoint_enabled = mock_components["checkpoint_enabled"]
            
            return executor
    
    async def test_execute_with_retry_delegates_and_handles_retries(self, executor):
        """Test that execute_with_retry properly handles retries and delegates to lifecycle manager."""
        # Arrange
        operation = AsyncMock(side_effect=[Exception("First failure"), Exception("Second failure"), "Success"])
        operation_args = {"arg1": "value1", "arg2": "value2"}
        operation_name = "test_operation"
        
        # Act
        result = await executor.execute_with_retry(
            operation=operation,
            operation_args=operation_args,
            operation_name=operation_name,
            retry_exceptions=(Exception,)
        )
        
        # Assert
        assert result == "Success"
        assert operation.call_count == 3
        # Verify progress reporting
        assert executor.lifecycle_manager.report_progress.call_count >= 3
    
    async def test_process_in_batches_delegates_batch_operations(self, executor):
        """Test that process_in_batches correctly delegates batch processing and checkpointing."""
        # Arrange
        items = list(range(250))  # 250 items with batch_size=100 means 3 batches
        processor = AsyncMock(side_effect=[
            list(range(0, 100)),    # First batch result
            list(range(100, 200)),  # Second batch result
            list(range(200, 250))   # Third batch result
        ])
        processor_name = "test_processor"
        checkpoint_key = "results"
        execution_id = "exec_123"
        
        # Act
        result = await executor.process_in_batches(
            items=items,
            processor=processor,
            processor_name=processor_name,
            checkpoint_key=checkpoint_key,
            execution_id=execution_id,
            checkpoint_state=None
        )
        
        # Assert
        assert len(result) == 250
        assert processor.call_count == 3
        # Verify batch progress reporting
        assert executor.lifecycle_manager.report_batch_progress.call_count == 6  # start + end for each batch
# tests/unit/core/test_mapping_executor.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from biomapper.core.mapping_executor import MappingExecutor


class TestMappingExecutor:
    """Test suite for MappingExecutor facade - verifying delegation pattern"""

    @pytest.fixture
    def mock_lifecycle_coordinator(self):
        """Create a mock LifecycleCoordinator"""
        mock = Mock()
        mock.dispose_resources = AsyncMock()
        mock.save_checkpoint = AsyncMock()
        mock.load_checkpoint = AsyncMock(return_value={"test": "checkpoint"})
        mock.start_session = AsyncMock(return_value=123)
        mock.end_session = AsyncMock()
        return mock

    @pytest.fixture
    def mock_mapping_coordinator(self):
        """Create a mock MappingCoordinatorService"""
        mock = Mock()
        mock.execute_mapping = AsyncMock(return_value={"mapping": "result"})
        mock.execute_path = AsyncMock(return_value={"path": {"result": "data"}})
        return mock

    @pytest.fixture
    def mock_strategy_coordinator(self):
        """Create a mock StrategyCoordinatorService"""
        mock = Mock()
        mock.execute_strategy = AsyncMock(return_value=Mock(spec=['results']))
        mock.execute_yaml_strategy = AsyncMock(return_value=Mock(spec=['results']))
        mock.execute_robust_yaml_strategy = AsyncMock(return_value={"robust": "result"})
        return mock

    @pytest.fixture
    def mock_session_manager(self):
        """Create a mock SessionManager"""
        mock = Mock()
        mock.get_async_metamapper_session = Mock()
        mock.get_async_cache_session = Mock(return_value=Mock())
        return mock

    @pytest.fixture
    def mock_metadata_query_service(self):
        """Create a mock MetadataQueryService"""
        mock = Mock()
        mock.get_strategy = AsyncMock(return_value=Mock(spec=['name']))
        return mock

    @pytest.fixture
    def executor(
        self,
        mock_lifecycle_coordinator,
        mock_mapping_coordinator,
        mock_strategy_coordinator,
        mock_session_manager,
        mock_metadata_query_service
    ):
        """Create a MappingExecutor instance with all mocked dependencies"""
        return MappingExecutor(
            lifecycle_coordinator=mock_lifecycle_coordinator,
            mapping_coordinator=mock_mapping_coordinator,
            strategy_coordinator=mock_strategy_coordinator,
            session_manager=mock_session_manager,
            metadata_query_service=mock_metadata_query_service
        )

    @pytest.mark.asyncio
    async def test_execute_mapping_delegates_correctly(self, executor, mock_mapping_coordinator):
        """Test that execute_mapping delegates to MappingCoordinatorService"""
        # Arrange
        source_name = "test_source"
        target_name = "test_target"
        test_kwargs = {"option1": "value1", "option2": "value2"}

        # Act
        result = await executor.execute_mapping(
            source_endpoint_name=source_name,
            target_endpoint_name=target_name,
            **test_kwargs
        )

        # Assert
        mock_mapping_coordinator.execute_mapping.assert_called_once_with(
            source_endpoint_name=source_name,
            target_endpoint_name=target_name,
            **test_kwargs
        )
        assert result == {"mapping": "result"}

    @pytest.mark.asyncio
    async def test_execute_path_delegates_correctly(self, executor, mock_mapping_coordinator):
        """Test that _execute_path delegates to MappingCoordinatorService"""
        # Arrange
        test_path = Mock()
        test_kwargs = {"batch_size": 100, "max_retries": 3}

        # Act
        result = await executor._execute_path(
            path=test_path,
            **test_kwargs
        )

        # Assert
        mock_mapping_coordinator.execute_path.assert_called_once_with(
            path=test_path,
            **test_kwargs
        )
        assert result == {"path": {"result": "data"}}

    @pytest.mark.asyncio
    async def test_execute_strategy_delegates_correctly(self, executor, mock_strategy_coordinator):
        """Test that execute_strategy delegates to StrategyCoordinatorService"""
        # Arrange
        strategy_name = "test_strategy"
        test_kwargs = {"param1": "value1"}

        # Act
        result = await executor.execute_strategy(
            strategy_name=strategy_name,
            **test_kwargs
        )

        # Assert
        mock_strategy_coordinator.execute_strategy.assert_called_once_with(
            strategy_name=strategy_name,
            **test_kwargs
        )
        assert hasattr(result, 'results')

    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_delegates_correctly(self, executor, mock_strategy_coordinator):
        """Test that execute_yaml_strategy delegates to StrategyCoordinatorService"""
        # Arrange
        yaml_path = "/path/to/strategy.yaml"
        test_kwargs = {"input_data": {"key": "value"}}

        # Act
        result = await executor.execute_yaml_strategy(
            yaml_file_path=yaml_path,
            **test_kwargs
        )

        # Assert
        mock_strategy_coordinator.execute_yaml_strategy.assert_called_once_with(
            yaml_file_path=yaml_path,
            **test_kwargs
        )
        assert hasattr(result, 'results')

    @pytest.mark.asyncio
    async def test_execute_robust_yaml_strategy_delegates_correctly(self, executor, mock_strategy_coordinator):
        """Test that execute_robust_yaml_strategy delegates to StrategyCoordinatorService"""
        # Arrange
        yaml_path = "/path/to/robust_strategy.yaml"
        test_kwargs = {"retry_config": {"max_attempts": 5}}

        # Act
        result = await executor.execute_robust_yaml_strategy(
            yaml_file_path=yaml_path,
            **test_kwargs
        )

        # Assert
        mock_strategy_coordinator.execute_robust_yaml_strategy.assert_called_once_with(
            yaml_file_path=yaml_path,
            **test_kwargs
        )
        assert result == {"robust": "result"}

    @pytest.mark.asyncio
    async def test_get_strategy_delegates_correctly(self, executor, mock_metadata_query_service, mock_session_manager):
        """Test that get_strategy delegates to MetadataQueryService"""
        # Arrange
        strategy_name = "test_strategy_name"
        mock_session = AsyncMock()
        mock_session_manager.get_async_metamapper_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_async_metamapper_session.return_value.__aexit__ = AsyncMock()

        # Act
        result = await executor.get_strategy(strategy_name)

        # Assert
        mock_metadata_query_service.get_strategy.assert_called_once_with(
            mock_session,
            strategy_name
        )
        assert hasattr(result, 'name')

    def test_get_cache_session_delegates_correctly(self, executor, mock_session_manager):
        """Test that get_cache_session delegates to SessionManager"""
        # Act
        result = executor.get_cache_session()

        # Assert
        mock_session_manager.get_async_cache_session.assert_called_once_with()
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_dispose_delegates_correctly(self, executor, mock_lifecycle_coordinator):
        """Test that async_dispose delegates to LifecycleCoordinator"""
        # Act
        await executor.async_dispose()

        # Assert
        mock_lifecycle_coordinator.dispose_resources.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_save_checkpoint_delegates_correctly(self, executor, mock_lifecycle_coordinator):
        """Test that save_checkpoint delegates to LifecycleCoordinator"""
        # Arrange
        execution_id = "exec_123"
        checkpoint_data = {"state": "in_progress", "step": 5}

        # Act
        await executor.save_checkpoint(execution_id, checkpoint_data)

        # Assert
        mock_lifecycle_coordinator.save_checkpoint.assert_called_once_with(
            execution_id,
            checkpoint_data
        )

    @pytest.mark.asyncio
    async def test_load_checkpoint_delegates_correctly(self, executor, mock_lifecycle_coordinator):
        """Test that load_checkpoint delegates to LifecycleCoordinator"""
        # Arrange
        execution_id = "exec_123"

        # Act
        result = await executor.load_checkpoint(execution_id)

        # Assert
        mock_lifecycle_coordinator.load_checkpoint.assert_called_once_with(execution_id)
        assert result == {"test": "checkpoint"}

    @pytest.mark.asyncio
    async def test_start_session_delegates_correctly(self, executor, mock_lifecycle_coordinator):
        """Test that start_session delegates to LifecycleCoordinator"""
        # Arrange
        test_args = ("arg1", "arg2")
        test_kwargs = {"source": "test_source", "target": "test_target"}

        # Act
        result = await executor.start_session(*test_args, **test_kwargs)

        # Assert
        mock_lifecycle_coordinator.start_session.assert_called_once_with(
            *test_args,
            **test_kwargs
        )
        assert result == 123

    @pytest.mark.asyncio
    async def test_end_session_delegates_correctly(self, executor, mock_lifecycle_coordinator):
        """Test that end_session delegates to LifecycleCoordinator"""
        # Arrange
        test_args = (123,)
        test_kwargs = {"status": "completed", "results": {"count": 100}}

        # Act
        await executor.end_session(*test_args, **test_kwargs)

        # Assert
        mock_lifecycle_coordinator.end_session.assert_called_once_with(
            *test_args,
            **test_kwargs
        )
"""Tests for MappingExecutor strategy execution methods."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.db.models import MappingStrategy


@pytest.fixture
async def mapping_executor():
    """Fixture for a properly initialized MappingExecutor with mock sessions."""
    # Create mock coordinators and services
    mock_lifecycle_coordinator = MagicMock(spec=LifecycleCoordinator)
    mock_mapping_coordinator = MagicMock(spec=MappingCoordinatorService)
    mock_strategy_coordinator = MagicMock(spec=StrategyCoordinatorService)
    mock_session_manager = MagicMock(spec=SessionManager)
    mock_metadata_query_service = MagicMock(spec=MetadataQueryService)
    
    # Add required attributes for the tests
    mock_strategy_coordinator.execute_strategy = AsyncMock()
    mock_strategy_coordinator.execute_yaml_strategy = AsyncMock()
    mock_strategy_coordinator.execute_robust_yaml_strategy = AsyncMock()
    mock_metadata_query_service.get_strategy = AsyncMock()
    mock_session_manager.get_async_metamapper_session = MagicMock()
    
    # Create the executor with mocked dependencies
    executor = MappingExecutor(
        lifecycle_coordinator=mock_lifecycle_coordinator,
        mapping_coordinator=mock_mapping_coordinator,
        strategy_coordinator=mock_strategy_coordinator,
        session_manager=mock_session_manager,
        metadata_query_service=mock_metadata_query_service
    )
    
    yield executor


@pytest.mark.asyncio
async def test_execute_strategy(mapping_executor):
    """Test execute_strategy delegates to strategy coordinator."""
    strategy_name = "test_strategy"
    identifiers = ["id1", "id2"]
    parameters = {"param": "value"}
    
    mock_result = MagicMock(spec=MappingResultBundle)
    mapping_executor.strategy_coordinator.execute_strategy.return_value = mock_result
    
    result = await mapping_executor.execute_strategy(strategy_name, identifiers, parameters)
    
    assert result == mock_result
    mapping_executor.strategy_coordinator.execute_strategy.assert_called_once_with(
        strategy_name, identifiers, parameters
    )


@pytest.mark.asyncio
async def test_execute_yaml_strategy(mapping_executor):
    """Test execute_yaml_strategy delegates to strategy coordinator."""
    yaml_content = """
    name: test_strategy
    steps:
      - action: map
    """
    identifiers = ["id1", "id2"]
    parameters = {"param": "value"}
    
    mock_result = MagicMock(spec=MappingResultBundle)
    mapping_executor.strategy_coordinator.execute_yaml_strategy.return_value = mock_result
    
    result = await mapping_executor.execute_yaml_strategy(yaml_content, identifiers, parameters)
    
    assert result == mock_result
    mapping_executor.strategy_coordinator.execute_yaml_strategy.assert_called_once_with(
        yaml_content, identifiers, parameters
    )


@pytest.mark.asyncio
async def test_execute_robust_yaml_strategy(mapping_executor):
    """Test execute_robust_yaml_strategy delegates to strategy coordinator."""
    yaml_content = """
    name: test_strategy
    steps:
      - action: map
    """
    identifiers = ["id1", "id2"]
    parameters = {"param": "value"}
    
    mock_result = {
        "status": "success",
        "results": {}
    }
    mapping_executor.strategy_coordinator.execute_robust_yaml_strategy.return_value = mock_result
    
    result = await mapping_executor.execute_robust_yaml_strategy(yaml_content, identifiers, parameters)
    
    assert result == mock_result
    mapping_executor.strategy_coordinator.execute_robust_yaml_strategy.assert_called_once_with(
        yaml_content, identifiers, parameters
    )


@pytest.mark.asyncio
async def test_get_strategy(mapping_executor):
    """Test get_strategy retrieves strategy via metadata query service."""
    strategy_name = "test_strategy"
    
    # Create mock strategy
    mock_strategy = MagicMock(spec=MappingStrategy)
    mock_strategy.name = strategy_name
    
    # Create mock session context
    mock_session = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    mock_context.__aexit__.return_value = None
    
    # Configure session manager to return context
    mapping_executor.session_manager.get_async_metamapper_session.return_value = mock_context
    
    # Configure metadata query service to return strategy
    mapping_executor.metadata_query_service.get_strategy.return_value = mock_strategy
    
    # Call get_strategy
    result = await mapping_executor.get_strategy(strategy_name)
    
    # Verify result
    assert result == mock_strategy
    
    # Verify session was used
    mapping_executor.session_manager.get_async_metamapper_session.assert_called_once()
    
    # Verify metadata query service was called
    mapping_executor.metadata_query_service.get_strategy.assert_called_once_with(
        mock_session, strategy_name
    )
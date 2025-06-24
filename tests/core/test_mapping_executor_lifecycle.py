"""Tests for MappingExecutor lifecycle methods."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService


@pytest.fixture
async def mapping_executor():
    """Fixture for a properly initialized MappingExecutor with mock sessions."""
    # Create mock coordinators and services
    mock_lifecycle_coordinator = AsyncMock(spec=LifecycleCoordinator)
    mock_mapping_coordinator = MagicMock(spec=MappingCoordinatorService)
    mock_strategy_coordinator = MagicMock(spec=StrategyCoordinatorService)
    mock_session_manager = MagicMock(spec=SessionManager)
    mock_metadata_query_service = MagicMock(spec=MetadataQueryService)
    
    # Add required attributes for the tests
    mock_mapping_coordinator.iterative_execution_service = AsyncMock()
    mock_session_manager.async_metamapper_session = AsyncMock()
    mock_session_manager.async_cache_session = AsyncMock()
    
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
async def test_async_dispose(mapping_executor):
    """Test async_dispose delegates to lifecycle coordinator."""
    await mapping_executor.async_dispose()
    mapping_executor.lifecycle_coordinator.async_dispose.assert_called_once()


@pytest.mark.asyncio
async def test_save_checkpoint(mapping_executor):
    """Test save_checkpoint delegates to lifecycle coordinator."""
    checkpoint_id = "test_checkpoint"
    state_data = {"key": "value"}
    
    await mapping_executor.save_checkpoint(checkpoint_id, state_data)
    mapping_executor.lifecycle_coordinator.save_checkpoint.assert_called_once_with(
        checkpoint_id, state_data
    )


@pytest.mark.asyncio
async def test_load_checkpoint(mapping_executor):
    """Test load_checkpoint delegates to lifecycle coordinator."""
    checkpoint_id = "test_checkpoint"
    expected_data = {"key": "value"}
    mapping_executor.lifecycle_coordinator.load_checkpoint.return_value = expected_data
    
    result = await mapping_executor.load_checkpoint(checkpoint_id)
    
    assert result == expected_data
    mapping_executor.lifecycle_coordinator.load_checkpoint.assert_called_once_with(checkpoint_id)


@pytest.mark.asyncio
async def test_start_session(mapping_executor):
    """Test start_session delegates to lifecycle coordinator."""
    session_id = "test_session"
    metadata = {"user": "test"}
    expected_id = 123
    
    result = await mapping_executor.start_session(session_id, metadata)
    
    assert result == expected_id
    mapping_executor.lifecycle_coordinator.start_execution.assert_called_once_with(
        execution_id=session_id,
        execution_type='mapping',
        metadata=metadata
    )


@pytest.mark.asyncio
async def test_end_session(mapping_executor):
    """Test end_session delegates to lifecycle coordinator."""
    session_id = "test_session"
    
    await mapping_executor.end_session(session_id)
    mapping_executor.lifecycle_coordinator.complete_execution.assert_called_once_with(
        execution_id=session_id,
        execution_type='mapping',
        result_summary=None
    )
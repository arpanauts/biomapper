"""Tests for the MappingStepExecutionService."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.services.mapping_step_execution_service import MappingStepExecutionService
from biomapper.core.exceptions import (
    ClientExecutionError,
    ClientInitializationError,
    ErrorCode,
)
from biomapper.db.models import MappingPathStep, MappingResource


# Dummy client for testing
class MockClient:
    def __init__(self, config=None):
        if config and config.get("fail_init", False):
            raise ValueError("Client Init Failed")
        self.config = config

    async def map_identifiers(self, ids, **kwargs):
        # Simple mock mapping
        return {id_: (["mapped_" + id_], None) for id_ in ids}


@pytest.fixture
def mock_client_manager():
    """Create a mock client manager."""
    manager = MagicMock()
    manager.get_client_instance = AsyncMock()
    return manager


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    manager = MagicMock()
    manager.check_cache = AsyncMock(return_value={})
    manager.cache_results = AsyncMock()
    return manager


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def step_execution_service(mock_client_manager, mock_cache_manager, mock_logger):
    """Create a MappingStepExecutionService instance with mocked dependencies."""
    return MappingStepExecutionService(
        client_manager=mock_client_manager,
        cache_manager=mock_cache_manager,
        logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_execute_step_client_error(step_execution_service, mock_client_manager):
    """Test that execute_step handles ClientError during mapping."""
    # Create a mock client that raises an error
    mock_client = AsyncMock()
    mock_client.map_identifiers.side_effect = Exception("API error during mapping")
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    mock_step.mapping_resource.config_template = "{}"
    
    # Call execute_step and verify it raises ClientExecutionError
    with pytest.raises(ClientExecutionError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1", "ID2"],
            is_reverse=False
        )
    
    # Verify the error details
    assert "Client error during step execution" in str(exc_info.value)
    assert exc_info.value.client_name == "test_client"
    assert exc_info.value.error_code == ErrorCode.CLIENT_EXECUTION_ERROR
    assert "API error during mapping" in str(exc_info.value.details)
    
    # Verify the mock client was called
    mock_client.map_identifiers.assert_called_once_with(["ID1", "ID2"], config={})


@pytest.mark.asyncio
async def test_execute_step_generic_exception(step_execution_service, mock_client_manager):
    """Test that execute_step handles general exceptions during mapping."""
    # Create a mock client that raises a generic exception
    mock_client = AsyncMock()
    mock_client.map_identifiers.side_effect = ValueError("Unexpected mapping error")
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    mock_step.mapping_resource.config_template = None
    
    # Call execute_step and verify it raises ClientExecutionError
    with pytest.raises(ClientExecutionError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1", "ID2"],
            is_reverse=False
        )
    
    # Verify the error details
    assert "Unexpected error during step execution" in str(exc_info.value)
    assert exc_info.value.client_name == "test_client"
    assert "Unexpected mapping error" in str(exc_info.value.details)
    assert exc_info.value.error_code == ErrorCode.CLIENT_EXECUTION_ERROR
    
    # Verify the mock client was called correctly
    mock_client.map_identifiers.assert_called_once_with(["ID1", "ID2"], config=None)


@pytest.mark.asyncio
async def test_execute_step_reverse_mapping(step_execution_service, mock_client_manager):
    """Test that execute_step handles reverse mapping correctly."""
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.map_identifiers.return_value = {
        "ID1": (["REVERSE1"], None),
        "ID2": (["REVERSE2"], None)
    }
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    mock_step.mapping_resource.config_template = None
    
    # Call execute_step in reverse mode
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["ID1", "ID2"],
        is_reverse=True
    )
    
    # Verify the result
    assert result == {
        "ID1": (["REVERSE1"], None),
        "ID2": (["REVERSE2"], None)
    }
    
    # Verify the mock was called with reverse=True
    mock_client.map_identifiers.assert_called_once_with(
        ["ID1", "ID2"],
        config=None,
        reverse=True
    )


@pytest.mark.asyncio
async def test_execute_step_with_cache_hit(step_execution_service, mock_cache_manager):
    """Test execute_step when cache contains results."""
    # Set up cache to return results
    cached_results = {
        "ID1": (["CACHED1"], {"cached": True}),
        "ID2": (["CACHED2"], {"cached": True})
    }
    mock_cache_manager.check_cache.return_value = cached_results
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    
    # Call execute_step
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["ID1", "ID2"],
        is_reverse=False
    )
    
    # Verify the result matches cached data
    assert result == cached_results
    
    # Verify cache was checked
    mock_cache_manager.check_cache.assert_called_once()
    
    # Verify client was not called (cache hit)
    step_execution_service.client_manager.get_client_instance.assert_not_called()


@pytest.mark.asyncio
async def test_execute_step_partial_cache_hit(step_execution_service, mock_client_manager, mock_cache_manager):
    """Test execute_step with partial cache hit."""
    # Set up partial cache results
    cached_results = {
        "ID1": (["CACHED1"], {"cached": True})
    }
    mock_cache_manager.check_cache.return_value = cached_results
    
    # Set up client to handle uncached ID
    mock_client = AsyncMock()
    mock_client.map_identifiers.return_value = {
        "ID2": (["MAPPED2"], None)
    }
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    mock_step.mapping_resource.config_template = None
    
    # Call execute_step
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["ID1", "ID2"],
        is_reverse=False
    )
    
    # Verify the result contains both cached and fresh results
    assert result == {
        "ID1": (["CACHED1"], {"cached": True}),
        "ID2": (["MAPPED2"], None)
    }
    
    # Verify client was called only for uncached ID
    mock_client.map_identifiers.assert_called_once_with(["ID2"], config=None)
    
    # Verify cache was updated with new results
    mock_cache_manager.cache_results.assert_called_once()


@pytest.mark.asyncio
async def test_execute_step_client_initialization_error(step_execution_service, mock_client_manager):
    """Test execute_step when client initialization fails."""
    # Make client manager raise an error
    mock_client_manager.get_client_instance.side_effect = ClientInitializationError(
        "Failed to initialize client",
        client_name="test_client"
    )
    
    # Create a mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_client"
    
    # Call execute_step and verify it raises ClientInitializationError
    with pytest.raises(ClientInitializationError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1", "ID2"],
            is_reverse=False
        )
    
    # Verify the error was propagated
    assert "Failed to initialize client" in str(exc_info.value)
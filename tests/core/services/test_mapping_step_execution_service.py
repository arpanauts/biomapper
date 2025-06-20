"""Tests for MappingStepExecutionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from biomapper.core.services.mapping_step_execution_service import MappingStepExecutionService
from biomapper.core.exceptions import (
    ClientError,
    ClientExecutionError,
    ClientInitializationError,
    ErrorCode,
)
from biomapper.db.models import MappingPathStep, MappingResource


@pytest.fixture
def mock_client_manager():
    """Create a mock client manager."""
    return AsyncMock()


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    return AsyncMock()


@pytest.fixture
def step_execution_service(mock_client_manager, mock_cache_manager):
    """Create a MappingStepExecutionService instance with mocked dependencies."""
    return MappingStepExecutionService(
        client_manager=mock_client_manager,
        cache_manager=mock_cache_manager
    )


@pytest.fixture
def mock_step():
    """Create a mock mapping path step."""
    step = MagicMock(spec=MappingPathStep)
    step.mapping_resource = MagicMock(spec=MappingResource)
    step.mapping_resource.name = "test_client"
    return step


@pytest.mark.asyncio
async def test_execute_step_forward_success(step_execution_service, mock_client_manager, mock_step):
    """Test successful forward mapping execution."""
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.map_identifiers.return_value = {
        "ID1": (["TARGET1"], None),
        "ID2": (["TARGET2", "TARGET3"], None),
    }
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["ID1", "ID2"],
        is_reverse=False
    )
    
    # Verify results
    assert result == {
        "ID1": (["TARGET1"], None),
        "ID2": (["TARGET2", "TARGET3"], None),
    }
    
    # Verify client was called correctly
    mock_client.map_identifiers.assert_called_once_with(["ID1", "ID2"], config=None)


@pytest.mark.asyncio
async def test_execute_step_with_uniprot_cache_bypass(step_execution_service, mock_client_manager, mock_step):
    """Test that UniProtHistoricalResolverClient bypasses cache when env var is set."""
    # Set environment variable
    os.environ['BYPASS_UNIPROT_CACHE'] = 'true'
    
    try:
        # Create a mock UniProt client
        mock_client = AsyncMock()
        mock_client.__class__.__name__ = 'UniProtHistoricalResolverClient'
        mock_client.map_identifiers.return_value = {
            "P12345": (["Q67890"], None),
        }
        mock_client_manager.get_client_instance.return_value = mock_client
        
        # Execute the step
        result = await step_execution_service.execute_step(
            step=mock_step,
            input_values=["P12345"],
            is_reverse=False
        )
        
        # Verify client was called with bypass_cache config
        mock_client.map_identifiers.assert_called_once_with(
            ["P12345"], 
            config={'bypass_cache': True}
        )
        
    finally:
        # Clean up environment variable
        del os.environ['BYPASS_UNIPROT_CACHE']


@pytest.mark.asyncio
async def test_execute_step_reverse_with_specialized_method(step_execution_service, mock_client_manager, mock_step):
    """Test reverse mapping using specialized reverse_map_identifiers method."""
    # Create a mock client with reverse_map_identifiers method
    mock_client = AsyncMock()
    mock_client.reverse_map_identifiers.return_value = {
        'primary_ids': ['SOURCE1'],
        'input_to_primary': {'TARGET1': 'SOURCE1'},
        'errors': []
    }
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step in reverse
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["TARGET1"],
        is_reverse=True
    )
    
    # Verify results
    assert result == {
        "TARGET1": (["SOURCE1"], None),
    }
    
    # Verify specialized method was called
    mock_client.reverse_map_identifiers.assert_called_once_with(["TARGET1"])


@pytest.mark.asyncio
async def test_execute_step_reverse_by_inversion(step_execution_service, mock_client_manager, mock_step):
    """Test reverse mapping by inverting forward results."""
    # Create a mock client without reverse_map_identifiers method
    mock_client = AsyncMock()
    mock_client.map_identifiers.return_value = {
        'input_to_primary': {
            'SOURCE1': 'TARGET1',
            'SOURCE2': 'TARGET1',
            'SOURCE3': 'TARGET2'
        }
    }
    # Remove reverse_map_identifiers to test fallback
    del mock_client.reverse_map_identifiers
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step in reverse
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["TARGET1", "TARGET2", "TARGET3"],
        is_reverse=True
    )
    
    # Verify results (inverted mapping)
    assert result == {
        "TARGET1": (["SOURCE1", "SOURCE2"], None),
        "TARGET2": (["SOURCE3"], None),
        "TARGET3": (None, None),  # No mapping found
    }


@pytest.mark.asyncio
async def test_execute_step_client_error(step_execution_service, mock_client_manager, mock_step):
    """Test handling of ClientError during execution."""
    # Create a mock client that raises ClientError
    mock_client = AsyncMock()
    mock_client.map_identifiers.side_effect = ClientError(
        "Test client error",
        error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
        details={"error_type": "test_error"}
    )
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step and expect ClientExecutionError
    with pytest.raises(ClientExecutionError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1"],
            is_reverse=False
        )
    
    # Verify error details
    assert "Client error during step execution" in str(exc_info.value)
    assert exc_info.value.client_name == "test_client"
    assert exc_info.value.details["error_type"] == "test_error"
    assert exc_info.value.error_code == ErrorCode.CLIENT_EXECUTION_ERROR


@pytest.mark.asyncio
async def test_execute_step_unexpected_error(step_execution_service, mock_client_manager, mock_step):
    """Test handling of unexpected exceptions during execution."""
    # Create a mock client that raises an unexpected exception
    mock_client = AsyncMock()
    mock_client.map_identifiers.side_effect = ValueError("Unexpected error")
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step and expect ClientExecutionError
    with pytest.raises(ClientExecutionError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1"],
            is_reverse=False
        )
    
    # Verify error details
    assert "Unexpected error during step execution" in str(exc_info.value)
    assert exc_info.value.client_name == "test_client"
    assert "Unexpected error" in str(exc_info.value.details)


@pytest.mark.asyncio
async def test_execute_step_initialization_error(step_execution_service, mock_client_manager, mock_step):
    """Test that ClientInitializationError is propagated."""
    # Make client manager raise initialization error
    mock_client_manager.get_client_instance.side_effect = ClientInitializationError(
        "Failed to initialize client"
    )
    
    # Execute the step and expect the error to propagate
    with pytest.raises(ClientInitializationError) as exc_info:
        await step_execution_service.execute_step(
            step=mock_step,
            input_values=["ID1"],
            is_reverse=False
        )
    
    assert "Failed to initialize client" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_step_ensures_all_inputs_in_results(step_execution_service, mock_client_manager, mock_step):
    """Test that all input values have entries in results, even if not returned by client."""
    # Create a mock client that only returns partial results
    mock_client = AsyncMock()
    mock_client.map_identifiers.return_value = {
        "ID1": (["TARGET1"], None),
        # ID2 and ID3 are missing from client results
    }
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Execute the step
    result = await step_execution_service.execute_step(
        step=mock_step,
        input_values=["ID1", "ID2", "ID3"],
        is_reverse=False
    )
    
    # Verify all inputs have entries
    assert result == {
        "ID1": (["TARGET1"], None),
        "ID2": (None, None),
        "ID3": (None, None),
    }
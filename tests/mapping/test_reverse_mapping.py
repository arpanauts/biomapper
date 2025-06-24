"""Test script to specifically test the reverse mapping functionality."""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from biomapper.core.services.mapping_step_execution_service import MappingStepExecutionService
from biomapper.db.models import MappingPathStep, MappingResource


@pytest.mark.asyncio
async def test_reverse_mapping():
    """Test the reverse mapping functionality in MappingStepExecutionService."""
    # Create mock dependencies
    mock_client_manager = AsyncMock()
    mock_cache_manager = MagicMock()
    mock_logger = MagicMock()
    
    # Create service instance
    service = MappingStepExecutionService(
        client_manager=mock_client_manager,
        cache_manager=mock_cache_manager,
        logger=mock_logger
    )
    
    # Create a mock client with reverse_map_identifiers method
    mock_client = AsyncMock()
    mock_client.reverse_map_identifiers = AsyncMock(return_value={
        "input_to_primary": {
            "ARIVALE_ID1": "UKBB_ID1",
            "ARIVALE_ID2": "UKBB_ID2"
        },
        "errors": []
    })
    mock_client_manager.get_client_instance.return_value = mock_client
    
    # Create mock step and resource
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.mapping_resource = MagicMock(spec=MappingResource)
    mock_step.mapping_resource.name = "test_reverse_client"
    
    # Test reverse mapping
    result = await service.execute_step(
        step=mock_step,
        input_values=["ARIVALE_ID1", "ARIVALE_ID2"],
        is_reverse=True
    )
    
    # Verify results
    assert result == {
        "ARIVALE_ID1": (["UKBB_ID1"], None),
        "ARIVALE_ID2": (["UKBB_ID2"], None)
    }
    
    # Verify the reverse_map_identifiers was called
    mock_client.reverse_map_identifiers.assert_called_once_with(["ARIVALE_ID1", "ARIVALE_ID2"])
    
    print("✓ Reverse mapping test passed successfully")

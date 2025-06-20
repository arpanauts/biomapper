"""
Test DirectMappingService functionality.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.services.direct_mapping_service import DirectMappingService
from biomapper.db.models import MappingPath, Endpoint


@pytest.mark.asyncio
async def test_direct_mapping_service_no_path_found():
    """Test DirectMappingService when no path is found."""
    # Create service instance
    service = DirectMappingService()
    
    # Mock dependencies
    mock_session = MagicMock()
    mock_path_finder = MagicMock()
    mock_path_executor = MagicMock()
    
    # Configure path_finder to return None (no path found)
    mock_path_finder.find_best_path = AsyncMock(return_value=None)
    
    # Execute direct mapping
    result = await service.execute_direct_mapping(
        meta_session=mock_session,
        path_finder=mock_path_finder,
        path_executor=mock_path_executor,
        primary_source_ontology="GENE_NAME",
        primary_target_ontology="ENSEMBL_GENE",
        original_input_ids_set={"GENE1", "GENE2"},
        processed_ids=set(),
        successful_mappings={},
        mapping_direction="forward",
        try_reverse_mapping=False,
        source_endpoint=None,
        target_endpoint=None,
        mapping_session_id="test_session_123",
        batch_size=100,
        max_hop_count=5,
        min_confidence=0.0,
        max_concurrent_batches=5
    )
    
    # Verify result
    assert result["path_found"] is False
    assert result["path_name"] is None
    assert result["path_id"] is None
    assert result["newly_mapped_count"] == 0
    assert result["execution_time"] > 0
    
    # Verify path_finder was called
    mock_path_finder.find_best_path.assert_called_once()


@pytest.mark.asyncio
async def test_direct_mapping_service_path_found_with_mappings():
    """Test DirectMappingService when path is found and mappings succeed."""
    # Create service instance
    service = DirectMappingService()
    
    # Mock dependencies
    mock_session = MagicMock()
    mock_path_finder = MagicMock()
    mock_path_executor = MagicMock()
    
    # Create mock path
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 123
    mock_path.name = "Gene to Ensembl Path"
    
    # Configure path_finder to return the mock path
    mock_path_finder.find_best_path = AsyncMock(return_value=mock_path)
    
    # Configure path_executor to return successful mappings
    mock_mapping_results = {
        "GENE1": {
            "target_identifiers": ["ENSG00000001"],
            "confidence_score": 0.95,
            "hop_count": 1
        },
        "GENE2": {
            "target_identifiers": ["ENSG00000002"],
            "confidence_score": 0.90,
            "hop_count": 1
        }
    }
    mock_path_executor._execute_path = AsyncMock(return_value=mock_mapping_results)
    
    # Execute direct mapping
    successful_mappings = {}
    processed_ids = set()
    
    result = await service.execute_direct_mapping(
        meta_session=mock_session,
        path_finder=mock_path_finder,
        path_executor=mock_path_executor,
        primary_source_ontology="GENE_NAME",
        primary_target_ontology="ENSEMBL_GENE",
        original_input_ids_set={"GENE1", "GENE2"},
        processed_ids=processed_ids,
        successful_mappings=successful_mappings,
        mapping_direction="forward",
        try_reverse_mapping=False,
        source_endpoint=None,
        target_endpoint=None,
        mapping_session_id="test_session_123",
        batch_size=100,
        max_hop_count=5,
        min_confidence=0.0,
        max_concurrent_batches=5
    )
    
    # Verify result
    assert result["path_found"] is True
    assert result["path_name"] == "Gene to Ensembl Path"
    assert result["path_id"] == 123
    assert result["newly_mapped_count"] == 2
    assert result["execution_time"] > 0
    
    # Verify successful_mappings and processed_ids were updated
    assert len(successful_mappings) == 2
    assert "GENE1" in successful_mappings
    assert "GENE2" in successful_mappings
    assert processed_ids == {"GENE1", "GENE2"}
    
    # Verify path_finder and path_executor were called
    mock_path_finder.find_best_path.assert_called_once()
    mock_path_executor._execute_path.assert_called_once()


@pytest.mark.asyncio
async def test_direct_mapping_service_all_ids_already_processed():
    """Test DirectMappingService when all IDs are already processed."""
    # Create service instance
    service = DirectMappingService()
    
    # Mock dependencies
    mock_session = MagicMock()
    mock_path_finder = MagicMock()
    mock_path_executor = MagicMock()
    
    # Create mock path
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 123
    mock_path.name = "Gene to Ensembl Path"
    
    # Configure path_finder to return the mock path
    mock_path_finder.find_best_path = AsyncMock(return_value=mock_path)
    
    # Execute direct mapping with all IDs already processed
    successful_mappings = {}
    processed_ids = {"GENE1", "GENE2"}  # All IDs already processed
    
    result = await service.execute_direct_mapping(
        meta_session=mock_session,
        path_finder=mock_path_finder,
        path_executor=mock_path_executor,
        primary_source_ontology="GENE_NAME",
        primary_target_ontology="ENSEMBL_GENE",
        original_input_ids_set={"GENE1", "GENE2"},
        processed_ids=processed_ids,
        successful_mappings=successful_mappings,
        mapping_direction="forward",
        try_reverse_mapping=False,
        source_endpoint=None,
        target_endpoint=None,
        mapping_session_id="test_session_123",
        batch_size=100,
        max_hop_count=5,
        min_confidence=0.0,
        max_concurrent_batches=5
    )
    
    # Verify result
    assert result["path_found"] is True
    assert result["path_name"] == "Gene to Ensembl Path"
    assert result["path_id"] == 123
    assert result["newly_mapped_count"] == 0
    assert result["execution_time"] > 0
    
    # Verify path_executor was NOT called since all IDs were already processed
    assert not mock_path_executor._execute_path.called
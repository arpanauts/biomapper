"""Tests for MappingExecutor mapping execution methods."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.db.cache_models import PathExecutionStatus


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
    mock_mapping_coordinator.iterative_execution_service = AsyncMock()
    mock_mapping_coordinator.execute_mapping = AsyncMock()
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
async def test_execute_mapping_success(mapping_executor):
    """Test execute_mapping with a successful path execution."""
    input_ids = ["APP", "BRCA1", "NonExistentGene"]
    
    # Create expected output structure
    expected_output = {
        "APP": {
            "source_identifier": "APP",
            "target_identifiers": ["ENSG00000142192.22"],
            "status": "success",
            "confidence_score": 0.9,
            "hop_count": 1,
            "mapping_direction": "forward",
        },
        "BRCA1": {
            "source_identifier": "BRCA1",
            "target_identifiers": ["ENSG00000012048.26"],
            "status": "success",
            "confidence_score": 0.9,
            "hop_count": 1,
            "mapping_direction": "forward",
        },
        "NonExistentGene": {
            "source_identifier": "NonExistentGene",
            "target_identifiers": None,
            "status": "no_mapping_found", 
            "message": "No mapping found",
            "confidence_score": 0.0,
            "hop_count": None,
            "mapping_direction": None,
        }
    }

    # Configure the mock to return our expected output
    mapping_executor.mapping_coordinator.execute_mapping.return_value = expected_output

    # Call execute_mapping
    result = await mapping_executor.execute_mapping(
        identifiers=input_ids,
        source_ontology="GENE_NAME",
        target_ontology="ENSEMBL_GENE"
    )

    # Verify the output matches our expectations
    assert result == expected_output
    assert result["APP"]["status"] == "success"
    assert result["APP"]["target_identifiers"] == ["ENSG00000142192.22"]
    assert result["BRCA1"]["target_identifiers"] == ["ENSG00000012048.26"]
    assert result["NonExistentGene"]["target_identifiers"] is None

    # Verify the mock was called with the correct parameters
    mapping_executor.mapping_coordinator.execute_mapping.assert_called_once_with(
        input_ids, "GENE_NAME", "ENSEMBL_GENE", None, None
    )


@pytest.mark.asyncio
async def test_execute_mapping_no_path_found(mapping_executor):
    """Test execute_mapping when no mapping path is found."""
    input_ids = ["APP", "BRCA1"]
    
    # Mock the mapping_coordinator to return no mapping found results
    expected_result = {
        "APP": {
            "source_identifier": "APP",
            "target_identifiers": None,
            "status": "no_mapping_found",
            "message": "No mapping path found",
            "confidence_score": 0.0,
            "hop_count": None,
            "mapping_direction": None,
        },
        "BRCA1": {
            "source_identifier": "BRCA1",
            "target_identifiers": None,
            "status": "no_mapping_found",
            "message": "No mapping path found",
            "confidence_score": 0.0,
            "hop_count": None,
            "mapping_direction": None,
        }
    }
    
    mapping_executor.mapping_coordinator.execute_mapping.return_value = expected_result
    
    # Act: Call execute_mapping
    result = await mapping_executor.execute_mapping(
        identifiers=input_ids,
        source_ontology="GENE_NAME",
        target_ontology="ENSEMBL_GENE"
    )
    
    # Verify the output structure
    for input_id in input_ids:
        assert input_id in result
        assert result[input_id]["target_identifiers"] is None
        assert result[input_id]["status"] == "no_mapping_found"
    
    # Verify that the mapping coordinator was called with correct parameters
    mapping_executor.mapping_coordinator.execute_mapping.assert_called_once_with(
        input_ids, "GENE_NAME", "ENSEMBL_GENE", None, None
    )


@pytest.mark.asyncio
async def test_execute_mapping_empty_input(mapping_executor):
    """Test execute_mapping with an empty list of input identifiers."""
    input_ids = []  # Empty input list
    expected_output = {}  # Empty results dictionary for empty input

    mapping_executor.mapping_coordinator.execute_mapping.return_value = expected_output

    # Call execute_mapping with empty input list
    result = await mapping_executor.execute_mapping(
        identifiers=input_ids,
        source_ontology="GENE_NAME",
        target_ontology="ENSEMBL_GENE"
    )

    # Verify the output matches our expectations
    assert result == expected_output
    assert result == {}  # Empty input should result in empty results dictionary

    # Verify the mock was called with the correct parameters
    mapping_executor.mapping_coordinator.execute_mapping.assert_called_once_with(
        input_ids, "GENE_NAME", "ENSEMBL_GENE", None, None
    )


@pytest.mark.asyncio 
async def test_execute_path_integration(mapping_executor):
    """Test _execute_path integration with _run_path_steps."""
    from unittest.mock import MagicMock
    
    # Create a mock path with a step
    mock_path = MagicMock()
    mock_path.id = 1
    mock_path.name = "TestPath"
    mock_path.is_reverse = False
    
    # Results from _run_path_steps
    run_path_results = {
        "input1": {
            "final_ids": ["output1"], 
            "provenance": [{
                "path_id": mock_path.id,
                "path_name": mock_path.name,
                "steps_details": [
                    {"resource_id": 1, "client_name": "MockStepClient", "resolved_historical": True}
                ]
            }]
        }
    }
    
    # Patch _run_path_steps to return predefined results
    with patch.object(mapping_executor, '_run_path_steps', new=AsyncMock(return_value=run_path_results)):
        # Call _execute_path
        results = await mapping_executor._execute_path(
            session=AsyncMock(),
            path=mock_path,
            input_identifiers=["input1"],
            source_ontology="SOURCE_ONT",
            target_ontology="TARGET_ONT"
        )
        
        # Verify _run_path_steps was called with the right arguments
        mapping_executor._run_path_steps.assert_called_once()
        call_args = mapping_executor._run_path_steps.call_args[1]
        assert call_args["path"] == mock_path
        assert call_args["initial_input_ids"] == {"input1"}
        
        # Verify the transformed results
        assert "input1" in results
        assert results["input1"]["source_identifier"] == "input1"
        assert results["input1"]["target_identifiers"] == ["output1"]
        assert results["input1"]["status"] == PathExecutionStatus.SUCCESS.value
        assert results["input1"]["mapping_path_details"]["path_id"] == mock_path.id
        assert results["input1"]["mapping_path_details"]["path_name"] == mock_path.name
        assert results["input1"]["mapping_path_details"]["direction"] == "forward"
        assert results["input1"]["mapping_path_details"]["resolved_historical"] is True
"""Tests for the PathFinder service."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.db.models import (
    MappingPath,
    MappingPathStep,
    MappingResource,
    OntologyPreference,
)


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def path_finder(mock_session):
    """Create a PathFinder instance with mocked dependencies."""
    session_factory = AsyncMock()
    session_factory.return_value.__aenter__.return_value = mock_session
    
    return PathFinder(
        session_factory=session_factory,
        cache_size=10,
        cache_expiry_seconds=300,
    )


@pytest.mark.asyncio
async def test_find_direct_paths(path_finder, mock_session):
    """Test _find_direct_paths method."""
    # Create a mock path with necessary attributes
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 998
    mock_path.name = "TestPath"
    mock_path.priority = 1
    
    # Create a mock step with required attributes
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.step_order = 1
    mock_step.mapping_resource = MagicMock()
    mock_step.mapping_resource.name = "TestResource"
    mock_step.mapping_resource.input_ontology_term = "GENE_NAME"
    mock_step.mapping_resource.output_ontology_term = "ENSEMBL_GENE"
    
    # Assign steps to the path
    mock_path.steps = [mock_step]
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = [mock_path]
    mock_session.execute.return_value = mock_result
    
    # Call the method
    paths = await path_finder._find_direct_paths(
        mock_session, 
        "GENE_NAME", 
        "ENSEMBL_GENE"
    )
    
    # Assertions
    assert len(paths) == 1
    assert paths[0].id == 998
    assert paths[0].name == "TestPath"
    
    # Verify the query was executed
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_mapping_paths_direct(path_finder, mock_session):
    """Test find_mapping_paths method for direct path."""
    # Create a mock path
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 1
    mock_path.name = "DirectPath"
    mock_path.priority = 1
    
    # Mock the _find_direct_paths method
    with patch.object(path_finder, '_find_direct_paths', new_callable=AsyncMock) as mock_find_direct:
        mock_find_direct.return_value = [mock_path]
        
        # Call the method
        paths = await path_finder.find_mapping_paths(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE",
            bidirectional=False
        )
        
        # Assertions
        assert len(paths) == 1
        assert paths[0].id == 1
        assert paths[0].name == "DirectPath"
        
        # Verify _find_direct_paths was called
        mock_find_direct.assert_called_once()


@pytest.mark.asyncio
async def test_find_mapping_paths_bidirectional(path_finder, mock_session):
    """Test find_mapping_paths method with bidirectional search."""
    # Create mock paths
    mock_forward_path = MagicMock(spec=MappingPath)
    mock_forward_path.id = 1
    mock_forward_path.name = "ForwardPath"
    mock_forward_path.priority = 1
    
    mock_reverse_path = MagicMock(spec=MappingPath)
    mock_reverse_path.id = 2
    mock_reverse_path.name = "ReversePath"
    mock_reverse_path.priority = 2
    
    # Mock the _find_direct_paths method
    with patch.object(path_finder, '_find_direct_paths', new_callable=AsyncMock) as mock_find_direct:
        # Return forward path on first call, reverse path on second
        mock_find_direct.side_effect = [[mock_forward_path], [mock_reverse_path]]
        
        # Call the method
        paths = await path_finder.find_mapping_paths(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE",
            bidirectional=True
        )
        
        # Assertions
        assert len(paths) == 2
        # Forward path should be first (higher priority)
        assert paths[0].id == 1
        # Reverse path should be wrapped in ReversiblePath
        assert hasattr(paths[1], 'is_reversed')
        
        # Verify _find_direct_paths was called twice
        assert mock_find_direct.call_count == 2


@pytest.mark.asyncio
async def test_find_best_path(path_finder, mock_session):
    """Test find_best_path method."""
    # Create mock paths
    mock_path1 = MagicMock(spec=MappingPath)
    mock_path1.id = 1
    mock_path1.name = "Path1"
    mock_path1.priority = 2
    
    mock_path2 = MagicMock(spec=MappingPath)
    mock_path2.id = 2
    mock_path2.name = "Path2"
    mock_path2.priority = 1  # Higher priority
    
    # Mock find_mapping_paths
    with patch.object(path_finder, 'find_mapping_paths', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [mock_path2, mock_path1]  # Ordered by priority
        
        # Call the method
        best_path = await path_finder.find_best_path(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE"
        )
        
        # Assertions
        assert best_path is not None
        assert best_path.id == 2
        assert best_path.name == "Path2"
        
        # Verify find_mapping_paths was called
        mock_find.assert_called_once_with(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE",
            bidirectional=False,
            preferred_direction=None,
            source_endpoint=None,
            target_endpoint=None
        )


@pytest.mark.asyncio
async def test_get_path_details(path_finder, mock_session):
    """Test get_path_details method."""
    # Create a mock path with steps
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 1
    mock_path.name = "TestPath"
    
    # Create mock steps
    mock_step1 = MagicMock(spec=MappingPathStep)
    mock_step1.step_order = 1
    mock_step1.mapping_resource = MagicMock()
    mock_step1.mapping_resource.name = "Resource1"
    mock_step1.mapping_resource.input_ontology_term = "GENE_NAME"
    mock_step1.mapping_resource.output_ontology_term = "GENE_ID"
    
    mock_step2 = MagicMock(spec=MappingPathStep)
    mock_step2.step_order = 2
    mock_step2.mapping_resource = MagicMock()
    mock_step2.mapping_resource.name = "Resource2"
    mock_step2.mapping_resource.input_ontology_term = "GENE_ID"
    mock_step2.mapping_resource.output_ontology_term = "ENSEMBL_GENE"
    
    mock_path.steps = [mock_step1, mock_step2]
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_path
    mock_session.execute.return_value = mock_result
    
    # Call the method
    details = await path_finder.get_path_details(1)
    
    # Assertions
    assert details is not None
    assert details['path_id'] == 1
    assert details['path_name'] == "TestPath"
    assert len(details['steps']) == 2
    assert details['steps'][0]['order'] == 1
    assert details['steps'][0]['resource_name'] == "Resource1"
    assert details['steps'][1]['order'] == 2
    assert details['steps'][1]['resource_name'] == "Resource2"


@pytest.mark.asyncio
async def test_cache_functionality(path_finder, mock_session):
    """Test that caching works correctly."""
    # Create a mock path
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 1
    mock_path.name = "CachedPath"
    mock_path.priority = 1
    
    # Mock the _find_direct_paths method
    with patch.object(path_finder, '_find_direct_paths', new_callable=AsyncMock) as mock_find_direct:
        mock_find_direct.return_value = [mock_path]
        
        # First call - should hit the database
        paths1 = await path_finder.find_mapping_paths(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE",
            bidirectional=False
        )
        
        # Second call - should use cache
        paths2 = await path_finder.find_mapping_paths(
            source_ontology="GENE_NAME",
            target_ontology="ENSEMBL_GENE",
            bidirectional=False
        )
        
        # Assertions
        assert len(paths1) == 1
        assert len(paths2) == 1
        assert paths1[0].id == paths2[0].id
        
        # Verify _find_direct_paths was only called once (cached on second call)
        mock_find_direct.assert_called_once()


@pytest.mark.asyncio
async def test_clear_cache(path_finder):
    """Test clear_cache method."""
    # Add some entries to cache
    path_finder._cache["test_key"] = "test_value"
    
    # Clear cache
    path_finder.clear_cache()
    
    # Verify cache is empty
    assert len(path_finder._cache) == 0
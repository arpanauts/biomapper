"""
Comprehensive unit tests for the PathFinder module.

This test suite validates the complex logic of path discovery in the mapping engine,
ensuring correct identification of routes between different ontologies.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.core.exceptions import BiomapperError, ErrorCode
from biomapper.db.models import (
    MappingPath,
    MappingPathStep,
    MappingResource,
    EndpointRelationship,
    Endpoint
)


class TestPathFinder:
    """Test cases for PathFinder class."""
    
    @pytest.fixture
    def path_finder(self):
        """Create a PathFinder instance for testing."""
        return PathFinder(cache_size=10, cache_expiry_seconds=60)
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_direct_path(self):
        """Create a mock direct mapping path."""
        # Create mock resource
        resource = Mock(spec=MappingResource)
        resource.id = 101
        resource.name = "Direct Mapper"
        resource.client_class_path = "clients.DirectMapper"
        resource.input_ontology_term = "GENE_SYMBOL"
        resource.output_ontology_term = "UNIPROT_ID"
        
        # Create mock step
        step = Mock(spec=MappingPathStep)
        step.step_order = 1
        step.mapping_resource = resource
        step.mapping_resource_id = resource.id
        
        # Create mock path
        path = Mock(spec=MappingPath)
        path.id = 1
        path.name = "Direct Gene to UniProt"
        path.priority = 10
        path.is_active = True
        path.source_type = "GENE_SYMBOL"
        path.target_type = "UNIPROT_ID"
        path.steps = [step]
        
        return path
    
    @pytest.fixture
    def mock_indirect_path(self):
        """Create a mock indirect (multi-step) mapping path."""
        # First step resource
        resource1 = Mock(spec=MappingResource)
        resource1.id = 201
        resource1.name = "Gene to Ensembl Mapper"
        resource1.client_class_path = "clients.GeneToEnsemblMapper"
        resource1.input_ontology_term = "GENE_SYMBOL"
        resource1.output_ontology_term = "ENSEMBL_ID"
        
        # Second step resource
        resource2 = Mock(spec=MappingResource)
        resource2.id = 202
        resource2.name = "Ensembl to UniProt Mapper"
        resource2.client_class_path = "clients.EnsemblToUniprotMapper"
        resource2.input_ontology_term = "ENSEMBL_ID"
        resource2.output_ontology_term = "UNIPROT_ID"
        
        # Create steps
        step1 = Mock(spec=MappingPathStep)
        step1.step_order = 1
        step1.mapping_resource = resource1
        step1.mapping_resource_id = resource1.id
        
        step2 = Mock(spec=MappingPathStep)
        step2.step_order = 2
        step2.mapping_resource = resource2
        step2.mapping_resource_id = resource2.id
        
        # Create path
        path = Mock(spec=MappingPath)
        path.id = 2
        path.name = "Indirect Gene to UniProt via Ensembl"
        path.priority = 20
        path.is_active = True
        path.source_type = "GENE_SYMBOL"
        path.target_type = "UNIPROT_ID"
        path.steps = [step1, step2]
        
        return path
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = Mock(spec=Endpoint)
        source.id = 100
        source.name = "HGNC Gene Database"
        
        target = Mock(spec=Endpoint)
        target.id = 200
        target.name = "UniProt Database"
        
        return source, target
    
    # Test Case 1: Test Direct Path Found
    @pytest.mark.asyncio
    async def test_direct_path_found(self, path_finder, mock_session, mock_direct_path):
        """Test that find_mapping_paths returns the correct single-step path."""
        # Mock the session to return a direct path
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute the path finding
        result = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], ReversiblePath)
        assert result[0].original_path == mock_direct_path
        assert result[0].name == "Direct Gene to UniProt"
        assert not result[0].is_reverse
        assert len(result[0].steps) == 1
    
    # Test Case 2: Test Indirect Path Found
    @pytest.mark.asyncio
    async def test_indirect_path_found(self, path_finder, mock_session, mock_indirect_path):
        """Test that find_mapping_paths correctly assembles a two-step path."""
        # Mock the session to return an indirect path
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_indirect_path])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute the path finding
        result = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], ReversiblePath)
        assert result[0].original_path == mock_indirect_path
        assert result[0].name == "Indirect Gene to UniProt via Ensembl"
        assert len(result[0].steps) == 2
        assert result[0].steps[0].step_order == 1
        assert result[0].steps[1].step_order == 2
    
    # Test Case 3: Test No Path Found
    @pytest.mark.asyncio
    async def test_no_path_found(self, path_finder, mock_session):
        """Test that find_mapping_paths returns empty list when no paths exist."""
        # Mock the session to return no paths
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute the path finding
        result = await path_finder.find_mapping_paths(
            mock_session,
            "NONEXISTENT_TYPE",
            "ANOTHER_NONEXISTENT_TYPE"
        )
        
        # Assertions
        assert result == []
    
    # Test Case 4: Test Path Ambiguity
    @pytest.mark.asyncio
    async def test_path_ambiguity_priority_selection(
        self, path_finder, mock_session, mock_direct_path, mock_indirect_path
    ):
        """Test that PathFinder correctly selects the path with highest priority."""
        # Create additional path with different priority
        high_priority_path = Mock(spec=MappingPath)
        high_priority_path.id = 3
        high_priority_path.name = "High Priority Path"
        high_priority_path.priority = 5  # Lower number = higher priority
        high_priority_path.is_active = True
        high_priority_path.steps = []
        
        # Mock session to return multiple paths
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(
                return_value=[mock_direct_path, mock_indirect_path, high_priority_path]
            )))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute the path finding
        result = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Assertions - paths should be sorted by priority
        assert len(result) == 3
        assert result[0].original_path == high_priority_path  # Priority 5
        assert result[1].original_path == mock_direct_path    # Priority 10
        assert result[2].original_path == mock_indirect_path  # Priority 20
    
    # Test Case 5: Test _get_path_details Logic
    @pytest.mark.asyncio
    async def test_get_path_details_logic(self, path_finder, mock_session, mock_indirect_path):
        """Test that get_path_details correctly constructs the path details dictionary."""
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_indirect_path)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute get_path_details
        details = await path_finder.get_path_details(mock_session, 2)
        
        # Assertions
        assert "step_1" in details
        assert "step_2" in details
        
        # Check step 1 details
        assert details["step_1"]["resource_id"] == 201
        assert details["step_1"]["resource_name"] == "Gene to Ensembl Mapper"
        assert details["step_1"]["resource_client"] == "clients.GeneToEnsemblMapper"
        assert details["step_1"]["input_ontology"] == "GENE_SYMBOL"
        assert details["step_1"]["output_ontology"] == "ENSEMBL_ID"
        
        # Check step 2 details
        assert details["step_2"]["resource_id"] == 202
        assert details["step_2"]["resource_name"] == "Ensembl to UniProt Mapper"
        assert details["step_2"]["resource_client"] == "clients.EnsemblToUniprotMapper"
        assert details["step_2"]["input_ontology"] == "ENSEMBL_ID"
        assert details["step_2"]["output_ontology"] == "UNIPROT_ID"
    
    @pytest.mark.asyncio
    async def test_get_path_details_not_found(self, path_finder, mock_session):
        """Test get_path_details when path doesn't exist."""
        # Mock the database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute get_path_details
        details = await path_finder.get_path_details(mock_session, 999)
        
        # Should return empty dict
        assert details == {}
    
    @pytest.mark.asyncio
    async def test_get_path_details_database_error(self, path_finder, mock_session):
        """Test get_path_details handles database errors gracefully."""
        # Mock database error
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("DB Error"))
        
        # Execute get_path_details - should not raise, just return empty dict
        details = await path_finder.get_path_details(mock_session, 1)
        
        assert details == {}
    
    # Test Case 6: Test Path Caching
    @pytest.mark.asyncio
    async def test_path_caching_behavior(self, path_finder, mock_session, mock_direct_path):
        """Test that find_mapping_paths caches results and uses cache on subsequent calls."""
        # Mock the database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # First call - should query database
        result1 = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Record number of database calls
        initial_call_count = mock_session.execute.call_count
        
        # Second call with same parameters - should use cache
        result2 = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Third call with same parameters - should still use cache
        result3 = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID"
        )
        
        # Assertions
        assert len(result1) == len(result2) == len(result3) == 1
        assert result1[0].original_path == result2[0].original_path == result3[0].original_path
        
        # Database should not have been called again
        assert mock_session.execute.call_count == initial_call_count
    
    @pytest.mark.asyncio
    async def test_path_caching_different_parameters(self, path_finder, mock_session, mock_direct_path):
        """Test that cache key includes all relevant parameters."""
        # Mock the database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Call with different parameter combinations
        await path_finder.find_mapping_paths(mock_session, "TYPE1", "TYPE2")
        await path_finder.find_mapping_paths(mock_session, "TYPE1", "TYPE2", bidirectional=True)
        await path_finder.find_mapping_paths(
            mock_session, "TYPE1", "TYPE2", bidirectional=True, preferred_direction="reverse"
        )
        
        # Each should result in a separate cache entry
        assert len(path_finder._path_cache) == 3
    
    @pytest.mark.asyncio
    async def test_cache_expiry_behavior(self, path_finder, mock_session, mock_direct_path):
        """Test that cache entries expire after the configured time."""
        # Set very short expiry for testing
        path_finder._path_cache_expiry_seconds = 0.1
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # First call
        await path_finder.find_mapping_paths(mock_session, "TYPE1", "TYPE2")
        initial_calls = mock_session.execute.call_count
        
        # Wait for expiry
        await asyncio.sleep(0.15)
        
        # Second call - should hit database again
        await path_finder.find_mapping_paths(mock_session, "TYPE1", "TYPE2")
        
        # Database should have been called again
        assert mock_session.execute.call_count > initial_calls
    
    # Additional tests for edge cases and error handling
    @pytest.mark.asyncio
    async def test_bidirectional_search_with_endpoints(
        self, path_finder, mock_session, mock_direct_path, mock_endpoints
    ):
        """Test bidirectional search with relationship-specific paths."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock relationship and paths
        mock_relationship = Mock(spec=EndpointRelationship)
        mock_relationship.id = 1
        
        # Mock the relationship query result
        rel_result = Mock()
        rel_result.scalar_one_or_none = Mock(return_value=mock_relationship)
        
        # Mock the paths query result
        paths_result = Mock()
        paths_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        
        # Mock for reverse relationship query (no relationship found)
        no_rel_result = Mock()
        no_rel_result.scalar_one_or_none = Mock(return_value=None)
        
        # We need 3 results: forward relationship, forward paths, reverse relationship (none)
        mock_session.execute = AsyncMock(side_effect=[rel_result, paths_result, no_rel_result])
        
        # Execute with endpoints
        result = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID",
            bidirectional=True,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )
        
        assert len(result) >= 1
        assert all(isinstance(p, ReversiblePath) for p in result)
    
    @pytest.mark.asyncio
    async def test_find_direct_paths_complex_query(self, path_finder, mock_session):
        """Test the complex query logic in _find_direct_paths."""
        # Create a path that should be found by the complex query
        resource = Mock(spec=MappingResource)
        resource.input_ontology_term = "SOURCE_ONTOLOGY"
        resource.output_ontology_term = "TARGET_ONTOLOGY"
        
        step = Mock(spec=MappingPathStep)
        step.step_order = 1
        step.mapping_resource = resource
        
        path = Mock(spec=MappingPath)
        path.id = 10
        path.name = "Complex Query Path"
        path.priority = 15
        path.is_active = True
        path.source_type = None  # This forces the complex query
        path.target_type = None
        path.steps = [step]
        
        # First query returns empty (simple query)
        empty_result = Mock()
        empty_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        # Second query returns the path (complex query)
        complex_result = Mock()
        complex_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[path])))
        ))
        
        mock_session.execute = AsyncMock(side_effect=[empty_result, complex_result])
        
        result = await path_finder._find_direct_paths(
            mock_session,
            "SOURCE_ONTOLOGY",
            "TARGET_ONTOLOGY"
        )
        
        assert len(result) == 1
        assert result[0] == path
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction_preserves_most_recent(self, path_finder, mock_session):
        """Test that LRU eviction keeps the most recently used entries."""
        # Set very small cache
        path_finder._path_cache_max_size = 2
        
        # Mock empty results for simplicity
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Add entries to cache
        await path_finder.find_mapping_paths(mock_session, "TYPE1", "TYPE2")
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await path_finder.find_mapping_paths(mock_session, "TYPE3", "TYPE4")
        await asyncio.sleep(0.01)
        
        # Cache should be full
        assert len(path_finder._path_cache) == 2
        
        # Add one more - should evict TYPE1->TYPE2
        await path_finder.find_mapping_paths(mock_session, "TYPE5", "TYPE6")
        
        # Check that oldest was evicted
        assert len(path_finder._path_cache) == 2
        assert "TYPE1_TYPE2_False_forward" not in path_finder._path_cache
        assert "TYPE3_TYPE4_False_forward" in path_finder._path_cache
        assert "TYPE5_TYPE6_False_forward" in path_finder._path_cache
    
    @pytest.mark.asyncio
    async def test_reversible_path_priority_adjustment(
        self, path_finder, mock_session, mock_direct_path
    ):
        """Test that reverse paths have adjusted priority."""
        # Create a reverse path  
        reverse_path = Mock(spec=MappingPath)
        reverse_path.id = 5
        reverse_path.name = "Reverse Path"
        reverse_path.priority = 10
        reverse_path.steps = []
        
        # Mock to return forward path first, then reverse
        forward_result = Mock()
        forward_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[mock_direct_path])))
        ))
        
        reverse_result = Mock()
        reverse_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(return_value=[reverse_path])))
        ))
        
        mock_session.execute = AsyncMock(side_effect=[forward_result, reverse_result])
        
        # Execute bidirectional search
        result = await path_finder.find_mapping_paths(
            mock_session,
            "GENE_SYMBOL",
            "UNIPROT_ID",
            bidirectional=True
        )
        
        # Check that priorities are adjusted
        forward_wrapped = next(p for p in result if not p.is_reverse)
        reverse_wrapped = next(p for p in result if p.is_reverse)
        
        assert forward_wrapped.priority == 10  # Original priority
        assert reverse_wrapped.priority == 15   # Original (10) + 5 for being reverse
    
    def test_clear_cache_functionality(self, path_finder):
        """Test that clear_cache removes all cached entries."""
        # Add some cache entries
        path_finder._path_cache = {
            "key1": [],
            "key2": [],
            "key3": []
        }
        path_finder._path_cache_timestamps = {
            "key1": time.time(),
            "key2": time.time(),
            "key3": time.time()
        }
        
        # Clear cache
        path_finder.clear_cache()
        
        # Verify everything is cleared
        assert len(path_finder._path_cache) == 0
        assert len(path_finder._path_cache_timestamps) == 0
    
    @pytest.mark.asyncio
    async def test_error_propagation_from_database(self, path_finder, mock_session):
        """Test that database errors are properly wrapped and propagated."""
        # Mock a database error
        mock_session.execute = AsyncMock(
            side_effect=SQLAlchemyError("Connection lost")
        )
        
        # Should raise BiomapperError with proper error code
        with pytest.raises(BiomapperError) as exc_info:
            await path_finder.find_mapping_paths(
                mock_session,
                "GENE_SYMBOL",
                "UNIPROT_ID"
            )
        
        assert exc_info.value.error_code == ErrorCode.DATABASE_QUERY_ERROR
        assert "Connection lost" in str(exc_info.value.details["error"])


class TestPathFinderIntegration:
    """Integration-style tests that test multiple components together."""
    
    @pytest.mark.asyncio
    async def test_complete_mapping_workflow(self):
        """Test a complete mapping workflow with caching and multiple path types."""
        path_finder = PathFinder(cache_size=5, cache_expiry_seconds=300)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Create various paths
        direct_path = Mock(spec=MappingPath)
        direct_path.id = 1
        direct_path.name = "Direct Path"
        direct_path.priority = 10
        direct_path.is_active = True
        direct_path.steps = []
        
        indirect_path = Mock(spec=MappingPath)
        indirect_path.id = 2
        indirect_path.name = "Indirect Path"
        indirect_path.priority = 20
        indirect_path.is_active = True
        indirect_path.steps = []
        
        # Mock database responses
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(
            unique=Mock(return_value=Mock(all=Mock(
                return_value=[direct_path, indirect_path]
            )))
        ))
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # First search - hits database
        paths1 = await path_finder.find_mapping_paths(
            mock_session, "TYPE_A", "TYPE_B"
        )
        assert len(paths1) == 2
        
        # Get best path
        best = await path_finder.find_best_path(
            mock_session, "TYPE_A", "TYPE_B"
        )
        assert best.original_path == direct_path
        
        # Second search - uses cache
        initial_calls = mock_session.execute.call_count
        paths2 = await path_finder.find_mapping_paths(
            mock_session, "TYPE_A", "TYPE_B"
        )
        assert mock_session.execute.call_count == initial_calls  # No new DB calls
        
        # Clear cache and search again
        path_finder.clear_cache()
        paths3 = await path_finder.find_mapping_paths(
            mock_session, "TYPE_A", "TYPE_B"
        )
        assert mock_session.execute.call_count > initial_calls  # New DB calls made
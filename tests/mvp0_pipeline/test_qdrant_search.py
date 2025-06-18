"""
Unit tests for the Qdrant search component in the MVP0 pipeline.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from biomapper.mvp0_pipeline.qdrant_search import search_qdrant_for_biochemical_name
from biomapper.schemas.mvp0_schema import QdrantSearchResultItem
from biomapper.schemas.rag_schema import MappingOutput, MappingResultItem


class TestQdrantSearch:
    """Test suite for the Qdrant search functionality."""

    @pytest.mark.asyncio
    async def test_search_successful_with_scores(self):
        """Test successful search with individual scores."""
        # Mock client and results
        mock_client = AsyncMock()
        
        # Create mock mapping results
        mock_mapping_output = MappingOutput(
            qdrant_points=[],  # Not used in our implementation
            metadata={}
        )
        
        # Add mock results to metadata
        mock_mapping_output.metadata["Aspirin"] = MappingResult(
            target_ids=["PUBCHEM:2244", "PUBCHEM:5353"],
            scores=[0.95, 0.89],
            metadata={}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        # Perform search
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="Aspirin",
            top_k=5,
            client=mock_client
        )
        
        # Verify results
        assert len(results) == 2
        assert results[0].cid == 2244
        assert results[0].qdrant_score == pytest.approx(0.95)
        assert results[1].cid == 5353
        assert results[1].qdrant_score == pytest.approx(0.89)
        
        # Verify client was called correctly
        mock_client.map_identifiers.assert_called_once_with(ids_to_map=["Aspirin"], top_k=5)
        mock_client.get_last_mapping_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_top_k_limit(self):
        """Test that top_k limit is respected."""
        mock_client = AsyncMock()
        
        # Create more results than top_k
        mock_mapping_output = MappingOutput(
            qdrant_points=[],
            metadata={}
        )
        
        mock_mapping_output.metadata["Compound"] = MappingResult(
            target_ids=[f"PUBCHEM:{i}" for i in range(1000, 1010)],
            scores=[0.9 - i*0.05 for i in range(10)],
            metadata={}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        # Search with top_k=3
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="Compound",
            top_k=3,
            client=mock_client
        )
        
        # Should only return top 3
        assert len(results) == 3
        assert results[0].cid == 1000
        assert results[1].cid == 1001
        assert results[2].cid == 1002

    @pytest.mark.asyncio
    async def test_search_empty_input(self):
        """Test handling of empty input."""
        mock_client = AsyncMock()
        
        # Test empty string
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="",
            top_k=5,
            client=mock_client
        )
        
        assert results == []
        mock_client.map_identifiers.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test handling when no results are found."""
        mock_client = AsyncMock()
        
        # Mock empty results
        mock_mapping_output = MappingOutput(
            qdrant_points=[],
            metadata={}
        )
        
        mock_mapping_output.metadata["UnknownCompound"] = MappingResult(
            target_ids=[],
            scores=[],
            metadata={}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="UnknownCompound",
            top_k=5,
            client=mock_client
        )
        
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_scores_mismatch(self):
        """Test fallback when scores list doesn't match target_ids length."""
        mock_client = AsyncMock()
        
        mock_mapping_output = MappingOutput(
            qdrant_points=[],
            metadata={}
        )
        
        # Mismatched lengths - should use best_score fallback
        mock_mapping_output.metadata["Compound"] = MappingResult(
            target_ids=["PUBCHEM:123", "PUBCHEM:456"],
            scores=[0.85],  # Only one score for two results
            metadata={"best_score": 0.85}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="Compound",
            top_k=5,
            client=mock_client
        )
        
        # Both results should have the same score
        assert len(results) == 2
        assert results[0].qdrant_score == pytest.approx(0.85)
        assert results[1].qdrant_score == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_search_client_error(self):
        """Test error handling when client raises exception."""
        mock_client = AsyncMock()
        mock_client.map_identifiers = AsyncMock(side_effect=Exception("Connection error"))
        
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="TestCompound",
            top_k=5,
            client=mock_client
        )
        
        # Should return empty list on error
        assert results == []

    @pytest.mark.asyncio
    async def test_search_invalid_pubchem_id(self):
        """Test handling of invalid PubChem IDs."""
        mock_client = AsyncMock()
        
        mock_mapping_output = MappingOutput(
            qdrant_points=[],
            metadata={}
        )
        
        # Mix of valid and invalid IDs
        mock_mapping_output.metadata["Compound"] = MappingResult(
            target_ids=["PUBCHEM:123", "INVALID:456", "PUBCHEM:not_a_number", "PUBCHEM:789"],
            scores=[0.9, 0.85, 0.8, 0.75],
            metadata={}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="Compound",
            top_k=5,
            client=mock_client
        )
        
        # Should only include valid PubChem IDs
        assert len(results) == 2
        assert results[0].cid == 123
        assert results[0].qdrant_score == pytest.approx(0.9)
        assert results[1].cid == 789
        assert results[1].qdrant_score == pytest.approx(0.75)

    @pytest.mark.asyncio
    @patch('biomapper.mvp0_pipeline.qdrant_search.get_default_client')
    async def test_search_with_default_client(self, mock_get_default_client):
        """Test using the default client when none is provided."""
        # Create a mock client
        mock_client = AsyncMock()
        mock_get_default_client.return_value = mock_client
        
        # Setup mock response
        mock_mapping_output = MappingOutput(
            qdrant_points=[],
            metadata={}
        )
        
        mock_mapping_output.metadata["Test"] = MappingResult(
            target_ids=["PUBCHEM:999"],
            scores=[0.87],
            metadata={}
        )
        
        mock_client.map_identifiers = AsyncMock(return_value=None)
        mock_client.get_last_mapping_output = AsyncMock(return_value=mock_mapping_output)
        
        # Call without providing client
        results = await search_qdrant_for_biochemical_name(
            biochemical_name="Test",
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0].cid == 999
        
        # Verify default client was retrieved
        mock_get_default_client.assert_called_once()
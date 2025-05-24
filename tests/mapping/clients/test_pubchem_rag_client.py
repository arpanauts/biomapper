"""Integration tests for PubChemRAGMappingClient score propagation."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import asyncio
import sys

# Mock qdrant_client module if not available
try:
    import qdrant_client
except ImportError:
    sys.modules['qdrant_client'] = MagicMock()
    sys.modules['qdrant_client.models'] = MagicMock()

# Mock sentence_transformers if not available
try:
    import sentence_transformers
except ImportError:
    sys.modules['sentence_transformers'] = MagicMock()

from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient
from biomapper.schemas.rag_schema import MappingResultItem, MappingOutput


class TestPubChemRAGMappingClientScores:
    """Test that PubChemRAGMappingClient properly propagates Qdrant similarity scores."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        mock_client = Mock()
        # Mock collection info
        mock_collection_info = Mock()
        mock_collection_info.points_count = 1000
        mock_client.get_collection.return_value = mock_collection_info
        return mock_client
    
    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock sentence transformer model."""
        mock_model = Mock()
        # Return consistent embeddings
        mock_model.encode.return_value = np.array([[0.1] * 384])
        return mock_model
    
    @pytest.fixture
    def pubchem_client(self, mock_qdrant_client, mock_embedding_model):
        """Create a PubChemRAGMappingClient with mocked dependencies."""
        with patch('biomapper.mapping.clients.pubchem_rag_client.QdrantClient', return_value=mock_qdrant_client):
            with patch('biomapper.mapping.clients.pubchem_rag_client.SentenceTransformer', return_value=mock_embedding_model):
                client = PubChemRAGMappingClient({
                    "qdrant_host": "localhost",
                    "qdrant_port": 6333,
                    "collection_name": "test_collection",
                    "top_k": 3,
                    "score_threshold": 0.5
                })
                return client
    
    @pytest.mark.asyncio
    async def test_map_identifiers_captures_scores(self, pubchem_client, mock_qdrant_client):
        """Test that map_identifiers captures and stores Qdrant similarity scores."""
        # Create mock search results with different scores
        mock_results = []
        scores = [0.95, 0.87, 0.73]
        cids = ["123456", "234567", "345678"]
        
        for i, (score, cid) in enumerate(zip(scores, cids)):
            mock_result = Mock()
            mock_result.score = score
            mock_result.payload = {"cid": cid}
            mock_results.append(mock_result)
        
        mock_qdrant_client.search.return_value = mock_results
        
        # Perform mapping
        test_identifiers = ["aspirin", "caffeine"]
        results = await pubchem_client.map_identifiers(test_identifiers)
        
        # Verify traditional results format (backward compatibility)
        assert "aspirin" in results
        assert "caffeine" in results
        
        # Check aspirin results
        target_ids, component_id = results["aspirin"]
        assert len(target_ids) == 3
        assert target_ids == ["PUBCHEM:123456", "PUBCHEM:234567", "PUBCHEM:345678"]
        assert component_id == "0.95"  # Best score as string
        
        # Verify detailed mapping output is stored
        assert pubchem_client.last_mapping_output is not None
        assert isinstance(pubchem_client.last_mapping_output, MappingOutput)
        
        # Check detailed results
        detailed_results = pubchem_client.get_last_mapping_output()
        assert len(detailed_results.results) == 2
        
        # Verify first result (aspirin)
        aspirin_result = detailed_results.results[0]
        assert aspirin_result.identifier == "aspirin"
        assert aspirin_result.qdrant_similarity_score == 0.95
        assert aspirin_result.confidence == 0.95
        assert aspirin_result.component_id == "0.95"
        assert aspirin_result.metadata["all_scores"] == [0.95, 0.87, 0.73]
        assert aspirin_result.metadata["distance_metric"] == "Cosine"
        assert "score_interpretation" in aspirin_result.metadata
    
    @pytest.mark.asyncio
    async def test_map_identifiers_no_results(self, pubchem_client, mock_qdrant_client):
        """Test behavior when no results are found."""
        mock_qdrant_client.search.return_value = []
        
        results = await pubchem_client.map_identifiers(["unknown_compound"])
        
        # Check traditional format
        assert results["unknown_compound"] == (None, None)
        
        # Check detailed output
        detailed_results = pubchem_client.get_last_mapping_output()
        assert len(detailed_results.results) == 1
        unknown_result = detailed_results.results[0]
        assert unknown_result.identifier == "unknown_compound"
        assert unknown_result.qdrant_similarity_score is None
        assert unknown_result.confidence is None
        assert unknown_result.target_ids is None
    
    @pytest.mark.asyncio
    async def test_map_identifiers_empty_input(self, pubchem_client):
        """Test handling of empty or whitespace identifiers."""
        test_identifiers = ["", "  ", "valid_name"]
        
        # Mock results for valid_name
        mock_result = Mock()
        mock_result.score = 0.9
        mock_result.payload = {"cid": "999999"}
        pubchem_client.qdrant_client.search.return_value = [mock_result]
        
        results = await pubchem_client.map_identifiers(test_identifiers)
        
        # Check all results are present
        assert "" in results
        assert "  " in results
        assert "valid_name" in results
        
        # Empty strings should have no results
        assert results[""] == (None, None)
        assert results["  "] == (None, None)
        
        # Valid name should have results
        assert results["valid_name"][0] == ["PUBCHEM:999999"]
        assert results["valid_name"][1] == "0.9"
        
        # Check detailed output
        detailed_results = pubchem_client.get_last_mapping_output()
        assert len(detailed_results.results) == 3
    
    @pytest.mark.asyncio
    async def test_map_identifiers_error_handling(self, pubchem_client, mock_qdrant_client):
        """Test error handling during mapping."""
        # Make search throw an exception
        mock_qdrant_client.search.side_effect = Exception("Connection error")
        
        results = await pubchem_client.map_identifiers(["test_compound"])
        
        # Should return None results
        assert results["test_compound"] == (None, None)
        
        # Check detailed output contains error
        detailed_results = pubchem_client.get_last_mapping_output()
        assert len(detailed_results.results) == 1
        error_result = detailed_results.results[0]
        assert error_result.identifier == "test_compound"
        assert error_result.qdrant_similarity_score is None
        assert "error" in error_result.metadata
        assert "Connection error" in error_result.metadata["error"]
    
    @pytest.mark.asyncio
    async def test_map_identifiers_metadata_propagation(self, pubchem_client, mock_qdrant_client):
        """Test that metadata is properly propagated in detailed output."""
        mock_result = Mock()
        mock_result.score = 0.85
        mock_result.payload = {"cid": "111111"}
        mock_qdrant_client.search.return_value = [mock_result]
        
        await pubchem_client.map_identifiers(["test"])
        
        detailed_results = pubchem_client.get_last_mapping_output()
        
        # Check output metadata
        assert detailed_results.metadata["collection"] == "test_collection"
        assert detailed_results.metadata["embedding_model"] == "BAAI/bge-small-en-v1.5"
        assert detailed_results.metadata["distance_metric"] == "Cosine"
        assert detailed_results.metadata["top_k"] == 3
        assert detailed_results.metadata["score_threshold"] == 0.5
    
    def test_get_last_mapping_output_before_mapping(self, pubchem_client):
        """Test get_last_mapping_output returns None before any mapping."""
        assert pubchem_client.get_last_mapping_output() is None
    
    @pytest.mark.asyncio
    async def test_multiple_scores_handling(self, pubchem_client, mock_qdrant_client):
        """Test handling of multiple results with different scores."""
        # Create results with various scores
        mock_results = []
        for i in range(5):
            mock_result = Mock()
            mock_result.score = 0.9 - (i * 0.1)
            mock_result.payload = {"cid": f"{100000 + i}"}
            mock_results.append(mock_result)
        
        mock_qdrant_client.search.return_value = mock_results
        
        await pubchem_client.map_identifiers(["multi_match"])
        
        detailed_results = pubchem_client.get_last_mapping_output()
        multi_result = detailed_results.results[0]
        
        # Should have captured all scores
        assert len(multi_result.metadata["all_scores"]) == 5
        assert multi_result.metadata["all_scores"] == [0.9, 0.8, 0.7, 0.6, 0.5]
        
        # Best score should be used for qdrant_similarity_score
        assert multi_result.qdrant_similarity_score == 0.9
        assert multi_result.confidence == 0.9
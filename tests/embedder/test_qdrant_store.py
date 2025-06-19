"""Tests for QdrantVectorStore score handling."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from typing import List, Dict, Any, Optional

# Mock the config loading before importing
with patch('os.makedirs'):
    from biomapper.embedder.storage.qdrant_store import QdrantVectorStore


# Create a concrete implementation for testing
class TestableQdrantVectorStore(QdrantVectorStore):
    """Concrete implementation of QdrantVectorStore for testing."""
    
    async def add_documents(
        self, documents: List[Any], embeddings: Optional[List[np.ndarray]] = None
    ) -> None:
        """Mock implementation of add_documents."""
        pass
    
    async def get_similar(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.0,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Mock implementation of get_similar."""
        return []
    
    async def clear(self) -> None:
        """Mock implementation of clear."""
        pass


class TestQdrantVectorStoreScores:
    """Test that QdrantVectorStore properly handles and returns similarity scores."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        mock_client = Mock()
        # Mock get_collections to return empty list
        mock_client.get_collections.return_value.collections = []
        return mock_client
    
    @pytest.fixture
    def qdrant_store(self, mock_qdrant_client):
        """Create a QdrantVectorStore instance with mocked client."""
        # Mock the conditional import check and permissions
        with patch('biomapper.embedder.storage.qdrant_store.HAS_QDRANT', True), \
             patch('os.makedirs'):
            # Create store instance
            store = TestableQdrantVectorStore(
                collection_name="test_collection",
                dimension=384,
                url="http://localhost:6333"
            )
            # Replace the client with our mock after initialization
            store.client = mock_qdrant_client
            return store
    
    def test_search_returns_similarity_scores(self, qdrant_store, mock_qdrant_client):
        """Test that search method returns similarity scores from Qdrant."""
        # Create mock search results with scores
        mock_results = []
        for i in range(3):
            mock_result = Mock()
            mock_result.id = f"test_id_{i}"
            mock_result.score = 0.95 - (i * 0.1)  # Decreasing scores
            mock_result.payload = {
                "metadata": {
                    "id": f"compound_{i}",
                    "name": f"Test Compound {i}",
                    "cid": f"12345{i}"
                }
            }
            mock_results.append(mock_result)
        
        mock_qdrant_client.search.return_value = mock_results
        
        # Perform search
        query_vector = np.random.rand(384)
        results = qdrant_store.search(query_vector, k=3)
        
        # Verify results contain similarity scores
        assert len(results) == 3
        
        # Check each result has proper structure with similarity score
        for i, result in enumerate(results):
            assert "id" in result
            assert "similarity" in result
            assert "metadata" in result
            
            # Verify similarity score matches what we set
            expected_score = 0.95 - (i * 0.1)
            assert result["similarity"] == expected_score
            assert isinstance(result["similarity"], float)
            
            # Verify metadata is preserved
            assert result["metadata"]["cid"] == f"12345{i}"
    
    def test_search_with_no_results(self, qdrant_store, mock_qdrant_client):
        """Test search behavior when no results are found."""
        mock_qdrant_client.search.return_value = []
        
        query_vector = np.random.rand(384)
        results = qdrant_store.search(query_vector, k=5)
        
        assert results == []
    
    def test_filter_search_returns_scores(self, qdrant_store, mock_qdrant_client):
        """Test that filter_search also returns similarity scores."""
        # Create mock filtered search results
        mock_results = []
        mock_result = Mock()
        mock_result.id = "filtered_id"
        mock_result.score = 0.88
        mock_result.payload = {
            "metadata": {
                "id": "filtered_compound",
                "category": "metabolite",
                "cid": "98765"
            }
        }
        mock_results.append(mock_result)
        
        mock_qdrant_client.search.return_value = mock_results
        
        # Perform filtered search
        query_vector = np.random.rand(384)
        filter_conditions = {"category": "metabolite"}
        results = qdrant_store.filter_search(query_vector, filter_conditions, k=5)
        
        # Verify results
        assert len(results) == 1
        assert results[0]["similarity"] == 0.88
        assert isinstance(results[0]["similarity"], float)
        assert results[0]["metadata"]["cid"] == "98765"
    
    def test_search_score_types(self, qdrant_store, mock_qdrant_client):
        """Test that scores are properly converted to float type."""
        # Create result with integer score (edge case)
        mock_result = Mock()
        mock_result.id = "test_id"
        mock_result.score = 1  # Integer score
        mock_result.payload = {"metadata": {"id": "test"}}
        
        mock_qdrant_client.search.return_value = [mock_result]
        
        query_vector = np.random.rand(384)
        results = qdrant_store.search(query_vector, k=1)
        
        # Verify score is converted to float
        assert len(results) == 1
        assert isinstance(results[0]["similarity"], float)
        assert results[0]["similarity"] == 1.0
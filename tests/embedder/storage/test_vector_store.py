"""Unit tests for FAISSVectorStore implementation."""

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from biomapper.embedder.storage.vector_store import FAISSVectorStore


class TestFAISSVectorStore:
    """Test suite for FAISSVectorStore."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def sample_embeddings(self):
        """Generate sample embeddings for testing."""
        np.random.seed(42)
        embeddings = np.random.randn(5, 384).astype(np.float32)
        ids = [f"item_{i}" for i in range(5)]
        metadata = [{"name": f"Item {i}", "category": "test"} for i in range(5)]
        return embeddings, ids, metadata
    
    def test_init_default(self):
        """Test default initialization."""
        store = FAISSVectorStore()
        assert store.dimension == 384
        assert store.normalize is True
        assert store.index_type == "Flat"
        assert store.metric == "L2"
        assert store.get_size() == 0
    
    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        store = FAISSVectorStore(
            dimension=512,
            normalize=False,
            index_type="HNSW",
            metric="IP"
        )
        assert store.dimension == 512
        assert store.normalize is False
        assert store.index_type == "HNSW"
        assert store.metric == "IP"
    
    def test_add_embeddings_basic(self, sample_embeddings):
        """Test adding embeddings to the store."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        
        returned_ids = store.add_embeddings(embeddings, ids, metadata)
        
        assert returned_ids == ids
        assert store.get_size() == 5
        assert len(store.metadata) == 5
        assert all(id in store.id_to_index for id in ids)
    
    def test_add_embeddings_without_metadata(self, sample_embeddings):
        """Test adding embeddings without metadata."""
        embeddings, ids, _ = sample_embeddings
        store = FAISSVectorStore()
        
        returned_ids = store.add_embeddings(embeddings, ids)
        
        assert returned_ids == ids
        assert store.get_size() == 5
    
    def test_add_embeddings_validation(self):
        """Test input validation for add_embeddings."""
        store = FAISSVectorStore(dimension=10)
        
        # Wrong dimension
        with pytest.raises(ValueError, match="Embedding dimension"):
            store.add_embeddings(np.ones((2, 5)), ["id1", "id2"])
        
        # Mismatched IDs
        with pytest.raises(ValueError, match="Number of embeddings must match"):
            store.add_embeddings(np.ones((2, 10)), ["id1"])
        
        # Mismatched metadata
        with pytest.raises(ValueError, match="Number of metadata entries"):
            store.add_embeddings(np.ones((2, 10)), ["id1", "id2"], [{}])
    
    def test_search_basic(self, sample_embeddings):
        """Test basic similarity search."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        # Search with the first embedding
        query = embeddings[0]
        results = store.search(query, k=3)
        
        assert len(results) == 3
        assert results[0][0] == "item_0"  # Should find itself first
        assert results[0][1] > 0.99  # High similarity for exact match
        assert all(isinstance(r[2], dict) for r in results)
    
    def test_search_empty_store(self):
        """Test searching in an empty store."""
        store = FAISSVectorStore()
        query = np.random.randn(384)
        
        results = store.search(query, k=5)
        assert results == []
    
    def test_search_with_filter(self, sample_embeddings):
        """Test search with filter function."""
        embeddings, ids, _ = sample_embeddings
        # Create metadata with different categories
        metadata = [
            {"category": "A" if i % 2 == 0 else "B"} 
            for i in range(len(ids))
        ]
        
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        # Search only for category A items
        query = embeddings[0]
        results = store.search(
            query, 
            k=5, 
            filter_func=lambda m: m.get("category") == "A"
        )
        
        # Should only return items with category A (indices 0, 2, 4)
        assert len(results) <= 3
        assert all(r[2]["category"] == "A" for r in results)
    
    def test_get_embedding(self, sample_embeddings):
        """Test retrieving individual embeddings."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        # Retrieve existing embedding
        retrieved = store.get_embedding("item_2")
        assert retrieved is not None
        assert retrieved.shape == (384,)
        
        # Try non-existent ID
        assert store.get_embedding("non_existent") is None
    
    def test_save_and_load(self, temp_dir, sample_embeddings):
        """Test saving and loading the vector store."""
        embeddings, ids, metadata = sample_embeddings
        index_path = os.path.join(temp_dir, "test.faiss")
        metadata_path = os.path.join(temp_dir, "test.meta")
        
        # Create and save store
        store1 = FAISSVectorStore(
            index_path=index_path,
            metadata_path=metadata_path,
            dimension=384,
            normalize=True,
            index_type="Flat",
            metric="L2"
        )
        store1.add_embeddings(embeddings, ids, metadata)
        
        # Load into new store
        store2 = FAISSVectorStore(
            index_path=index_path,
            metadata_path=metadata_path
        )
        
        # Verify loaded store
        assert store2.get_size() == 5
        assert store2.dimension == 384
        assert store2.normalize is True
        assert store2.index_type == "Flat"
        assert store2.metric == "L2"
        
        # Test search on loaded store
        results = store2.search(embeddings[0], k=3)
        assert len(results) == 3
        assert results[0][0] == "item_0"
    
    def test_save_without_metadata_path(self, temp_dir, sample_embeddings):
        """Test saving with auto-generated metadata path."""
        embeddings, ids, metadata = sample_embeddings
        index_path = os.path.join(temp_dir, "test.faiss")
        
        store = FAISSVectorStore(index_path=index_path)
        store.add_embeddings(embeddings, ids, metadata)
        
        # Check that metadata file was created
        expected_meta_path = os.path.join(temp_dir, "test.meta")
        assert os.path.exists(expected_meta_path)
    
    def test_clear(self, sample_embeddings):
        """Test clearing the vector store."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        assert store.get_size() == 5
        
        store.clear()
        
        assert store.get_size() == 0
        assert len(store.metadata) == 0
        assert len(store.id_to_index) == 0
    
    def test_normalize_embeddings(self):
        """Test embedding normalization."""
        store = FAISSVectorStore(dimension=3, normalize=True)
        
        # Create embeddings with different norms
        embeddings = np.array([
            [3.0, 4.0, 0.0],  # norm = 5
            [1.0, 0.0, 0.0],  # norm = 1
            [1.0, 1.0, 1.0]   # norm = sqrt(3)
        ], dtype=np.float32)
        ids = ["a", "b", "c"]
        
        store.add_embeddings(embeddings, ids)
        
        # Retrieve and check normalization
        for id in ids:
            emb = store.get_embedding(id)
            norm = np.linalg.norm(emb)
            np.testing.assert_almost_equal(norm, 1.0, decimal=5)
    
    def test_ivf_index_type(self, sample_embeddings):
        """Test IVFFlat index type (requires training)."""
        store = FAISSVectorStore(dimension=384, index_type="IVFFlat")
        
        # Need enough data to train IVF index
        np.random.seed(42)
        embeddings = np.random.randn(100, 384).astype(np.float32)
        ids = [f"item_{i}" for i in range(100)]
        
        store.add_embeddings(embeddings, ids)
        assert store.get_size() == 100
        
        # Test search
        results = store.search(embeddings[0], k=5)
        assert len(results) == 5
        assert results[0][0] == "item_0"
    
    def test_inner_product_metric(self):
        """Test inner product similarity metric."""
        store = FAISSVectorStore(dimension=3, metric="IP", normalize=False)
        
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0]
        ], dtype=np.float32)
        ids = ["x", "y", "xy"]
        
        store.add_embeddings(embeddings, ids)
        
        # Query with [1, 1, 0] should rank "xy" highest
        query = np.array([1.0, 1.0, 0.0], dtype=np.float32)
        results = store.search(query, k=3)
        
        assert results[0][0] == "xy"  # Highest inner product
        assert results[0][1] == 2.0    # Inner product value
    
    def test_repr(self, sample_embeddings):
        """Test string representation."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        repr_str = repr(store)
        assert "FAISSVectorStore" in repr_str
        assert "dimension=384" in repr_str
        assert "size=5" in repr_str
    
    def test_len(self, sample_embeddings):
        """Test __len__ method."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore()
        
        assert len(store) == 0
        
        store.add_embeddings(embeddings, ids, metadata)
        assert len(store) == 5
    
    def test_persistence_with_different_paths(self, temp_dir, sample_embeddings):
        """Test save/load with different paths."""
        embeddings, ids, metadata = sample_embeddings
        
        # Create store without initial paths
        store = FAISSVectorStore()
        store.add_embeddings(embeddings, ids, metadata)
        
        # Save to specific paths
        index_path = os.path.join(temp_dir, "custom.faiss")
        meta_path = os.path.join(temp_dir, "custom.json")
        store.save(index_path, meta_path)
        
        # Load from those paths
        new_store = FAISSVectorStore()
        new_store.load(index_path, meta_path)
        
        assert new_store.get_size() == 5
        assert new_store.search(embeddings[0], k=1)[0][0] == "item_0"
    
    def test_dimension_mismatch_on_search(self, sample_embeddings):
        """Test error handling for dimension mismatch during search."""
        embeddings, ids, metadata = sample_embeddings
        store = FAISSVectorStore(dimension=384)
        store.add_embeddings(embeddings, ids, metadata)
        
        # Try searching with wrong dimension
        wrong_query = np.random.randn(256)
        with pytest.raises(ValueError, match="Query dimension"):
            store.search(wrong_query)
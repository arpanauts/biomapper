"""FAISS-based vector storage implementation for the Biomapper Embedder module."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """Local file-based storage using Facebook AI Similarity Search (FAISS).
    
    This implementation provides efficient similarity search for vector embeddings
    using the FAISS library. It supports various index types and persistence.
    """
    
    def __init__(
        self,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        dimension: int = 384,
        normalize: bool = True,
        index_type: str = "Flat",
        metric: str = "L2"
    ):
        """Initialize the FAISS vector store.
        
        Args:
            index_path: Path to save/load the FAISS index
            metadata_path: Path to save/load the metadata
            dimension: Dimension of the embeddings
            normalize: Whether to normalize embeddings
            index_type: Type of FAISS index ("Flat", "IVFFlat", "HNSW")
            metric: Distance metric ("L2" or "IP" for inner product)
        """
        self.index_path = index_path
        self.metadata_path = metadata_path or (
            str(Path(index_path).with_suffix('.meta')) if index_path else None
        )
        self.dimension = dimension
        self.normalize = normalize
        self.index_type = index_type
        self.metric = metric
        
        # Initialize or load the index
        if index_path and os.path.exists(index_path):
            self._load()
        else:
            self._initialize_index()
            self.metadata: Dict[str, Dict[str, Any]] = {}
            self.id_to_index: Dict[str, int] = {}
            self.index_to_id: Dict[int, str] = {}
            self._embeddings_cache: Dict[str, np.ndarray] = {}
        
        logger.info(
            f"Initialized FAISSVectorStore with dimension={dimension}, "
            f"index_type={index_type}, metric={metric}"
        )
    
    def _initialize_index(self):
        """Initialize a new FAISS index based on the specified type."""
        if self.metric == "L2":
            base_index = faiss.IndexFlatL2(self.dimension)
        elif self.metric == "IP":
            base_index = faiss.IndexFlatIP(self.dimension)
        else:
            raise ValueError(f"Unsupported metric: {self.metric}")
        
        if self.index_type == "Flat":
            self.index = base_index
        elif self.index_type == "IVFFlat":
            # For IVF, we need to train with some data first
            # Using a smaller number of centroids for initialization
            nlist = min(100, self.dimension // 4)
            self.index = faiss.IndexIVFFlat(base_index, self.dimension, nlist)
            self._is_trained = False
        elif self.index_type == "HNSW":
            # HNSW is a graph-based index for fast approximate search
            M = 32  # Number of connections per vertex
            self.index = faiss.IndexHNSWFlat(self.dimension, M)
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")
        
        # Add ID mapping support
        self.index = faiss.IndexIDMap(self.index)
    
    def add_embeddings(
        self, 
        embeddings: np.ndarray, 
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Add embeddings with metadata to the store.
        
        Args:
            embeddings: Array of embeddings to add (shape: [n_samples, dimension])
            ids: List of unique identifiers for each embedding
            metadata: Optional list of metadata dictionaries for each embedding
            
        Returns:
            List of IDs for the added items
        """
        # Ensure embeddings are float32 (required by FAISS)
        embeddings = embeddings.astype(np.float32)
        
        # Validate inputs
        if embeddings.shape[0] != len(ids):
            raise ValueError("Number of embeddings must match number of IDs")
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} does not match "
                f"expected dimension {self.dimension}"
            )
        
        if metadata and len(metadata) != len(ids):
            raise ValueError("Number of metadata entries must match number of IDs")
        
        # Normalize if requested
        if self.normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-10)  # Avoid division by zero
        
        # Train IVF index if needed
        if hasattr(self, '_is_trained') and not self._is_trained:
            if self.index.ntotal + len(embeddings) >= 100:  # Need enough data to train
                logger.info("Training IVF index...")
                self.index.train(embeddings)
                self._is_trained = True
            else:
                logger.warning(
                    "Not enough data to train IVF index yet. "
                    "Will train when more data is available."
                )
                return ids
        
        # Generate integer IDs for FAISS
        start_idx = len(self.id_to_index)
        int_ids = np.arange(start_idx, start_idx + len(ids), dtype=np.int64)
        
        # Add to index
        try:
            self.index.add_with_ids(embeddings, int_ids)
        except Exception as e:
            logger.error(f"Failed to add embeddings to FAISS index: {e}")
            raise
        
        # Update mappings and cache embeddings
        for i, (str_id, int_id) in enumerate(zip(ids, int_ids)):
            self.id_to_index[str_id] = int(int_id)
            self.index_to_id[int(int_id)] = str_id
            self._embeddings_cache[str_id] = embeddings[i].copy()
            
            if metadata:
                if str_id not in self.metadata:
                    self.metadata[str_id] = {}
                self.metadata[str_id].update(metadata[i])
        
        # Save if paths are specified
        if self.index_path:
            self.save()
        
        logger.info(f"Added {len(ids)} embeddings to the vector store")
        return ids
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter_func: Optional[callable] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors.
        
        Args:
            query_embedding: Query embedding (1D array)
            k: Number of results to return
            filter_func: Optional function to filter results based on metadata
            
        Returns:
            List of tuples (id, distance/similarity, metadata)
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Ensure query is 2D and float32
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)
        
        if query_embedding.shape[1] != self.dimension:
            raise ValueError(
                f"Query dimension {query_embedding.shape[1]} does not match "
                f"expected dimension {self.dimension}"
            )
        
        # Normalize if requested
        if self.normalize:
            norm = np.linalg.norm(query_embedding)
            if norm > 0:
                query_embedding = query_embedding / norm
        
        # Search for more than k results if filtering is needed
        search_k = min(k * 10 if filter_func else k, self.index.ntotal)
        
        # For IVF indexes, set nprobe to search more clusters for better recall
        original_nprobe = None
        if self.index_type == "IVFFlat" and hasattr(self.index.index, 'nprobe'):
            original_nprobe = self.index.index.nprobe
            # Set nprobe to search more clusters, but not more than available
            self.index.index.nprobe = min(
                max(10, search_k // 5),  # At least 10, or roughly 1/5 of search_k
                self.index.index.nlist   # But no more than total clusters
            )
        
        try:
            distances, indices = self.index.search(query_embedding, search_k)
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            raise
        finally:
            # Restore original nprobe value if we changed it
            if original_nprobe is not None:
                self.index.index.nprobe = original_nprobe
        
        # Process results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
                
            str_id = self.index_to_id.get(int(idx))
            if str_id is None:
                logger.warning(f"No ID mapping found for index {idx}")
                continue
            
            meta = self.metadata.get(str_id, {})
            
            # Apply filter if provided
            if filter_func is None or filter_func(meta):
                # Convert L2 distance to similarity score if using L2 metric
                score = float(dist) if self.metric == "IP" else 1.0 / (1.0 + float(dist))
                results.append((str_id, score, meta))
                
                if len(results) >= k:
                    break
        
        return results
    
    def get_embedding(self, id: str) -> Optional[np.ndarray]:
        """Retrieve the embedding for a given ID.
        
        Args:
            id: The ID of the embedding to retrieve
            
        Returns:
            The embedding array or None if not found
        """
        # Return from cache if available
        if hasattr(self, '_embeddings_cache') and id in self._embeddings_cache:
            return self._embeddings_cache[id].copy()
        
        # Otherwise, log warning as reconstruction is not supported with IndexIDMap
        logger.warning(f"Embedding for ID {id} not found in cache")
        return None
    
    def get_size(self) -> int:
        """Get the total number of vectors in the store."""
        return self.index.ntotal
    
    def save(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """Save the index and metadata to disk.
        
        Args:
            index_path: Optional path to save the index (uses self.index_path if not provided)
            metadata_path: Optional path to save metadata (uses self.metadata_path if not provided)
        """
        index_path = index_path or self.index_path
        metadata_path = metadata_path or self.metadata_path
        
        if not index_path:
            raise ValueError("No index path specified for saving")
        
        # Create directory if needed
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # Save FAISS index
        try:
            faiss.write_index(self.index, index_path)
            logger.info(f"Saved FAISS index to {index_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            raise
        
        # Save metadata
        if metadata_path:
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            meta_data = {
                'metadata': self.metadata,
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id,
                'dimension': self.dimension,
                'normalize': self.normalize,
                'index_type': self.index_type,
                'metric': self.metric,
                'embeddings_cache': {k: v.tolist() for k, v in getattr(self, '_embeddings_cache', {}).items()}
            }
            
            try:
                with open(metadata_path, 'w') as f:
                    json.dump(meta_data, f, indent=2)
                logger.info(f"Saved metadata to {metadata_path}")
            except Exception as e:
                logger.error(f"Failed to save metadata: {e}")
                raise
    
    def load(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """Load the index and metadata from disk.
        
        Args:
            index_path: Optional path to load the index from
            metadata_path: Optional path to load metadata from
        """
        self._load(index_path, metadata_path)
    
    def _load(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """Internal method to load the index and metadata."""
        index_path = index_path or self.index_path
        metadata_path = metadata_path or self.metadata_path
        
        if not index_path or not os.path.exists(index_path):
            raise ValueError(f"Index file not found: {index_path}")
        
        # Load FAISS index
        try:
            self.index = faiss.read_index(index_path)
            logger.info(f"Loaded FAISS index from {index_path}")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise
        
        # Load metadata
        if metadata_path and os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    meta_data = json.load(f)
                
                self.metadata = meta_data.get('metadata', {})
                self.id_to_index = meta_data.get('id_to_index', {})
                # Convert string keys back to int for index_to_id
                self.index_to_id = {
                    int(k): v for k, v in meta_data.get('index_to_id', {}).items()
                }
                
                # Update configuration from saved metadata
                self.dimension = meta_data.get('dimension', self.dimension)
                self.normalize = meta_data.get('normalize', self.normalize)
                self.index_type = meta_data.get('index_type', self.index_type)
                self.metric = meta_data.get('metric', self.metric)
                
                # Load embeddings cache
                embeddings_cache_data = meta_data.get('embeddings_cache', {})
                self._embeddings_cache = {
                    k: np.array(v, dtype=np.float32) for k, v in embeddings_cache_data.items()
                }
                
                logger.info(f"Loaded metadata from {metadata_path}")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                raise
        else:
            logger.warning(f"Metadata file not found: {metadata_path}")
            self.metadata = {}
            self.id_to_index = {}
            self.index_to_id = {}
            self._embeddings_cache = {}
    
    def clear(self):
        """Clear all data from the vector store."""
        self._initialize_index()
        self.metadata.clear()
        self.id_to_index.clear()
        self.index_to_id.clear()
        if hasattr(self, '_embeddings_cache'):
            self._embeddings_cache.clear()
        logger.info("Cleared all data from vector store")
    
    def __len__(self) -> int:
        """Return the number of vectors in the store."""
        return self.get_size()
    
    def __repr__(self) -> str:
        """String representation of the vector store."""
        return (
            f"FAISSVectorStore(dimension={self.dimension}, "
            f"index_type={self.index_type}, metric={self.metric}, "
            f"size={self.get_size()})"
        )
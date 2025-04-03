"""Vector storage implementations."""

import os
import json
import logging
import threading
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple

from ..core.base import BaseVectorStore
from ..core.config import default_config

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logging.warning("faiss-cpu package not found. FAISSVectorStore will not work correctly.")


class FAISSVectorStore(BaseVectorStore):
    """Vector store implementation using FAISS."""
    
    def __init__(
        self, 
        dimension: Optional[int] = None,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        normalize: bool = True
    ):
        """Initialize the FAISS vector store.
        
        Args:
            dimension: Embedding dimension
            index_path: Path to load/save the index
            metadata_path: Path to load/save metadata
            normalize: Whether to normalize vectors before adding to the index
        """
        self.dimension = dimension or default_config.embedding_dimension
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.normalize = normalize
        
        # Add a lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize the index and metadata
        self._initialize()
    
    def _initialize(self):
        """Initialize or load index and metadata."""
        if not HAS_FAISS:
            logging.error("FAISS is not available. Please install faiss-cpu or faiss-gpu.")
            self.index = None
            self.metadata = {}
            self.id_to_index = {}
            return
            
        try:
            # Initialize metadata
            self.metadata = {}
            self.id_to_index = {}
            
            # Try to load existing index
            if self.index_path and os.path.exists(self.index_path):
                logging.info(f"Loading FAISS index from {self.index_path}")
                self.index = faiss.read_index(self.index_path)
                
                # Load metadata if available
                if self.metadata_path and os.path.exists(self.metadata_path):
                    logging.info(f"Loading metadata from {self.metadata_path}")
                    with open(self.metadata_path, 'r') as f:
                        self.metadata = json.load(f)
                        
                    # Rebuild id_to_index mapping
                    self.id_to_index = {id: idx for idx, id in enumerate(self.metadata.keys())}
                    
                    logging.info(f"Loaded {len(self.metadata)} items from metadata")
                else:
                    logging.warning("Index loaded but metadata file not found")
            else:
                # Create a new index
                logging.info(f"Creating new FAISS index with dimension {self.dimension}")
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                
                # Create directories for paths if provided
                if self.index_path:
                    os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
                if self.metadata_path:
                    os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
                    
                logging.info("New FAISS index created")
                
        except Exception as e:
            logging.error(f"Error initializing FAISS index: {str(e)}")
            # Create a backup in-memory index if loading fails
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = {}
            self.id_to_index = {}
    
    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> List[str]:
        """Add embeddings with metadata to the store.
        
        Args:
            embeddings: Array of embeddings with shape (n_embeddings, embedding_dim)
            metadata: List of metadata dictionaries, one per embedding
            
        Returns:
            List of IDs for the added embeddings
        """
        if not HAS_FAISS or self.index is None:
            logging.error("FAISS is not available. Cannot add embeddings.")
            return []
            
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings and metadata must match")
            
        if len(embeddings) == 0:
            logging.warning("Empty embeddings list provided")
            return []
            
        # Ensure embeddings have the right shape
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}")
        
        # Thread safety
        with self.lock:
            try:
                # Normalize embeddings for cosine similarity if requested
                if self.normalize:
                    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
                
                # Get current index size
                start_idx = self.index.ntotal
                
                # Add to index
                self.index.add(embeddings)
                
                # Generate IDs and store metadata
                ids = []
                for i, meta in enumerate(metadata):
                    # Use provided ID or generate one
                    id = meta.get('id', f"item_{start_idx + i}")
                    
                    # Store metadata
                    self.metadata[id] = meta
                    
                    # Update mapping
                    self.id_to_index[id] = start_idx + i
                    
                    ids.append(id)
                
                # Save if paths are specified
                self._save_index_and_metadata()
                    
                return ids
                
            except Exception as e:
                logging.error(f"Error adding embeddings to index: {str(e)}")
                return []
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: Query embedding
            k: Number of results to return
            
        Returns:
            List of dictionaries with search results including 'id', 'similarity' and 'metadata'
        """
        if not HAS_FAISS or self.index is None:
            logging.error("FAISS is not available. Cannot search.")
            return []
            
        if self.index.ntotal == 0:
            logging.warning("Empty index, no results to return")
            return []
            
        with self.lock:
            try:
                # Ensure query has the right shape
                if query_vector.ndim == 1:
                    query_vector = query_vector.reshape(1, -1)
                
                # Ensure dimension matches
                if query_vector.shape[1] != self.dimension:
                    raise ValueError(f"Query dimension mismatch: expected {self.dimension}, got {query_vector.shape[1]}")
                
                # Normalize the query for cosine similarity if needed
                if self.normalize:
                    query_vector = query_vector / np.linalg.norm(query_vector)
                
                # Limit k to the number of items in the index
                k = min(k, self.index.ntotal)
                
                # Search
                distances, indices = self.index.search(query_vector, k)
                
                # Get metadata and prepare results
                results = []
                for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx >= 0 and idx < self.index.ntotal:
                        # Find the ID for this index
                        id = next((id for id, index in self.id_to_index.items() if index == idx), None)
                        if id and id in self.metadata:
                            result = {
                                "id": id,
                                "similarity": float(distance),
                                "metadata": self.metadata[id]
                            }
                            results.append(result)
                
                return results
                
            except Exception as e:
                logging.error(f"Error searching index: {str(e)}")
                return []
    
    def delete(self, ids: List[str]) -> bool:
        """Delete embeddings by ID.
        
        Note: FAISS doesn't support direct deletion, so this actually
        just removes the metadata. The vectors remain in the index
        but will not be returned in search results.
        
        Args:
            ids: List of embedding IDs to delete
            
        Returns:
            True if deletion was successful
        """
        if not ids:
            return True
            
        with self.lock:
            try:
                for id in ids:
                    if id in self.metadata:
                        del self.metadata[id]
                        
                    if id in self.id_to_index:
                        del self.id_to_index[id]
                
                # Save metadata changes
                self._save_index_and_metadata()
                    
                return True
                
            except Exception as e:
                logging.error(f"Error deleting IDs: {str(e)}")
                return False
    
    def _save_index_and_metadata(self):
        """Save the index and metadata to disk if paths are specified."""
        # Skip if no paths specified
        if not self.index_path and not self.metadata_path:
            return
            
        try:
            # Save index
            if self.index_path:
                # Create temp file for atomic write
                temp_index_path = f"{self.index_path}.temp"
                
                # Write to temp file
                faiss.write_index(self.index, temp_index_path)
                
                # Atomic rename
                os.replace(temp_index_path, self.index_path)
                logging.debug(f"Saved index to {self.index_path}")
            
            # Save metadata
            if self.metadata_path:
                # Create temp file for atomic write
                temp_metadata_path = f"{self.metadata_path}.temp"
                
                # Write to temp file
                with open(temp_metadata_path, 'w') as f:
                    json.dump(self.metadata, f)
                
                # Atomic rename
                os.replace(temp_metadata_path, self.metadata_path)
                logging.debug(f"Saved metadata to {self.metadata_path}")
                
        except Exception as e:
            logging.error(f"Error saving index and metadata: {str(e)}")
    
    def get_total_count(self) -> int:
        """Get the total number of vectors in the index.
        
        Returns:
            Number of vectors in the index
        """
        if not HAS_FAISS or self.index is None:
            return 0
            
        return self.index.ntotal

"""Qdrant vector storage implementation."""

import os
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import numpy as np
from pathlib import Path

from ..core.base import BaseVectorStore
from ..core.config import default_config

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    logging.warning("qdrant-client package not found. QdrantVectorStore will not work correctly.")


class QdrantVectorStore(BaseVectorStore):
    """Vector store implementation using Qdrant.
    
    This implementation provides persistent storage of vector embeddings with 
    full-featured filtering, collections, and cloud deployment options.
    
    Qdrant supports both local on-disk and remote server modes.
    """
    
    def __init__(
        self, 
        collection_name: str,
        dimension: Optional[int] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        local_path: Optional[str] = None,
        normalize: bool = True,
        distance: str = "Cosine",
        metadata_payload_key: str = "metadata"
    ):
        """Initialize the Qdrant vector store.
        
        Args:
            collection_name: Name of the Qdrant collection
            dimension: Embedding dimension
            url: URL for the Qdrant server (e.g., 'http://localhost:6333')
            api_key: API key for Qdrant cloud
            local_path: Path for local Qdrant storage (alternative to url)
            normalize: Whether to normalize vectors before adding to the index
            distance: Distance metric to use ('Cosine', 'Euclid', or 'Dot')
            metadata_payload_key: Key to use for storing metadata in Qdrant
        """
        self.collection_name = collection_name
        self.dimension = dimension or default_config.embedding_dimension
        self.url = url
        self.api_key = api_key
        self.local_path = local_path
        self.normalize = normalize
        self.distance = distance
        self.metadata_payload_key = metadata_payload_key
        
        # Add a lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize the client and collection
        self._initialize()
    
    def _initialize(self):
        """Initialize or connect to Qdrant client and collection."""
        if not HAS_QDRANT:
            logging.error("Qdrant client is not available. Please install qdrant-client.")
            self.client = None
            return
            
        try:
            # Initialize client based on connection type
            if self.url:
                # Connect to remote Qdrant server
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key
                )
                logging.info(f"Connected to Qdrant server at {self.url}")
            else:
                # Use local storage
                storage_path = self.local_path or os.path.join(
                    default_config.storage_dir, 
                    "qdrant"
                )
                os.makedirs(storage_path, exist_ok=True)
                
                self.client = QdrantClient(
                    path=storage_path
                )
                logging.info(f"Connected to local Qdrant storage at {storage_path}")
            
            # Check if collection exists, create it if not
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Map distance string to Qdrant distance enum
                distance_map = {
                    "Cosine": models.Distance.COSINE,
                    "Euclid": models.Distance.EUCLID,
                    "Dot": models.Distance.DOT,
                }
                distance = distance_map.get(self.distance, models.Distance.COSINE)
                
                # Create new collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.dimension,
                        distance=distance
                    )
                )
                logging.info(f"Created new Qdrant collection '{self.collection_name}'")
                
        except Exception as e:
            logging.error(f"Error initializing Qdrant client: {str(e)}")
            self.client = None
    
    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> List[str]:
        """Add embeddings with metadata to the store.
        
        Args:
            embeddings: Array of embeddings with shape (n_embeddings, embedding_dim)
            metadata: List of metadata dictionaries, one per embedding
            
        Returns:
            List of IDs for the added embeddings
        """
        if not HAS_QDRANT or self.client is None:
            logging.error("Qdrant client is not available. Cannot add embeddings.")
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
                
                # Prepare points for batch upload
                points = []
                ids = []
                
                for i, (embedding, meta) in enumerate(zip(embeddings, metadata)):
                    # Use provided ID or generate one
                    if 'id' in meta:
                        id_value = meta['id']
                    else:
                        id_value = f"item_{len(ids) + 1}"
                        meta['id'] = id_value
                    
                    # Add ID to return list
                    ids.append(id_value)
                    
                    # Convert ID to string (Qdrant supports string IDs)
                    point_id = str(id_value)
                    
                    # Create Qdrant point
                    point = models.PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            self.metadata_payload_key: meta,
                        }
                    )
                    points.append(point)
                
                # Upload points in batch
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logging.info(f"Added {len(points)} embeddings to Qdrant collection '{self.collection_name}'")
                return ids
                
            except Exception as e:
                logging.error(f"Error adding embeddings to Qdrant: {str(e)}")
                return []
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: Query embedding
            k: Number of results to return
            
        Returns:
            List of dictionaries with search results including 'id', 'similarity' and 'metadata'
        """
        if not HAS_QDRANT or self.client is None:
            logging.error("Qdrant client is not available. Cannot search.")
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
                
                # Convert to list for Qdrant
                query_vector_list = query_vector[0].tolist()
                
                # Search the collection
                search_results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector_list,
                    limit=k,
                    with_payload=True
                )
                
                # Format results to match our API
                results = []
                for result in search_results:
                    # Extract metadata from payload
                    metadata = result.payload.get(self.metadata_payload_key, {})
                    
                    # Create result entry
                    entry = {
                        "id": metadata.get("id", result.id),
                        "similarity": float(result.score),
                        "metadata": metadata
                    }
                    results.append(entry)
                
                return results
                
            except Exception as e:
                logging.error(f"Error searching Qdrant: {str(e)}")
                return []
    
    def delete(self, ids: List[str]) -> bool:
        """Delete embeddings by ID.
        
        Args:
            ids: List of embedding IDs to delete
            
        Returns:
            True if deletion was successful
        """
        if not HAS_QDRANT or self.client is None:
            logging.error("Qdrant client is not available. Cannot delete embeddings.")
            return False
            
        if not ids:
            return True
            
        with self.lock:
            try:
                # Convert IDs to strings for Qdrant
                string_ids = [str(id) for id in ids]
                
                # Delete points by ID
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=string_ids
                    )
                )
                
                logging.info(f"Deleted {len(ids)} embeddings from Qdrant collection '{self.collection_name}'")
                return True
                
            except Exception as e:
                logging.error(f"Error deleting embeddings from Qdrant: {str(e)}")
                return False
    
    def get_total_count(self) -> int:
        """Get the total number of vectors in the collection.
        
        Returns:
            Number of vectors in the collection
        """
        if not HAS_QDRANT or self.client is None:
            return 0
            
        try:
            # Get collection info
            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )
            
            # Return vector count
            return collection_info.vectors_count
            
        except Exception as e:
            logging.error(f"Error getting vector count from Qdrant: {str(e)}")
            return 0
            
    def filter_search(
        self, 
        query_vector: np.ndarray,
        filter_conditions: Dict[str, Any],
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search with metadata filtering.
        
        Args:
            query_vector: Query embedding
            filter_conditions: Dictionary of filter conditions
            k: Number of results to return
            
        Returns:
            List of dictionaries with search results
        """
        if not HAS_QDRANT or self.client is None:
            logging.error("Qdrant client is not available. Cannot search.")
            return []
            
        with self.lock:
            try:
                # Ensure query has the right shape
                if query_vector.ndim == 1:
                    query_vector = query_vector.reshape(1, -1)
                
                # Normalize if needed
                if self.normalize:
                    query_vector = query_vector / np.linalg.norm(query_vector)
                
                # Convert to list for Qdrant
                query_vector_list = query_vector[0].tolist()
                
                # Build filter from conditions
                filter_parts = []
                for key, value in filter_conditions.items():
                    # Create path to nested field in metadata
                    field_path = f"{self.metadata_payload_key}.{key}"
                    
                    # Handle different value types
                    if isinstance(value, list):
                        # Filter for any value in the list
                        filter_parts.append(
                            models.FieldCondition(
                                key=field_path,
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        # Exact match filter
                        filter_parts.append(
                            models.FieldCondition(
                                key=field_path,
                                match=models.MatchValue(value=value)
                            )
                        )
                
                # Combine filters with AND logic
                if filter_parts:
                    filter_condition = models.Filter(
                        must=filter_parts
                    )
                else:
                    filter_condition = None
                
                # Search with filter
                search_results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector_list,
                    limit=k,
                    with_payload=True,
                    filter=filter_condition
                )
                
                # Format results
                results = []
                for result in search_results:
                    metadata = result.payload.get(self.metadata_payload_key, {})
                    entry = {
                        "id": metadata.get("id", result.id),
                        "similarity": float(result.score),
                        "metadata": metadata
                    }
                    results.append(entry)
                
                return results
                
            except Exception as e:
                logging.error(f"Error searching Qdrant with filter: {str(e)}")
                return []
                
    def create_payload_index(self, field: str) -> bool:
        """Create an index on a metadata field for faster filtering.
        
        Args:
            field: Field name in the metadata to index
            
        Returns:
            True if index creation was successful
        """
        if not HAS_QDRANT or self.client is None:
            logging.error("Qdrant client is not available. Cannot create index.")
            return False
            
        try:
            # Create path to nested field in metadata
            field_path = f"{self.metadata_payload_key}.{field}"
            
            # Create the index
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_path,
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            logging.info(f"Created index on field '{field_path}' in collection '{self.collection_name}'")
            return True
            
        except Exception as e:
            logging.error(f"Error creating index on field '{field}': {str(e)}")
            return False

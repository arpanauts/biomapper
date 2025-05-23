"""PubChem RAG Mapping Client for metabolite name resolution using vector search."""

import logging
from typing import List, Optional, Dict, Any, Tuple
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from biomapper.mapping.clients.base_client import BaseMappingClient

logger = logging.getLogger(__name__)


class PubChemRAGMappingClient(BaseMappingClient):
    """
    RAG-based mapping client for PubChem using Qdrant vector search.
    
    This client uses semantic search over PubChem compound embeddings to resolve
    metabolite names to PubChem CIDs. It leverages the pre-filtered biologically
    relevant subset of PubChem compounds indexed in Qdrant.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the PubChem RAG mapping client.
        
        Args:
            config: Configuration dictionary with Qdrant and model settings
        """
        super().__init__(config)
        
        # Configuration with defaults
        self.qdrant_host = self.get_config_value("qdrant_host", "localhost")
        self.qdrant_port = self.get_config_value("qdrant_port", 6333)
        self.collection_name = self.get_config_value("collection_name", "pubchem_bge_small_v1_5")
        self.embedding_model_name = self.get_config_value("embedding_model", "BAAI/bge-small-en-v1.5")
        self.top_k = self.get_config_value("top_k", 5)
        self.score_threshold = self.get_config_value("score_threshold", 0.7)
        
        # Initialize clients
        self.qdrant_client = None
        self.embedding_model = None
        self._initialize_clients()
    
    def get_required_config_keys(self) -> List[str]:
        """Return required configuration keys."""
        return []  # All keys have defaults
    
    def _initialize_clients(self):
        """Initialize Qdrant and embedding model clients."""
        try:
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Verify collection exists
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            logger.info(f"Connected to Qdrant collection '{self.collection_name}' with {collection_info.points_count} points")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PubChem RAG client: {e}")
            raise
    
    async def map_identifiers(
        self, 
        identifiers: List[str], 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map metabolite names to PubChem CIDs using semantic search.
        
        Args:
            identifiers: List of metabolite names to map
            config: Optional per-call configuration
        
        Returns:
            Dictionary mapping input identifiers to (target_identifiers, component_id) tuples
        """
        results = {}
        
        for identifier in identifiers:
            try:
                if not identifier or not identifier.strip():
                    results[identifier] = self.format_result(None, None)
                    continue
                
                # Generate embedding for the query
                query_embedding = self.embedding_model.encode([identifier.strip()])[0]
                
                # Search in Qdrant
                search_results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding.tolist(),
                    limit=self.top_k,
                    score_threshold=self.score_threshold
                )
                
                if search_results:
                    # Extract CIDs from results
                    target_cids = []
                    for result in search_results:
                        cid = result.payload.get("cid")
                        if cid:
                            target_cids.append(f"PUBCHEM:{cid}")
                    
                    if target_cids:
                        results[identifier] = self.format_result(target_cids, None)
                        logger.info(f"Found {len(target_cids)} mappings for '{identifier}' (top score: {search_results[0].score:.3f})")
                    else:
                        results[identifier] = self.format_result(None, None)
                else:
                    results[identifier] = self.format_result(None, None)
                    logger.info(f"No mappings found for '{identifier}'")
                    
            except Exception as e:
                logger.error(f"Error mapping '{identifier}': {e}")
                results[identifier] = self.format_result(None, None)
        
        return results
    
    async def reverse_map_identifiers(
        self, 
        identifiers: List[str], 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Reverse mapping is not supported for RAG-based semantic search.
        """
        raise NotImplementedError("PubChemRAGMappingClient does not support reverse mapping")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RAG system.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Check Qdrant connection
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            # Test embedding model
            test_embedding = self.embedding_model.encode(["test"])
            
            # Perform a test query
            test_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=test_embedding[0].tolist(),
                limit=1
            )
            
            return {
                "status": "healthy",
                "qdrant_connected": True,
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "embedding_model": self.embedding_model_name,
                "test_query_success": len(test_results) > 0
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "qdrant_connected": False
            }
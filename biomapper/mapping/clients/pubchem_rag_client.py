"""PubChem RAG Mapping Client for metabolite name resolution using vector search."""

import logging
from typing import List, Optional, Dict, Any, Tuple
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from biomapper.mapping.clients.base_client import BaseMappingClient
from biomapper.schemas.rag_schema import MappingResultItem, MappingOutput

logger = logging.getLogger(__name__)


class PubChemRAGMappingClient(BaseMappingClient):
    """
    RAG-based mapping client for PubChem using Qdrant vector search.
    
    This client uses semantic search over PubChem compound embeddings to resolve
    metabolite names to PubChem CIDs. It leverages the pre-filtered biologically
    relevant subset of PubChem compounds indexed in Qdrant.
    
    Attributes:
        last_mapping_output: Stores the detailed MappingOutput from the most recent
                           map_identifiers call, including Qdrant similarity scores.
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
        
        # Store detailed mapping results
        self.last_mapping_output: Optional[MappingOutput] = None
    
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
        
        This method performs vector search in Qdrant and captures similarity scores.
        The detailed results including Qdrant similarity scores are stored in 
        self.last_mapping_output.
        
        Args:
            identifiers: List of metabolite names to map
            config: Optional per-call configuration
        
        Returns:
            Dictionary mapping input identifiers to (target_identifiers, component_id) tuples
            Note: The component_id field contains the best similarity score as a string
                  for backward compatibility.
        """
        results = {}
        mapping_result_items = []
        
        for identifier in identifiers:
            try:
                if not identifier or not identifier.strip():
                    results[identifier] = self.format_result(None, None)
                    mapping_result_items.append(
                        MappingResultItem(
                            identifier=identifier,
                            target_ids=None,
                            component_id=None,
                            confidence=None,
                            qdrant_similarity_score=None
                        )
                    )
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
                    # Extract CIDs and scores from results
                    target_cids = []
                    best_score = 0.0
                    scores = []
                    
                    for result in search_results:
                        cid = result.payload.get("cid")
                        if cid:
                            target_cids.append(f"PUBCHEM:{cid}")
                            scores.append(result.score)
                            if result.score > best_score:
                                best_score = result.score
                    
                    if target_cids:
                        # Store best score as string in component_id for backward compatibility
                        results[identifier] = self.format_result(target_cids, str(best_score))
                        
                        # Create detailed result item
                        mapping_result_items.append(
                            MappingResultItem(
                                identifier=identifier,
                                target_ids=target_cids,
                                component_id=str(best_score),
                                confidence=best_score,  # Use best score as confidence
                                qdrant_similarity_score=best_score,
                                metadata={
                                    "all_scores": scores,
                                    "distance_metric": "Cosine",
                                    "score_interpretation": "Higher scores indicate better similarity (cosine distance)"
                                }
                            )
                        )
                        
                        logger.info(f"Found {len(target_cids)} mappings for '{identifier}' (top score: {best_score:.3f})")
                    else:
                        results[identifier] = self.format_result(None, None)
                        mapping_result_items.append(
                            MappingResultItem(
                                identifier=identifier,
                                target_ids=None,
                                component_id=None,
                                confidence=None,
                                qdrant_similarity_score=None
                            )
                        )
                else:
                    results[identifier] = self.format_result(None, None)
                    mapping_result_items.append(
                        MappingResultItem(
                            identifier=identifier,
                            target_ids=None,
                            component_id=None,
                            confidence=None,
                            qdrant_similarity_score=None
                        )
                    )
                    logger.info(f"No mappings found for '{identifier}'")
                    
            except Exception as e:
                logger.error(f"Error mapping '{identifier}': {e}")
                results[identifier] = self.format_result(None, None)
                mapping_result_items.append(
                    MappingResultItem(
                        identifier=identifier,
                        target_ids=None,
                        component_id=None,
                        confidence=None,
                        qdrant_similarity_score=None,
                        metadata={"error": str(e)}
                    )
                )
        
        # Store detailed results
        self.last_mapping_output = MappingOutput(
            results=mapping_result_items,
            metadata={
                "collection": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "distance_metric": "Cosine",
                "top_k": self.top_k,
                "score_threshold": self.score_threshold
            }
        )
        
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
    
    def get_last_mapping_output(self) -> Optional[MappingOutput]:
        """
        Retrieve the detailed mapping output from the most recent map_identifiers call.
        
        Returns:
            MappingOutput with detailed results including Qdrant similarity scores,
            or None if no mapping has been performed yet.
        """
        return self.last_mapping_output
    
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
from typing import List, Optional
import asyncio
import logging
import os

from biomapper.schemas.mvp0_schema import QdrantSearchResultItem
from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient

logger = logging.getLogger(__name__)

# Configuration - can be overridden by environment variables
DEFAULT_CONFIG = {
    "qdrant_host": os.getenv("QDRANT_HOST", "localhost"),
    "qdrant_port": int(os.getenv("QDRANT_PORT", "6333")),
    "collection_name": os.getenv("QDRANT_COLLECTION", "pubchem_bge_small_v1_5"),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
    "score_threshold": float(os.getenv("QDRANT_SCORE_THRESHOLD", "0.7"))
}

# Global client instance (lazy initialization)
_client_instance: Optional[PubChemRAGMappingClient] = None

def _get_client() -> PubChemRAGMappingClient:
    """Get or create a singleton PubChemRAGMappingClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = PubChemRAGMappingClient(config=DEFAULT_CONFIG)
        logger.info("Initialized PubChemRAGMappingClient with default configuration")
    return _client_instance

async def search_qdrant_for_biochemical_name(
    biochemical_name: str,
    top_k: int,
    client: Optional[PubChemRAGMappingClient] = None
) -> List[QdrantSearchResultItem]:
    """
    Searches Qdrant for a given biochemical name using PubChemRAGMappingClient
    and returns the top_k candidate PubChem CIDs and their similarity scores.

    Args:
        biochemical_name: The biochemical name to search for.
        top_k: The number of top results to return.
        client: An instance of PubChemRAGMappingClient. If not provided, uses a default instance.

    Returns:
        A list of QdrantSearchResultItem objects sorted by score (highest first).
        Returns an empty list if no results are found or an error occurs.
    
    Design Notes (from design.md & implementation_notes.md):
    - Instantiate PubChemRAGMappingClient (consider how it's configured - API URL, keys).
    - Call `await client.map_identifiers([biochemical_name])`.
    - Call `client.get_last_mapping_output()` to retrieve `MappingOutput` object.
      (MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a])
    - Extract CIDs and qdrant_similarity_score from MappingResultItem list.
    - Ensure results are sorted by score if not already (higher is better for cosine).
    - Limit to top_k results.
    - Handle cases where PubChemRAGMappingClient returns no matches gracefully.
    - Logging: Add logging for input, number of hits, and output.
    """
    # Use provided client or get default instance
    if client is None:
        client = _get_client()
    
    logger.info(f"Searching Qdrant for biochemical name: '{biochemical_name}' with top_k={top_k}")
    
    try:
        # Override client's top_k for this search
        original_top_k = client.top_k
        client.top_k = top_k
        
        # Perform the search
        await client.map_identifiers([biochemical_name])
        
        # Restore original top_k
        client.top_k = original_top_k
        
        # Get detailed mapping output
        mapping_output = client.get_last_mapping_output()
        
        if not mapping_output or not mapping_output.results:
            logger.info(f"No results found for '{biochemical_name}'")
            return []
        
        # Extract results from the first (and only) mapping result
        mapping_result = mapping_output.results[0]
        
        if not mapping_result.target_ids or not mapping_result.qdrant_similarity_score:
            logger.info(f"No valid mappings found for '{biochemical_name}'")
            return []
        
        # Build list of QdrantSearchResultItem objects
        results = []
        
        # Get all scores if available in metadata
        all_scores = mapping_result.metadata.get("all_scores", []) if mapping_result.metadata else []
        
        for i, target_id in enumerate(mapping_result.target_ids):
            # Extract CID from PUBCHEM:CID format
            if target_id.startswith("PUBCHEM:"):
                try:
                    cid = int(target_id.replace("PUBCHEM:", ""))
                    # Use individual score if available, otherwise use the best score
                    score = all_scores[i] if i < len(all_scores) else mapping_result.qdrant_similarity_score
                    results.append(QdrantSearchResultItem(cid=cid, score=score))
                except ValueError:
                    logger.warning(f"Invalid CID format: {target_id}")
        
        # Sort by score (descending) and limit to top_k
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:top_k]
        
        logger.info(f"Found {len(results)} results for '{biochemical_name}' (scores: {[r.score for r in results]})")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching Qdrant for '{biochemical_name}': {e}")
        return []

# Example usage (for testing this component independently)
async def main():
    """Example usage of the Qdrant search function."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test searches
    test_names = ["glucose", "caffeine", "aspirin", "unknown_compound_xyz"]
    
    for name_to_search in test_names:
        print(f"\n--- Searching for: {name_to_search} ---")
        top_results = await search_qdrant_for_biochemical_name(name_to_search, top_k=5)
        
        if top_results:
            print(f"Top {len(top_results)} Qdrant results for '{name_to_search}':")
            for i, item in enumerate(top_results, 1):
                print(f"  {i}. CID: {item.cid}, Score: {item.score:.4f}")
        else:
            print(f"No Qdrant results found for '{name_to_search}'.")

if __name__ == "__main__":
    asyncio.run(main())

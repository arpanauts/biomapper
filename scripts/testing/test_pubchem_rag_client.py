#!/usr/bin/env python3
"""Test the PubChemRAGMappingClient functionality."""

import sys
import asyncio
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pubchem_rag_client():
    """Test the PubChem RAG mapping client."""
    
    # Initialize the client
    config = {
        "qdrant_host": "localhost",
        "qdrant_port": 6333,
        "collection_name": "pubchem_bge_small_v1_5",
        "top_k": 5,
        "score_threshold": 0.5  # Lower threshold for testing
    }
    client = PubChemRAGMappingClient(config)
    
    # Perform health check
    logger.info("Performing health check...")
    health_status = client.health_check()
    logger.info(f"Health check result: {health_status}")
    
    if health_status["status"] != "healthy":
        logger.error(f"Client is not healthy: {health_status}")
        return
    
    # Test metabolites
    test_names = [
        "aspirin",
        "acetylsalicylic acid",
        "caffeine",
        "1,3,7-trimethylxanthine",
        "dopamine",
        "3,4-dihydroxyphenethylamine",
        "serotonin",
        "5-hydroxytryptamine",
        "cholesterol",
        "vitamin C",
        "ascorbic acid",
        "glucose",
        "ATP",
        "adenosine triphosphate"
    ]
    
    logger.info("\nTesting individual metabolite names:")
    for name in test_names:
        logger.info(f"\nSearching for: '{name}'")
        mapping_results = await client.map_identifiers([name])
        
        if name in mapping_results:
            target_ids, component_id = mapping_results[name]
            if target_ids:
                logger.info(f"  Found {len(target_ids)} results:")
                for i, cid in enumerate(target_ids[:3]):  # Show top 3
                    logger.info(f"  {i+1}. {cid}")
            else:
                logger.info(f"  No results found")
        else:
            logger.info(f"  No results found")
    
    # Test batch mapping
    logger.info("\n\nTesting batch mapping:")
    batch_names = ["aspirin", "caffeine", "dopamine", "invalid_metabolite_xyz"]
    batch_results = await client.map_identifiers(batch_names)
    
    for name, (target_ids, component_id) in batch_results.items():
        if target_ids:
            logger.info(f"\n'{name}': {len(target_ids)} results")
            logger.info(f"  Top match: {target_ids[0]}")
        else:
            logger.info(f"\n'{name}': No results")


if __name__ == "__main__":
    asyncio.run(test_pubchem_rag_client())
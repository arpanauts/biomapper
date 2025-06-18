#!/usr/bin/env python
"""
Test historical resolution on a small batch of unmatched proteins.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_batch_resolution():
    """Test resolution on a batch of unmatched proteins."""
    
    # Read first 10 unmatched proteins
    with open("/home/ubuntu/biomapper/data/results/ukbb_unmatched_proteins.txt", 'r') as f:
        unmatched = [line.strip() for line in f.readlines()[:10]]
    
    logger.info(f"Testing resolution for {len(unmatched)} proteins: {unmatched}")
    
    # Create resolver
    resolver = UniProtHistoricalResolverClient()
    
    # Resolve batch
    results = await resolver.map_identifiers(unmatched)
    
    # Analyze results
    resolved_count = 0
    for uniprot_id, (mapped_ids, error) in results.items():
        if mapped_ids:
            resolved_count += 1
            logger.info(f"{uniprot_id}: RESOLVED -> {mapped_ids}")
        else:
            logger.info(f"{uniprot_id}: NOT FOUND (error: {error})")
    
    logger.info(f"\nSummary: {resolved_count}/{len(unmatched)} proteins have historical records")
    
    return resolved_count

if __name__ == "__main__":
    result = asyncio.run(test_batch_resolution())
    logger.info(f"Test completed. Resolved: {result}")
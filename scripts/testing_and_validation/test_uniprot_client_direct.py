#!/usr/bin/env python
"""
Direct test of UniProtHistoricalResolverClient to debug API interaction.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_uniprot_client():
    """Test the UniProtHistoricalResolverClient directly."""
    
    # Test IDs from the prompt
    test_ids = [
        'P69905',  # Known primary UniProt ID
        'P02768',  # Known primary UniProt ID
        'Q15823',  # Known primary UniProt ID
        'O00159',  # Known primary UniProt ID
        'P12345_UNKNOWN',  # Expected to fail
    ]
    
    logger.info(f"Testing UniProtHistoricalResolverClient with IDs: {test_ids}")
    
    # Create client
    client = UniProtHistoricalResolverClient()
    
    # Test with cache bypass
    logger.info("\n" + "="*60)
    logger.info("Testing with cache bypass enabled")
    logger.info("="*60)
    
    config = {'bypass_cache': True}
    results = await client.map_identifiers(test_ids, config=config)
    
    logger.info("\nFinal results from map_identifiers:")
    for id, (primary_ids, metadata) in results.items():
        logger.info(f"  {id}: primary_ids={primary_ids}, metadata={metadata}")
    
    # Count successful mappings
    successful = sum(1 for _, (pids, _) in results.items() if pids)
    logger.info(f"\nSuccessfully mapped: {successful}/{len(test_ids)} IDs")


async def main():
    """Main entry point."""
    try:
        await test_uniprot_client()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
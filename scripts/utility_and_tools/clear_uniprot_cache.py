#!/usr/bin/env python
"""
Clear the UniProtHistoricalResolverClient's in-memory cache.
This is useful for testing to ensure we're not getting stale cached results.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient


async def clear_cache():
    """Clear the UniProt historical resolver client cache."""
    # Create a client instance
    client = UniProtHistoricalResolverClient()
    
    # Get cache stats before clearing
    stats_before = client.get_cache_stats()
    print(f"Cache stats before clearing:")
    print(f"  Size: {stats_before['size']}")
    print(f"  Hits: {stats_before['hits']}")
    print(f"  Misses: {stats_before['misses']}")
    if stats_before['size'] > 0:
        print(f"  Hit rate: {stats_before['hit_rate']:.2%}")
    
    # Clear the cache
    await client.clear_cache()
    print("\nCache cleared!")
    
    # Get cache stats after clearing
    stats_after = client.get_cache_stats()
    print(f"\nCache stats after clearing:")
    print(f"  Size: {stats_after['size']}")
    print(f"  Hits: {stats_after['hits']}")
    print(f"  Misses: {stats_after['misses']}")


if __name__ == "__main__":
    asyncio.run(clear_cache())
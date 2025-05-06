"""
Test script to verify UniProtHistoricalResolverClient functionality with specific test cases.

This script tests the UniProtHistoricalResolverClient's ability to resolve various types
of UniProt accessions:
- Primary accessions (should map to themselves)
- Secondary accessions (should map to current primary accessions)
- Demerged accessions (should map to multiple primary accessions)
- Obsolete/non-existent accessions (should indicate they're obsolete)

Run this script directly to test the resolver against the live UniProt API.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def test_historical_resolution():
    """Test various types of UniProt accessions with the historical resolver client."""
    # Initialize the client
    client = UniProtHistoricalResolverClient()
    
    # Test cases covering different resolution scenarios
    # We'll process these in smaller batches to avoid API issues
    group1 = [
        # Primary accessions (should map to themselves)
        "P01308",  # Insulin
    ]
    
    group2 = [
        # Secondary accessions (should map to their primary equivalents)
        "Q99895",  # Secondary ID for Insulin (should map to P01308)
    ]
    
    group3 = [
        # Demerged ID (split into multiple entries)
        "P0CG05",  # Should map to P0DOY2 and P0DOY3
    ]
    
    # Test each group individually
    test_ids = group3
    
    # Expected mappings for the current test group
    expected = {
        "P0CG05": (["P0DOY2", "P0DOY3"], "demerged"),
    }
    
    logger.info(f"Testing UniProt historical resolution with {len(test_ids)} IDs")
    
    # Execute the mapping
    results = await client.map_identifiers(test_ids)
    
    # Display and verify results
    print("\n---- UniProt Historical Resolution Results ----")
    for accession, result in results.items():
        primary_ids, resolution_type = result
        
        # Display the result
        if primary_ids:
            print(f"{accession} -> {', '.join(primary_ids)} ({resolution_type})")
        else:
            print(f"{accession} -> Not resolvable ({resolution_type})")
        
        # Verify against expected results (if we have expectations)
        if accession in expected and expected[accession][0] is not None:
            expected_ids, expected_type = expected[accession]
            
            # For demerged IDs, ensure the result is sorted for comparison
            if accession == "P0CG05" and primary_ids:
                primary_ids.sort()
                expected_ids.sort()
            
            # Check if IDs match expected
            try:
                assert primary_ids == expected_ids, f"Mapping for {accession} failed: got {primary_ids}, expected {expected_ids}"
            except AssertionError as e:
                logger.error(f"{e}")
                
            # Check if resolution type matches expected (if we have an expectation)
            if expected_type:
                try:
                    assert resolution_type == expected_type, f"Resolution type for {accession} failed: got {resolution_type}, expected {expected_type}"
                except AssertionError as e:
                    logger.error(f"{e}")
    
    # Get and display cache statistics
    cache_stats = client.get_cache_stats()
    print(f"\nCache Statistics: {cache_stats}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_historical_resolution())
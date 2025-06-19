"""
Test script for the UniProtHistoricalResolverClient with verified test cases.

Based on our direct API testing, we now have a set of verified test cases
that correctly match the current state of the UniProt database.
"""
import asyncio
import logging

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_test():
    """Test the UniProtHistoricalResolverClient with verified test cases."""
    # Initialize the client
    client = UniProtHistoricalResolverClient()
    
    # Test cases with verified expected results
    test_cases = [
        {
            "id": "P01308",             # Insulin
            "expected_type": "primary", 
            "expected_ids": ["P01308"]
        },
        {
            "id": "P0CG05",             # Demerged ID that ALSO exists as a primary entry
            "expected_type": "demerged",
            "expected_ids": ["P0DOY2", "P0DOY3"]
        },
        {
            "id": "FAKEID123",          # Invalid format
            "expected_type": "obsolete",
            "expected_ids": None
        },
        {
            "id": "A0M8Q4",             # Known secondary accession (appears in P0DOY2 and P0DOY3)
            "expected_type": "demerged",
            "expected_ids": ["P0DOY2", "P0DOY3"]
        },
    ]
    
    # Extract test IDs
    test_ids = [case["id"] for case in test_cases]
    
    # Run the resolver
    logger.info(f"Testing UniProtHistoricalResolverClient with {len(test_ids)} verified IDs")
    results = await client.map_identifiers(test_ids)
    
    # Process and verify results
    print("\n=== UniProt ID Resolution Test Results ===")
    success_count = 0
    
    for case in test_cases:
        acc_id = case["id"]
        expected_type = case["expected_type"]
        expected_ids = case["expected_ids"]
        
        if acc_id not in results:
            print(f"{acc_id} -> ERROR: No result returned")
            continue
            
        primary_ids, metadata = results[acc_id]
        
        # Display the result
        if primary_ids:
            print(f"{acc_id} -> {', '.join(primary_ids)} ({metadata})")
        else:
            print(f"{acc_id} -> Not resolvable ({metadata})")
            
        # Verify against expected results
        type_match = metadata == expected_type
        
        # For demerged IDs, sort before comparing
        if expected_type == "demerged" and primary_ids:
            id_match = sorted(primary_ids) == sorted(expected_ids)
        else:
            id_match = primary_ids == expected_ids
            
        if type_match and id_match:
            success_count += 1
            print("  ✓ Verified successfully")
        else:
            if not type_match:
                print(f"  ✗ Type mismatch - Expected: {expected_type}, Got: {metadata}")
            if not id_match:
                print(f"  ✗ ID mismatch - Expected: {expected_ids}, Got: {primary_ids}")
    
    # Summary
    print(f"\nResults: {success_count}/{len(test_cases)} IDs verified successfully")
    
    # Cache statistics
    cache_stats = client.get_cache_stats()
    print(f"Cache Statistics: {cache_stats}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_test())
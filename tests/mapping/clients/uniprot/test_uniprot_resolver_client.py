"""
Test script for the UniProtHistoricalResolverClient with various ID types.

This script tests the client with specific examples of different ID types:
- Primary IDs: Should map to themselves
- Secondary IDs: Should map to their current primary IDs
- Demerged IDs: Should map to multiple primary IDs
- Invalid/obsolete IDs: Should be marked as not resolvable
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

# Set client logger to debug level
client_logger = logging.getLogger("biomapper.mapping.clients.uniprot_historical_resolver_client")
client_logger.setLevel(logging.DEBUG)

async def run_test():
    """Test the UniProtHistoricalResolverClient with various ID types."""
    # Initialize the client
    client = UniProtHistoricalResolverClient()
    
    # Test IDs with known outcomes
    test_ids = [
        # Primary accessions
        "P01308",        # Insulin (primary)
        "P05067",        # APP (primary)
        
        # Secondary accessions
        "Q99895",        # Secondary for Insulin (should map to P01308)
        "A6NFQ7",        # Secondary for APP (should map to P05067)
        
        # Demerged ID
        "P0CG05",        # Should map to P0DOY2 and P0DOY3
        
        # Invalid/obsolete IDs
        "FAKEID123",     # Not a valid UniProt ID
        "P99999",        # Non-existent ID
    ]
    
    # Expected results for verification
    expected = {
        # Primary accessions
        "P01308": {"type": "primary", "ids": ["P01308"]},
        "P05067": {"type": "primary", "ids": ["P05067"]},
        
        # Secondary accessions
        "Q99895": {"type": "secondary:P01308", "ids": ["P01308"]},
        "A6NFQ7": {"type": "secondary:P05067", "ids": ["P05067"]},
        
        # Demerged ID
        "P0CG05": {"type": "demerged", "ids": ["P0DOY2", "P0DOY3"]},
        
        # Invalid/obsolete IDs
        "FAKEID123": {"type": "obsolete", "ids": None},
        "P99999": {"type": "obsolete", "ids": None},
    }
    
    # Run the resolver
    logger.info(f"Testing UniProtHistoricalResolverClient with {len(test_ids)} IDs")
    results = await client.map_identifiers(test_ids)
    
    # Process and verify results
    print("\n=== UniProt ID Resolution Test Results ===")
    success_count = 0
    
    for acc_id, result in results.items():
        primary_ids, metadata = result
        
        # Display the result
        if primary_ids:
            print(f"{acc_id} -> {', '.join(primary_ids)} ({metadata})")
        else:
            print(f"{acc_id} -> Not resolvable ({metadata})")
            
        # Verify against expected results
        if acc_id in expected:
            expected_type = expected[acc_id]["type"]
            expected_ids = expected[acc_id]["ids"]
            
            type_match = metadata == expected_type
            
            # For demerged IDs, we need to sort before comparing
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
    print(f"\nResults: {success_count}/{len(test_ids)} IDs verified successfully")
    
    # Cache statistics
    cache_stats = client.get_cache_stats()
    print(f"Cache Statistics: {cache_stats}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_test())
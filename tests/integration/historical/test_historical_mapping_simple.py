"""
Simple test script to verify UniProtHistoricalResolverClient functionality.

This script directly tests the historical resolver client with a set of known test cases,
bypassing the MappingExecutor to simplify testing and avoid database dependencies.

Usage:
    python test_historical_mapping_simple.py
"""
import asyncio
import logging
import pandas as pd
from pathlib import Path

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set more detailed logs for the client
client_logger = logging.getLogger("biomapper.mapping.clients.uniprot_historical_resolver_client")
client_logger.setLevel(logging.DEBUG)

# Test data
TEST_DATA_PATH = Path(__file__).parent / "data" / "ukbb_test_data_with_historical_ids.tsv"
OUTPUT_PATH = Path(__file__).parent / "data" / "ukbb_test_results_simple.tsv"

# Expected results for validation (mapping from test data descriptions)
EXPECTED_RESULTS = {
    "P01308": {"type": "primary", "expected_mapping": ["P01308"]},
    "Q99895": {"type": "secondary", "expected_mapping": ["P01308"]},
    "P05067": {"type": "primary", "expected_mapping": ["P05067"]},
    "A6NFQ7": {"type": "secondary", "expected_mapping": ["P05067"]},
    "P0CG05": {"type": "demerged", "expected_mapping": ["P0DOY2", "P0DOY3"]},
    "FAKEID123": {"type": "obsolete", "expected_mapping": None},
    "P78358": {"type": "primary", "expected_mapping": ["P78358"]},
    "P97333": {"type": "primary", "expected_mapping": ["P97333"]}
}


async def run_test():
    """Test the historical resolver client with test data."""
    # 1. Read the test data
    logger.info(f"Reading test data from {TEST_DATA_PATH}")
    try:
        df = pd.read_csv(TEST_DATA_PATH, sep="\t", comment="#")
        logger.info(f"Loaded {len(df)} test cases")
        
        # Extract UniProt IDs for mapping
        # Handle composite IDs by splitting them and flattening
        uniprot_ids = []
        for id_str in df["UniProt"].dropna():
            # If ID contains a comma, it's a composite
            if "," in str(id_str):
                for part in id_str.split(","):
                    uniprot_ids.append(part.strip())
            else:
                uniprot_ids.append(id_str)
                
        # Remove duplicates
        uniprot_ids = list(set(uniprot_ids))
        logger.info(f"Found {len(uniprot_ids)} unique UniProt IDs to test")
        
    except Exception as e:
        logger.error(f"Error reading test data: {e}")
        # Fallback to hardcoded test IDs
        uniprot_ids = ["P01308", "Q99895", "P05067", "A6NFQ7", "P0CG05", "FAKEID123", "P78358", "P97333"]
        logger.info(f"Using {len(uniprot_ids)} fallback test IDs")
    
    # 2. Initialize the historical resolver client
    logger.info("Initializing the historical resolver client")
    client = UniProtHistoricalResolverClient(
        config={"cache_size": 1000}
    )
    
    # 3. Execute mapping for all IDs
    logger.info(f"Resolving {len(uniprot_ids)} UniProt IDs with historical resolver...")
    all_results = await client.map_identifiers(uniprot_ids)
    
    # 4. Display and verify results
    print("\n---- UniProt Historical Resolution Results ----")
    success_count = 0
    test_results = []
    
    for identifier, (primary_ids, metadata) in all_results.items():
        # Prepare result details for DataFrame
        result_entry = {
            "UniProt": identifier,
            "PrimaryIDs": ",".join(primary_ids) if primary_ids else "None",
            "ResolutionType": metadata,
            "Result": "Success" if primary_ids else "Failed"
        }
        
        # Check against expected results
        if identifier in EXPECTED_RESULTS:
            expected = EXPECTED_RESULTS[identifier]
            result_entry["ExpectedType"] = expected["type"]
            
            if expected["expected_mapping"]:
                result_entry["ExpectedMapping"] = ",".join(expected["expected_mapping"])
            else:
                result_entry["ExpectedMapping"] = "None"
                
            # Determine if test passed
            type_match = False
            mapping_match = False
            
            # Check resolution type
            if expected["type"] == "primary" and metadata == "primary":
                type_match = True
            elif expected["type"] == "secondary" and metadata.startswith("secondary:"):
                type_match = True
            elif expected["type"] == "demerged" and metadata == "demerged":
                type_match = True
            elif expected["type"] == "obsolete" and metadata == "obsolete":
                type_match = True
                
            # Check mapped IDs
            if expected["expected_mapping"] is None and primary_ids is None:
                mapping_match = True
            elif expected["expected_mapping"] and primary_ids:
                # For demerged IDs, sort for comparison
                if expected["type"] == "demerged":
                    sorted_expected = sorted(expected["expected_mapping"])
                    sorted_actual = sorted(primary_ids)
                    mapping_match = sorted_expected == sorted_actual
                # For simple cases, just check if expected in actual (allowing for variations)
                else:
                    mapping_match = any(exp_id in primary_ids for exp_id in expected["expected_mapping"])
                    
            result_entry["TypeMatch"] = "Yes" if type_match else "No"
            result_entry["MappingMatch"] = "Yes" if mapping_match else "No"
            result_entry["TestPassed"] = "Yes" if type_match and mapping_match else "No"
        else:
            # No expectations for this ID
            result_entry["TestPassed"] = "Unknown"
        
        # Display result in console
        if primary_ids:
            print(f"{identifier} -> {', '.join(primary_ids)} ({metadata})")
            success_count += 1
        else:
            print(f"{identifier} -> Not resolvable ({metadata})")
            
        test_results.append(result_entry)
    
    # 5. Save results to DataFrame
    results_df = pd.DataFrame(test_results)
    logger.info(f"Saving results to {OUTPUT_PATH}")
    results_df.to_csv(OUTPUT_PATH, sep="\t", index=False)
    
    # 6. Print summary
    print(f"\nSummary: {success_count}/{len(all_results)} UniProt IDs successfully resolved")
    
    # Get and print cache statistics
    cache_stats = client.get_cache_stats()
    print(f"Cache Statistics: {cache_stats}")
    
    return results_df


if __name__ == "__main__":
    asyncio.run(run_test())
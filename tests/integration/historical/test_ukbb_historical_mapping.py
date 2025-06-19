"""
Test script for end-to-end UniProt historical ID resolution and mapping to Arivale.

This script demonstrates mapping from UKBB to Arivale with:
1. Direct mapping for primary UniProt IDs
2. Historical resolution + mapping for secondary/demerged UniProt IDs

It uses the synthetic test dataset with a mix of different UniProt ID types.
"""
import asyncio
import logging
import pandas as pd
from pathlib import Path

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants for the test
TEST_DATA_PATH = Path(__file__).parent / "data" / "ukbb_test_data_with_historical_ids.tsv"
OUTPUT_PATH = Path(__file__).parent / "data" / "ukbb_test_results.tsv"

# Source/target configuration
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "Arivale_Protein"
SOURCE_ONTOLOGY = "UNIPROTKB_AC"
TARGET_ONTOLOGY = "ARIVALE_PROTEIN_ID"

# Column names
UNIPROT_COLUMN = "UniProt"
ARIVALE_ID_COLUMN = "ARIVALE_PROTEIN_ID"
MAPPING_PATH_COLUMN = "MappingPath"
CONFIDENCE_COLUMN = "Confidence"
HOP_COUNT_COLUMN = "Hops"


async def test_historical_mapping():
    """Run a test of historical ID resolution and mapping to Arivale."""
    # Initialize configuration
    config = Config.get_instance()
    # Fix database paths to point to the correct location 
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    logger.info(f"Using Config DB: {config.get('database.config_db_url')}")
    logger.info(f"Using Cache DB: {config.get('database.cache_db_url')}")
    
    # Make sure test data exists
    if not TEST_DATA_PATH.exists():
        logger.error(f"Test data file not found: {TEST_DATA_PATH}")
        return
    
    # 1. Read test data
    logger.info(f"Reading test data from {TEST_DATA_PATH}")
    df = pd.read_csv(TEST_DATA_PATH, sep="\t", comment="#")
    logger.info(f"Loaded {len(df)} test cases")
    
    # 2. Extract UniProt IDs for mapping
    uniprot_ids = df[UNIPROT_COLUMN].dropna().unique().tolist()
    logger.info(f"Found {len(uniprot_ids)} unique UniProt IDs to map")
    
    # 3. Initialize mapping executor
    logger.info("Initializing MappingExecutor")
    executor = MappingExecutor()
    
    # 4. Execute mapping
    logger.info(f"Executing mapping from {SOURCE_ENDPOINT_NAME}.{SOURCE_ONTOLOGY} to {TARGET_ENDPOINT_NAME}.{TARGET_ONTOLOGY}")
    mapping_result = await executor.execute_mapping(
        source_endpoint_name=SOURCE_ENDPOINT_NAME,
        target_endpoint_name=TARGET_ENDPOINT_NAME,
        source_identifiers=uniprot_ids,
        source_ontology_type=SOURCE_ONTOLOGY,
        target_ontology_type=TARGET_ONTOLOGY,
        max_hop_count=3,
        min_confidence=0.1,
        allow_reverse_paths=False,
    )
    
    # 5. Process and analyze results
    if mapping_result["status"] in ["success", "partial_success"]:
        logger.info(f"Mapping completed with status: {mapping_result['status']}")
        
        # Extract results
        results_dict = mapping_result.get("results", {})
        logger.info(f"Received {len(results_dict)} mapping results")
        
        # Create a DataFrame from the results for analysis
        results_data = []
        for uniprot_id, result_data in results_dict.items():
            target_ids = result_data.get("target_identifiers")
            mapped_id = target_ids[0] if target_ids else None
            path_name = result_data.get("mapping_path_name", "None")
            confidence = result_data.get("confidence_score", 0)
            hop_count = result_data.get("hop_count", 0)
            
            results_data.append({
                UNIPROT_COLUMN: uniprot_id,
                ARIVALE_ID_COLUMN: mapped_id,
                MAPPING_PATH_COLUMN: path_name,
                CONFIDENCE_COLUMN: confidence,
                HOP_COUNT_COLUMN: hop_count
            })
        
        # Create results DataFrame
        results_df = pd.DataFrame(results_data)
        
        # Merge with original data for comparison
        merged_df = pd.merge(df, results_df, on=UNIPROT_COLUMN, how="left")
        
        # Calculate some statistics
        direct_mappings = merged_df[merged_df[MAPPING_PATH_COLUMN] == "UKBB_to_Arivale_Protein_via_UniProt"]
        historical_mappings = merged_df[merged_df[MAPPING_PATH_COLUMN] == "UKBB_to_Arivale_Protein_via_Historical_Resolution"]
        failed_mappings = merged_df[merged_df[ARIVALE_ID_COLUMN].isna()]
        
        # Print analysis
        print("\n===== Mapping Results Analysis =====")
        print(f"Total test cases: {len(df)}")
        print(f"Direct mappings: {len(direct_mappings)} ({len(direct_mappings)/len(df)*100:.1f}%)")
        print(f"Historical resolution + mappings: {len(historical_mappings)} ({len(historical_mappings)/len(df)*100:.1f}%)")
        print(f"Failed mappings: {len(failed_mappings)} ({len(failed_mappings)/len(df)*100:.1f}%)")
        
        # Save the results
        logger.info(f"Saving results to {OUTPUT_PATH}")
        merged_df.to_csv(OUTPUT_PATH, sep="\t", index=False)
        
        # Return paths to make it easier to examine results
        return merged_df
    else:
        logger.error(f"Mapping failed: {mapping_result.get('error', 'Unknown error')}")
        return None


if __name__ == "__main__":
    asyncio.run(test_historical_mapping())
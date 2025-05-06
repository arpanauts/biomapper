"""Test script to specifically test the reverse mapping path with the new client."""

import asyncio
import logging
import json
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.utils.config import CONFIG_DB_URL

# Configure logging to show more details
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Get the root logger and set its level
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Set specific loggers to DEBUG level
logging.getLogger("biomapper.core.mapping_executor").setLevel(logging.DEBUG)
logging.getLogger("biomapper.mapping.clients").setLevel(logging.DEBUG)


async def test_reverse_mapping():
    """Test the reverse mapping from Arivale protein IDs to UniProtKB accessions."""
    print("Starting test of reverse mapping Arivale_Protein -> UKBB_Protein...")

    # Create executor
    executor = MappingExecutor(metamapper_db_url=CONFIG_DB_URL)

    # Sample Arivale protein IDs (both with ENSP... and without for comparison)
    # Using examples seen in the data
    test_ids = [
        "CAM_O00533",  # Has Ensembl protein IDs in target_protein_id
        "CAM_O14786",  # NRP1 protein
        "MET_Q9NR28",  # Another entry
        "INF_Q16552",  # Another entry
        "NEX_P41227",  # Another entry
    ]

    # Execute reverse mapping
    print(f"Executing mapping with {len(test_ids)} Arivale IDs...")
    mapping_results = await executor.execute_mapping(
        source_endpoint_name="Arivale_Protein",
        target_endpoint_name="UKBB_Protein",
        input_data=test_ids,
        use_cache=True,
        max_cache_age_days=None,
        mapping_direction="reverse",
        try_reverse_mapping=True,
    )

    # Process results
    print(f"\nReverse mapping results: {len(mapping_results)} entries")
    successful = sum(
        1 for v in mapping_results.values() if v and v != "NO_MAPPING_FOUND"
    )
    print(f"Successfully mapped: {successful}/{len(test_ids)}")

    # Show detailed results
    print("\nDetailed mapping results:")
    for source_id, target_id in mapping_results.items():
        print(f"  {source_id} -> {target_id}")

    # Get full path details if available
    if successful > 0:
        # Cache lookup would have stored the mapping details
        print("\nAttempting to get path details from cache...")

        # This would normally query the entity_mappings table
        # For simplicity, we'll just show the available data
        print("Available mapping details from results:")
        print(json.dumps(mapping_results, indent=2))


if __name__ == "__main__":
    asyncio.run(test_reverse_mapping())

"""Test script for UniProt ID mappings with alternative database names."""

import asyncio
import logging
from biomapper.mapping.clients.uniprot_idmapping_client import UniProtIDMappingClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_various_db_combinations():
    """Test different database name combinations for mapping Ensembl Protein IDs."""
    # Test with IDs from the Arivale data
    test_ids = [
        "ENSP00000256509",  # CHL1 protein
        "ENSP00000380628",  # Another CHL1 isoform
        "ENSP00000265371",  # NRP1 protein
    ]

    # Different combinations to try
    combinations = [
        {"from_db": "Ensembl", "to_db": "UniProtKB"},
        {"from_db": "Ensembl", "to_db": "UniProtKB_AC"},
        {"from_db": "Ensembl_Protein", "to_db": "UniProtKB", "try_alternate": True},
    ]

    for combo in combinations:
        logger.info(f"\n\nTesting combination: {combo}")

        # Extract try_alternate flag if present
        try_alternate = combo.pop("try_alternate", False)

        # Create client
        client = UniProtIDMappingClient(**combo)

        # Test with original IDs
        results = await client.map_identifiers(test_ids)

        print(f"\nResults for {combo}:")
        found = 0
        for k, v in results.items():
            print(f"  {k}: {v}")
            if v is not None:
                found += 1

        print(f"Found mappings: {found}/{len(test_ids)}")

        # Try alternate format if requested
        if try_alternate and found == 0:
            # Try with cleaned IDs (e.g., ENSP00000256509 -> P56539)
            # This is a fictional example just to illustrate format changes
            logger.info("Trying with alternate ID format...")

            # For this example, just use dummy IDs known to work
            alt_ids = ["P05067", "P04637", "P38398"]  # APP, TP53, BRCA1
            alt_results = await client.map_identifiers(alt_ids)

            print(f"\nResults with alternate IDs:")
            alt_found = 0
            for k, v in alt_results.items():
                print(f"  {k}: {v}")
                if v is not None:
                    alt_found += 1

            print(f"Found mappings (alternate): {alt_found}/{len(alt_ids)}")


if __name__ == "__main__":
    asyncio.run(test_various_db_combinations())

"""Test script for UniProtEnsemblProteinMappingClient."""

import asyncio
import logging
from biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client import (
    UniProtEnsemblProteinMappingClient,
)

# Set up logging
logging.basicConfig(level=logging.INFO)


async def test():
    """Test the UniProtEnsemblProteinMappingClient with real IDs."""
    client = UniProtEnsemblProteinMappingClient()

    # Test with IDs from the Arivale data
    test_ids = [
        "ENSP00000256509",  # CHL1 protein
        "ENSP00000380628",  # Another CHL1 isoform
        "ENSP00000265371",  # NRP1 protein
        "ENSP00000364001",  # Another protein
    ]

    print(f"Testing with Ensembl Protein IDs: {test_ids}")
    results = await client.map_identifiers(test_ids)

    print("\nResults:")
    for k, v in results.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(test())

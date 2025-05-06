"""Debug script to test UniProtEnsemblProteinMappingClient."""

import asyncio
import logging
from biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client import (
    UniProtEnsemblProteinMappingClient,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# Also set UniProt client loggers to DEBUG
logging.getLogger("biomapper.mapping.clients.uniprot_idmapping_client").setLevel(
    logging.DEBUG
)
logging.getLogger(
    "biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client"
).setLevel(logging.DEBUG)


async def run_test():
    """Run a test of the UniProtEnsemblProteinMappingClient with various database options."""

    # Test with different database name combinations
    test_configs = [
        {"name": "Default", "from_db": "Ensembl_Protein", "to_db": "UniProtKB_AC-ID"},
        {"name": "Ensembl", "from_db": "Ensembl", "to_db": "UniProtKB"},
        {"name": "Ensembl_ID", "from_db": "Ensembl_ID", "to_db": "UniProtKB"},
        {"name": "Ensembl_PRO", "from_db": "Ensembl_PRO", "to_db": "UniProtKB"},
    ]

    # Example Ensembl Protein IDs
    test_ids = ["ENSP00000256509", "ENSP00000380628", "ENSP00000265371"]

    for config in test_configs:
        print(f"\n--- Testing configuration: {config['name']} ---")
        try:
            client = UniProtEnsemblProteinMappingClient(
                {"from_db": config["from_db"], "to_db": config["to_db"]}
            )

            print(f"Mapping with from_db={client.from_db} to_db={client.to_db}")
            results = await client.map_identifiers(
                test_ids[:1]
            )  # Just try one ID to be faster

            print("Results:")
            for ensembl_id, uniprot_id in results.items():
                print(f"  {ensembl_id}: {uniprot_id}")

        except Exception as e:
            print(f"Error testing {config['name']}: {e}")

        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(run_test())

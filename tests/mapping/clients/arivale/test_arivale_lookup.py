"""Test script to verify Arivale lookup client functionality."""
import asyncio
import logging
from biomapper.mapping.clients.arivale_lookup_client import ArivaleMetadataLookupClient
from biomapper.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_arivale_lookup_client():
    """Test the ArivaleMetadataLookupClient with sample UniProt IDs."""
    # Get the config for file path
    config = Config.get_instance()
    
    # These are UniProt ACs from UKBB test data that mapped successfully
    test_uniprot_ids = [
        "P23560",  # BDNF
        "P14210",  # HGF
        "P15692",  # VEGFA
    ]
    
    # Arivale lookup client configuration - from mapping resource definition
    client_config = {
        "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
        "key_column": "uniprot",
        "value_column": "name"
    }
    
    # Initialize client
    client = ArivaleMetadataLookupClient(config=client_config)
    
    print(f"Testing ArivaleMetadataLookupClient with UniProt IDs: {test_uniprot_ids}")
    
    # Map UniProt IDs to Arivale IDs
    results = await client.map_identifiers(test_uniprot_ids)
    
    # Display results
    print("\nMapping Results:")
    if "primary_ids" in results:
        print(f"  primary_ids: {', '.join(results['primary_ids'])}")
    
    if "input_to_primary" in results:
        for uniprot_id, arivale_id in results["input_to_primary"].items():
            print(f"  {uniprot_id} -> {arivale_id}")
    
    if "errors" in results:
        for error in results["errors"]:
            print(f"  {error['input_id']} -> No mapping found")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_arivale_lookup_client())
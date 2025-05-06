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
    for uniprot_id, mapping_result in results.items():
        arivale_ids = mapping_result[0]  # First element is list of mapped IDs
        print(f"  {uniprot_id}: {arivale_ids}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_arivale_lookup_client())
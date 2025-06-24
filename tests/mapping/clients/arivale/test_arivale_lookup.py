"""Test script to verify Arivale lookup client functionality."""
import asyncio
import logging
import tempfile
import os
from unittest.mock import patch, MagicMock
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
    
    # Create a temporary TSV file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as tmp_file:
        # Write test data to the file
        tmp_file.write("uniprot\tname\n")
        tmp_file.write("P23560\tBDNF_HUMAN\n")
        tmp_file.write("P14210\tHGF_HUMAN\n")
        tmp_file.write("P15692\tVEGFA_HUMAN\n")
        tmp_file.write("P99999\tTEST_HUMAN\n")
        tmp_file_path = tmp_file.name
    
    try:
        # Arivale lookup client configuration - use temporary file
        client_config = {
            "file_path": tmp_file_path,
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
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

if __name__ == "__main__":
    results = asyncio.run(test_arivale_lookup_client())
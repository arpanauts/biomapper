"""
Test script to verify UniProt name mapping functionality.
"""
import asyncio
import logging
from biomapper.mapping.clients.uniprot_name_client import UniProtNameClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_uniprot_name_client():
    """Test the UniProtNameClient with sample protein names."""
    client = UniProtNameClient()
    
    # Sample protein names from UKBB test data
    test_proteins = [
        "IL-6",       # Interleukin-6
        "BDNF",       # Brain-derived neurotrophic factor
        "HGF",        # Hepatocyte growth factor
        "VEGFA"       # Vascular endothelial growth factor A
    ]
    
    print(f"Testing UniProtNameClient with proteins: {test_proteins}")
    
    # Map the proteins to UniProt ACs
    results = await client.map_identifiers(test_proteins)
    
    # Display results
    print("\nMapping Results:")
    for name, accession in results.items():
        print(f"  {name}: {accession}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_uniprot_name_client())
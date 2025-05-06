"""
Test script to identify the correct query parameters for demerged UniProt IDs

This script focuses specifically on querying for P0CG05 (a known demerged ID)
"""
import asyncio
import aiohttp
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# UniProt API URLs
UNIPROT_API_URL = "https://rest.uniprot.org/uniprotkb/search"

async def test_uniprot_demerged():
    """Test querying for a demerged UniProt ID using various approaches"""
    # The ID we're testing with
    test_id = "P0CG05"
    
    # Method 1: Direct accession lookup
    logger.info(f"Method 1: Direct accession lookup for {test_id}")
    params1 = {
        "query": f"accession:{test_id}",
        "format": "json",
        "size": 10
    }
    await make_request(params1)
    
    # Method 2: Secondary accession lookup
    logger.info(f"Method 2: Secondary accession lookup for {test_id}")
    params2 = {
        "query": f"sec_acc:{test_id}",
        "format": "json",
        "size": 10
    }
    await make_request(params2)
    
    # Method 3: ID lookup (which searches across multiple fields)
    logger.info(f"Method 3: ID lookup for {test_id}")
    params3 = {
        "query": f"id:{test_id}",
        "format": "json",
        "size": 10
    }
    await make_request(params3)
    
    # Method 4: Search across all fields
    logger.info(f"Method 4: Search across all fields for {test_id}")
    params4 = {
        "query": test_id,
        "format": "json",
        "size": 10
    }
    await make_request(params4)

async def make_request(params):
    """Make a request to the UniProt API with the given parameters"""
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Request URL: {UNIPROT_API_URL}")
            logger.info(f"Parameters: {params}")
            
            async with session.get(UNIPROT_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result_count = len(data.get("results", []))
                    logger.info(f"Success! Found {result_count} results")
                    
                    # Process and display the results
                    if result_count > 0:
                        for i, entry in enumerate(data["results"], 1):
                            primary_acc = entry.get("primaryAccession")
                            sec_accs = entry.get("secondaryAccessions", [])
                            logger.info(f"Result {i}: Primary={primary_acc}, Secondary={sec_accs}")
                            
                            # Check if our test ID is in the secondary accessions
                            if "P0CG05" in sec_accs:
                                logger.info(f"FOUND: P0CG05 is secondary to {primary_acc}")
                    else:
                        logger.info("No results found")
                else:
                    error_text = await response.text()
                    logger.error(f"Error: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_uniprot_demerged())
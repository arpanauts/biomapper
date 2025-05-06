"""
Test script for checking specific UniProt IDs directly with the API.

This script focuses on direct API interaction to understand the behavior
for certain test IDs that didn't resolve as expected.
"""
import asyncio
import aiohttp
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# UniProt API URL
UNIPROT_API_URL = "https://rest.uniprot.org/uniprotkb/search"

async def fetch_entry_info(acc_id: str) -> None:
    """Fetch detailed information about a specific accession."""
    logger.info(f"Checking ID: {acc_id}")
    
    # 1. First check if it's a primary accession
    primary_params = {
        "query": f"accession:{acc_id}",
        "format": "json",
        "size": 5
    }
    
    logger.info("Checking if it's a primary accession...")
    primary_data = await make_request(primary_params)
    primary_results = primary_data.get("results", [])
    
    if primary_results:
        logger.info(f"Found {len(primary_results)} entries with this as primary accession")
        for i, entry in enumerate(primary_results, 1):
            primary_acc = entry.get("primaryAccession")
            sec_accs = entry.get("secondaryAccessions", [])
            
            logger.info(f"Entry {i}: Primary={primary_acc}, Secondary={sec_accs if sec_accs else 'None'}")
    else:
        logger.info("Not found as a primary accession")
    
    # 2. Check if it appears as a secondary accession in any entry
    secondary_params = {
        "query": f"sec_acc:{acc_id}",
        "format": "json",
        "size": 5
    }
    
    logger.info("Checking if it appears as a secondary accession...")
    secondary_data = await make_request(secondary_params)
    secondary_results = secondary_data.get("results", [])
    
    if secondary_results:
        logger.info(f"Found {len(secondary_results)} entries with this as a secondary accession")
        for i, entry in enumerate(secondary_results, 1):
            primary_acc = entry.get("primaryAccession")
            sec_accs = entry.get("secondaryAccessions", [])
            
            logger.info(f"Entry {i}: Primary={primary_acc}, Secondary={sec_accs}")
    else:
        logger.info("Not found as a secondary accession")
    
    # 3. Check raw ID search to see all mentions
    id_params = {
        "query": acc_id,
        "format": "json",
        "size": 5
    }
    
    logger.info("Checking raw ID search...")
    id_data = await make_request(id_params)
    id_results = id_data.get("results", [])
    
    if id_results:
        logger.info(f"Found {len(id_results)} entries mentioning this ID")
        for i, entry in enumerate(id_results, 1):
            primary_acc = entry.get("primaryAccession")
            sec_accs = entry.get("secondaryAccessions", [])
            
            logger.info(f"Entry {i}: Primary={primary_acc}, Secondary={sec_accs}")
    else:
        logger.info("Not found in raw ID search")
    
    logger.info(f"=== Completed checks for {acc_id} ===\n")

async def make_request(params):
    """Make a request to the UniProt API with the given parameters."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(UNIPROT_API_URL, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API Error: Status {response.status}, Text: {error_text}")
                    return {"error": error_text}
        except Exception as e:
            logger.error(f"Request Error: {str(e)}")
            return {"error": str(e)}

async def main():
    """Test specific UniProt IDs that didn't resolve as expected."""
    # Test IDs that had issues
    test_ids = [
        "Q99895",  # Expected to be a secondary ID for P01308 (insulin)
        "A6NFQ7",  # Expected to be a secondary ID for P05067 (APP)
        "P99999",  # Expected to be obsolete/not found
    ]
    
    # Also check our known good demerged case
    test_ids.append("P0CG05")
    
    for acc_id in test_ids:
        await fetch_entry_info(acc_id)

if __name__ == "__main__":
    asyncio.run(main())
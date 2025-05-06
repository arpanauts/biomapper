"""
Test script to identify the correct query parameters for UniProt API

This script directly tests querying the UniProt API for P0CG05 (a known demerged ID)
and prints the results in a structured format to understand the response structure.
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
UNIPROT_REST_BASE_URL = "https://rest.uniprot.org/uniprotkb"
UNIPROT_API_SEARCH_URL = f"{UNIPROT_REST_BASE_URL}/search"

async def test_uniprot_api():
    """Test the UniProt API with different query parameters"""
    # Query 1: Search for P0CG05 using id field
    query1 = "id:P0CG05"
    params1 = {
        "query": query1,
        "format": "json",
        "size": 10
    }
    logger.info(f"Testing query: {query1}")
    results1 = await make_api_request(params1)
    
    # Query 2: Search for primary accession P0DOY2
    query2 = "accession:P0DOY2"
    params2 = {
        "query": query2,
        "format": "json",
        "size": 10
    }
    logger.info(f"Testing query: {query2}")
    results2 = await make_api_request(params2)
    
    # Query 3: Search for P0CG05 specifically as a secondary accession (if this works)
    query3 = "secondaryAccession:P0CG05"
    params3 = {
        "query": query3,
        "format": "json",
        "size": 10
    }
    logger.info(f"Testing query: {query3}")
    results3 = await make_api_request(params3)
    
    # Query 4: Try an alternate field format for secondary accessions
    query4 = "sec_acc:P0CG05"
    params4 = {
        "query": query4,
        "format": "json",
        "size": 10
    }
    logger.info(f"Testing query: {query4}")
    results4 = await make_api_request(params4)

async def make_api_request(params):
    """Make a request to the UniProt API and return the results"""
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Requesting {UNIPROT_API_SEARCH_URL} with params: {params}")
            async with session.get(UNIPROT_API_SEARCH_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Success! Got {len(data.get('results', []))} results")
                    
                    # Print the results in a structured format
                    for i, entry in enumerate(data.get("results", []), 1):
                        logger.info(f"--- Result {i} ---")
                        primary_acc = entry.get("primaryAccession", entry.get("accession"))
                        logger.info(f"Primary accession: {primary_acc}")
                        
                        # Try to get secondary accessions in different formats
                        secondary_accs = None
                        if "secondaryAccessions" in entry:
                            secondary_accs = entry["secondaryAccessions"]
                        elif "secondary_accessions" in entry:
                            secondary_accs = entry["secondary_accessions"]
                        elif "sec_acc" in entry:
                            secondary_accs = entry["sec_acc"]
                            
                        logger.info(f"Secondary accessions: {secondary_accs}")
                        
                        # Print available field names in this entry
                        logger.info(f"Available fields: {', '.join(entry.keys())}")
                    
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"API error: Status {response.status}, Response: {error_text}")
                    return {"error": error_text}
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            return {"error": str(e)}

if __name__ == "__main__":
    asyncio.run(test_uniprot_api())
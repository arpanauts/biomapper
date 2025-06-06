#!/usr/bin/env python
"""
Test script for the updated UMLSClient

This script tests the updated UMLSClient with direct API key authentication
against the UMLS API.
"""

import asyncio
import logging
import sys
import os
from typing import List, Dict, Any, Tuple, Optional
import importlib.util
import inspect

# Dynamically import the updated UMLSClient
spec = importlib.util.spec_from_file_location(
    "umls_client_updated", 
    "/home/ubuntu/biomapper/biomapper/mapping/clients/umls_client_updated.py"
)
umls_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(umls_client_module)
UMLSClient = umls_client_module.UMLSClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Sample metabolite names for testing
TEST_METABOLITES = [
    "glucose",
    "cholesterol",
    "lactate",
    "triglycerides",
    "uric acid",
    "creatinine",
    "l-alanine",
    "glycerol",
    "adenosine triphosphate",
    "non-existent-metabolite-123456"  # Test with an invalid name
]

async def test_umls_client(target_db: str = "CHEBI"):
    """
    Test the updated UMLSClient with sample metabolite names.
    
    Args:
        target_db: Target database for mapping (default: CHEBI)
    """
    # Get API key from environment or .env file
    api_key = os.environ.get("UMLS_API_KEY", "4a91d447-736a-4578-82de-c4db552cd62e")
    
    logger.info(f"Testing updated UMLSClient with target_db={target_db}")
    
    # Initialize the client
    client = UMLSClient(config={"target_db": target_db, "api_key": api_key})
    
    try:
        # Map the test metabolite names
        results = await client.map_identifiers(terms=TEST_METABOLITES)
        
        # Display the results
        logger.info(f"Successfully mapped {len(results)} metabolite names")
        print("\nMapping Results:")
        print("=" * 80)
        
        for name, (identifiers, confidence) in results.items():
            if identifiers:
                print(f"{name:<30} -> {', '.join(identifiers)} (confidence: {confidence})")
            else:
                print(f"{name:<30} -> No mapping found")
        
        # Count successful and failed mappings
        successful = sum(1 for ids, _ in results.values() if ids is not None)
        failed = sum(1 for ids, _ in results.values() if ids is None)
        
        print("\nSummary:")
        print(f"Total metabolites: {len(TEST_METABOLITES)}")
        print(f"Successfully mapped: {successful}")
        print(f"Failed to map: {failed}")
        print(f"Success rate: {successful/len(TEST_METABOLITES)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        # Close the client
        await client.close()

async def main():
    """
    Main entry point for the script.
    """
    # Test with CHEBI as the target database
    await test_umls_client(target_db="CHEBI")
    
    print("\n" + "=" * 80 + "\n")
    
    # Test with PUBCHEM as the target database
    await test_umls_client(target_db="PUBCHEM")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
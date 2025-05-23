#!/usr/bin/env python
"""
Test the TranslatorNameResolverClient on real metabolite data with batching.

This script processes three different metadata files in batches,
adding name resolver results as new columns to each,
and saves the results as new TSV files.
"""

import asyncio
import csv
import logging
import os
import sys
from typing import List, Dict, Tuple, Optional, Set
import pandas as pd
import time

# Add the biomapper directory to the path
sys.path.append(os.path.abspath('/home/ubuntu/biomapper'))

from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Paths to input files
CHEMISTRIES_METADATA_PATH = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv"
UKBB_NMR_META_PATH = "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv"
METABOLOMICS_METADATA_PATH = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"

# Paths to output files
CHEMISTRIES_OUTPUT_PATH = "/home/ubuntu/biomapper/chemistries_metadata_with_resolver.tsv"
UKBB_NMR_OUTPUT_PATH = "/home/ubuntu/biomapper/UKBB_NMR_Meta_with_resolver.tsv"
METABOLOMICS_OUTPUT_PATH = "/home/ubuntu/biomapper/metabolomics_metadata_with_resolver.tsv"

# Databases to resolve to
TARGET_DBS = ["PUBCHEM", "CHEBI", "HMDB"]

# Batch size for processing
BATCH_SIZE = 25

async def resolve_names(client, names: List[str], target_db: str) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
    """
    Resolve a list of names to identifiers using the TranslatorNameResolverClient.
    
    Args:
        client: The TranslatorNameResolverClient instance
        names: List of names to resolve
        target_db: Target database for resolution
        
    Returns:
        Dictionary mapping names to (identifiers, confidence) tuples
    """
    logger.info(f"Resolving {len(names)} names to {target_db}")
    
    # Configure the client for this target database
    config = {"target_db": target_db}
    
    # Remove duplicate names and empty strings
    unique_names = list(set([name for name in names if name]))
    
    try:
        # Map the names to identifiers
        results = await client.map_identifiers(
            names=unique_names,
            target_biolink_type="biolink:SmallMolecule",
            **{"config": config}
        )
        
        logger.info(f"Successfully resolved {len(results)} names to {target_db}")
        return results
    except Exception as e:
        logger.error(f"Error resolving names to {target_db}: {str(e)}")
        return {name: (None, None) for name in unique_names}

async def process_in_batches(
    all_names: List[str], 
    client, 
    batch_size: int = BATCH_SIZE
) -> Dict[str, Dict[str, Tuple[Optional[List[str]], Optional[str]]]]:
    """
    Process a list of names in batches.
    
    Args:
        all_names: List of all names to process
        client: The TranslatorNameResolverClient instance
        batch_size: Size of each batch
        
    Returns:
        Dictionary mapping target DBs to results dictionaries
    """
    # Initialize results
    all_results = {target_db: {} for target_db in TARGET_DBS}
    
    # Process in batches
    for i in range(0, len(all_names), batch_size):
        batch = all_names[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_names) + batch_size - 1)//batch_size} ({len(batch)} names)")
        
        # Resolve names to each target database
        for target_db in TARGET_DBS:
            batch_results = await resolve_names(client, batch, target_db)
            all_results[target_db].update(batch_results)
        
        # Small delay between batches to avoid overwhelming the API
        await asyncio.sleep(1)
    
    return all_results

async def process_chemistries_metadata():
    """
    Process the chemistries metadata file and add name resolver results.
    """
    logger.info(f"Processing chemistries metadata file: {CHEMISTRIES_METADATA_PATH}")
    
    # Read the TSV file with pandas, handling commented lines
    with open(CHEMISTRIES_METADATA_PATH, 'r') as f:
        comments = []
        for line in f:
            if line.startswith('#'):
                comments.append(line.strip())
            else:
                break
    
    # Read the actual data, skipping comment lines
    df = pd.read_csv(CHEMISTRIES_METADATA_PATH, sep='\t', comment='#', quotechar='"')
    
    # Extract the "Name" column values
    names = df["Name"].tolist()
    
    # Initialize the TranslatorNameResolverClient
    client = TranslatorNameResolverClient(config={"target_db": "PUBCHEM"})
    
    try:
        # Process in batches
        all_results = await process_in_batches(names, client)
        
        # Add results as new columns
        for target_db in TARGET_DBS:
            # Add identifier column
            df[f"{target_db}_IDs"] = df["Name"].apply(
                lambda name: ",".join(all_results[target_db].get(name, (None, None))[0] or [])
            )
            
            # Add confidence column
            df[f"{target_db}_Confidence"] = df["Name"].apply(
                lambda name: all_results[target_db].get(name, (None, None))[1]
            )
        
        # Write the updated dataframe to a new TSV file
        with open(CHEMISTRIES_OUTPUT_PATH, 'w') as f:
            # Write the original comments
            for comment in comments:
                f.write(f"{comment}\n")
            
            # Write the updated dataframe
            df.to_csv(f, sep='\t', index=False, quotechar='"')
        
        logger.info(f"Wrote updated chemistries metadata to {CHEMISTRIES_OUTPUT_PATH}")
    finally:
        # Close the client
        await client.close()

async def process_ukbb_nmr_metadata():
    """
    Process the UKBB NMR metadata file and add name resolver results.
    """
    logger.info(f"Processing UKBB NMR metadata file: {UKBB_NMR_META_PATH}")
    
    # Read the TSV file with pandas
    df = pd.read_csv(UKBB_NMR_META_PATH, sep='\t')
    
    # Extract the "title" column values
    names = df["title"].tolist()
    
    # Initialize the TranslatorNameResolverClient
    client = TranslatorNameResolverClient(config={"target_db": "PUBCHEM"})
    
    try:
        # Process in batches
        all_results = await process_in_batches(names, client)
        
        # Add results as new columns
        for target_db in TARGET_DBS:
            # Add identifier column
            df[f"{target_db}_IDs"] = df["title"].apply(
                lambda name: ",".join(all_results[target_db].get(name, (None, None))[0] or [])
            )
            
            # Add confidence column
            df[f"{target_db}_Confidence"] = df["title"].apply(
                lambda name: all_results[target_db].get(name, (None, None))[1]
            )
        
        # Write the updated dataframe to a new TSV file
        df.to_csv(UKBB_NMR_OUTPUT_PATH, sep='\t', index=False)
        
        logger.info(f"Wrote updated UKBB NMR metadata to {UKBB_NMR_OUTPUT_PATH}")
    finally:
        # Close the client
        await client.close()

async def process_metabolomics_metadata():
    """
    Process the metabolomics metadata file and add name resolver results.
    """
    logger.info(f"Processing metabolomics metadata file: {METABOLOMICS_METADATA_PATH}")
    
    # Read the TSV file with pandas, handling commented lines
    with open(METABOLOMICS_METADATA_PATH, 'r') as f:
        comments = []
        for line in f:
            if line.startswith('#'):
                comments.append(line.strip())
            else:
                break
    
    # Read the actual data, skipping comment lines
    df = pd.read_csv(METABOLOMICS_METADATA_PATH, sep='\t', comment='#', quotechar='"')
    
    # Extract the "BIOCHEMICAL_NAME" column values
    names = df["BIOCHEMICAL_NAME"].tolist()
    
    # Initialize the TranslatorNameResolverClient
    client = TranslatorNameResolverClient(config={"target_db": "PUBCHEM"})
    
    try:
        # Process in batches
        all_results = await process_in_batches(names, client)
        
        # Add results as new columns
        for target_db in TARGET_DBS:
            # Add identifier column
            df[f"{target_db}_Resolver_IDs"] = df["BIOCHEMICAL_NAME"].apply(
                lambda name: ",".join(all_results[target_db].get(name, (None, None))[0] or [])
            )
            
            # Add confidence column
            df[f"{target_db}_Resolver_Confidence"] = df["BIOCHEMICAL_NAME"].apply(
                lambda name: all_results[target_db].get(name, (None, None))[1]
            )
        
        # Write the updated dataframe to a new TSV file
        with open(METABOLOMICS_OUTPUT_PATH, 'w') as f:
            # Write the original comments
            for comment in comments:
                f.write(f"{comment}\n")
            
            # Write the updated dataframe
            df.to_csv(f, sep='\t', index=False, quotechar='"')
        
        logger.info(f"Wrote updated metabolomics metadata to {METABOLOMICS_OUTPUT_PATH}")
    finally:
        # Close the client
        await client.close()

async def main():
    """
    Main entry point for the script.
    """
    start_time = time.time()
    
    # Process all three metadata files
    await process_chemistries_metadata()
    await process_ukbb_nmr_metadata()
    await process_metabolomics_metadata()
    
    end_time = time.time()
    logger.info(f"Total processing time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
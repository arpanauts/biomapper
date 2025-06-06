"""
Process unmapped UKBB entries using UniProt gene name fallback mapping.

This script reads unmapped UKBB entries from the Phase 1 output, queries the UniProt 
ID Mapping service to find corresponding UniProtKB Accession numbers (ACs) using 
gene names, maps these UniProt ACs to Arivale protein IDs, and produces an output 
file that can be integrated with the original Phase 1 mapping results.

The workflow consists of three main steps:
1. Gene name to UniProt AC mapping using UniProt ID Mapping API with enhanced filtering
2. UniProt AC to Arivale protein ID mapping using Arivale metadata
3. Generation of a rich output file with mapping details
"""

import asyncio
import logging
import json
import os
import pandas as pd
import aiohttp
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# Biomapper imports
from biomapper.mapping.clients.uniprot_idmapping_client import map_gene_names_to_uniprot_acs
from biomapper.mapping.clients.arivale_lookup_client import ArivaleMetadataLookupClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/enhanced_process_uniprot_gene_fallback.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# File paths
# For testing with a sample dataset
SAMPLE_MODE = True  # Set to False for full dataset processing

if SAMPLE_MODE:
    INPUT_FILE = "/home/ubuntu/output/phase1_unmapped_for_uniprot_sample.tsv"
    OUTPUT_FILE_NAME = "enhanced_uniprot_fallback_results_sample.tsv"
else:
    INPUT_FILE = "/home/ubuntu/output/phase1_unmapped_for_uniprot.tsv"
    OUTPUT_FILE_NAME = "enhanced_uniprot_fallback_results.tsv"

ARIVALE_METADATA_PATH = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"
OUTPUT_DIR = "/home/ubuntu/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, OUTPUT_FILE_NAME)

# Constants
TAXON_ID = "9606"  # Homo sapiens
FALLBACK_CONFIDENCE = 0.7  # Default confidence score for UniProt fallback mappings
BATCH_SIZE = 100  # Number of gene names to process in each batch for rate limiting

# Enable more detailed logging for debugging purposes
logging.getLogger('biomapper.mapping.clients.uniprot_idmapping_client').setLevel(logging.DEBUG)

# UniProt AC pattern for Swiss-Prot (reviewed) entries - typically P[0-9]+ or Q[0-9]+
# These are prioritized in matching since they're more likely to be in Arivale
SWISSPROT_PATTERN = re.compile(r'^[OPQ][0-9][A-Z0-9]{3}[0-9]$')

# Pre-load Arivale UniProt IDs for faster lookup
arivale_uniprot_ids: Set[str] = set()


async def load_arivale_metadata() -> pd.DataFrame:
    """
    Load Arivale proteomics metadata for mapping UniProt ACs to Arivale protein IDs.
    Also populates the global arivale_uniprot_ids set for faster filtering.
    
    Returns:
        DataFrame containing Arivale metadata
    """
    global arivale_uniprot_ids
    
    logger.info(f"Loading Arivale metadata from {ARIVALE_METADATA_PATH}")
    
    # Find header row, skipping comments
    header_line = 0
    with open(ARIVALE_METADATA_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip().startswith("#"):
                header_line = i
                break
    
    # Load the data
    arivale_df = pd.read_csv(
        ARIVALE_METADATA_PATH, 
        sep="\t", 
        skiprows=header_line
    )
    
    # Extract and store all UniProt IDs for fast lookup
    if 'uniprot' in arivale_df.columns:
        arivale_uniprot_ids = set(arivale_df['uniprot'].dropna().astype(str).str.strip().unique())
        logger.info(f"Loaded {len(arivale_uniprot_ids)} unique UniProt IDs from Arivale dataset")
    
    logger.info(f"Loaded {len(arivale_df)} Arivale protein entries")
    return arivale_df


def filter_and_prioritize_uniprot_acs(uniprot_acs: List[str]) -> List[str]:
    """
    Filter and prioritize UniProt ACs:
    1. Prioritize Swiss-Prot entries (P/Q/O followed by digits)
    2. Filter to only those UniProt ACs that exist in the Arivale dataset
    3. Return a sorted list with highest priority entries first
    
    Args:
        uniprot_acs: List of UniProt ACs to filter and prioritize
        
    Returns:
        Filtered and prioritized list of UniProt ACs
    """
    if not uniprot_acs:
        return []
    
    # Find the intersection with Arivale dataset
    arivale_matches = [ac for ac in uniprot_acs if ac in arivale_uniprot_ids]
    
    # If we have matches in Arivale, return those only
    if arivale_matches:
        # Sort by SwissProt pattern (P/Q entries first)
        return sorted(arivale_matches, 
                     key=lambda ac: (0 if SWISSPROT_PATTERN.match(ac) else 1, ac))
    
    # If no matches in Arivale, return the filtered UniProt ACs prioritizing Swiss-Prot entries
    # For debugging/logging purposes
    return sorted(uniprot_acs, 
                 key=lambda ac: (0 if SWISSPROT_PATTERN.match(ac) else 1, ac))


async def map_gene_names_to_uniprot_batch(
    gene_names: List[str], 
    session: aiohttp.ClientSession
) -> Dict[str, Tuple[List[str], List[str]]]:
    """
    Map a batch of gene names to UniProt ACs using the UniProt ID Mapping service.
    Returns both the filtered (Arivale-compatible) and full results for each gene name.
    
    Args:
        gene_names: List of gene names to map
        session: aiohttp ClientSession for making HTTP requests
        
    Returns:
        Dictionary mapping gene names to tuples of (filtered_uniprot_acs, all_uniprot_acs)
    """
    try:
        logger.info(f"Mapping batch of {len(gene_names)} gene names to UniProt ACs")
        results = await map_gene_names_to_uniprot_acs(
            gene_names=gene_names,
            taxon_id=TAXON_ID,
            session=session
        )
        
        # Filter and prioritize results
        filtered_results: Dict[str, Tuple[List[str], List[str]]] = {}
        
        for gene_name, uniprot_acs in results.items():
            if uniprot_acs:
                # Filter and prioritize the UniProt ACs
                filtered_acs = filter_and_prioritize_uniprot_acs(uniprot_acs)
                filtered_results[gene_name] = (filtered_acs, uniprot_acs)
            else:
                filtered_results[gene_name] = ([], [])
        
        # Count successful mappings
        successful_mappings = sum(1 for filtered_acs, _ in filtered_results.values() 
                                 if filtered_acs and len(filtered_acs) > 0)
        logger.info(f"Successfully mapped {successful_mappings}/{len(gene_names)} gene names to Arivale-compatible UniProt ACs")
        
        return filtered_results
    except Exception as e:
        logger.error(f"Error mapping gene names to UniProt ACs: {e}", exc_info=True)
        # Return empty results if there was an error
        return {gene: ([], []) for gene in gene_names}


async def map_uniprot_to_arivale(
    uniprot_acs: List[str],
    arivale_df: pd.DataFrame
) -> Dict[str, str]:
    """
    Map UniProt ACs to Arivale protein IDs using the ArivaleMetadataLookupClient.
    
    Args:
        uniprot_acs: List of UniProt ACs to map
        arivale_df: DataFrame containing Arivale metadata
        
    Returns:
        Dictionary mapping UniProt ACs to Arivale protein IDs
    """
    logger.info(f"Mapping {len(uniprot_acs)} UniProt ACs to Arivale protein IDs")
    
    # Initialize the Arivale lookup client
    try:
        arivale_client = ArivaleMetadataLookupClient({
            "file_path": ARIVALE_METADATA_PATH,
            "key_column": "uniprot",  # Original column name in the file
            "value_column": "name"    # Original column name in the file
        })
        
        # Perform the mapping
        mapping_results = await arivale_client.map_identifiers(uniprot_acs)
    except Exception as e:
        logger.error(f"Error in Arivale mapping: {e}", exc_info=True)
        return {}
    
    # Extract the input to primary mapping
    uniprot_to_arivale: Dict[str, str] = mapping_results.get('input_to_primary', {})
    
    # Log statistics
    mapped_count = len(uniprot_to_arivale)
    total_count = len(uniprot_acs)
    percentage = (mapped_count / total_count * 100) if total_count > 0 else 0
    logger.info(f"Mapped {mapped_count}/{total_count} UniProt ACs to Arivale protein IDs ({percentage:.2f}%)")
    
    return uniprot_to_arivale


async def process_gene_mapping_with_batching(
    input_df: pd.DataFrame, 
    batch_size: int = BATCH_SIZE
) -> List[Dict[str, Any]]:
    """
    Process gene name mapping to UniProt ACs and then to Arivale protein IDs with batching.
    Uses enhanced filtering to prioritize matches that are likely to be in the Arivale dataset.
    
    Args:
        input_df: DataFrame containing unmapped UKBB entries
        batch_size: Number of gene names to process in each batch
        
    Returns:
        List of dictionaries containing mapping results for each UKBB entry
    """
    logger.info(f"Processing {len(input_df)} unmapped UKBB entries with batch size {batch_size}")
    
    # Initialize results list
    all_results = []
    
    try:
        # Load Arivale metadata
        arivale_df = await load_arivale_metadata()
        
        # Create a session for all HTTP requests
        async with aiohttp.ClientSession() as session:
            # Get unique gene names (to reduce API calls)
            gene_series = input_df['ukbb_gene_name'].dropna()
            unique_gene_names = gene_series.unique().tolist()
            logger.info(f"Found {len(unique_gene_names)} unique gene names to map")
            
            # Process gene names in batches
            gene_to_uniprot_map = {}
            for i in range(0, len(unique_gene_names), batch_size):
                batch = unique_gene_names[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{len(unique_gene_names)//batch_size + 1} ({len(batch)} gene names)")
                
                # Map gene names to UniProt ACs with filtering
                batch_results = await map_gene_names_to_uniprot_batch(batch, session)
                
                # Update the gene to UniProt map
                gene_to_uniprot_map.update(batch_results)
                
                # Log detailed results for debugging
                mapped_count = sum(1 for filtered_acs, _ in batch_results.values() 
                                   if filtered_acs and len(filtered_acs) > 0)
                logger.info(f"Batch mapping results: {mapped_count}/{len(batch)} gene names mapped to Arivale-compatible UniProt ACs")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
            
            # Extract all unique UniProt ACs from the filtered results
            all_uniprot_acs = []
            for gene, (filtered_acs, _) in gene_to_uniprot_map.items():
                if filtered_acs:  # If mapping was successful
                    all_uniprot_acs.extend(filtered_acs)
            
            # Remove duplicates
            unique_uniprot_acs = list(set(all_uniprot_acs))
            logger.info(f"Found {len(unique_uniprot_acs)} unique Arivale-compatible UniProt ACs from gene name mapping")
            
            # Map UniProt ACs to Arivale protein IDs
            uniprot_to_arivale_map = await map_uniprot_to_arivale(unique_uniprot_acs, arivale_df)
            
            # Process each row in the input DataFrame - always generate output for all input rows
            for _, row in input_df.iterrows():
                try:
                    ukbb_id = row['ukbb_id']
                    ukbb_assay = row['ukbb_assay']
                    ukbb_gene_name = row['ukbb_gene_name']
                    ukbb_uniprot = row['ukbb_uniprot']
                    ukbb_panel = row['ukbb_panel']
                    
                    # Skip if no gene name
                    if pd.isna(ukbb_gene_name):
                        logger.warning(f"Skipping {ukbb_id} - No gene name available")
                        all_results.append({
                            'ukbb_id': ukbb_id,
                            'ukbb_assay': ukbb_assay,
                            'ukbb_gene_name': ukbb_gene_name,
                            'ukbb_uniprot': ukbb_uniprot,
                            'ukbb_panel': ukbb_panel,
                            'derived_uniprot_ac': None,
                            'mapped_arivale_id': None,
                            'confidence_score': 0.0,
                            'mapping_method': 'Missing_Gene_Name',
                            'mapping_details': json.dumps({
                                "status": "failed",
                                "reason": "No gene name available for mapping"
                            })
                        })
                        continue
                    
                    # Get UniProt ACs for this gene name
                    filtered_and_all = gene_to_uniprot_map.get(ukbb_gene_name, ([], []))
                    filtered_uniprot_acs, all_uniprot_acs = filtered_and_all
                    
                    # Check if any UniProt ACs were found at all
                    if not all_uniprot_acs:
                        logger.warning(f"No UniProt AC found for gene name {ukbb_gene_name} ({ukbb_id})")
                        all_results.append({
                            'ukbb_id': ukbb_id,
                            'ukbb_assay': ukbb_assay,
                            'ukbb_gene_name': ukbb_gene_name,
                            'ukbb_uniprot': ukbb_uniprot,
                            'ukbb_panel': ukbb_panel,
                            'derived_uniprot_ac': None,
                            'mapped_arivale_id': None,
                            'confidence_score': 0.0,
                            'mapping_method': 'UniProt_Gene_Name_API_Failed',
                            'mapping_details': json.dumps({
                                "method": "UniProt ID Mapping API",
                                "query_type": "gene_name",
                                "status": "failed",
                                "reason": "No UniProt AC found for gene name"
                            })
                        })
                        continue
                    
                    # Check if no Arivale-compatible UniProt ACs were found
                    if not filtered_uniprot_acs:
                        all_acs_str = ','.join(all_uniprot_acs[:10])  # First 10 ACs for brevity
                        if len(all_uniprot_acs) > 10:
                            all_acs_str += f"... ({len(all_uniprot_acs) - 10} more)"
                            
                        logger.warning(f"Found {len(all_uniprot_acs)} UniProt ACs for gene name {ukbb_gene_name}, but none are compatible with Arivale ({ukbb_id})")
                        all_results.append({
                            'ukbb_id': ukbb_id,
                            'ukbb_assay': ukbb_assay,
                            'ukbb_gene_name': ukbb_gene_name,
                            'ukbb_uniprot': ukbb_uniprot,
                            'ukbb_panel': ukbb_panel,
                            'derived_uniprot_ac': all_acs_str,
                            'mapped_arivale_id': None,
                            'confidence_score': 0.0,
                            'mapping_method': 'UniProt_Gene_Name_API_No_Arivale_Compatible_ACs',
                            'mapping_details': json.dumps({
                                "method": "UniProt ID Mapping API",
                                "query_type": "gene_name",
                                "gene_name": ukbb_gene_name,
                                "uniprot_acs": all_uniprot_acs[:50],  # Limit to first 50 for size
                                "total_acs_found": len(all_uniprot_acs),
                                "status": "no_arivale_compatible_acs"
                            })
                        })
                        continue
                    
                    # For each filtered UniProt AC, check if it maps to an Arivale protein ID
                    mapped = False
                    for uniprot_ac in filtered_uniprot_acs:
                        arivale_id = uniprot_to_arivale_map.get(uniprot_ac)
                        
                        if arivale_id:  # If mapping was successful
                            mapped = True
                            all_results.append({
                                'ukbb_id': ukbb_id,
                                'ukbb_assay': ukbb_assay,
                                'ukbb_gene_name': ukbb_gene_name,
                                'ukbb_uniprot': ukbb_uniprot,
                                'ukbb_panel': ukbb_panel,
                                'derived_uniprot_ac': uniprot_ac,
                                'mapped_arivale_id': arivale_id,
                                'confidence_score': FALLBACK_CONFIDENCE,
                                'mapping_method': 'UniProt_Gene_Name_API',
                                'mapping_details': json.dumps({
                                    "method": "UniProt ID Mapping API",
                                    "query_type": "gene_name",
                                    "gene_name": ukbb_gene_name,
                                    "uniprot_ac": uniprot_ac,
                                    "arivale_id": arivale_id,
                                    "total_acs_found": len(all_uniprot_acs),
                                    "filtered_acs_count": len(filtered_uniprot_acs)
                                })
                            })
                            
                            # Break after the first successful mapping
                            # If we want to include all possible mappings, remove this break
                            break
                    
                    # If no Arivale ID was found for any UniProt AC
                    if not mapped:
                        # Join all filtered UniProt ACs for the message
                        filtered_acs_str = ','.join(filtered_uniprot_acs)
                        logger.warning(f"Found {len(filtered_uniprot_acs)} filtered UniProt ACs for gene name {ukbb_gene_name}, but no matching Arivale protein ID ({ukbb_id})")
                        all_results.append({
                            'ukbb_id': ukbb_id,
                            'ukbb_assay': ukbb_assay,
                            'ukbb_gene_name': ukbb_gene_name,
                            'ukbb_uniprot': ukbb_uniprot,
                            'ukbb_panel': ukbb_panel,
                            'derived_uniprot_ac': filtered_acs_str,
                            'mapped_arivale_id': None,
                            'confidence_score': 0.0,
                            'mapping_method': 'UniProt_Gene_Name_API_No_Arivale_Match',
                            'mapping_details': json.dumps({
                                "method": "UniProt ID Mapping API",
                                "query_type": "gene_name",
                                "gene_name": ukbb_gene_name,
                                "filtered_uniprot_acs": filtered_uniprot_acs,
                                "total_acs_found": len(all_uniprot_acs),
                                "status": "no_arivale_match"
                            })
                        })
                except Exception as e:
                    logger.error(f"Error processing row with UKBB ID {row.get('ukbb_id', 'unknown')}: {e}")
                    # Add error entry to ensure we have output for all input rows
                    all_results.append({
                        'ukbb_id': row.get('ukbb_id', 'error'),
                        'ukbb_assay': row.get('ukbb_assay', ''),
                        'ukbb_gene_name': row.get('ukbb_gene_name', ''),
                        'ukbb_uniprot': row.get('ukbb_uniprot', ''),
                        'ukbb_panel': row.get('ukbb_panel', ''),
                        'derived_uniprot_ac': None,
                        'mapped_arivale_id': None,
                        'confidence_score': 0.0,
                        'mapping_method': 'Error_Processing_Row',
                        'mapping_details': json.dumps({
                            "status": "error",
                            "reason": str(e)
                        })
                    })
    except Exception as e:
        logger.error(f"Error in process_gene_mapping_with_batching: {e}", exc_info=True)
        # Return any results collected so far
    
    return all_results


async def main() -> int:
    """Main entry point for the enhanced UniProt gene fallback mapping script."""
    logger.info("Starting Enhanced UniProt gene fallback mapping process")
    logger.info(f"Running in {'SAMPLE' if SAMPLE_MODE else 'FULL'} mode")
    
    # Create output and logs directories if they don't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)
    
    try:
        # Read the unmapped entries
        logger.info(f"Reading unmapped entries from {INPUT_FILE}")
        input_df = pd.read_csv(INPUT_FILE, sep='\t')
        logger.info(f"Loaded {len(input_df)} unmapped entries")
        
        # Process the gene name mappings
        results = await process_gene_mapping_with_batching(input_df)
        
        if not results:
            logger.warning("No mapping results generated")
            return 0
        
        # Create a DataFrame from the results
        output_df = pd.DataFrame(results)
        
        # Save the output
        output_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        logger.info(f"Saved {len(output_df)} enhanced UniProt fallback mapping results to {OUTPUT_FILE}")
        
        # Calculate statistics
        successful_mappings = len(output_df[pd.notna(output_df['mapped_arivale_id'])])
        total_count = len(output_df)
        failed_mappings = total_count - successful_mappings
        success_rate = (successful_mappings / total_count * 100) if total_count > 0 else 0
        
        logger.info("Mapping Statistics:")
        logger.info(f"  Total processed: {len(output_df)}")
        logger.info(f"  Successful mappings: {successful_mappings} ({success_rate:.2f}%)")
        logger.info(f"  Failed mappings: {failed_mappings} ({100 - success_rate:.2f}%)")
        
    except Exception as e:
        logger.error(f"Error in enhanced UniProt gene fallback mapping process: {e}", exc_info=True)
    
    logger.info("Enhanced UniProt gene fallback mapping process completed")
    return len(output_df) if 'output_df' in locals() else 0


if __name__ == "__main__":
    # Run the main coroutine
    import sys
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
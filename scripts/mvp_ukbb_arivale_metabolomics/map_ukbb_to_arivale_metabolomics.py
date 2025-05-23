#!/usr/bin/env python3
"""
Main script to map UKBB NMR metabolite data to Arivale metabolomics data.

This script uses PubChemRAGMappingClient to resolve UKBB metabolite names
to PubChem CIDs, then matches these to Arivale entries.
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_ukbb_data(filepath: str) -> List[Dict[str, str]]:
    """
    Load UKBB NMR metadata.
    
    Args:
        filepath: Path to the UKBB NMR metadata file
    
    Returns:
        List of dictionaries containing UKBB metabolite information
    """
    ukbb_entries = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                ukbb_entries.append({
                    'field_id': row.get('field_id', ''),
                    'title': row.get('title', ''),
                    'group': row.get('Group', ''),
                    'subgroup': row.get('Subgroup', '')
                })
        
        logger.info(f"Loaded {len(ukbb_entries)} UKBB entries")
        return ukbb_entries
        
    except Exception as e:
        logger.error(f"Error loading UKBB data: {e}")
        raise


def load_arivale_data(filepath: str) -> Dict[str, Dict[str, str]]:
    """
    Load Arivale metabolomics metadata and create PubChem CID lookup.
    
    Args:
        filepath: Path to the Arivale metabolomics metadata file
    
    Returns:
        Dictionary mapping PubChem CIDs to Arivale entries
    """
    pubchem_to_arivale = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Skip metadata header lines
            for line in f:
                if not line.startswith('#'):
                    break
            
            # Read column headers
            headers = line.strip().split('\t')
            reader = csv.DictReader(f, fieldnames=headers, delimiter='\t')
            
            for row in reader:
                pubchem_cid = row.get('PUBCHEM', '').strip()
                
                # Only include entries with valid PubChem CIDs
                if pubchem_cid and pubchem_cid != 'NA':
                    pubchem_to_arivale[pubchem_cid] = {
                        'chemical_id': row.get('CHEMICAL_ID', ''),
                        'biochemical_name': row.get('BIOCHEMICAL_NAME', ''),
                        'pubchem': pubchem_cid,
                        'kegg': row.get('KEGG', ''),
                        'hmdb': row.get('HMDB', ''),
                        'super_pathway': row.get('SUPER_PATHWAY', ''),
                        'sub_pathway': row.get('SUB_PATHWAY', '')
                    }
        
        logger.info(f"Loaded {len(pubchem_to_arivale)} Arivale entries with PubChem CIDs")
        return pubchem_to_arivale
        
    except Exception as e:
        logger.error(f"Error loading Arivale data: {e}")
        raise


async def map_ukbb_to_pubchem(ukbb_entries: List[Dict[str, str]], 
                              confidence_threshold: float = 0.8) -> List[Dict[str, any]]:
    """
    Map UKBB titles to PubChem CIDs using RAG client.
    
    Args:
        ukbb_entries: List of UKBB metabolite entries
        confidence_threshold: Minimum confidence score for accepting mappings
    
    Returns:
        List of mapping results with PubChem CIDs and confidence scores
    """
    # Initialize RAG client
    try:
        rag_client = PubChemRAGMappingClient()
        logger.info("Successfully initialized PubChemRAGMappingClient")
        
        # Perform health check
        health_status = rag_client.health_check()
        logger.info(f"RAG client health: {health_status['status']}")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG client: {e}")
        raise
    
    # Get unique titles to map
    unique_titles = list({entry['title'] for entry in ukbb_entries})
    logger.info(f"Mapping {len(unique_titles)} unique UKBB titles")
    
    # Map titles to PubChem CIDs
    title_to_mapping = {}
    
    # Process in batches to show progress
    batch_size = 50
    for i in range(0, len(unique_titles), batch_size):
        batch = unique_titles[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(unique_titles) + batch_size - 1)//batch_size}")
        
        try:
            mapping_results = await rag_client.map_identifiers(batch)
            
            for title in batch:
                if title in mapping_results:
                    mapped_cids, _ = mapping_results[title]
                    
                    if mapped_cids:
                        # Extract CID from first result
                        top_cid = mapped_cids[0].replace("PUBCHEM:", "")
                        
                        # Estimate confidence based on number of results
                        # (In a real implementation, we'd get actual scores from Qdrant)
                        confidence = 1.0 - (0.05 * min(len(mapped_cids) - 1, 10))
                        
                        title_to_mapping[title] = {
                            'pubchem_cid': top_cid,
                            'all_cids': [cid.replace("PUBCHEM:", "") for cid in mapped_cids],
                            'confidence': confidence
                        }
                    else:
                        title_to_mapping[title] = {
                            'pubchem_cid': None,
                            'all_cids': [],
                            'confidence': 0.0
                        }
                        
        except Exception as e:
            logger.error(f"Error mapping batch starting at {i}: {e}")
            # Mark failed entries
            for title in batch:
                if title not in title_to_mapping:
                    title_to_mapping[title] = {
                        'pubchem_cid': None,
                        'all_cids': [],
                        'confidence': 0.0
                    }
    
    # Create results for each UKBB entry
    results = []
    for entry in ukbb_entries:
        title = entry['title']
        mapping = title_to_mapping.get(title, {'pubchem_cid': None, 'confidence': 0.0})
        
        result = {
            'ukbb_field_id': entry['field_id'],
            'ukbb_title': title,
            'derived_pubchem_cid': mapping['pubchem_cid'],
            'rag_confidence_score': mapping['confidence']
        }
        
        # Apply confidence threshold
        if mapping['confidence'] < confidence_threshold and mapping['pubchem_cid']:
            result['derived_pubchem_cid'] = None
            result['note'] = f"Below confidence threshold ({confidence_threshold})"
        
        results.append(result)
    
    return results


def match_to_arivale(mapping_results: List[Dict[str, any]], 
                     arivale_lookup: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Match PubChem CIDs to Arivale entries and determine mapping status.
    
    Args:
        mapping_results: Results from UKBB to PubChem mapping
        arivale_lookup: Dictionary mapping PubChem CIDs to Arivale entries
    
    Returns:
        Final mapping results with Arivale matches and status
    """
    final_results = []
    
    for result in mapping_results:
        # Initialize output record
        output = {
            'ukbb_field_id': result['ukbb_field_id'],
            'ukbb_title': result['ukbb_title'],
            'derived_pubchem_cid': result['derived_pubchem_cid'] or '',
            'rag_confidence_score': f"{result['rag_confidence_score']:.3f}",
            'mapping_status': '',
            'arivale_chemical_id': '',
            'arivale_biochemical_name': '',
            'arivale_pubchem_id': '',
            'arivale_kegg_id': '',
            'arivale_hmdb_id': ''
        }
        
        # Determine mapping status and populate Arivale fields
        if not result['derived_pubchem_cid']:
            output['mapping_status'] = 'RAG Mapping Failed'
        else:
            pubchem_cid = result['derived_pubchem_cid']
            
            if pubchem_cid in arivale_lookup:
                # Successfully mapped to Arivale
                arivale_entry = arivale_lookup[pubchem_cid]
                output['mapping_status'] = 'Successfully Mapped to Arivale'
                output['arivale_chemical_id'] = arivale_entry['chemical_id']
                output['arivale_biochemical_name'] = arivale_entry['biochemical_name']
                output['arivale_pubchem_id'] = arivale_entry['pubchem']
                output['arivale_kegg_id'] = arivale_entry.get('kegg', '')
                output['arivale_hmdb_id'] = arivale_entry.get('hmdb', '')
            else:
                # Mapped to PubChem but not in Arivale
                output['mapping_status'] = 'Mapped to PubChem - Not in Arivale'
        
        final_results.append(output)
    
    return final_results


def write_results(results: List[Dict[str, str]], output_path: str):
    """
    Write mapping results to TSV file.
    
    Args:
        results: List of mapping results
        output_path: Path to output TSV file
    """
    # Define column order
    columns = [
        'ukbb_field_id', 'ukbb_title', 'derived_pubchem_cid', 
        'rag_confidence_score', 'mapping_status', 'arivale_chemical_id',
        'arivale_biochemical_name', 'arivale_pubchem_id', 
        'arivale_kegg_id', 'arivale_hmdb_id'
    ]
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, delimiter='\t')
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"Results written to {output_path}")
        
    except Exception as e:
        logger.error(f"Error writing results: {e}")
        raise


def print_summary_statistics(results: List[Dict[str, str]]):
    """Print summary statistics of the mapping results."""
    # Count by mapping status
    status_counts = defaultdict(int)
    for result in results:
        status_counts[result['mapping_status']] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("UKBB to Arivale Metabolomics Mapping Summary")
    print("=" * 60)
    print(f"Total UKBB entries processed: {len(results)}")
    print(f"\nMapping Status Breakdown:")
    
    for status, count in sorted(status_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    # Additional statistics
    mapped_to_arivale = status_counts.get('Successfully Mapped to Arivale', 0)
    mapped_to_pubchem_only = status_counts.get('Mapped to PubChem - Not in Arivale', 0)
    failed_mappings = status_counts.get('RAG Mapping Failed', 0)
    
    total_pubchem_mapped = mapped_to_arivale + mapped_to_pubchem_only
    
    print(f"\nAdditional Statistics:")
    print(f"  Total mapped to PubChem: {total_pubchem_mapped} ({(total_pubchem_mapped/len(results))*100:.1f}%)")
    print(f"  Coverage in Arivale: {mapped_to_arivale}/{total_pubchem_mapped} ({(mapped_to_arivale/total_pubchem_mapped)*100:.1f}%)") if total_pubchem_mapped > 0 else None
    print("=" * 60)


async def main():
    """Main execution function."""
    # Input and output paths
    ukbb_path = "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv"
    arivale_path = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"
    output_dir = Path("/home/ubuntu/biomapper/output")
    output_path = output_dir / "ukbb_to_arivale_metabolomics_mapping.tsv"
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting UKBB to Arivale metabolomics mapping...")
    start_time = datetime.now()
    
    try:
        # Load data
        logger.info("Loading UKBB data...")
        ukbb_data = load_ukbb_data(ukbb_path)
        
        logger.info("Loading Arivale data...")
        arivale_lookup = load_arivale_data(arivale_path)
        
        # Map UKBB to PubChem using RAG
        logger.info("Mapping UKBB titles to PubChem CIDs...")
        mapping_results = await map_ukbb_to_pubchem(ukbb_data)
        
        # Match to Arivale entries
        logger.info("Matching PubChem CIDs to Arivale entries...")
        final_results = match_to_arivale(mapping_results, arivale_lookup)
        
        # Write results
        write_results(final_results, str(output_path))
        
        # Print summary
        print_summary_statistics(final_results)
        
        # Report completion time
        elapsed_time = datetime.now() - start_time
        logger.info(f"Mapping completed in {elapsed_time.total_seconds():.1f} seconds")
        
    except Exception as e:
        logger.error(f"Mapping failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
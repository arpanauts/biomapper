#!/usr/bin/env python3
"""
Test script for PubChemRAGMappingClient on Arivale metabolomics data.

This script validates the RAG client's ability to map metabolite names
from the Arivale dataset to PubChem CIDs.
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_arivale_sample(filepath: str, sample_size: int = 20) -> List[Dict[str, str]]:
    """
    Load a sample of Arivale metabolomics entries.
    
    Args:
        filepath: Path to the Arivale metabolomics metadata file
        sample_size: Number of entries to sample for testing
    
    Returns:
        List of dictionaries containing metabolite information
    """
    samples = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Skip metadata header lines (starting with #)
            for line in f:
                if not line.startswith('#'):
                    break
            
            # Read the column headers
            headers = line.strip().split('\t')
            reader = csv.DictReader(f, fieldnames=headers, delimiter='\t')
            
            # Collect samples with known PubChem IDs
            for row in reader:
                if row.get('PUBCHEM') and row['PUBCHEM'].strip() and row['PUBCHEM'] != 'NA':
                    samples.append({
                        'chemical_id': row.get('CHEMICAL_ID', ''),
                        'name': row.get('BIOCHEMICAL_NAME', ''),
                        'pubchem_cid': row.get('PUBCHEM', ''),
                        'kegg': row.get('KEGG', ''),
                        'hmdb': row.get('HMDB', '')
                    })
                    
                    if len(samples) >= sample_size:
                        break
            
            logger.info(f"Loaded {len(samples)} Arivale entries with PubChem IDs for testing")
            return samples
            
    except Exception as e:
        logger.error(f"Error loading Arivale data: {e}")
        raise


async def test_rag_mapping(samples: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Test PubChemRAGMappingClient on sample data.
    
    Args:
        samples: List of sample metabolites to test
    
    Returns:
        Dictionary with test results and statistics
    """
    # Initialize the RAG client
    try:
        rag_client = PubChemRAGMappingClient()
        logger.info("Successfully initialized PubChemRAGMappingClient")
        
        # Perform health check
        health_status = rag_client.health_check()
        logger.info(f"Health check: {health_status}")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG client: {e}")
        raise
    
    # Test mapping for each sample
    results = []
    correct_mappings = 0
    total_tested = 0
    
    for sample in samples:
        name = sample['name']
        ground_truth_cid = sample['pubchem_cid']
        
        try:
            # Map the metabolite name
            mapping_result = await rag_client.map_identifiers([name])
            
            if name in mapping_result:
                mapped_cids, _ = mapping_result[name]
                
                if mapped_cids:
                    # Extract CID from the first result (format: "PUBCHEM:12345")
                    top_mapped_cid = mapped_cids[0].replace("PUBCHEM:", "")
                    
                    # Check if mapping is correct
                    is_match = top_mapped_cid == ground_truth_cid
                    
                    # Get confidence score from search results (approximation based on result order)
                    confidence = 1.0 - (0.1 * min(len(mapped_cids) - 1, 5))
                    
                    results.append({
                        'input_name': name,
                        'ground_truth_cid': ground_truth_cid,
                        'rag_cids': [cid.replace("PUBCHEM:", "") for cid in mapped_cids],
                        'top_rag_cid': top_mapped_cid,
                        'confidence': confidence,
                        'match_status': 'MATCH' if is_match else 'MISMATCH',
                        'chemical_id': sample['chemical_id']
                    })
                    
                    if is_match:
                        correct_mappings += 1
                    total_tested += 1
                    
                else:
                    results.append({
                        'input_name': name,
                        'ground_truth_cid': ground_truth_cid,
                        'rag_cids': [],
                        'top_rag_cid': None,
                        'confidence': 0.0,
                        'match_status': 'NO_MAPPING',
                        'chemical_id': sample['chemical_id']
                    })
                    total_tested += 1
                    
        except Exception as e:
            logger.error(f"Error mapping '{name}': {e}")
            results.append({
                'input_name': name,
                'ground_truth_cid': ground_truth_cid,
                'rag_cids': [],
                'top_rag_cid': None,
                'confidence': 0.0,
                'match_status': 'ERROR',
                'chemical_id': sample['chemical_id']
            })
            total_tested += 1
    
    # Calculate statistics
    accuracy = correct_mappings / total_tested if total_tested > 0 else 0.0
    
    return {
        'results': results,
        'total_tested': total_tested,
        'correct_mappings': correct_mappings,
        'accuracy': accuracy,
        'no_mapping_count': sum(1 for r in results if r['match_status'] == 'NO_MAPPING'),
        'error_count': sum(1 for r in results if r['match_status'] == 'ERROR')
    }


def print_test_results(test_data: Dict[str, Any]):
    """Print formatted test results."""
    print("\n" + "=" * 80)
    print("PubChemRAGMappingClient Test Results")
    print("=" * 80)
    
    # Overall statistics
    print(f"\nOverall Statistics:")
    print(f"  Total Tested: {test_data['total_tested']}")
    print(f"  Correct Mappings: {test_data['correct_mappings']}")
    print(f"  Accuracy: {test_data['accuracy']:.2%}")
    print(f"  No Mapping Found: {test_data['no_mapping_count']}")
    print(f"  Errors: {test_data['error_count']}")
    
    # Detailed results
    print(f"\nDetailed Results:")
    print("-" * 80)
    print(f"{'Input Name':<40} {'Ground Truth':<12} {'RAG CID':<12} {'Confidence':<10} {'Status':<10}")
    print("-" * 80)
    
    for result in test_data['results']:
        name = result['input_name'][:39]  # Truncate long names
        ground_truth = result['ground_truth_cid']
        rag_cid = result['top_rag_cid'] if result['top_rag_cid'] else 'N/A'
        confidence = f"{result['confidence']:.3f}" if result['confidence'] > 0 else 'N/A'
        status = result['match_status']
        
        print(f"{name:<40} {ground_truth:<12} {rag_cid:<12} {confidence:<10} {status:<10}")
    
    print("-" * 80)


async def main():
    """Main test execution function."""
    # Path to Arivale metadata
    arivale_path = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"
    
    logger.info("Starting PubChemRAGMappingClient test...")
    
    try:
        # Load sample data
        samples = load_arivale_sample(arivale_path, sample_size=20)
        
        # Run tests
        test_results = await test_rag_mapping(samples)
        
        # Print results
        print_test_results(test_results)
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
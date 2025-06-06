#!/usr/bin/env python3
"""
UKBB NMR to Arivale Chemistries Mapping Script (MVP)

This script performs direct name matching between UKBB NMR metabolite data
and Arivale Chemistries metadata.

Author: Claude Code Assistant
Date: 2025-05-23
"""

import argparse
import csv
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/home/ubuntu/biomapper/output/ukbb_arivale_chemistries_mapping.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)


def load_ukbb_data(file_path: str) -> List[Dict[str, str]]:
    """
    Load UKBB NMR metadata from TSV file.
    
    Args:
        file_path: Path to UKBB_NMR_Meta.tsv
        
    Returns:
        List of dictionaries containing UKBB data
    """
    logger.info(f"Loading UKBB data from: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"UKBB file not found: {file_path}")
    
    ukbb_data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            ukbb_data.append({
                'field_id': row['field_id'],
                'title': row['title'],
                'group': row.get('Group', ''),
                'subgroup': row.get('Subgroup', '')
            })
    
    logger.info(f"Loaded {len(ukbb_data)} UKBB entries")
    return ukbb_data


def load_arivale_data(file_path: str) -> List[Dict[str, str]]:
    """
    Load Arivale Chemistries metadata from TSV file.
    Handles comment lines starting with '#'.
    
    Args:
        file_path: Path to chemistries_metadata.tsv
        
    Returns:
        List of dictionaries containing Arivale data
    """
    logger.info(f"Loading Arivale data from: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arivale file not found: {file_path}")
    
    arivale_data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        # Skip comment lines
        lines = []
        for line in f:
            if not line.startswith('#'):
                lines.append(line)
        
        # Parse TSV data
        reader = csv.DictReader(lines, delimiter='\t')
        
        # Log actual column names found
        if reader.fieldnames:
            logger.info(f"Arivale column names found: {reader.fieldnames}")
        
        for row in reader:
            arivale_data.append({
                'name': row.get('Name', ''),
                'display_name': row.get('Display Name', ''),
                'labcorp_id': row.get('Labcorp ID', ''),
                'labcorp_name': row.get('Labcorp Name', ''),
                'labcorp_loinc_id': row.get('Labcorp LOINC ID', ''),
                'labcorp_loinc_name': row.get('Labcorp LOINC Name', ''),
                'quest_id': row.get('Quest ID', ''),
                'quest_name': row.get('Quest Name', ''),
                'quest_loinc_id': row.get('Quest LOINC ID', '')
            })
    
    logger.info(f"Loaded {len(arivale_data)} Arivale entries")
    return arivale_data


def normalize_name(name: str) -> str:
    """
    Normalize a name for matching.
    Simple normalization: lowercase and strip whitespace.
    
    Args:
        name: Name to normalize
        
    Returns:
        Normalized name
    """
    if not name:
        return ''
    return name.lower().strip()


def perform_mapping(ukbb_data: List[Dict[str, str]], 
                   arivale_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Perform direct name matching between UKBB titles and Arivale names.
    
    Args:
        ukbb_data: List of UKBB entries
        arivale_data: List of Arivale entries
        
    Returns:
        List of mapping results
    """
    logger.info("Starting direct name matching...")
    
    # Create normalized lookup dictionaries for Arivale data
    arivale_by_display_name = {}
    arivale_by_name = {}
    
    for arivale_entry in arivale_data:
        # Index by Display Name
        display_name_norm = normalize_name(arivale_entry['display_name'])
        if display_name_norm and display_name_norm != 'na':
            if display_name_norm not in arivale_by_display_name:
                arivale_by_display_name[display_name_norm] = []
            arivale_by_display_name[display_name_norm].append(arivale_entry)
        
        # Index by Name
        name_norm = normalize_name(arivale_entry['name'])
        if name_norm and name_norm != 'na':
            if name_norm not in arivale_by_name:
                arivale_by_name[name_norm] = []
            arivale_by_name[name_norm].append(arivale_entry)
    
    # Perform mapping
    mapping_results = []
    for ukbb_entry in ukbb_data:
        ukbb_title_norm = normalize_name(ukbb_entry['title'])
        
        result = {
            'ukbb_field_id': ukbb_entry['field_id'],
            'ukbb_title': ukbb_entry['title'],
            'ukbb_group': ukbb_entry['group'],
            'ukbb_subgroup': ukbb_entry['subgroup'],
            'mapping_status': 'unmatched',
            'match_type': '',
            'arivale_name': '',
            'arivale_display_name': '',
            'arivale_labcorp_id': '',
            'arivale_labcorp_name': '',
            'arivale_labcorp_loinc_id': '',
            'arivale_labcorp_loinc_name': '',
            'arivale_quest_id': '',
            'arivale_quest_name': '',
            'arivale_quest_loinc_id': ''
        }
        
        # Try to match with Display Name first
        if ukbb_title_norm in arivale_by_display_name:
            matches = arivale_by_display_name[ukbb_title_norm]
            if len(matches) == 1:
                result['mapping_status'] = 'matched'
            else:
                result['mapping_status'] = 'multiple_matches'
            
            result['match_type'] = 'display_name'
            # Use the first match
            match = matches[0]
            result.update({
                'arivale_name': match['name'],
                'arivale_display_name': match['display_name'],
                'arivale_labcorp_id': match['labcorp_id'],
                'arivale_labcorp_name': match['labcorp_name'],
                'arivale_labcorp_loinc_id': match['labcorp_loinc_id'],
                'arivale_labcorp_loinc_name': match['labcorp_loinc_name'],
                'arivale_quest_id': match['quest_id'],
                'arivale_quest_name': match['quest_name'],
                'arivale_quest_loinc_id': match['quest_loinc_id']
            })
        
        # If no match with Display Name, try Name
        elif ukbb_title_norm in arivale_by_name:
            matches = arivale_by_name[ukbb_title_norm]
            if len(matches) == 1:
                result['mapping_status'] = 'matched'
            else:
                result['mapping_status'] = 'multiple_matches'
            
            result['match_type'] = 'name'
            # Use the first match
            match = matches[0]
            result.update({
                'arivale_name': match['name'],
                'arivale_display_name': match['display_name'],
                'arivale_labcorp_id': match['labcorp_id'],
                'arivale_labcorp_name': match['labcorp_name'],
                'arivale_labcorp_loinc_id': match['labcorp_loinc_id'],
                'arivale_labcorp_loinc_name': match['labcorp_loinc_name'],
                'arivale_quest_id': match['quest_id'],
                'arivale_quest_name': match['quest_name'],
                'arivale_quest_loinc_id': match['quest_loinc_id']
            })
        
        mapping_results.append(result)
    
    return mapping_results


def write_output(mapping_results: List[Dict[str, str]], output_path: str):
    """
    Write mapping results to TSV file.
    
    Args:
        mapping_results: List of mapping results
        output_path: Path to output TSV file
    """
    logger.info(f"Writing output to: {output_path}")
    
    # Define output columns in specified order
    output_columns = [
        'ukbb_field_id',
        'ukbb_title',
        'ukbb_group',
        'ukbb_subgroup',
        'mapping_status',
        'match_type',
        'arivale_name',
        'arivale_display_name',
        'arivale_labcorp_id',
        'arivale_labcorp_name',
        'arivale_labcorp_loinc_id',
        'arivale_labcorp_loinc_name',
        'arivale_quest_id',
        'arivale_quest_name',
        'arivale_quest_loinc_id'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_columns, delimiter='\t')
        writer.writeheader()
        writer.writerows(mapping_results)
    
    logger.info(f"Output written successfully")


def print_summary_statistics(mapping_results: List[Dict[str, str]]):
    """
    Print summary statistics of the mapping results.
    
    Args:
        mapping_results: List of mapping results
    """
    status_counts = defaultdict(int)
    match_type_counts = defaultdict(int)
    
    for result in mapping_results:
        status_counts[result['mapping_status']] += 1
        if result['match_type']:
            match_type_counts[result['match_type']] += 1
    
    print("\n" + "="*60)
    print("MAPPING SUMMARY STATISTICS")
    print("="*60)
    print(f"Total UKBB entries processed: {len(mapping_results)}")
    print("\nMapping Status Breakdown:")
    for status, count in sorted(status_counts.items()):
        percentage = (count / len(mapping_results)) * 100
        print(f"  - {status}: {count} ({percentage:.1f}%)")
    
    if match_type_counts:
        print("\nMatch Type Breakdown (for matched entries):")
        for match_type, count in sorted(match_type_counts.items()):
            print(f"  - {match_type}: {count}")
    
    print("="*60 + "\n")
    
    # Also log the summary
    logger.info("Mapping Summary Statistics:")
    logger.info(f"Total UKBB entries processed: {len(mapping_results)}")
    for status, count in sorted(status_counts.items()):
        percentage = (count / len(mapping_results)) * 100
        logger.info(f"  {status}: {count} ({percentage:.1f}%)")


def main():
    """Main function to orchestrate the mapping process."""
    parser = argparse.ArgumentParser(
        description='Map UKBB NMR metabolites to Arivale Chemistries using direct name matching'
    )
    parser.add_argument(
        '--ukbb-file',
        default='/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv',
        help='Path to UKBB NMR metadata file'
    )
    parser.add_argument(
        '--arivale-file',
        default='/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv',
        help='Path to Arivale chemistries metadata file'
    )
    parser.add_argument(
        '--output-file',
        default='/home/ubuntu/biomapper/output/ukbb_to_arivale_chemistries_mapping.tsv',
        help='Path to output mapping file'
    )
    
    args = parser.parse_args()
    
    try:
        # Load data
        ukbb_data = load_ukbb_data(args.ukbb_file)
        arivale_data = load_arivale_data(args.arivale_file)
        
        # Perform mapping
        mapping_results = perform_mapping(ukbb_data, arivale_data)
        
        # Write output
        write_output(mapping_results, args.output_file)
        
        # Print summary statistics
        print_summary_statistics(mapping_results)
        
        logger.info("Mapping completed successfully")
        
    except Exception as e:
        logger.error(f"Error during mapping: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
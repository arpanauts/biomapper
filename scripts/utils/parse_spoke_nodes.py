#!/usr/bin/env python3
"""
Parse SPOKE v6 nodes from JSONL file and extract entity information to CSV files.

This script processes the SPOKE v6 data file and extracts information for various
entity types into separate CSV files for use in the Biomapper project.

Usage:
    python parse_spoke_nodes.py --explore    # Run schema discovery only
    python parse_spoke_nodes.py              # Run full extraction
"""

import json
import csv
import os
import sys
import argparse
from typing import Dict, List, Any, Set
from collections import defaultdict
import datetime


# Configuration - Mapping SPOKE labels to output files and readable names
TARGET_ENTITY_CATEGORIES = {
    "Protein": {"file": "spoke_proteins.csv", "name": "Protein"},
    "Compound": {"file": "spoke_metabolites.csv", "name": "Metabolite"},
    "Gene": {"file": "spoke_genes.csv", "name": "Gene"},
    "Disease": {"file": "spoke_diseases.csv", "name": "Disease"},
    "Pathway": {"file": "spoke_pathways.csv", "name": "Pathway"},
    "Anatomy": {"file": "spoke_anatomy.csv", "name": "Anatomy"},
    "Variant": {"file": "spoke_variants.csv", "name": "Variant"},
    "ClinicalLab": {"file": "spoke_clinical_labs.csv", "name": "Clinical Lab"},
    "Symptom": {"file": "spoke_symptoms.csv", "name": "Symptom"},
    "EC": {"file": "spoke_ec_numbers.csv", "name": "EC Number"},
    "Organism": {"file": "spoke_organisms.csv", "name": "Organism"},
    "CellType": {"file": "spoke_cell_types.csv", "name": "Cell Type"},
}

# Absolute paths
INPUT_FILE = "/home/ubuntu/data/spokeV6.jsonl"
OUTPUT_DIR = "/home/ubuntu/biomapper/data/spoke_ontologies/"


def explore_schema(input_file: str, sample_size: int = 1000) -> None:
    """
    Analyze and report on the schema of the SPOKE JSONL file.
    
    Args:
        input_file: Path to the SPOKE JSONL file
        sample_size: Number of nodes to sample for schema analysis
    """
    print(f"\n{'='*80}")
    print(f"SPOKE Schema Discovery - {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Track schema information
    field_types = defaultdict(set)
    field_examples = defaultdict(list)
    label_counts = defaultdict(int)
    label_field_counts = defaultdict(lambda: defaultdict(int))
    
    nodes_processed = 0
    errors = 0
    
    print(f"Sampling up to {sample_size} nodes from {input_file}...\n")
    
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if nodes_processed >= sample_size:
                break
                
            try:
                data = json.loads(line.strip())
                
                # Only process nodes
                if data.get('type') != 'node':
                    continue
                    
                nodes_processed += 1
                
                # Track labels
                labels = data.get('labels', [])
                for label in labels:
                    label_counts[label] += 1
                
                # Track top-level fields
                for field, value in data.items():
                    field_type = type(value).__name__
                    field_types[field].add(field_type)
                    
                    # Collect examples (limit to 5 per field)
                    if len(field_examples[field]) < 5:
                        if isinstance(value, (list, dict)):
                            field_examples[field].append(json.dumps(value)[:100] + "...")
                        else:
                            field_examples[field].append(str(value)[:100])
                
                # Track properties for each label type
                if 'properties' in data and isinstance(data['properties'], dict):
                    for label in labels:
                        for prop_name in data['properties'].keys():
                            label_field_counts[label][prop_name] += 1
                
            except json.JSONDecodeError as e:
                errors += 1
                if errors <= 5:
                    print(f"JSON decode error on line {line_num}: {e}")
                continue
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"Error processing line {line_num}: {e}")
                continue
    
    # Report findings
    print(f"\n{'='*60}")
    print("SCHEMA DISCOVERY RESULTS")
    print(f"{'='*60}\n")
    
    print(f"Nodes processed: {nodes_processed}")
    print(f"Errors encountered: {errors}\n")
    
    print("TOP-LEVEL FIELDS:")
    print("-" * 40)
    for field, types in sorted(field_types.items()):
        print(f"\n{field}:")
        print(f"  Types: {', '.join(sorted(types))}")
        print(f"  Examples:")
        for example in field_examples[field][:3]:
            print(f"    - {example}")
    
    print(f"\n\nLABEL DISTRIBUTION:")
    print("-" * 40)
    for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{label:20} {count:10,d}")
    
    print(f"\n\nPROPERTIES BY LABEL TYPE:")
    print("-" * 40)
    for label in sorted(label_field_counts.keys()):
        if label in TARGET_ENTITY_CATEGORIES:
            print(f"\n{label}:")
            # Show top 10 most common properties
            props = sorted(label_field_counts[label].items(), 
                         key=lambda x: x[1], reverse=True)[:10]
            for prop_name, count in props:
                print(f"  {prop_name:30} (found in {count} nodes)")


def extract_list_field(value: Any, separator: str = "|") -> str:
    """
    Extract list field as a delimited string.
    
    Args:
        value: The field value (could be list, string, or None)
        separator: Delimiter to use for joining list items
        
    Returns:
        String representation of the field
    """
    if value is None:
        return ""
    elif isinstance(value, list):
        # Convert all items to strings and join
        return separator.join(str(item) for item in value)
    elif isinstance(value, str):
        return value
    else:
        return str(value)


def process_nodes(input_file: str, output_dir: str) -> None:
    """
    Process SPOKE nodes and extract to entity-specific CSV files.
    
    Args:
        input_file: Path to the SPOKE JSONL file
        output_dir: Directory to write CSV files
    """
    print(f"\n{'='*80}")
    print(f"SPOKE Node Extraction - {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}\n")
    
    # Initialize CSV writers
    csv_files = {}
    csv_writers = {}
    
    for label, config in TARGET_ENTITY_CATEGORIES.items():
        filepath = os.path.join(output_dir, config['file'])
        csv_files[label] = open(filepath, 'w', newline='', encoding='utf-8')
        csv_writers[label] = csv.writer(csv_files[label])
        # Write headers
        csv_writers[label].writerow(['id', 'name', 'category', 'description', 'synonyms', 'xrefs'])
        print(f"Created {config['file']} for {config['name']} entities")
    
    # Track statistics
    stats = defaultdict(int)
    nodes_processed = 0
    errors = 0
    
    print(f"\nProcessing {input_file}...")
    print("Progress updates every 100,000 nodes...\n")
    
    try:
        with open(input_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    
                    # Only process nodes
                    if data.get('type') != 'node':
                        continue
                    
                    nodes_processed += 1
                    
                    # Progress update
                    if nodes_processed % 100000 == 0:
                        print(f"Processed {nodes_processed:,} nodes...")
                        for label, count in sorted(stats.items()):
                            if count > 0:
                                print(f"  {label}: {count:,}")
                        print()
                    
                    # Get labels
                    labels = data.get('labels', [])
                    
                    # Process each matching label
                    for label in labels:
                        if label in TARGET_ENTITY_CATEGORIES:
                            stats[label] += 1
                            
                            # Extract properties
                            props = data.get('properties', {})
                            
                            # Extract ID (using 'identifier' field)
                            entity_id = props.get('identifier', data.get('id', ''))
                            
                            # Extract name
                            name = props.get('name', '')
                            
                            # Category is the label itself
                            category = label
                            
                            # Extract description
                            description = props.get('description', '')
                            
                            # Extract synonyms (could be in various fields)
                            synonyms = []
                            if 'synonyms' in props:
                                synonyms = props['synonyms']
                            elif 'synonym' in props:
                                synonyms = props['synonym']
                            synonyms_str = extract_list_field(synonyms)
                            
                            # Extract cross-references
                            xrefs = []
                            # Collect various xref fields based on entity type
                            if label == 'Protein':
                                # Collect RefSeq, ChEMBL, EC numbers
                                if 'refseq' in props:
                                    refseq = extract_list_field(props['refseq'], ';')
                                    if refseq:
                                        xrefs.append(f"RefSeq:{refseq}")
                                if 'chembl_id' in props and props['chembl_id'] != 'Null':
                                    xrefs.append(f"ChEMBL:{props['chembl_id']}")
                                if 'EC' in props:
                                    ec = extract_list_field(props['EC'], ';')
                                    if ec:
                                        xrefs.append(f"EC:{ec}")
                            elif label == 'Compound':
                                # Collect PubChem IDs
                                if 'pubchem_compound_ids' in props:
                                    pubchem = extract_list_field(props['pubchem_compound_ids'], ';')
                                    if pubchem:
                                        xrefs.append(f"PubChem:{pubchem}")
                                if 'pdb_ligand_ids' in props:
                                    pdb = extract_list_field(props['pdb_ligand_ids'], ';')
                                    if pdb:
                                        xrefs.append(f"PDB:{pdb}")
                            elif label == 'Gene':
                                # Collect Ensembl IDs
                                if 'ensembl' in props:
                                    xrefs.append(f"Ensembl:{props['ensembl']}")
                            elif label == 'Disease':
                                # Collect OMIM and MeSH
                                if 'omim_list' in props:
                                    omim = extract_list_field(props['omim_list'], ';')
                                    if omim:
                                        xrefs.append(f"OMIM:{omim}")
                                if 'mesh_list' in props:
                                    mesh = extract_list_field(props['mesh_list'], ';')
                                    if mesh:
                                        xrefs.append(f"MeSH:{mesh}")
                            elif label == 'Anatomy':
                                # Collect MeSH and BTO
                                if 'mesh_id' in props and props['mesh_id']:
                                    xrefs.append(f"MeSH:{props['mesh_id']}")
                                if 'bto' in props:
                                    bto = extract_list_field(props['bto'], ';')
                                    if bto:
                                        xrefs.append(f"BTO:{bto}")
                            
                            xrefs_str = '|'.join(xrefs)
                            
                            # Write to CSV
                            csv_writers[label].writerow([
                                entity_id,
                                name,
                                category,
                                description,
                                synonyms_str,
                                xrefs_str
                            ])
                    
                except json.JSONDecodeError as e:
                    errors += 1
                    if errors <= 5:
                        print(f"JSON decode error on line {line_num}: {e}")
                    continue
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"Error processing line {line_num}: {e}")
                    continue
    
    finally:
        # Close all CSV files
        for f in csv_files.values():
            f.close()
    
    # Final report
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}\n")
    
    print(f"Total nodes processed: {nodes_processed:,}")
    print(f"Total errors: {errors:,}\n")
    
    print("Entities extracted by type:")
    for label, count in sorted(stats.items()):
        config = TARGET_ENTITY_CATEGORIES[label]
        print(f"  {config['name']:20} {count:10,} -> {config['file']}")
    
    print(f"\nOutput files written to: {output_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse SPOKE v6 nodes and extract entity information to CSV files"
    )
    parser.add_argument(
        '--explore',
        action='store_true',
        help='Run schema discovery only (samples the file to understand structure)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    
    if args.explore:
        # Run schema discovery
        explore_schema(INPUT_FILE, sample_size=5000)
    else:
        # Run full extraction
        process_nodes(INPUT_FILE, OUTPUT_DIR)


if __name__ == "__main__":
    main()
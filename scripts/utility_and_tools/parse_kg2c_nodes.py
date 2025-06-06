#!/usr/bin/env python3
"""
Parse KG2c nodes JSONL file and extract ontological datasets by entity type.

This script processes the RTX KG2c (Knowledge Graph 2, canonicalized) node data
to extract structured ontological information for various entity types such as
proteins, metabolites, genes, diseases, etc.
"""

import json
import csv
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configuration
TARGET_ENTITY_CATEGORIES = {
    "biolink:Protein": {"file": "kg2c_proteins.csv", "name": "Protein"},
    "biolink:SmallMolecule": {"file": "kg2c_metabolites.csv", "name": "Metabolite"},
    "biolink:Gene": {"file": "kg2c_genes.csv", "name": "Gene"},
    "biolink:Disease": {"file": "kg2c_diseases.csv", "name": "Disease"},
    "biolink:PhenotypicFeature": {"file": "kg2c_phenotypes.csv", "name": "Phenotype"},
    "biolink:Pathway": {"file": "kg2c_pathways.csv", "name": "Pathway"},
    # Additional categories that might be useful
    "biolink:Drug": {"file": "kg2c_drugs.csv", "name": "Drug"},
    "biolink:ChemicalEntity": {"file": "kg2c_chemicals.csv", "name": "Chemical Entity"},
    "biolink:BiologicalProcess": {"file": "kg2c_biological_processes.csv", "name": "Biological Process"},
    "biolink:MolecularActivity": {"file": "kg2c_molecular_activities.csv", "name": "Molecular Activity"},
    "biolink:CellularComponent": {"file": "kg2c_cellular_components.csv", "name": "Cellular Component"},
}

# Paths
INPUT_FILE = "/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl"
OUTPUT_DIR = "/home/ubuntu/biomapper/data/kg2c_ontologies/"

# CSV Headers
CSV_HEADERS = ["id", "name", "category", "description", "synonyms", "xrefs"]


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def list_to_pipe_separated(items: Optional[List[str]]) -> str:
    """Convert a list of strings to a pipe-separated string."""
    if not items:
        return ""
    # Filter out None values and convert to strings
    return "|".join(str(item) for item in items if item is not None)


def extract_node_data(node: Dict[str, Any]) -> Dict[str, str]:
    """Extract relevant fields from a node JSON object."""
    return {
        "id": node.get("id", ""),
        "name": node.get("name", ""),
        "category": node.get("category", ""),
        "description": node.get("description", ""),
        "synonyms": list_to_pipe_separated(node.get("all_names", [])),
        "xrefs": list_to_pipe_separated(node.get("equivalent_curies", []))
    }


def explore_schema(num_lines: int = 20):
    """Explore the schema of the first few lines of the JSONL file."""
    print("\n=== Schema Discovery ===")
    print(f"Analyzing first {num_lines} lines of {INPUT_FILE}...\n")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= num_lines:
                    break
                
                try:
                    node = json.loads(line.strip())
                    if i == 0:
                        print(f"Keys in first node: {list(node.keys())}\n")
                    
                    print(f"Node {i + 1}:")
                    print(f"  ID: {node.get('id', 'N/A')}")
                    print(f"  Name: {node.get('name', 'N/A')}")
                    print(f"  Category: {node.get('category', 'N/A')}")
                    print(f"  Description: {node.get('description', 'N/A')[:100]}..." if node.get('description') else "  Description: N/A")
                    print(f"  All Names (first 3): {node.get('all_names', [])[:3]}")
                    print(f"  Equivalent CURIEs (first 3): {node.get('equivalent_curies', [])[:3]}")
                    print()
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {i + 1}: {e}")
                    
    except FileNotFoundError:
        print(f"Error: Input file not found: {INPUT_FILE}")
        sys.exit(1)


def process_nodes():
    """Process all nodes in the JSONL file and extract data by entity type."""
    print("\n=== Full Data Extraction ===")
    
    # Ensure output directory exists
    ensure_output_dir()
    
    # Initialize CSV writers for each entity type
    csv_files = {}
    csv_writers = {}
    entity_counts = {cat: 0 for cat in TARGET_ENTITY_CATEGORIES}
    
    try:
        # Open CSV files for each target category
        for category, info in TARGET_ENTITY_CATEGORIES.items():
            filepath = os.path.join(OUTPUT_DIR, info["file"])
            csv_files[category] = open(filepath, 'w', newline='', encoding='utf-8')
            csv_writers[category] = csv.DictWriter(csv_files[category], fieldnames=CSV_HEADERS)
            csv_writers[category].writeheader()
            print(f"Created output file: {filepath}")
        
        # Process the JSONL file
        total_nodes = 0
        errors = 0
        
        print(f"\nProcessing nodes from {INPUT_FILE}...")
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    node = json.loads(line.strip())
                    total_nodes += 1
                    
                    # Check if this node's category is one we're interested in
                    category = node.get("category")
                    if category in TARGET_ENTITY_CATEGORIES:
                        # Extract and write node data
                        node_data = extract_node_data(node)
                        csv_writers[category].writerow(node_data)
                        entity_counts[category] += 1
                    
                    # Progress update every 100,000 nodes
                    if total_nodes % 100000 == 0:
                        print(f"Processed {total_nodes:,} nodes...")
                        for cat, count in entity_counts.items():
                            if count > 0:
                                print(f"  {TARGET_ENTITY_CATEGORIES[cat]['name']}: {count:,}")
                
                except json.JSONDecodeError as e:
                    errors += 1
                    if errors <= 10:  # Only print first 10 errors
                        print(f"Error parsing line {line_num}: {e}")
                    elif errors == 11:
                        print("Suppressing further JSON parsing errors...")
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"Unexpected error on line {line_num}: {e}")
        
        print(f"\n=== Processing Complete ===")
        print(f"Total nodes processed: {total_nodes:,}")
        print(f"Total errors: {errors:,}")
        print(f"\nEntities extracted by category:")
        
        for category, count in entity_counts.items():
            print(f"  {TARGET_ENTITY_CATEGORIES[category]['name']}: {count:,}")
            
    finally:
        # Close all CSV files
        for f in csv_files.values():
            f.close()


def main():
    """Main function to run the script."""
    print(f"KG2c Node Parser - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    
    # Part A: Schema discovery (optional, for debugging/exploration)
    if "--explore" in sys.argv:
        explore_schema()
        return
    
    # Part B: Full data extraction
    process_nodes()
    
    print(f"\nCompleted at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
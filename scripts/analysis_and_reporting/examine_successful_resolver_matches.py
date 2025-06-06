#!/usr/bin/env python
"""
Examine successful name resolver matches in the three output files.

This script prints a few examples of successful matches from each file to
better understand the resolver's behavior.
"""

import pandas as pd

# Paths to the three output files
CHEMISTRIES_OUTPUT_PATH = "/home/ubuntu/biomapper/chemistries_metadata_with_resolver.tsv"
UKBB_NMR_OUTPUT_PATH = "/home/ubuntu/biomapper/UKBB_NMR_Meta_with_resolver.tsv"
METABOLOMICS_OUTPUT_PATH = "/home/ubuntu/biomapper/metabolomics_metadata_with_resolver.tsv"

def examine_successful_matches(file_path, name_column, existing_id_column=None, max_examples=5):
    """
    Examine successful matches for a given file.
    
    Args:
        file_path: Path to the TSV file with resolver results
        name_column: Name of the column containing the entity names
        existing_id_column: Name of the column containing existing IDs, if any
        max_examples: Maximum number of examples to print
    """
    print(f"\n{'='*80}\nExamining successful matches in {file_path}\n{'='*80}")
    
    # Read the file, handling commented lines if needed
    if "metabolomics" in file_path or "chemistries" in file_path:
        df = pd.read_csv(file_path, sep='\t', comment='#', quotechar='"')
    else:
        df = pd.read_csv(file_path, sep='\t')
    
    # Determine the column names for the resolver results
    if "metabolomics" in file_path:
        id_column = "PUBCHEM_Resolver_IDs"
        confidence_column = "PUBCHEM_Resolver_Confidence"
    else:
        id_column = "PUBCHEM_IDs"
        confidence_column = "PUBCHEM_Confidence"
    
    # Filter for successful matches
    successful = df[df[id_column].str.len() > 0]
    
    if len(successful) == 0:
        print("No successful matches found!")
        return
    
    print(f"Found {len(successful)} successful matches. Showing up to {max_examples}:")
    
    # Print examples
    for i, (idx, row) in enumerate(successful.iterrows()):
        if i >= max_examples:
            break
        
        print(f"\nExample {i+1}:")
        print(f"  {name_column}: {row[name_column]}")
        print(f"  {id_column}: {row[id_column]}")
        print(f"  {confidence_column}: {row[confidence_column]}")
        
        # Print existing ID if available
        if existing_id_column and existing_id_column in df.columns:
            print(f"  {existing_id_column}: {row[existing_id_column]}")
            
            # Check if existing ID is in the resolver results
            existing_id = str(row[existing_id_column])
            resolved_ids = str(row[id_column])
            
            if existing_id and existing_id != "nan" and resolved_ids:
                if existing_id in resolved_ids.split(','):
                    print("  ✅ Existing ID found in resolver results!")
                else:
                    print("  ❌ Existing ID not found in resolver results.")

def main():
    """
    Main entry point for the script.
    """
    # Examine successful matches for each file
    examine_successful_matches(CHEMISTRIES_OUTPUT_PATH, "Name")
    examine_successful_matches(UKBB_NMR_OUTPUT_PATH, "title")
    examine_successful_matches(METABOLOMICS_OUTPUT_PATH, "BIOCHEMICAL_NAME", "PUBCHEM")

if __name__ == "__main__":
    main()
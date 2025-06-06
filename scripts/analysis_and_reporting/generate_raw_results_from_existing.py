#!/usr/bin/env python
"""
Generate simplified CSV files with raw name resolver results from existing files.

This script creates CSV files with raw name resolver results, limiting to
10 mappings per entry and including only the relevant columns.
"""

import pandas as pd
import os

# Paths to the three output files
CHEMISTRIES_OUTPUT_PATH = "/home/ubuntu/biomapper/chemistries_metadata_with_resolver.tsv"
UKBB_NMR_OUTPUT_PATH = "/home/ubuntu/biomapper/UKBB_NMR_Meta_with_resolver.tsv"
METABOLOMICS_OUTPUT_PATH = "/home/ubuntu/biomapper/metabolomics_metadata_with_resolver.tsv"

# Paths to the simplified CSV files
CHEMISTRIES_CSV_PATH = "/home/ubuntu/biomapper/chemistries_resolver_results.csv"
UKBB_NMR_CSV_PATH = "/home/ubuntu/biomapper/ukbb_nmr_resolver_results.csv"
METABOLOMICS_CSV_PATH = "/home/ubuntu/biomapper/metabolomics_resolver_results.csv"

# Single-entry CSV for visualization
ALL_ENTRIES_CSV_PATH = "/home/ubuntu/biomapper/all_resolver_results.csv"

def limit_mappings(id_str, max_mappings=10):
    """
    Limit the number of mappings in a comma-separated string.
    
    Args:
        id_str: Comma-separated string of IDs
        max_mappings: Maximum number of mappings to include
        
    Returns:
        Limited comma-separated string of IDs
    """
    if not id_str or pd.isna(id_str) or id_str == "":
        return ""
    
    ids = str(id_str).split(',')
    if len(ids) <= max_mappings:
        return str(id_str)
    else:
        return ','.join(ids[:max_mappings]) + f"... ({len(ids) - max_mappings} more)"

def process_chemistries_metadata():
    """
    Process the chemistries metadata file and create a simplified CSV.
    """
    print(f"Processing chemistries metadata file: {CHEMISTRIES_OUTPUT_PATH}")
    
    # Read the TSV file with pandas, handling commented lines
    df = pd.read_csv(CHEMISTRIES_OUTPUT_PATH, sep='\t', comment='#', quotechar='"')
    
    # Create a simplified DataFrame with only the relevant columns
    simplified_df = pd.DataFrame({
        'Name': df['Name'],
        'PUBCHEM_IDs': df['PUBCHEM_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'PUBCHEM_Confidence': df['PUBCHEM_Confidence'],
        'CHEBI_IDs': df['CHEBI_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'CHEBI_Confidence': df['CHEBI_Confidence'],
        'HMDB_IDs': df['HMDB_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'HMDB_Confidence': df['HMDB_Confidence']
    })
    
    # Add a source column
    simplified_df['Source'] = 'Chemistries'
    
    # Write to CSV
    simplified_df.to_csv(CHEMISTRIES_CSV_PATH, index=False)
    print(f"Wrote simplified chemistries metadata to {CHEMISTRIES_CSV_PATH}")
    
    return simplified_df

def process_ukbb_nmr_metadata():
    """
    Process the UKBB NMR metadata file and create a simplified CSV.
    """
    print(f"Processing UKBB NMR metadata file: {UKBB_NMR_OUTPUT_PATH}")
    
    # Read the TSV file with pandas
    df = pd.read_csv(UKBB_NMR_OUTPUT_PATH, sep='\t')
    
    # Create a simplified DataFrame with only the relevant columns
    simplified_df = pd.DataFrame({
        'Name': df['title'],
        'PUBCHEM_IDs': df['PUBCHEM_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'PUBCHEM_Confidence': df['PUBCHEM_Confidence'],
        'CHEBI_IDs': df['CHEBI_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'CHEBI_Confidence': df['CHEBI_Confidence'],
        'HMDB_IDs': df['HMDB_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'HMDB_Confidence': df['HMDB_Confidence']
    })
    
    # Add a source column
    simplified_df['Source'] = 'UKBB_NMR'
    
    # Write to CSV
    simplified_df.to_csv(UKBB_NMR_CSV_PATH, index=False)
    print(f"Wrote simplified UKBB NMR metadata to {UKBB_NMR_CSV_PATH}")
    
    return simplified_df

def process_metabolomics_metadata():
    """
    Process the metabolomics metadata file and create a simplified CSV.
    """
    print(f"Processing metabolomics metadata file: {METABOLOMICS_OUTPUT_PATH}")
    
    # Read the TSV file with pandas, handling commented lines
    df = pd.read_csv(METABOLOMICS_OUTPUT_PATH, sep='\t', comment='#', quotechar='"')
    
    # Create a simplified DataFrame with only the relevant columns
    simplified_df = pd.DataFrame({
        'Name': df['BIOCHEMICAL_NAME'],
        'Original_PUBCHEM': df['PUBCHEM'],
        'PUBCHEM_IDs': df['PUBCHEM_Resolver_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'PUBCHEM_Confidence': df['PUBCHEM_Resolver_Confidence'],
        'CHEBI_IDs': df['CHEBI_Resolver_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'CHEBI_Confidence': df['CHEBI_Resolver_Confidence'],
        'HMDB_IDs': df['HMDB_Resolver_IDs'].apply(lambda x: limit_mappings(x) if pd.notna(x) else ""),
        'HMDB_Confidence': df['HMDB_Resolver_Confidence']
    })
    
    # Add a source column
    simplified_df['Source'] = 'Metabolomics'
    
    # Write to CSV
    simplified_df.to_csv(METABOLOMICS_CSV_PATH, index=False)
    print(f"Wrote simplified metabolomics metadata to {METABOLOMICS_CSV_PATH}")
    
    return simplified_df

def create_combined_csv(chemistries_df, ukbb_df, metabolomics_df):
    """
    Create a combined CSV with all entries.
    """
    print("Creating combined CSV with all entries")
    
    # Combine all DataFrames
    all_df = pd.concat([chemistries_df, ukbb_df, metabolomics_df], ignore_index=True)
    
    # Create a single-entry CSV with all successful mappings
    successful = all_df[
        (all_df['PUBCHEM_IDs'] != "") | 
        (all_df['CHEBI_IDs'] != "") | 
        (all_df['HMDB_IDs'] != "")
    ]
    
    # Write to CSV
    successful.to_csv(ALL_ENTRIES_CSV_PATH, index=False)
    print(f"Wrote combined CSV with {len(successful)} successful mappings to {ALL_ENTRIES_CSV_PATH}")

def create_separate_mappings_files():
    """
    Create separate files for individual mappings.
    """
    print("Creating separate files for individual mappings")
    
    # For all three sources and all three target databases, generate files with
    # one row per name-ID mapping pair
    
    # First, process chemistries metadata
    chemistries_df = pd.read_csv(CHEMISTRIES_CSV_PATH)
    for target_db in ["PUBCHEM", "CHEBI", "HMDB"]:
        rows = []
        for _, row in chemistries_df.iterrows():
            name = row['Name']
            ids_str = row[f'{target_db}_IDs']
            confidence = row[f'{target_db}_Confidence']
            
            if ids_str and pd.notna(ids_str) and "..." not in ids_str:  # Skip truncated lists
                ids = str(ids_str).split(',')
                for id in ids:
                    rows.append({
                        'Name': name,
                        'ID': id,
                        'Confidence': confidence,
                        'Source': 'Chemistries'
                    })
        
        # Create DataFrame and write to CSV
        if rows:
            mappings_df = pd.DataFrame(rows)
            path = f"/home/ubuntu/biomapper/chemistries_{target_db.lower()}_individual_mappings.csv"
            mappings_df.to_csv(path, index=False)
            print(f"Wrote {len(rows)} individual {target_db} mappings for chemistries to {path}")
    
    # Then, process UKBB NMR metadata
    ukbb_df = pd.read_csv(UKBB_NMR_CSV_PATH)
    for target_db in ["PUBCHEM", "CHEBI", "HMDB"]:
        rows = []
        for _, row in ukbb_df.iterrows():
            name = row['Name']
            ids_str = row[f'{target_db}_IDs']
            confidence = row[f'{target_db}_Confidence']
            
            if ids_str and pd.notna(ids_str) and "..." not in ids_str:  # Skip truncated lists
                ids = str(ids_str).split(',')
                for id in ids:
                    rows.append({
                        'Name': name,
                        'ID': id,
                        'Confidence': confidence,
                        'Source': 'UKBB_NMR'
                    })
        
        # Create DataFrame and write to CSV
        if rows:
            mappings_df = pd.DataFrame(rows)
            path = f"/home/ubuntu/biomapper/ukbb_nmr_{target_db.lower()}_individual_mappings.csv"
            mappings_df.to_csv(path, index=False)
            print(f"Wrote {len(rows)} individual {target_db} mappings for UKBB NMR to {path}")
    
    # Finally, process metabolomics metadata
    metabolomics_df = pd.read_csv(METABOLOMICS_CSV_PATH)
    for target_db in ["PUBCHEM", "CHEBI", "HMDB"]:
        rows = []
        for _, row in metabolomics_df.iterrows():
            name = row['Name']
            ids_str = row[f'{target_db}_IDs']
            confidence = row[f'{target_db}_Confidence']
            
            if ids_str and pd.notna(ids_str) and "..." not in ids_str:  # Skip truncated lists
                ids = str(ids_str).split(',')
                for id in ids:
                    rows.append({
                        'Name': name,
                        'ID': id,
                        'Confidence': confidence,
                        'Source': 'Metabolomics'
                    })
        
        # Create DataFrame and write to CSV
        if rows:
            mappings_df = pd.DataFrame(rows)
            path = f"/home/ubuntu/biomapper/metabolomics_{target_db.lower()}_individual_mappings.csv"
            mappings_df.to_csv(path, index=False)
            print(f"Wrote {len(rows)} individual {target_db} mappings for metabolomics to {path}")

def main():
    """
    Main entry point for the script.
    """
    # Process each file and create simplified CSVs
    chemistries_df = process_chemistries_metadata()
    ukbb_df = process_ukbb_nmr_metadata()
    metabolomics_df = process_metabolomics_metadata()
    
    # Create a combined CSV with all entries
    create_combined_csv(chemistries_df, ukbb_df, metabolomics_df)
    
    # Create separate files for individual mappings
    create_separate_mappings_files()
    
    print("Done!")

if __name__ == "__main__":
    main()
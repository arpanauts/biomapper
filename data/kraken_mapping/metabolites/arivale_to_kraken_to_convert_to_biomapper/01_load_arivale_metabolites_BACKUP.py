#!/usr/bin/env python3
"""
Proto-action: Load and normalize Arivale metabolomics data
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_FILE = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def normalize_hmdb_id(value):
    """Normalize HMDB ID to standard format."""
    if pd.isna(value) or value is None:
        return None

    str_value = str(value).strip()

    # Check for empty or invalid strings
    if str_value in ['', 'nan', 'None', 'NaN', 'null']:
        return None

    # Handle HMDB format
    if str_value.startswith('HMDB'):
        return str_value.upper()

    # Handle numeric HMDB (pad to proper format)
    if str_value.isdigit():
        # Pad to 7 digits after HMDB prefix
        return f"HMDB{str_value.zfill(7)}"

    return None

def normalize_pubchem_id(value):
    """Normalize PubChem ID to standard format."""
    if pd.isna(value) or value is None:
        return None

    str_value = str(value).strip()

    # Check for empty or invalid strings
    if str_value in ['', 'nan', 'None', 'NaN', 'null']:
        return None

    # Handle decimal notation
    if '.' in str_value:
        try:
            # Convert to int to remove decimal, then to string
            str_value = str(int(float(str_value)))
        except (ValueError, TypeError):
            return None

    # Validate that result is numeric
    if str_value.isdigit():
        return str_value

    return None

def main():
    """Load and clean Arivale metabolomics data."""
    print("Loading Arivale metabolomics data...")

    # Load data, skipping comment lines
    df = pd.read_csv(INPUT_FILE, sep='\t', comment='#')

    print(f"Loaded {len(df)} metabolites from Arivale")
    print(f"Columns: {list(df.columns)}")

    # Clean and normalize the data
    df_clean = df.copy()

    # Create a unique metabolite ID from CHEMICAL_ID
    df_clean['arivale_metabolite_id'] = df_clean['CHEMICAL_ID'].astype(str)

    # Normalize identifiers
    df_clean['hmdb_normalized'] = df_clean['HMDB'].apply(normalize_hmdb_id)
    df_clean['pubchem_normalized'] = df_clean['PUBCHEM'].apply(normalize_pubchem_id)

    # Clean biochemical name
    df_clean['metabolite_name'] = df_clean['BIOCHEMICAL_NAME'].str.strip()

    # Add pathway information
    df_clean['super_pathway'] = df_clean['SUPER_PATHWAY']
    df_clean['sub_pathway'] = df_clean['SUB_PATHWAY']

    # Create mapping ready columns
    columns_to_keep = [
        'arivale_metabolite_id',
        'metabolite_name',
        'hmdb_normalized',
        'pubchem_normalized',
        'super_pathway',
        'sub_pathway',
        'KEGG',
        'CAS'
    ]

    df_final = df_clean[columns_to_keep].copy()

    # Report statistics
    total_metabolites = len(df_final)
    with_hmdb = len(df_final[df_final['hmdb_normalized'].notna()])
    with_pubchem = len(df_final[df_final['pubchem_normalized'].notna()])
    with_either = len(df_final[(df_final['hmdb_normalized'].notna()) |
                             (df_final['pubchem_normalized'].notna())])

    print(f"\nArivale Metabolites Summary:")
    print(f"Total metabolites: {total_metabolites}")
    print(f"With HMDB ID: {with_hmdb} ({100*with_hmdb/total_metabolites:.1f}%)")
    print(f"With PubChem ID: {with_pubchem} ({100*with_pubchem/total_metabolites:.1f}%)")
    print(f"With either ID: {with_either} ({100*with_either/total_metabolites:.1f}%)")

    # Save cleaned data
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / "arivale_metabolites_clean.tsv"
    df_final.to_csv(output_file, sep='\t', index=False)

    print(f"\nSaved cleaned data to: {output_file}")

    # Show sample of data
    print(f"\nSample data:")
    print(df_final.head(3).to_string())

if __name__ == "__main__":
    main()
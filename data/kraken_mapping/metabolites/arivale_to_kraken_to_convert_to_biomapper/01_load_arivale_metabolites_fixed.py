#!/usr/bin/env python3
"""
Proto-action: Load and clean Arivale metabolites (FIXED)
Properly normalizes HMDB IDs to 7-digit format for Kraken matching
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_FILE = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def normalize_hmdb_id(hmdb_id):
    """Normalize HMDB ID to 7-digit format (e.g., HMDB0000001)."""
    if pd.isna(hmdb_id) or str(hmdb_id).strip() == '':
        return np.nan

    hmdb_str = str(hmdb_id).strip()

    # Remove quotes if present
    hmdb_str = hmdb_str.strip('"').strip("'")

    # Extract the numeric part
    if hmdb_str.upper().startswith('HMDB'):
        numeric_part = hmdb_str[4:]
        # Pad to 7 digits
        if numeric_part.isdigit():
            return f"HMDB{numeric_part.zfill(7)}"

    return np.nan

def normalize_pubchem_id(pubchem_id):
    """Normalize PubChem ID to numeric format."""
    if pd.isna(pubchem_id) or str(pubchem_id).strip() == '':
        return np.nan

    pubchem_str = str(pubchem_id).strip()

    # Remove any non-numeric characters
    if pubchem_str.replace('.', '').replace('-', '').isdigit():
        # Handle scientific notation or decimals
        try:
            return str(int(float(pubchem_str)))
        except:
            return np.nan

    return np.nan

def main():
    print("Loading Arivale metabolomics data...")

    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read the file, skipping comment lines
    df = pd.read_csv(INPUT_FILE, sep='\t', comment='#')

    print(f"Loaded {len(df)} metabolites from Arivale")
    print(f"Columns: {list(df.columns)}")

    # Clean and normalize identifiers
    print("\nNormalizing identifiers...")

    # Normalize HMDB to 7-digit format for Kraken
    df['hmdb_normalized'] = df['HMDB'].apply(normalize_hmdb_id)

    # Normalize PubChem
    df['pubchem_normalized'] = df['PUBCHEM'].apply(normalize_pubchem_id)

    # Create a unique identifier for each metabolite
    df['arivale_metabolite_id'] = df['CHEMICAL_ID']

    # Select and rename columns for output
    output_columns = {
        'arivale_metabolite_id': 'arivale_metabolite_id',
        'BIOCHEMICAL_NAME': 'metabolite_name',
        'hmdb_normalized': 'hmdb_normalized',
        'pubchem_normalized': 'pubchem_normalized',
        'SUPER_PATHWAY': 'super_pathway',
        'SUB_PATHWAY': 'sub_pathway',
        'KEGG': 'KEGG',
        'CAS': 'CAS'
    }

    clean_df = df[list(output_columns.keys())].rename(columns=output_columns)

    # Save cleaned data
    output_file = OUTPUT_DIR / "arivale_metabolites_clean.tsv"
    clean_df.to_csv(output_file, sep='\t', index=False)

    # Print summary statistics
    print(f"\nArivale Metabolites Summary:")
    print(f"Total metabolites: {len(clean_df)}")

    # Count valid identifiers
    hmdb_count = clean_df['hmdb_normalized'].notna().sum()
    pubchem_count = clean_df['pubchem_normalized'].notna().sum()
    either_count = (clean_df['hmdb_normalized'].notna() | clean_df['pubchem_normalized'].notna()).sum()

    print(f"With HMDB ID: {hmdb_count} ({100*hmdb_count/len(clean_df):.1f}%)")
    print(f"With PubChem ID: {pubchem_count} ({100*pubchem_count/len(clean_df):.1f}%)")
    print(f"With either ID: {either_count} ({100*either_count/len(clean_df):.1f}%)")

    # Show sample of HMDB IDs to verify format
    print(f"\nSample normalized HMDB IDs (7-digit format):")
    sample_hmdb = clean_df[clean_df['hmdb_normalized'].notna()]['hmdb_normalized'].head(10)
    for hmdb in sample_hmdb:
        print(f"  {hmdb}")

    print(f"\nSaved cleaned data to: {output_file}")

    # Show sample of the data
    print("\nSample data:")
    print(clean_df[['arivale_metabolite_id', 'metabolite_name', 'hmdb_normalized', 'pubchem_normalized', 'super_pathway']].head(3))

    print("\n✓ Step 1 completed successfully!")

if __name__ == "__main__":
    main()
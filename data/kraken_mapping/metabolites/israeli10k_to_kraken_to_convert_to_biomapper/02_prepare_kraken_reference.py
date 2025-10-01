#!/usr/bin/env python3
"""
Proto-strategy Script 2: Prepare Kraken chemical reference data
This is a STANDALONE script for Israeli10K Nightingale to Kraken mapping
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "kraken_chebi_prepared.tsv"

def extract_chebi_id(kraken_id):
    """Extract numeric ChEBI ID from Kraken ID format"""
    if pd.isna(kraken_id) or str(kraken_id).strip() == '':
        return None

    id_str = str(kraken_id).strip()
    if id_str.startswith('CHEBI:'):
        return id_str.replace('CHEBI:', '').strip()
    return None

def clean_description(desc):
    """Clean and truncate description for readability"""
    if pd.isna(desc):
        return ""
    desc_str = str(desc).strip()
    # Truncate long descriptions
    if len(desc_str) > 200:
        desc_str = desc_str[:200] + "..."
    return desc_str

def main():
    print("="*60)
    print("ISRAELI10K NIGHTINGALE TO KRAKEN MAPPING - STEP 2")
    print("Preparing Kraken chemical reference data")
    print("="*60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Load Kraken chemicals data
        print(f"Loading Kraken chemicals from: {INPUT_FILE}")
        print("Note: This is a large file, may take a moment...")

        # Read in chunks to handle large file efficiently
        chunk_size = 10000
        chebi_chunks = []

        for chunk in pd.read_csv(INPUT_FILE, chunksize=chunk_size):
            # Filter to ChEBI entries only
            chebi_chunk = chunk[chunk['id'].str.startswith('CHEBI:', na=False)]
            if not chebi_chunk.empty:
                chebi_chunks.append(chebi_chunk)

        if not chebi_chunks:
            raise ValueError("No ChEBI entries found in Kraken chemicals file")

        # Combine all ChEBI chunks
        kraken_chebi_df = pd.concat(chebi_chunks, ignore_index=True)
        print(f"Found {len(kraken_chebi_df)} ChEBI entries in Kraken database")

        # Extract numeric ChEBI IDs for joining
        print("Extracting numeric ChEBI IDs for joining...")
        kraken_chebi_df['chebi_id_for_join'] = kraken_chebi_df['id'].apply(extract_chebi_id)

        # Remove any rows where ID extraction failed
        valid_chebi_df = kraken_chebi_df[kraken_chebi_df['chebi_id_for_join'].notna()].copy()
        print(f"Retained {len(valid_chebi_df)} valid ChEBI entries")

        # Clean descriptions
        valid_chebi_df['description_clean'] = valid_chebi_df['description'].apply(clean_description)

        # Select and rename columns for output
        output_columns = {
            'id': 'kraken_node_id',
            'name': 'kraken_name',
            'category': 'kraken_category',
            'description_clean': 'kraken_description',
            'synonyms': 'kraken_synonyms',
            'xrefs': 'kraken_xrefs',
            'chebi_id_for_join': 'chebi_id_for_join'
        }

        prepared_df = valid_chebi_df[list(output_columns.keys())].rename(columns=output_columns)

        # Add chemical classification
        prepared_df['chemical_class'] = 'chemical_entity'

        # Save prepared reference data
        prepared_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        print(f"\nSaved prepared Kraken reference to: {OUTPUT_FILE}")
        print(f"Prepared {len(prepared_df)} ChEBI entries for joining")

        # Show sample of prepared data
        print("\nSample of prepared Kraken ChEBI data:")
        sample_cols = ['kraken_node_id', 'kraken_name', 'chebi_id_for_join']
        print(prepared_df[sample_cols].head())

        # Summary statistics
        print(f"\nSummary statistics:")
        print(f"- Total ChEBI entries: {len(prepared_df)}")
        print(f"- Unique categories: {prepared_df['kraken_category'].nunique()}")
        if len(prepared_df) > 0:
            print(f"- Sample categories: {', '.join(prepared_df['kraken_category'].value_counts().head().index.tolist())}")

        print("\n✅ Step 2 completed successfully!")

    except Exception as e:
        print(f"❌ Error in Step 2: {str(e)}")
        raise

if __name__ == "__main__":
    main()
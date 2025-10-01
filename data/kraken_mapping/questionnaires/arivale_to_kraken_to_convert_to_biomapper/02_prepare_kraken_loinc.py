#!/usr/bin/env python3
"""
Proto-strategy: Prepare Kraken 1.0.0 LOINC clinical findings
This is a STANDALONE script for loading and preparing Kraken LOINC nodes for joining
"""
import pandas as pd
from pathlib import Path

# Input file path
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    print("Loading Kraken 1.0.0 clinical findings with LOINC codes...")

    # Load the Kraken clinical findings CSV file
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"Loaded {len(df)} total Kraken clinical findings")
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return

    # Display column information
    print(f"Columns: {list(df.columns)}")
    print(f"Shape: {df.shape}")

    # Show initial statistics
    print("\n=== INITIAL STATISTICS ===")
    print(f"Total clinical findings: {len(df)}")

    # Check that we have LOINC IDs
    loinc_entries = df['id'].str.startswith('LOINC:', na=False)
    print(f"LOINC entries (start with 'LOINC:'): {loinc_entries.sum()}")

    if loinc_entries.sum() == 0:
        print("WARNING: No LOINC entries found!")
        return

    # Filter for LOINC entries only
    kraken_loinc = df[loinc_entries].copy()
    print(f"Filtered to LOINC entries: {len(kraken_loinc)}")

    # Clean and prepare the data
    print("\n=== PREPARING DATA ===")

    # Extract clean LOINC code (remove "LOINC:" prefix for joining)
    kraken_loinc['clean_loinc'] = kraken_loinc['id'].str.replace('LOINC:', '', regex=False)
    print(f"Extracted clean LOINC codes")

    # Verify clean LOINC codes
    print(f"Sample clean LOINC codes: {kraken_loinc['clean_loinc'].head().tolist()}")

    # Remove any entries with empty clean LOINC codes
    kraken_loinc = kraken_loinc[kraken_loinc['clean_loinc'].str.len() > 0]
    print(f"After removing empty LOINC codes: {len(kraken_loinc)}")

    # Check for duplicates
    duplicates = kraken_loinc['clean_loinc'].duplicated().sum()
    print(f"Duplicate LOINC codes: {duplicates}")

    if duplicates > 0:
        print("Removing duplicates, keeping first occurrence...")
        kraken_loinc = kraken_loinc.drop_duplicates(subset=['clean_loinc'], keep='first')
        print(f"After removing duplicates: {len(kraken_loinc)}")

    # Select and rename columns for clarity
    output_columns = ['id', 'name', 'category', 'description', 'clean_loinc']
    if 'synonyms' in kraken_loinc.columns:
        output_columns.insert(-1, 'synonyms')
    if 'xrefs' in kraken_loinc.columns:
        output_columns.insert(-1, 'xrefs')

    output_df = kraken_loinc[output_columns].copy()

    # Rename columns for clarity
    output_df = output_df.rename(columns={
        'id': 'kraken_id',
        'name': 'kraken_name',
        'category': 'kraken_category',
        'description': 'kraken_description'
    })

    # Add metadata
    output_df['source'] = 'kraken_1.0.0'
    output_df['entity_type'] = 'clinical_finding'

    # Save the prepared data
    output_file = OUTPUT_DIR / "kraken_clinical_findings.tsv"
    output_df.to_csv(output_file, sep='\t', index=False)

    print(f"\n=== RESULTS ===")
    print(f"Saved {len(output_df)} Kraken LOINC clinical findings to {output_file}")
    print(f"Unique LOINC codes: {output_df['clean_loinc'].nunique()}")

    # Show some statistics about the data
    print(f"\n=== KRAKEN DATA STATISTICS ===")
    print(f"Clinical findings with names: {output_df['kraken_name'].notna().sum()}")
    print(f"Clinical findings with descriptions: {output_df['kraken_description'].notna().sum()}")

    # Show sample of results
    print(f"\n=== SAMPLE DATA ===")
    print(output_df[['kraken_id', 'kraken_name', 'clean_loinc']].head())

    print(f"\n✅ Successfully prepared Kraken LOINC clinical findings")
    print(f"   Input: {len(df)} total clinical findings")
    print(f"   Output: {len(output_df)} LOINC clinical findings ready for mapping")

if __name__ == "__main__":
    main()
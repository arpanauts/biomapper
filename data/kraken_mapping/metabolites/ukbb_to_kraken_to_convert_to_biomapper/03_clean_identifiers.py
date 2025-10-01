#!/usr/bin/env python3
"""
Proto-action: Clean and normalize identifiers for direct matching
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

def clean_chebi_ids(series):
    """Clean ChEBI IDs by removing prefixes and standardizing format"""
    if series is None or len(series) == 0:
        return series

    # Convert to string and handle NaN
    cleaned = series.astype(str)

    # Replace NaN strings back to actual NaN
    cleaned = cleaned.replace(['nan', 'None', ''], np.nan)

    # Remove CHEBI: prefix if present
    cleaned = cleaned.str.replace('CHEBI:', '', regex=False)

    # Strip whitespace
    cleaned = cleaned.str.strip()

    # Convert empty strings back to NaN
    cleaned = cleaned.replace('', np.nan)

    # Convert to numeric and then to integer where possible to ensure type consistency
    # This fixes the float64 vs int64 mismatch issue
    cleaned = pd.to_numeric(cleaned, errors='coerce')
    cleaned = cleaned.astype('Int64')  # Use nullable integer type

    # Convert back to string for consistent joining (both will be strings)
    cleaned = cleaned.astype(str)
    cleaned = cleaned.replace('nan', np.nan)
    cleaned = cleaned.replace('<NA>', np.nan)

    return cleaned

def clean_hmdb_ids(series):
    """Clean HMDB IDs by removing prefixes and standardizing format"""
    if series is None or len(series) == 0:
        return series

    # Convert to string and handle NaN
    cleaned = series.astype(str)

    # Replace NaN strings back to actual NaN
    cleaned = cleaned.replace(['nan', 'None', ''], np.nan)

    # Remove HMDB prefix if present - handle all variations
    # First handle the double prefix case "HMDBHMDB"
    cleaned = cleaned.str.replace('HMDBHMDB', 'HMDB', regex=False)  # Fix double prefix
    # Then remove the single prefix
    cleaned = cleaned.str.replace('HMDB:HMDB', '', regex=False)  # Handle HMDB:HMDB format
    cleaned = cleaned.str.replace('HMDB:', '', regex=False)      # Handle HMDB: format
    cleaned = cleaned.str.replace('HMDB', '', regex=False)       # Handle HMDB format

    # Strip whitespace
    cleaned = cleaned.str.strip()

    # Convert empty strings back to NaN
    cleaned = cleaned.replace('', np.nan)

    # Standardize HMDB format - should be 7 digits with leading zeros
    def standardize_hmdb(val):
        if pd.isna(val) or val == '':
            return np.nan
        # Convert to string first to avoid float issues
        val = str(val)
        # Remove .0 if it exists (from float conversion)
        if '.0' in val:
            val = val.replace('.0', '')
        # Remove any remaining non-numeric characters
        val = ''.join(c for c in val if c.isdigit())
        if val:
            # Pad with zeros to 7 digits if needed (some have 5, some have 6, standard is 7)
            return val.zfill(7)
        return np.nan

    cleaned = cleaned.apply(standardize_hmdb)

    return cleaned

def main():
    print("Cleaning and normalizing identifiers for direct mapping...")

    # Load Nightingale data
    nightingale_file = INPUT_DIR / "nightingale_loaded.tsv"
    print(f"Loading Nightingale data from {nightingale_file}")

    try:
        nightingale_df = pd.read_csv(nightingale_file, sep='\t')
        print(f"  Loaded {len(nightingale_df)} Nightingale biomarkers")
    except FileNotFoundError:
        print(f"ERROR: Could not find {nightingale_file}")
        print("Run script 01_load_nightingale_data.py first")
        return

    # Clean Nightingale IDs
    print("\nCleaning Nightingale identifiers...")

    if 'ChEBI_ID' in nightingale_df.columns:
        nightingale_df['chebi_clean'] = clean_chebi_ids(nightingale_df['ChEBI_ID'])
        chebi_count = nightingale_df['chebi_clean'].notna().sum()
        print(f"  ChEBI IDs: {chebi_count} valid IDs after cleaning")

        # Show sample cleaned ChEBI IDs
        sample_chebi = nightingale_df[nightingale_df['chebi_clean'].notna()]['chebi_clean'].head(5).tolist()
        print(f"    Sample cleaned ChEBI IDs: {sample_chebi}")

    if 'HMDB_ID_merged' in nightingale_df.columns:
        nightingale_df['hmdb_clean'] = clean_hmdb_ids(nightingale_df['HMDB_ID_merged'])
        hmdb_count = nightingale_df['hmdb_clean'].notna().sum()
        print(f"  HMDB IDs: {hmdb_count} valid IDs after cleaning")

        # Show sample cleaned HMDB IDs
        sample_hmdb = nightingale_df[nightingale_df['hmdb_clean'].notna()]['hmdb_clean'].head(5).tolist()
        print(f"    Sample cleaned HMDB IDs: {sample_hmdb}")

    # Clean Kraken ChEBI data
    kraken_chebi_file = INPUT_DIR / "kraken_chebi.tsv"
    if kraken_chebi_file.exists():
        print(f"\nLoading and cleaning Kraken ChEBI data from {kraken_chebi_file}")
        kraken_chebi_df = pd.read_csv(kraken_chebi_file, sep='\t')

        if 'id' in kraken_chebi_df.columns:
            kraken_chebi_df['chebi_clean'] = clean_chebi_ids(kraken_chebi_df['id'])
            chebi_kraken_count = kraken_chebi_df['chebi_clean'].notna().sum()
            print(f"  Kraken ChEBI: {chebi_kraken_count} valid IDs after cleaning")

            # Show sample cleaned Kraken ChEBI IDs
            sample_kraken_chebi = kraken_chebi_df[kraken_chebi_df['chebi_clean'].notna()]['chebi_clean'].head(5).tolist()
            print(f"    Sample cleaned Kraken ChEBI IDs: {sample_kraken_chebi}")
    else:
        print(f"WARNING: Kraken ChEBI file not found: {kraken_chebi_file}")
        kraken_chebi_df = None

    # Clean Kraken HMDB data
    kraken_hmdb_file = INPUT_DIR / "kraken_hmdb.tsv"
    if kraken_hmdb_file.exists():
        print(f"\nLoading and cleaning Kraken HMDB data from {kraken_hmdb_file}")
        kraken_hmdb_df = pd.read_csv(kraken_hmdb_file, sep='\t')

        if 'id' in kraken_hmdb_df.columns:
            kraken_hmdb_df['hmdb_clean'] = clean_hmdb_ids(kraken_hmdb_df['id'])
            hmdb_kraken_count = kraken_hmdb_df['hmdb_clean'].notna().sum()
            print(f"  Kraken HMDB: {hmdb_kraken_count} valid IDs after cleaning")

            # Show sample cleaned Kraken HMDB IDs
            sample_kraken_hmdb = kraken_hmdb_df[kraken_hmdb_df['hmdb_clean'].notna()]['hmdb_clean'].head(5).tolist()
            print(f"    Sample cleaned Kraken HMDB IDs: {sample_kraken_hmdb}")
    else:
        print(f"WARNING: Kraken HMDB file not found: {kraken_hmdb_file}")
        kraken_hmdb_df = None

    # Save cleaned data
    print("\nSaving cleaned data...")

    # Save Nightingale with cleaned IDs
    nightingale_clean_file = OUTPUT_DIR / "nightingale_cleaned.tsv"
    nightingale_df.to_csv(nightingale_clean_file, sep='\t', index=False)
    print(f"  Saved cleaned Nightingale data: {nightingale_clean_file}")

    # Save Kraken data with cleaned IDs
    if kraken_chebi_df is not None:
        kraken_chebi_clean_file = OUTPUT_DIR / "kraken_chebi_cleaned.tsv"
        kraken_chebi_df.to_csv(kraken_chebi_clean_file, sep='\t', index=False)
        print(f"  Saved cleaned Kraken ChEBI data: {kraken_chebi_clean_file}")

    if kraken_hmdb_df is not None:
        kraken_hmdb_clean_file = OUTPUT_DIR / "kraken_hmdb_cleaned.tsv"
        kraken_hmdb_df.to_csv(kraken_hmdb_clean_file, sep='\t', index=False)
        print(f"  Saved cleaned Kraken HMDB data: {kraken_hmdb_clean_file}")

    # Summary
    print("\nSUMMARY:")
    print(f"  - Nightingale biomarkers processed: {len(nightingale_df)}")

    if 'chebi_clean' in nightingale_df.columns:
        chebi_ready = nightingale_df['chebi_clean'].notna().sum()
        print(f"  - ChEBI IDs ready for matching: {chebi_ready}")

    if 'hmdb_clean' in nightingale_df.columns:
        hmdb_ready = nightingale_df['hmdb_clean'].notna().sum()
        print(f"  - HMDB IDs ready for matching: {hmdb_ready}")

    if kraken_chebi_df is not None:
        print(f"  - Kraken ChEBI nodes ready: {len(kraken_chebi_df)}")

    if kraken_hmdb_df is not None:
        print(f"  - Kraken HMDB nodes ready: {len(kraken_hmdb_df)}")

    print("  - Ready for direct ID mapping!")

if __name__ == "__main__":
    main()
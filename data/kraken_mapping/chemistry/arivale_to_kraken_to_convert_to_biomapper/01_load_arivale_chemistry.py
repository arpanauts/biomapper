#!/usr/bin/env python3
"""
Proto-action: Load Arivale chemistry metadata
This is a STANDALONE script, not a biomapper action

Loads Arivale clinical chemistry metadata and performs basic preprocessing.
Handles file comments and extracts relevant columns for LOINC mapping.
"""

import pandas as pd
from pathlib import Path
import sys

# Input data path - Updated to use authoritative MAPPING_ONTOLOGIES source
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "arivale_chemistry_raw.tsv"

def load_arivale_chemistry():
    """Load and preprocess Arivale chemistry metadata."""

    print(f"Loading Arivale chemistry data from: {INPUT_FILE}")

    # Check if input file exists
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    # Read the TSV file, handling comment lines that start with #
    df = pd.read_csv(INPUT_FILE, sep='\t', comment='#')

    print(f"Loaded {len(df)} chemistry tests")
    print(f"Columns: {list(df.columns)}")

    # Display sample of the data
    print("\nFirst few rows:")
    print(df.head(3))

    # Check for key columns we need
    required_columns = ['Name', 'Display Name', 'Labcorp LOINC ID', 'Quest LOINC ID']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"WARNING: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")

    # Basic data cleaning
    print("\nData cleaning...")

    # Remove any completely empty rows
    initial_count = len(df)
    df = df.dropna(how='all')
    if len(df) < initial_count:
        print(f"Removed {initial_count - len(df)} empty rows")

    # Clean up column names by stripping whitespace
    df.columns = df.columns.str.strip()

    # Display LOINC code statistics
    if 'Labcorp LOINC ID' in df.columns:
        labcorp_loinc_count = df['Labcorp LOINC ID'].notna().sum()
        print(f"Tests with Labcorp LOINC codes: {labcorp_loinc_count}")

    if 'Quest LOINC ID' in df.columns:
        quest_loinc_count = df['Quest LOINC ID'].notna().sum()
        print(f"Tests with Quest LOINC codes: {quest_loinc_count}")

    # Save cleaned data
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"\nSaved cleaned data to: {OUTPUT_FILE}")
    print(f"Final dataset: {len(df)} chemistry tests")

    return df

def main():
    """Main execution function."""
    try:
        df = load_arivale_chemistry()
        print("\n✅ 01_load_arivale_chemistry.py completed successfully")
    except Exception as e:
        print(f"\n❌ Error in 01_load_arivale_chemistry.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
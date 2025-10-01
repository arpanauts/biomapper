#!/usr/bin/env python3
"""
Proto-action: Prepare LOINC codes for Kraken mapping
This is a STANDALONE script, not a biomapper action

Cleans and prepares LOINC codes from Nightingale clinical chemistry data
for direct matching with Kraken LOINC nodes.
"""
import pandas as pd
from pathlib import Path
import sys
import re

# Input and output paths
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = INPUT_DIR
INPUT_FILE = INPUT_DIR / "nightingale_clinical.tsv"

def clean_loinc_code(loinc_code):
    """
    Clean and standardize LOINC codes for Kraken matching

    Args:
        loinc_code: Raw LOINC code from data

    Returns:
        Clean LOINC code in format: "12345-6"
    """
    if pd.isna(loinc_code) or str(loinc_code).strip() in ['', 'nan', 'None', 'NO_MATCH']:
        return None

    loinc_str = str(loinc_code).strip()

    # Remove any prefixes (LOINC:, etc.)
    if ':' in loinc_str:
        loinc_str = loinc_str.split(':', 1)[1]

    # Standard LOINC format: NNNNN-N (e.g., "12345-6")
    loinc_pattern = re.compile(r'^(\d{1,6}-\d)$')
    if loinc_pattern.match(loinc_str):
        return loinc_str

    # Try to extract LOINC pattern from string
    match = re.search(r'(\d{1,6}-\d)', loinc_str)
    if match:
        return match.group(1)

    # If no valid pattern found, return None
    print(f"WARNING: Could not parse LOINC code: {loinc_code}")
    return None

def add_kraken_prefix(loinc_code):
    """
    Add Kraken prefix to LOINC code for matching

    Args:
        loinc_code: Clean LOINC code (e.g., "12345-6")

    Returns:
        Kraken-formatted ID (e.g., "LOINC:12345-6")
    """
    if pd.isna(loinc_code):
        return None
    return f"LOINC:{loinc_code}"

def main():
    print("Preparing LOINC codes for Kraken mapping...")

    # Check if input file exists
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run 01_load_nightingale_clinical.py first")
        sys.exit(1)

    # Load the clinical chemistry data
    try:
        df = pd.read_csv(INPUT_FILE, sep='\t', low_memory=False)
        print(f"Loaded {len(df)} clinical chemistry biomarkers")
    except Exception as e:
        print(f"ERROR loading file: {e}")
        sys.exit(1)

    # Show input LOINC codes
    print(f"\nOriginal LOINC codes found:")
    if 'loinc_code' in df.columns:
        original_loinc = df['loinc_code'].dropna().unique()
        for loinc in original_loinc[:10]:  # Show first 10
            print(f"  {loinc}")
        if len(original_loinc) > 10:
            print(f"  ... and {len(original_loinc) - 10} more")
    else:
        print("  No loinc_code column found!")
        sys.exit(1)

    # Clean LOINC codes
    print("\nCleaning LOINC codes...")
    df['loinc_code_clean'] = df['loinc_code'].apply(clean_loinc_code)

    # Count valid vs invalid LOINC codes
    valid_loinc = df['loinc_code_clean'].notna()
    print(f"Valid LOINC codes: {valid_loinc.sum()}/{len(df)}")

    if valid_loinc.sum() == 0:
        print("ERROR: No valid LOINC codes found after cleaning!")
        sys.exit(1)

    # Add Kraken prefix for matching
    print("Adding Kraken prefixes...")
    df['kraken_loinc_id'] = df['loinc_code_clean'].apply(add_kraken_prefix)

    # Filter to records with valid LOINC codes
    prepared_df = df[valid_loinc].copy()

    # Add metadata for Israeli10K context
    prepared_df['source_dataset'] = 'israeli10k_nightingale'
    prepared_df['mapping_version'] = 'v1.0'
    prepared_df['biomarker_category'] = 'clinical_chemistry'

    # Create mapping confidence based on LOINC assignment quality
    def assign_confidence(row):
        """Assign mapping confidence based on LOINC metadata"""
        if pd.notna(row.get('loinc_confidence')):
            confidence_str = str(row['loinc_confidence']).upper()
            if confidence_str == 'HIGH':
                return 0.95
            elif confidence_str == 'MEDIUM':
                return 0.85
            elif confidence_str == 'LOW':
                return 0.75

        # Default confidence for clinical chemistry with LOINC
        return 0.90

    prepared_df['mapping_confidence'] = prepared_df.apply(assign_confidence, axis=1)

    # Show cleaned results
    print(f"\nCleaned LOINC codes:")
    clean_loinc = prepared_df['loinc_code_clean'].unique()
    for loinc in clean_loinc[:10]:
        print(f"  {loinc} -> LOINC:{loinc}")
    if len(clean_loinc) > 10:
        print(f"  ... and {len(clean_loinc) - 10} more")

    # Save prepared data
    output_file = OUTPUT_DIR / "nightingale_clinical_prepared.tsv"
    prepared_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved {len(prepared_df)} prepared biomarkers to {output_file}")

    # Summary statistics
    print(f"\nPreparation Summary:")
    print(f"  Input biomarkers: {len(df)}")
    print(f"  Valid LOINC codes: {len(prepared_df)}")
    print(f"  Coverage: {100 * len(prepared_df) / len(df):.1f}%")
    print(f"  Unique LOINC codes: {prepared_df['loinc_code_clean'].nunique()}")
    print(f"  Average confidence: {prepared_df['mapping_confidence'].mean():.3f}")

    # Show biomarker categories if available
    if 'Group' in prepared_df.columns:
        print(f"\nBiomarker groups:")
        group_counts = prepared_df['Group'].value_counts()
        for group, count in group_counts.items():
            print(f"  {group}: {count}")

    print("\n02_prepare_loinc_mapping.py completed successfully!")

if __name__ == "__main__":
    main()
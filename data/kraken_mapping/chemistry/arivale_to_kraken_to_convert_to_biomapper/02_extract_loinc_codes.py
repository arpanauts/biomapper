#!/usr/bin/env python3
"""
Proto-action: Extract and normalize LOINC codes from Arivale chemistry data
This is a STANDALONE script, not a biomapper action

Consolidates LOINC codes from Labcorp and Quest columns, handles special values,
and creates a unified LOINC mapping ready for Kraken matching.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
import sys

# Input/Output paths
INPUT_DIR = Path(__file__).parent / "data"
INPUT_FILE = INPUT_DIR / "arivale_chemistry_raw.tsv"
OUTPUT_FILE = INPUT_DIR / "arivale_chemistry_with_loinc.tsv"

def is_valid_loinc(loinc_code):
    """Check if a LOINC code is valid (format: XXXX-X)."""
    if pd.isna(loinc_code) or loinc_code == "":
        return False

    # Convert to string and clean
    loinc_str = str(loinc_code).strip()

    # Check for special values that are not valid LOINC codes
    invalid_values = ["SOLOINC", "SENDOUT NO LOINC PROVIDED", "NA", ""]
    if loinc_str in invalid_values:
        return False

    # Check LOINC format: digits-digit (e.g., 1759-0, 12345-6)
    loinc_pattern = re.compile(r'^\d{1,5}-\d$')
    return bool(loinc_pattern.match(loinc_str))

def extract_loinc_codes(df):
    """Extract and consolidate LOINC codes from multiple vendor columns."""

    print("Extracting and consolidating LOINC codes...")

    # Initialize consolidated LOINC column
    df['consolidated_loinc'] = ""
    df['loinc_source'] = ""

    # Track statistics
    stats = {
        'total_tests': len(df),
        'labcorp_valid': 0,
        'quest_valid': 0,
        'both_valid': 0,
        'neither_valid': 0,
        'consolidated_valid': 0
    }

    for idx, row in df.iterrows():
        labcorp_loinc = row.get('Labcorp LOINC ID', '')
        quest_loinc = row.get('Quest LOINC ID', '')

        labcorp_valid = is_valid_loinc(labcorp_loinc)
        quest_valid = is_valid_loinc(quest_loinc)

        if labcorp_valid:
            stats['labcorp_valid'] += 1
        if quest_valid:
            stats['quest_valid'] += 1

        # Consolidation logic: prefer Labcorp, fallback to Quest
        if labcorp_valid and quest_valid:
            stats['both_valid'] += 1
            # Check if they're the same
            if str(labcorp_loinc).strip() == str(quest_loinc).strip():
                df.at[idx, 'consolidated_loinc'] = str(labcorp_loinc).strip()
                df.at[idx, 'loinc_source'] = 'both_same'
            else:
                # Different codes - prefer Labcorp but note discrepancy
                df.at[idx, 'consolidated_loinc'] = str(labcorp_loinc).strip()
                df.at[idx, 'loinc_source'] = 'labcorp_preferred'
                print(f"  DISCREPANCY for {row.get('Name', 'Unknown')}: "
                      f"Labcorp={labcorp_loinc}, Quest={quest_loinc}")

        elif labcorp_valid:
            df.at[idx, 'consolidated_loinc'] = str(labcorp_loinc).strip()
            df.at[idx, 'loinc_source'] = 'labcorp_only'

        elif quest_valid:
            df.at[idx, 'consolidated_loinc'] = str(quest_loinc).strip()
            df.at[idx, 'loinc_source'] = 'quest_only'

        else:
            stats['neither_valid'] += 1
            df.at[idx, 'consolidated_loinc'] = ""
            df.at[idx, 'loinc_source'] = 'none'

    # Final count of consolidated valid LOINC codes
    stats['consolidated_valid'] = (df['consolidated_loinc'] != "").sum()

    return df, stats

def print_statistics(stats):
    """Print comprehensive statistics about LOINC code extraction."""

    print("\n" + "="*50)
    print("LOINC CODE EXTRACTION STATISTICS")
    print("="*50)

    total = stats['total_tests']
    print(f"Total chemistry tests: {total}")
    print(f"Labcorp LOINC codes: {stats['labcorp_valid']} ({100*stats['labcorp_valid']/total:.1f}%)")
    print(f"Quest LOINC codes: {stats['quest_valid']} ({100*stats['quest_valid']/total:.1f}%)")
    print(f"Both vendors have codes: {stats['both_valid']} ({100*stats['both_valid']/total:.1f}%)")
    print(f"Neither vendor has codes: {stats['neither_valid']} ({100*stats['neither_valid']/total:.1f}%)")
    print()
    print(f"✅ CONSOLIDATED VALID LOINC CODES: {stats['consolidated_valid']} ({100*stats['consolidated_valid']/total:.1f}%)")
    print(f"❌ Tests without LOINC codes: {total - stats['consolidated_valid']} ({100*(total - stats['consolidated_valid'])/total:.1f}%)")

def analyze_unmapped_tests(df):
    """Analyze tests that don't have valid LOINC codes."""

    unmapped = df[df['consolidated_loinc'] == ""]

    if len(unmapped) > 0:
        print(f"\n📋 TESTS WITHOUT VALID LOINC CODES ({len(unmapped)} tests):")
        print("-" * 60)

        for _, row in unmapped.iterrows():
            test_name = row.get('Name', 'Unknown')
            display_name = row.get('Display Name', 'Unknown')
            labcorp_raw = row.get('Labcorp LOINC ID', '')
            quest_raw = row.get('Quest LOINC ID', '')

            print(f"• {test_name}")
            if display_name and display_name != test_name:
                print(f"  Display: {display_name}")
            if labcorp_raw:
                print(f"  Labcorp: {labcorp_raw}")
            if quest_raw:
                print(f"  Quest: {quest_raw}")
            print()

def main():
    """Main execution function."""

    print("Starting LOINC code extraction...")

    # Check input file
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Make sure to run 01_load_arivale_chemistry.py first.")
        sys.exit(1)

    try:
        # Load data
        df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(df)} chemistry tests from {INPUT_FILE}")

        # Extract and consolidate LOINC codes
        df, stats = extract_loinc_codes(df)

        # Print statistics
        print_statistics(stats)

        # Analyze unmapped tests
        analyze_unmapped_tests(df)

        # Save results
        df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        print(f"\n💾 Saved processed data to: {OUTPUT_FILE}")

        print("\n✅ 02_extract_loinc_codes.py completed successfully")

    except Exception as e:
        print(f"\n❌ Error in 02_extract_loinc_codes.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
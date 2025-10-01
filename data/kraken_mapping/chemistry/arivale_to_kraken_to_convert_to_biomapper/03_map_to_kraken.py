#!/usr/bin/env python3
"""
Proto-action: Map Arivale chemistry tests to Kraken LOINC nodes
This is a STANDALONE script, not a biomapper action

Performs direct ID matching between Arivale LOINC codes and Kraken LOINC nodes.
No fuzzy matching - just simple pandas merge operations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Input/Output paths
INPUT_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
INPUT_FILE = INPUT_DIR / "arivale_chemistry_with_loinc.tsv"
KRAKEN_LOINC_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"
OUTPUT_FILE = RESULTS_DIR / "arivale_kraken_chemistry_mapping.tsv"

def load_kraken_loinc_nodes():
    """Load Kraken LOINC nodes for mapping."""

    print(f"Loading Kraken LOINC nodes from: {KRAKEN_LOINC_FILE}")

    # Check if Kraken file exists
    if not Path(KRAKEN_LOINC_FILE).exists():
        print(f"ERROR: Kraken LOINC file not found: {KRAKEN_LOINC_FILE}")
        print("Available files in Kraken directory:")
        kraken_dir = Path(KRAKEN_LOINC_FILE).parent
        if kraken_dir.exists():
            for file in kraken_dir.glob("*.tsv"):
                print(f"  {file.name}")
        return None

    try:
        # Load all clinical findings
        kraken_df = pd.read_csv(KRAKEN_LOINC_FILE)
        print(f"Loaded {len(kraken_df)} Kraken clinical findings")

        # Filter to only LOINC codes
        loinc_mask = kraken_df['id'].str.startswith('LOINC:', na=False)
        kraken_loinc_df = kraken_df[loinc_mask].copy()
        print(f"Filtered to {len(kraken_loinc_df)} LOINC codes")

        # Display sample of Kraken data
        print("\nKraken LOINC nodes sample:")
        print(f"Columns: {list(kraken_loinc_df.columns)}")
        if len(kraken_loinc_df) > 0:
            print(kraken_loinc_df.head(3))

        return kraken_loinc_df

    except Exception as e:
        print(f"ERROR loading Kraken LOINC file: {e}")
        return None

def prepare_kraken_ids(kraken_df):
    """Prepare Kraken IDs for joining by removing LOINC: prefix."""

    print("Preparing Kraken IDs for joining...")

    # Check if 'id' column exists
    if 'id' not in kraken_df.columns:
        print(f"ERROR: 'id' column not found in Kraken data. Available columns: {list(kraken_df.columns)}")
        return None

    # Remove LOINC: prefix to get clean LOINC codes
    kraken_df = kraken_df.copy()
    kraken_df['clean_loinc'] = kraken_df['id'].str.replace('LOINC:', '', regex=False)

    # Show some examples
    print("Sample ID transformations:")
    sample_ids = kraken_df[['id', 'clean_loinc']].head(5)
    for _, row in sample_ids.iterrows():
        print(f"  {row['id']} → {row['clean_loinc']}")

    return kraken_df

def perform_direct_mapping(arivale_df, kraken_df):
    """Perform direct ID mapping between Arivale and Kraken."""

    print("\nPerforming direct LOINC code mapping...")

    # Only map tests that have valid LOINC codes
    arivale_with_loinc = arivale_df[arivale_df['consolidated_loinc'] != ""].copy()
    print(f"Arivale tests with LOINC codes: {len(arivale_with_loinc)}")

    if len(arivale_with_loinc) == 0:
        print("No Arivale tests have valid LOINC codes to map!")
        return None

    # Direct join on LOINC codes
    mapped_df = arivale_with_loinc.merge(
        kraken_df,
        left_on='consolidated_loinc',    # Arivale's consolidated LOINC
        right_on='clean_loinc',          # Kraken's clean LOINC (without LOINC: prefix)
        how='left',                      # Keep all Arivale tests
        suffixes=('_arivale', '_kraken')
    )

    # Add mapping confidence scores
    mapped_df['mapping_confidence'] = mapped_df['id'].notna().astype(float)  # 1.0 if mapped, 0.0 if not
    mapped_df['mapping_method'] = mapped_df['id'].notna().map({True: 'direct_loinc', False: 'unmapped'})

    return mapped_df

def analyze_mapping_results(mapped_df, arivale_df):
    """Analyze and report mapping statistics."""

    print("\n" + "="*60)
    print("KRAKEN MAPPING RESULTS")
    print("="*60)

    total_tests = len(arivale_df)
    tests_with_loinc = len(arivale_df[arivale_df['consolidated_loinc'] != ""])
    mapped_count = len(mapped_df[mapped_df['mapping_confidence'] == 1.0])
    unmapped_count = len(mapped_df[mapped_df['mapping_confidence'] == 0.0])

    print(f"Total Arivale chemistry tests: {total_tests}")
    print(f"Tests with valid LOINC codes: {tests_with_loinc} ({100*tests_with_loinc/total_tests:.1f}%)")
    print(f"Successfully mapped to Kraken: {mapped_count} ({100*mapped_count/tests_with_loinc:.1f}% of tests with LOINC)")
    print(f"Unmapped (had LOINC but no Kraken match): {unmapped_count}")

    print(f"\n🎯 OVERALL MAPPING RATE: {mapped_count}/{total_tests} ({100*mapped_count/total_tests:.1f}%)")

    # Show some successful mappings
    if mapped_count > 0:
        print(f"\n✅ SAMPLE SUCCESSFUL MAPPINGS:")
        print("-" * 80)
        successful = mapped_df[mapped_df['mapping_confidence'] == 1.0].head(5)
        for _, row in successful.iterrows():
            arivale_name = row.get('Name', 'Unknown')
            loinc_code = row.get('consolidated_loinc', 'Unknown')
            kraken_id = row.get('id', 'Unknown')
            kraken_name = row.get('name', 'Unknown')
            print(f"• {arivale_name}")
            print(f"  LOINC: {loinc_code} → Kraken: {kraken_id}")
            print(f"  Kraken name: {kraken_name}")
            print()

    # Show unmapped tests
    if unmapped_count > 0:
        print(f"\n❌ UNMAPPED TESTS (had LOINC but no Kraken match):")
        print("-" * 80)
        unmapped = mapped_df[mapped_df['mapping_confidence'] == 0.0]
        for _, row in unmapped.iterrows():
            arivale_name = row.get('Name', 'Unknown')
            loinc_code = row.get('consolidated_loinc', 'Unknown')
            print(f"• {arivale_name} (LOINC: {loinc_code})")

def prepare_final_output(mapped_df):
    """Prepare the final output with standardized columns."""

    print("\nPreparing final output...")

    # Select and rename columns for final output
    output_columns = {
        'Name': 'arivale_test_name',
        'Display Name': 'arivale_display_name',
        'Labcorp LOINC ID': 'labcorp_loinc',
        'Quest LOINC ID': 'quest_loinc',
        'consolidated_loinc': 'unified_loinc',
        'loinc_source': 'loinc_source',
        'id': 'kraken_node_id',
        'name': 'kraken_name',
        'category': 'kraken_category',
        'mapping_confidence': 'mapping_confidence',
        'mapping_method': 'mapping_method'
    }

    # Create final dataframe with selected columns
    final_df = mapped_df.copy()

    # Rename columns that exist
    rename_dict = {old: new for old, new in output_columns.items() if old in final_df.columns}
    final_df = final_df.rename(columns=rename_dict)

    # Add missing columns with default values
    for old, new in output_columns.items():
        if new not in final_df.columns:
            if old in ['category']:
                final_df[new] = 'clinical_chemistry'  # Default category
            else:
                final_df[new] = ''

    # Select final columns in order
    final_columns = list(output_columns.values())
    available_columns = [col for col in final_columns if col in final_df.columns]
    final_df = final_df[available_columns]

    return final_df

def main():
    """Main execution function."""

    print("Starting Kraken mapping for Arivale chemistry tests...")

    # Check input file
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Make sure to run 02_extract_loinc_codes.py first.")
        sys.exit(1)

    try:
        # Load Arivale data
        arivale_df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(arivale_df)} Arivale chemistry tests")

        # Load Kraken LOINC nodes
        kraken_df = load_kraken_loinc_nodes()
        if kraken_df is None:
            sys.exit(1)

        # Prepare Kraken IDs for joining
        kraken_df = prepare_kraken_ids(kraken_df)
        if kraken_df is None:
            sys.exit(1)

        # Perform direct mapping
        mapped_df = perform_direct_mapping(arivale_df, kraken_df)
        if mapped_df is None:
            sys.exit(1)

        # Analyze results
        analyze_mapping_results(mapped_df, arivale_df)

        # Prepare final output
        final_df = prepare_final_output(mapped_df)

        # Save results
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        final_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        print(f"\n💾 Saved final mapping to: {OUTPUT_FILE}")

        print("\n✅ 03_map_to_kraken.py completed successfully")

    except Exception as e:
        print(f"\n❌ Error in 03_map_to_kraken.py: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
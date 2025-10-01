#!/usr/bin/env python3
"""
Proto-action: Map UKBB chemistry tests to Kraken 1.0.0 nodes
This is a STANDALONE script, not a biomapper action

Direct join of LOINC codes to Kraken LOINC nodes.
"""
import pandas as pd
import json
from pathlib import Path

# Input/output paths
INPUT_DIR = Path(__file__).parent / "data"
INPUT_FILE = INPUT_DIR / "ukbb_with_loinc.tsv"
RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_FILE = RESULTS_DIR / "ukbb_kraken_mappings.tsv"
STATS_FILE = INPUT_DIR / "mapping_stats.json"

# Kraken LOINC nodes path
KRAKEN_LOINC_PATH = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"

def prepare_loinc_for_join(loinc_code):
    """
    Prepare LOINC code for joining with Kraken nodes.
    Kraken uses "LOINC:" prefix format.
    """
    if pd.isna(loinc_code):
        return None

    loinc_code = str(loinc_code).strip()
    if loinc_code and not loinc_code.startswith("LOINC:"):
        return f"LOINC:{loinc_code}"

    return loinc_code if loinc_code else None

def main():
    """Map UKBB chemistry tests to Kraken nodes via LOINC codes."""
    print("Loading UKBB chemistry data with LOINC codes...")
    ukbb_df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(ukbb_df)} UKBB chemistry tests")

    # Count tests with LOINC codes
    with_loinc = len(ukbb_df[ukbb_df['loinc_code'].notna()])
    print(f"Tests with LOINC codes: {with_loinc} ({100*with_loinc/len(ukbb_df):.1f}%)")

    print("Loading Kraken LOINC nodes...")
    try:
        kraken_df = pd.read_csv(KRAKEN_LOINC_PATH, sep=',')
        print(f"Loaded {len(kraken_df)} Kraken LOINC nodes")
    except FileNotFoundError:
        print(f"Error: Kraken LOINC nodes file not found at {KRAKEN_LOINC_PATH}")
        print("Cannot proceed with mapping. Please check file path.")
        return

    # Prepare UKBB LOINC codes for joining
    print("Preparing LOINC codes for joining...")
    ukbb_df['kraken_lookup_id'] = ukbb_df['loinc_code'].apply(prepare_loinc_for_join)

    # Filter to only tests that have LOINC codes
    ukbb_with_loinc = ukbb_df[ukbb_df['kraken_lookup_id'].notna()].copy()
    print(f"Tests ready for Kraken mapping: {len(ukbb_with_loinc)}")

    # Perform direct join with Kraken nodes
    print("Joining with Kraken LOINC nodes...")
    mapped_df = ukbb_with_loinc.merge(
        kraken_df,
        left_on='kraken_lookup_id',
        right_on='id',  # Kraken node ID column
        how='left',
        suffixes=('', '_kraken')
    )

    # Count successful mappings
    kraken_mapped = mapped_df['id'].notna()
    kraken_matched_count = kraken_mapped.sum()

    print(f"Successfully mapped to Kraken: {kraken_matched_count}/{len(ukbb_with_loinc)} ({100*kraken_matched_count/len(ukbb_with_loinc):.1f}%)")

    # Prepare final output with required columns
    print("Preparing final output...")

    # Create output dataframe with required columns
    result_df = pd.DataFrame()

    # Required columns per prompt specification
    result_df['ukbb_field_id'] = mapped_df['field_id'].astype(str)
    result_df['ukbb_field_name'] = mapped_df['original_field_name']
    result_df['assigned_loinc_code'] = mapped_df['loinc_code']

    # Kraken node information
    result_df['kraken_node_id'] = mapped_df['id']  # This is the Kraken node ID
    result_df['kraken_name'] = mapped_df.get('name', '')  # Kraken node name
    result_df['kraken_category'] = mapped_df.get('category', 'clinical_test')  # Default category

    # Mapping metadata
    result_df['mapping_method'] = mapped_df['mapping_method']
    result_df['mapping_confidence'] = mapped_df['mapping_confidence']

    # Add mapping status
    result_df['kraken_mapped'] = kraken_mapped
    result_df['has_loinc'] = True  # All rows in this output have LOINC

    # Also include unmapped tests (those without LOINC codes)
    print("Including unmapped tests...")
    unmapped_df = ukbb_df[ukbb_df['loinc_code'].isna()].copy()

    if not unmapped_df.empty:
        unmapped_result = pd.DataFrame()
        unmapped_result['ukbb_field_id'] = unmapped_df['field_id'].astype(str)
        unmapped_result['ukbb_field_name'] = unmapped_df['original_field_name']
        unmapped_result['assigned_loinc_code'] = None
        unmapped_result['kraken_node_id'] = None
        unmapped_result['kraken_name'] = None
        unmapped_result['kraken_category'] = None
        unmapped_result['mapping_method'] = 'none'
        unmapped_result['mapping_confidence'] = 0.0
        unmapped_result['kraken_mapped'] = False
        unmapped_result['has_loinc'] = False

        # Combine mapped and unmapped
        final_df = pd.concat([result_df, unmapped_result], ignore_index=True)
    else:
        final_df = result_df

    # Sort by field ID
    final_df = final_df.sort_values('ukbb_field_id')

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    final_df.to_csv(OUTPUT_FILE, sep='\t', index=False)

    # Calculate comprehensive statistics
    total_ukbb_tests = len(ukbb_df)
    tests_with_loinc = len(ukbb_df[ukbb_df['loinc_code'].notna()])
    tests_mapped_to_kraken = len(final_df[final_df['kraken_mapped'] == True])

    stats = {
        'total_ukbb_tests': int(total_ukbb_tests),
        'tests_with_loinc': int(tests_with_loinc),
        'loinc_match_rate': float(tests_with_loinc / total_ukbb_tests),
        'tests_mapped_to_kraken': int(tests_mapped_to_kraken),
        'kraken_match_rate': float(tests_mapped_to_kraken / total_ukbb_tests),
        'loinc_to_kraken_rate': float(tests_mapped_to_kraken / tests_with_loinc) if tests_with_loinc > 0 else 0.0,
        'mapping_methods': {},
        'confidence_distribution': {}
    }

    # Method breakdown
    if not final_df.empty:
        method_counts = final_df[final_df['has_loinc'] == True]['mapping_method'].value_counts()
        stats['mapping_methods'] = method_counts.to_dict()

        # Confidence distribution
        confidence_ranges = {
            'high (0.8-1.0)': len(final_df[final_df['mapping_confidence'] >= 0.8]),
            'medium (0.5-0.8)': len(final_df[(final_df['mapping_confidence'] >= 0.5) & (final_df['mapping_confidence'] < 0.8)]),
            'low (0.0-0.5)': len(final_df[(final_df['mapping_confidence'] > 0.0) & (final_df['mapping_confidence'] < 0.5)]),
            'unmapped (0.0)': len(final_df[final_df['mapping_confidence'] == 0.0])
        }
        stats['confidence_distribution'] = confidence_ranges

    # Save statistics
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\nMapping Results Summary:")
    print(f"Total UKBB tests: {total_ukbb_tests}")
    print(f"Tests with LOINC codes: {tests_with_loinc} ({100*stats['loinc_match_rate']:.1f}%)")
    print(f"Tests mapped to Kraken: {tests_mapped_to_kraken} ({100*stats['kraken_match_rate']:.1f}%)")

    if tests_with_loinc > 0:
        print(f"LOINC→Kraken success rate: {100*stats['loinc_to_kraken_rate']:.1f}%")

    print(f"\nSaved final mappings to: {OUTPUT_FILE}")
    print(f"Saved statistics to: {STATS_FILE}")

    # Show sample mappings
    print(f"\nSample successful mappings:")
    successful = final_df[final_df['kraken_mapped'] == True].head(5)
    for _, row in successful.iterrows():
        print(f"  {row['ukbb_field_id']}: {row['ukbb_field_name']} → {row['assigned_loinc_code']} → {row['kraken_node_id']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Map Nightingale clinical chemistry to Kraken knowledge graph
This is a STANDALONE script, not a biomapper action

Performs direct LOINC-based mapping between prepared Nightingale clinical
chemistry biomarkers and Kraken 1.0.0 LOINC nodes.
"""
import pandas as pd
from pathlib import Path
import sys

# Input and output paths
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = INPUT_DIR
INPUT_FILE = INPUT_DIR / "nightingale_clinical_prepared.tsv"

# Kraken LOINC nodes (clinical findings)
KRAKEN_LOINC_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"

def main():
    print("Mapping Nightingale clinical chemistry to Kraken LOINC nodes...")

    # Check if input file exists
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run 02_prepare_loinc_mapping.py first")
        sys.exit(1)

    # Load prepared Nightingale data
    try:
        nightingale_df = pd.read_csv(INPUT_FILE, sep='\t', low_memory=False)
        print(f"Loaded {len(nightingale_df)} prepared Nightingale biomarkers")
    except Exception as e:
        print(f"ERROR loading Nightingale file: {e}")
        sys.exit(1)

    # Check if Kraken LOINC file exists
    if not Path(KRAKEN_LOINC_FILE).exists():
        print(f"ERROR: Kraken LOINC file not found: {KRAKEN_LOINC_FILE}")
        print("This file should contain Kraken 1.0.0 LOINC nodes")
        sys.exit(1)

    # Load Kraken LOINC nodes (clinical findings CSV)
    try:
        kraken_df = pd.read_csv(KRAKEN_LOINC_FILE, low_memory=False)
        print(f"Loaded {len(kraken_df)} Kraken clinical findings")
    except Exception as e:
        print(f"ERROR loading Kraken file: {e}")
        sys.exit(1)

    # Display Kraken columns for debugging
    print(f"Kraken LOINC columns: {list(kraken_df.columns)}")

    # Show sample Kraken IDs
    if 'id' in kraken_df.columns:
        sample_ids = kraken_df['id'].head(5).tolist()
        print(f"Sample Kraken LOINC IDs: {sample_ids}")
    else:
        print("WARNING: No 'id' column found in Kraken LOINC file")

    # Show Nightingale LOINC codes to map
    print(f"\nNightingale LOINC codes to map:")
    if 'kraken_loinc_id' in nightingale_df.columns:
        sample_loinc = nightingale_df['kraken_loinc_id'].head(5).tolist()
        print(f"Sample prepared LOINC IDs: {sample_loinc}")
    else:
        print("ERROR: No 'kraken_loinc_id' column found in Nightingale data")
        sys.exit(1)

    # DIRECT JOIN - Match Nightingale LOINC codes with Kraken LOINC nodes
    print(f"\nPerforming direct LOINC mapping...")
    mapped_df = nightingale_df.merge(
        kraken_df,
        left_on='kraken_loinc_id',  # Nightingale LOINC with "LOINC:" prefix
        right_on='id',              # Kraken node ID column
        how='left',                 # Keep all Nightingale records
        suffixes=('_nightingale', '_kraken')
    )

    print(f"Mapping completed: {len(mapped_df)} total records")

    # Calculate mapping statistics
    total_biomarkers = len(nightingale_df)
    mapped_biomarkers = len(mapped_df[mapped_df['id'].notna()])
    mapping_rate = (mapped_biomarkers / total_biomarkers) * 100

    print(f"\nMapping Statistics:")
    print(f"  Total biomarkers: {total_biomarkers}")
    print(f"  Successfully mapped: {mapped_biomarkers}")
    print(f"  Mapping rate: {mapping_rate:.1f}%")

    # Show sample successful mappings
    successful_maps = mapped_df[mapped_df['id'].notna()]
    if len(successful_maps) > 0:
        print(f"\nSample successful mappings:")
        for i, row in successful_maps.head(5).iterrows():
            biomarker = row.get('Biomarker', 'Unknown')
            loinc_code = row.get('loinc_code_clean', 'Unknown')
            kraken_id = row.get('id', 'Unknown')
            kraken_name = row.get('name', 'Unknown')
            print(f"  {biomarker} -> {loinc_code} -> {kraken_id} ({kraken_name})")

    # Show unmapped biomarkers
    unmapped = mapped_df[mapped_df['id'].isna()]
    if len(unmapped) > 0:
        print(f"\nUnmapped biomarkers ({len(unmapped)}):")
        for i, row in unmapped.head(5).iterrows():
            biomarker = row.get('Biomarker', 'Unknown')
            loinc_code = row.get('loinc_code_clean', 'Unknown')
            print(f"  {biomarker} (LOINC: {loinc_code})")
        if len(unmapped) > 5:
            print(f"  ... and {len(unmapped) - 5} more")

    # Add Israeli10K-specific metadata
    mapped_df['mapping_timestamp'] = pd.Timestamp.now().isoformat()
    mapped_df['cohort'] = 'israeli10k'
    mapped_df['platform'] = 'nightingale_nmr'
    mapped_df['mapping_method'] = 'direct_loinc_match'

    # Calculate final confidence (combine LOINC confidence with mapping success)
    def calculate_final_confidence(row):
        base_confidence = row.get('mapping_confidence', 0.90)
        if pd.isna(row.get('id')):
            return 0.0  # No mapping found
        return base_confidence

    mapped_df['final_mapping_confidence'] = mapped_df.apply(calculate_final_confidence, axis=1)

    # Save mapped results
    output_file = OUTPUT_DIR / "israeli10k_nightingale_kraken_mapped.tsv"
    mapped_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved mapping results to {output_file}")

    # Save mapping summary
    summary = {
        'total_biomarkers': total_biomarkers,
        'mapped_biomarkers': mapped_biomarkers,
        'mapping_rate_percent': mapping_rate,
        'unique_loinc_codes': nightingale_df['loinc_code_clean'].nunique(),
        'mapped_loinc_codes': successful_maps['loinc_code_clean'].nunique() if len(successful_maps) > 0 else 0,
        'kraken_nodes_available': len(kraken_df),
        'mapping_timestamp': pd.Timestamp.now().isoformat()
    }

    summary_file = OUTPUT_DIR / "mapping_summary.json"
    import json
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved mapping summary to {summary_file}")

    # Final validation
    if mapping_rate < 50:
        print(f"\nWARNING: Low mapping rate ({mapping_rate:.1f}%)")
        print("This may indicate issues with:")
        print("  - LOINC code format differences")
        print("  - Missing Kraken LOINC nodes")
        print("  - Prefix/suffix mismatches")
    else:
        print(f"\nSUCCESS: Good mapping rate ({mapping_rate:.1f}%)")

    print("\n03_map_to_kraken.py completed successfully!")

if __name__ == "__main__":
    main()
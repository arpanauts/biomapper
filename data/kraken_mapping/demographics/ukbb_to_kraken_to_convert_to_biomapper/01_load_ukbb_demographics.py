#!/usr/bin/env python3
"""
Proto-strategy Script 1: Load UKBB Demographics with LOINC mappings
This is a STANDALONE script for the ukbb_to_kraken proto-strategy
"""
import pandas as pd
from pathlib import Path
import sys

def main():
    """Load and clean UKBB demographics data with LOINC mappings"""

    # Input file paths - Updated to use completed file with LLM reasoning
    input_file = "/home/ubuntu/biomapper/data/harmonization/demographics/loinc_demographics_to_convert_to_biomapper/results/ukbb_demographics_loinc_final.tsv"

    # Output directory
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    print("=== UKBB Demographics to Kraken Proto-Strategy ===")
    print(f"Loading UKBB demographics from: {input_file}")

    # Load the TSV data
    try:
        df = pd.read_csv(input_file, sep='\t')
        print(f"Loaded {len(df)} demographic fields")
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    # Print column information
    print(f"Columns: {list(df.columns)}")

    # Filter out NO_MATCH entries (confidence_score = 0.0)
    print(f"\nFiltering demographic fields...")
    print(f"Before filtering: {len(df)} fields")

    # Apply standardization: process ALL fields with mapping status indicators
    # This ensures complete source coverage rather than filtering out fields
    all_fields = df.copy()

    # Add mapping status based on LOINC availability
    all_fields['mapping_status'] = all_fields['loinc_code'].apply(
        lambda x: 'Mapped' if x != 'NO_MATCH' and pd.notna(x) else 'Unmapped'
    )

    # Keep separate counts for reporting
    valid_loinc = df[
        (df['loinc_code'] != 'NO_MATCH') &
        (df['loinc_code'].notna()) &
        (df['confidence_score'] > 0.0)
    ].copy()

    print(f"Processing: {len(all_fields)} total fields (standardized approach)")
    print(f"  - With LOINC codes: {len(valid_loinc)} fields")
    print(f"  - Without LOINC (NO_MATCH): {len(all_fields) - len(valid_loinc)} fields")

    # Clean and standardize the data using ALL fields
    print(f"\nCleaning and standardizing data...")

    # Extract field information - using field_name as field_id if no separate field_id column
    if 'field_id' in all_fields.columns:
        all_fields['ukbb_field_id'] = all_fields['field_id']
    else:
        # Generate field IDs from field names or use index
        all_fields['ukbb_field_id'] = all_fields.index.astype(str)

    all_fields['ukbb_field_name'] = all_fields['field_name']
    all_fields['matched_loinc_code'] = all_fields['loinc_code'].replace('NO_MATCH', '')
    all_fields['loinc_name'] = all_fields['loinc_name'].fillna('')
    all_fields['mapping_confidence'] = all_fields['confidence_score']
    all_fields['demographic_category'] = all_fields['category']

    # Select and rename columns for output (include mapping_status)
    output_columns = [
        'ukbb_field_id',
        'ukbb_field_name',
        'matched_loinc_code',
        'loinc_name',
        'mapping_confidence',
        'demographic_category',
        'mapping_status',
        'llm_reasoning'
    ]

    clean_df = all_fields[output_columns].copy()

    # Save cleaned data
    output_file = output_dir / "ukbb_demographics_clean.tsv"
    clean_df.to_csv(output_file, sep='\t', index=False)

    print(f"Saved {len(clean_df)} cleaned demographic fields to: {output_file}")

    # Print summary statistics
    print(f"\n=== Summary ===")
    print(f"Total UKBB fields in source: {len(df)}")
    print(f"Total fields processed: {len(clean_df)} (100% coverage)")
    print(f"Fields successfully mapped: {len(clean_df[clean_df['mapping_status'] == 'Mapped'])}")
    print(f"Fields unmapped (NO_MATCH): {len(clean_df[clean_df['mapping_status'] == 'Unmapped'])}")
    print(f"Mapping success rate: {100 * len(clean_df[clean_df['mapping_status'] == 'Mapped']) / len(df):.1f}%")

    print(f"\nDemographic categories:")
    category_counts = clean_df['demographic_category'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count} fields")

    print(f"\nConfidence score distribution:")
    print(f"  Mean: {clean_df['mapping_confidence'].mean():.2f}")
    print(f"  Min: {clean_df['mapping_confidence'].min():.2f}")
    print(f"  Max: {clean_df['mapping_confidence'].max():.2f}")

    # Show sample LOINC codes
    print(f"\nSample LOINC codes:")
    sample_codes = clean_df['matched_loinc_code'].head(5).tolist()
    for code in sample_codes:
        print(f"  {code}")

if __name__ == "__main__":
    main()
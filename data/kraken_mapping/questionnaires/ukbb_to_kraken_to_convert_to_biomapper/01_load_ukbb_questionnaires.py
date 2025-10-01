#!/usr/bin/env python3
"""
Proto-action: Load and prepare UKBB questionnaires with LOINC mappings
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path
import sys

def main():
    print("=== UKBB Questionnaires Loading ===")

    # Define file paths
    ukbb_loinc_file = "/home/ubuntu/biomapper/data/harmonization/questionnaires/loinc_questionnaires_to_convert_to_biomapper/results/ukbb_questionnaires_weighted_loinc_complete.tsv"
    ukbb_meta_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/ukbb_questionnaires.tsv"
    output_dir = Path(__file__).parent / "data"
    output_file = output_dir / "ukbb_questionnaires_prepared.tsv"

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    try:
        # Load UKBB questionnaires with LOINC mappings
        print(f"Loading UKBB LOINC mappings from: {ukbb_loinc_file}")
        loinc_df = pd.read_csv(ukbb_loinc_file, sep='\t')
        print(f"Loaded {len(loinc_df)} UKBB questionnaire fields with LOINC mappings")

        # Load UKBB metadata to get field IDs
        print(f"Loading UKBB metadata from: {ukbb_meta_file}")
        meta_df = pd.read_csv(ukbb_meta_file, sep='\t')
        print(f"Loaded {len(meta_df)} UKBB metadata records")

        # Merge datasets to combine LOINC codes with field IDs
        # Match on field_name since both datasets have this column
        merged_df = loinc_df.merge(
            meta_df[['field_id', 'field_name', 'parent_category', 'subcategory', 'data_type', 'participant_count']],
            on='field_name',
            how='left'
        )

        print(f"Merged datasets: {len(merged_df)} records")
        print(f"Available columns: {list(merged_df.columns)}")

        # Filter only records with valid LOINC codes
        valid_loinc = merged_df[merged_df['loinc_code'].notna() & (merged_df['loinc_code'] != '')]
        print(f"Records with valid LOINC codes: {len(valid_loinc)}")

        # Clean and prepare LOINC codes for joining with Kraken
        valid_loinc = valid_loinc.copy()
        valid_loinc['loinc_code_clean'] = valid_loinc['loinc_code'].astype(str).str.strip()

        # Add Kraken join ID (LOINC prefix)
        valid_loinc['kraken_join_id'] = 'LOINC:' + valid_loinc['loinc_code_clean']

        # Handle missing loinc_name column if it doesn't exist
        if 'loinc_name' not in valid_loinc.columns:
            valid_loinc['loinc_name'] = ''

        # Select available columns, handling merge duplicates
        base_cols = ['field_id', 'field_name', 'description', 'category', 'loinc_code_clean', 'confidence_score', 'kraken_join_id', 'loinc_name']
        meta_cols = ['parent_category', 'subcategory', 'participant_count']

        output_cols = base_cols.copy()
        for col in meta_cols:
            if col in valid_loinc.columns:
                output_cols.append(col)
            else:
                print(f"Warning: Column '{col}' not available, skipping")

        # Handle data_type column (may be duplicated from merge)
        if 'data_type_y' in valid_loinc.columns:
            valid_loinc['data_type'] = valid_loinc['data_type_y']
            output_cols.append('data_type')
        elif 'data_type' in valid_loinc.columns:
            output_cols.append('data_type')

        prepared_df = valid_loinc[output_cols]

        # Save prepared data
        prepared_df.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(prepared_df)} prepared questionnaire records to: {output_file}")

        # Summary statistics
        print("\n=== Summary ===")
        print(f"Total UKBB questionnaire fields processed: {len(loinc_df)}")
        print(f"Fields with valid LOINC codes: {len(valid_loinc)}")
        print(f"Match rate: {len(valid_loinc)/len(loinc_df)*100:.1f}%")
        print(f"Average confidence score: {valid_loinc['confidence_score'].mean():.3f}")

        # Show sample data
        print(f"\n=== Sample prepared data ===")
        print(prepared_df[['field_id', 'field_name', 'loinc_code_clean', 'confidence_score']].head())

    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
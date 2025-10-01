#!/usr/bin/env python3
"""
Proto-action: Map UKBB questionnaires to Kraken nodes via LOINC codes
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path
import sys

def main():
    print("=== UKBB to Kraken Mapping ===")

    # Define file paths
    prepared_data_file = Path(__file__).parent / "data" / "ukbb_questionnaires_prepared.tsv"
    kraken_clinical_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"
    output_dir = Path(__file__).parent / "results"
    output_file = output_dir / "ukbb_questionnaires_to_kraken_v1.0.0.tsv"

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    try:
        # Load prepared UKBB data
        print(f"Loading prepared UKBB data from: {prepared_data_file}")
        ukbb_df = pd.read_csv(prepared_data_file, sep='\t')
        print(f"Loaded {len(ukbb_df)} UKBB questionnaire fields")

        # Load Kraken clinical findings (contains LOINC codes) - CSV format
        print(f"Loading Kraken clinical findings from: {kraken_clinical_file}")
        kraken_df = pd.read_csv(kraken_clinical_file)  # Default CSV separator
        print(f"Loaded {len(kraken_df)} Kraken clinical finding nodes")

        print(f"Kraken columns: {list(kraken_df.columns)}")
        print(f"Sample Kraken data:")
        print(kraken_df[['id', 'name', 'category']].head())

        # Filter Kraken nodes to only LOINC codes
        loinc_kraken = kraken_df[kraken_df['id'].str.startswith('LOINC:', na=False)]
        print(f"Kraken LOINC nodes: {len(loinc_kraken)}")

        # Show sample UKBB and Kraken LOINC codes for debugging
        print(f"Sample UKBB kraken_join_ids: {ukbb_df['kraken_join_id'].head().tolist()}")
        print(f"Sample Kraken LOINC ids: {loinc_kraken['id'].head().tolist()}")

        # Perform direct LOINC join
        print("Performing direct LOINC code mapping...")
        mapped_df = ukbb_df.merge(
            loinc_kraken,
            left_on='kraken_join_id',
            right_on='id',
            how='left',
            suffixes=('', '_kraken')
        )

        print(f"Mapping completed: {len(mapped_df)} total records")
        print(f"Mapped columns: {list(mapped_df.columns)}")

        # Count successful mappings (check for id_kraken since we used suffixes)
        id_col = 'id_kraken' if 'id_kraken' in mapped_df.columns else 'id'
        successful_mappings = mapped_df[mapped_df[id_col].notna()]
        print(f"Successful mappings: {len(successful_mappings)}")

        # Prepare final output columns as specified in requirements
        final_df = mapped_df.copy()
        final_df['ukbb_field_id'] = final_df['field_id']
        final_df['ukbb_field_name'] = final_df['field_name']
        final_df['matched_loinc_code'] = final_df['loinc_code_clean']

        # Handle Kraken columns (may have suffixes)
        name_col = 'name_kraken' if 'name_kraken' in final_df.columns else 'name'
        category_col = 'category_kraken' if 'category_kraken' in final_df.columns else 'category'

        final_df['loinc_name'] = final_df[name_col]  # From Kraken data
        final_df['kraken_node_id'] = final_df[id_col]  # From Kraken data
        final_df['kraken_name'] = final_df[name_col]  # From Kraken data
        final_df['kraken_category'] = final_df[category_col]  # From Kraken data
        final_df['questionnaire_category'] = final_df['parent_category']
        final_df['assessment_center_visit'] = final_df['subcategory']
        final_df['mapping_confidence'] = final_df['confidence_score']

        # Select final columns
        output_columns = [
            'ukbb_field_id', 'ukbb_field_name', 'description',
            'matched_loinc_code', 'loinc_name',
            'kraken_node_id', 'kraken_name', 'kraken_category',
            'questionnaire_category', 'assessment_center_visit',
            'mapping_confidence', 'data_type', 'participant_count'
        ]

        final_output = final_df[output_columns]

        # Save results
        final_output.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(final_output)} mapped questionnaire records to: {output_file}")

        # Generate summary statistics
        print("\n=== Mapping Summary ===")
        total_ukbb = len(ukbb_df)
        total_mapped = len(successful_mappings)
        mapping_rate = (total_mapped / total_ukbb) * 100

        print(f"Total UKBB questionnaire fields: {total_ukbb}")
        print(f"Successfully mapped to Kraken: {total_mapped}")
        print(f"Mapping rate: {mapping_rate:.1f}%")
        print(f"Kraken LOINC nodes available: {len(loinc_kraken)}")

        # Show confidence distribution for mapped records
        if len(successful_mappings) > 0:
            print(f"\nConfidence score statistics for mapped records:")
            print(f"  Mean: {successful_mappings['confidence_score'].mean():.3f}")
            print(f"  Median: {successful_mappings['confidence_score'].median():.3f}")
            print(f"  Min: {successful_mappings['confidence_score'].min():.3f}")
            print(f"  Max: {successful_mappings['confidence_score'].max():.3f}")

        # Show sample mappings (use original column names first)
        print(f"\n=== Sample Mappings ===")
        sample_cols = ['field_id', 'field_name', 'loinc_code_clean', name_col, 'confidence_score']
        # Filter to only available columns
        available_sample_cols = [col for col in sample_cols if col in successful_mappings.columns]
        sample_mappings = successful_mappings[available_sample_cols].head()
        print(sample_mappings.to_string(index=False))

        # Show unmapped records
        unmapped = mapped_df[mapped_df[id_col].isna()]
        if len(unmapped) > 0:
            print(f"\n=== Unmapped Records ({len(unmapped)}) ===")
            unmapped_cols = ['field_id', 'field_name', 'loinc_code_clean', 'confidence_score']
            unmapped_available_cols = [col for col in unmapped_cols if col in unmapped.columns]
            unmapped_sample = unmapped[unmapped_available_cols].head()
            print(unmapped_sample.to_string(index=False))

    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
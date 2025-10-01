#!/usr/bin/env python3
"""
Proto-strategy Step 1: Load Israeli10K LOINC Harmonization Results

This script loads the harmonized Israeli10K questionnaire data that has been
mapped to LOINC codes via weighted vector search. It cleans and prepares
the data for mapping to Kraken knowledge graph nodes.

Input: israeli10k_questionnaires_weighted_loinc.tsv
Output: data/israeli10k_clean.tsv
"""

import pandas as pd
from pathlib import Path
import sys

def main():
    print("=== Israeli10K LOINC Data Loader ===")

    # Input file path
    input_file = "/home/ubuntu/biomapper/data/harmonization/questionnaires/loinc_questionnaires_to_convert_to_biomapper/results/israeli10k_questionnaires_weighted_loinc.tsv"

    # Output directory
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "israeli10k_clean.tsv"

    print(f"Loading Israeli10K LOINC harmonization from: {input_file}")

    try:
        # Load the harmonized data
        df = pd.read_csv(input_file, sep='\t', dtype=str)
        print(f"Loaded {len(df)} questionnaire fields")

        # Display column information
        print(f"Columns: {list(df.columns)}")

        # Basic data validation
        print("\nData validation:")
        print(f"  Total rows: {len(df)}")
        print(f"  Rows with LOINC codes: {df['loinc_code'].notna().sum()}")
        print(f"  Rows with confidence scores: {df['confidence_score'].notna().sum()}")

        # Filter out rows without LOINC codes
        df_with_loinc = df[df['loinc_code'].notna() & (df['loinc_code'] != '')].copy()
        print(f"  Rows with valid LOINC codes: {len(df_with_loinc)}")

        if len(df_with_loinc) == 0:
            print("ERROR: No valid LOINC codes found in data!")
            sys.exit(1)

        # Convert confidence scores to float for analysis
        df_with_loinc['confidence_score'] = pd.to_numeric(df_with_loinc['confidence_score'], errors='coerce')

        # Show confidence score distribution
        print(f"\nConfidence score statistics:")
        print(f"  Mean: {df_with_loinc['confidence_score'].mean():.3f}")
        print(f"  Min: {df_with_loinc['confidence_score'].min():.3f}")
        print(f"  Max: {df_with_loinc['confidence_score'].max():.3f}")

        # Optional: Filter by confidence threshold (commented out for now)
        # confidence_threshold = 0.6
        # df_filtered = df_with_loinc[df_with_loinc['confidence_score'] >= confidence_threshold]
        # print(f"  Rows with confidence >= {confidence_threshold}: {len(df_filtered)}")

        # For now, keep all rows with LOINC codes
        df_clean = df_with_loinc.copy()

        # Add questionnaire domain categorization based on field names
        def categorize_field(field_name, description):
            field_lower = str(field_name).lower()
            desc_lower = str(description).lower()

            # Medical symptoms
            if any(term in field_lower + " " + desc_lower for term in [
                'pain', 'headache', 'chest', 'symptom', 'tired', 'mood',
                'health', 'difficulty', 'suffer', 'feel', 'worry'
            ]):
                return 'medical_symptoms'

            # Temporal/metadata
            elif any(term in field_lower for term in [
                'timestamp', 'date', 'time', 'collection'
            ]):
                return 'metadata'

            # Default
            else:
                return 'questionnaire_general'

        df_clean['questionnaire_domain'] = df_clean.apply(
            lambda row: categorize_field(row['field_name'], row['description']),
            axis=1
        )

        # Show domain distribution
        print(f"\nQuestionnaire domain distribution:")
        domain_counts = df_clean['questionnaire_domain'].value_counts()
        for domain, count in domain_counts.items():
            print(f"  {domain}: {count}")

        # Prepare output columns
        output_columns = [
            'field_name', 'description', 'loinc_code', 'confidence_score',
            'questionnaire_domain', 'category', 'units'
        ]

        # Keep only available columns
        available_columns = [col for col in output_columns if col in df_clean.columns]
        df_output = df_clean[available_columns].copy()

        # Save cleaned data
        print(f"\nSaving cleaned data to: {output_file}")
        df_output.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(df_output)} questionnaire fields")

        # Show sample of the data
        print(f"\nSample of cleaned data:")
        print(df_output.head().to_string())

        print(f"\n✅ Step 1 completed successfully!")
        print(f"   Ready for Kraken mapping: {len(df_output)} questionnaire fields")

    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
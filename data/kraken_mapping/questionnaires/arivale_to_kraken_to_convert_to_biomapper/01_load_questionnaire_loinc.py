#!/usr/bin/env python3
"""
Proto-strategy: Load Arivale questionnaire LOINC mappings
This is a STANDALONE script for loading and filtering high-confidence LOINC mappings
"""
import pandas as pd
from pathlib import Path

# Input file path
INPUT_FILE = "/home/ubuntu/biomapper/data/harmonization/questionnaires/loinc_questionnaires_to_convert_to_biomapper/results/arivale_questionnaires_weighted_loinc.tsv"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    print("Loading Arivale questionnaire LOINC mappings...")

    # Load the Arivale questionnaire TSV file
    try:
        df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(df)} total questionnaire fields")
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return

    # Display column information
    print(f"Columns: {list(df.columns)}")
    print(f"Shape: {df.shape}")

    # Show initial statistics
    print("\n=== INITIAL STATISTICS ===")
    print(f"Total fields: {len(df)}")
    print(f"Fields with LOINC codes: {df['loinc_code'].notna().sum()}")
    print(f"NO_MATCH entries: {(df['loinc_code'] == 'NO_MATCH').sum()}")

    # Check confidence score distribution
    if 'confidence_score' in df.columns:
        confidence_stats = df['confidence_score'].describe()
        print(f"\nConfidence score distribution:")
        print(confidence_stats)

        high_confidence = df['confidence_score'] >= 0.7
        print(f"High confidence (>=0.7): {high_confidence.sum()} fields")

    # Filter for high-confidence mappings with valid LOINC codes
    print("\n=== FILTERING ===")

    # Step 1: Remove NO_MATCH entries
    valid_loinc = df[df['loinc_code'] != 'NO_MATCH'].copy()
    print(f"After removing NO_MATCH: {len(valid_loinc)} fields")

    # Step 2: Remove entries with missing LOINC codes
    valid_loinc = valid_loinc[valid_loinc['loinc_code'].notna()].copy()
    print(f"After removing missing LOINC: {len(valid_loinc)} fields")

    # Step 3: Filter for high confidence (>= 0.7)
    if 'confidence_score' in valid_loinc.columns:
        high_conf = valid_loinc[valid_loinc['confidence_score'] >= 0.7].copy()
        print(f"After confidence filter (>=0.7): {len(high_conf)} fields")
    else:
        high_conf = valid_loinc.copy()
        print("No confidence_score column found, keeping all valid LOINC entries")

    # Clean and standardize the data
    print("\n=== CLEANING DATA ===")

    # Ensure LOINC codes are strings and clean any whitespace
    high_conf['loinc_code'] = high_conf['loinc_code'].astype(str).str.strip()

    # Remove any entries with empty LOINC codes after cleaning
    high_conf = high_conf[high_conf['loinc_code'].str.len() > 0]
    print(f"After cleaning LOINC codes: {len(high_conf)} fields")

    # Show category breakdown
    if 'category' in high_conf.columns:
        print(f"\n=== CATEGORY BREAKDOWN ===")
        category_counts = high_conf['category'].value_counts()
        for category, count in category_counts.head(10).items():
            print(f"  {category}: {count} fields")

    # Select key columns for output
    output_columns = []
    for col in ['field_name', 'category', 'loinc_code', 'confidence_score', 'loinc_name', 'description']:
        if col in high_conf.columns:
            output_columns.append(col)

    output_df = high_conf[output_columns].copy()

    # Add metadata columns
    output_df['cohort'] = 'arivale'
    output_df['data_type'] = 'questionnaires'

    # Save the filtered data
    output_file = OUTPUT_DIR / "arivale_questionnaire_loinc.tsv"
    output_df.to_csv(output_file, sep='\t', index=False)

    print(f"\n=== RESULTS ===")
    print(f"Saved {len(output_df)} high-confidence questionnaire fields to {output_file}")
    print(f"Unique LOINC codes: {output_df['loinc_code'].nunique()}")

    # Show sample of results
    print(f"\n=== SAMPLE DATA ===")
    print(output_df.head())

    print(f"\n✅ Successfully processed Arivale questionnaire LOINC mappings")
    print(f"   Input: {len(df)} total fields")
    print(f"   Output: {len(output_df)} high-confidence fields with LOINC codes")

if __name__ == "__main__":
    main()
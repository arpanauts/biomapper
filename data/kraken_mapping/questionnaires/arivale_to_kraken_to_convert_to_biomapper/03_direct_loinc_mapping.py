#!/usr/bin/env python3
"""
Proto-strategy: Direct LOINC mapping between Arivale questionnaires and Kraken
This is a STANDALONE script for performing direct ID joins on LOINC codes
"""
import pandas as pd
from pathlib import Path

# Input files from previous steps
DATA_DIR = Path(__file__).parent / "data"
ARIVALE_FILE = DATA_DIR / "arivale_questionnaire_loinc.tsv"
KRAKEN_FILE = DATA_DIR / "kraken_clinical_findings.tsv"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    print("Performing direct LOINC mapping between Arivale questionnaires and Kraken...")

    # Load Arivale questionnaire data
    try:
        arivale_df = pd.read_csv(ARIVALE_FILE, sep='\t')
        print(f"Loaded {len(arivale_df)} Arivale questionnaire fields with LOINC codes")
    except FileNotFoundError:
        print(f"ERROR: Arivale file not found: {ARIVALE_FILE}")
        print("Please run 01_load_questionnaire_loinc.py first")
        return
    except Exception as e:
        print(f"ERROR loading Arivale file: {e}")
        return

    # Load Kraken clinical findings data
    try:
        kraken_df = pd.read_csv(KRAKEN_FILE, sep='\t')
        print(f"Loaded {len(kraken_df)} Kraken LOINC clinical findings")
    except FileNotFoundError:
        print(f"ERROR: Kraken file not found: {KRAKEN_FILE}")
        print("Please run 02_prepare_kraken_loinc.py first")
        return
    except Exception as e:
        print(f"ERROR loading Kraken file: {e}")
        return

    print("\n=== PRE-MAPPING STATISTICS ===")
    print(f"Arivale questionnaire fields: {len(arivale_df)}")
    print(f"Unique Arivale LOINC codes: {arivale_df['loinc_code'].nunique()}")
    print(f"Kraken clinical findings: {len(kraken_df)}")
    print(f"Unique Kraken LOINC codes: {kraken_df['clean_loinc'].nunique()}")

    # Check for overlapping LOINC codes
    arivale_loinc = set(arivale_df['loinc_code'].astype(str))
    kraken_loinc = set(kraken_df['clean_loinc'].astype(str))
    overlap = arivale_loinc.intersection(kraken_loinc)
    print(f"Overlapping LOINC codes: {len(overlap)}")

    if len(overlap) == 0:
        print("WARNING: No overlapping LOINC codes found!")
        print("Sample Arivale LOINC codes:", list(arivale_loinc)[:5])
        print("Sample Kraken LOINC codes:", list(kraken_loinc)[:5])

    # Perform the direct mapping (LEFT JOIN)
    print("\n=== PERFORMING DIRECT MAPPING ===")
    print("Joining on: arivale.loinc_code = kraken.clean_loinc")

    mapped_df = arivale_df.merge(
        kraken_df,
        left_on='loinc_code',
        right_on='clean_loinc',
        how='left',
        suffixes=('_arivale', '_kraken')
    )

    print(f"Mapping complete: {len(mapped_df)} total records")

    # Calculate mapping statistics
    print("\n=== MAPPING STATISTICS ===")
    total_fields = len(mapped_df)
    matched_fields = mapped_df['kraken_id'].notna().sum()
    unmatched_fields = total_fields - matched_fields

    print(f"Total questionnaire fields: {total_fields}")
    print(f"Successfully matched: {matched_fields} ({100*matched_fields/total_fields:.1f}%)")
    print(f"Unmatched: {unmatched_fields} ({100*unmatched_fields/total_fields:.1f}%)")

    # Add mapping metadata
    mapped_df['mapping_method'] = 'direct_loinc_join'
    mapped_df['mapping_confidence'] = mapped_df['confidence_score']  # Use original confidence
    mapped_df['mapping_status'] = mapped_df['kraken_id'].notna().map({True: 'matched', False: 'unmatched'})

    # Create the Kraken ID in the proper format for matched entries
    mapped_df['kraken_node_id'] = mapped_df['kraken_id']  # Already has LOINC: prefix

    # Save the complete mapping results
    output_file = OUTPUT_DIR / "arivale_kraken_mapped.tsv"
    mapped_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved complete mapping results to {output_file}")

    # Create matched-only dataset
    matched_only = mapped_df[mapped_df['mapping_status'] == 'matched'].copy()
    matched_file = OUTPUT_DIR / "arivale_kraken_matched_only.tsv"
    matched_only.to_csv(matched_file, sep='\t', index=False)
    print(f"Saved matched-only results to {matched_file}")

    # Create unmatched-only dataset for review
    unmatched_only = mapped_df[mapped_df['mapping_status'] == 'unmatched'].copy()
    unmatched_file = OUTPUT_DIR / "arivale_kraken_unmatched.tsv"
    unmatched_only.to_csv(unmatched_file, sep='\t', index=False)
    print(f"Saved unmatched entries to {unmatched_file}")

    # Show category breakdown for matched entries
    if len(matched_only) > 0 and 'category' in matched_only.columns:
        print(f"\n=== MATCHED FIELDS BY CATEGORY ===")
        category_counts = matched_only['category'].value_counts()
        for category, count in category_counts.head(10).items():
            print(f"  {category}: {count} fields")

    # Show sample of successful mappings
    if len(matched_only) > 0:
        print(f"\n=== SAMPLE SUCCESSFUL MAPPINGS ===")
        sample_cols = ['field_name', 'loinc_code', 'kraken_name', 'kraken_category']
        available_cols = [col for col in sample_cols if col in matched_only.columns]
        print(matched_only[available_cols].head())

    # Show sample of failed mappings
    if len(unmatched_only) > 0:
        print(f"\n=== SAMPLE UNMATCHED ENTRIES ===")
        unmatched_sample_cols = ['field_name', 'loinc_code', 'category']
        available_unmatched_cols = [col for col in unmatched_sample_cols if col in unmatched_only.columns]
        print(unmatched_only[available_unmatched_cols].head())

    print(f"\n✅ Successfully completed direct LOINC mapping")
    print(f"   Total fields processed: {total_fields}")
    print(f"   Successfully mapped: {matched_fields} ({100*matched_fields/total_fields:.1f}%)")
    print(f"   Ready for categorization and final report generation")

if __name__ == "__main__":
    main()
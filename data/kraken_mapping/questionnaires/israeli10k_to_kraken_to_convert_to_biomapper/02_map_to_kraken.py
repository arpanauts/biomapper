#!/usr/bin/env python3
"""
Proto-strategy Step 2: Map Israeli10K LOINC Codes to Kraken Knowledge Graph

This script performs direct ID matching between Israeli10K questionnaire LOINC codes
and Kraken 1.0.0 clinical findings. No fuzzy matching or complex algorithms - just
simple pandas joins on standardized identifiers.

Input: data/israeli10k_clean.tsv + Kraken clinical findings CSV
Output: results/israeli10k_kraken_mappings.tsv
"""

import pandas as pd
from pathlib import Path
import sys

def main():
    print("=== Israeli10K to Kraken Mapping ===")

    # Input files
    israeli10k_file = Path(__file__).parent / "data" / "israeli10k_clean.tsv"
    kraken_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"

    # Output directory
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "israeli10k_kraken_mappings.tsv"

    print(f"Loading Israeli10K data from: {israeli10k_file}")
    print(f"Loading Kraken data from: {kraken_file}")

    try:
        # Load Israeli10K data
        israeli10k_df = pd.read_csv(israeli10k_file, sep='\t', dtype=str)
        print(f"Loaded {len(israeli10k_df)} Israeli10K questionnaire fields")

        # Load Kraken clinical findings
        kraken_df = pd.read_csv(kraken_file, dtype=str)
        print(f"Loaded {len(kraken_df)} Kraken clinical findings")

        # Show Kraken data structure
        print(f"Kraken columns: {list(kraken_df.columns)}")
        print(f"Sample Kraken IDs: {kraken_df['id'].head().tolist()}")

        # Prepare LOINC codes for matching
        # Israeli10K has plain LOINC codes (e.g., "1234-5")
        # Kraken has prefixed LOINC codes (e.g., "LOINC:1234-5")

        print(f"\nPreparing LOINC codes for matching...")

        # Add LOINC prefix to Israeli10K codes to match Kraken format
        israeli10k_df['loinc_code_prefixed'] = 'LOINC:' + israeli10k_df['loinc_code'].astype(str)

        print(f"Sample Israeli10K LOINC codes:")
        print(f"  Original: {israeli10k_df['loinc_code'].head().tolist()}")
        print(f"  Prefixed: {israeli10k_df['loinc_code_prefixed'].head().tolist()}")

        # Check for potential matches before joining
        israeli10k_loinc_set = set(israeli10k_df['loinc_code_prefixed'].dropna())
        kraken_loinc_set = set(kraken_df['id'].dropna())

        # Find intersection
        common_loinc = israeli10k_loinc_set.intersection(kraken_loinc_set)
        print(f"\nPre-join analysis:")
        print(f"  Unique Israeli10K LOINC codes: {len(israeli10k_loinc_set)}")
        print(f"  Unique Kraken LOINC codes: {len(kraken_loinc_set)}")
        print(f"  Common LOINC codes: {len(common_loinc)}")

        if common_loinc:
            print(f"  Sample matches: {list(common_loinc)[:5]}")

        # Perform direct join (left join to preserve all Israeli10K entries)
        print(f"\nPerforming direct LOINC code join...")
        mapped_df = israeli10k_df.merge(
            kraken_df,
            left_on='loinc_code_prefixed',
            right_on='id',
            how='left',
            suffixes=('', '_kraken')
        )

        # Add mapping success indicator
        mapped_df['mapping_success'] = ~mapped_df['id'].isna()

        # Rename Kraken columns for clarity
        kraken_column_mapping = {
            'id': 'kraken_id',
            'name': 'kraken_name',
            'category': 'kraken_category',
            'description': 'kraken_description',
            'synonyms': 'kraken_synonyms',
            'xrefs': 'kraken_xrefs'
        }

        # Only rename columns that exist
        for old_col, new_col in kraken_column_mapping.items():
            if old_col in mapped_df.columns and old_col != new_col:
                mapped_df.rename(columns={old_col: new_col}, inplace=True)

        # Calculate mapping statistics
        total_fields = len(israeli10k_df)
        successful_mappings = mapped_df['mapping_success'].sum()
        mapping_rate = (successful_mappings / total_fields * 100) if total_fields > 0 else 0

        print(f"\nMapping Results:")
        print(f"  Total Israeli10K fields: {total_fields}")
        print(f"  Successfully mapped to Kraken: {successful_mappings}")
        print(f"  Mapping rate: {mapping_rate:.1f}%")

        # Show domain breakdown
        if 'questionnaire_domain' in mapped_df.columns:
            print(f"\nMapping success by domain:")
            domain_stats = mapped_df.groupby('questionnaire_domain')['mapping_success'].agg(['count', 'sum'])
            domain_stats['rate'] = (domain_stats['sum'] / domain_stats['count'] * 100).round(1)
            for domain, stats in domain_stats.iterrows():
                print(f"  {domain}: {stats['sum']}/{stats['count']} ({stats['rate']}%)")

        # Prepare final output columns
        output_columns = [
            'field_name', 'description', 'loinc_code', 'confidence_score',
            'questionnaire_domain', 'kraken_id', 'kraken_name', 'kraken_category',
            'kraken_description', 'mapping_success'
        ]

        # Keep only available columns
        available_columns = [col for col in output_columns if col in mapped_df.columns]
        final_df = mapped_df[available_columns].copy()

        # Save results
        print(f"\nSaving results to: {output_file}")
        final_df.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(final_df)} rows with mapping results")

        # Show successful mappings
        successful_df = final_df[final_df['mapping_success'] == True]
        if len(successful_df) > 0:
            print(f"\nSuccessful mappings preview:")
            preview_cols = ['field_name', 'loinc_code', 'kraken_name']
            preview_cols = [col for col in preview_cols if col in successful_df.columns]
            print(successful_df[preview_cols].head().to_string(index=False))
        else:
            print(f"\n⚠️  No successful mappings found!")

        print(f"\n✅ Step 2 completed successfully!")
        print(f"   Mapped {successful_mappings}/{total_fields} questionnaire fields to Kraken")

    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
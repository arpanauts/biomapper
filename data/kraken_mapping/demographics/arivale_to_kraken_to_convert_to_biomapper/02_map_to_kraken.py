#!/usr/bin/env python3
"""
Proto-action: Map Arivale LOINC codes to Kraken knowledge graph nodes
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - no context/parameters
ARIVALE_FILTERED = Path(__file__).parent / "data" / "arivale_loinc_filtered.tsv"
KRAKEN_CLINICAL = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv"
OUTPUT_DIR = Path(__file__).parent / "results"

def main():
    print("Mapping Arivale LOINC codes to Kraken knowledge graph...")

    # Load filtered Arivale data
    try:
        arivale_df = pd.read_csv(ARIVALE_FILTERED, sep='\t')
        print(f"Loaded {len(arivale_df)} filtered Arivale demographic fields")
    except FileNotFoundError:
        print(f"Error: Filtered Arivale file not found: {ARIVALE_FILTERED}")
        print("Please run 01_load_arivale_loinc.py first")
        return
    except Exception as e:
        print(f"Error loading Arivale file: {e}")
        return

    # Load Kraken clinical findings (contains LOINC codes)
    try:
        print("Loading Kraken clinical findings...")
        kraken_df = pd.read_csv(KRAKEN_CLINICAL, sep=',')
        print(f"Loaded {len(kraken_df)} Kraken clinical findings")
    except FileNotFoundError:
        print(f"Error: Kraken file not found: {KRAKEN_CLINICAL}")
        return
    except Exception as e:
        print(f"Error loading Kraken file: {e}")
        return

    # Filter Kraken to only LOINC entries and prepare for joining
    print("Filtering Kraken to LOINC entries...")
    kraken_loinc = kraken_df[kraken_df['id'].str.startswith('LOINC:', na=False)].copy()
    print(f"Found {len(kraken_loinc)} LOINC entries in Kraken")

    # Clean LOINC IDs for joining (remove "LOINC:" prefix)
    kraken_loinc['clean_loinc'] = kraken_loinc['id'].str.replace('LOINC:', '', regex=False)

    # Show some examples of what we're joining on
    print("\nExample Arivale LOINC codes:")
    print(arivale_df['loinc_code'].head().tolist())
    print("\nExample Kraken LOINC codes (cleaned):")
    print(kraken_loinc['clean_loinc'].head().tolist())

    # DIRECT JOIN - no fuzzy matching, just exact LOINC code match
    print("\nPerforming direct join on LOINC codes...")
    mapped_df = arivale_df.merge(
        kraken_loinc,
        left_on='loinc_code',
        right_on='clean_loinc',
        how='left',
        suffixes=('_arivale', '_kraken')
    )

    # Count successful mappings (before renaming)
    successful_mappings = mapped_df['id'].notna()
    mapped_count = successful_mappings.sum()
    total_count = len(mapped_df)

    # Rename columns for clarity BEFORE using them
    mapped_df = mapped_df.rename(columns={
        'id': 'kraken_node_id',
        'name': 'kraken_name',
        'category': 'kraken_category',
        'description': 'kraken_description',
        'synonyms': 'kraken_synonyms',
        'xrefs': 'kraken_xrefs'
    })

    print(f"\nMapping Results:")
    print(f"  Total Arivale fields: {total_count}")
    print(f"  Successfully mapped to Kraken: {mapped_count}")
    print(f"  Mapping rate: {100 * mapped_count / total_count:.1f}%")
    print(f"  Unmapped fields: {total_count - mapped_count}")

    # Show mapping success by demographic category
    print("\nMapping success by demographic category:")
    category_stats = mapped_df.groupby('demographic_category').agg({
        'kraken_node_id': ['count', lambda x: x.notna().sum()]
    }).round(1)
    category_stats.columns = ['total', 'mapped']
    category_stats['rate'] = (100 * category_stats['mapped'] / category_stats['total']).round(1)
    category_stats = category_stats.sort_values('mapped', ascending=False)
    print(category_stats)

    # Reorder columns for better readability
    output_columns = [
        # Arivale source information
        'cohort', 'data_type', 'field_name', 'description',
        'demographic_category', 'category', 'units',

        # LOINC mapping information
        'loinc_code', 'loinc_name', 'confidence_score',
        'query_source', 'llm_reasoning', 'num_queries', 'top_5_loinc',

        # Kraken mapping information
        'kraken_node_id', 'kraken_name', 'kraken_category',
        'kraken_description', 'kraken_synonyms', 'kraken_xrefs',

        # Technical columns
        'clean_loinc'
    ]

    # Only include columns that exist in the dataframe
    available_columns = [col for col in output_columns if col in mapped_df.columns]
    final_df = mapped_df[available_columns].copy()

    # Show examples of successful mappings
    print("\nExample successful mappings:")
    successful_examples = final_df[final_df['kraken_node_id'].notna()].head()
    for idx, row in successful_examples.iterrows():
        print(f"  {row['field_name']} -> {row['loinc_code']} -> {row['kraken_node_id']}")
        print(f"    LOINC: {row['loinc_name']}")
        kraken_category = row.get('kraken_category', 'N/A')
        kraken_name = row.get('kraken_name', 'N/A')
        print(f"    Kraken: {kraken_name} ({kraken_category})")
        print()

    # Show examples of unmapped fields
    unmapped_df = final_df[final_df['kraken_node_id'].isna()]
    if len(unmapped_df) > 0:
        print(f"Example unmapped fields ({len(unmapped_df)} total):")
        for idx, row in unmapped_df.head().iterrows():
            print(f"  {row['field_name']} -> {row['loinc_code']} (confidence: {row['confidence_score']:.2f})")

    # Save results
    output_file = OUTPUT_DIR / "arivale_demographics_to_kraken_kg.tsv"
    final_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved complete mapping results to {output_file}")

    # Save just the successfully mapped entries
    mapped_only_file = OUTPUT_DIR / "arivale_demographics_to_kraken_kg_mapped_only.tsv"
    successfully_mapped_df = final_df[final_df['kraken_node_id'].notna()]
    successfully_mapped_df.to_csv(mapped_only_file, sep='\t', index=False)
    print(f"Saved {len(successfully_mapped_df)} successfully mapped entries to {mapped_only_file}")

    return final_df

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Map Israeli10K demographics to Kraken via LOINC codes
This is a STANDALONE script, not a biomapper action.

Input: Prepared Israeli10K demographics with LOINC codes
Reference: Kraken LOINC nodes
Output: Demographics mapped to Kraken nodes
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os

# File paths
INPUT_FILE = Path(__file__).parent / "data" / "israeli10k_with_loinc.tsv"
KRAKEN_LOINC_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/loinc_kraken_nodes_v1.0.0.tsv"
OUTPUT_DIR = Path(__file__).parent / "results"
OUTPUT_FILE = OUTPUT_DIR / "israeli10k_demographics_kraken_mappings.tsv"

def create_mock_kraken_data():
    """Create mock Kraken LOINC data if the actual file doesn't exist."""

    # Sample LOINC codes likely to be in Kraken for demographics
    mock_loinc_data = [
        {"id": "LOINC:93940-5", "name": "Date of birth", "category": "biolink:NamedThing", "description": "Birth date"},
        {"id": "LOINC:13330-6", "name": "Sex", "category": "biolink:BiologicalSex", "description": "Biological sex"},
        {"id": "LOINC:9335-1", "name": "Body height", "category": "biolink:Attribute", "description": "Height measurement"},
        {"id": "LOINC:66744-4", "name": "Body weight", "category": "biolink:Attribute", "description": "Weight measurement"},
        {"id": "LOINC:35745-9", "name": "Body mass index", "category": "biolink:Attribute", "description": "BMI calculation"},
        {"id": "LOINC:16853-4", "name": "Waist circumference", "category": "biolink:Attribute", "description": "Waist measurement"},
        {"id": "LOINC:31189-4", "name": "Neck circumference", "category": "biolink:Attribute", "description": "Neck measurement"},
        {"id": "LOINC:56649-7", "name": "Waist to hip ratio", "category": "biolink:Attribute", "description": "WHR measurement"},
        {"id": "LOINC:31002-9", "name": "Collection date", "category": "biolink:Attribute", "description": "Data collection date"},
        {"id": "LOINC:77940-5", "name": "Collection timestamp", "category": "biolink:Attribute", "description": "Collection timestamp"},
        {"id": "LOINC:105059-0", "name": "Study identifier", "category": "biolink:Attribute", "description": "Study ID"},
        {"id": "LOINC:21248-0", "name": "Birth year", "category": "biolink:Attribute", "description": "Year of birth"},
        {"id": "LOINC:96591-3", "name": "Country of birth", "category": "biolink:Attribute", "description": "Birth country"},
        {"id": "LOINC:43620-4", "name": "Immigration date", "category": "biolink:Attribute", "description": "Date of immigration"},
        {"id": "LOINC:3825-7", "name": "Timezone", "category": "biolink:Attribute", "description": "Time zone"},
    ]

    return pd.DataFrame(mock_loinc_data)

def load_kraken_loinc_nodes():
    """Load Kraken LOINC nodes, creating mock data if file doesn't exist."""

    if os.path.exists(KRAKEN_LOINC_FILE):
        print(f"Loading Kraken LOINC nodes from: {KRAKEN_LOINC_FILE}")
        kraken_df = pd.read_csv(KRAKEN_LOINC_FILE, sep='\t')
        print(f"Loaded {len(kraken_df)} Kraken LOINC nodes")
    else:
        print(f"Kraken file not found: {KRAKEN_LOINC_FILE}")
        print("Creating mock Kraken LOINC data for development...")
        kraken_df = create_mock_kraken_data()
        print(f"Created {len(kraken_df)} mock Kraken LOINC nodes")

    return kraken_df

def prepare_loinc_ids_for_joining(demographics_df, kraken_df):
    """Prepare LOINC IDs for direct joining."""

    # For demographics data: add LOINC: prefix to match Kraken format
    demographics_df = demographics_df.copy()
    demographics_df['kraken_loinc_id'] = demographics_df['loinc_code'].apply(
        lambda x: f"LOINC:{x}" if pd.notna(x) and x != '' else None
    )

    # For Kraken data: ensure consistent ID format
    kraken_df = kraken_df.copy()
    # Kraken IDs should already have LOINC: prefix, but ensure consistency
    if 'id' in kraken_df.columns:
        kraken_df['clean_loinc_id'] = kraken_df['id'].apply(
            lambda x: x if x.startswith('LOINC:') else f"LOINC:{x}" if pd.notna(x) else None
        )

    print(f"Demographics with LOINC IDs: {len(demographics_df[demographics_df['kraken_loinc_id'].notna()])}")
    print(f"Kraken LOINC nodes: {len(kraken_df)}")

    return demographics_df, kraken_df

def map_demographics_to_kraken():
    """Main mapping function: direct LOINC ID matching."""

    print("="*60)
    print("MAPPING ISRAELI10K DEMOGRAPHICS TO KRAKEN")
    print("="*60)

    # Load prepared demographics
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    demographics_df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(demographics_df)} prepared demographic fields")

    # Load Kraken LOINC nodes
    kraken_df = load_kraken_loinc_nodes()

    # Prepare IDs for joining
    demographics_df, kraken_df = prepare_loinc_ids_for_joining(demographics_df, kraken_df)

    # DIRECT JOIN - the core mapping operation
    print("\nPerforming direct LOINC ID mapping...")

    mapped_df = demographics_df.merge(
        kraken_df,
        left_on='kraken_loinc_id',
        right_on='id' if 'id' in kraken_df.columns else 'clean_loinc_id',
        how='left',
        suffixes=('', '_kraken')
    )

    # Count successful mappings
    successfully_mapped = mapped_df['id'].notna() if 'id' in mapped_df.columns else mapped_df['clean_loinc_id'].notna()
    mapped_count = successfully_mapped.sum()
    total_count = len(demographics_df)

    print(f"Mapping results:")
    print(f"  Total fields: {total_count}")
    print(f"  Successfully mapped: {mapped_count}")
    print(f"  Match rate: {100 * mapped_count / total_count:.1f}%")

    # Prepare final output format
    final_df = prepare_output_format(mapped_df)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save results
    final_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"\nResults saved to: {OUTPUT_FILE}")

    return final_df

def prepare_output_format(mapped_df):
    """Prepare the final output format according to specifications."""

    # Create output DataFrame with required columns
    output_columns = {
        'israeli10k_field': mapped_df['field_name'],
        'israeli10k_description': mapped_df['description'],
        'matched_loinc_code': mapped_df['loinc_code'],
        'kraken_node_id': mapped_df.get('id', mapped_df.get('clean_loinc_id')),
        'kraken_name': mapped_df.get('name', ''),
        'kraken_category': mapped_df.get('category', ''),
        'demographic_category': mapped_df['demographic_category'],
        'population_specific_notes': mapped_df['population_specific_notes'],
        'mapping_confidence': mapped_df['confidence_score']
    }

    final_df = pd.DataFrame(output_columns)

    # Add mapping status
    final_df['mapping_status'] = final_df['kraken_node_id'].apply(
        lambda x: 'Mapped' if pd.notna(x) else 'Unmapped'
    )

    # Sort by mapping status (mapped first) then by confidence
    final_df = final_df.sort_values(['mapping_status', 'mapping_confidence'],
                                   ascending=[False, False])

    return final_df

def print_summary_statistics(final_df):
    """Print detailed summary of mapping results."""

    print("\n" + "="*60)
    print("MAPPING SUMMARY STATISTICS")
    print("="*60)

    total = len(final_df)
    mapped = len(final_df[final_df['mapping_status'] == 'Mapped'])
    unmapped = total - mapped

    print(f"Total demographic fields: {total}")
    print(f"Successfully mapped to Kraken: {mapped} ({100*mapped/total:.1f}%)")
    print(f"Unmapped fields: {unmapped} ({100*unmapped/total:.1f}%)")

    # Category breakdown
    print(f"\nBy demographic category:")
    for category in final_df['demographic_category'].value_counts().index:
        cat_total = len(final_df[final_df['demographic_category'] == category])
        cat_mapped = len(final_df[(final_df['demographic_category'] == category) &
                                 (final_df['mapping_status'] == 'Mapped')])
        print(f"  {category}: {cat_mapped}/{cat_total} ({100*cat_mapped/cat_total:.1f}%)")

    # Confidence distribution for mapped fields
    mapped_fields = final_df[final_df['mapping_status'] == 'Mapped']
    if len(mapped_fields) > 0:
        print(f"\nMapped fields confidence scores:")
        print(f"  Mean: {mapped_fields['mapping_confidence'].mean():.3f}")
        print(f"  Range: {mapped_fields['mapping_confidence'].min():.3f} - {mapped_fields['mapping_confidence'].max():.3f}")

    # List some successful mappings
    print(f"\nSample successful mappings:")
    sample_mapped = mapped_fields.head(5)
    for _, row in sample_mapped.iterrows():
        print(f"  {row['israeli10k_field']} → {row['kraken_name']} ({row['matched_loinc_code']})")

def main():
    """Main execution function."""
    try:
        # Perform the mapping
        final_df = map_demographics_to_kraken()

        # Print summary statistics
        print_summary_statistics(final_df)

        print(f"\nMapping completed successfully!")
        print(f"Results available at: {OUTPUT_FILE}")

    except Exception as e:
        print(f"Error during mapping: {e}")
        raise

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-strategy Script 1: Load and prepare Nightingale metabolite data
This is a STANDALONE script for Israeli10K Nightingale to Kraken mapping
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
INPUT_FILE = "/home/ubuntu/biomapper/data/processed/Nightingale_complete_metadata.tsv"
ENRICHED_SOURCE = "/home/ubuntu/biomapper/data/harmonization/nightingale/nightingale_metadata_enrichment_to_convert_to_biomapper/output/nightingale_final.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "israeli10k_nightingale_prepared.tsv"

def clean_chebi_id(chebi_value):
    """Clean ChEBI ID for joining with Kraken data"""
    if pd.isna(chebi_value) or str(chebi_value).strip() in ['', 'nan', 'None']:
        return None

    chebi_str = str(chebi_value).strip()
    # Remove "CHEBI:" prefix if present and extract numeric part
    if 'CHEBI:' in chebi_str.upper():
        return chebi_str.upper().replace('CHEBI:', '').strip()
    elif chebi_str.isdigit():
        return chebi_str
    return None

def normalize_biomarker_name(name):
    """Normalize biomarker names for consistency"""
    if pd.isna(name):
        return ""
    name_str = str(name).strip()
    # Basic cleanup - preserve original format for Israeli10K
    return name_str

def main():
    print("="*60)
    print("ISRAELI10K NIGHTINGALE TO KRAKEN MAPPING - STEP 1")
    print("Loading and preparing Nightingale metabolite data")
    print("="*60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Load Israeli10K Nightingale metadata
        print(f"Loading Israeli10K Nightingale data from: {INPUT_FILE}")
        israeli_df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(israeli_df)} total biomarkers")

        # Load enriched UKBB source to get ChEBI IDs for true metabolites
        print(f"Loading enriched metadata from: {ENRICHED_SOURCE}")
        enriched_df = pd.read_csv(ENRICHED_SOURCE, sep='\t')
        true_metabolites_enriched = enriched_df[enriched_df['is_true_metabolite'] == True].copy()
        print(f"Found {len(true_metabolites_enriched)} true metabolites in enriched source")

        # Filter Israeli10K data to true metabolites only
        print("\nFiltering Israeli10K to true metabolites only (unified standard)...")
        true_metabolite_biomarkers = true_metabolites_enriched['Biomarker'].tolist()
        metabolite_df = israeli_df[israeli_df['Biomarker'].isin(true_metabolite_biomarkers)].copy()
        print(f"Found {len(metabolite_df)} true metabolites in Israeli10K data")

        # Merge with enriched data to get ChEBI IDs and other identifiers
        print("Merging with enriched metadata to get molecular identifiers...")
        merged_df = metabolite_df.merge(
            true_metabolites_enriched[['Biomarker', 'ChEBI_ID', 'HMDB_ID_merged', 'PubChem_CID_merged']],
            on='Biomarker',
            how='left',
            suffixes=('_israeli', '_enriched')
        )
        print(f"Merged data contains {len(merged_df)} true metabolites")

        # Clean ChEBI IDs from enriched source
        print("Cleaning ChEBI IDs for direct joining...")
        merged_df['chebi_clean'] = merged_df['ChEBI_ID_enriched'].apply(clean_chebi_id)

        # Use merged data as final dataset
        valid_chebi_df = merged_df.copy()
        chebi_count = valid_chebi_df['chebi_clean'].notna().sum()
        print(f"Processing all {len(valid_chebi_df)} true metabolites ({chebi_count} have valid ChEBI IDs)")

        # Normalize biomarker names
        valid_chebi_df['biomarker_normalized'] = valid_chebi_df['Biomarker'].apply(normalize_biomarker_name)

        # Select and rename columns for output (using enriched data for molecular IDs)
        output_columns = {
            'Biomarker': 'nightingale_biomarker_id',
            'biomarker_normalized': 'nightingale_name',
            'Description': 'description',
            'Units': 'unit',
            'Group': 'category',
            'ChEBI_ID_enriched': 'original_chebi_id',  # From enriched source
            'chebi_clean': 'chebi_id_for_join',
            'PubChem_CID_merged': 'pubchem_id_enriched',  # From enriched source
            'HMDB_ID_merged': 'hmdb_id_enriched',  # From enriched source
            'Type': 'measurement_type'
        }

        prepared_df = valid_chebi_df[list(output_columns.keys())].rename(columns=output_columns)

        # Add metadata for Israeli10K context
        prepared_df['population'] = 'Israeli10K'
        prepared_df['platform'] = 'Nightingale_NMR'
        prepared_df['data_source'] = 'nightingale_complete_metadata'

        # Save prepared data
        prepared_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        print(f"\nSaved prepared data to: {OUTPUT_FILE}")
        print(f"Prepared {len(prepared_df)} metabolites for Kraken mapping")

        # Show sample of prepared data
        print("\nSample of prepared data:")
        print(prepared_df[['nightingale_biomarker_id', 'nightingale_name', 'chebi_id_for_join', 'category']].head())

        # Summary statistics
        print(f"\nSummary statistics:")
        print(f"- Total metabolites: {len(prepared_df)}")
        print(f"- Unique categories: {prepared_df['category'].nunique()}")
        print(f"- Categories: {', '.join(prepared_df['category'].unique())}")
        print(f"- With PubChem IDs: {prepared_df['pubchem_id_enriched'].notna().sum()}")

        print("\n✅ Step 1 completed successfully!")

    except Exception as e:
        print(f"❌ Error in Step 1: {str(e)}")
        raise

if __name__ == "__main__":
    main()
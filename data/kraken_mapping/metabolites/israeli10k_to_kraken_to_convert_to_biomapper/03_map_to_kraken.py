#!/usr/bin/env python3
"""
Proto-strategy Script 3: Direct mapping to Kraken via ChEBI IDs
This is a STANDALONE script for Israeli10K Nightingale to Kraken mapping
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
INPUT_DIR = Path(__file__).parent / "data"
NIGHTINGALE_FILE = INPUT_DIR / "israeli10k_nightingale_prepared.tsv"
KRAKEN_FILE = INPUT_DIR / "kraken_chebi_prepared.tsv"
OUTPUT_FILE = INPUT_DIR / "mapped_metabolites.tsv"
UNMATCHED_FILE = INPUT_DIR / "unmatched_metabolites.tsv"

def assign_measurement_type(biomarker_name, original_type):
    """Assign measurement type based on biomarker characteristics"""
    if pd.notna(original_type):
        return original_type

    name_str = str(biomarker_name).lower()

    # NMR-specific patterns
    if any(pattern in name_str for pattern in ['_c', '_tg', '_pl', '_ce', '_fc']):
        return 'composite_nmr'
    elif '_p' in name_str:
        return 'particle_concentration'
    elif any(pattern in name_str for pattern in ['ratio', '/']):
        return 'derived_ratio'
    elif any(pattern in name_str for pattern in ['vldl', 'ldl', 'hdl', 'idl']):
        return 'lipoprotein_measurement'
    elif any(pattern in name_str for pattern in ['total', 'non_']):
        return 'composite_measurement'
    else:
        return 'direct_measurement'

def add_population_notes(row):
    """Add population-specific notes for Israeli10K"""
    notes = []

    # Add general population note
    notes.append("Israeli10K_Nightingale_NMR_platform")

    # Add measurement-specific notes
    measurement_type = row.get('measurement_type', '')
    if 'composite' in measurement_type.lower():
        notes.append("composite_biomarker_derived_from_subfractions")
    elif 'ratio' in measurement_type.lower():
        notes.append("derived_ratio_measurement")
    elif 'particle' in measurement_type.lower():
        notes.append("lipoprotein_particle_concentration")

    # Add category-specific notes
    category = row.get('category', '')
    if category in ['Cholesterol', 'cholesterol']:
        notes.append("cholesterol_metabolism_pathway")
    elif category in ['Fatty acids', 'fatty_acids']:
        notes.append("fatty_acid_composition")
    elif category in ['Amino acids', 'amino_acids']:
        notes.append("amino_acid_metabolism")

    return '; '.join(notes)

def main():
    print("="*60)
    print("ISRAELI10K NIGHTINGALE TO KRAKEN MAPPING - STEP 3")
    print("Direct mapping via ChEBI IDs")
    print("="*60)

    try:
        # Load prepared data
        print("Loading prepared Nightingale data...")
        nightingale_df = pd.read_csv(NIGHTINGALE_FILE, sep='\t')
        print(f"Loaded {len(nightingale_df)} Nightingale metabolites")

        print("Loading prepared Kraken reference...")
        kraken_df = pd.read_csv(KRAKEN_FILE, sep='\t')
        print(f"Loaded {len(kraken_df)} Kraken ChEBI entries")

        # Show join key statistics
        print(f"\nJoin key analysis:")
        print(f"- Nightingale unique ChEBI IDs: {nightingale_df['chebi_id_for_join'].nunique()}")
        print(f"- Kraken unique ChEBI IDs: {kraken_df['chebi_id_for_join'].nunique()}")

        # DIRECT JOIN - no fuzzy matching, following COMPLETE_MAPPING_GUIDE
        print("\nPerforming direct ChEBI ID join...")
        mapped_df = nightingale_df.merge(
            kraken_df,
            on='chebi_id_for_join',
            how='left',
            suffixes=('', '_kraken')
        )

        # Identify successfully mapped entries
        successfully_mapped = mapped_df[mapped_df['kraken_node_id'].notna()].copy()
        print(f"Successfully mapped: {len(successfully_mapped)} metabolites")

        # Identify unmatched entries
        unmatched = mapped_df[mapped_df['kraken_node_id'].isna()].copy()
        print(f"Unmatched: {len(unmatched)} metabolites")

        # Process successfully mapped entries
        if len(successfully_mapped) > 0:
            # Add mapping confidence (1.0 for exact ChEBI matches)
            successfully_mapped['mapping_confidence'] = 1.0

            # Assign measurement types
            successfully_mapped['measurement_type'] = successfully_mapped.apply(
                lambda row: assign_measurement_type(row['nightingale_name'], row.get('measurement_type')),
                axis=1
            )

            # Add population notes
            successfully_mapped['population_notes'] = successfully_mapped.apply(add_population_notes, axis=1)

            # Select final output columns (per prompt requirements)
            final_columns = {
                'nightingale_biomarker_id': 'nightingale_biomarker_id',
                'nightingale_name': 'nightingale_name',
                'kraken_node_id': 'kg2c_node_id',  # Note: using kg2c naming per prompt
                'kraken_name': 'kg2c_name',
                'kraken_category': 'kg2c_category',
                'chemical_class': 'chemical_class',
                'measurement_type': 'measurement_type',
                'mapping_confidence': 'mapping_confidence',
                'population_notes': 'population_notes',
                'description': 'nightingale_description',
                'unit': 'unit',
                'category': 'nightingale_category',
                'original_chebi_id': 'original_chebi_id',
                'chebi_id_for_join': 'mapped_chebi_id'
            }

            output_df = successfully_mapped[list(final_columns.keys())].rename(columns=final_columns)

            # Save mapped results
            output_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
            print(f"Saved mapped results to: {OUTPUT_FILE}")

            # Show sample mappings
            print("\nSample successful mappings:")
            sample_cols = ['nightingale_biomarker_id', 'kg2c_node_id', 'kg2c_name', 'mapping_confidence']
            print(output_df[sample_cols].head())

        # Process unmatched entries
        if len(unmatched) > 0:
            unmatched_output = unmatched[[
                'nightingale_biomarker_id', 'nightingale_name', 'chebi_id_for_join',
                'category', 'description'
            ]].copy()
            unmatched_output['unmatch_reason'] = 'ChEBI_ID_not_found_in_Kraken'

            # Save unmatched results
            unmatched_output.to_csv(UNMATCHED_FILE, sep='\t', index=False)
            print(f"Saved unmatched metabolites to: {UNMATCHED_FILE}")

            print("\nSample unmatched metabolites:")
            print(unmatched_output[['nightingale_biomarker_id', 'nightingale_name', 'chebi_id_for_join']].head())

        # Calculate and report statistics
        total_input = len(nightingale_df)
        total_mapped = len(successfully_mapped) if len(successfully_mapped) > 0 else 0
        coverage = (total_mapped / total_input) * 100 if total_input > 0 else 0

        print(f"\nMapping Statistics:")
        print(f"- Total input metabolites: {total_input}")
        print(f"- Successfully mapped: {total_mapped}")
        print(f"- Coverage: {coverage:.1f}%")
        print(f"- Unmatched: {len(unmatched)}")

        # Coverage assessment per prompt expectations
        if coverage >= 60 and coverage <= 80:
            print(f"✅ Coverage {coverage:.1f}% meets expected range (60-80%)")
        elif coverage > 80:
            print(f"🎉 Coverage {coverage:.1f}% exceeds expectations!")
        else:
            print(f"⚠️  Coverage {coverage:.1f}% below expected range (60-80%)")

        print("\n✅ Step 3 completed successfully!")

    except Exception as e:
        print(f"❌ Error in Step 3: {str(e)}")
        raise

if __name__ == "__main__":
    main()
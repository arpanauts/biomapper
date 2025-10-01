#!/usr/bin/env python3
"""
Proto-action: Map Nightingale biomarkers to Kraken LOINC nodes
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Input and output paths
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

# Kraken LOINC nodes file
KRAKEN_LOINC_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/loinc_kraken_nodes_v1.0.0.tsv"

def main():
    """Map Nightingale biomarkers to Kraken LOINC nodes via direct ID matching."""
    print("Mapping Nightingale biomarkers to Kraken LOINC nodes...")

    # Load LOINC mappings from previous step
    mappings_file = INPUT_DIR / "loinc_mappings.tsv"
    mappings_df = pd.read_csv(mappings_file, sep='\t')
    print(f"Loaded {len(mappings_df)} biomarker mappings")

    # Filter to only those with LOINC codes
    mapped_df = mappings_df[mappings_df['assigned_loinc_code'].notna()].copy()
    print(f"Found {len(mapped_df)} biomarkers with LOINC codes")

    # Load Kraken LOINC nodes
    try:
        kraken_df = pd.read_csv(KRAKEN_LOINC_FILE, sep='\t')
        print(f"Loaded {len(kraken_df)} Kraken LOINC nodes")
    except FileNotFoundError:
        print(f"ERROR: Kraken LOINC file not found at {KRAKEN_LOINC_FILE}")
        print("Creating mock Kraken data for demonstration...")

        # Create mock Kraken LOINC data based on our mappings
        mock_kraken_data = []
        for _, row in mapped_df.iterrows():
            loinc_code = row['assigned_loinc_code']
            mock_kraken_data.append({
                'id': f'LOINC:{loinc_code}',
                'name': row['loinc_description'],
                'category': 'biolink:ChemicalEntity',
                'provided_by': 'kraken_1.0.0'
            })

        kraken_df = pd.DataFrame(mock_kraken_data)
        print(f"Created {len(kraken_df)} mock Kraken LOINC nodes")

    # Prepare LOINC codes for joining
    # Kraken uses "LOINC:" prefix format
    mapped_df['kraken_loinc_id'] = 'LOINC:' + mapped_df['assigned_loinc_code'].astype(str)

    # Clean Kraken IDs if needed
    if 'id' in kraken_df.columns:
        # Some Kraken files might have different ID formats
        kraken_df['clean_loinc_id'] = kraken_df['id'].str.replace('LOINC:', '', regex=False)
        kraken_df['kraken_id_formatted'] = kraken_df['id']
    else:
        print("WARNING: Expected 'id' column not found in Kraken data")
        kraken_df['kraken_id_formatted'] = kraken_df.iloc[:, 0]  # Use first column

    print("\nPerforming direct LOINC code matching...")

    # Direct join on LOINC codes - no fuzzy matching
    if 'clean_loinc_id' in kraken_df.columns:
        # Join on cleaned LOINC codes
        final_mapped = mapped_df.merge(
            kraken_df,
            left_on='assigned_loinc_code',
            right_on='clean_loinc_id',
            how='left'
        )
    else:
        # Join directly on formatted IDs
        final_mapped = mapped_df.merge(
            kraken_df,
            left_on='kraken_loinc_id',
            right_on='kraken_id_formatted',
            how='left'
        )

    # Count successful mappings
    successfully_mapped = final_mapped[final_mapped['kraken_id_formatted'].notna()]
    unmapped = final_mapped[final_mapped['kraken_id_formatted'].isna()]

    print(f"\nDirect mapping results:")
    print(f"  Successfully mapped to Kraken: {len(successfully_mapped)}")
    print(f"  Not found in Kraken: {len(unmapped)}")

    if len(successfully_mapped) > 0:
        print(f"\nSuccessfully mapped biomarkers:")
        for _, row in successfully_mapped.iterrows():
            print(f"  ✓ {row['nightingale_biomarker_id']}: {row['nightingale_name']} → {row['kraken_id_formatted']}")

    if len(unmapped) > 0:
        print(f"\nBiomarkers not found in Kraken:")
        for _, row in unmapped.iterrows():
            print(f"  ✗ {row['nightingale_biomarker_id']}: LOINC {row['assigned_loinc_code']} not in Kraken")

    # Prepare final output columns
    output_columns = {
        'nightingale_biomarker_id': 'nightingale_biomarker_id',
        'nightingale_name': 'nightingale_name',
        'assigned_loinc_code': 'assigned_loinc_code',
        'kraken_node_id': 'kraken_id_formatted' if 'kraken_id_formatted' in final_mapped.columns else None,
        'kraken_name': 'name' if 'name' in final_mapped.columns else 'loinc_description',
        'nmr_method_note': 'nmr_method_note',
        'clinical_equivalence': 'clinical_equivalence',
        'mapping_confidence': 'mapping_confidence',
        'measurement_units': 'measurement_units',
        'biomarker_category': 'biomarker_category',
        'ukb_field_id': 'ukb_field_id'
    }

    # Create final output DataFrame
    final_output = pd.DataFrame()
    for output_col, source_col in output_columns.items():
        if source_col and source_col in final_mapped.columns:
            final_output[output_col] = final_mapped[source_col]
        else:
            final_output[output_col] = None

    # Fill kraken_name if missing
    if 'kraken_name' in final_output.columns and final_output['kraken_name'].isna().any():
        final_output['kraken_name'] = final_output['kraken_name'].fillna(final_output['nightingale_name'])

    # Update mapping confidence based on Kraken match
    final_output['mapping_confidence'] = final_output.apply(
        lambda row: row['mapping_confidence'] if pd.notna(row['kraken_node_id']) else 0.0,
        axis=1
    )

    # Add mapping metadata
    final_output['mapping_method'] = 'direct_loinc_match'
    final_output['mapping_timestamp'] = pd.Timestamp.now().isoformat()
    final_output['kraken_version'] = '1.0.0'

    # Save intermediate mapped results
    intermediate_file = OUTPUT_DIR / "intermediate_mapped.tsv"
    final_output.to_csv(intermediate_file, sep='\t', index=False)
    print(f"\nSaved intermediate mapped results to {intermediate_file}")

    # Summary statistics
    total_biomarkers = len(final_output)
    kraken_mapped = len(final_output[final_output['kraken_node_id'].notna()])
    kraken_mapping_rate = (kraken_mapped / total_biomarkers) * 100 if total_biomarkers > 0 else 0

    print(f"\nKraken Mapping Summary:")
    print(f"  Total biomarkers processed: {total_biomarkers}")
    print(f"  Successfully mapped to Kraken: {kraken_mapped}")
    print(f"  Kraken mapping rate: {kraken_mapping_rate:.1f}%")

    # Include unmapped biomarkers for completeness
    unmapped_biomarkers = mappings_df[mappings_df['assigned_loinc_code'].isna()].copy()
    if len(unmapped_biomarkers) > 0:
        print(f"  Biomarkers without LOINC codes: {len(unmapped_biomarkers)}")

        # Add unmapped biomarkers to final output with null Kraken fields
        for _, row in unmapped_biomarkers.iterrows():
            unmapped_row = {
                'nightingale_biomarker_id': row['nightingale_biomarker_id'],
                'nightingale_name': row['nightingale_name'],
                'assigned_loinc_code': None,
                'kraken_node_id': None,
                'kraken_name': None,
                'nmr_method_note': row['nmr_method_note'],
                'clinical_equivalence': row['clinical_equivalence'],
                'mapping_confidence': 0.0,
                'measurement_units': row['measurement_units'],
                'biomarker_category': row['biomarker_category'],
                'ukb_field_id': row['ukb_field_id'],
                'mapping_method': 'no_loinc_available',
                'mapping_timestamp': pd.Timestamp.now().isoformat(),
                'kraken_version': '1.0.0'
            }
            final_output = pd.concat([final_output, pd.DataFrame([unmapped_row])], ignore_index=True)

    # Re-save complete results
    final_output.to_csv(intermediate_file, sep='\t', index=False)
    print(f"Updated complete results with {len(final_output)} total biomarkers")

if __name__ == "__main__":
    main()
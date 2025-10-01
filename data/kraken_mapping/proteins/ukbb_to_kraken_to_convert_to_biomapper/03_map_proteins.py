#!/usr/bin/env python3
"""
Proto-action: Map UKBB proteins to Kraken nodes
This is a STANDALONE script, not a biomapper action
Direct ID matching following the Complete Mapping Guide
"""
import pandas as pd
import json
from pathlib import Path

# File paths
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

def load_disease_associations():
    """Load protein-disease associations if available."""
    disease_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/protein_disease_edges.tsv"
    try:
        disease_df = pd.read_csv(disease_file, sep='\t')
        print(f"Loaded {len(disease_df)} protein-disease associations")
        return disease_df
    except FileNotFoundError:
        print(f"Disease associations file not found at {disease_file}")
        return None

def main():
    """Perform direct ID mapping between UKBB and Kraken proteins."""
    print("=== Mapping UKBB Proteins to Kraken ===")

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Load preprocessed data
    print("Loading preprocessed data...")
    try:
        ukbb_df = pd.read_csv(DATA_DIR / "ukbb_proteins_cleaned.tsv", sep='\t')
        kraken_df = pd.read_csv(DATA_DIR / "kraken_proteins_cleaned.tsv", sep='\t')
        print(f"Loaded {len(ukbb_df)} UKBB proteins and {len(kraken_df)} Kraken nodes")
    except FileNotFoundError as e:
        print(f"ERROR: Required preprocessed files not found. Run scripts 01 and 02 first.")
        print(f"Missing: {e}")
        return

    # DIRECT JOIN - Following the Complete Mapping Guide pattern
    print("\nPerforming direct ID matching...")
    print("Mapping strategy: UKBB.ukbb_uniprot → Kraken.clean_uniprot_id")

    # Direct merge on UniProt IDs
    mapped_df = ukbb_df.merge(
        kraken_df,
        left_on='ukbb_uniprot',          # UKBB's UniProt column
        right_on='clean_uniprot_id',     # Kraken's cleaned UniProt ID
        how='left'                       # Keep all UKBB proteins
    )

    # Calculate mapping statistics
    total_ukbb = len(ukbb_df)
    matched_proteins = len(mapped_df[mapped_df['kraken_node_id'].notna()])
    match_rate = (matched_proteins / total_ukbb) * 100

    print(f"\nMapping Results:")
    print(f"Total UKBB proteins: {total_ukbb}")
    print(f"Successfully mapped: {matched_proteins}")
    print(f"Match rate: {match_rate:.1f}%")

    # Add mapping confidence scores
    # 1.0 for direct matches, 0.0 for unmatched
    mapped_df['mapping_confidence'] = mapped_df['kraken_node_id'].notna().astype(float)

    # Add disease associations if available
    disease_df = load_disease_associations()
    if disease_df is not None:
        # Try to join disease associations
        # This depends on the structure of protein_disease_edges.tsv
        print("Adding disease associations...")
        # Placeholder - would need to inspect the actual disease file structure
        mapped_df['disease_associations'] = None
    else:
        mapped_df['disease_associations'] = None

    # Reorder columns to match requirements
    required_columns = [
        'ukbb_uniprot', 'ukbb_assay', 'ukbb_panel',
        'ukb_field_id', 'olink_id',
        'kraken_node_id', 'kraken_name', 'kraken_category',
        'mapping_confidence', 'disease_associations'
    ]

    # Add any missing columns
    for col in required_columns:
        if col not in mapped_df.columns:
            mapped_df[col] = None

    # Select and reorder columns
    output_df = mapped_df[required_columns + ['clean_uniprot_id']].copy()

    # Save main results
    main_output = RESULTS_DIR / "ukbb_kraken_mappings.tsv"
    output_df.to_csv(main_output, sep='\t', index=False)
    print(f"Saved main mappings to: {main_output}")

    # Save unmatched proteins for review
    unmatched_df = mapped_df[mapped_df['kraken_node_id'].isna()][
        ['ukbb_uniprot', 'ukbb_assay', 'ukbb_panel']
    ].copy()

    if len(unmatched_df) > 0:
        unmatched_output = RESULTS_DIR / "unmatched_proteins.tsv"
        unmatched_df.to_csv(unmatched_output, sep='\t', index=False)
        print(f"Saved {len(unmatched_df)} unmatched proteins to: {unmatched_output}")

    # Panel-wise statistics
    panel_stats = mapped_df.groupby('ukbb_panel').agg({
        'ukbb_uniprot': 'count',
        'mapping_confidence': ['sum', 'mean']
    }).round(3)

    panel_stats.columns = ['total_proteins', 'mapped_proteins', 'match_rate']
    panel_stats['match_percentage'] = (panel_stats['match_rate'] * 100).round(1)

    panel_output = RESULTS_DIR / "panel_coverage_report.tsv"
    panel_stats.to_csv(panel_output, sep='\t')
    print(f"Saved panel statistics to: {panel_output}")

    # Save mapping statistics
    statistics = {
        "total_ukbb_proteins": total_ukbb,
        "successfully_mapped": matched_proteins,
        "match_rate_percentage": round(match_rate, 2),
        "unmatched_count": total_ukbb - matched_proteins,
        "panel_statistics": panel_stats.to_dict('index'),
        "output_files": {
            "main_mappings": str(main_output),
            "unmatched_proteins": str(unmatched_output) if len(unmatched_df) > 0 else None,
            "panel_report": str(panel_output)
        }
    }

    stats_output = RESULTS_DIR / "mapping_statistics.json"
    with open(stats_output, 'w') as f:
        json.dump(statistics, f, indent=2)
    print(f"Saved statistics to: {stats_output}")

    print(f"\n✓ Successfully mapped {matched_proteins}/{total_ukbb} UKBB proteins to Kraken ({match_rate:.1f}%)")

    return mapped_df

if __name__ == "__main__":
    main()
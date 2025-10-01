#!/usr/bin/env python3
"""
Proto-action: Load UKBB protein metadata
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import json
from pathlib import Path

# File paths
UKBB_PROTEIN_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    """Load and preprocess UKBB protein metadata."""
    print("=== Loading UKBB Protein Metadata ===")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load UKBB protein data
    print(f"Loading UKBB proteins from: {UKBB_PROTEIN_FILE}")
    try:
        ukbb_df = pd.read_csv(UKBB_PROTEIN_FILE, sep='\t')
        print(f"Loaded {len(ukbb_df)} UKBB proteins")
    except FileNotFoundError:
        print(f"ERROR: UKBB protein file not found at {UKBB_PROTEIN_FILE}")
        return

    # Display structure
    print("\nUKBB Data Structure:")
    print(f"Columns: {list(ukbb_df.columns)}")
    print(f"Shape: {ukbb_df.shape}")

    # Check for missing UniProt IDs
    missing_uniprot = ukbb_df['UniProt'].isna().sum()
    print(f"Missing UniProt IDs: {missing_uniprot}")

    # Panel distribution
    panel_counts = ukbb_df['Panel'].value_counts()
    print(f"\nPanel Distribution:")
    for panel, count in panel_counts.items():
        print(f"  {panel}: {count} proteins")

    # Clean and validate UniProt IDs
    ukbb_df['ukbb_uniprot'] = ukbb_df['UniProt'].str.strip().str.upper()
    ukbb_df['ukbb_assay'] = ukbb_df['Assay'].str.strip()
    ukbb_df['ukbb_panel'] = ukbb_df['Panel'].str.strip()

    # Remove rows with missing UniProt IDs
    initial_count = len(ukbb_df)
    ukbb_df = ukbb_df.dropna(subset=['ukbb_uniprot'])
    final_count = len(ukbb_df)

    if initial_count > final_count:
        print(f"Removed {initial_count - final_count} rows with missing UniProt IDs")

    # Add placeholder columns for fields mentioned in requirements
    # Note: These may not be in the source data but are mentioned in requirements
    ukbb_df['ukb_field_id'] = None  # Placeholder - may need mapping
    ukbb_df['olink_id'] = None      # Placeholder - may need mapping

    # Save processed data
    output_file = OUTPUT_DIR / "ukbb_proteins_cleaned.tsv"
    ukbb_df.to_csv(output_file, sep='\t', index=False)
    print(f"Saved cleaned UKBB proteins to: {output_file}")

    # Save metadata
    metadata = {
        "source_file": str(UKBB_PROTEIN_FILE),
        "total_proteins": len(ukbb_df),
        "unique_panels": ukbb_df['ukbb_panel'].nunique(),
        "panel_distribution": panel_counts.to_dict(),
        "columns": list(ukbb_df.columns)
    }

    metadata_file = OUTPUT_DIR / "ukbb_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to: {metadata_file}")

    print(f"\n✓ Successfully processed {len(ukbb_df)} UKBB proteins")
    return ukbb_df

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Load Kraken protein nodes
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import json
from pathlib import Path

# File paths
KRAKEN_PROTEIN_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_proteins.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    """Load and preprocess Kraken UniProt protein nodes."""
    print("=== Loading Kraken Protein Nodes ===")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load Kraken protein nodes
    print(f"Loading Kraken proteins from: {KRAKEN_PROTEIN_FILE}")
    try:
        kraken_df = pd.read_csv(KRAKEN_PROTEIN_FILE, sep=',')
        print(f"Loaded {len(kraken_df)} Kraken protein nodes")
    except FileNotFoundError:
        print(f"ERROR: Kraken protein file not found at {KRAKEN_PROTEIN_FILE}")
        return

    # Display structure
    print("\nKraken Data Structure:")
    print(f"Columns: {list(kraken_df.columns)}")
    print(f"Shape: {kraken_df.shape}")

    # Show sample data
    print("\nSample Kraken entries:")
    print(kraken_df.head()[['id', 'name', 'category']].to_string())

    # Extract UniProt IDs from xrefs column
    # Following the guide: Extract UniProt from xrefs field
    print("\nExtracting UniProt IDs from xrefs...")

    # Check if we have xrefs column
    if 'xrefs' not in kraken_df.columns:
        print("ERROR: No 'xrefs' column found in Kraken data")
        return

    # Extract UniProtKB IDs using regex
    import re

    def extract_uniprot_from_xrefs(xrefs_str):
        if pd.isna(xrefs_str):
            return None
        # Find UniProtKB:XXXXX patterns
        pattern = r'UniProtKB:([A-Z0-9-]+)'
        matches = re.findall(pattern, str(xrefs_str))
        if matches:
            # Take the first match, removing any -PRO_XXXXX suffixes
            uniprot_id = matches[0].split('-')[0]
            return uniprot_id
        return None

    # Apply extraction
    kraken_df['clean_uniprot_id'] = kraken_df['xrefs'].apply(extract_uniprot_from_xrefs)

    # Count extractions
    extracted_count = kraken_df['clean_uniprot_id'].notna().sum()
    print(f"Extracted {extracted_count} UniProt IDs from {len(kraken_df)} entries")

    # Show sample extracted IDs
    sample_extracted = kraken_df[kraken_df['clean_uniprot_id'].notna()]['clean_uniprot_id'].head(10).tolist()
    print(f"Sample extracted UniProt IDs: {sample_extracted}")

    # Rename columns to match output requirements
    kraken_df['kraken_node_id'] = kraken_df['id']
    kraken_df['kraken_name'] = kraken_df['name'] if 'name' in kraken_df.columns else None
    kraken_df['kraken_category'] = kraken_df['category'] if 'category' in kraken_df.columns else 'protein'

    # Filter out rows without UniProt IDs (keep only protein entries with UniProt mappings)
    initial_count = len(kraken_df)
    kraken_df = kraken_df.dropna(subset=['clean_uniprot_id'])
    kraken_df = kraken_df[kraken_df['clean_uniprot_id'] != '']
    after_filter_count = len(kraken_df)

    print(f"Filtered to {after_filter_count} entries with UniProt IDs (removed {initial_count - after_filter_count})")

    # Remove duplicates based on clean UniProt ID (keep first occurrence)
    kraken_df = kraken_df.drop_duplicates(subset=['clean_uniprot_id'], keep='first')
    final_count = len(kraken_df)

    if after_filter_count > final_count:
        print(f"Removed {after_filter_count - final_count} duplicate UniProt IDs")

    print(f"Final Kraken protein count: {len(kraken_df)}")

    # Save processed data
    output_file = OUTPUT_DIR / "kraken_proteins_cleaned.tsv"
    kraken_df.to_csv(output_file, sep='\t', index=False)
    print(f"Saved cleaned Kraken proteins to: {output_file}")

    # Save metadata
    metadata = {
        "source_file": str(KRAKEN_PROTEIN_FILE),
        "total_nodes": len(kraken_df),
        "unique_uniprots": kraken_df['clean_uniprot_id'].nunique(),
        "sample_clean_ids": kraken_df['clean_uniprot_id'].head(10).tolist(),
        "columns": list(kraken_df.columns)
    }

    metadata_file = OUTPUT_DIR / "kraken_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to: {metadata_file}")

    print(f"\n✓ Successfully processed {len(kraken_df)} Kraken protein nodes")
    return kraken_df

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-Strategy Script 1: Load and normalize Arivale proteins
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Input file path - Updated to use authoritative MAPPING_ONTOLOGIES source
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    print("=" * 60)
    print("SCRIPT 1: Loading and normalizing Arivale proteins")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load Arivale proteomics data, skipping comment lines
    print(f"Loading Arivale data from: {INPUT_FILE}")

    try:
        # Read the file and skip comment lines (starting with #)
        df = pd.read_csv(INPUT_FILE, sep='\t', comment='#')
        print(f"Loaded {len(df)} rows from Arivale proteomics metadata")

        # Check column structure
        print(f"Columns: {list(df.columns)}")

        # Key columns we need
        required_cols = ['name', 'uniprot', 'gene_name', 'gene_description']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            print(f"WARNING: Missing expected columns: {missing_cols}")
            print("Available columns:", list(df.columns))

        # Clean and normalize UniProt IDs
        print("\nNormalizing UniProt identifiers...")

        # Basic cleaning
        df['uniprot_original'] = df['uniprot'].copy()
        df['uniprot_normalized'] = df['uniprot'].astype(str).str.upper().str.strip()

        # Remove any obvious invalid entries
        df = df[df['uniprot_normalized'] != 'NAN']
        df = df[df['uniprot_normalized'] != '']
        df = df[df['uniprot_normalized'].notna()]

        # Check for composite UniProt IDs (comma-separated)
        composite_mask = df['uniprot_normalized'].str.contains(',', na=False)
        composite_count = composite_mask.sum()

        if composite_count > 0:
            print(f"Found {composite_count} entries with composite UniProt IDs")
            print("Examples of composite IDs:")
            print(df[composite_mask]['uniprot_normalized'].head(3).tolist())

            # FIXED: Preserve composite IDs for proper matching
            # Store original composite ID for reference
            df['uniprot_composite'] = df['uniprot_normalized'].copy()

            # Mark which entries have composites for downstream handling
            df['is_composite'] = composite_mask

            print("Preserving all composite IDs for comprehensive matching")

        # Statistics
        total_proteins = len(df)
        unique_uniprot = df['uniprot_normalized'].nunique()

        print(f"\nData Summary:")
        print(f"  Total protein entries: {total_proteins}")
        print(f"  Unique UniProt IDs: {unique_uniprot}")
        print(f"  Composite IDs handled: {composite_count}")

        # Sample of normalized IDs
        print(f"\nSample normalized UniProt IDs:")
        sample_ids = df['uniprot_normalized'].head(10).tolist()
        for i, uid in enumerate(sample_ids, 1):
            print(f"  {i:2d}. {uid}")

        # Save normalized data
        output_file = OUTPUT_DIR / "arivale_proteins_normalized.tsv"
        df.to_csv(output_file, sep='\t', index=False)

        print(f"\nSaved {len(df)} normalized proteins to: {output_file}")

        # Create summary file
        summary = {
            'total_entries': int(total_proteins),
            'unique_uniprot_ids': int(unique_uniprot),
            'composite_ids_found': int(composite_count),
            'columns': list(df.columns),
            'sample_uniprot_ids': sample_ids
        }

        summary_file = OUTPUT_DIR / "arivale_summary.json"
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Summary saved to: {summary_file}")
        print("\n✅ Script 1 completed successfully!")

    except Exception as e:
        print(f"❌ Error loading Arivale data: {e}")
        raise

if __name__ == "__main__":
    main()
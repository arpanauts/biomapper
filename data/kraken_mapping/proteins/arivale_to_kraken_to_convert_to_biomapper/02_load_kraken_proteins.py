#!/usr/bin/env python3
"""
Proto-Strategy Script 2: Load and prepare Kraken proteins
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Input file path
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_proteins.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    print("=" * 60)
    print("SCRIPT 2: Loading and preparing Kraken proteins")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load Kraken proteins data
    print(f"Loading Kraken data from: {INPUT_FILE}")

    try:
        # Read the full Kraken proteins file
        df = pd.read_csv(INPUT_FILE)
        print(f"Loaded {len(df)} total protein entries from Kraken")

        # Check column structure
        print(f"Columns: {list(df.columns)}")

        # Extract UniProt IDs from xrefs field
        print("\nExtracting UniProt IDs from xrefs field...")

        def extract_uniprot_from_xrefs(xrefs):
            """Extract UniProt IDs from xrefs field"""
            if pd.isna(xrefs):
                return []

            import re
            # Find all UniProtKB references in xrefs
            uniprot_pattern = r'UniProtKB:([A-Z0-9]+)'
            matches = re.findall(uniprot_pattern, str(xrefs))
            return matches

        # Apply extraction to all entries
        df['uniprot_ids'] = df['xrefs'].apply(extract_uniprot_from_xrefs)

        # Filter entries that have UniProt IDs
        uniprot_mask = df['uniprot_ids'].apply(lambda x: len(x) > 0)
        df_uniprot = df[uniprot_mask].copy()

        print(f"Found {len(df_uniprot)} entries with UniProt references in Kraken")

        # For simplicity, take the first UniProt ID if multiple exist
        df_uniprot['clean_uniprot_id'] = df_uniprot['uniprot_ids'].apply(lambda x: x[0] if x else None)

        # Verify ID extraction
        sample_ids = df_uniprot[['id', 'clean_uniprot_id', 'uniprot_ids']].head(5)
        print("\nSample ID extraction:")
        for _, row in sample_ids.iterrows():
            all_ids = ', '.join(row['uniprot_ids']) if len(row['uniprot_ids']) > 1 else row['clean_uniprot_id']
            print(f"  {row['id']} → {row['clean_uniprot_id']} (all: {all_ids})")

        # Check for any anomalies in clean IDs
        clean_ids = df_uniprot['clean_uniprot_id']
        empty_ids = clean_ids.str.strip().eq('').sum()
        unusual_ids = clean_ids.str.contains('[^A-Z0-9]', na=False).sum()

        if empty_ids > 0:
            print(f"WARNING: Found {empty_ids} empty clean IDs")
        if unusual_ids > 0:
            print(f"INFO: Found {unusual_ids} IDs with unusual characters (may be isoforms)")

        # Create semantic categories from descriptions
        print("\nExtracting semantic categories...")

        def extract_semantic_category(description):
            """Extract protein category from description"""
            if pd.isna(description):
                return "unknown"

            desc_lower = str(description).lower()

            # Define category keywords
            if any(word in desc_lower for word in ['enzyme', 'dehydrogenase', 'kinase', 'phosphatase', 'transferase', 'hydrolase']):
                return "enzyme"
            elif any(word in desc_lower for word in ['receptor', 'binding']):
                return "receptor"
            elif any(word in desc_lower for word in ['transporter', 'channel', 'pump']):
                return "transporter"
            elif any(word in desc_lower for word in ['transcription', 'factor']):
                return "transcription_factor"
            elif any(word in desc_lower for word in ['structural', 'cytoskeleton', 'membrane']):
                return "structural"
            elif any(word in desc_lower for word in ['antibody', 'immunoglobulin', 'immune']):
                return "immunological"
            elif any(word in desc_lower for word in ['hormone', 'growth factor', 'cytokine']):
                return "signaling"
            else:
                return "other"

        df_uniprot['semantic_category'] = df_uniprot['description'].apply(extract_semantic_category)

        # Count semantic categories
        category_counts = df_uniprot['semantic_category'].value_counts()
        print("Semantic category distribution:")
        for category, count in category_counts.items():
            print(f"  {category}: {count}")

        # Prepare final dataset with required columns
        final_columns = [
            'id',                    # Original Kraken ID (e.g., NCBIGene:10752)
            'clean_uniprot_id',      # Clean UniProt ID (P12345)
            'name',                  # Protein name
            'category',              # Biolink category
            'description',           # Full description
            'semantic_category',     # Our extracted category
            'synonyms',              # Alternative names
            'xrefs',                 # Cross-references
            'uniprot_ids'            # All UniProt IDs found
        ]

        df_final = df_uniprot[final_columns].copy()

        # Statistics
        total_entries = len(df_final)
        unique_clean_ids = df_final['clean_uniprot_id'].nunique()

        print(f"\nFinal Data Summary:")
        print(f"  Total UniProt entries: {total_entries}")
        print(f"  Unique clean UniProt IDs: {unique_clean_ids}")
        print(f"  Semantic categories: {len(category_counts)}")

        # Sample of final data
        print(f"\nSample processed entries:")
        for i, (_, row) in enumerate(df_final.head(3).iterrows(), 1):
            print(f"  {i}. {row['clean_uniprot_id']} - {row['name'][:50]}...")
            print(f"     Category: {row['semantic_category']}")

        # Save processed data
        output_file = OUTPUT_DIR / "kraken_proteins_uniprot.tsv"
        df_final.to_csv(output_file, sep='\t', index=False)

        print(f"\nSaved {len(df_final)} processed Kraken proteins to: {output_file}")

        # Create summary file
        summary = {
            'total_kraken_entries': len(df),
            'uniprot_entries': total_entries,
            'unique_clean_ids': unique_clean_ids,
            'semantic_categories': category_counts.to_dict(),
            'columns': final_columns,
            'sample_clean_ids': df_final['clean_uniprot_id'].head(10).tolist()
        }

        summary_file = OUTPUT_DIR / "kraken_summary.json"
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Summary saved to: {summary_file}")
        print("\n✅ Script 2 completed successfully!")

    except Exception as e:
        print(f"❌ Error loading Kraken data: {e}")
        raise

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Load and prepare Kraken reference data (Optimized v2)
Processes each ontology (HMDB, ChEBI) separately then merges results
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Set

# Direct file paths
KRAKEN_CHEMICALS = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
KRAKEN_METABOLITES = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_metabolites.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def extract_hmdb_from_xrefs(xrefs_str):
    """Extract HMDB IDs from xrefs field."""
    if pd.isna(xrefs_str):
        return []

    hmdb_ids = []
    xrefs_str = str(xrefs_str)

    # Pattern for HMDB references
    hmdb_patterns = [
        r'HMDB:HMDB(\d+)',
        r'HMDB:(HMDB\d+)',
        r'hmdb:HMDB(\d+)',
        r'HMDB\s*:\s*(\d+)'
    ]

    for pattern in hmdb_patterns:
        matches = re.findall(pattern, xrefs_str, re.IGNORECASE)
        hmdb_ids.extend(matches)

    # Normalize to HMDB00000 format
    normalized = []
    for hmdb_id in hmdb_ids:
        if hmdb_id.startswith('HMDB'):
            hmdb_id = hmdb_id[4:]
        if hmdb_id.isdigit():
            normalized.append(f"HMDB{hmdb_id.zfill(7)}")

    return list(set(normalized))

def extract_chebi_from_id(node_id):
    """Extract ChEBI ID from Kraken node ID."""
    if pd.isna(node_id) or not str(node_id).startswith('CHEBI:'):
        return None
    return str(node_id)  # Keep full CHEBI:xxxxx format

def process_hmdb_subset(chunk_size=50000):
    """Process Kraken entries that have HMDB references in xrefs."""
    print("\n=== Processing HMDB mappings ===")
    hmdb_mappings = []
    total_processed = 0

    # Process in chunks
    for chunk_num, chunk in enumerate(pd.read_csv(KRAKEN_CHEMICALS, chunksize=chunk_size)):
        # Filter rows that contain HMDB in xrefs
        if 'xrefs' in chunk.columns:
            hmdb_mask = chunk['xrefs'].astype(str).str.contains('HMDB', case=False, na=False)
            hmdb_chunk = chunk[hmdb_mask]

            if not hmdb_chunk.empty:
                print(f"  Chunk {chunk_num+1}: Found {len(hmdb_chunk)} entries with HMDB references")

                for idx, row in hmdb_chunk.iterrows():
                    hmdb_ids = extract_hmdb_from_xrefs(row.get('xrefs'))
                    for hmdb_id in hmdb_ids:
                        hmdb_mappings.append({
                            'kraken_id': row['id'],
                            'kraken_name': row.get('name', ''),
                            'kraken_category': row.get('category', ''),
                            'mapping_type': 'hmdb',
                            'identifier': hmdb_id
                        })

        total_processed += len(chunk)
        if total_processed % 500000 == 0:
            print(f"  Processed {total_processed:,} total entries...")

    hmdb_df = pd.DataFrame(hmdb_mappings)
    print(f"  Total HMDB mappings found: {len(hmdb_df)}")

    # Remove duplicates
    if not hmdb_df.empty:
        hmdb_df = hmdb_df.drop_duplicates(subset=['identifier', 'kraken_id'])
        print(f"  After deduplication: {len(hmdb_df)} unique HMDB mappings")

    return hmdb_df

def process_chebi_subset(chunk_size=50000):
    """Process Kraken entries that have ChEBI as primary ID."""
    print("\n=== Processing ChEBI mappings ===")
    chebi_mappings = []
    total_processed = 0

    # Process in chunks
    for chunk_num, chunk in enumerate(pd.read_csv(KRAKEN_CHEMICALS, chunksize=chunk_size)):
        # Filter rows where ID starts with CHEBI:
        chebi_chunk = chunk[chunk['id'].str.startswith('CHEBI:', na=False)]

        if not chebi_chunk.empty:
            print(f"  Chunk {chunk_num+1}: Found {len(chebi_chunk)} ChEBI entries")

            for idx, row in chebi_chunk.iterrows():
                chebi_id = extract_chebi_from_id(row['id'])
                if chebi_id:
                    chebi_mappings.append({
                        'kraken_id': row['id'],
                        'kraken_name': row.get('name', ''),
                        'kraken_category': row.get('category', ''),
                        'mapping_type': 'chebi',
                        'identifier': chebi_id
                    })

        total_processed += len(chunk)
        if total_processed % 500000 == 0:
            print(f"  Processed {total_processed:,} total entries...")

    chebi_df = pd.DataFrame(chebi_mappings)
    print(f"  Total ChEBI mappings found: {len(chebi_df)}")

    return chebi_df

def process_metabolites_file():
    """Process the dedicated metabolites file if it exists."""
    print("\n=== Processing metabolites file ===")

    if not Path(KRAKEN_METABOLITES).exists():
        print(f"  Metabolites file not found: {KRAKEN_METABOLITES}")
        return pd.DataFrame()

    try:
        metabolites_df = pd.read_csv(KRAKEN_METABOLITES)
        print(f"  Loaded {len(metabolites_df)} entries from metabolites file")

        metabolite_mappings = []

        # Check for HMDB in xrefs
        if 'xrefs' in metabolites_df.columns:
            for idx, row in metabolites_df.iterrows():
                hmdb_ids = extract_hmdb_from_xrefs(row.get('xrefs'))
                for hmdb_id in hmdb_ids:
                    metabolite_mappings.append({
                        'kraken_id': row['id'],
                        'kraken_name': row.get('name', ''),
                        'kraken_category': row.get('category', 'metabolite'),
                        'mapping_type': 'hmdb',
                        'identifier': hmdb_id
                    })

        # Check for ChEBI IDs
        for idx, row in metabolites_df.iterrows():
            if str(row['id']).startswith('CHEBI:'):
                metabolite_mappings.append({
                    'kraken_id': row['id'],
                    'kraken_name': row.get('name', ''),
                    'kraken_category': row.get('category', 'metabolite'),
                    'mapping_type': 'chebi',
                    'identifier': row['id']
                })

        result_df = pd.DataFrame(metabolite_mappings)
        print(f"  Extracted {len(result_df)} mappings from metabolites file")
        return result_df

    except Exception as e:
        print(f"  Error processing metabolites file: {e}")
        return pd.DataFrame()

def main():
    print("="*60)
    print("Loading and preparing Kraken reference data (Optimized v2)")
    print("Processing each ontology separately then merging")
    print("="*60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process each ontology type separately
    print("\nStep 1: Processing HMDB mappings from chemicals file...")
    hmdb_df = process_hmdb_subset()

    print("\nStep 2: Processing ChEBI mappings from chemicals file...")
    chebi_df = process_chebi_subset()

    print("\nStep 3: Processing dedicated metabolites file...")
    metabolites_df = process_metabolites_file()

    # Merge all results
    print("\n=== Merging all mappings ===")
    all_mappings = pd.concat([hmdb_df, chebi_df, metabolites_df], ignore_index=True)

    if all_mappings.empty:
        print("WARNING: No mappings found!")
        # Create empty dataframes
        for mapping_type in ['hmdb', 'chebi', 'all']:
            pd.DataFrame().to_csv(OUTPUT_DIR / f"kraken_{mapping_type}_mappings.tsv", sep='\t', index=False)
        return

    # Remove duplicates
    all_mappings = all_mappings.drop_duplicates(subset=['identifier', 'kraken_id'])
    print(f"Total unique mappings after merge: {len(all_mappings)}")

    # Split by mapping type for separate files
    hmdb_mappings = all_mappings[all_mappings['mapping_type'] == 'hmdb']
    chebi_mappings = all_mappings[all_mappings['mapping_type'] == 'chebi']

    # Save the mapping files
    print("\n=== Saving mapping files ===")

    # Save HMDB mappings
    if not hmdb_mappings.empty:
        hmdb_file = OUTPUT_DIR / "kraken_hmdb_mappings.tsv"
        hmdb_mappings.to_csv(hmdb_file, sep='\t', index=False)
        print(f"  Saved {len(hmdb_mappings)} HMDB mappings to {hmdb_file}")

    # Save ChEBI mappings
    if not chebi_mappings.empty:
        chebi_file = OUTPUT_DIR / "kraken_chebi_mappings.tsv"
        chebi_mappings.to_csv(chebi_file, sep='\t', index=False)
        print(f"  Saved {len(chebi_mappings)} ChEBI mappings to {chebi_file}")

    # Save all mappings
    all_file = OUTPUT_DIR / "kraken_all_mappings.tsv"
    all_mappings.to_csv(all_file, sep='\t', index=False)
    print(f"  Saved {len(all_mappings)} total mappings to {all_file}")

    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"HMDB mappings: {len(hmdb_mappings)}")
    print(f"  Unique HMDB IDs: {hmdb_mappings['identifier'].nunique() if not hmdb_mappings.empty else 0}")
    print(f"  Unique Kraken nodes: {hmdb_mappings['kraken_id'].nunique() if not hmdb_mappings.empty else 0}")

    print(f"\nChEBI mappings: {len(chebi_mappings)}")
    print(f"  Unique ChEBI IDs: {chebi_mappings['identifier'].nunique() if not chebi_mappings.empty else 0}")
    print(f"  Unique Kraken nodes: {chebi_mappings['kraken_id'].nunique() if not chebi_mappings.empty else 0}")

    print(f"\nTotal unique Kraken nodes with mappings: {all_mappings['kraken_id'].nunique()}")

    print("\n✓ Step 2 completed successfully!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Load Kraken references using targeted approach
Only loads entries for HMDB IDs that exist in Arivale data
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re

# Direct file paths
ARIVALE_CLEAN = Path(__file__).parent / "data" / "arivale_metabolites_clean.tsv"
KRAKEN_CHEMICALS = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
KRAKEN_METABOLITES = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_metabolites.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def get_arivale_identifiers():
    """Get unique HMDB IDs from Arivale data."""
    print("Loading Arivale identifiers...")
    arivale_df = pd.read_csv(ARIVALE_CLEAN, sep='\t')

    # Get unique HMDB IDs
    hmdb_ids = set()
    for hmdb in arivale_df['hmdb_normalized'].dropna():
        if hmdb and str(hmdb) != 'nan':
            hmdb_ids.add(str(hmdb))

    print(f"  Found {len(hmdb_ids)} unique HMDB IDs in Arivale data")
    return hmdb_ids

def extract_hmdb_from_xrefs(xrefs_str):
    """Extract and normalize HMDB IDs from xrefs field."""
    if pd.isna(xrefs_str):
        return []

    hmdb_ids = []
    xrefs_str = str(xrefs_str)

    # Look for HMDB patterns
    matches = re.findall(r'HMDB:HMDB(\d+)', xrefs_str, re.IGNORECASE)
    for match in matches:
        hmdb_ids.append(f"HMDB{match.zfill(5)}")

    # Also look for simple HMDB followed by numbers
    matches = re.findall(r'HMDB:(\d+)', xrefs_str, re.IGNORECASE)
    for match in matches:
        if len(match) <= 5:  # Likely a valid HMDB number
            hmdb_ids.append(f"HMDB{match.zfill(5)}")

    return list(set(hmdb_ids))

def search_kraken_for_hmdb(target_hmdb_ids, chunk_size=50000):
    """Search Kraken chemicals for specific HMDB IDs only."""
    print(f"\nSearching Kraken for {len(target_hmdb_ids)} target HMDB IDs...")
    found_mappings = []
    total_processed = 0
    chunks_with_matches = 0

    # Process chemicals file in chunks
    for chunk_num, chunk in enumerate(pd.read_csv(KRAKEN_CHEMICALS, chunksize=chunk_size)):
        chunk_mappings = []

        # Only process if xrefs column exists
        if 'xrefs' in chunk.columns:
            for idx, row in chunk.iterrows():
                if pd.notna(row.get('xrefs')):
                    hmdb_ids = extract_hmdb_from_xrefs(row['xrefs'])

                    # Check if any extracted HMDB IDs match our targets
                    matching_ids = set(hmdb_ids) & target_hmdb_ids
                    for hmdb_id in matching_ids:
                        chunk_mappings.append({
                            'kraken_id': row['id'],
                            'kraken_name': row.get('name', ''),
                            'kraken_category': row.get('category', ''),
                            'mapping_type': 'hmdb',
                            'identifier': hmdb_id
                        })

        if chunk_mappings:
            chunks_with_matches += 1
            found_mappings.extend(chunk_mappings)
            print(f"  Chunk {chunk_num+1}: Found {len(chunk_mappings)} matches")

        total_processed += len(chunk)
        if total_processed % 500000 == 0:
            print(f"  Processed {total_processed:,} entries, found {len(found_mappings)} matches so far...")

    # Also check metabolites file if it exists
    if Path(KRAKEN_METABOLITES).exists():
        print(f"\nSearching metabolites file...")
        try:
            metabolites_df = pd.read_csv(KRAKEN_METABOLITES)
            if 'xrefs' in metabolites_df.columns:
                for idx, row in metabolites_df.iterrows():
                    if pd.notna(row.get('xrefs')):
                        hmdb_ids = extract_hmdb_from_xrefs(row['xrefs'])
                        matching_ids = set(hmdb_ids) & target_hmdb_ids
                        for hmdb_id in matching_ids:
                            found_mappings.append({
                                'kraken_id': row['id'],
                                'kraken_name': row.get('name', ''),
                                'kraken_category': row.get('category', 'metabolite'),
                                'mapping_type': 'hmdb',
                                'identifier': hmdb_id
                            })
            print(f"  Found {len(found_mappings)} total matches including metabolites file")
        except Exception as e:
            print(f"  Could not process metabolites file: {e}")

    return pd.DataFrame(found_mappings)

def search_kraken_for_chebi(chunk_size=50000):
    """Get ChEBI entries from Kraken (limited to reasonable number)."""
    print("\nExtracting ChEBI entries from Kraken...")
    chebi_mappings = []
    max_entries = 200000  # Limit to match what other projects used
    entries_processed = 0

    for chunk in pd.read_csv(KRAKEN_CHEMICALS, chunksize=chunk_size):
        # Filter for ChEBI primary IDs
        chebi_chunk = chunk[chunk['id'].str.startswith('CHEBI:', na=False)]

        for idx, row in chebi_chunk.iterrows():
            chebi_mappings.append({
                'kraken_id': row['id'],
                'kraken_name': row.get('name', ''),
                'kraken_category': row.get('category', ''),
                'mapping_type': 'chebi',
                'identifier': row['id']
            })

        entries_processed += len(chebi_chunk)
        if entries_processed >= max_entries:
            print(f"  Reached limit of {max_entries} ChEBI entries")
            break

    print(f"  Extracted {len(chebi_mappings)} ChEBI entries")
    return pd.DataFrame(chebi_mappings)

def main():
    print("="*60)
    print("Loading Kraken references - TARGETED APPROACH")
    print("Only loading entries needed for Arivale metabolites")
    print("="*60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # First, get the HMDB IDs we need from Arivale
    arivale_hmdb_ids = get_arivale_identifiers()

    # Search Kraken for just these HMDB IDs
    hmdb_df = search_kraken_for_hmdb(arivale_hmdb_ids)
    print(f"\nFound {len(hmdb_df)} HMDB mappings for Arivale metabolites")
    print(f"Covered {hmdb_df['identifier'].nunique()} unique HMDB IDs out of {len(arivale_hmdb_ids)} targets")

    # Also get ChEBI mappings (limited set)
    chebi_df = search_kraken_for_chebi()

    # Save the results
    print("\n=== Saving mapping files ===")

    # Save HMDB mappings
    if not hmdb_df.empty:
        hmdb_file = OUTPUT_DIR / "kraken_hmdb_mappings.tsv"
        hmdb_df.to_csv(hmdb_file, sep='\t', index=False)
        print(f"  Saved {len(hmdb_df)} HMDB mappings")

    # Save ChEBI mappings
    if not chebi_df.empty:
        chebi_file = OUTPUT_DIR / "kraken_chebi_mappings.tsv"
        chebi_df.to_csv(chebi_file, sep='\t', index=False)
        print(f"  Saved {len(chebi_df)} ChEBI mappings")

    # Save combined
    all_mappings = pd.concat([hmdb_df, chebi_df], ignore_index=True)
    if not all_mappings.empty:
        all_mappings = all_mappings.drop_duplicates(subset=['identifier', 'kraken_id'])
        all_file = OUTPUT_DIR / "kraken_all_mappings.tsv"
        all_mappings.to_csv(all_file, sep='\t', index=False)
        print(f"  Saved {len(all_mappings)} total mappings")

    # Print coverage summary
    print("\n=== Coverage Summary ===")
    if not hmdb_df.empty:
        coverage = (hmdb_df['identifier'].nunique() / len(arivale_hmdb_ids)) * 100
        print(f"HMDB coverage: {hmdb_df['identifier'].nunique()}/{len(arivale_hmdb_ids)} ({coverage:.1f}%)")

        # Show some examples of found mappings
        print("\nSample HMDB mappings found:")
        sample = hmdb_df[['identifier', 'kraken_name']].drop_duplicates('identifier').head(5)
        for _, row in sample.iterrows():
            print(f"  {row['identifier']}: {row['kraken_name'][:50]}...")

    print("\n✓ Step 2 completed!")

if __name__ == "__main__":
    main()
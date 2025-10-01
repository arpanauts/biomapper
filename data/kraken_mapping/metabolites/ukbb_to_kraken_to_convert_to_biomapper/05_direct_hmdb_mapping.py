#!/usr/bin/env python3
"""
Proto-action: Direct HMDB ID mapping for remaining Nightingale metabolites
This is a STANDALONE script, not a biomapper action
Now includes xref-aware searching to find HMDB IDs in cross-references
Searches in BOTH ChEBI and HMDB datasets since many HMDB IDs are in ChEBI xrefs
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

def search_hmdb_in_xrefs(xrefs_str, hmdb_id):
    """Check if an HMDB ID exists in the xrefs string"""
    if pd.isna(xrefs_str) or pd.isna(hmdb_id):
        return False

    # Clean the HMDB ID - handle float conversion issues
    hmdb_id = str(hmdb_id)
    if '.0' in hmdb_id:
        hmdb_id = hmdb_id.replace('.0', '')

    # Pad to 7 digits if needed
    if hmdb_id.isdigit():
        hmdb_id = hmdb_id.zfill(7)

    # Create patterns to search for - accounting for Kraken's format
    # Kraken uses "HMDB:HMDB0000161" format in xrefs
    patterns = [
        f"HMDB:HMDB{hmdb_id}",     # Standard Kraken format with double HMDB
        f"HMDB:{hmdb_id}",         # Alternative format with single prefix
        f"HMDB{hmdb_id}",          # Without colon
        f"hmdb:{hmdb_id}",         # Lowercase variation
        f"HMDB:HMDB00{hmdb_id[-5:]}",  # Handle 5-digit IDs (older format)
    ]

    xrefs_str = str(xrefs_str)
    for pattern in patterns:
        if pattern in xrefs_str:
            return True

    return False

def perform_xref_mapping(unmatched_with_hmdb, kraken_df, dataset_name):
    """Map Nightingale HMDB IDs to Kraken nodes via xrefs column"""

    if 'xrefs' not in kraken_df.columns:
        print(f"  WARNING: No xrefs column in {dataset_name} data")
        return pd.DataFrame()

    print(f"\n  Searching for Nightingale HMDB IDs in {dataset_name} xrefs...")

    matches = []

    # For each unmatched biomarker with HMDB ID
    for idx, nightingale_row in unmatched_with_hmdb.iterrows():
        hmdb_id = nightingale_row['hmdb_clean']

        if pd.isna(hmdb_id):
            continue

        # Search for this HMDB ID in Kraken xrefs
        for _, kraken_row in kraken_df.iterrows():
            if search_hmdb_in_xrefs(kraken_row.get('xrefs', ''), hmdb_id):
                # Found a match in xrefs!
                match = {
                    'Biomarker': nightingale_row['Biomarker'],
                    'hmdb_clean': hmdb_id,
                    'kraken_id': kraken_row['id'],
                    'kraken_name': kraken_row.get('name', ''),
                    'matched_in': f'xrefs_{dataset_name}',
                    'mapping_type': f'xref_hmdb_{dataset_name}',
                    'mapping_confidence': 0.93,  # Slightly lower than ChEBI xref
                    'mapping_stage': 2
                }

                # Copy all Nightingale columns
                for col in nightingale_row.index:
                    if col not in match:
                        match[f'{col}_nightingale'] = nightingale_row[col]

                # Copy all Kraken columns
                for col in kraken_row.index:
                    if col not in ['id', 'name']:
                        match[f'{col}_kraken'] = kraken_row[col]

                matches.append(match)
                break  # Found match, move to next Nightingale biomarker

    if matches:
        xref_matches_df = pd.DataFrame(matches)
        print(f"    Found {len(xref_matches_df)} matches via {dataset_name} xrefs")
        return xref_matches_df
    else:
        print(f"    No matches found via {dataset_name} xrefs")
        return pd.DataFrame()

def main():
    print("Performing HMDB ID mapping (direct + xref-aware) for remaining metabolites...")
    print("NOTE: Now searching HMDB IDs in BOTH HMDB and ChEBI datasets")

    # Load all unmatched records from ChEBI step
    unmatched_files = [
        INPUT_DIR / "chebi_unmatched.tsv",
        INPUT_DIR / "no_chebi_ids.tsv"
    ]

    unmatched_dfs = []
    total_unmatched = 0

    for file in unmatched_files:
        if file.exists():
            df = pd.read_csv(file, sep='\t')
            unmatched_dfs.append(df)
            total_unmatched += len(df)
            print(f"  Loaded {len(df)} unmatched records from {file.name}")

    if not unmatched_dfs:
        print("ERROR: No unmatched files found. Run script 04_direct_chebi_mapping.py first")
        return

    # Combine all unmatched records
    all_unmatched_df = pd.concat(unmatched_dfs, ignore_index=True)
    print(f"Total unmatched biomarkers for HMDB mapping: {len(all_unmatched_df)}")

    # Load BOTH Kraken HMDB and ChEBI data (since HMDB IDs can be in ChEBI xrefs)
    datasets = {}

    # Load Kraken HMDB data
    kraken_hmdb_file = INPUT_DIR / "kraken_hmdb_cleaned.tsv"
    print(f"\nLoading cleaned Kraken HMDB data from {kraken_hmdb_file}")

    try:
        kraken_hmdb_df = pd.read_csv(kraken_hmdb_file, sep='\t')
        datasets['hmdb'] = kraken_hmdb_df
        print(f"  Loaded {len(kraken_hmdb_df)} Kraken HMDB nodes")
        print(f"  Columns: {list(kraken_hmdb_df.columns)}")

        if 'xrefs' in kraken_hmdb_df.columns:
            xrefs_count = kraken_hmdb_df['xrefs'].notna().sum()
            print(f"  Nodes with xrefs: {xrefs_count}/{len(kraken_hmdb_df)}")

    except FileNotFoundError:
        print(f"  WARNING: Could not find {kraken_hmdb_file}")
        datasets['hmdb'] = pd.DataFrame()

    # Load Kraken ChEBI data (many metabolites have HMDB IDs in ChEBI xrefs!)
    kraken_chebi_file = INPUT_DIR / "kraken_chebi_cleaned.tsv"
    print(f"\nLoading cleaned Kraken ChEBI data from {kraken_chebi_file}")

    try:
        kraken_chebi_df = pd.read_csv(kraken_chebi_file, sep='\t')
        datasets['chebi'] = kraken_chebi_df
        print(f"  Loaded {len(kraken_chebi_df)} Kraken ChEBI nodes")

        if 'xrefs' in kraken_chebi_df.columns:
            # Check how many ChEBI nodes have HMDB IDs in xrefs
            hmdb_in_xrefs = kraken_chebi_df['xrefs'].str.contains('HMDB:', na=False).sum()
            print(f"  ChEBI nodes with HMDB in xrefs: {hmdb_in_xrefs}")

    except FileNotFoundError:
        print(f"  WARNING: Could not find {kraken_chebi_file}")
        datasets['chebi'] = pd.DataFrame()

    # Filter records with HMDB IDs
    unmatched_with_hmdb = all_unmatched_df[all_unmatched_df['hmdb_clean'].notna()].copy()
    print(f"\nUnmatched biomarkers with HMDB IDs: {len(unmatched_with_hmdb)}")

    if len(unmatched_with_hmdb) == 0:
        print("No unmatched biomarkers have HMDB IDs. Skipping HMDB mapping.")

        # Save all unmatched as final unmatched
        final_unmatched_file = OUTPUT_DIR / "final_unmatched.tsv"
        all_unmatched_df.to_csv(final_unmatched_file, sep='\t', index=False)
        print(f"Saved {len(all_unmatched_df)} final unmatched records to {final_unmatched_file}")
        return

    # Ensure HMDB IDs are strings for consistent processing
    unmatched_with_hmdb['hmdb_clean'] = unmatched_with_hmdb['hmdb_clean'].astype(str)

    # Show sample IDs before mapping
    print("\nSample HMDB IDs to match:")
    sample_nightingale = unmatched_with_hmdb['hmdb_clean'].head(5).tolist()
    print(f"  Nightingale: {sample_nightingale}")

    all_matches = []

    # STEP 1: Try direct matching with HMDB dataset (if we have clean HMDB IDs on both sides)
    if 'hmdb' in datasets and len(datasets['hmdb']) > 0:
        kraken_hmdb_df = datasets['hmdb']

        # Filter Kraken records with clean HMDB IDs
        kraken_with_hmdb = kraken_hmdb_df[kraken_hmdb_df['hmdb_clean'].notna()].copy()
        print(f"\nKraken HMDB nodes with HMDB IDs: {len(kraken_with_hmdb)}")

        if len(kraken_with_hmdb) > 0:
            kraken_with_hmdb['hmdb_clean'] = kraken_with_hmdb['hmdb_clean'].astype(str)

            print(f"\nSTEP 1: Performing direct HMDB ID join...")
            mapped = unmatched_with_hmdb.merge(
                kraken_with_hmdb,
                left_on='hmdb_clean',
                right_on='hmdb_clean',
                how='left',
                suffixes=('_nightingale', '_kraken')
            )

            # Identify successful direct matches
            kraken_id_col = 'id_kraken' if 'id_kraken' in mapped.columns else 'id'
            if kraken_id_col not in mapped.columns:
                id_cols = [col for col in mapped.columns if 'id' in col.lower()]
                if id_cols:
                    kraken_id_col = id_cols[0]

            successful_direct_matches = mapped[mapped[kraken_id_col].notna()].copy()
            print(f"  Successful direct HMDB matches: {len(successful_direct_matches)}")

            if len(successful_direct_matches) > 0:
                # Add mapping metadata
                successful_direct_matches['mapping_type'] = 'direct_hmdb'
                successful_direct_matches['mapping_confidence'] = 0.95
                successful_direct_matches['mapping_stage'] = 2
                successful_direct_matches['matched_in'] = 'primary_id'

                # Rename Kraken ID column to standard name
                if kraken_id_col != 'kraken_id':
                    successful_direct_matches['kraken_id'] = successful_direct_matches[kraken_id_col]

                all_matches.append(successful_direct_matches)

                # Update unmatched list
                unmatched_with_hmdb = unmatched_with_hmdb[
                    ~unmatched_with_hmdb['Biomarker'].isin(successful_direct_matches['Biomarker'])
                ].copy()

    # STEP 2: XREF MAPPING in both HMDB and ChEBI datasets
    print(f"\nSTEP 2: Searching xrefs for {len(unmatched_with_hmdb)} remaining biomarkers...")

    # Search in HMDB xrefs
    if 'hmdb' in datasets and len(datasets['hmdb']) > 0:
        xref_matches = perform_xref_mapping(unmatched_with_hmdb, datasets['hmdb'], 'hmdb')
        if len(xref_matches) > 0:
            all_matches.append(xref_matches)
            # Update unmatched list
            unmatched_with_hmdb = unmatched_with_hmdb[
                ~unmatched_with_hmdb['Biomarker'].isin(xref_matches['Biomarker'])
            ].copy()

    # Search in ChEBI xrefs (many metabolites have HMDB IDs here!)
    if 'chebi' in datasets and len(datasets['chebi']) > 0 and len(unmatched_with_hmdb) > 0:
        xref_matches = perform_xref_mapping(unmatched_with_hmdb, datasets['chebi'], 'chebi')
        if len(xref_matches) > 0:
            all_matches.append(xref_matches)

    # Combine all successful matches
    if all_matches:
        successful_matches = pd.concat(all_matches, ignore_index=True)
        print(f"\nTotal successful HMDB matches: {len(successful_matches)}")

        # Show breakdown by match type
        print("\nMatch type breakdown:")
        if 'matched_in' in successful_matches.columns:
            print(successful_matches['matched_in'].value_counts())

        # Show sample successful matches
        print(f"\nSample successful HMDB mappings:")
        for i, row in successful_matches.head(5).iterrows():
            biomarker = row['Biomarker']
            kraken_name = row.get('kraken_name', 'N/A')
            kraken_id = row.get('kraken_id', 'N/A')
            hmdb_id = row['hmdb_clean']
            matched_in = row.get('matched_in', 'N/A')
            print(f"  {biomarker} → {kraken_name} ({kraken_id}) via {matched_in} [HMDB{hmdb_id}]")

        # Save successful HMDB matches
        hmdb_matches_file = OUTPUT_DIR / "hmdb_direct_matches.tsv"
        successful_matches.to_csv(hmdb_matches_file, sep='\t', index=False)
        print(f"\nSaved {len(successful_matches)} HMDB matches to {hmdb_matches_file}")
    else:
        successful_matches = pd.DataFrame()
        print("\nNo HMDB matches found")

    # Identify final unmatched records
    all_successful_biomarkers = set()
    if len(successful_matches) > 0:
        all_successful_biomarkers.update(successful_matches['Biomarker'])

    final_unmatched = all_unmatched_df[~all_unmatched_df['Biomarker'].isin(all_successful_biomarkers)].copy()
    print(f"\nFinal unmatched: {len(final_unmatched)} biomarkers")

    if len(final_unmatched) > 0:
        # Save final unmatched records
        final_unmatched_file = OUTPUT_DIR / "final_unmatched.tsv"
        final_unmatched.to_csv(final_unmatched_file, sep='\t', index=False)
        print(f"Saved {len(final_unmatched)} final unmatched records to {final_unmatched_file}")

        # Show sample final unmatched
        print(f"\nSample final unmatched biomarkers:")
        sample_unmatched = final_unmatched[['Biomarker', 'metabolite_classification']].head(10)
        for idx, row in sample_unmatched.iterrows():
            print(f"  {row['Biomarker']} ({row['metabolite_classification']})")

    # Calculate cumulative match rates
    total_hmdb_mapped = len(successful_matches) if len(successful_matches) > 0 else 0
    total_unmatched_with_hmdb = len(all_unmatched_df[all_unmatched_df['hmdb_clean'].notna()])

    print(f"\nHMDB MAPPING SUMMARY:")
    print(f"  - Unmatched biomarkers processed: {len(all_unmatched_df)}")
    print(f"  - Had HMDB IDs: {total_unmatched_with_hmdb}")
    print(f"  - Successfully mapped to Kraken: {total_hmdb_mapped}")

    # Show breakdown by match type
    if total_hmdb_mapped > 0:
        if 'matched_in' in successful_matches.columns:
            for match_type, count in successful_matches['matched_in'].value_counts().items():
                print(f"    - {match_type}: {count}")

    if total_unmatched_with_hmdb > 0:
        hmdb_match_rate = (total_hmdb_mapped / total_unmatched_with_hmdb) * 100
        print(f"  - HMDB match rate: {hmdb_match_rate:.1f}%")
    print(f"  - Final unmatched: {len(final_unmatched)}")

if __name__ == "__main__":
    main()
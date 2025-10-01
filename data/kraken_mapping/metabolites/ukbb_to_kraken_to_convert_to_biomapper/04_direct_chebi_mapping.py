#!/usr/bin/env python3
"""
Proto-action: Direct ChEBI ID mapping between Nightingale and Kraken
This is a STANDALONE script, not a biomapper action
Now includes xref-aware searching to find ChEBI IDs in cross-references
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

def search_chebi_in_xrefs(xrefs_str, chebi_id):
    """Check if a ChEBI ID exists in the xrefs string"""
    if pd.isna(xrefs_str) or pd.isna(chebi_id):
        return False

    # Create patterns to search for - with and without CHEBI: prefix
    patterns = [
        f"CHEBI:{chebi_id}",  # Standard format
        f"ChEBI:{chebi_id}",  # Case variation
        f"chebi:{chebi_id}",  # Lowercase variation
    ]

    xrefs_str = str(xrefs_str)
    for pattern in patterns:
        if pattern in xrefs_str:
            return True

    return False

def perform_xref_mapping(nightingale_with_chebi, kraken_chebi_df):
    """Map Nightingale ChEBI IDs to Kraken nodes via xrefs column"""

    if 'xrefs' not in kraken_chebi_df.columns:
        print("  WARNING: No xrefs column in Kraken data")
        return pd.DataFrame()

    print("\nSearching for Nightingale ChEBI IDs in Kraken xrefs...")

    matches = []

    # For each Nightingale biomarker with ChEBI ID
    for idx, nightingale_row in nightingale_with_chebi.iterrows():
        chebi_id = nightingale_row['chebi_clean']

        if pd.isna(chebi_id):
            continue

        # Search for this ChEBI ID in Kraken xrefs
        for _, kraken_row in kraken_chebi_df.iterrows():
            if search_chebi_in_xrefs(kraken_row.get('xrefs', ''), chebi_id):
                # Found a match in xrefs!
                match = {
                    'Biomarker': nightingale_row['Biomarker'],
                    'chebi_clean': chebi_id,
                    'kraken_id': kraken_row['id'],
                    'kraken_name': kraken_row.get('name', ''),
                    'matched_in': 'xrefs',
                    'mapping_type': 'xref_chebi',
                    'mapping_confidence': 0.95,  # Slightly lower than direct match
                    'mapping_stage': 1
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
        print(f"  Found {len(xref_matches_df)} matches via xrefs")
        return xref_matches_df
    else:
        print("  No matches found via xrefs")
        return pd.DataFrame()

def main():
    print("Performing ChEBI ID mapping (direct + xref-aware)...")

    # Load cleaned Nightingale data
    nightingale_file = INPUT_DIR / "nightingale_cleaned.tsv"
    print(f"Loading cleaned Nightingale data from {nightingale_file}")

    try:
        nightingale_df = pd.read_csv(nightingale_file, sep='\t')
        print(f"  Loaded {len(nightingale_df)} Nightingale biomarkers")
    except FileNotFoundError:
        print(f"ERROR: Could not find {nightingale_file}")
        print("Run script 03_clean_identifiers.py first")
        return

    # Load cleaned Kraken ChEBI data (now with xrefs)
    kraken_chebi_file = INPUT_DIR / "kraken_chebi_cleaned.tsv"
    print(f"Loading cleaned Kraken ChEBI data from {kraken_chebi_file}")

    try:
        kraken_chebi_df = pd.read_csv(kraken_chebi_file, sep='\t')
        print(f"  Loaded {len(kraken_chebi_df)} Kraken ChEBI nodes")
        print(f"  Columns: {list(kraken_chebi_df.columns)}")

        # Check if xrefs column exists
        if 'xrefs' in kraken_chebi_df.columns:
            xrefs_count = kraken_chebi_df['xrefs'].notna().sum()
            print(f"  Nodes with xrefs: {xrefs_count}/{len(kraken_chebi_df)}")

    except FileNotFoundError:
        print(f"ERROR: Could not find {kraken_chebi_file}")
        print("Run script 02_load_kraken_references.py and 03_clean_identifiers.py first")
        return

    # Filter Nightingale records with ChEBI IDs
    nightingale_with_chebi = nightingale_df[nightingale_df['chebi_clean'].notna()].copy()
    print(f"\nNightingale biomarkers with ChEBI IDs: {len(nightingale_with_chebi)}")

    # Filter Kraken records with clean ChEBI IDs
    kraken_with_chebi = kraken_chebi_df[kraken_chebi_df['chebi_clean'].notna()].copy()
    print(f"Kraken nodes with ChEBI IDs: {len(kraken_with_chebi)}")

    if len(nightingale_with_chebi) == 0:
        print("ERROR: No Nightingale biomarkers have ChEBI IDs!")
        return

    if len(kraken_with_chebi) == 0:
        print("ERROR: No Kraken nodes have ChEBI IDs!")
        return

    # Ensure ChEBI IDs are strings for consistent joining
    nightingale_with_chebi['chebi_clean'] = nightingale_with_chebi['chebi_clean'].apply(
        lambda x: str(int(float(x))) if pd.notna(x) and str(x) not in ['nan', '<NA>'] else np.nan
    )
    kraken_with_chebi['chebi_clean'] = kraken_with_chebi['chebi_clean'].astype(str)

    # Show sample IDs before mapping
    print("\nSample ChEBI IDs to match:")
    sample_nightingale = nightingale_with_chebi['chebi_clean'].head(5).tolist()
    sample_kraken = kraken_with_chebi['chebi_clean'].head(5).tolist()
    print(f"  Nightingale: {sample_nightingale}")
    print(f"  Kraken primary IDs: {sample_kraken}")

    # STEP 1: DIRECT JOIN on primary IDs
    print(f"\nSTEP 1: Performing direct ChEBI ID join...")
    mapped = nightingale_with_chebi.merge(
        kraken_with_chebi,
        left_on='chebi_clean',
        right_on='chebi_clean',
        how='left',
        suffixes=('_nightingale', '_kraken')
    )

    # Identify successful direct matches
    kraken_id_col = 'id_kraken' if 'id_kraken' in mapped.columns else 'id'
    if kraken_id_col not in mapped.columns:
        print(f"  Available columns after merge: {list(mapped.columns)}")
        id_cols = [col for col in mapped.columns if 'id' in col.lower()]
        print(f"  Columns with 'id': {id_cols}")
        if id_cols:
            kraken_id_col = id_cols[0]
        else:
            print("  ERROR: No ID columns found after merge!")
            return

    successful_direct_matches = mapped[mapped[kraken_id_col].notna()].copy()
    print(f"  Successful direct ChEBI matches: {len(successful_direct_matches)}")

    if len(successful_direct_matches) > 0:
        # Add mapping metadata
        successful_direct_matches['mapping_type'] = 'direct_chebi'
        successful_direct_matches['mapping_confidence'] = 1.0
        successful_direct_matches['mapping_stage'] = 1
        successful_direct_matches['matched_in'] = 'primary_id'

        # Rename Kraken ID column to standard name
        if kraken_id_col != 'kraken_id':
            successful_direct_matches['kraken_id'] = successful_direct_matches[kraken_id_col]

        # Show sample successful matches
        print(f"\nSample successful direct ChEBI mappings:")
        name_col = 'name_kraken' if 'name_kraken' in successful_direct_matches.columns else 'name'
        for i, row in successful_direct_matches.head(5).iterrows():
            biomarker = row['Biomarker']
            kraken_name = row.get(name_col, 'N/A')
            chebi_id = row['chebi_clean']
            print(f"  {biomarker} → {kraken_name} (ChEBI:{chebi_id})")

    # STEP 2: XREF MAPPING for unmatched records
    unmatched_after_direct = nightingale_with_chebi[
        ~nightingale_with_chebi['Biomarker'].isin(successful_direct_matches['Biomarker'] if len(successful_direct_matches) > 0 else [])
    ].copy()

    print(f"\nSTEP 2: Searching xrefs for {len(unmatched_after_direct)} unmatched biomarkers...")

    xref_matches = perform_xref_mapping(unmatched_after_direct, kraken_chebi_df)

    # Combine all successful matches
    all_matches = []
    if len(successful_direct_matches) > 0:
        all_matches.append(successful_direct_matches)
    if len(xref_matches) > 0:
        all_matches.append(xref_matches)

    if all_matches:
        successful_matches = pd.concat(all_matches, ignore_index=True)
        print(f"\nTotal successful ChEBI matches: {len(successful_matches)}")

        # Show breakdown by match type
        print("\nMatch type breakdown:")
        if 'matched_in' in successful_matches.columns:
            print(successful_matches['matched_in'].value_counts())

        # Save successful ChEBI matches
        chebi_matches_file = OUTPUT_DIR / "chebi_direct_matches.tsv"
        successful_matches.to_csv(chebi_matches_file, sep='\t', index=False)
        print(f"\nSaved {len(successful_matches)} ChEBI matches to {chebi_matches_file}")
    else:
        successful_matches = pd.DataFrame()
        print("\nNo ChEBI matches found")

    # Identify final unmatched records
    unmatched = nightingale_with_chebi[
        ~nightingale_with_chebi['Biomarker'].isin(successful_matches['Biomarker'] if len(successful_matches) > 0 else [])
    ].copy()
    print(f"\nChEBI unmatched: {len(unmatched)} biomarkers")

    if len(unmatched) > 0:
        # Save unmatched ChEBI records
        chebi_unmatched_file = OUTPUT_DIR / "chebi_unmatched.tsv"
        unmatched.to_csv(chebi_unmatched_file, sep='\t', index=False)
        print(f"Saved {len(unmatched)} unmatched records to {chebi_unmatched_file}")

        # Show sample unmatched ChEBI IDs (for debugging)
        print(f"\nSample unmatched ChEBI IDs:")
        sample_unmatched = unmatched[['Biomarker', 'chebi_clean']].head(10)
        for idx, row in sample_unmatched.iterrows():
            print(f"  {row['Biomarker']}: ChEBI:{row['chebi_clean']}")

    # Also save records with no ChEBI IDs for next steps
    nightingale_no_chebi = nightingale_df[nightingale_df['chebi_clean'].isna()].copy()
    print(f"\nBiomarkers without ChEBI IDs: {len(nightingale_no_chebi)}")

    if len(nightingale_no_chebi) > 0:
        no_chebi_file = OUTPUT_DIR / "no_chebi_ids.tsv"
        nightingale_no_chebi.to_csv(no_chebi_file, sep='\t', index=False)
        print(f"Saved {len(nightingale_no_chebi)} records with no ChEBI to {no_chebi_file}")

    # Calculate match rate
    total_nightingale = len(nightingale_df)
    total_mapped = len(successful_matches) if len(successful_matches) > 0 else 0
    match_rate = (total_mapped / total_nightingale) * 100

    print(f"\nCHEBI MAPPING SUMMARY:")
    print(f"  - Total Nightingale biomarkers: {total_nightingale}")
    print(f"  - Had ChEBI IDs: {len(nightingale_with_chebi)}")
    print(f"  - Successfully mapped to Kraken: {total_mapped}")

    # Show breakdown by match type
    if total_mapped > 0:
        direct_count = len(successful_matches[successful_matches['matched_in'] == 'primary_id']) if 'matched_in' in successful_matches.columns else 0
        xref_count = len(successful_matches[successful_matches['matched_in'] == 'xrefs']) if 'matched_in' in successful_matches.columns else 0
        print(f"    - Direct ID matches: {direct_count}")
        print(f"    - Xref matches: {xref_count}")

    print(f"  - ChEBI match rate: {match_rate:.1f}%")
    print(f"  - Remaining for other mapping methods: {total_nightingale - total_mapped}")

if __name__ == "__main__":
    main()
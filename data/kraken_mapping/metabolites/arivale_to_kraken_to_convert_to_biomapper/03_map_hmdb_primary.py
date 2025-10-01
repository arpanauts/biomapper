#!/usr/bin/env python3
"""
Proto-action: Primary HMDB-based mapping between Arivale and Kraken
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    """Perform primary HMDB-based mapping."""
    print("Starting primary HMDB-based mapping...")

    # Load cleaned Arivale data
    arivale_file = INPUT_DIR / "arivale_metabolites_clean.tsv"
    print(f"Loading Arivale data from: {arivale_file}")
    arivale_df = pd.read_csv(arivale_file, sep='\t')
    print(f"Loaded {len(arivale_df)} Arivale metabolites")

    # Load Kraken HMDB mappings (using production version with 7-digit fix)
    kraken_hmdb_file = INPUT_DIR / "kraken_hmdb_mappings_production.tsv"
    print(f"Loading Kraken HMDB mappings from: {kraken_hmdb_file}")

    if not kraken_hmdb_file.exists():
        print(f"Error: Kraken HMDB mappings file not found: {kraken_hmdb_file}")
        print("Please run 02_load_kraken_references.py first")
        return

    kraken_hmdb_df = pd.read_csv(kraken_hmdb_file, sep='\t')
    print(f"Loaded {len(kraken_hmdb_df)} Kraken HMDB mappings")

    # Filter Arivale data to only those with HMDB IDs
    arivale_with_hmdb = arivale_df[arivale_df['hmdb_normalized'].notna()].copy()
    print(f"Arivale metabolites with HMDB IDs: {len(arivale_with_hmdb)}")

    if len(arivale_with_hmdb) == 0:
        print("No Arivale metabolites have HMDB IDs for mapping!")
        return

    # Perform direct HMDB ID matching
    print("Performing HMDB ID mapping...")
    mapped_hmdb = arivale_with_hmdb.merge(
        kraken_hmdb_df,
        left_on='hmdb_normalized',
        right_on='identifier',
        how='left'
    )

    # Count successful mappings
    successful_mappings = mapped_hmdb[mapped_hmdb['kraken_id'].notna()]
    total_attempts = len(arivale_with_hmdb)
    successful_count = len(successful_mappings)

    print(f"\nHMDB Mapping Results:")
    print(f"Attempted mappings: {total_attempts}")
    print(f"Successful mappings: {successful_count}")
    print(f"Success rate: {100*successful_count/total_attempts:.1f}%")

    # Prepare final output with standardized columns
    if successful_count > 0:
        hmdb_results = successful_mappings.copy()

        # Standardize output columns
        hmdb_results['arivale_metabolite_id'] = hmdb_results['arivale_metabolite_id']
        hmdb_results['arivale_name'] = hmdb_results['metabolite_name']
        hmdb_results['arivale_super_pathway'] = hmdb_results['super_pathway']
        hmdb_results['arivale_sub_pathway'] = hmdb_results['sub_pathway']
        hmdb_results['mapping_source'] = 'hmdb'
        hmdb_results['mapping_confidence'] = 1.0  # Direct ID match = highest confidence
        hmdb_results['matched_identifier'] = hmdb_results['hmdb_normalized']

        # Keep relevant columns
        output_columns = [
            'arivale_metabolite_id',
            'arivale_name',
            'arivale_super_pathway',
            'arivale_sub_pathway',
            'matched_identifier',
            'kraken_id',
            'kraken_name',
            'kraken_category',
            'entity_type',
            'mapping_source',
            'mapping_confidence'
        ]

        hmdb_final = hmdb_results[output_columns].copy()

        # Save results
        output_file = OUTPUT_DIR / "hmdb_mapped_results.tsv"
        hmdb_final.to_csv(output_file, sep='\t', index=False)
        print(f"Saved HMDB mapping results to: {output_file}")

        # Show sample results
        print(f"\nSample HMDB mappings:")
        print(hmdb_final.head(3).to_string())

        # Save unmatched for next stage
        unmatched_hmdb = arivale_with_hmdb[
            ~arivale_with_hmdb['arivale_metabolite_id'].isin(
                successful_mappings['arivale_metabolite_id']
            )
        ].copy()

        if len(unmatched_hmdb) > 0:
            unmatched_file = OUTPUT_DIR / "hmdb_unmatched.tsv"
            unmatched_hmdb.to_csv(unmatched_file, sep='\t', index=False)
            print(f"Saved {len(unmatched_hmdb)} unmatched HMDB records to: {unmatched_file}")

    else:
        print("No successful HMDB mappings found!")

    # Also save metabolites without HMDB IDs for PubChem mapping
    arivale_without_hmdb = arivale_df[arivale_df['hmdb_normalized'].isna()].copy()
    if len(arivale_without_hmdb) > 0:
        no_hmdb_file = OUTPUT_DIR / "no_hmdb_for_pubchem.tsv"
        arivale_without_hmdb.to_csv(no_hmdb_file, sep='\t', index=False)
        print(f"Saved {len(arivale_without_hmdb)} metabolites without HMDB IDs for PubChem mapping")

    print(f"\nPrimary HMDB mapping completed!")

if __name__ == "__main__":
    main()
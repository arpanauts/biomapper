#!/usr/bin/env python3
"""
Proto-action: Secondary PubChem-based mapping for unmatched metabolites
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    """Perform secondary PubChem-based mapping for unmatched metabolites."""
    print("Starting secondary PubChem-based mapping...")

    # Load Kraken PubChem mappings
    kraken_pubchem_file = INPUT_DIR / "kraken_pubchem_mappings.tsv"
    print(f"Loading Kraken PubChem mappings from: {kraken_pubchem_file}")

    if not kraken_pubchem_file.exists():
        print(f"Error: Kraken PubChem mappings file not found: {kraken_pubchem_file}")
        print("Please run 02_load_kraken_references.py first")
        return

    kraken_pubchem_df = pd.read_csv(kraken_pubchem_file, sep='\t')
    print(f"Loaded {len(kraken_pubchem_df)} Kraken PubChem mappings")

    # Load unmatched from HMDB stage
    unmatched_files = [
        INPUT_DIR / "hmdb_unmatched.tsv",
        INPUT_DIR / "no_hmdb_for_pubchem.tsv"
    ]

    unmatched_dfs = []
    for file in unmatched_files:
        if file.exists():
            df = pd.read_csv(file, sep='\t')
            unmatched_dfs.append(df)
            print(f"Loaded {len(df)} unmatched metabolites from: {file.name}")

    if not unmatched_dfs:
        print("No unmatched metabolites found for PubChem mapping!")
        return

    # Combine all unmatched data
    unmatched_df = pd.concat(unmatched_dfs, ignore_index=True)
    print(f"Total unmatched metabolites for PubChem mapping: {len(unmatched_df)}")

    # Filter to only those with PubChem IDs
    unmatched_with_pubchem = unmatched_df[unmatched_df['pubchem_normalized'].notna()].copy()
    print(f"Unmatched metabolites with PubChem IDs: {len(unmatched_with_pubchem)}")

    if len(unmatched_with_pubchem) == 0:
        print("No unmatched metabolites have PubChem IDs for mapping!")
        # Still save the unmatched for final combining
        final_unmatched = unmatched_df[unmatched_df['pubchem_normalized'].isna()].copy()
        if len(final_unmatched) > 0:
            unmatched_file = OUTPUT_DIR / "final_unmatched.tsv"
            final_unmatched.to_csv(unmatched_file, sep='\t', index=False)
            print(f"Saved {len(final_unmatched)} finally unmatched metabolites to: {unmatched_file}")
        return

    # Perform direct PubChem ID matching
    print("Performing PubChem ID mapping...")
    mapped_pubchem = unmatched_with_pubchem.merge(
        kraken_pubchem_df,
        left_on='pubchem_normalized',
        right_on='identifier',
        how='left'
    )

    # Count successful mappings
    successful_mappings = mapped_pubchem[mapped_pubchem['kraken_id'].notna()]
    total_attempts = len(unmatched_with_pubchem)
    successful_count = len(successful_mappings)

    print(f"\nPubChem Mapping Results:")
    print(f"Attempted mappings: {total_attempts}")
    print(f"Successful mappings: {successful_count}")
    print(f"Success rate: {100*successful_count/total_attempts:.1f}%")

    # Prepare final output with standardized columns
    if successful_count > 0:
        pubchem_results = successful_mappings.copy()

        # Standardize output columns
        pubchem_results['arivale_metabolite_id'] = pubchem_results['arivale_metabolite_id']
        pubchem_results['arivale_name'] = pubchem_results['metabolite_name']
        pubchem_results['arivale_super_pathway'] = pubchem_results['super_pathway']
        pubchem_results['arivale_sub_pathway'] = pubchem_results['sub_pathway']
        pubchem_results['mapping_source'] = 'pubchem'
        pubchem_results['mapping_confidence'] = 0.9  # Slightly lower than HMDB
        pubchem_results['matched_identifier'] = pubchem_results['pubchem_normalized']

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

        pubchem_final = pubchem_results[output_columns].copy()

        # Save results
        output_file = OUTPUT_DIR / "pubchem_mapped_results.tsv"
        pubchem_final.to_csv(output_file, sep='\t', index=False)
        print(f"Saved PubChem mapping results to: {output_file}")

        # Show sample results
        print(f"\nSample PubChem mappings:")
        print(pubchem_final.head(3).to_string())

    else:
        print("No successful PubChem mappings found!")

    # Combine all remaining unmatched metabolites
    all_unmatched = []

    # Add PubChem unmatched
    if successful_count > 0:
        unmatched_pubchem = unmatched_with_pubchem[
            ~unmatched_with_pubchem['arivale_metabolite_id'].isin(
                successful_mappings['arivale_metabolite_id']
            )
        ].copy()
        if len(unmatched_pubchem) > 0:
            all_unmatched.append(unmatched_pubchem)
    else:
        all_unmatched.append(unmatched_with_pubchem)

    # Add metabolites without PubChem IDs
    no_pubchem = unmatched_df[unmatched_df['pubchem_normalized'].isna()].copy()
    if len(no_pubchem) > 0:
        all_unmatched.append(no_pubchem)

    # Save final unmatched
    if all_unmatched:
        final_unmatched_df = pd.concat(all_unmatched, ignore_index=True)
        unmatched_file = OUTPUT_DIR / "final_unmatched.tsv"
        final_unmatched_df.to_csv(unmatched_file, sep='\t', index=False)
        print(f"Saved {len(final_unmatched_df)} finally unmatched metabolites to: {unmatched_file}")

    print(f"\nSecondary PubChem mapping completed!")

if __name__ == "__main__":
    main()
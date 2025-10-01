#!/usr/bin/env python3
"""
Proto-Strategy Script 3: Direct UniProt mapping between Arivale and Kraken
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Input/Output paths
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

def main():
    print("=" * 60)
    print("SCRIPT 3: Direct UniProt mapping (Arivale → Kraken)")
    print("=" * 60)

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Load processed data from previous scripts
    print("Loading processed data...")

    try:
        # Load Arivale normalized proteins
        arivale_file = DATA_DIR / "arivale_proteins_normalized.tsv"
        arivale_df = pd.read_csv(arivale_file, sep='\t')
        print(f"Loaded {len(arivale_df)} Arivale proteins")

        # Load Kraken UniProt proteins
        kraken_file = DATA_DIR / "kraken_proteins_uniprot.tsv"
        kraken_df = pd.read_csv(kraken_file, sep='\t')
        print(f"Loaded {len(kraken_df)} Kraken UniProt proteins")

        print("\nData overview:")
        print(f"  Arivale unique UniProt IDs: {arivale_df['uniprot_normalized'].nunique()}")
        print(f"  Kraken unique UniProt IDs: {kraken_df['clean_uniprot_id'].nunique()}")

        # DIRECT MAPPING with composite ID handling
        print("\nPerforming direct UniProt ID mapping...")
        print("Mapping strategy: Handle composite IDs by checking ANY ID in composite")

        # Check if composite column exists
        has_composite = 'is_composite' in arivale_df.columns

        # First, try exact match
        mapped_df = arivale_df.merge(
            kraken_df,
            left_on='uniprot_normalized',
            right_on='clean_uniprot_id',
            how='left',
            suffixes=('_arivale', '_kraken')
        )

        # For composite IDs that didn't match, try matching ANY ID in the composite
        if has_composite:
            composite_unmapped = mapped_df['is_composite'] & mapped_df['clean_uniprot_id'].isna()
            composite_unmapped_count = composite_unmapped.sum()

            if composite_unmapped_count > 0:
                print(f"Attempting alternate matching for {composite_unmapped_count} unmapped composite IDs...")

                for idx in mapped_df[composite_unmapped].index:
                    composite_id = mapped_df.at[idx, 'uniprot_normalized']
                    # Split and try each ID
                    id_parts = [p.strip() for p in str(composite_id).split(',')]

                    for part in id_parts:
                        match = kraken_df[kraken_df['clean_uniprot_id'] == part]
                        if not match.empty:
                            # Found a match! Update the row
                            for col in kraken_df.columns:
                                if col != 'clean_uniprot_id':
                                    mapped_df.at[idx, f"{col}_kraken"] = match.iloc[0][col]
                            mapped_df.at[idx, 'clean_uniprot_id'] = part
                            print(f"  Matched composite {composite_id} via part {part}")
                            break

        print(f"Merge completed: {len(mapped_df)} total rows")

        # Calculate mapping statistics
        print("\nCalculating mapping statistics...")

        total_arivale = len(arivale_df)
        unique_arivale = arivale_df['uniprot_normalized'].nunique()

        # Count successful mappings
        matched_mask = mapped_df['clean_uniprot_id'].notna()
        matched_count = matched_mask.sum()
        unique_matched = mapped_df[matched_mask]['uniprot_normalized'].nunique()

        # Unmapped entries
        unmapped_mask = ~matched_mask
        unmapped_count = unmapped_mask.sum()
        unique_unmapped = mapped_df[unmapped_mask]['uniprot_normalized'].nunique()

        print(f"Mapping Results:")
        print(f"  Total Arivale entries: {total_arivale}")
        print(f"  Unique Arivale UniProt IDs: {unique_arivale}")
        print(f"  Mapped entries: {matched_count}")
        print(f"  Unique mapped UniProt IDs: {unique_matched}")
        print(f"  Unmapped entries: {unmapped_count}")
        print(f"  Unique unmapped UniProt IDs: {unique_unmapped}")
        print(f"  Mapping rate: {100 * unique_matched / unique_arivale:.1f}%")

        # Add mapping metadata columns
        print("\nAdding mapping metadata...")

        # Initialize mapping metadata
        mapped_df['mapping_confidence'] = 0.0
        mapped_df['mapping_type'] = 'unmapped'

        # Set values for successful mappings
        mapped_df.loc[matched_mask, 'mapping_confidence'] = 1.0
        mapped_df.loc[matched_mask, 'mapping_type'] = 'exact'

        # Create the final output format matching the requirements
        print("Creating final output format...")

        # Create a proper kraken_node_id that includes the UniProt ID for successful matches
        mapped_df['kraken_node_id'] = mapped_df.apply(
            lambda row: f"UniProtKB:{row['clean_uniprot_id']}" if pd.notna(row['clean_uniprot_id']) else '',
            axis=1
        )

        # Required columns according to the prompt:
        # arivale_uniprot, arivale_name, kg2c_node_id, kg2c_name, kg2c_category,
        # mapping_confidence, mapping_type, semantic_category
        final_df = mapped_df[[
            'uniprot_normalized',        # → arivale_uniprot
            'name_arivale',              # → arivale_name
            'kraken_node_id',            # → kraken_node_id (UniProtKB:P12345 format)
            'name_kraken',               # → kraken_name (was kg2c_name)
            'category',                  # → kraken_category (was kg2c_category)
            'mapping_confidence',        # → mapping_confidence
            'mapping_type',              # → mapping_type
            'semantic_category',         # → semantic_category
            'gene_name',                 # Additional Arivale info
            'gene_description',          # Additional Arivale info
            'description'                # Kraken description
        ]].copy()

        # Rename columns to match requirements
        final_df = final_df.rename(columns={
            'uniprot_normalized': 'arivale_uniprot',
            'name_arivale': 'arivale_name',
            'id': 'kraken_node_id',
            'name_kraken': 'kraken_name',
            'category': 'kraken_category',
            'description': 'kraken_description'
        })

        # Handle unmapped entries - fill with appropriate values
        unmapped_final_mask = final_df['kraken_node_id'].isna()
        final_df.loc[unmapped_final_mask, 'kraken_node_id'] = ''
        final_df.loc[unmapped_final_mask, 'kraken_name'] = ''
        final_df.loc[unmapped_final_mask, 'kraken_category'] = ''
        final_df.loc[unmapped_final_mask, 'semantic_category'] = 'unmapped'
        final_df.loc[unmapped_final_mask, 'kraken_description'] = ''

        # Display sample mappings
        print("\nSample successful mappings:")
        sample_mapped = final_df[final_df['mapping_type'] == 'exact'].head(5)
        for i, (_, row) in enumerate(sample_mapped.iterrows(), 1):
            print(f"  {i}. {row['arivale_uniprot']} → {row['kraken_node_id']}")
            print(f"     {row['arivale_name']} → {row['kraken_name']}")
            print(f"     Category: {row['semantic_category']}")

        if unique_unmapped > 0:
            print(f"\nSample unmapped UniProt IDs:")
            sample_unmapped = final_df[final_df['mapping_type'] == 'unmapped']['arivale_uniprot'].unique()[:5]
            for i, uid in enumerate(sample_unmapped, 1):
                print(f"  {i}. {uid}")

        # Save final mappings
        output_file = RESULTS_DIR / "arivale_kraken_mappings.tsv"
        final_df.to_csv(output_file, sep='\t', index=False)
        print(f"\nSaved final mappings to: {output_file}")

        # Create mapping statistics for the report
        mapping_stats = {
            'total_arivale_entries': total_arivale,
            'unique_arivale_uniprot_ids': unique_arivale,
            'mapped_entries': int(matched_count),
            'unique_mapped_ids': int(unique_matched),
            'unmapped_entries': int(unmapped_count),
            'unique_unmapped_ids': int(unique_unmapped),
            'mapping_rate_percent': round(100 * unique_matched / unique_arivale, 2),
            'semantic_category_distribution': final_df[final_df['semantic_category'] != 'unmapped']['semantic_category'].value_counts().to_dict(),
            'sample_mapped_ids': sample_mapped[['arivale_uniprot', 'kraken_node_id']].to_dict('records'),
            'unmapped_ids': sample_unmapped.tolist() if unique_unmapped > 0 else []
        }

        # Save statistics
        stats_file = RESULTS_DIR / "mapping_statistics.json"
        import json
        with open(stats_file, 'w') as f:
            json.dump(mapping_stats, f, indent=2)

        print(f"Mapping statistics saved to: {stats_file}")

        # Summary
        print(f"\n{'='*60}")
        print("MAPPING SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successfully mapped: {unique_matched}/{unique_arivale} UniProt IDs ({mapping_stats['mapping_rate_percent']}%)")
        print(f"❌ Unmapped: {unique_unmapped} UniProt IDs")
        print(f"📊 Total entries processed: {total_arivale}")
        print(f"📁 Results saved to: {output_file}")
        print("\n✅ Script 3 completed successfully!")

    except Exception as e:
        print(f"❌ Error during mapping: {e}")
        raise

if __name__ == "__main__":
    main()
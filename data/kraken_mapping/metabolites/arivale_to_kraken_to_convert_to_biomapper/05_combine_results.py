#!/usr/bin/env python3
"""
Proto-action: Combine all mapping results and generate final outputs
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path
import json

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "results"

def main():
    """Combine all mapping results and generate final reports."""
    print("Combining all mapping results...")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load all mapping results
    mapping_files = [
        ("hmdb", INPUT_DIR / "hmdb_mapped_results.tsv"),
        ("pubchem", INPUT_DIR / "pubchem_mapped_results.tsv")
    ]

    all_mappings = []
    total_mapped = 0

    for mapping_type, file_path in mapping_files:
        if file_path.exists():
            df = pd.read_csv(file_path, sep='\t')
            all_mappings.append(df)
            print(f"Loaded {len(df)} {mapping_type.upper()} mappings")
            total_mapped += len(df)
        else:
            print(f"Warning: {mapping_type.upper()} mapping file not found: {file_path}")

    # Load unmatched metabolites
    unmatched_file = INPUT_DIR / "final_unmatched.tsv"
    unmatched_df = None
    if unmatched_file.exists():
        unmatched_df = pd.read_csv(unmatched_file, sep='\t')
        print(f"Loaded {len(unmatched_df)} unmatched metabolites")
    else:
        print("No unmatched metabolites file found")

    # Load original Arivale data for totals
    arivale_file = INPUT_DIR / "arivale_metabolites_clean.tsv"
    if arivale_file.exists():
        arivale_df = pd.read_csv(arivale_file, sep='\t')
        total_arivale = len(arivale_df)
        print(f"Total Arivale metabolites: {total_arivale}")
    else:
        print("Warning: Original Arivale data not found for statistics")
        total_arivale = total_mapped + (len(unmatched_df) if unmatched_df is not None else 0)

    # Combine all successful mappings
    if all_mappings:
        combined_mappings = pd.concat(all_mappings, ignore_index=True)

        # Sort by confidence score (highest first) and then by mapping source
        combined_mappings = combined_mappings.sort_values(
            ['mapping_confidence', 'mapping_source'],
            ascending=[False, True]
        ).reset_index(drop=True)

        print(f"\nFinal Mapping Summary:")
        print(f"Total successful mappings: {len(combined_mappings)}")
        print(f"Mapping success rate: {100*len(combined_mappings)/total_arivale:.1f}%")

        # Breakdown by mapping source
        source_counts = combined_mappings['mapping_source'].value_counts()
        for source, count in source_counts.items():
            print(f"  {source.upper()}: {count} ({100*count/len(combined_mappings):.1f}%)")

        # Breakdown by Kraken entity type
        if 'entity_type' in combined_mappings.columns:
            entity_counts = combined_mappings['entity_type'].value_counts()
            print(f"\nMapped to Kraken entity types:")
            for entity_type, count in entity_counts.items():
                print(f"  {entity_type.title()}: {count}")

        # Save final combined mappings
        final_file = OUTPUT_DIR / "arivale_to_kraken_metabolites_mapping.tsv"
        combined_mappings.to_csv(final_file, sep='\t', index=False)
        print(f"\nSaved final mappings to: {final_file}")

        # Create a summary mapping file with key fields only
        summary_columns = [
            'arivale_metabolite_id',
            'arivale_name',
            'kraken_id',
            'kraken_name',
            'mapping_source',
            'mapping_confidence'
        ]

        if all(col in combined_mappings.columns for col in summary_columns):
            summary_mappings = combined_mappings[summary_columns].copy()
            summary_file = OUTPUT_DIR / "arivale_to_kraken_metabolites_summary.tsv"
            summary_mappings.to_csv(summary_file, sep='\t', index=False)
            print(f"Saved summary mappings to: {summary_file}")

        # Show sample mappings
        print(f"\nSample final mappings:")
        print(combined_mappings[summary_columns].head(5).to_string())

    else:
        print("No successful mappings found!")
        combined_mappings = pd.DataFrame()

    # Save unmatched metabolites if any
    if unmatched_df is not None and len(unmatched_df) > 0:
        unmatched_output_file = OUTPUT_DIR / "arivale_unmatched_metabolites.tsv"
        unmatched_df.to_csv(unmatched_output_file, sep='\t', index=False)
        print(f"Saved {len(unmatched_df)} unmatched metabolites to: {unmatched_output_file}")

    # Generate mapping statistics report
    stats = {
        "total_arivale_metabolites": total_arivale,
        "total_mapped": len(combined_mappings) if len(combined_mappings) > 0 else 0,
        "total_unmatched": len(unmatched_df) if unmatched_df is not None else 0,
        "mapping_success_rate": round(100 * len(combined_mappings) / total_arivale, 2) if total_arivale > 0 else 0,
        "mapping_breakdown": {}
    }

    if len(combined_mappings) > 0:
        source_counts = combined_mappings['mapping_source'].value_counts()
        for source, count in source_counts.items():
            stats["mapping_breakdown"][source] = {
                "count": int(count),
                "percentage": round(100 * count / len(combined_mappings), 2)
            }

    # Save statistics
    stats_file = OUTPUT_DIR / "mapping_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Saved mapping statistics to: {stats_file}")

    # Print final summary
    print(f"\n" + "="*50)
    print(f"ARIVALE TO KRAKEN METABOLITE MAPPING COMPLETE")
    print(f"="*50)
    print(f"Total Arivale metabolites: {total_arivale}")
    print(f"Successfully mapped: {len(combined_mappings) if len(combined_mappings) > 0 else 0} ({stats['mapping_success_rate']:.1f}%)")
    print(f"Unmatched: {stats['total_unmatched']}")
    print(f"\nResults saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
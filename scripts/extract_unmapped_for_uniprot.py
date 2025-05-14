"""
Extract unmapped entries from Phase 1 forward mapping results for UniProt fallback mapping.

This script reads the phase1_forward_mapping_intermediate.tsv file, extracts entries
that were not mapped through direct or secondary methods, and saves them to a file
for processing by the UniProt fallback mapping client.
"""

import pandas as pd
import os
from pathlib import Path

# Define paths
INPUT_FILE = "/home/ubuntu/output/phase1_forward_mapping_intermediate.tsv"
OUTPUT_DIR = "/home/ubuntu/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "phase1_unmapped_for_uniprot.tsv")

def main():
    # Create output directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Read the phase 1 mapping results
    print(f"Reading mapping results from {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, sep='\t')
    
    # Extract unmapped entries
    unmapped = df[df['mapping_method'] == 'No mapping found']
    print(f"Found {len(unmapped)} unmapped entries out of {len(df)} total entries ({len(unmapped)/len(df)*100:.2f}%)")
    
    # Count unique gene names in unmapped entries
    unique_gene_names = unmapped["source_ukbb_parsed_gene_name"].nunique()
    print(f"Number of unique gene names in unmapped entries: {unique_gene_names}")
    
    # Select only the relevant columns for UniProt fallback
    unmapped_for_uniprot = unmapped[
        ['source_ukbb_assay_raw', 'source_ukbb_uniprot_ac', 'source_ukbb_parsed_gene_name', 'source_ukbb_panel']
    ].copy()
    
    # Add an ID column for tracking through the fallback process
    unmapped_for_uniprot['ukbb_id'] = unmapped_for_uniprot['source_ukbb_assay_raw']
    
    # Rename columns to simpler names for the fallback client
    unmapped_for_uniprot = unmapped_for_uniprot.rename(columns={
        'source_ukbb_assay_raw': 'ukbb_assay',
        'source_ukbb_uniprot_ac': 'ukbb_uniprot',
        'source_ukbb_parsed_gene_name': 'ukbb_gene_name',
        'source_ukbb_panel': 'ukbb_panel'
    })
    
    # Save to file
    unmapped_for_uniprot.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"Saved {len(unmapped_for_uniprot)} entries to {OUTPUT_FILE}")
    
    # Analyze panel distribution
    panel_distribution = unmapped_for_uniprot['ukbb_panel'].value_counts()
    print("\nPanel distribution of unmapped entries:")
    for panel, count in panel_distribution.items():
        print(f"  {panel}: {count} entries ({count/len(unmapped_for_uniprot)*100:.2f}%)")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Proto-action: Load UKBB Nightingale metabolite data
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - no context/parameters
INPUT_FILE = "/home/ubuntu/biomapper/data/harmonization/nightingale/nightingale_metadata_enrichment_to_convert_to_biomapper/output/nightingale_final.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    print("Loading UKBB Nightingale metabolite data...")

    # Load the enriched Nightingale data
    try:
        df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(df)} Nightingale biomarkers from {INPUT_FILE}")
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Available files in directory:")
        import os
        directory = os.path.dirname(INPUT_FILE)
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith(('.tsv', '.csv')):
                    print(f"  {os.path.join(directory, file)}")
        return

    # Display data structure
    print(f"\nColumns available: {list(df.columns)}")
    print(f"Sample data shape: {df.shape}")

    # Filter for true metabolites only (unified standard)
    print(f"\nFiltering for true metabolites only...")
    if 'is_true_metabolite' in df.columns:
        df_true_metabolites = df[df['is_true_metabolite'] == True].copy()
        print(f"Found {len(df_true_metabolites)} true metabolites out of {len(df)} total biomarkers")
    else:
        print("ERROR: is_true_metabolite column not found in source data")
        return

    # Select relevant columns for metabolite mapping
    key_columns = ['Biomarker']  # Always needed
    optional_columns = ['ChEBI_ID', 'HMDB_ID_merged', 'PubChem_CID_merged',
                       'metabolite_classification', 'is_true_metabolite']

    selected_columns = [col for col in key_columns + optional_columns if col in df_true_metabolites.columns]
    df_selected = df_true_metabolites[selected_columns].copy()

    print(f"\nSelected columns for mapping: {selected_columns}")

    # Show sample data
    print(f"\nSample true metabolite records:")
    print(df_selected.head(3).to_string())

    # Check for ID availability in true metabolites
    id_columns = ['ChEBI_ID', 'HMDB_ID_merged', 'PubChem_CID_merged']
    for col in id_columns:
        if col in df_selected.columns:
            non_null_count = df_selected[col].notna().sum()
            print(f"\n{col}: {non_null_count}/{len(df_selected)} true metabolites have IDs ({100*non_null_count/len(df_selected):.1f}%)")

    # Save the loaded data
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / "nightingale_loaded.tsv"
    df_selected.to_csv(output_file, sep='\t', index=False)

    print(f"\nSaved {len(df_selected)} Nightingale biomarkers to {output_file}")

    # Summary
    print(f"\nSUMMARY:")
    print(f"  - Total biomarkers loaded: {len(df_selected)}")
    print(f"  - Columns saved: {len(selected_columns)}")
    print(f"  - Output: {output_file}")

if __name__ == "__main__":
    main()
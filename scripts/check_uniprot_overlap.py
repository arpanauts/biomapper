import pandas as pd
import csv

# File paths
ukbb_file = '/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv'
arivale_file = '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv'

# --- Load UKBB UniProt IDs ---
try:
    print(f"Loading UKBB data from: {ukbb_file}")
    ukbb_df = pd.read_csv(ukbb_file, sep='\t', usecols=['UniProt'])
    ukbb_uniprot_ids = set(ukbb_df['UniProt'].dropna().unique())
    print(f"Found {len(ukbb_uniprot_ids)} unique UniProt IDs in UKBB file.")
except Exception as e:
    print(f"Error loading UKBB file: {e}")
    ukbb_uniprot_ids = set()

# --- Load Arivale UniProt IDs ---
try:
    print(f"Loading Arivale data from: {arivale_file}")
    # Need to skip comments and handle potential quoting/dialect issues
    # Find the first non-comment line to get headers
    header_line_num = 0
    with open(arivale_file, 'r') as f:
        for i, line in enumerate(f):
            if not line.startswith('#'):
                header_line_num = i
                break

    arivale_df = pd.read_csv(
        arivale_file, 
        sep='\t', 
        skiprows=header_line_num, 
        usecols=['uniprot'],
        quoting=csv.QUOTE_ALL, # Based on head output
        on_bad_lines='warn' # Log lines that can't be parsed
    )
    arivale_uniprot_ids = set(arivale_df['uniprot'].dropna().unique())
    print(f"Found {len(arivale_uniprot_ids)} unique UniProt IDs in Arivale file.")
except Exception as e:
    print(f"Error loading Arivale file: {e}")
    arivale_uniprot_ids = set()

# --- Calculate Intersection ---
if ukbb_uniprot_ids and arivale_uniprot_ids:
    overlap = ukbb_uniprot_ids.intersection(arivale_uniprot_ids)
    print(f"\nOverlap Calculation:")
    print(f"- UKBB Unique UniProt IDs: {len(ukbb_uniprot_ids)}")
    print(f"- Arivale Unique UniProt IDs: {len(arivale_uniprot_ids)}")
    print(f"- Number of overlapping UniProt IDs: {len(overlap)}")

    # Print the first overlapping ID found, if any
    if overlap:
        first_overlap_id = next(iter(overlap))
        print(f"\nExample Overlapping ID: {first_overlap_id}")
        exit()
    else:
        print("\nNo overlapping IDs found.")
else:
    print("\nCould not perform overlap calculation due to errors loading files.")

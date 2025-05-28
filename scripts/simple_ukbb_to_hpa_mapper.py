#!/usr/bin/env python3
"""Simple UKBB to HPA protein mapper using direct lookup"""

import argparse
import pandas as pd
from datetime import datetime
import os

def main():
    parser = argparse.ArgumentParser(description='Map UKBB proteins to HPA proteins')
    parser.add_argument('input_file', help='Input UKBB file path')
    parser.add_argument('output_file', help='Output file path')
    parser.add_argument('--hpa_file', default='/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv',
                        help='HPA data file path')
    parser.add_argument('--summary', action='store_true', help='Generate summary report')
    args = parser.parse_args()
    
    print(f"Loading HPA data from {args.hpa_file}...")
    hpa_df = pd.read_csv(args.hpa_file)
    
    # Check columns
    print(f"HPA columns: {hpa_df.columns.tolist()}")
    print(f"HPA shape: {hpa_df.shape}")
    print(f"First few rows of HPA data:")
    print(hpa_df.head())
    
    # Determine the UniProt column name in HPA
    uniprot_col = None
    for col in ['uniprot', 'UniProt', 'uniprotkb_ac', 'UniProtKB_AC']:
        if col in hpa_df.columns:
            uniprot_col = col
            break
    
    if uniprot_col is None:
        print("ERROR: Could not find UniProt column in HPA data")
        print(f"Available columns: {hpa_df.columns.tolist()}")
        return
    
    print(f"Using UniProt column: {uniprot_col}")
    
    # Create a set of HPA UniProt IDs
    hpa_uniprot_ids = set(hpa_df[uniprot_col].dropna().unique())
    print(f"Loaded {len(hpa_uniprot_ids)} unique proteins from HPA")
    
    print(f"Loading UKBB data from {args.input_file}...")
    ukbb_df = pd.read_csv(args.input_file, sep='\t')
    print(f"Loaded {len(ukbb_df)} rows from UKBB")
    
    # Add mapping columns
    ukbb_df['HPA_UniProtKB_AC'] = ''
    ukbb_df['mapping_confidence_score'] = ''
    ukbb_df['mapping_path_details'] = ''
    ukbb_df['mapping_hop_count'] = ''
    ukbb_df['mapping_direction'] = ''
    ukbb_df['validation_status'] = ''
    
    # Perform mapping
    mapped_count = 0
    for idx, row in ukbb_df.iterrows():
        uniprot_id = row['UniProt']
        if pd.notna(uniprot_id) and uniprot_id in hpa_uniprot_ids:
            # Found a match
            ukbb_df.at[idx, 'HPA_UniProtKB_AC'] = uniprot_id
            ukbb_df.at[idx, 'mapping_confidence_score'] = 1.0
            ukbb_df.at[idx, 'mapping_path_details'] = 'Direct UniProtKB AC match'
            ukbb_df.at[idx, 'mapping_hop_count'] = 0
            ukbb_df.at[idx, 'mapping_direction'] = 'forward'
            ukbb_df.at[idx, 'validation_status'] = 'validated'
            mapped_count += 1
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    
    # Write output
    print(f"Writing results to {args.output_file}...")
    ukbb_df.to_csv(args.output_file, sep='\t', index=False)
    
    print(f"Successfully mapped {mapped_count} out of {len(ukbb_df)} proteins ({mapped_count/len(ukbb_df)*100:.1f}%)")
    
    # Generate summary if requested
    if args.summary:
        summary_file = args.output_file.replace('.tsv', '_summary_report.txt')
        with open(summary_file, 'w') as f:
            f.write(f"# UKBB_Protein to HPA_Protein Mapping Summary Report\n\n")
            f.write(f"Input File: {args.input_file}\n")
            f.write(f"Output File: {args.output_file}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Overall Statistics\n")
            f.write(f"Total records: {len(ukbb_df)}\n")
            f.write(f"Successfully mapped: {mapped_count} ({mapped_count/len(ukbb_df)*100:.2f}%)\n\n")
            f.write(f"## HPA Data Statistics\n")
            f.write(f"Total unique proteins in HPA: {len(hpa_uniprot_ids)}\n")
        print(f"Summary report written to {summary_file}")

if __name__ == '__main__':
    main()
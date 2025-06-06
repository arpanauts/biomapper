#!/usr/bin/env python3
"""Simple UKBB to QIN protein mapper using direct lookup"""

import argparse
import pandas as pd
from datetime import datetime
import os

def main():
    parser = argparse.ArgumentParser(description='Map UKBB proteins to QIN proteins')
    parser.add_argument('input_file', help='Input UKBB file path')
    parser.add_argument('output_file', help='Output file path')
    parser.add_argument('--qin_file', default='/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv',
                        help='QIN data file path')
    parser.add_argument('--summary', action='store_true', help='Generate summary report')
    args = parser.parse_args()
    
    print(f"Loading QIN data from {args.qin_file}...")
    qin_df = pd.read_csv(args.qin_file)
    
    # Create a mapping of UniProt to organs
    qin_mapping = {}
    for _, row in qin_df.iterrows():
        uniprot = row['uniprot']
        if pd.notna(uniprot):
            if uniprot not in qin_mapping:
                qin_mapping[uniprot] = []
            qin_mapping[uniprot].append({
                'gene': row['gene'],
                'organ': row['organ']
            })
    
    print(f"Loaded {len(qin_mapping)} unique proteins from QIN")
    
    print(f"Loading UKBB data from {args.input_file}...")
    ukbb_df = pd.read_csv(args.input_file, sep='\t')
    print(f"Loaded {len(ukbb_df)} rows from UKBB")
    
    # Add mapping columns
    ukbb_df['QIN_UniProtKB_AC'] = ''
    ukbb_df['QIN_gene'] = ''
    ukbb_df['QIN_organs'] = ''
    ukbb_df['mapping_confidence_score'] = ''
    ukbb_df['mapping_path_details'] = ''
    ukbb_df['mapping_hop_count'] = ''
    ukbb_df['mapping_direction'] = ''
    ukbb_df['validation_status'] = ''
    
    # Perform mapping
    mapped_count = 0
    for idx, row in ukbb_df.iterrows():
        uniprot_id = row['UniProt']
        if pd.notna(uniprot_id) and uniprot_id in qin_mapping:
            # Found a match
            qin_info = qin_mapping[uniprot_id]
            ukbb_df.at[idx, 'QIN_UniProtKB_AC'] = uniprot_id
            ukbb_df.at[idx, 'QIN_gene'] = qin_info[0]['gene']
            ukbb_df.at[idx, 'QIN_organs'] = '|'.join([info['organ'] for info in qin_info])
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
            f.write(f"# UKBB_Protein to Qin_Protein Mapping Summary Report\n\n")
            f.write(f"Input File: {args.input_file}\n")
            f.write(f"Output File: {args.output_file}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Overall Statistics\n")
            f.write(f"Total records: {len(ukbb_df)}\n")
            f.write(f"Successfully mapped: {mapped_count} ({mapped_count/len(ukbb_df)*100:.2f}%)\n\n")
            f.write(f"## QIN Data Statistics\n")
            f.write(f"Total unique proteins in QIN: {len(qin_mapping)}\n")
            f.write(f"Total protein-organ pairs in QIN: {len(qin_df)}\n")
        print(f"Summary report written to {summary_file}")

if __name__ == '__main__':
    main()
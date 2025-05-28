#!/usr/bin/env python3
"""Quick test to check if QIN protein lookup is working"""

import pandas as pd
import sys

# Load QIN data
qin_df = pd.read_csv('/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv')
print(f"QIN data shape: {qin_df.shape}")
print(f"QIN columns: {qin_df.columns.tolist()}")
print(f"\nFirst 5 rows:")
print(qin_df.head())

# Get unique UniProt IDs from QIN
qin_uniprot_ids = set(qin_df['uniprot'].dropna().unique())
print(f"\nTotal unique UniProt IDs in QIN: {len(qin_uniprot_ids)}")

# Load UKBB data (first 100 rows for testing)
ukbb_df = pd.read_csv('/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv', sep='\t', nrows=100)
print(f"\nUKBB data shape (first 100): {ukbb_df.shape}")
print(f"UKBB columns: {ukbb_df.columns.tolist()}")

# Get UKBB UniProt IDs
ukbb_uniprot_ids = set(ukbb_df['UniProt'].dropna().unique())
print(f"\nTotal unique UniProt IDs in UKBB sample: {len(ukbb_uniprot_ids)}")

# Find overlap
overlap = ukbb_uniprot_ids.intersection(qin_uniprot_ids)
print(f"\nOverlap between UKBB and QIN: {len(overlap)} proteins")
print(f"Overlap percentage: {len(overlap) / len(ukbb_uniprot_ids) * 100:.1f}%")

if overlap:
    print(f"\nExample overlapping proteins: {list(overlap)[:5]}")
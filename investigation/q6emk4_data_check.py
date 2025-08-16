#!/usr/bin/env python3
"""Verify Q6EMK4 presence and format in both datasets"""

import pandas as pd
import re

# 1. Load and check Arivale
arivale_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

# Find Q6EMK4
q6_rows = arivale_df[arivale_df['uniprot'] == 'Q6EMK4']
print(f"Q6EMK4 in Arivale: {len(q6_rows)} rows")
for idx, row in q6_rows.iterrows():
    print(f"  Row {idx}:")
    print(f"    uniprot: '{row['uniprot']}'")
    print(f"    Length: {len(row['uniprot'])}")
    print(f"    Hex: {row['uniprot'].encode('utf-8').hex()}")
    print(f"    Other columns: {row.to_dict()}")

# 2. Load and check KG2c
kg2c_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

# Find all Q6EMK4 occurrences
print("\nQ6EMK4 in KG2c:")

# Check id column
id_matches = kg2c_df[kg2c_df['id'].str.contains('Q6EMK4', na=False)]
print(f"  In id column: {len(id_matches)} rows")

# Check xrefs column
xref_matches = kg2c_df[kg2c_df['xrefs'].str.contains('Q6EMK4', na=False)]
print(f"  In xrefs column: {len(xref_matches)} rows")

for idx, row in xref_matches.head(10).iterrows():
    print(f"\n  Row {idx} ({row['id']}):")
    # Extract the Q6EMK4 part
    xrefs = str(row['xrefs'])
    pattern = re.compile(r'(?:UniProtKB|PR)[:\s]+(Q6EMK4)')
    matches = pattern.findall(xrefs)
    print(f"    Extracted: {matches}")
    
    # Check exact substring
    if 'UniProtKB:Q6EMK4' in xrefs:
        start = xrefs.index('UniProtKB:Q6EMK4')
        substring = xrefs[start:start+20]
        print(f"    Substring: '{substring}'")
        print(f"    Hex: {substring.encode('utf-8').hex()}")
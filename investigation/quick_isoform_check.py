#!/usr/bin/env python3
"""Quick check of isoform patterns for matched vs unmatched proteins"""

import pandas as pd
import re

print("QUICK ISOFORM PATTERN CHECK")
print("=" * 80)

# Load datasets
target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)
results_df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)

# Get sample proteins
matched_proteins = results_df[results_df['match_status'] == 'matched']['uniprot'].dropna().unique()[:5]
source_only_proteins = results_df[results_df['match_status'] == 'source_only']['uniprot'].dropna().unique()[:5]

print("Checking 5 matched proteins:")
for protein in matched_proteins:
    # Quick search in xrefs
    matches = target_df[target_df['xrefs'].str.contains(protein, na=False)]
    if len(matches) > 0:
        xref_sample = str(matches.iloc[0]['xrefs'])
        # Look for the protein pattern
        if f'{protein}-' in xref_sample:
            print(f"  {protein}: Found WITH ISOFORM suffix")
        else:
            print(f"  {protein}: Found as BASE (no isoform)")

print("\nChecking 5 source-only proteins:")
for protein in source_only_proteins:
    matches = target_df[target_df['xrefs'].str.contains(protein, na=False)]
    if len(matches) > 0:
        xref_sample = str(matches.iloc[0]['xrefs'])
        if f'{protein}-' in xref_sample:
            print(f"  {protein}: Found WITH ISOFORM suffix")
        else:
            print(f"  {protein}: Found as BASE (no isoform)")

# Special check for Q6EMK4
print("\nQ6EMK4 specific check:")
q6_matches = target_df[target_df['xrefs'].str.contains('Q6EMK4', na=False)]
if len(q6_matches) > 0:
    xref = str(q6_matches.iloc[0]['xrefs'])
    idx = xref.find('Q6EMK4')
    context = xref[max(0, idx-10):min(len(xref), idx+20)]
    print(f"  Context: ...{context}...")
    if 'Q6EMK4-' in xref:
        print("  Q6EMK4 has ISOFORM suffix")
    else:
        print("  Q6EMK4 is BASE protein (no isoform)")
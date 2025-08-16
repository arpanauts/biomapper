#!/usr/bin/env python3
"""Deep analysis of why only 0.7% of proteins match when we expect much higher"""

import pandas as pd
import re
from collections import defaultdict

print("ANALYZING MATCH FAILURE - ONE-TO-MANY MAPPING BUG")
print("=" * 80)

# Load both datasets
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

print(f"Source dataset: {len(source_df)} rows")
print(f"Target dataset: {len(target_df)} rows")

# Count unique proteins in source
unique_source_proteins = source_df['uniprot'].dropna().unique()
print(f"Unique source proteins: {len(unique_source_proteins)}")

# Build index of what SHOULD match
print("\nBuilding target index to see what SHOULD match...")
target_uniprot_ids = set()

# Extract from id column
for idx, row in target_df.iterrows():
    target_id = str(row['id'])
    if target_id.startswith('UniProtKB:'):
        uniprot_id = target_id.replace('UniProtKB:', '').split('-')[0]  # Remove isoform
        target_uniprot_ids.add(uniprot_id)

# Extract from xrefs column
pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
for idx, row in target_df.iterrows():
    xrefs = str(row.get('xrefs', ''))
    if xrefs and xrefs != 'nan':
        for match in pattern.finditer(xrefs):
            uniprot_id = match.group(1).split('-')[0]  # Remove isoform
            target_uniprot_ids.add(uniprot_id)

print(f"Unique UniProt IDs in target: {len(target_uniprot_ids)}")

# Calculate expected matches
expected_matches = []
for source_protein in unique_source_proteins:
    if source_protein in target_uniprot_ids:
        expected_matches.append(source_protein)

print(f"\nEXPECTED matches: {len(expected_matches)} ({len(expected_matches)/len(unique_source_proteins)*100:.1f}%)")

# Load actual results
results_path = '/tmp/biomapper_results/protein_mapping_results.csv'
results_df = pd.read_csv(results_path, low_memory=False)

# Get actual matches
actual_matched = results_df[results_df['match_status'] == 'matched']
unique_matched = actual_matched['uniprot'].dropna().unique()
print(f"ACTUAL matches: {len(unique_matched)} ({len(unique_matched)/len(unique_source_proteins)*100:.1f}%)")

print(f"\n🔴 MISSING MATCHES: {len(expected_matches) - len(unique_matched)}")
print(f"🔴 Match rate discrepancy: {(len(expected_matches) - len(unique_matched))/len(unique_source_proteins)*100:.1f}% of proteins that SHOULD match are failing")

# Find examples of proteins that should match but don't
missing_matches = set(expected_matches) - set(unique_matched)
print(f"\nSample of proteins that SHOULD match but DON'T:")
for protein in list(missing_matches)[:20]:
    source_info = source_df[source_df['uniprot'] == protein].iloc[0]
    result_info = results_df[results_df['uniprot'] == protein]
    if len(result_info) > 0:
        result_status = result_info.iloc[0]['match_status']
    else:
        result_status = "NOT IN RESULTS"
    print(f"  {protein}: {source_info.get('gene_name', 'N/A')} -> {result_status}")

# Analyze the pattern
print("\n" + "=" * 80)
print("PATTERN ANALYSIS:")

# Check if there's a pattern in what fails
source_only_proteins = results_df[results_df['match_status'] == 'source_only']['uniprot'].dropna().unique()
print(f"\nProteins marked as 'source_only': {len(source_only_proteins)}")
print(f"Of these, how many are in target index: {len([p for p in source_only_proteins if p in target_uniprot_ids])}")

# One-to-many analysis
print("\nONE-TO-MANY MAPPING ANALYSIS:")
target_to_source_count = defaultdict(list)
for idx, row in target_df.iterrows():
    xrefs = str(row.get('xrefs', ''))
    if xrefs and xrefs != 'nan':
        for match in pattern.finditer(xrefs):
            uniprot_id = match.group(1).split('-')[0]
            target_to_source_count[uniprot_id].append(idx)

# Count distribution
one_to_one = 0
one_to_many = 0
for protein, indices in target_to_source_count.items():
    if len(indices) == 1:
        one_to_one += 1
    else:
        one_to_many += 1

print(f"Proteins with ONE target match: {one_to_one}")
print(f"Proteins with MULTIPLE target matches: {one_to_many}")

# Check Q6EMK4 specifically
if 'Q6EMK4' in target_to_source_count:
    print(f"\nQ6EMK4 has {len(target_to_source_count['Q6EMK4'])} target matches")
    print(f"Q6EMK4 in expected matches: {'Q6EMK4' in expected_matches}")
    print(f"Q6EMK4 in actual matches: {'Q6EMK4' in unique_matched}")
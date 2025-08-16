#!/usr/bin/env python3
"""Check if duplicate matches could be causing the issue"""

import pandas as pd
import re
from collections import defaultdict

# Load data
target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

print("CHECKING FOR DUPLICATE MATCH ISSUES")
print("=" * 80)

# Build index and check for duplicates
target_uniprot_to_indices = defaultdict(list)
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

proteins_of_interest = ['Q6EMK4', 'Q16769', 'Q16853', 'Q8N423', 'Q8NHL6']
protein_occurrences = defaultdict(list)

for target_idx, target_row in target_df.iterrows():
    xref_value = str(target_row.get('xrefs', ''))
    if xref_value and xref_value != 'nan':
        for match in uniprot_pattern.finditer(xref_value):
            uniprot_id = match.group(1)
            target_uniprot_to_indices[uniprot_id].append(target_idx)
            
            if uniprot_id in proteins_of_interest:
                protein_occurrences[uniprot_id].append({
                    'target_idx': target_idx,
                    'target_id': target_row['id'],
                    'name': target_row['name']
                })

print("Proteins and their occurrences in target:")
for protein in proteins_of_interest:
    occurrences = protein_occurrences[protein]
    print(f"\n{protein}: {len(occurrences)} occurrences")
    for occ in occurrences[:3]:  # Show first 3
        print(f"  - idx={occ['target_idx']}, id={occ['target_id']}, name={occ['name']}")

# Check if Q6EMK4 has something special
print("\n" + "=" * 80)
print("SPECIAL ANALYSIS FOR Q6EMK4:")

q6_occurrences = protein_occurrences['Q6EMK4']
if q6_occurrences:
    print(f"Q6EMK4 appears {len(q6_occurrences)} time(s)")
    
    # Compare with a working protein
    q16769_occurrences = protein_occurrences['Q16769']
    print(f"Q16769 (working) appears {len(q16769_occurrences)} time(s)")
    
    # Key insight: Check if single vs multiple occurrences matters
    single_occurrence_proteins = [p for p in proteins_of_interest if len(protein_occurrences[p]) == 1]
    multiple_occurrence_proteins = [p for p in proteins_of_interest if len(protein_occurrences[p]) > 1]
    
    print(f"\nProteins with SINGLE occurrence: {single_occurrence_proteins}")
    print(f"Proteins with MULTIPLE occurrences: {multiple_occurrence_proteins}")
    
    # Load results to check which ones matched
    results_df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)
    
    print("\nChecking match status for these proteins:")
    for protein in proteins_of_interest:
        result = results_df[results_df['uniprot'] == protein]
        if len(result) > 0:
            status = result.iloc[0]['match_status']
            occurrences = len(protein_occurrences[protein])
            print(f"  {protein}: {status} (occurrences: {occurrences})")

print("\n" + "=" * 80)
print("HYPOTHESIS:")
print("If proteins with single occurrences fail while those with multiple succeed,")
print("there might be a bug in how single matches are handled vs multiple matches.")
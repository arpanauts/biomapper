#!/usr/bin/env python3
"""Investigate if isoform handling is causing the matching failure"""

import pandas as pd
import re

print("ISOFORM PATTERN INVESTIGATION")
print("=" * 80)

# Load datasets
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

results_df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)

# Get matched and unmatched proteins
matched_proteins = results_df[results_df['match_status'] == 'matched']['uniprot'].dropna().unique()
source_only_proteins = results_df[results_df['match_status'] == 'source_only']['uniprot'].dropna().unique()

print(f"Matched proteins: {len(matched_proteins)}")
print(f"Source-only proteins: {len(source_only_proteins)}")

# Sample analysis - check a few matched vs unmatched
print("\n" + "=" * 80)
print("CHECKING MATCHED PROTEINS IN KG2C:")
print("-" * 80)

pattern = re.compile(r'(?:UniProtKB|PR)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

# Check some matched proteins
matched_sample = list(matched_proteins)[:10]
for protein in matched_sample:
    found_as_isoform = False
    found_as_base = False
    found_locations = []
    
    for idx, row in target_df.iterrows():
        xrefs = str(row.get('xrefs', ''))
        if xrefs and xrefs != 'nan':
            # Look for exact match with isoform
            if f'UniProtKB:{protein}-' in xrefs or f'PR:{protein}-' in xrefs:
                found_as_isoform = True
                # Find the exact isoform
                matches = re.findall(f'{protein}-\\d+', xrefs)
                if matches:
                    found_locations.append(f"Row {idx}: {matches[0]} (ISOFORM)")
            # Look for base protein without isoform
            elif f'UniProtKB:{protein}' in xrefs or f'PR:{protein}' in xrefs:
                # Make sure it's not followed by a dash (isoform)
                if not re.search(f'{protein}-\\d+', xrefs):
                    found_as_base = True
                    found_locations.append(f"Row {idx}: {protein} (BASE)")
                else:
                    found_as_isoform = True
                    matches = re.findall(f'{protein}-\\d+', xrefs)
                    found_locations.append(f"Row {idx}: {matches[0]} (ISOFORM)")
    
    if found_locations:
        print(f"✅ {protein}: Found as {'ISOFORM' if found_as_isoform else 'BASE'}")
        for loc in found_locations[:2]:  # Show first 2 locations
            print(f"    {loc}")

print("\n" + "=" * 80)
print("CHECKING SOURCE-ONLY PROTEINS IN KG2C:")
print("-" * 80)

# Check some source-only proteins
source_only_sample = list(source_only_proteins)[:10]
for protein in source_only_sample:
    found_as_isoform = False
    found_as_base = False
    found_locations = []
    
    for idx, row in target_df.iterrows():
        xrefs = str(row.get('xrefs', ''))
        if xrefs and xrefs != 'nan':
            # Look for exact match with isoform
            if f'UniProtKB:{protein}-' in xrefs or f'PR:{protein}-' in xrefs:
                found_as_isoform = True
                matches = re.findall(f'{protein}-\\d+', xrefs)
                if matches:
                    found_locations.append(f"Row {idx}: {matches[0]} (ISOFORM)")
            # Look for base protein without isoform
            elif f'UniProtKB:{protein}' in xrefs or f'PR:{protein}' in xrefs:
                # Make sure it's not followed by a dash
                if not re.search(f'{protein}-\\d+', xrefs):
                    found_as_base = True
                    found_locations.append(f"Row {idx}: {protein} (BASE)")
                else:
                    found_as_isoform = True
                    matches = re.findall(f'{protein}-\\d+', xrefs)
                    found_locations.append(f"Row {idx}: {matches[0]} (ISOFORM)")
    
    if found_locations:
        print(f"❌ {protein}: Found as {'ISOFORM' if found_as_isoform else 'BASE'} BUT NOT MATCHED")
        for loc in found_locations[:2]:
            print(f"    {loc}")
    else:
        print(f"❓ {protein}: NOT FOUND (checking deeper...)")

# Special check for Q6EMK4
print("\n" + "=" * 80)
print("SPECIAL ANALYSIS FOR Q6EMK4:")
print("-" * 80)

for idx, row in target_df.iterrows():
    xrefs = str(row.get('xrefs', ''))
    if 'Q6EMK4' in xrefs:
        print(f"Found Q6EMK4 at row {idx}")
        print(f"  ID: {row['id']}")
        print(f"  Name: {row['name']}")
        
        # Extract the exact format
        if 'UniProtKB:Q6EMK4' in xrefs:
            # Find the exact context
            start = xrefs.index('UniProtKB:Q6EMK4')
            end = min(start + 30, len(xrefs))
            context = xrefs[start:end]
            print(f"  Context: ...{context}...")
            
            # Check if it's followed by isoform
            if start + len('UniProtKB:Q6EMK4') < len(xrefs):
                next_char = xrefs[start + len('UniProtKB:Q6EMK4')]
                print(f"  Next character after Q6EMK4: '{next_char}' (ord: {ord(next_char)})")
                if next_char == '-':
                    print("  ⚠️ Q6EMK4 appears to have an isoform suffix!")
                elif next_char == '|':
                    print("  ✅ Q6EMK4 is stored as BASE protein (no isoform)")
                    
        if 'PR:Q6EMK4' in xrefs:
            start = xrefs.index('PR:Q6EMK4')
            end = min(start + 20, len(xrefs))
            context = xrefs[start:end]
            print(f"  PR Context: ...{context}...")

print("\n" + "=" * 80)
print("HYPOTHESIS:")
print("The matching logic might be incorrectly handling base proteins when:")
print("1. They appear WITHOUT isoform suffixes in KG2c")
print("2. The extraction regex might be capturing them differently")
print("3. The matching logic might expect isoforms but get base IDs")
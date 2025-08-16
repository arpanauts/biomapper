#!/usr/bin/env python3
"""Trace exactly what happens to Q6EMK4 in the matching logic"""

import pandas as pd
import re

# Load data
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

# Simulate parameters
class Params:
    source_id_column = 'uniprot'
    target_id_column = 'id'
    target_xref_column = 'xrefs'
    composite_separator = '||'

params = Params()

print("TRACING Q6EMK4 THROUGH EXACT PRODUCTION LOGIC")
print("=" * 80)

# Find Q6EMK4 in source
q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_source) > 0:
    q6_source_idx = q6_source.index[0]
    print(f"Q6EMK4 found at source index: {q6_source_idx}")
    
    # Build indices exactly as production
    target_id_to_indices = {}
    target_uniprot_to_indices = {}
    
    print("\nBuilding target indices...")
    uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    q6_found_in_index = False
    for target_idx, target_row in target_df.iterrows():
        target_id = str(target_row[params.target_id_column])
        
        # Store original ID
        if target_id not in target_id_to_indices:
            target_id_to_indices[target_id] = []
        target_id_to_indices[target_id].append((target_idx, target_row))
        
        # Extract from xrefs
        if hasattr(params, 'target_xref_column'):
            xref_value = str(target_row.get(params.target_xref_column, ''))
            if xref_value and xref_value != 'nan':
                for match in uniprot_pattern.finditer(xref_value):
                    uniprot_id = match.group(1)
                    if uniprot_id not in target_uniprot_to_indices:
                        target_uniprot_to_indices[uniprot_id] = []
                    target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
                    
                    if uniprot_id == 'Q6EMK4':
                        q6_found_in_index = True
                        print(f"  Added Q6EMK4 to index at target_idx={target_idx}")
    
    print(f"\nIndex built. Q6EMK4 in index: {q6_found_in_index}")
    
    # Now trace what happens when we process Q6EMK4
    print("\nProcessing Q6EMK4 as source...")
    source_id = 'Q6EMK4'
    
    # Check first condition
    print(f"  Checking if '{source_id}' in target_uniprot_to_indices: {source_id in target_uniprot_to_indices}")
    
    if source_id in target_uniprot_to_indices:
        print("  ✅ FOUND in target_uniprot_to_indices")
        for target_idx, target_row in target_uniprot_to_indices[source_id]:
            print(f"    Would create match: source_idx={q6_source_idx}, target_idx={target_idx}")
            print(f"    Target ID: {target_row[params.target_id_column]}")
            # This should work!
    
    # Check if it would hit the elif
    elif source_id in target_id_to_indices:
        print("  Would check target_id_to_indices (but won't reach here due to elif)")
    
    # Check composite logic
    if params.composite_separator in source_id:
        print("  Would check composite (Q6EMK4 is not composite)")
    else:
        print("  Q6EMK4 is not composite")
        # Check the else branch at line 462
        target_composite_parts = {}
        # Build composite parts (simplified)
        for target_idx, target_row in target_df.iterrows():
            target_id = str(target_row[params.target_id_column])
            if params.composite_separator in target_id:
                parts = target_id.split(params.composite_separator)
                for part in parts:
                    if part not in target_composite_parts:
                        target_composite_parts[part] = []
                    target_composite_parts[part].append((target_idx, target_id, target_row))
        
        if source_id in target_composite_parts:
            print(f"  Q6EMK4 found in composite parts: {len(target_composite_parts[source_id])} matches")
        else:
            print(f"  Q6EMK4 NOT in composite parts")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("Q6EMK4 SHOULD match via the first condition (target_uniprot_to_indices)")
    print("The match should be created successfully")
    print("\nSo why doesn't it work in production?")
    print("Possibilities:")
    print("1. The match is created but later discarded")
    print("2. The matched_source_indices set has an issue")
    print("3. There's a duplicate match that causes problems")
    print("4. The confidence filtering removes it (but it has 1.0 confidence)")
else:
    print("Q6EMK4 not found in source!")
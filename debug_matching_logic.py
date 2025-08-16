#!/usr/bin/env python3
"""
Debug the full matching logic to understand why Q6EMK4 doesn't match
"""
import pandas as pd
import re

print("🔍 DEBUGGING FULL MATCHING LOGIC FOR Q6EMK4")
print("=" * 60)

# Load datasets
print("\n1. Loading datasets...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')

print(f"   Arivale: {len(arivale_df)} rows")
print(f"   KG2c: {len(kg2c_df)} rows")

# Check Q6EMK4 in source
print("\n2. Q6EMK4 in Arivale dataset:")
q6emk4_arivale = arivale_df[arivale_df['uniprot'] == 'Q6EMK4']
if len(q6emk4_arivale) > 0:
    print(f"   ✅ Found at index {q6emk4_arivale.index[0]}")
    print(f"   uniprot column: '{q6emk4_arivale.iloc[0]['uniprot']}'")
else:
    print("   ❌ Not found")

# Build the exact index as the action does
print("\n3. Building KG2c index (simulating action logic)...")
target_uniprot_to_indices = {}

# Process only the row we know has Q6EMK4
vasn_row = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
if len(vasn_row) > 0:
    target_idx = vasn_row.index[0]
    target_row = vasn_row.iloc[0]
    
    print(f"\n   Processing row {target_idx} (NCBIGene:114990):")
    
    # Check id column
    target_id = str(target_row['id'])
    print(f"   id column: '{target_id}'")
    
    if target_id.startswith('UniProtKB:'):
        uniprot_id = target_id.replace('UniProtKB:', '')
        print(f"   Extracted from id: {uniprot_id}")
    else:
        print("   No UniProt in id column")
    
    # Check xrefs column
    xref_value = str(target_row.get('xrefs', ''))
    print(f"   xrefs column: {xref_value[:100]}...")
    
    if xref_value and xref_value != 'nan':
        uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
        matches = uniprot_pattern.findall(xref_value)
        print(f"   UniProt IDs from xrefs: {matches}")
        
        for uniprot_id in matches:
            # Store with isoform
            if uniprot_id not in target_uniprot_to_indices:
                target_uniprot_to_indices[uniprot_id] = []
            target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
            
            # Also store base ID (without isoform suffix)
            base_id = uniprot_id.split('-')[0]
            if base_id != uniprot_id:
                if base_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[base_id] = []
                target_uniprot_to_indices[base_id].append((target_idx, target_row))
                print(f"   Also indexed base ID: {base_id}")

print(f"\n4. Index contents:")
print(f"   Keys in index: {list(target_uniprot_to_indices.keys())}")

# Now simulate the matching
print("\n5. Simulating matching for Q6EMK4...")

source_id = 'Q6EMK4'
print(f"   Looking up '{source_id}' in index...")

if source_id in target_uniprot_to_indices:
    print(f"   ✅ FOUND in index!")
    entries = target_uniprot_to_indices[source_id]
    print(f"   Number of matches: {len(entries)}")
    for idx, row in entries:
        print(f"     - Row {idx}: {row['id']} ({row['name']})")
else:
    print(f"   ❌ NOT FOUND in index")
    
    # Try base ID
    base_id = source_id.split('-')[0]
    print(f"   Trying base ID: '{base_id}'")
    if base_id in target_uniprot_to_indices:
        print(f"   ✅ Base ID found!")
    else:
        print(f"   ❌ Base ID not found either")

# Now check the actual results file
print("\n6. Checking actual results file...")
results_df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)

q6emk4_results = results_df[results_df['uniprot'] == 'Q6EMK4']
print(f"   Q6EMK4 rows in results: {len(q6emk4_results)}")

if len(q6emk4_results) > 0:
    for idx, row in q6emk4_results.iterrows():
        print(f"\n   Result row {idx}:")
        print(f"     uniprot: {row['uniprot']}")
        print(f"     match_status: {row['match_status']}")
        if 'match_type' in row:
            print(f"     match_type: {row.get('match_type', 'N/A')}")
        if 'target_id' in row and pd.notna(row['target_id']):
            print(f"     target_id: {row.get('target_id', 'N/A')}")

print("\n" + "=" * 60)
print("💡 ANALYSIS:")
if 'Q6EMK4' in target_uniprot_to_indices and len(q6emk4_results) > 0:
    if q6emk4_results.iloc[0]['match_status'] == 'source_only':
        print("   ❌ Q6EMK4 IS in the index but shows as 'source_only'!")
        print("   This suggests the matching logic is not working correctly.")
    elif q6emk4_results.iloc[0]['match_status'] == 'matched':
        print("   ✅ Q6EMK4 is matched correctly!")
else:
    print("   The extraction or matching has an issue.")
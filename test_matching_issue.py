#!/usr/bin/env python3
"""
Demonstrate the matching issue with Q6EMK4
"""
import pandas as pd
import re

print("🔍 DEMONSTRATING THE Q6EMK4 MATCHING ISSUE")
print("=" * 60)

# Create minimal test data
print("\n1. Creating test datasets...")

# Arivale data with Q6EMK4
arivale_data = pd.DataFrame({
    'uniprot': ['Q6EMK4', 'P12345', 'O00533'],
    'description': ['VASN protein', 'Test protein 1', 'Test protein 2']
})

# KG2c data with Q6EMK4 in xrefs
kg2c_data = pd.DataFrame({
    'id': ['NCBIGene:114990', 'UniProtKB:P12345', 'UniProtKB:O00533'],
    'name': ['VASN', 'Protein 1', 'Protein 2'],
    'xrefs': [
        'ENSEMBL:ENSG00000168140||UniProtKB:Q6EMK4||PR:Q6EMK4',
        'RefSeq:NP_001234',
        'RefSeq:NP_005678'
    ]
})

print(f"   Arivale: {len(arivale_data)} proteins")
print(f"   KG2c: {len(kg2c_data)} entities")

# Simulate the matching logic
print("\n2. Building index (simulating action logic)...")

target_uniprot_to_indices = {}
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

for target_idx, target_row in kg2c_data.iterrows():
    target_id = str(target_row['id'])
    
    # Extract from ID column
    if target_id.startswith('UniProtKB:'):
        uniprot_id = target_id.replace('UniProtKB:', '')
        if uniprot_id not in target_uniprot_to_indices:
            target_uniprot_to_indices[uniprot_id] = []
        target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
        print(f"   Indexed from ID: {uniprot_id} -> row {target_idx}")
    
    # Extract from xrefs column
    xref_value = str(target_row.get('xrefs', ''))
    if xref_value and xref_value != 'nan':
        matches = uniprot_pattern.findall(xref_value)
        for uniprot_id in matches:
            if uniprot_id not in target_uniprot_to_indices:
                target_uniprot_to_indices[uniprot_id] = []
            target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
            print(f"   Indexed from xrefs: {uniprot_id} -> row {target_idx}")

print(f"\nIndex contents: {list(target_uniprot_to_indices.keys())}")

# Now simulate the matching
print("\n3. Simulating matching process...")

matches = []
for source_idx, source_row in arivale_data.iterrows():
    source_id = str(source_row['uniprot'])
    print(f"\nProcessing source: {source_id}")
    
    # Check if source ID is in the UniProt index
    if source_id in target_uniprot_to_indices:
        print(f"  ✅ Found in UniProt index!")
        for target_idx, target_row in target_uniprot_to_indices[source_id]:
            match_info = {
                "source_idx": source_idx,
                "target_idx": target_idx,
                "source_id": source_id,
                "target_id": str(target_row['id']),
                "match_type": "direct",
            }
            matches.append(match_info)
            print(f"  Matched to: {target_row['id']} ({target_row['name']})")
    else:
        print(f"  ❌ Not found in index")

print(f"\n4. Results:")
print(f"   Total matches: {len(matches)}")
print(f"   Matched proteins: {[m['source_id'] for m in matches]}")

# Create result dataframe
print("\n5. Creating result dataset (as the action would)...")

matched_source_indices = {m['source_idx'] for m in matches}
result_rows = []

# Add matched rows
for match in matches:
    source_row = arivale_data.iloc[match['source_idx']]
    target_row = kg2c_data.iloc[match['target_idx']]
    
    result_row = {
        'uniprot': source_row['uniprot'],
        'description': source_row['description'],
        'target_id': target_row['id'],
        'target_name': target_row['name'],
        'match_status': 'matched',
        'match_type': match['match_type']
    }
    result_rows.append(result_row)

# Add unmatched source rows
for source_idx, source_row in arivale_data.iterrows():
    if source_idx not in matched_source_indices:
        result_row = {
            'uniprot': source_row['uniprot'],
            'description': source_row['description'],
            'target_id': None,
            'target_name': None,
            'match_status': 'source_only',
            'match_type': None
        }
        result_rows.append(result_row)

result_df = pd.DataFrame(result_rows)

print("\nFinal results:")
print(result_df.to_string())

print("\n" + "=" * 60)
print("💡 CONCLUSION:")
if result_df[result_df['uniprot'] == 'Q6EMK4']['match_status'].iloc[0] == 'matched':
    print("   ✅ Q6EMK4 matched successfully!")
    print("   The extraction and matching logic works correctly.")
else:
    print("   ❌ Q6EMK4 did not match!")
    print("   There is an issue with the matching implementation.")
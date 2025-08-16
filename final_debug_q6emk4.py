#!/usr/bin/env python3
"""
Final debug to understand Q6EMK4 issue
"""
import pandas as pd
import re

print("🔍 FINAL DEBUG: WHY Q6EMK4 DOESN'T MATCH")
print("=" * 60)

# Load actual production data
print("\n1. Loading production datasets (only Q6EMK4 relevant rows)...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')

# Get Q6EMK4 row from Arivale
q6_arivale = arivale_df[arivale_df['uniprot'] == 'Q6EMK4']
print(f"   Q6EMK4 in Arivale:")
print(f"     Row index: {q6_arivale.index[0]}")
print(f"     uniprot value: '{q6_arivale.iloc[0]['uniprot']}'")
print(f"     Type: {type(q6_arivale.iloc[0]['uniprot'])}")

# Check for any hidden characters
uniprot_val = q6_arivale.iloc[0]['uniprot']
print(f"     Length: {len(uniprot_val)}")
print(f"     Repr: {repr(uniprot_val)}")
print(f"     Hex: {uniprot_val.encode('utf-8').hex()}")

# Load KG2c
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')

# Get the row with Q6EMK4 in xrefs
vasn_row = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
print(f"\n   NCBIGene:114990 in KG2c:")
print(f"     Row index: {vasn_row.index[0]}")

xrefs = vasn_row.iloc[0]['xrefs']
print(f"     xrefs substring check: {'Q6EMK4' in xrefs}")

# Extract UniProt IDs
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
extracted = uniprot_pattern.findall(xrefs)
print(f"     Extracted UniProt IDs: {extracted}")
print(f"     Q6EMK4 in extracted: {'Q6EMK4' in extracted}")

# Check exact extracted value
if 'Q6EMK4' in extracted:
    idx = extracted.index('Q6EMK4')
    extracted_val = extracted[idx]
    print(f"     Extracted Q6EMK4 value: '{extracted_val}'")
    print(f"     Type: {type(extracted_val)}")
    print(f"     Length: {len(extracted_val)}")
    print(f"     Repr: {repr(extracted_val)}")
    print(f"     Hex: {extracted_val.encode('utf-8').hex()}")

# Compare the values
print(f"\n2. Comparison:")
print(f"   Arivale uniprot == Extracted: {uniprot_val == 'Q6EMK4'}")
if 'Q6EMK4' in extracted:
    print(f"   Arivale uniprot == Extracted Q6EMK4: {uniprot_val == extracted_val}")
    print(f"   Both are 'Q6EMK4': {uniprot_val == 'Q6EMK4' and extracted_val == 'Q6EMK4'}")

# Now simulate the exact matching logic
print(f"\n3. Simulating exact matching logic...")

# Build index
target_uniprot_to_indices = {}

# Process the specific KG2c row
target_idx = vasn_row.index[0]
target_row = vasn_row.iloc[0]

xref_value = str(target_row.get('xrefs', ''))
if xref_value and xref_value != 'nan':
    matches = uniprot_pattern.findall(xref_value)
    for uniprot_id in matches:
        if uniprot_id not in target_uniprot_to_indices:
            target_uniprot_to_indices[uniprot_id] = []
        target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
        
        # Also add base ID
        base_id = uniprot_id.split('-')[0]
        if base_id != uniprot_id:
            if base_id not in target_uniprot_to_indices:
                target_uniprot_to_indices[base_id] = []
            target_uniprot_to_indices[base_id].append((target_idx, target_row))

print(f"   Index keys: {list(target_uniprot_to_indices.keys())}")

# Try matching
source_id = str(q6_arivale.iloc[0]['uniprot'])
print(f"\n   Trying to match source ID: '{source_id}'")
print(f"   source_id in index: {source_id in target_uniprot_to_indices}")

if source_id in target_uniprot_to_indices:
    print(f"   ✅ MATCH FOUND!")
else:
    print(f"   ❌ NO MATCH!")
    
    # Try exact string
    if 'Q6EMK4' in target_uniprot_to_indices:
        print(f"   But 'Q6EMK4' IS in index!")
        print(f"   This suggests a type/encoding issue")
    
    # Debug the actual keys
    print(f"\n   Debugging index keys:")
    for key in target_uniprot_to_indices.keys():
        if 'Q6' in key or 'EMK' in key:
            print(f"     Key: '{key}' (repr: {repr(key)}, hex: {key.encode('utf-8').hex()})")

print("\n" + "=" * 60)
print("💡 ANALYSIS:")
if source_id in target_uniprot_to_indices:
    print("   The matching SHOULD work. Issue is elsewhere in the action.")
else:
    print("   The source ID doesn't match the index key. Check for:")
    print("   - Hidden characters")
    print("   - Type conversion issues")
    print("   - String encoding problems")
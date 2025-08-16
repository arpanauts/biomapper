#!/usr/bin/env python3
"""Find the REAL bug - why Q6EMK4 isn't matching"""

import pandas as pd
import re

print("FINDING THE REAL BUG")
print("=" * 80)

# Load the actual data files
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

print(f"Loaded source: {len(source_df)} rows")
print(f"Loaded target: {len(target_df)} rows")

# Check Q6EMK4 in source
q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_source) > 0:
    q6_idx = q6_source.index[0]
    print(f"\n✅ Q6EMK4 found in source at index {q6_idx}")
    print(f"   Value: '{q6_source.iloc[0]['uniprot']}'")
else:
    print("\n❌ Q6EMK4 NOT in source!")

# Check Q6EMK4 in target xrefs
print("\n" + "=" * 80)
print("CHECKING TARGET FOR Q6EMK4:")

# Look for any row containing Q6EMK4
q6_in_target = target_df[target_df['xrefs'].str.contains('Q6EMK4', na=False)]
print(f"\nRows containing 'Q6EMK4' string: {len(q6_in_target)}")

if len(q6_in_target) > 0:
    for idx, row in q6_in_target.iterrows():
        print(f"\nRow {idx}:")
        print(f"  id: {row['id']}")
        print(f"  name: {row['name']}")
        xrefs = str(row['xrefs'])
        print(f"  xrefs (first 200 chars): {xrefs[:200]}")
        
        # Check what patterns match
        patterns_to_test = [
            (r'UniProtKB:Q6EMK4', 'UniProtKB:Q6EMK4'),
            (r'PR:Q6EMK4', 'PR:Q6EMK4'),
            (r'UniProtKB[:\s]+Q6EMK4', 'UniProtKB with optional space'),
            (r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', 'Production regex'),
        ]
        
        print(f"\n  Pattern matching tests:")
        for pattern_str, description in patterns_to_test:
            pattern = re.compile(pattern_str)
            matches = pattern.findall(xrefs)
            print(f"    {description}: {matches if matches else 'NO MATCH'}")

# Now simulate the EXACT production index building
print("\n" + "=" * 80)
print("SIMULATING PRODUCTION INDEX BUILDING:")

target_uniprot_to_indices = {}

# Check if target_xref_column is being used
print("\nUsing target_xref_column='xrefs'")

# This is the EXACT pattern from production
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

rows_processed = 0
q6_found_during_indexing = False

for target_idx, target_row in target_df.iterrows():
    rows_processed += 1
    
    # Check xrefs column (this is what production does)
    xref_value = str(target_row.get('xrefs', ''))
    
    if xref_value and xref_value != 'nan':
        # Extract UniProt IDs
        for match in uniprot_pattern.finditer(xref_value):
            uniprot_id = match.group(1)
            
            if uniprot_id not in target_uniprot_to_indices:
                target_uniprot_to_indices[uniprot_id] = []
            
            target_uniprot_to_indices[uniprot_id].append(target_idx)
            
            # Check if we found Q6EMK4
            if uniprot_id == 'Q6EMK4':
                q6_found_during_indexing = True
                print(f"\n✅ Found Q6EMK4 during indexing at row {target_idx}")
                print(f"   Extracted from: {xref_value[:100]}...")

print(f"\nProcessed {rows_processed} rows")
print(f"Built index with {len(target_uniprot_to_indices)} UniProt IDs")
print(f"Q6EMK4 in index: {'Q6EMK4' in target_uniprot_to_indices}")

if 'Q6EMK4' in target_uniprot_to_indices:
    indices = target_uniprot_to_indices['Q6EMK4']
    print(f"Q6EMK4 maps to {len(indices)} target rows: {indices[:5]}")

# Now test matching
print("\n" + "=" * 80)
print("TESTING MATCHING:")

source_id = 'Q6EMK4'
if source_id in target_uniprot_to_indices:
    print(f"✅ Q6EMK4 SHOULD match!")
    print(f"   Would match to rows: {target_uniprot_to_indices[source_id]}")
else:
    print(f"❌ Q6EMK4 would NOT match!")
    print(f"   Not found in target_uniprot_to_indices")
    
    # Debug: Check if it's a key type issue
    print("\n   Debugging key types:")
    print(f"   source_id type: {type(source_id)}")
    print(f"   source_id value: '{source_id}'")
    print(f"   source_id bytes: {source_id.encode('utf-8').hex()}")
    
    # Check a few keys in the index
    print("\n   Sample keys from index:")
    sample_keys = list(target_uniprot_to_indices.keys())[:10]
    for key in sample_keys:
        if 'Q6' in key:
            print(f"     '{key}' (type: {type(key)})")

# Final check: Is there something wrong with the regex?
print("\n" + "=" * 80)
print("REGEX VALIDATION:")

test_string = "UniProtKB:Q6EMK4"
matches = uniprot_pattern.findall(test_string)
print(f"Test string: '{test_string}'")
print(f"Regex matches: {matches}")

test_string2 = "PR:Q6EMK4||UniProtKB:Q6EMK4"
matches2 = uniprot_pattern.findall(test_string2)
print(f"Test string: '{test_string2}'")
print(f"Regex matches: {matches2}")
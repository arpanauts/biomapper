#!/usr/bin/env python3
"""Check for whitespace and encoding issues in Q6EMK4"""

import pandas as pd
import re

print("CHECKING FOR WHITESPACE/ENCODING ISSUES")
print("=" * 80)

# Load source
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

# Get Q6EMK4 from source
q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_source) > 0:
    source_value = q6_source.iloc[0]['uniprot']
    print("SOURCE Q6EMK4:")
    print(f"  Value: '{source_value}'")
    print(f"  Repr: {repr(source_value)}")
    print(f"  Length: {len(source_value)}")
    print(f"  Bytes: {source_value.encode('utf-8').hex()}")
    print(f"  Stripped: '{source_value.strip()}'")
    print(f"  Has whitespace: {source_value != source_value.strip()}")
    
    # Check for invisible characters
    import unicodedata
    categories = {}
    for char in source_value:
        cat = unicodedata.category(char)
        categories[cat] = categories.get(cat, 0) + 1
    print(f"  Unicode categories: {categories}")

# Load target and check xrefs
target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

print("\n" + "=" * 80)
print("TARGET Q6EMK4 IN XREFS:")

# Get the row with Q6EMK4
q6_target = target_df[target_df['xrefs'].str.contains('Q6EMK4', na=False)]
if len(q6_target) > 0:
    xrefs = str(q6_target.iloc[0]['xrefs'])
    
    # Find the Q6EMK4 part
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    matches = pattern.findall(xrefs)
    
    if matches:
        for extracted in matches:
            if 'Q6EMK4' in extracted:
                print(f"  Extracted: '{extracted}'")
                print(f"  Repr: {repr(extracted)}")
                print(f"  Length: {len(extracted)}")
                print(f"  Bytes: {extracted.encode('utf-8').hex()}")
                print(f"  Stripped: '{extracted.strip()}'")
                print(f"  Has whitespace: {extracted != extracted.strip()}")

# Now check if they're EXACTLY equal
print("\n" + "=" * 80)
print("COMPARISON:")

if len(q6_source) > 0 and matches:
    source_val = q6_source.iloc[0]['uniprot']
    target_val = matches[0] if 'Q6EMK4' in matches[0] else None
    
    if target_val:
        print(f"Source: '{source_val}'")
        print(f"Target: '{target_val}'")
        print(f"Equal: {source_val == target_val}")
        print(f"Equal after strip: {source_val.strip() == target_val.strip()}")
        
        # Byte-by-byte comparison
        if source_val != target_val:
            print("\nByte-by-byte comparison:")
            source_bytes = source_val.encode('utf-8')
            target_bytes = target_val.encode('utf-8')
            for i, (sb, tb) in enumerate(zip(source_bytes, target_bytes)):
                if sb != tb:
                    print(f"  Position {i}: source={sb:02x} target={tb:02x}")

# Check the actual matching logic
print("\n" + "=" * 80)
print("TESTING EXACT MATCHING LOGIC:")

# Build a simple index
test_index = {}
test_value = 'Q6EMK4'  # What we extract from xrefs
test_index[test_value] = [6789]

# Test with source value
source_test = 'Q6EMK4'  # What we get from source
print(f"Source value: '{source_test}'")
print(f"Looking for in index...")
if source_test in test_index:
    print(f"  ✅ Found in index!")
else:
    print(f"  ❌ NOT found in index!")
    print(f"  Index keys: {list(test_index.keys())}")

# Now test with actual source value
if len(q6_source) > 0:
    actual_source = str(q6_source.iloc[0]['uniprot'])
    print(f"\nActual source value: '{actual_source}'")
    if actual_source in test_index:
        print(f"  ✅ Found in index!")
    else:
        print(f"  ❌ NOT found in index!")
        
        # Try stripping
        stripped = actual_source.strip()
        if stripped in test_index:
            print(f"  ✅ Found after stripping!")
        else:
            print(f"  ❌ Still not found after stripping!")
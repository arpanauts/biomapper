#!/usr/bin/env python3
"""
Investigate the data to understand why we're getting 0 matches
"""
import pandas as pd
import re

print("🔍 INVESTIGATING DATA FORMATS")
print("=" * 60)

# Load a sample of each dataset
print("\n1. Loading Arivale proteins...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', sep='\t')
print(f"   Loaded {len(arivale_df)} rows")
print(f"   Columns: {list(arivale_df.columns)}")

# Check what Arivale UniProt IDs look like
print("\n2. Sample Arivale UniProt IDs:")
if 'uniprot' in arivale_df.columns:
    sample_ids = arivale_df['uniprot'].dropna().head(10)
    for i, uid in enumerate(sample_ids, 1):
        print(f"   {i}. '{uid}' (type: {type(uid).__name__})")
    
    # Check for unique patterns
    unique_ids = arivale_df['uniprot'].dropna().unique()
    print(f"\n   Total unique Arivale IDs: {len(unique_ids)}")
    
    # Check format patterns
    uniprot_pattern = re.compile(r'^[A-Z][0-9][A-Z0-9]{3}[0-9]$|^[A-Z][0-9][A-Z0-9]{3}[0-9]-\d+$')
    matching_pattern = sum(1 for uid in unique_ids if uniprot_pattern.match(str(uid)))
    print(f"   IDs matching UniProt pattern: {matching_pattern}/{len(unique_ids)}")

print("\n3. Loading KG2c entities...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
print(f"   Loaded {len(kg2c_df)} rows")
print(f"   Columns: {list(kg2c_df.columns)}")

# Check what KG2c ID column contains
print("\n4. Sample KG2c 'id' column:")
sample_ids = kg2c_df['id'].head(10)
for i, kid in enumerate(sample_ids, 1):
    print(f"   {i}. '{kid}'")

# Check if there's an xrefs/equivalent_identifiers column
xref_col = None
for col in ['equivalent_identifiers', 'xrefs', 'xref', 'cross_references']:
    if col in kg2c_df.columns:
        xref_col = col
        break

if xref_col:
    print(f"\n5. Found xrefs column: '{xref_col}'")
    print("   Sample xref values:")
    sample_xrefs = kg2c_df[xref_col].dropna().head(5)
    for i, xref in enumerate(sample_xrefs, 1):
        print(f"   {i}. '{xref[:200]}...' (length: {len(str(xref))})")
    
    # Look for UniProt references in xrefs
    print("\n6. Checking for UniProt references in xrefs...")
    uniprot_count = 0
    uniprot_examples = []
    
    for idx, row in kg2c_df.head(1000).iterrows():  # Check first 1000 rows
        xref = str(row.get(xref_col, ''))
        if 'UniProt' in xref or 'uniprot' in xref:
            uniprot_count += 1
            if len(uniprot_examples) < 3:
                # Extract the UniProt ID from the xref
                match = re.search(r'UniProt[^:]*:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', xref)
                if match:
                    uniprot_examples.append((row['id'], match.group(1), xref[:100]))
    
    print(f"   Found {uniprot_count}/1000 entries with UniProt references")
    
    if uniprot_examples:
        print("\n   Examples of UniProt extraction:")
        for kg2c_id, uniprot_id, xref_snippet in uniprot_examples:
            print(f"   KG2c ID: {kg2c_id}")
            print(f"   Extracted UniProt: {uniprot_id}")
            print(f"   From xref: {xref_snippet}...")
            print()
else:
    print("\n5. ❌ No xrefs column found!")
    print(f"   Available columns: {kg2c_df.columns.tolist()}")

# Direct comparison test
print("\n7. Direct matching test:")
arivale_ids = set(arivale_df['uniprot'].dropna().astype(str))
kg2c_direct_ids = set(kg2c_df['id'].astype(str))

direct_matches = arivale_ids & kg2c_direct_ids
print(f"   Direct matches between Arivale 'uniprot' and KG2c 'id': {len(direct_matches)}")

if direct_matches:
    print("   Examples:", list(direct_matches)[:5])

# Check if KG2c IDs are prefixed
print("\n8. Checking KG2c ID formats:")
kg2c_prefixes = {}
for kid in kg2c_df['id'].head(1000):
    prefix = str(kid).split(':')[0] if ':' in str(kid) else 'NO_PREFIX'
    kg2c_prefixes[prefix] = kg2c_prefixes.get(prefix, 0) + 1

print("   ID prefix distribution (first 1000):")
for prefix, count in sorted(kg2c_prefixes.items(), key=lambda x: -x[1])[:10]:
    print(f"   - {prefix}: {count}")

print("\n" + "=" * 60)
print("📊 SUMMARY:")
print(f"   Arivale: {len(unique_ids)} unique UniProt IDs")
print(f"   KG2c: {len(kg2c_df)} total entities")
print(f"   Direct matches: {len(direct_matches)}")
print(f"   Xrefs column: {'✅ Found' if xref_col else '❌ Not found'}")
print("\n💡 CONCLUSION:")
if len(direct_matches) == 0 and xref_col:
    print("   We need to extract UniProt IDs from the xrefs field!")
    print("   The KG2c 'id' column doesn't contain UniProt IDs directly.")
elif len(direct_matches) > 0:
    print("   Some direct matches found, but may need xref extraction for full coverage.")
else:
    print("   Unable to determine matching strategy - check data formats.")
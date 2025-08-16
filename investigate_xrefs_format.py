#!/usr/bin/env python3
"""
Deep investigation of xrefs format in KG2c data
"""
import pandas as pd
import re
from collections import Counter

print("🔍 INVESTIGATING XREFS FORMAT IN KG2C")
print("=" * 60)

# Load KG2c data
print("\n1. Loading KG2c data...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
print(f"   Loaded {len(kg2c_df)} rows")

# Focus on entries with xrefs
xrefs_data = kg2c_df[kg2c_df['xrefs'].notna()].copy()
print(f"   Entries with xrefs: {len(xrefs_data)}")

print("\n2. Analyzing xrefs format patterns...")
# Sample some xrefs to understand the format
sample_xrefs = xrefs_data['xrefs'].head(20)
print("   First 20 xrefs samples:")
for i, xref in enumerate(sample_xrefs, 1):
    xref_str = str(xref)
    # Look for UniProt patterns
    uniprot_matches = re.findall(r'UniProtKB:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', xref_str)
    if uniprot_matches:
        print(f"   {i}. Found UniProt IDs: {uniprot_matches}")
        print(f"      Raw snippet: {xref_str[:100]}...")
    else:
        print(f"   {i}. No UniProt found in: {xref_str[:100]}...")

print("\n3. Counting UniProt references in xrefs...")
uniprot_pattern = re.compile(r'UniProtKB:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
kg2c_uniprot_from_xrefs = set()

for xref in xrefs_data['xrefs']:
    if pd.notna(xref):
        matches = uniprot_pattern.findall(str(xref))
        kg2c_uniprot_from_xrefs.update(matches)

print(f"   Total unique UniProt IDs extracted from xrefs: {len(kg2c_uniprot_from_xrefs)}")

# Also check the id column for UniProtKB: prefix
print("\n4. Checking id column for UniProtKB: prefix...")
kg2c_uniprot_from_id = set()
for id_val in kg2c_df['id']:
    if str(id_val).startswith('UniProtKB:'):
        uniprot_id = str(id_val).replace('UniProtKB:', '')
        kg2c_uniprot_from_id.add(uniprot_id)

print(f"   UniProt IDs from id column: {len(kg2c_uniprot_from_id)}")

# Combine all UniProt IDs from KG2c
all_kg2c_uniprot = kg2c_uniprot_from_id | kg2c_uniprot_from_xrefs
print(f"\n5. Total unique UniProt IDs in KG2c (id + xrefs): {len(all_kg2c_uniprot)}")

# Load Arivale data
print("\n6. Loading Arivale data...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')
arivale_uniprot = set(arivale_df['uniprot'].dropna().astype(str))
print(f"   Arivale unique UniProt IDs: {len(arivale_uniprot)}")

# Check for matches
print("\n7. Checking for matches...")
matches = arivale_uniprot & all_kg2c_uniprot
print(f"   ✅ MATCHES FOUND: {len(matches)}")
print(f"      Match rate: {len(matches)/len(arivale_uniprot)*100:.1f}% of Arivale proteins")

if matches:
    print(f"\n   Sample matches:")
    for match in list(matches)[:10]:
        print(f"      - {match}")

# Check what's NOT matching
print("\n8. Analyzing non-matches...")
non_matches = arivale_uniprot - all_kg2c_uniprot
print(f"   Arivale IDs not found in KG2c: {len(non_matches)}")
if non_matches:
    print(f"   Sample non-matches:")
    for nm in list(non_matches)[:10]:
        print(f"      - {nm}")

# Check if there are other UniProt patterns in xrefs
print("\n9. Looking for alternative UniProt patterns in xrefs...")
alt_patterns = [
    (r'uniprot:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', 'uniprot:'),
    (r'UniProt:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', 'UniProt:'),
    (r'UNIPROT:([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)', 'UNIPROT:'),
]

for pattern_str, prefix in alt_patterns:
    pattern = re.compile(pattern_str)
    found_ids = set()
    for xref in xrefs_data['xrefs'].head(1000):  # Check first 1000
        if pd.notna(xref):
            matches = pattern.findall(str(xref))
            found_ids.update(matches)
    if found_ids:
        print(f"   Found {len(found_ids)} IDs with pattern '{prefix}'")

print("\n" + "=" * 60)
print("💡 CONCLUSIONS:")
print(f"   - KG2c has {len(all_kg2c_uniprot)} unique UniProt IDs total")
print(f"   - Arivale has {len(arivale_uniprot)} unique UniProt IDs")
print(f"   - Found {len(matches)} matches ({len(matches)/len(arivale_uniprot)*100:.1f}% coverage)")
print(f"   - Missing {len(non_matches)} Arivale proteins in KG2c")
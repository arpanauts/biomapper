#!/usr/bin/env python3
"""
Check if removing isoform suffixes improves matching
"""
import pandas as pd
import re

print("🔍 CHECKING ISOFORM MATCHING")
print("=" * 60)

# Load data
print("\n1. Loading datasets...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')

# Extract UniProt IDs from KG2c
print("\n2. Extracting UniProt IDs from KG2c...")
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

kg2c_uniprot_with_isoform = set()
kg2c_uniprot_base = set()  # Without isoform suffix

# From id column
for id_val in kg2c_df['id']:
    if str(id_val).startswith('UniProtKB:'):
        uniprot_id = str(id_val).replace('UniProtKB:', '')
        kg2c_uniprot_with_isoform.add(uniprot_id)
        # Remove isoform suffix if present
        base_id = uniprot_id.split('-')[0]
        kg2c_uniprot_base.add(base_id)

# From xrefs column
for xref_value in kg2c_df['xrefs']:
    if pd.notna(xref_value):
        matches = uniprot_pattern.findall(str(xref_value))
        for match in matches:
            kg2c_uniprot_with_isoform.add(match)
            # Remove isoform suffix if present
            base_id = match.split('-')[0]
            kg2c_uniprot_base.add(base_id)

print(f"   KG2c UniProt IDs (with isoforms): {len(kg2c_uniprot_with_isoform)}")
print(f"   KG2c UniProt IDs (base only): {len(kg2c_uniprot_base)}")

# Get Arivale IDs
arivale_uniprot = set(arivale_df['uniprot'].dropna().astype(str))
print(f"\n3. Arivale UniProt IDs: {len(arivale_uniprot)}")

# Check if Arivale has any isoform suffixes
arivale_with_isoform = [aid for aid in arivale_uniprot if '-' in aid]
print(f"   Arivale IDs with isoform suffix: {len(arivale_with_isoform)}")
if arivale_with_isoform:
    print(f"   Examples: {arivale_with_isoform[:5]}")

# Compare matching with and without isoform consideration
print("\n4. Matching comparison:")
print("   a) Exact matching (current approach):")
exact_matches = arivale_uniprot & kg2c_uniprot_with_isoform
print(f"      Matches: {len(exact_matches)} ({len(exact_matches)/len(arivale_uniprot)*100:.1f}%)")

print("\n   b) Base ID matching (ignoring isoforms):")
base_matches = arivale_uniprot & kg2c_uniprot_base
print(f"      Matches: {len(base_matches)} ({len(base_matches)/len(arivale_uniprot)*100:.1f}%)")

# Show improvement
improvement = len(base_matches) - len(exact_matches)
print(f"\n   ✨ IMPROVEMENT: {improvement} additional matches")
print(f"      New match rate: {len(base_matches)/len(arivale_uniprot)*100:.1f}%")

# Show examples of new matches
if improvement > 0:
    new_matches = base_matches - exact_matches
    print(f"\n5. Examples of new matches (base IDs that match):")
    for aid in list(new_matches)[:10]:
        # Find the KG2c isoform version
        kg2c_versions = [kid for kid in kg2c_uniprot_with_isoform if kid.startswith(aid)]
        print(f"   Arivale: {aid} -> KG2c: {kg2c_versions}")

print("\n" + "=" * 60)
print("💡 RECOMMENDATION:")
if improvement > 100:  # Significant improvement
    print("   We should implement base ID matching (ignore isoform suffixes)")
    print("   This is standard practice when one dataset lacks isoform specificity")
else:
    print("   Isoform matching doesn't significantly improve coverage")
    print("   The low match rate is due to different protein coverage in datasets")
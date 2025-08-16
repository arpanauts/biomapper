#!/usr/bin/env python3
"""
Investigate why Q6EMK4 didn't map
"""
import pandas as pd
import re

print("🔍 INVESTIGATING Q6EMK4 MAPPING ISSUE")
print("=" * 60)

# Check if Q6EMK4 is in Arivale
print("\n1. Checking Arivale dataset...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')
q6emk4_in_arivale = arivale_df[arivale_df['uniprot'] == 'Q6EMK4']
print(f"   Q6EMK4 in Arivale: {len(q6emk4_in_arivale) > 0}")
if len(q6emk4_in_arivale) > 0:
    print(f"   Row data: {q6emk4_in_arivale.iloc[0].to_dict()}")

# Check KG2.10.2c
print("\n2. Checking KG2.10.2c dataset...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')

# Search in id column
print("\n   a) Searching in 'id' column...")
id_matches = kg2c_df[kg2c_df['id'].str.contains('Q6EMK4', na=False)]
print(f"      Found in id column: {len(id_matches)} times")
if len(id_matches) > 0:
    for idx, row in id_matches.iterrows():
        print(f"      - {row['id']}")

# Search in xrefs column
print("\n   b) Searching in 'xrefs' column...")
xref_matches = kg2c_df[kg2c_df['xrefs'].str.contains('Q6EMK4', na=False)]
print(f"      Found in xrefs column: {len(xref_matches)} times")
if len(xref_matches) > 0:
    for idx, row in xref_matches.head(3).iterrows():
        # Extract the UniProt reference
        xref_str = str(row['xrefs'])
        if 'UniProtKB:Q6EMK4' in xref_str:
            print(f"      Row {idx}: id='{row['id']}', name='{row['name']}'")
            print(f"         xrefs contains: UniProtKB:Q6EMK4")

# Test our extraction regex
print("\n3. Testing UniProt extraction regex...")
uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

test_xrefs = "PR:Q6EMK4||UMLS:C1505435||UMLS:C1823617||UniProtKB:Q6EMK4"
matches = uniprot_pattern.findall(test_xrefs)
print(f"   Test string: {test_xrefs}")
print(f"   Extracted: {matches}")

# Check specific row
print("\n4. Checking NCBIGene:114990 row (VASN)...")
vasn_row = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
if len(vasn_row) > 0:
    xrefs = str(vasn_row.iloc[0]['xrefs'])
    print(f"   xrefs field: {xrefs[:100]}...")
    
    # Apply our extraction
    extracted = uniprot_pattern.findall(xrefs)
    print(f"   UniProt IDs extracted: {extracted}")
    
    # Check if Q6EMK4 was extracted
    if 'Q6EMK4' in extracted:
        print("   ✅ Q6EMK4 was extracted correctly")
    else:
        print("   ❌ Q6EMK4 was NOT extracted")
        
        # Debug the exact pattern
        if 'UniProtKB:Q6EMK4' in xrefs:
            print("   But 'UniProtKB:Q6EMK4' IS in the xrefs!")
            # Try simpler pattern
            simple_pattern = re.compile(r'UniProtKB:([A-Z][0-9][A-Z0-9]{3}[0-9])')
            simple_matches = simple_pattern.findall(xrefs)
            print(f"   Simple pattern extracts: {simple_matches}")

# Load the actual mapping results
print("\n5. Checking actual mapping results...")
results_df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)

# Check if Q6EMK4 is in the results
q6emk4_results = results_df[results_df['uniprot'] == 'Q6EMK4']
print(f"   Q6EMK4 in results: {len(q6emk4_results)} rows")
if len(q6emk4_results) > 0:
    print(f"   Match status: {q6emk4_results.iloc[0]['match_status']}")
    print(f"   Match type: {q6emk4_results.iloc[0].get('match_type', 'N/A')}")

print("\n" + "=" * 60)
print("💡 ANALYSIS:")
if len(xref_matches) > 0 and len(q6emk4_results) > 0 and q6emk4_results.iloc[0]['match_status'] == 'source_only':
    print("   Q6EMK4 IS in KG2c (in xrefs) but wasn't matched!")
    print("   This suggests an issue with the xrefs extraction pattern.")
#!/usr/bin/env python3
"""
Check if Q6EMK4 is being extracted from KG2c xrefs
"""
import pandas as pd
import re

# Load KG2c
print("Loading KG2c...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')

# Find the NCBIGene:114990 row
vasn_rows = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
print(f"\nFound {len(vasn_rows)} rows with id='NCBIGene:114990'")

if len(vasn_rows) > 0:
    row = vasn_rows.iloc[0]
    xrefs = str(row['xrefs'])
    
    print(f"\nRow index: {vasn_rows.index[0]}")
    print(f"xrefs field (first 200 chars): {xrefs[:200]}...")
    
    # Check if Q6EMK4 is in there
    if 'Q6EMK4' in xrefs:
        print(f"\n✅ Q6EMK4 found in xrefs")
        
        # Try the extraction pattern
        pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
        matches = pattern.findall(xrefs)
        
        print(f"\nExtracted UniProt IDs: {matches}")
        
        if 'Q6EMK4' in matches:
            print("✅ Q6EMK4 successfully extracted")
        else:
            print("❌ Q6EMK4 NOT extracted by pattern")
            
            # Debug the pattern
            if 'UniProtKB:Q6EMK4' in xrefs:
                print("\n'UniProtKB:Q6EMK4' is in xrefs")
                # Try simpler pattern
                simple = re.findall(r'UniProtKB:([A-Z0-9]+)', xrefs)
                print(f"Simple pattern extracts: {simple}")
    else:
        print(f"\n❌ Q6EMK4 NOT in xrefs")

# Also check if there's a different encoding
print("\n\nChecking all rows with Q6EMK4 in xrefs:")
q6_rows = kg2c_df[kg2c_df['xrefs'].str.contains('Q6EMK4', na=False)]
print(f"Found {len(q6_rows)} rows with Q6EMK4 in xrefs")

for idx, row in q6_rows.head(3).iterrows():
    print(f"\nRow {idx}:")
    print(f"  id: {row['id']}")
    print(f"  name: {row['name']}")
    xrefs_substr = str(row['xrefs'])
    # Find Q6EMK4 position
    pos = xrefs_substr.find('Q6EMK4')
    if pos >= 0:
        context = xrefs_substr[max(0, pos-20):min(len(xrefs_substr), pos+30)]
        print(f"  Context around Q6EMK4: ...{context}...")
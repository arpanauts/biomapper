#!/usr/bin/env python3
"""
Debug the xrefs extraction in the actual matching process
"""
import pandas as pd
import re

print("🔍 DEBUGGING XREFS EXTRACTION")
print("=" * 60)

# Load the datasets
print("\n1. Loading datasets...")
arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                         sep='\t', comment='#')
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')

print(f"   Arivale: {len(arivale_df)} rows")
print(f"   KG2c: {len(kg2c_df)} rows")

# Simulate what the action does
print("\n2. Simulating the extraction logic from merge_with_uniprot_resolution.py...")

# Build index of extracted UniProt IDs from target (KG2c)
target_uniprot_to_indices = {}
xref_extraction_count = 0

for target_idx, target_row in kg2c_df.iterrows():
    target_id = str(target_row['id'])
    
    # Extract UniProt ID if the ID column contains UniProtKB prefix
    if target_id.startswith('UniProtKB:'):
        uniprot_id = target_id.replace('UniProtKB:', '')
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
    
    # Extract from xrefs column
    xref_value = str(target_row.get('xrefs', ''))
    if xref_value and xref_value != 'nan':
        # This is the exact pattern from the action
        uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
        for match in uniprot_pattern.finditer(xref_value):
            uniprot_id = match.group(1)
            xref_extraction_count += 1
            
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
    
    # Show progress for first 10000 rows
    if target_idx > 0 and target_idx % 10000 == 0:
        print(f"   Processed {target_idx} rows...")
        if target_idx >= 10000:  # Just check first 10k for debugging
            break

print(f"\n3. Extraction results (first 10k rows):")
print(f"   Total unique UniProt IDs extracted: {len(target_uniprot_to_indices)}")
print(f"   UniProt IDs extracted from xrefs: {xref_extraction_count}")

# Check if Q6EMK4 was extracted
print("\n4. Checking for Q6EMK4...")
if 'Q6EMK4' in target_uniprot_to_indices:
    print("   ✅ Q6EMK4 IS in the index!")
    entries = target_uniprot_to_indices['Q6EMK4']
    print(f"   Found in {len(entries)} rows:")
    for idx, row in entries[:3]:
        print(f"     - Row {idx}: id='{row['id']}', name='{row['name']}'")
else:
    print("   ❌ Q6EMK4 NOT in the index!")
    
    # Debug: Check the specific row we know has it
    vasn_row = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
    if len(vasn_row) > 0:
        print("\n   Debugging NCBIGene:114990 row:")
        row_idx = vasn_row.index[0]
        print(f"   Row index: {row_idx}")
        if row_idx <= 10000:
            xrefs = str(vasn_row.iloc[0]['xrefs'])
            print(f"   xrefs: {xrefs[:200]}...")
            
            # Test extraction
            uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
            matches = uniprot_pattern.findall(xrefs)
            print(f"   Pattern matches: {matches}")

# Now check with full dataset
print("\n5. Processing FULL dataset to find Q6EMK4...")
target_uniprot_full = {}
for target_idx, target_row in kg2c_df.iterrows():
    # Only check xrefs for the specific row we know has Q6EMK4
    if target_row['id'] == 'NCBIGene:114990':
        xref_value = str(target_row.get('xrefs', ''))
        print(f"   Processing row {target_idx} (NCBIGene:114990)")
        print(f"   xrefs: {xref_value[:100]}...")
        
        uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
        matches = uniprot_pattern.findall(xref_value)
        print(f"   Extracted UniProt IDs: {matches}")
        
        if 'Q6EMK4' in matches:
            print("   ✅ Q6EMK4 extracted successfully!")
        else:
            print("   ❌ Q6EMK4 NOT extracted!")
            
            # Try different patterns
            print("\n   Testing alternative patterns:")
            
            # Pattern 1: Just UniProtKB:
            pattern1 = re.compile(r'UniProtKB:([A-Z0-9]+)')
            matches1 = pattern1.findall(xref_value)
            print(f"   Pattern 'UniProtKB:([A-Z0-9]+)': {matches1}")
            
            # Pattern 2: More flexible
            pattern2 = re.compile(r'UniProtKB:([A-Z][0-9][A-Z0-9]+)')
            matches2 = pattern2.findall(xref_value)
            print(f"   Pattern 'UniProtKB:([A-Z][0-9][A-Z0-9]+)': {matches2}")
        
        break
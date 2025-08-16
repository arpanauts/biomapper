#!/usr/bin/env python3
"""
Test that the full extraction processes all rows including Q6EMK4
"""
import pandas as pd
import re
import time

print("🔍 TESTING FULL EXTRACTION WITH ALL ROWS")
print("=" * 60)

# Load KG2c dataset
print("\n1. Loading KG2c dataset...")
kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')
print(f"   Total rows: {len(kg2c_df)}")

# Find the row with Q6EMK4
vasn_row = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990']
if len(vasn_row) > 0:
    print(f"   NCBIGene:114990 found at index: {vasn_row.index[0]}")
else:
    print("   NCBIGene:114990 NOT FOUND!")

# Build the full index (simulating the action)
print("\n2. Building full index (this may take a minute)...")
start_time = time.time()

target_uniprot_to_indices = {}
xref_extraction_count = 0
rows_with_xrefs = 0
rows_processed = 0

uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')

for target_idx, target_row in kg2c_df.iterrows():
    rows_processed += 1
    
    # Process ID column
    target_id = str(target_row['id'])
    if target_id.startswith('UniProtKB:'):
        uniprot_id = target_id.replace('UniProtKB:', '')
        # Store with isoform
        if uniprot_id not in target_uniprot_to_indices:
            target_uniprot_to_indices[uniprot_id] = []
        target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
        
        # Also store base ID
        base_id = uniprot_id.split('-')[0]
        if base_id != uniprot_id:
            if base_id not in target_uniprot_to_indices:
                target_uniprot_to_indices[base_id] = []
            target_uniprot_to_indices[base_id].append((target_idx, target_row))
    
    # Process xrefs column
    xref_value = str(target_row.get('xrefs', ''))
    if xref_value and xref_value != 'nan':
        rows_with_xrefs += 1
        matches = uniprot_pattern.findall(xref_value)
        if matches:
            xref_extraction_count += len(matches)
            for uniprot_id in matches:
                # Store with isoform
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
                
                # Also store base ID
                base_id = uniprot_id.split('-')[0]
                if base_id != uniprot_id:
                    if base_id not in target_uniprot_to_indices:
                        target_uniprot_to_indices[base_id] = []
                    target_uniprot_to_indices[base_id].append((target_idx, target_row))
    
    # Check if this is the Q6EMK4 row
    if target_id == 'NCBIGene:114990':
        print(f"\n   Processing NCBIGene:114990 at index {target_idx}:")
        print(f"   xrefs: {xref_value[:100]}...")
        matches = uniprot_pattern.findall(xref_value)
        print(f"   Extracted UniProt IDs: {matches}")
    
    # Progress indicator
    if rows_processed % 50000 == 0:
        elapsed = time.time() - start_time
        print(f"   Processed {rows_processed:,} rows ({elapsed:.1f}s)...")

elapsed = time.time() - start_time
print(f"\n3. Index built in {elapsed:.1f} seconds")
print(f"   Total rows processed: {rows_processed:,}")
print(f"   Rows with xrefs: {rows_with_xrefs:,}")
print(f"   UniProt IDs from xrefs: {xref_extraction_count:,}")
print(f"   Unique UniProt IDs in index: {len(target_uniprot_to_indices):,}")

# Check for Q6EMK4
print("\n4. Checking for Q6EMK4 in index...")
if 'Q6EMK4' in target_uniprot_to_indices:
    print(f"   ✅ Q6EMK4 IS in the index!")
    entries = target_uniprot_to_indices['Q6EMK4']
    print(f"   Found in {len(entries)} rows:")
    for idx, row in entries[:3]:
        print(f"     - Row {idx}: {row['id']} ({row['name']})")
else:
    print(f"   ❌ Q6EMK4 NOT in the index!")

print("\n" + "=" * 60)
print("💡 SUMMARY:")
if 'Q6EMK4' in target_uniprot_to_indices:
    print("   Q6EMK4 was successfully extracted and indexed.")
    print("   The issue must be in the matching logic or result creation.")
else:
    print("   Q6EMK4 was NOT extracted from the full dataset!")
    print("   This is the root cause of the matching issue.")
#!/usr/bin/env python3
"""Verify that storing DataFrame row references causes the bug"""

import pandas as pd
import gc

print("TESTING STALE REFERENCE HYPOTHESIS")
print("=" * 80)

# Create a simple test
df = pd.DataFrame({
    'id': ['A', 'B', 'C'],
    'value': [1, 2, 3]
})

print("Original DataFrame:")
print(df)

# Store references to rows
stored_rows = []
for idx, row in df.iterrows():
    stored_rows.append((idx, row))
    print(f"Stored row {idx}: {row['id']} = {row['value']}")

print("\nStored row references:")
for idx, row in stored_rows:
    print(f"  {idx}: {row['id']} = {row['value']}")

# Now iterate again (simulating the second loop)
print("\nIterating again (second loop)...")
for idx, row in df.iterrows():
    # This might affect the stored references
    pass

# Force garbage collection
gc.collect()

print("\nChecking stored references after second iteration:")
for idx, row in stored_rows:
    print(f"  {idx}: {row['id']} = {row['value']}")

# Now test with actual data
print("\n" + "=" * 80)
print("TESTING WITH ACTUAL DATA")
print("=" * 80)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv',
    nrows=1000  # Just test with first 1000 rows
)

# Build index storing row references (BAD)
index_with_refs = {}
for idx, row in target_df.iterrows():
    if idx < 10:  # Just store first 10
        index_with_refs[idx] = row

# Build index storing row copies (GOOD)
index_with_copies = {}
for idx, row in target_df.iterrows():
    if idx < 10:  # Just store first 10
        index_with_copies[idx] = row.copy()  # Make a copy!

# Build index storing just the needed data (BEST)
index_with_data = {}
for idx, row in target_df.iterrows():
    if idx < 10:  # Just store first 10
        index_with_data[idx] = {
            'id': row['id'],
            'name': row['name'],
            'xrefs': row.get('xrefs', '')
        }

print("Memory usage comparison:")
import sys
print(f"  With references: {sys.getsizeof(index_with_refs)} bytes")
print(f"  With copies: {sys.getsizeof(index_with_copies)} bytes")
print(f"  With data dict: {sys.getsizeof(index_with_data)} bytes")

# Check if references are still valid
print("\nChecking if stored references are still valid:")
for idx in range(min(3, len(index_with_refs))):
    ref_id = index_with_refs[idx]['id']
    copy_id = index_with_copies[idx]['id']
    data_id = index_with_data[idx]['id']
    print(f"  Row {idx}: ref={ref_id}, copy={copy_id}, data={data_id}")
    if ref_id != copy_id or ref_id != data_id:
        print("    ⚠️ MISMATCH DETECTED!")
#!/usr/bin/env python3
"""Test if DataFrame conversion from list of dicts causes the bug"""

import pandas as pd

print("TESTING DATAFRAME CONVERSION ISSUE")
print("=" * 80)

# Simulate how data comes from context (list of dicts)
source_data = [
    {'uniprot': 'Q6EMK4', 'gene': 'VASN'},
    {'uniprot': 'P12345', 'gene': 'TEST1'},
    {'uniprot': 'O00533', 'gene': 'TEST2'},
]

print("Original source data (list of dicts):")
for i, row in enumerate(source_data):
    print(f"  {i}: {row}")

# Convert to DataFrame (as the action does)
source_df = pd.DataFrame(source_data)

print("\nConverted to DataFrame:")
print(source_df)

print("\nDataFrame index:")
print(f"  Type: {type(source_df.index)}")
print(f"  Values: {list(source_df.index)}")

# Find Q6EMK4
q6_rows = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_rows) > 0:
    q6_idx = q6_rows.index[0]
    print(f"\nQ6EMK4 found at index: {q6_idx}")
    print(f"  Index type: {type(q6_idx)}")
    
    # Simulate matching
    matches = []
    for idx, row in source_df.iterrows():
        if row['uniprot'] == 'Q6EMK4':
            matches.append({
                'source_idx': idx,
                'source_id': row['uniprot']
            })
            print(f"\nCreated match with source_idx={idx} (type: {type(idx)})")
    
    # Build matched indices
    matched_source_indices = set()
    for match in matches:
        matched_source_indices.add(match['source_idx'])
    
    print(f"\nMatched indices: {matched_source_indices}")
    print(f"Q6EMK4 index {q6_idx} in matched set: {q6_idx in matched_source_indices}")

# Now test with a LARGE dataset to see if behavior changes
print("\n" + "=" * 80)
print("TESTING WITH LARGE DATASET")

# Create a large list of dicts (simulating production)
large_data = []
for i in range(1000):
    large_data.append({'uniprot': f'P{i:05d}', 'gene': f'GENE{i}'})

# Insert Q6EMK4 at position 80 (like in production)
large_data[80] = {'uniprot': 'Q6EMK4', 'gene': 'VASN'}

print(f"Created {len(large_data)} rows with Q6EMK4 at position 80")

# Convert to DataFrame
large_df = pd.DataFrame(large_data)

# Find Q6EMK4
q6_rows = large_df[large_df['uniprot'] == 'Q6EMK4']
if len(q6_rows) > 0:
    q6_idx = q6_rows.index[0]
    print(f"Q6EMK4 found at index: {q6_idx}")
    
    # Check if the index matches the position
    if q6_idx == 80:
        print("✅ Index matches expected position")
    else:
        print(f"❌ Index mismatch! Expected 80, got {q6_idx}")
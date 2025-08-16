#!/usr/bin/env python3
"""Check if the DataFrame index is causing the issue"""

import pandas as pd

# Load the actual target dataframe
target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

print("TARGET DATAFRAME INDEX ANALYSIS")
print("=" * 80)

print(f"DataFrame shape: {target_df.shape}")
print(f"Index type: {type(target_df.index)}")
print(f"Index dtype: {target_df.index.dtype}")
print(f"Index is sequential: {target_df.index.equals(pd.RangeIndex(len(target_df)))}")
print(f"First 10 index values: {list(target_df.index[:10])}")
print(f"Last 10 index values: {list(target_df.index[-10:])}")

# Check if index matches row position
mismatches = []
for i, (idx, row) in enumerate(target_df.head(100).iterrows()):
    if i != idx:
        mismatches.append((i, idx))

if mismatches:
    print(f"\n⚠️ WARNING: Index doesn't match row position!")
    print(f"First 5 mismatches: {mismatches[:5]}")
else:
    print(f"\n✅ Index matches row position (checked first 100 rows)")

# Now check the source DataFrame
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

print("\n" + "=" * 80)
print("SOURCE DATAFRAME INDEX ANALYSIS")
print("=" * 80)

print(f"DataFrame shape: {source_df.shape}")
print(f"Index type: {type(source_df.index)}")
print(f"Index dtype: {source_df.index.dtype}")
print(f"Index is sequential: {source_df.index.equals(pd.RangeIndex(len(source_df)))}")
print(f"First 10 index values: {list(source_df.index[:10])}")

# Check Q6EMK4's index
q6_rows = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_rows) > 0:
    print(f"\nQ6EMK4 index value: {q6_rows.index[0]}")
    print(f"Q6EMK4 position in DataFrame: {source_df.index.get_loc(q6_rows.index[0])}")

# Check what happens when we iterate
print("\n" + "=" * 80)
print("ITERATION BEHAVIOR")
print("=" * 80)

print("First 5 rows via iterrows():")
for i, (idx, row) in enumerate(source_df.head(5).iterrows()):
    print(f"  Loop iteration {i}: idx={idx}, type={type(idx)}, uniprot={row['uniprot']}")

# The key insight: if matches are stored with DataFrame index but compared
# with sequential position, we'd have a mismatch!
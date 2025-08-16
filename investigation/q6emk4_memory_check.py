#!/usr/bin/env python3
"""Check if memory or state issues affect Q6EMK4"""

import pandas as pd
import psutil
import gc

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

print("Memory and State Analysis for Q6EMK4")
print("=" * 60)

# Check initial memory
initial_memory = get_memory_usage()
print(f"Initial memory: {initial_memory:.1f} MB")

# Load datasets
print("\nLoading datasets...")
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)
print(f"After loading source: {get_memory_usage():.1f} MB")

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)
print(f"After loading target: {get_memory_usage():.1f} MB")

# Check if Q6EMK4 is at a problematic position
q6_rows = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_rows) > 0:
    q6_idx = q6_rows.index[0]
    print(f"\nQ6EMK4 is at index: {q6_idx}")
    print(f"Total source rows: {len(source_df)}")
    print(f"Position in dataset: {q6_idx/len(source_df)*100:.1f}%")
    
    # Check if there's something special about row 80
    print(f"\nChecking rows around index {q6_idx}:")
    for i in range(max(0, q6_idx-2), min(len(source_df), q6_idx+3)):
        row = source_df.iloc[i]
        print(f"  Row {i}: {row['uniprot']}")
else:
    print("\nQ6EMK4 not found in source dataset!")
    
# Check for duplicates
print(f"\nChecking for duplicates:")
uniprot_counts = source_df['uniprot'].value_counts()
duplicates = uniprot_counts[uniprot_counts > 1]
print(f"  Duplicate UniProt IDs: {len(duplicates)}")
if 'Q6EMK4' in duplicates.index:
    print(f"  Q6EMK4 appears {duplicates['Q6EMK4']} times!")
else:
    print(f"  Q6EMK4 appears only once (no duplicates)")

# Force garbage collection and check memory
gc.collect()
print(f"\nAfter garbage collection: {get_memory_usage():.1f} MB")
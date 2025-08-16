#!/usr/bin/env python3
"""
Check the actual match statistics from the results
"""
import pandas as pd

print("📊 CHECKING MATCH STATISTICS")
print("=" * 60)

# Load results
print("\nLoading results...")
df = pd.read_csv('/tmp/biomapper_results/protein_mapping_results.csv', low_memory=False)

print(f"Total rows: {len(df):,}")

# Check match status column
if 'match_status' in df.columns:
    print("\nMatch status distribution:")
    status_counts = df['match_status'].value_counts()
    for status, count in status_counts.items():
        print(f"  {status}: {count:,}")
    
    # Calculate match rate
    matched = df[df['match_status'] == 'matched']
    unique_matched_arivale = matched['uniprot'].nunique()
    total_arivale = df[df['match_status'].notna()]['uniprot'].nunique()
    
    print(f"\nUnique Arivale proteins:")
    print(f"  Total: {total_arivale}")
    print(f"  Matched: {unique_matched_arivale}")
    print(f"  Match rate: {unique_matched_arivale/total_arivale*100:.1f}%")
else:
    print("\n⚠️  No 'match_status' column found")
    print("Available columns:", list(df.columns)[:10])

# Check for match_type
if 'match_type' in df.columns:
    print("\nMatch type distribution:")
    match_types = df[df['match_type'].notna()]['match_type'].value_counts()
    for mtype, count in match_types.items():
        print(f"  {mtype}: {count:,}")

print("\n" + "=" * 60)
print("✅ Analysis complete")
#!/usr/bin/env python3
"""
Analyze the RefMet CSV file to understand the structure and available mappings.
"""

import pandas as pd
import sys
from pathlib import Path

# Path to RefMet CSV
refmet_path = Path('data/refmet/refmet.csv')

if not refmet_path.exists():
    print(f"Error: RefMet file not found at {refmet_path}")
    sys.exit(1)

print(f"Reading RefMet CSV file from {refmet_path}...")
df = pd.read_csv(refmet_path)

# Basic info
print(f"\nRefMet CSV Overview:")
print(f"Total entries: {len(df)}")
print(f"Columns: {', '.join(df.columns)}")

# Count non-null values for each column
print("\nCompleteness of data (non-null values):")
for column in df.columns:
    count = df[column].count()
    percentage = (count / len(df)) * 100
    print(f"{column}: {count} ({percentage:.2f}%)")

# Check for unique values in ID columns
print("\nUnique values in ID columns:")
for column in ['refmet_id', 'pubchem_cid', 'chebi_id', 'hmdb_id', 'lipidmaps_id', 'kegg_id', 'inchi_key']:
    if column in df.columns:
        unique_count = df[column].nunique()
        print(f"{column}: {unique_count} unique values")

# Sample data for first few rows
print("\nSample data (first 5 rows):")
print(df.head().to_string())

# Sample data for a few complete rows (with most mappings)
print("\nSample rows with most complete mappings:")
# Count non-empty fields per row
df['mapping_count'] = df[['pubchem_cid', 'chebi_id', 'hmdb_id', 'lipidmaps_id', 'kegg_id', 'inchi_key']].notna().sum(axis=1)
# Get top 5 rows with most mappings
top_mappings = df.sort_values('mapping_count', ascending=False).head(5)
print(top_mappings.to_string())

# Check distribution of super_class, main_class, and sub_class
print("\nMost common super_class categories (top 10):")
print(df['super_class'].value_counts().head(10))

print("\nMost common main_class categories (top 10):")
print(df['main_class'].value_counts().head(10))

# Additional mappings available in the file
print("\nMapping statistics for external databases:")
for db in ['pubchem_cid', 'chebi_id', 'hmdb_id', 'lipidmaps_id', 'kegg_id']:
    if db in df.columns:
        mapped_count = df[db].notna().sum()
        percentage = (mapped_count / len(df)) * 100
        print(f"{db}: {mapped_count} mappings ({percentage:.2f}%)")

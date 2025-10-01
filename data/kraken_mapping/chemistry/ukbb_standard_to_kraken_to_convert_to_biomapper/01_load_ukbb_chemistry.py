#!/usr/bin/env python3
"""
Proto-action: Load and clean UKBB clinical chemistry data
This is a STANDALONE script, not a biomapper action

Loads UKBB chemistry metadata and filters/cleans for actual clinical tests.
"""
import pandas as pd
import re
from pathlib import Path

# Input file path
INPUT_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/ukbb_chemistry.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "ukbb_chemistry_clean.tsv"

def normalize_field_name(field_name):
    """
    Normalize UKBB field names for chemistry test matching.
    Remove vendor prefixes, standardize units, clean formatting.
    """
    if pd.isna(field_name):
        return ""

    name = str(field_name).lower().strip()

    # Remove UKBB field ID prefixes
    name = re.sub(r'^field\s+\d+\s*', '', name, flags=re.IGNORECASE)

    # Remove common metadata suffixes that aren't part of the test name
    metadata_suffixes = [
        'freeze-thaw cycles',
        'acquisition time',
        'device id',
        'acquisition route',
        'batch',
        'measurement date',
        'measurement time'
    ]

    for suffix in metadata_suffixes:
        name = re.sub(rf'\s*{re.escape(suffix)}\s*$', '', name, flags=re.IGNORECASE)

    # Standardize common chemistry test patterns
    name = re.sub(r'\b(leukocyte|leucocyte)\b', 'white blood cell', name)
    name = re.sub(r'\berythrocyte\b', 'red blood cell', name)
    name = re.sub(r'\bthrombocyte\b', 'platelet', name)

    # Clean up whitespace
    name = ' '.join(name.split())

    return name.title() if name else ""

def is_chemistry_test(row):
    """
    Determine if a UKBB field represents an actual chemistry test
    (vs metadata, administrative fields, etc.)
    """
    field_name = str(row['field_name']).lower()
    data_type = str(row.get('data_type', '')).lower()

    # Skip obvious metadata fields
    metadata_patterns = [
        'freeze-thaw cycles',
        'acquisition time',
        'device id',
        'acquisition route',
        'batch',
        'invitation',
        'date sent',
        'measurement date',
        'measurement time',
        'field \\d+$'  # Generic field entries without descriptive names
    ]

    for pattern in metadata_patterns:
        if re.search(pattern, field_name, re.IGNORECASE):
            return False

    # Include fields that are likely actual chemistry tests
    chemistry_indicators = [
        'count',
        'level',
        'concentration',
        'glucose',
        'cholesterol',
        'protein',
        'albumin',
        'creatinine',
        'urea',
        'bilirubin',
        'enzyme',
        'hormone',
        'vitamin',
        'mineral',
        'blood',
        'serum',
        'plasma',
        'urine'
    ]

    # Must be continuous numeric data for most chemistry tests
    if data_type in ['continuous', 'integer']:
        # Check if field name contains chemistry indicators
        for indicator in chemistry_indicators:
            if indicator in field_name:
                return True

    # Also include categorical tests that might be chemistry-related
    if data_type == 'categorical':
        categorical_chemistry = ['blood group', 'blood type']
        for indicator in categorical_chemistry:
            if indicator in field_name:
                return True

    return False

def main():
    """Load, filter, and clean UKBB chemistry data."""
    print("Loading UKBB chemistry data...")

    # Load the data
    df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(df)} total UKBB fields")

    # Filter to chemistry tests only
    print("Filtering to actual chemistry tests...")
    chemistry_mask = df.apply(is_chemistry_test, axis=1)
    chemistry_df = df[chemistry_mask].copy()

    print(f"Found {len(chemistry_df)} chemistry test fields")

    # Clean and normalize field names
    print("Normalizing field names...")
    chemistry_df['normalized_field_name'] = chemistry_df['field_name'].apply(normalize_field_name)

    # Add useful columns for downstream processing
    chemistry_df['original_field_name'] = chemistry_df['field_name']
    chemistry_df['field_id_str'] = chemistry_df['field_id'].astype(str)

    # Remove rows where normalization resulted in empty names
    chemistry_df = chemistry_df[chemistry_df['normalized_field_name'].str.len() > 0].copy()

    print(f"After cleaning: {len(chemistry_df)} chemistry tests")

    # Sort by field ID for consistency
    chemistry_df = chemistry_df.sort_values('field_id')

    # Save the cleaned data
    OUTPUT_DIR.mkdir(exist_ok=True)
    chemistry_df.to_csv(OUTPUT_FILE, sep='\t', index=False)

    print(f"Saved cleaned chemistry data to {OUTPUT_FILE}")
    print(f"Sample fields:")
    for _, row in chemistry_df.head(10).iterrows():
        print(f"  {row['field_id']}: {row['normalized_field_name']}")

if __name__ == "__main__":
    main()
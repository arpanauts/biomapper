#!/usr/bin/env python3
"""
Proto-action: Load and filter Nightingale clinical chemistry biomarkers
This is a STANDALONE script, not a biomapper action

Extracts clinical chemistry biomarkers from Nightingale data that already
has LOINC mappings assigned via LLM enrichment process.
"""
import pandas as pd
from pathlib import Path
import sys

# Input data path
NIGHTINGALE_FILE = "/home/ubuntu/biomapper/data/harmonization/nightingale/nightingale_metadata_enrichment_to_convert_to_biomapper/output/nightingale_complete_with_loinc.tsv"

# Output configuration
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Clinical chemistry biomarkers to extract
CLINICAL_CHEMISTRY_PATTERNS = [
    'Glucose', 'glucose',
    'Creatinine', 'creatinine',
    'Albumin', 'albumin',
    'Total protein', 'total protein',
    'Calcium', 'calcium',
    'Bilirubin', 'bilirubin',
    'ALP', 'alp', 'alkaline phosphatase',
    'ALT', 'alt', 'alanine',
    'AST', 'ast', 'aspartate',
    'GGT', 'ggt', 'gamma',
    'CRP', 'crp', 'c-reactive',
    'Sodium', 'sodium',
    'Potassium', 'potassium',
    'Chloride', 'chloride',
    'Urea', 'urea'
]

def main():
    print("Loading Nightingale data with LOINC mappings...")

    # Check if input file exists
    if not Path(NIGHTINGALE_FILE).exists():
        print(f"ERROR: Input file not found: {NIGHTINGALE_FILE}")
        sys.exit(1)

    # Load the Nightingale data
    try:
        df = pd.read_csv(NIGHTINGALE_FILE, sep='\t', low_memory=False)
        print(f"Loaded {len(df)} total Nightingale biomarkers")
    except Exception as e:
        print(f"ERROR loading file: {e}")
        sys.exit(1)

    # Display column information
    print(f"Columns available: {list(df.columns)}")

    # Filter for clinical chemistry biomarkers
    print("\nFiltering for clinical chemistry biomarkers...")

    # Create mask for clinical chemistry biomarkers
    clinical_mask = pd.Series([False] * len(df))

    for pattern in CLINICAL_CHEMISTRY_PATTERNS:
        # Check in Biomarker name
        mask_biomarker = df['Biomarker'].str.contains(pattern, case=False, na=False)
        # Check in Description if available
        if 'Description' in df.columns:
            mask_description = df['Description'].str.contains(pattern, case=False, na=False)
            clinical_mask |= mask_biomarker | mask_description
        else:
            clinical_mask |= mask_biomarker

    clinical_df = df[clinical_mask].copy()
    print(f"Found {len(clinical_df)} clinical chemistry biomarkers")

    # Show what we found
    if len(clinical_df) > 0:
        print("\nClinical chemistry biomarkers found:")
        for i, row in clinical_df.iterrows():
            biomarker = row['Biomarker']
            loinc_code = row.get('loinc_code', 'No LOINC')
            loinc_term = row.get('loinc_term', 'No term')
            print(f"  {biomarker} -> {loinc_code} ({loinc_term})")

    # Filter to only records with LOINC codes
    print("\nFiltering to biomarkers with LOINC codes...")
    loinc_available = clinical_df['loinc_code'].notna() & (clinical_df['loinc_code'] != 'NO_MATCH')
    clinical_with_loinc = clinical_df[loinc_available].copy()
    print(f"Found {len(clinical_with_loinc)} clinical chemistry biomarkers with LOINC codes")

    if len(clinical_with_loinc) == 0:
        print("WARNING: No clinical chemistry biomarkers found with LOINC codes!")
        # Still save the clinical biomarkers for inspection
        output_file = OUTPUT_DIR / "nightingale_clinical.tsv"
        clinical_df.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(clinical_df)} clinical biomarkers (without LOINC) to {output_file}")
    else:
        # Save the clinical chemistry biomarkers with LOINC codes
        output_file = OUTPUT_DIR / "nightingale_clinical.tsv"
        clinical_with_loinc.to_csv(output_file, sep='\t', index=False)
        print(f"Saved {len(clinical_with_loinc)} clinical chemistry biomarkers to {output_file}")

        # Show summary of LOINC codes found
        print(f"\nLOINC codes available:")
        loinc_counts = clinical_with_loinc['loinc_code'].value_counts()
        for loinc_code, count in loinc_counts.head(10).items():
            print(f"  {loinc_code}: {count} biomarker(s)")

    print("\n01_load_nightingale_clinical.py completed successfully!")

if __name__ == "__main__":
    main()
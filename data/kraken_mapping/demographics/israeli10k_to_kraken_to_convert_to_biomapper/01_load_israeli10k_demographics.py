#!/usr/bin/env python3
"""
Proto-action: Load Israeli10K demographics with LOINC mappings
This is a STANDALONE script, not a biomapper action.

Input: Israeli10K demographics with LOINC codes from harmonization
Output: Cleaned demographics data ready for Kraken mapping
"""

import pandas as pd
import numpy as np
from pathlib import Path

# File paths - Updated to use consolidated LLM reasoning from JSON files
INPUT_FILE = "/home/ubuntu/biomapper/data/harmonization/demographics/loinc_demographics_to_convert_to_biomapper/results/israeli10k_demographics_weighted_loinc_CONSOLIDATED.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "israeli10k_with_loinc.tsv"

def load_and_prepare_demographics():
    """Load Israeli10K demographics and prepare for Kraken mapping."""

    print("Loading Israeli10K demographics with LOINC mappings...")

    # Load the harmonized demographics data
    df = pd.read_csv(INPUT_FILE, sep='\t')

    print(f"Loaded {len(df)} demographic fields")
    print(f"Columns: {list(df.columns)}")

    # Apply field expansion methodology - process all fields with LOINC codes
    # All fields have valid LOINC codes, so lower confidence threshold to include all
    has_loinc = df['loinc_code'].notna() & (df['loinc_code'] != '')
    moderate_confidence = df['confidence_score'] >= 0.5  # Expanded from 0.7 to 0.5

    # Process all fields with LOINC codes and moderate confidence (includes all 20 fields)
    selected = df[has_loinc & moderate_confidence].copy()

    # Add mapping status indicator for tracking
    selected['mapping_status'] = 'Attempted'

    print(f"Selected {len(selected)} fields for mapping (expanded from {len(df[has_loinc & (df['confidence_score'] >= 0.7)])} with strict filtering):")
    print(f"  - With LOINC codes: {len(selected[selected['loinc_code'].notna()])}")
    print(f"  - Confidence >= 0.7: {len(selected[selected['confidence_score'] >= 0.7])}")
    print(f"  - Confidence >= 0.5: {len(selected[selected['confidence_score'] >= 0.5])}")
    print(f"  - Coverage improvement: {len(selected)}/20 = {100*len(selected)/20:.1f}% (vs {100*len(df[has_loinc & (df['confidence_score'] >= 0.7)])/20:.1f}% before)")

    # Add demographic categorization
    selected['demographic_category'] = selected.apply(categorize_demographic, axis=1)

    # Add population-specific notes for Israeli10K
    selected['population_specific_notes'] = selected.apply(add_population_notes, axis=1)

    # Clean and standardize field names
    selected['clean_field_name'] = selected['field_name'].str.strip().str.lower()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Save prepared data
    selected.to_csv(OUTPUT_FILE, sep='\t', index=False)

    print(f"\nSaved prepared demographics to: {OUTPUT_FILE}")
    print(f"Ready for Kraken mapping: {len(selected)} fields")

    return selected

def categorize_demographic(row):
    """Categorize demographic field based on field name and description."""
    field_name = str(row['field_name']).lower()
    description = str(row['description']).lower()

    # Physical measurements
    if any(term in field_name + description for term in ['height', 'weight', 'bmi', 'circumference', 'waist', 'hip', 'neck']):
        return 'Physical Measurements'

    # Basic demographics
    elif any(term in field_name + description for term in ['birth', 'age', 'sex', 'gender']):
        return 'Basic Demographics'

    # Collection metadata
    elif any(term in field_name + description for term in ['collection', 'timestamp', 'date', 'timezone']):
        return 'Collection Metadata'

    # Israeli-specific
    elif any(term in field_name + description for term in ['aliya', 'country_of_birth', 'birth_land']):
        return 'Population-Specific'

    # Study identifiers
    elif any(term in field_name + description for term in ['study_id', 'identifier']):
        return 'Study Identifiers'

    else:
        return 'Other Demographics'

def add_population_notes(row):
    """Add population-specific notes for Israeli10K demographics."""
    field_name = str(row['field_name']).lower()

    notes = []

    # Israeli-specific fields
    if 'aliya' in field_name:
        notes.append("Israeli immigration-specific field (year of aliyah)")

    if 'country_of_birth' in field_name or 'birth_land' in field_name:
        notes.append("May include Hebrew text; diverse immigrant population")

    # Collection considerations
    if 'timezone' in field_name:
        notes.append("Israel Standard Time (IST/IDT)")

    # Physical measurements in diverse population
    if any(term in field_name for term in ['circumference', 'bmi', 'weight', 'height']):
        notes.append("Measured in diverse Middle Eastern population")

    # Return concatenated notes or empty string
    return "; ".join(notes) if notes else ""

def main():
    """Main execution function."""
    try:
        # Load and prepare demographics
        demographics = load_and_prepare_demographics()

        # Print summary statistics
        print("\n" + "="*50)
        print("ISRAELI10K DEMOGRAPHICS PREPARATION SUMMARY")
        print("="*50)

        print(f"Total fields processed: {len(demographics)}")
        print(f"Fields with LOINC codes: {len(demographics[demographics['loinc_code'].notna()])}")

        # Category breakdown
        print("\nBy category:")
        for category in demographics['demographic_category'].value_counts().index:
            count = len(demographics[demographics['demographic_category'] == category])
            print(f"  {category}: {count}")

        # Confidence score distribution
        print(f"\nConfidence scores:")
        print(f"  Mean: {demographics['confidence_score'].mean():.3f}")
        print(f"  ≥0.8: {len(demographics[demographics['confidence_score'] >= 0.8])}")
        print(f"  ≥0.7: {len(demographics[demographics['confidence_score'] >= 0.7])}")

        print(f"\nData prepared successfully. Ready for Kraken mapping.")

    except Exception as e:
        print(f"Error processing demographics: {e}")
        raise

if __name__ == "__main__":
    main()
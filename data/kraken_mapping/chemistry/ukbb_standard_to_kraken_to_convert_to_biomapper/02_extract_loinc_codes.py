#!/usr/bin/env python3
"""
Proto-action: Extract LOINC codes for UKBB chemistry tests
This is a STANDALONE script, not a biomapper action

Maps UKBB chemistry test names to LOINC codes using fuzzy matching
and manual mappings for common tests.
"""
import pandas as pd
import re
from pathlib import Path
try:
    from fuzzywuzzy import fuzz
except ImportError:
    from rapidfuzz import fuzz

# Input/output paths
INPUT_DIR = Path(__file__).parent / "data"
INPUT_FILE = INPUT_DIR / "ukbb_chemistry_clean.tsv"
OUTPUT_FILE = INPUT_DIR / "ukbb_with_loinc.tsv"

# LOINC database path
LOINC_DB_PATH = "/procedure/data/local_data/MAPPING_ONTOLOGIES/loinc/Loinc.csv"

# Manual LOINC mappings for common chemistry tests
MANUAL_LOINC_MAPPINGS = {
    # Blood chemistry - basic metabolic panel
    'glucose': '2345-7',           # Glucose [Mass/volume] in Serum or Plasma
    'blood glucose': '2345-7',
    'sodium': '2951-2',            # Sodium [Moles/volume] in Serum or Plasma
    'potassium': '2823-3',         # Potassium [Moles/volume] in Serum or Plasma
    'chloride': '2075-0',          # Chloride [Moles/volume] in Serum or Plasma
    'co2': '2028-9',               # Carbon dioxide [Moles/volume] in Serum or Plasma
    'carbon dioxide': '2028-9',
    'urea': '3094-0',              # Blood Urea Nitrogen [Mass/volume] in Serum or Plasma
    'blood urea nitrogen': '3094-0',
    'bun': '3094-0',
    'creatinine': '2160-0',        # Creatinine [Mass/volume] in Serum or Plasma

    # Lipid panel
    'cholesterol': '2093-3',       # Cholesterol [Mass/volume] in Serum or Plasma
    'total cholesterol': '2093-3',
    'hdl cholesterol': '2085-9',   # HDL Cholesterol [Mass/volume] in Serum or Plasma
    'ldl cholesterol': '2089-1',   # LDL Cholesterol [Mass/volume] in Serum or Plasma
    'triglycerides': '2571-8',     # Triglyceride [Mass/volume] in Serum or Plasma

    # Blood count
    'white blood cell count': '6690-2',   # Leukocytes [#/volume] in Blood by Automated count
    'wbc count': '6690-2',
    'leukocyte count': '6690-2',
    'red blood cell count': '789-8',      # Red blood cells [#/volume] in Blood by Automated count
    'rbc count': '789-8',
    'erythrocyte count': '789-8',
    'hemoglobin': '718-7',         # Hemoglobin [Mass/volume] in Blood
    'hematocrit': '4544-3',        # Hematocrit [Volume Fraction] of Blood by Automated count
    'platelet count': '777-3',     # Platelets [#/volume] in Blood by Automated count

    # Liver function
    'albumin': '1751-7',           # Albumin [Mass/volume] in Serum or Plasma
    'total protein': '2885-2',     # Total protein [Mass/volume] in Serum or Plasma
    'bilirubin': '1975-2',         # Total bilirubin [Mass/volume] in Serum or Plasma
    'total bilirubin': '1975-2',
    'alt': '1742-6',               # Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma
    'alanine aminotransferase': '1742-6',
    'ast': '1920-8',               # Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma
    'aspartate aminotransferase': '1920-8',
    'alkaline phosphatase': '6768-6',  # Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma

    # Diabetes markers
    'hba1c': '4548-4',            # Hemoglobin A1c [Mass fraction] in Blood
    'hemoglobin a1c': '4548-4',
    'glycated hemoglobin': '4548-4',

    # Thyroid function
    'tsh': '3016-3',              # Thyrotropin [Units/volume] in Serum or Plasma
    'thyroid stimulating hormone': '3016-3',
    'free t4': '3024-7',          # Free thyroxine [Mass/volume] in Serum or Plasma
    'free thyroxine': '3024-7',
    't4': '3026-2',               # Thyroxine [Mass/volume] in Serum or Plasma
    'thyroxine': '3026-2',

    # Cardiac markers
    'troponin': '6598-7',         # Troponin T [Mass/volume] in Serum or Plasma
    'troponin t': '6598-7',
    'troponin i': '6597-9',       # Troponin I [Mass/volume] in Serum or Plasma
    'ck-mb': '13969-1',           # Creatine kinase MB [Mass/volume] in Serum or Plasma

    # Inflammation markers
    'c-reactive protein': '1988-5', # C reactive protein [Mass/volume] in Serum or Plasma
    'crp': '1988-5',
    'esr': '4537-7',              # Erythrocyte sedimentation rate by Westergren method
}

def normalize_test_name(test_name):
    """Normalize test name for matching."""
    if pd.isna(test_name):
        return ""

    name = str(test_name).lower().strip()

    # Remove common prefixes/suffixes
    name = re.sub(r'^(serum|plasma|blood|urine)\s+', '', name)
    name = re.sub(r'\s+(serum|plasma|blood|urine)$', '', name)
    name = re.sub(r'\s+(level|concentration|count)$', '', name)

    # Standardize punctuation
    name = re.sub(r'[,;:]', ' ', name)
    name = re.sub(r'[()]', '', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def extract_loinc_from_text(text):
    """Extract LOINC codes from text using regex patterns."""
    if pd.isna(text):
        return None

    # Look for LOINC code patterns (e.g., "1234-5")
    loinc_pattern = r'\b(\d{4,5}-\d)\b'
    matches = re.findall(loinc_pattern, str(text))

    return matches[0] if matches else None

def fuzzy_match_loinc(test_name, loinc_df, threshold=80):
    """
    Fuzzy match test name against LOINC component names.
    Returns best match above threshold.
    """
    normalized_test = normalize_test_name(test_name)

    if not normalized_test:
        return None, 0

    best_match = None
    best_score = 0
    best_loinc = None

    # Search through LOINC component names
    for _, row in loinc_df.iterrows():
        if pd.isna(row.get('COMPONENT')):
            continue

        component = normalize_test_name(row['COMPONENT'])
        long_common_name = normalize_test_name(row.get('LONG_COMMON_NAME', ''))

        # Try fuzzy matching against component and long name
        for target in [component, long_common_name]:
            if target:
                score = fuzz.ratio(normalized_test, target)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = target
                    best_loinc = row['LOINC_NUM']

    return best_loinc, best_score

def main():
    """Extract LOINC codes for UKBB chemistry tests."""
    print("Loading cleaned UKBB chemistry data...")
    ukbb_df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(ukbb_df)} chemistry tests")

    print("Loading LOINC database...")
    try:
        loinc_df = pd.read_csv(LOINC_DB_PATH, sep=',', low_memory=False)
        print(f"Loaded {len(loinc_df)} LOINC entries")
    except FileNotFoundError:
        print(f"Warning: LOINC database not found at {LOINC_DB_PATH}")
        print("Proceeding with manual mappings only...")
        loinc_df = pd.DataFrame()

    # Initialize result columns
    ukbb_df['loinc_code'] = None
    ukbb_df['mapping_method'] = None
    ukbb_df['mapping_confidence'] = 0.0

    print("Applying LOINC mappings...")

    for idx, row in ukbb_df.iterrows():
        field_name = row['normalized_field_name']
        original_name = row['original_field_name']

        loinc_code = None
        method = None
        confidence = 0.0

        # 1. Check for direct LOINC codes in text
        direct_loinc = extract_loinc_from_text(original_name)
        if direct_loinc:
            loinc_code = direct_loinc
            method = 'direct'
            confidence = 1.0

        # 2. Check manual mappings
        elif field_name:
            normalized = normalize_test_name(field_name)
            if normalized in MANUAL_LOINC_MAPPINGS:
                loinc_code = MANUAL_LOINC_MAPPINGS[normalized]
                method = 'manual'
                confidence = 0.9

        # 3. Fuzzy matching against LOINC database
        if not loinc_code and not loinc_df.empty:
            fuzzy_loinc, fuzzy_score = fuzzy_match_loinc(field_name, loinc_df, threshold=75)
            if fuzzy_loinc and fuzzy_score > 0:
                loinc_code = fuzzy_loinc
                method = 'fuzzy'
                confidence = fuzzy_score / 100.0

        # Update the dataframe
        if loinc_code:
            ukbb_df.at[idx, 'loinc_code'] = loinc_code
            ukbb_df.at[idx, 'mapping_method'] = method
            ukbb_df.at[idx, 'mapping_confidence'] = confidence

    # Calculate statistics
    total_tests = len(ukbb_df)
    mapped_tests = len(ukbb_df[ukbb_df['loinc_code'].notna()])

    print(f"\nLOINC Mapping Results:")
    print(f"Total tests: {total_tests}")
    print(f"Mapped to LOINC: {mapped_tests} ({100*mapped_tests/total_tests:.1f}%)")

    # Breakdown by method
    method_counts = ukbb_df[ukbb_df['loinc_code'].notna()]['mapping_method'].value_counts()
    for method, count in method_counts.items():
        print(f"  {method}: {count}")

    # Save results
    ukbb_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"\nSaved results to {OUTPUT_FILE}")

    # Show sample mappings
    print("\nSample LOINC mappings:")
    sample_mapped = ukbb_df[ukbb_df['loinc_code'].notna()].head(10)
    for _, row in sample_mapped.iterrows():
        print(f"  {row['field_id']}: {row['normalized_field_name']} → {row['loinc_code']} ({row['mapping_method']}, {row['mapping_confidence']:.2f})")

if __name__ == "__main__":
    main()
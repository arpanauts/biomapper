#!/usr/bin/env python3
"""
Proto-action: Load and filter Nightingale clinical chemistry biomarkers
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Input file path
INPUT_FILE = "/home/ubuntu/biomapper/data/harmonization/nightingale/nightingale_metadata_enrichment_to_convert_to_biomapper/context/nightingale_classified.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def main():
    """Load Nightingale data and filter to clinical chemistry markers."""
    print("Loading Nightingale classified data...")

    # Load the classified Nightingale data
    df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(df)} total Nightingale biomarkers")

    # Filter to clinical chemistry relevant markers
    # Include true metabolites and proteins that are clinically relevant
    clinical_chemistry_filter = (
        (df['is_true_metabolite'] == True) |
        (df['metabolite_classification'] == 'protein')
    )

    clinical_df = df[clinical_chemistry_filter].copy()
    print(f"Filtered to {len(clinical_df)} clinical chemistry markers")

    # Focus on key clinical chemistry biomarkers
    key_clinical_biomarkers = [
        'Glucose', 'Creatinine', 'Albumin', 'GlycA',
        'Ala', 'Gln', 'His', 'Ile', 'Leu', 'Val', 'Phe', 'Tyr',  # Amino acids
        'Lactate', 'Pyruvate', 'Citrate', 'bOHbutyrate', 'Acetate', 'Acetoacetate',  # Metabolites
        'Total_C', 'LDL_C', 'HDL_C', 'Total_TG'  # Key lipids often used clinically
    ]

    # Extract biomarkers that match our key clinical chemistry list
    key_df = clinical_df[clinical_df['Biomarker'].isin(key_clinical_biomarkers)].copy()
    print(f"Found {len(key_df)} key clinical chemistry biomarkers:")

    for biomarker in sorted(key_df['Biomarker'].tolist()):
        desc = key_df[key_df['Biomarker'] == biomarker]['Description'].iloc[0]
        units = key_df[key_df['Biomarker'] == biomarker]['Units'].iloc[0]
        classification = key_df[key_df['Biomarker'] == biomarker]['metabolite_classification'].iloc[0]
        print(f"  - {biomarker}: {desc} ({units}) [{classification}]")

    # Add metadata columns for downstream processing
    key_df['nightingale_biomarker_id'] = key_df['Biomarker']
    key_df['nightingale_name'] = key_df['Description']
    key_df['measurement_units'] = key_df['Units']
    key_df['biomarker_category'] = key_df['Group']
    key_df['ukb_field_id'] = key_df['UKB.Field.ID']

    # Save the filtered clinical chemistry data
    output_file = OUTPUT_DIR / "nightingale_clinical_filtered.tsv"
    OUTPUT_DIR.mkdir(exist_ok=True)
    key_df.to_csv(output_file, sep='\t', index=False)

    print(f"\nSaved {len(key_df)} clinical chemistry biomarkers to {output_file}")

    # Summary by category
    print("\nBreakdown by category:")
    category_counts = key_df['metabolite_classification'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count} biomarkers")

    # Check for ChEBI IDs (will be useful for cross-referencing)
    chebi_count = key_df['ChEBI_ID'].notna().sum()
    print(f"\nBiomarkers with ChEBI IDs: {chebi_count}/{len(key_df)}")

    # Check for PubChem IDs
    pubchem_count = key_df['PubChem_ID'].notna().sum()
    print(f"Biomarkers with PubChem IDs: {pubchem_count}/{len(key_df)}")

if __name__ == "__main__":
    main()
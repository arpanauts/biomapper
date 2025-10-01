#!/usr/bin/env python3
"""
Proto-action: Extract LOINC mappings from existing Nightingale patterns
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path
import json

# Input and output paths
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "data"

# LOINC mappings extracted from nightingale_nmr_match.py
NIGHTINGALE_LOINC_PATTERNS = {
    # Lipids and Lipoproteins
    "Total_C": {
        "description": "Total cholesterol",
        "loinc": "2093-3",
        "unit": "mmol/L",
        "category": "lipids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR-derived total cholesterol correlates well with enzymatic methods"
    },
    "LDL_C": {
        "description": "LDL cholesterol",
        "loinc": "13457-7",
        "unit": "mmol/L",
        "category": "lipids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR-derived LDL-C shows good correlation with calculated LDL-C"
    },
    "HDL_C": {
        "description": "HDL cholesterol",
        "loinc": "2085-9",
        "unit": "mmol/L",
        "category": "lipids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR HDL-C correlates well with precipitation methods"
    },
    "Total_TG": {
        "description": "Total triglycerides",
        "loinc": "2571-8",
        "unit": "mmol/L",
        "category": "lipids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR triglycerides show excellent correlation with enzymatic assays"
    },

    # Amino Acids
    "Ala": {
        "description": "Alanine",
        "loinc": "1916-6",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR provides direct measurement of alanine concentration"
    },
    "Gln": {
        "description": "Glutamine",
        "loinc": "14681-2",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR glutamine measurement complementary to traditional amino acid analysis"
    },
    "His": {
        "description": "Histidine",
        "loinc": "14682-0",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR provides quantitative histidine measurement"
    },
    "Ile": {
        "description": "Isoleucine",
        "loinc": "14684-6",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR measurement of isoleucine correlates with chromatographic methods"
    },
    "Leu": {
        "description": "Leucine",
        "loinc": "14685-3",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR leucine measurement provides branched-chain amino acid information"
    },
    "Val": {
        "description": "Valine",
        "loinc": "14691-1",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR valine measurement for branched-chain amino acid assessment"
    },
    "Phe": {
        "description": "Phenylalanine",
        "loinc": "14687-9",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR phenylalanine measurement clinically relevant for metabolic disorders"
    },
    "Tyr": {
        "description": "Tyrosine",
        "loinc": "14692-9",
        "unit": "mmol/L",
        "category": "amino_acids",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR tyrosine complements phenylalanine for metabolic assessment"
    },

    # Core Clinical Chemistry
    "Glucose": {
        "description": "Glucose",
        "loinc": "2345-7",
        "unit": "mmol/L",
        "category": "glycolysis",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR glucose shows excellent correlation with enzymatic glucose methods"
    },
    "Lactate": {
        "description": "Lactate",
        "loinc": "2524-7",
        "unit": "mmol/L",
        "category": "glycolysis",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR lactate measurement useful for metabolic assessment"
    },
    "Pyruvate": {
        "description": "Pyruvate",
        "loinc": "5544-7",
        "unit": "mmol/L",
        "category": "glycolysis",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR pyruvate provides direct measurement for lactate/pyruvate ratio"
    },
    "Citrate": {
        "description": "Citrate",
        "loinc": "2069-3",
        "unit": "mmol/L",
        "category": "energy_metabolism",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR citrate measurement for Krebs cycle assessment"
    },
    "Creatinine": {
        "description": "Creatinine",
        "loinc": "2160-0",
        "unit": "mmol/L",
        "category": "kidney_function",
        "clinical_equivalence": "approximate",
        "nmr_method_note": "NMR creatinine shows good correlation but may differ from Jaffe/enzymatic methods"
    },

    # Ketone Bodies
    "bOHbutyrate": {
        "description": "Beta-hydroxybutyrate",
        "loinc": "53060-9",
        "unit": "mmol/L",
        "category": "ketone_bodies",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR beta-hydroxybutyrate excellent for ketosis assessment"
    },
    "Acetate": {
        "description": "Acetate",
        "loinc": "25747-0",
        "unit": "mmol/L",
        "category": "ketone_bodies",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR acetate measurement for metabolic profiling"
    },
    "Acetoacetate": {
        "description": "Acetoacetate",
        "loinc": "1988-5",
        "unit": "mmol/L",
        "category": "ketone_bodies",
        "clinical_equivalence": "equivalent",
        "nmr_method_note": "NMR acetoacetate complements beta-hydroxybutyrate for ketosis assessment"
    },

    # Proteins (special case)
    "Albumin": {
        "description": "Albumin",
        "loinc": "1751-7",
        "unit": "g/L",
        "category": "proteins",
        "clinical_equivalence": "different",
        "nmr_method_note": "NMR measures albumin-bound signals, not direct albumin concentration like BCG/BCP methods"
    },

    # Inflammation
    "GlycA": {
        "description": "Glycoprotein acetyls",
        "loinc": None,  # No direct LOINC code
        "unit": "mmol/L",
        "category": "inflammation",
        "clinical_equivalence": "different",
        "nmr_method_note": "NMR-specific biomarker reflecting inflammation, no traditional equivalent"
    }
}

def main():
    """Extract LOINC mappings for Nightingale biomarkers."""
    print("Extracting LOINC mappings from Nightingale patterns...")

    # Load the filtered clinical chemistry data
    input_file = INPUT_DIR / "nightingale_clinical_filtered.tsv"
    df = pd.read_csv(input_file, sep='\t')
    print(f"Loaded {len(df)} filtered biomarkers")

    # Create LOINC mapping table
    loinc_mappings = []

    for _, row in df.iterrows():
        biomarker = row['nightingale_biomarker_id']

        if biomarker in NIGHTINGALE_LOINC_PATTERNS:
            pattern = NIGHTINGALE_LOINC_PATTERNS[biomarker]

            mapping = {
                'nightingale_biomarker_id': biomarker,
                'nightingale_name': row['nightingale_name'],
                'assigned_loinc_code': pattern['loinc'],
                'loinc_description': pattern['description'],
                'measurement_units': pattern['unit'],
                'biomarker_category': pattern['category'],
                'clinical_equivalence': pattern['clinical_equivalence'],
                'nmr_method_note': pattern['nmr_method_note'],
                'mapping_confidence': 0.95 if pattern['loinc'] else 0.0,
                'ukb_field_id': row['ukb_field_id']
            }
            loinc_mappings.append(mapping)

            status = "✓" if pattern['loinc'] else "✗"
            print(f"  {status} {biomarker}: {pattern['description']} → LOINC {pattern['loinc']}")
        else:
            # Biomarker not in our patterns
            mapping = {
                'nightingale_biomarker_id': biomarker,
                'nightingale_name': row['nightingale_name'],
                'assigned_loinc_code': None,
                'loinc_description': None,
                'measurement_units': row['measurement_units'],
                'biomarker_category': row['biomarker_category'],
                'clinical_equivalence': 'unknown',
                'nmr_method_note': 'No LOINC mapping available',
                'mapping_confidence': 0.0,
                'ukb_field_id': row['ukb_field_id']
            }
            loinc_mappings.append(mapping)
            print(f"  ✗ {biomarker}: No LOINC mapping found")

    # Convert to DataFrame
    mappings_df = pd.DataFrame(loinc_mappings)

    # Save LOINC mappings
    output_file = OUTPUT_DIR / "loinc_mappings.tsv"
    mappings_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved LOINC mappings to {output_file}")

    # Summary statistics
    total_biomarkers = len(mappings_df)
    mapped_biomarkers = len(mappings_df[mappings_df['assigned_loinc_code'].notna()])
    mapping_rate = (mapped_biomarkers / total_biomarkers) * 100

    print(f"\nLOINC Mapping Summary:")
    print(f"  Total biomarkers: {total_biomarkers}")
    print(f"  Successfully mapped: {mapped_biomarkers}")
    print(f"  Mapping rate: {mapping_rate:.1f}%")

    # Breakdown by clinical equivalence
    print(f"\nClinical Equivalence Breakdown:")
    equivalence_counts = mappings_df['clinical_equivalence'].value_counts()
    for equivalence, count in equivalence_counts.items():
        print(f"  {equivalence}: {count} biomarkers")

    # Breakdown by category
    print(f"\nCategory Breakdown:")
    category_counts = mappings_df['biomarker_category'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count} biomarkers")

if __name__ == "__main__":
    main()
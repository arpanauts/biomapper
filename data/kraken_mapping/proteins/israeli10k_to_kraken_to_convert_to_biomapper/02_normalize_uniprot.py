#!/usr/bin/env python3
"""
Proto-action: Map Nightingale protein names to UniProt IDs
This is a STANDALONE script, not a biomapper action

Maps protein biomarker names to standardized UniProt identifiers:
- Uses known mappings for major proteins
- Handles composite biomarkers (ratios)
- Documents NMR vs traditional assay differences
"""
import pandas as pd
from pathlib import Path

# Input/output paths
DATA_DIR = Path(__file__).parent / "data"
INPUT_FILE = DATA_DIR / "nightingale_proteins.tsv"
OUTPUT_FILE = DATA_DIR / "proteins_with_uniprot.tsv"

# Known UniProt mappings for Nightingale proteins
PROTEIN_UNIPROT_MAPPING = {
    'ApoA1': {
        'uniprot': 'P02647',
        'official_name': 'Apolipoprotein A-I',
        'gene_symbol': 'APOA1',
        'nmr_notes': 'NMR measures total ApoA1; immunoassays may show different values due to different epitopes'
    },
    'ApoB': {
        'uniprot': 'P04114',
        'official_name': 'Apolipoprotein B-100',
        'gene_symbol': 'APOB',
        'nmr_notes': 'NMR measures ApoB-100; some assays measure total ApoB (B-100 + B-48)'
    },
    'ApoB_by_ApoA1': {
        'uniprot': 'P04114,P02647',  # Composite ratio
        'official_name': 'ApoB/ApoA1 Ratio',
        'gene_symbol': 'APOB/APOA1',
        'nmr_notes': 'Calculated ratio from individual NMR measurements; clinically equivalent to immunoassay ratios'
    },
    'Albumin': {
        'uniprot': 'P02768',
        'official_name': 'Serum albumin',
        'gene_symbol': 'ALB',
        'nmr_notes': 'NMR albumin correlates well with BCG and BCP dye-binding assays'
    },
    'GlycA': {
        'uniprot': 'COMPOSITE',  # Multiple glycoproteins
        'official_name': 'Glycoprotein Acetyls (composite)',
        'gene_symbol': 'GlycA',
        'nmr_notes': 'Composite NMR signal from multiple acute-phase glycoproteins; no direct immunoassay equivalent'
    }
}

def normalize_biomarker_name(name):
    """Normalize biomarker name for mapping lookup"""
    # Handle common variations
    name_variations = {
        'ApoB_by_ApoA1': 'ApoB_by_ApoA1',
        'ApoB by ApoA1': 'ApoB_by_ApoA1',
        'ApoB/ApoA1': 'ApoB_by_ApoA1'
    }
    return name_variations.get(name, name)

def map_to_uniprot(df):
    """Map protein names to UniProt IDs and add metadata"""

    # Add UniProt mapping columns
    df['derived_uniprot'] = ''
    df['official_protein_name'] = ''
    df['gene_symbol'] = ''
    df['uniprot_mapping_confidence'] = 0.0
    df['nmr_assay_notes'] = ''
    df['is_composite_biomarker'] = False

    for idx, row in df.iterrows():
        biomarker_name = normalize_biomarker_name(row['biomarker_name'])

        if biomarker_name in PROTEIN_UNIPROT_MAPPING:
            mapping = PROTEIN_UNIPROT_MAPPING[biomarker_name]

            df.at[idx, 'derived_uniprot'] = mapping['uniprot']
            df.at[idx, 'official_protein_name'] = mapping['official_name']
            df.at[idx, 'gene_symbol'] = mapping['gene_symbol']
            df.at[idx, 'uniprot_mapping_confidence'] = 1.0  # High confidence for known mappings
            df.at[idx, 'nmr_assay_notes'] = mapping['nmr_notes']

            # Mark composite biomarkers
            if ',' in mapping['uniprot'] or mapping['uniprot'] == 'COMPOSITE':
                df.at[idx, 'is_composite_biomarker'] = True
        else:
            # Unknown protein - manual review needed
            df.at[idx, 'uniprot_mapping_confidence'] = 0.0
            df.at[idx, 'nmr_assay_notes'] = 'Unknown protein - requires manual UniProt mapping'

    return df

def add_israeli10k_context(df):
    """Add Israeli10K population-specific notes"""

    # Population-specific considerations
    population_notes = []

    for _, row in df.iterrows():
        notes = []

        if 'Apo' in row['biomarker_name']:
            notes.append("Apolipoprotein levels may vary in Middle Eastern populations")

        if row['biomarker_name'] == 'Albumin':
            notes.append("Reference ranges should be established for Israeli population")

        if row['biomarker_name'] == 'GlycA':
            notes.append("Inflammatory protein marker - may reflect population-specific inflammatory patterns")

        population_notes.append('; '.join(notes) if notes else row['population_notes'])

    df['population_notes'] = population_notes
    return df

def main():
    """Map protein names to UniProt IDs"""
    print("Mapping Nightingale proteins to UniProt IDs...")

    # Load extracted proteins
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        print("Please run 01_extract_proteins.py first")
        return

    df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(df)} protein biomarkers")

    # Map to UniProt
    df = map_to_uniprot(df)

    # Add population context
    df = add_israeli10k_context(df)

    # Save results
    df.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"Saved results to: {OUTPUT_FILE}")

    # Summary report
    print("\nUniProt Mapping Summary:")
    print(f"  Total proteins: {len(df)}")
    print(f"  Successfully mapped: {len(df[df['uniprot_mapping_confidence'] > 0])}")
    print(f"  Composite biomarkers: {len(df[df['is_composite_biomarker'] == True])}")
    print(f"  Require manual review: {len(df[df['uniprot_mapping_confidence'] == 0])}")

    print("\nMapped proteins:")
    for _, row in df.iterrows():
        confidence = "✓" if row['uniprot_mapping_confidence'] > 0 else "?"
        composite = " (composite)" if row['is_composite_biomarker'] else ""
        print(f"  {confidence} {row['biomarker_name']} → {row['derived_uniprot']}{composite}")

if __name__ == "__main__":
    main()
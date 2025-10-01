#!/usr/bin/env python3
"""
Proto-action: Extract Nightingale protein biomarkers for Israeli10K
This is a STANDALONE script, not a biomapper action

Identifies and extracts protein biomarkers from Nightingale RAG data:
- ApoA1, ApoB, ApoB/ApoA1 ratio
- Albumin
- GlycA (Glycoprotein Acetyls)
"""
import json
import pandas as pd
from pathlib import Path

# Input data - Nightingale RAG JSON files
RAG_DATA_DIR = Path("/home/ubuntu/biomapper/data/harmonization/nightingale/nightingale_metadata_enrichment_to_convert_to_biomapper/rag_data")
OUTPUT_DIR = Path(__file__).parent / "data"

# Protein biomarkers to extract
PROTEIN_BIOMARKERS = [
    "biomarker_039_ApoB.json",
    "biomarker_040_ApoA1.json",
    "biomarker_041_ApoB_by_ApoA1.json",
    "biomarker_079_Albumin.json",
    "biomarker_080_GlycA.json"
]

def extract_biomarker_data(json_file):
    """Extract relevant information from a biomarker JSON file"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract basic biomarker information
    biomarker_info = {
        'biomarker_id': f"nightingale_{data.get('index', '')}",
        'biomarker_name': data.get('biomarker', ''),
        'description': data.get('description', ''),
        'units': data.get('units', ''),
        'mapping_type': data.get('mapping_type', ''),
        'platform_annotation': 'Nightingale NMR',
        'measurement_method': 'Nuclear Magnetic Resonance (NMR)',
        'cohort': 'Israeli10K',
        'entity_type': 'protein'
    }

    # Extract LOINC mapping if available
    priority_results = data.get('priority_results', [])
    if priority_results and len(priority_results) > 0:
        best_match = priority_results[0]
        biomarker_info['loinc_code'] = best_match.get('loinc_code', '')
        biomarker_info['loinc_component'] = best_match.get('component', best_match.get('term', ''))
        biomarker_info['loinc_score'] = best_match.get('score', best_match.get('adjusted_score', 0.0))
    else:
        biomarker_info['loinc_code'] = ''
        biomarker_info['loinc_component'] = ''
        biomarker_info['loinc_score'] = 0.0

    return biomarker_info

def main():
    """Extract protein biomarkers from Nightingale RAG data"""
    print("Extracting Nightingale protein biomarkers for Israeli10K...")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Extract data from each protein biomarker
    protein_data = []
    for biomarker_file in PROTEIN_BIOMARKERS:
        json_path = RAG_DATA_DIR / biomarker_file
        if json_path.exists():
            print(f"Processing {biomarker_file}...")
            biomarker_info = extract_biomarker_data(json_path)
            protein_data.append(biomarker_info)
        else:
            print(f"Warning: {biomarker_file} not found")

    # Create DataFrame and save
    df = pd.DataFrame(protein_data)

    # Add Israeli10K specific metadata
    df['population_notes'] = 'Israeli10K cohort - Middle Eastern population genetics'
    df['nmr_specifics'] = 'NMR-derived biomarkers may have different reference ranges than traditional immunoassays'

    # Save to TSV
    output_file = OUTPUT_DIR / "nightingale_proteins.tsv"
    df.to_csv(output_file, sep='\t', index=False)

    print(f"Extracted {len(df)} protein biomarkers")
    print(f"Output saved to: {output_file}")

    # Print summary
    print("\nProtein biomarkers extracted:")
    for _, row in df.iterrows():
        print(f"  - {row['biomarker_name']}: {row['description']}")

if __name__ == "__main__":
    main()
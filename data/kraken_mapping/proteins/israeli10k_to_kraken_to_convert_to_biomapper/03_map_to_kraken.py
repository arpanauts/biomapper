#!/usr/bin/env python3
"""
Proto-action: Map proteins to Kraken Knowledge Graph nodes
This is a STANDALONE script, not a biomapper action

Performs direct ID matching between UniProt IDs and Kraken protein nodes:
- Loads Kraken 1.0.0 protein knowledge graph
- Extracts UniProtKB IDs from xrefs column
- Direct pandas join - no fuzzy matching
- Generates final output with required fields
"""
import pandas as pd
import re
from pathlib import Path

# Input/output paths
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
INPUT_FILE = DATA_DIR / "proteins_with_uniprot.tsv"

# Kraken reference data
KRAKEN_PROTEINS_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_proteins.csv"

# Output files
OUTPUT_FILE = RESULTS_DIR / "israeli10k_nightingale_proteins_mapped.tsv"
VALIDATION_REPORT = RESULTS_DIR / "mapping_validation_report.txt"

def load_kraken_proteins():
    """Load Kraken protein nodes and extract UniProt mappings"""
    print("Loading Kraken 1.0.0 protein knowledge graph...")

    # Load Kraken proteins
    kraken_df = pd.read_csv(KRAKEN_PROTEINS_FILE)
    print(f"Loaded {len(kraken_df)} Kraken protein nodes")

    # Extract UniProtKB IDs from xrefs column
    kraken_uniprot = []

    for idx, row in kraken_df.iterrows():
        xrefs = str(row.get('xrefs', ''))

        # Find all UniProtKB references
        uniprot_matches = re.findall(r'UniProtKB:([A-Z0-9]+(?:-[A-Z0-9]+)?)', xrefs)

        for uniprot_id in uniprot_matches:
            # Clean up the UniProt ID (remove any suffixes like -PRO_...)
            clean_uniprot = re.sub(r'-PRO_.*$', '', uniprot_id)

            kraken_uniprot.append({
                'uniprot_id': clean_uniprot,
                'kraken_node_id': row['id'],
                'kraken_name': row['name'],
                'kraken_category': row['category'],
                'kraken_description': row.get('description', ''),
                'kraken_synonyms': row.get('synonyms', '')
            })

    # Create UniProt -> Kraken mapping DataFrame
    uniprot_kraken_df = pd.DataFrame(kraken_uniprot)
    print(f"Extracted {len(uniprot_kraken_df)} UniProt mappings from Kraken")

    # Remove duplicates (keep first occurrence)
    uniprot_kraken_df = uniprot_kraken_df.drop_duplicates(subset=['uniprot_id'], keep='first')
    print(f"Unique UniProt IDs: {len(uniprot_kraken_df)}")

    return uniprot_kraken_df

def map_proteins_to_kraken(proteins_df, kraken_mapping_df):
    """Map protein biomarkers to Kraken nodes via UniProt IDs"""
    print("Mapping proteins to Kraken nodes...")

    # Handle composite biomarkers (multiple UniProt IDs)
    mapped_results = []

    for idx, row in proteins_df.iterrows():
        uniprot_ids = str(row['derived_uniprot']).split(',')

        # Map each UniProt ID
        mappings_found = []
        for uniprot_id in uniprot_ids:
            uniprot_id = uniprot_id.strip()

            if uniprot_id and uniprot_id != 'COMPOSITE':
                # Direct join with Kraken mapping
                kraken_matches = kraken_mapping_df[kraken_mapping_df['uniprot_id'] == uniprot_id]

                if not kraken_matches.empty:
                    mappings_found.extend(kraken_matches.to_dict('records'))

        # Create output records
        if mappings_found:
            # If multiple mappings (composite biomarker), create separate records
            for mapping in mappings_found:
                mapped_row = {
                    # Original Nightingale data
                    'nightingale_biomarker_id': row['biomarker_id'],
                    'nightingale_name': row['biomarker_name'],
                    'biomarker_description': row['description'],
                    'units': row['units'],

                    # Protein mapping data
                    'derived_uniprot': mapping['uniprot_id'],
                    'official_protein_name': row['official_protein_name'],
                    'gene_symbol': row['gene_symbol'],
                    'measurement_method': row['measurement_method'],

                    # Kraken knowledge graph data
                    'kraken_node_id': mapping['kraken_node_id'],
                    'kraken_name': mapping['kraken_name'],
                    'kraken_category': mapping['kraken_category'],
                    'kraken_description': mapping['kraken_description'][:500],  # Truncate long descriptions

                    # Mapping quality and metadata
                    'mapping_confidence': row['uniprot_mapping_confidence'],
                    'is_composite_biomarker': row['is_composite_biomarker'],
                    'nmr_assay_notes': row['nmr_assay_notes'],
                    'population_notes': row['population_notes'],

                    # Technical metadata
                    'mapping_method': 'Direct UniProt ID matching',
                    'kraken_version': '1.0.0',
                    'mapping_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                mapped_results.append(mapped_row)
        else:
            # No Kraken mapping found
            unmapped_row = {
                'nightingale_biomarker_id': row['biomarker_id'],
                'nightingale_name': row['biomarker_name'],
                'biomarker_description': row['description'],
                'units': row['units'],
                'derived_uniprot': row['derived_uniprot'],
                'official_protein_name': row['official_protein_name'],
                'gene_symbol': row['gene_symbol'],
                'measurement_method': row['measurement_method'],
                'kraken_node_id': '',
                'kraken_name': '',
                'kraken_category': '',
                'kraken_description': '',
                'mapping_confidence': 0.0,
                'is_composite_biomarker': row['is_composite_biomarker'],
                'nmr_assay_notes': row['nmr_assay_notes'],
                'population_notes': row['population_notes'] + ' [UNMAPPED - no Kraken node found]',
                'mapping_method': 'Direct UniProt ID matching',
                'kraken_version': '1.0.0',
                'mapping_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            mapped_results.append(unmapped_row)

    return pd.DataFrame(mapped_results)

def generate_validation_report(original_df, mapped_df):
    """Generate validation report"""

    report_lines = [
        "=== Israeli10K Nightingale Proteins to Kraken Mapping Validation Report ===",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Input Summary",
        f"Original protein biomarkers: {len(original_df)}",
        f"Output mapped records: {len(mapped_df)}",
        "",
        "## Mapping Statistics",
        f"Successfully mapped to Kraken: {len(mapped_df[mapped_df['kraken_node_id'] != ''])}",
        f"Unmapped (no Kraken node): {len(mapped_df[mapped_df['kraken_node_id'] == ''])}",
        f"Composite biomarkers: {len(mapped_df[mapped_df['is_composite_biomarker'] == True])}",
        f"Match rate: {100 * len(mapped_df[mapped_df['kraken_node_id'] != '']) / len(original_df):.1f}%",
        "",
        "## Individual Protein Results"
    ]

    # Add individual results
    for _, row in original_df.iterrows():
        protein_mappings = mapped_df[mapped_df['nightingale_biomarker_id'] == row['biomarker_id']]
        mapped_count = len(protein_mappings[protein_mappings['kraken_node_id'] != ''])

        if mapped_count > 0:
            status = f"✓ MAPPED ({mapped_count} Kraken nodes)"
        else:
            status = "✗ UNMAPPED"

        report_lines.append(f"  {row['biomarker_name']} ({row['derived_uniprot']}): {status}")

    report_lines.extend([
        "",
        "## Validation Checklist",
        f"□ All Nightingale proteins processed: {len(original_df)} biomarkers",
        f"□ UniProt mappings verified: {len(original_df[original_df['uniprot_mapping_confidence'] > 0])} mapped",
        f"□ Kraken nodes correctly identified: {len(mapped_df[mapped_df['kraken_node_id'] != ''])} found",
        f"□ NMR measurement notes included: {len(mapped_df[mapped_df['nmr_assay_notes'] != ''])} annotated",
        f"□ Composite biomarkers handled: {len(mapped_df[mapped_df['is_composite_biomarker'] == True])} identified",
        "",
        "## Key Proteins Status",
        "Manual verification recommended for:"
    ])

    # Check key proteins mentioned in original requirements
    key_proteins = ['Albumin', 'ApoA1', 'ApoB']
    for protein in key_proteins:
        protein_status = mapped_df[mapped_df['nightingale_name'] == protein]
        if not protein_status.empty and protein_status.iloc[0]['kraken_node_id']:
            report_lines.append(f"  ✓ {protein}: Mapped to {protein_status.iloc[0]['kraken_node_id']}")
        else:
            report_lines.append(f"  ✗ {protein}: NOT MAPPED")

    return '\n'.join(report_lines)

def main():
    """Map proteins to Kraken knowledge graph"""
    print("Mapping Israeli10K Nightingale proteins to Kraken KG...")

    # Check input file exists
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        print("Please run 02_normalize_uniprot.py first")
        return

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Load input data
    proteins_df = pd.read_csv(INPUT_FILE, sep='\t')
    print(f"Loaded {len(proteins_df)} protein biomarkers")

    # Load Kraken protein mappings
    kraken_mapping_df = load_kraken_proteins()

    # Perform mapping
    mapped_df = map_proteins_to_kraken(proteins_df, kraken_mapping_df)

    # Save results
    mapped_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
    print(f"Saved mapping results to: {OUTPUT_FILE}")

    # Generate validation report
    validation_report = generate_validation_report(proteins_df, mapped_df)
    with open(VALIDATION_REPORT, 'w') as f:
        f.write(validation_report)
    print(f"Saved validation report to: {VALIDATION_REPORT}")

    # Print summary
    total_original = len(proteins_df)
    total_mapped = len(mapped_df[mapped_df['kraken_node_id'] != ''])
    total_unmapped = len(mapped_df[mapped_df['kraken_node_id'] == ''])

    print(f"\n=== MAPPING COMPLETE ===")
    print(f"Original biomarkers: {total_original}")
    print(f"Mapped to Kraken: {total_mapped}")
    print(f"Unmapped: {total_unmapped}")
    print(f"Success rate: {100 * total_mapped / len(mapped_df):.1f}%")

if __name__ == "__main__":
    main()
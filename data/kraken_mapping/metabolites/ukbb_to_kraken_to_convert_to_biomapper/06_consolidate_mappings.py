#!/usr/bin/env python3
"""
Proto-action: Consolidate all mappings and generate final output
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Direct file paths - no context/parameters
INPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "results"

def main():
    print("Consolidating all mappings and generating final output...")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load all successful matches
    match_files = [
        (INPUT_DIR / "chebi_direct_matches.tsv", "ChEBI"),
        (INPUT_DIR / "hmdb_direct_matches.tsv", "HMDB")
    ]

    all_matches = []
    total_mapped = 0

    for file_path, match_type in match_files:
        if file_path.exists():
            df = pd.read_csv(file_path, sep='\t')
            all_matches.append(df)
            total_mapped += len(df)
            print(f"  Loaded {len(df)} {match_type} matches from {file_path.name}")
        else:
            print(f"  No {match_type} matches file found: {file_path}")

    # Combine all successful matches
    if all_matches:
        combined_matches = pd.concat(all_matches, ignore_index=True)
        print(f"\nTotal successful mappings: {len(combined_matches)}")
    else:
        print("ERROR: No match files found!")
        combined_matches = pd.DataFrame()

    # Load original Nightingale data for total count
    original_file = INPUT_DIR / "nightingale_loaded.tsv"
    if original_file.exists():
        original_df = pd.read_csv(original_file, sep='\t')
        total_nightingale = len(original_df)
        print(f"Total original Nightingale biomarkers: {total_nightingale}")
    else:
        total_nightingale = 0
        print("WARNING: Could not load original Nightingale data")

    # Create final mapping output with required fields per specification
    if len(combined_matches) > 0:
        print("\nCreating final mapping output with required fields...")

        final_mapping = pd.DataFrame()

        # Required fields from specification:
        # - nightingale_biomarker_id, nightingale_name
        # - ukbb_field_id (if available)
        # - kg2c_node_id, kg2c_name, kg2c_category → kraken_node_id, kraken_name, kraken_category
        # - chemical_class, measurement_type
        # - mapping_confidence

        final_mapping['nightingale_biomarker_id'] = combined_matches['Biomarker']
        final_mapping['nightingale_name'] = combined_matches['Biomarker']  # Same as biomarker ID in this case

        # UKBB field ID - not available in current data, set as placeholder
        final_mapping['ukbb_field_id'] = 'N/A'

        # Kraken node information - handle column naming from merge
        kraken_id_col = 'id_kraken' if 'id_kraken' in combined_matches.columns else 'id'
        kraken_name_col = 'name_kraken' if 'name_kraken' in combined_matches.columns else 'name'
        kraken_category_col = 'category_kraken' if 'category_kraken' in combined_matches.columns else 'category'

        final_mapping['kraken_node_id'] = combined_matches[kraken_id_col]
        final_mapping['kraken_name'] = combined_matches.get(kraken_name_col, 'N/A')
        final_mapping['kraken_category'] = combined_matches.get(kraken_category_col, 'biolink:SmallMolecule')

        # Chemical classification
        final_mapping['chemical_class'] = combined_matches.get('metabolite_classification', 'metabolite')
        final_mapping['measurement_type'] = 'nmr_biomarker'

        # Mapping metadata
        final_mapping['mapping_confidence'] = combined_matches['mapping_confidence']
        final_mapping['mapping_type'] = combined_matches['mapping_type']
        final_mapping['mapping_stage'] = combined_matches['mapping_stage']

        # Add source identifiers for traceability
        final_mapping['source_chebi_id'] = combined_matches.get('ChEBI_ID', '')
        final_mapping['source_hmdb_id'] = combined_matches.get('HMDB_ID_merged', '')
        final_mapping['source_pubchem_id'] = combined_matches.get('PubChem_CID_merged', '')

        # Add timestamp
        final_mapping['mapping_timestamp'] = datetime.now().isoformat()

        # Save final mapping
        final_mapping_file = OUTPUT_DIR / "ukbb_nightingale_to_kraken_mapping.tsv"
        final_mapping.to_csv(final_mapping_file, sep='\t', index=False)
        print(f"Saved final mapping to {final_mapping_file}")

        # Create simplified version with just key fields
        simplified_mapping = final_mapping[[
            'nightingale_biomarker_id',
            'nightingale_name',
            'kraken_node_id',
            'kraken_name',
            'mapping_confidence',
            'mapping_type'
        ]].copy()

        simplified_file = OUTPUT_DIR / "ukbb_nightingale_to_kraken_simplified.tsv"
        simplified_mapping.to_csv(simplified_file, sep='\t', index=False)
        print(f"Saved simplified mapping to {simplified_file}")

    # Load and save unmatched records
    unmatched_file = INPUT_DIR / "final_unmatched.tsv"
    if unmatched_file.exists():
        unmatched_df = pd.read_csv(unmatched_file, sep='\t')
        print(f"\nUnmatched biomarkers: {len(unmatched_df)}")

        # Save unmatched with relevant fields
        unmatched_output = pd.DataFrame()
        unmatched_output['nightingale_biomarker_id'] = unmatched_df['Biomarker']
        unmatched_output['nightingale_name'] = unmatched_df['Biomarker']
        unmatched_output['available_chebi_id'] = unmatched_df.get('ChEBI_ID', '')
        unmatched_output['available_hmdb_id'] = unmatched_df.get('HMDB_ID_merged', '')
        unmatched_output['available_pubchem_id'] = unmatched_df.get('PubChem_CID_merged', '')
        unmatched_output['chemical_class'] = unmatched_df.get('metabolite_classification', '')
        unmatched_output['reason_unmatched'] = 'No matching Kraken node found'

        unmatched_output_file = OUTPUT_DIR / "unmatched_metabolites.tsv"
        unmatched_output.to_csv(unmatched_output_file, sep='\t', index=False)
        print(f"Saved unmatched metabolites to {unmatched_output_file}")

    # Generate comprehensive summary report
    summary_report = []
    summary_report.append("# UKBB Nightingale to Kraken Metabolite Mapping Report")
    summary_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_report.append("")

    summary_report.append("## Mapping Results")
    summary_report.append(f"- Total Nightingale biomarkers: {total_nightingale}")
    summary_report.append(f"- Successfully mapped to Kraken: {total_mapped}")

    if total_nightingale > 0:
        overall_match_rate = (total_mapped / total_nightingale) * 100
        summary_report.append(f"- Overall match rate: {overall_match_rate:.1f}%")

    if len(combined_matches) > 0:
        summary_report.append("")
        summary_report.append("## Mapping Breakdown by Method")

        # Count by mapping type
        mapping_counts = combined_matches['mapping_type'].value_counts()
        for mapping_type, count in mapping_counts.items():
            percentage = (count / total_mapped) * 100
            avg_confidence = combined_matches[combined_matches['mapping_type'] == mapping_type]['mapping_confidence'].mean()
            summary_report.append(f"- {mapping_type}: {count} ({percentage:.1f}%, avg confidence: {avg_confidence:.3f})")

    if unmatched_file.exists():
        unmatched_count = len(unmatched_df)
        summary_report.append("")
        summary_report.append("## Unmatched Biomarkers")
        summary_report.append(f"- Total unmatched: {unmatched_count}")
        if total_nightingale > 0:
            unmatched_rate = (unmatched_count / total_nightingale) * 100
            summary_report.append(f"- Unmatched rate: {unmatched_rate:.1f}%")

    summary_report.append("")
    summary_report.append("## Output Files")
    summary_report.append(f"- Main mapping: ukbb_nightingale_to_kraken_mapping.tsv")
    summary_report.append(f"- Simplified mapping: ukbb_nightingale_to_kraken_simplified.tsv")
    summary_report.append(f"- Unmatched biomarkers: unmatched_metabolites.tsv")

    # Save summary report
    summary_file = OUTPUT_DIR / "mapping_summary.md"
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary_report))
    print(f"Saved summary report to {summary_file}")

    # Display summary to console
    print("\n" + "="*60)
    print("FINAL MAPPING SUMMARY")
    print("="*60)

    if total_nightingale > 0:
        overall_match_rate = (total_mapped / total_nightingale) * 100
        print(f"Total Nightingale biomarkers: {total_nightingale}")
        print(f"Successfully mapped to Kraken: {total_mapped}")
        print(f"Overall match rate: {overall_match_rate:.1f}%")

        if len(combined_matches) > 0:
            print(f"\nBreakdown by method:")
            mapping_counts = combined_matches['mapping_type'].value_counts()
            for mapping_type, count in mapping_counts.items():
                percentage = (count / total_mapped) * 100
                avg_confidence = combined_matches[combined_matches['mapping_type'] == mapping_type]['mapping_confidence'].mean()
                print(f"  {mapping_type}: {count} ({percentage:.1f}%, avg confidence: {avg_confidence:.3f})")

        if unmatched_file.exists():
            unmatched_count = len(unmatched_df)
            print(f"\nUnmatched: {unmatched_count} ({100-overall_match_rate:.1f}%)")

    print(f"\nResults saved to: {OUTPUT_DIR}/")
    print("Mapping pipeline completed successfully!")

if __name__ == "__main__":
    main()
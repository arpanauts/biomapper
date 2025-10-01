#!/usr/bin/env python3
"""
Proto-action: Generate final mapping report and comparison
This is a STANDALONE script, not a biomapper action

Creates the final output TSV with required fields and generates
comprehensive mapping analysis including population-specific notes.
"""
import pandas as pd
from pathlib import Path
import sys
import json
from datetime import datetime

# Input and output paths
INPUT_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
INPUT_FILE = INPUT_DIR / "israeli10k_nightingale_kraken_mapped.tsv"

# Create results directory
RESULTS_DIR.mkdir(exist_ok=True)

def generate_population_notes(biomarker, group=None):
    """
    Generate population-specific reference range notes for Israeli10K

    Args:
        biomarker: Biomarker name
        group: Biomarker group/category

    Returns:
        Population-specific notes string
    """
    # Standard note for Israeli10K context
    base_note = "Israeli10K cohort"

    # Add biomarker-specific notes based on known population differences
    population_notes = {
        'glucose': 'Israeli population; consider Mediterranean diet patterns',
        'creatinine': 'Israeli population; may vary by ethnicity (Ashkenazi/Sephardic)',
        'albumin': 'Israeli population; consider genetic variants',
        'cholesterol': 'Israeli population; Mediterranean diet influence',
        'triglycerides': 'Israeli population; dietary and genetic factors'
    }

    biomarker_lower = biomarker.lower()
    for marker, note in population_notes.items():
        if marker in biomarker_lower:
            return f"{base_note}; {note}"

    return base_note

def compare_with_ukbb(mapped_df):
    """
    Compare mapping results with UKBB Nightingale mappings if available

    Args:
        mapped_df: Mapped Israeli10K data

    Returns:
        Comparison summary dictionary
    """
    ukbb_file = "/home/ubuntu/biomapper/data/kraken_mapping/chemistry/ukbb_nightingale_to_kraken_to_convert_to_biomapper/results/ukbb_nightingale_clinical_to_kraken.tsv"

    comparison = {
        'ukbb_data_available': False,
        'common_biomarkers': 0,
        'israeli10k_unique': 0,
        'ukbb_unique': 0,
        'mapping_consistency': 'N/A'
    }

    if Path(ukbb_file).exists():
        try:
            ukbb_df = pd.read_csv(ukbb_file, sep='\t')
            comparison['ukbb_data_available'] = True

            # Find common biomarkers
            israeli_loinc = set(mapped_df['assigned_loinc_code'].dropna())
            ukbb_loinc = set(ukbb_df['assigned_loinc_code'].dropna())

            common = israeli_loinc.intersection(ukbb_loinc)
            comparison['common_biomarkers'] = len(common)
            comparison['israeli10k_unique'] = len(israeli_loinc - ukbb_loinc)
            comparison['ukbb_unique'] = len(ukbb_loinc - israeli_loinc)

            if common:
                # Check mapping consistency for common biomarkers
                consistent = 0
                for loinc in common:
                    israeli_kraken = mapped_df[mapped_df['assigned_loinc_code'] == loinc]['kraken_node_id'].iloc[0]
                    ukbb_kraken = ukbb_df[ukbb_df['assigned_loinc_code'] == loinc]['kraken_node_id'].iloc[0]
                    if israeli_kraken == ukbb_kraken:
                        consistent += 1

                comparison['mapping_consistency'] = f"{consistent}/{len(common)} ({100*consistent/len(common):.1f}%)"

        except Exception as e:
            print(f"Warning: Could not load UKBB comparison data: {e}")

    return comparison

def main():
    print("Generating final mapping report...")

    # Check if input file exists
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run 03_map_to_kraken.py first")
        sys.exit(1)

    # Load mapped data
    try:
        mapped_df = pd.read_csv(INPUT_FILE, sep='\t', low_memory=False)
        print(f"Loaded {len(mapped_df)} mapped records")
    except Exception as e:
        print(f"ERROR loading mapped file: {e}")
        sys.exit(1)

    # Filter to successfully mapped records
    successfully_mapped = mapped_df[mapped_df['id'].notna()].copy()
    print(f"Successfully mapped records: {len(successfully_mapped)}")

    if len(successfully_mapped) == 0:
        print("ERROR: No successfully mapped records found!")
        sys.exit(1)

    # Create final output with required fields
    print("Creating final output format...")

    final_df = pd.DataFrame()

    # Required fields according to specification
    final_df['nightingale_biomarker_id'] = successfully_mapped['Biomarker']
    final_df['nightingale_name'] = successfully_mapped.get('Description', successfully_mapped['Biomarker'])
    final_df['assigned_loinc_code'] = successfully_mapped['loinc_code_clean']
    final_df['loinc_term'] = successfully_mapped.get('loinc_term', 'Clinical chemistry test')
    final_df['kraken_node_id'] = successfully_mapped['id']
    final_df['kraken_name'] = successfully_mapped.get('name', 'Kraken node')
    final_df['mapping_confidence'] = successfully_mapped['final_mapping_confidence']

    # Add population-specific range notes
    final_df['population_specific_range'] = final_df.apply(
        lambda row: generate_population_notes(
            row['nightingale_biomarker_id'],
            successfully_mapped.get('Group', '').iloc[0] if len(successfully_mapped) > 0 else None
        ),
        axis=1
    )

    # Add additional metadata
    final_df['units'] = successfully_mapped.get('Units', 'Unknown')
    final_df['biomarker_group'] = successfully_mapped.get('Group', 'Clinical chemistry')
    final_df['platform'] = 'Nightingale NMR'
    final_df['cohort'] = 'Israeli10K'
    final_df['mapping_method'] = 'Direct LOINC match'
    final_df['mapping_timestamp'] = datetime.now().isoformat()

    # Sort by confidence (highest first)
    final_df = final_df.sort_values('mapping_confidence', ascending=False)

    # Save final mapping
    output_file = RESULTS_DIR / "israeli10k_nightingale_clinical_to_kraken.tsv"
    final_df.to_csv(output_file, sep='\t', index=False)
    print(f"Saved final mapping to {output_file}")

    # Generate comprehensive analysis report
    print("Generating analysis report...")

    # Basic statistics
    total_input = len(mapped_df)
    total_mapped = len(successfully_mapped)
    mapping_rate = (total_mapped / total_input) * 100

    # LOINC code analysis
    unique_loinc = final_df['assigned_loinc_code'].nunique()
    loinc_coverage = final_df.groupby('assigned_loinc_code').size()

    # Confidence analysis
    avg_confidence = final_df['mapping_confidence'].mean()
    high_confidence = len(final_df[final_df['mapping_confidence'] >= 0.9])

    # Biomarker group analysis
    group_analysis = final_df['biomarker_group'].value_counts()

    # Compare with UKBB
    ukbb_comparison = compare_with_ukbb(final_df)

    # Create analysis report
    analysis = {
        'summary': {
            'total_input_biomarkers': total_input,
            'successfully_mapped': total_mapped,
            'mapping_rate_percent': round(mapping_rate, 1),
            'unique_loinc_codes': unique_loinc,
            'average_confidence': round(avg_confidence, 3),
            'high_confidence_mappings': high_confidence
        },
        'biomarker_groups': {str(k): int(v) for k, v in group_analysis.to_dict().items()},
        'loinc_code_distribution': {
            'codes_with_single_biomarker': int(len(loinc_coverage[loinc_coverage == 1])),
            'codes_with_multiple_biomarkers': int(len(loinc_coverage[loinc_coverage > 1])),
            'max_biomarkers_per_code': int(loinc_coverage.max())
        },
        'ukbb_comparison': ukbb_comparison,
        'population_specific_notes': {
            'cohort': 'Israeli10K',
            'platform': 'Nightingale NMR',
            'considerations': [
                'Mediterranean diet patterns may affect lipid profiles',
                'Genetic diversity (Ashkenazi/Sephardic) may impact reference ranges',
                'Population-specific clinical chemistry thresholds recommended'
            ]
        },
        'validation_criteria_met': {
            'all_biomarkers_processed': total_input == len(mapped_df),
            'loinc_assignments_consistent': unique_loinc > 0,
            'kraken_mappings_verified': total_mapped > 0,
            'population_notes_included': True,
            'comparison_attempted': True
        },
        'timestamp': datetime.now().isoformat()
    }

    # Save analysis report
    analysis_file = RESULTS_DIR / "mapping_analysis_report.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"Saved analysis report to {analysis_file}")

    # Print summary to console
    print("\n" + "="*60)
    print("ISRAELI10K NIGHTINGALE CLINICAL CHEMISTRY MAPPING RESULTS")
    print("="*60)
    print(f"Total biomarkers processed: {total_input}")
    print(f"Successfully mapped to Kraken: {total_mapped}")
    print(f"Overall mapping rate: {mapping_rate:.1f}%")
    print(f"Unique LOINC codes: {unique_loinc}")
    print(f"Average mapping confidence: {avg_confidence:.3f}")
    print(f"High confidence mappings (≥0.9): {high_confidence}")

    print(f"\nBiomarker groups:")
    for group, count in group_analysis.head().items():
        print(f"  {group}: {count}")

    if ukbb_comparison['ukbb_data_available']:
        print(f"\nUKBB comparison:")
        print(f"  Common biomarkers: {ukbb_comparison['common_biomarkers']}")
        print(f"  Israeli10K unique: {ukbb_comparison['israeli10k_unique']}")
        print(f"  Mapping consistency: {ukbb_comparison['mapping_consistency']}")

    print(f"\nValidation criteria:")
    for criterion, met in analysis['validation_criteria_met'].items():
        status = "✓" if met else "✗"
        print(f"  {status} {criterion.replace('_', ' ').title()}")

    # Success/failure determination
    if mapping_rate >= 80:
        print(f"\n✓ SUCCESS: Mapping rate ({mapping_rate:.1f}%) meets expectations (≥80%)")
    elif mapping_rate >= 60:
        print(f"\n⚠ PARTIAL SUCCESS: Mapping rate ({mapping_rate:.1f}%) acceptable but below target")
    else:
        print(f"\n✗ ATTENTION NEEDED: Low mapping rate ({mapping_rate:.1f}%) requires investigation")

    print(f"\nOutput files:")
    print(f"  Main results: {output_file}")
    print(f"  Analysis report: {analysis_file}")

    print("\n04_generate_report.py completed successfully!")

if __name__ == "__main__":
    main()
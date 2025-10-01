#!/usr/bin/env python3
"""
Coverage analysis for Israeli10K demographics to Kraken mapping
This is a STANDALONE script, not a biomapper action.

Analyzes mapping results, generates coverage reports, and documents
population-specific considerations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime

# File paths
RESULTS_FILE = Path(__file__).parent / "results" / "israeli10k_demographics_kraken_mappings.tsv"
ORIGINAL_DATA_FILE = "/home/ubuntu/biomapper/data/harmonization/demographics/loinc_demographics_to_convert_to_biomapper/results/israeli10k_demographics_weighted_loinc.tsv"
ANALYSIS_OUTPUT_DIR = Path(__file__).parent / "results"
COVERAGE_REPORT_FILE = ANALYSIS_OUTPUT_DIR / "coverage_analysis_report.txt"
DETAILED_STATS_FILE = ANALYSIS_OUTPUT_DIR / "detailed_mapping_statistics.json"

def load_mapping_results():
    """Load the mapping results and original data."""

    if not RESULTS_FILE.exists():
        raise FileNotFoundError(f"Mapping results not found: {RESULTS_FILE}")

    mapped_df = pd.read_csv(RESULTS_FILE, sep='\t')
    print(f"Loaded mapping results: {len(mapped_df)} records")

    # Load original data for comparison
    original_df = pd.read_csv(ORIGINAL_DATA_FILE, sep='\t')
    print(f"Loaded original demographics: {len(original_df)} records")

    return mapped_df, original_df

def analyze_overall_coverage(mapped_df, original_df):
    """Analyze overall mapping coverage."""

    analysis = {}

    # Basic counts
    total_original = len(original_df)
    total_processed = len(mapped_df)
    successfully_mapped = len(mapped_df[mapped_df['mapping_status'] == 'Mapped'])

    analysis['overall'] = {
        'total_original_fields': total_original,
        'total_processed_fields': total_processed,
        'successfully_mapped': successfully_mapped,
        'processing_rate': total_processed / total_original * 100,
        'mapping_rate': successfully_mapped / total_processed * 100,
        'overall_success_rate': successfully_mapped / total_original * 100
    }

    # Coverage by confidence score ranges
    confidence_ranges = [
        (0.9, 1.0, "Excellent (≥0.9)"),
        (0.8, 0.9, "Very Good (0.8-0.9)"),
        (0.7, 0.8, "Good (0.7-0.8)"),
        (0.6, 0.7, "Fair (0.6-0.7)"),
        (0.0, 0.6, "Poor (<0.6)")
    ]

    analysis['confidence_distribution'] = {}
    for min_conf, max_conf, label in confidence_ranges:
        in_range = mapped_df[
            (mapped_df['mapping_confidence'] >= min_conf) &
            (mapped_df['mapping_confidence'] < max_conf)
        ]
        mapped_in_range = in_range[in_range['mapping_status'] == 'Mapped']

        analysis['confidence_distribution'][label] = {
            'total_fields': len(in_range),
            'mapped_fields': len(mapped_in_range),
            'mapping_rate': len(mapped_in_range) / len(in_range) * 100 if len(in_range) > 0 else 0
        }

    return analysis

def analyze_category_coverage(mapped_df):
    """Analyze mapping coverage by demographic category."""

    category_analysis = {}

    for category in mapped_df['demographic_category'].unique():
        cat_fields = mapped_df[mapped_df['demographic_category'] == category]
        cat_mapped = cat_fields[cat_fields['mapping_status'] == 'Mapped']

        category_analysis[category] = {
            'total_fields': len(cat_fields),
            'mapped_fields': len(cat_mapped),
            'mapping_rate': len(cat_mapped) / len(cat_fields) * 100,
            'avg_confidence': cat_fields['mapping_confidence'].mean(),
            'sample_fields': cat_fields['israeli10k_field'].head(3).tolist()
        }

        # Best and worst mappings in category
        if len(cat_mapped) > 0:
            best_mapping = cat_mapped.loc[cat_mapped['mapping_confidence'].idxmax()]
            category_analysis[category]['best_mapping'] = {
                'field': best_mapping['israeli10k_field'],
                'kraken_name': best_mapping['kraken_name'],
                'confidence': best_mapping['mapping_confidence']
            }

    return category_analysis

def analyze_population_considerations(mapped_df):
    """Analyze population-specific considerations for Israeli10K."""

    population_analysis = {
        'israeli_specific_fields': [],
        'cultural_considerations': [],
        'translation_issues': [],
        'measurement_standards': []
    }

    for _, row in mapped_df.iterrows():
        field_name = str(row['israeli10k_field']).lower()
        notes = str(row['population_specific_notes']).lower()

        # Israeli-specific fields
        if 'aliya' in field_name or 'immigration' in notes:
            population_analysis['israeli_specific_fields'].append({
                'field': row['israeli10k_field'],
                'description': row['israeli10k_description'],
                'mapped': row['mapping_status'] == 'Mapped',
                'notes': row['population_specific_notes']
            })

        # Cultural considerations
        if 'hebrew' in notes or 'diverse' in notes:
            population_analysis['cultural_considerations'].append({
                'field': row['israeli10k_field'],
                'consideration': row['population_specific_notes']
            })

        # Measurement standards
        if any(measure in field_name for measure in ['circumference', 'height', 'weight', 'bmi']):
            population_analysis['measurement_standards'].append({
                'field': row['israeli10k_field'],
                'mapped': row['mapping_status'] == 'Mapped',
                'population_note': row['population_specific_notes']
            })

    return population_analysis

def compare_with_other_cohorts():
    """Compare Israeli10K mapping rates with other cohorts (if data available)."""

    comparison = {
        'israeli10k': {
            'note': "Current analysis",
            'expected_rate': "35-40% (from project specifications)"
        },
        'arivale': {
            'note': "Reference from harmonization data",
            'expected_rate': "~61% LOINC mapping rate"
        },
        'ukbb': {
            'note': "Reference from harmonization data",
            'expected_rate': "~71% LOINC mapping rate"
        }
    }

    return comparison

def generate_coverage_report(analysis_data):
    """Generate comprehensive coverage report."""

    report_lines = []

    # Header
    report_lines.append("=" * 80)
    report_lines.append("ISRAELI10K DEMOGRAPHICS TO KRAKEN MAPPING - COVERAGE ANALYSIS")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Overall coverage
    overall = analysis_data['overall']
    report_lines.append("OVERALL COVERAGE SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Original demographic fields: {overall['total_original_fields']}")
    report_lines.append(f"Fields processed for mapping: {overall['total_processed_fields']}")
    report_lines.append(f"Successfully mapped to Kraken: {overall['successfully_mapped']}")
    report_lines.append(f"Processing rate: {overall['processing_rate']:.1f}%")
    report_lines.append(f"Mapping rate: {overall['mapping_rate']:.1f}%")
    report_lines.append(f"Overall success rate: {overall['overall_success_rate']:.1f}%")
    report_lines.append("")

    # Confidence distribution
    report_lines.append("MAPPING QUALITY DISTRIBUTION")
    report_lines.append("-" * 40)
    for conf_range, stats in analysis_data['confidence_distribution'].items():
        if stats['total_fields'] > 0:
            report_lines.append(f"{conf_range}: {stats['mapped_fields']}/{stats['total_fields']} ({stats['mapping_rate']:.1f}%)")
    report_lines.append("")

    # Category breakdown
    report_lines.append("COVERAGE BY DEMOGRAPHIC CATEGORY")
    report_lines.append("-" * 40)
    for category, stats in analysis_data['category_coverage'].items():
        report_lines.append(f"{category}:")
        report_lines.append(f"  Fields: {stats['mapped_fields']}/{stats['total_fields']} ({stats['mapping_rate']:.1f}%)")
        report_lines.append(f"  Avg confidence: {stats['avg_confidence']:.3f}")
        if 'best_mapping' in stats:
            best = stats['best_mapping']
            report_lines.append(f"  Best mapping: {best['field']} → {best['kraken_name']} ({best['confidence']:.3f})")
        report_lines.append("")

    # Population considerations
    pop_analysis = analysis_data['population_analysis']
    report_lines.append("POPULATION-SPECIFIC CONSIDERATIONS")
    report_lines.append("-" * 40)

    if pop_analysis['israeli_specific_fields']:
        report_lines.append("Israeli-specific fields:")
        for field_info in pop_analysis['israeli_specific_fields']:
            status = "✓ Mapped" if field_info['mapped'] else "✗ Unmapped"
            report_lines.append(f"  {field_info['field']} - {status}")
            report_lines.append(f"    Notes: {field_info['notes']}")
        report_lines.append("")

    # Cohort comparison
    report_lines.append("COMPARISON WITH OTHER COHORTS")
    report_lines.append("-" * 40)
    for cohort, info in analysis_data['cohort_comparison'].items():
        report_lines.append(f"{cohort.upper()}: {info['expected_rate']} - {info['note']}")
    report_lines.append("")

    # Recommendations
    report_lines.append("RECOMMENDATIONS")
    report_lines.append("-" * 40)
    recommendations = generate_recommendations(analysis_data)
    for rec in recommendations:
        report_lines.append(f"• {rec}")
    report_lines.append("")

    return "\n".join(report_lines)

def generate_recommendations(analysis_data):
    """Generate recommendations based on analysis."""

    recommendations = []

    overall = analysis_data['overall']
    mapping_rate = overall['mapping_rate']

    if mapping_rate >= 40:
        recommendations.append("Excellent mapping rate achieved, meeting project expectations")
    elif mapping_rate >= 30:
        recommendations.append("Good mapping rate, consider enhancing LOINC coverage for remaining fields")
    else:
        recommendations.append("Consider additional semantic matching for unmapped high-value fields")

    # Category-specific recommendations
    category_coverage = analysis_data['category_coverage']
    for category, stats in category_coverage.items():
        if stats['mapping_rate'] < 30 and stats['total_fields'] > 2:
            recommendations.append(f"Low coverage in {category} - consider manual review")

    # Population-specific recommendations
    israeli_fields = analysis_data['population_analysis']['israeli_specific_fields']
    unmapped_israeli = [f for f in israeli_fields if not f['mapped']]
    if unmapped_israeli:
        recommendations.append("Consider creating custom mappings for Israeli-specific demographic fields")

    recommendations.append("Document translation considerations for Hebrew text fields")
    recommendations.append("Validate measurement units for diverse population anthropometrics")

    return recommendations

def main():
    """Main execution function."""
    try:
        print("Analyzing Israeli10K demographics mapping coverage...")

        # Load data
        mapped_df, original_df = load_mapping_results()

        # Perform analyses
        print("Analyzing overall coverage...")
        overall_analysis = analyze_overall_coverage(mapped_df, original_df)

        print("Analyzing category coverage...")
        category_analysis = analyze_category_coverage(mapped_df)

        print("Analyzing population considerations...")
        population_analysis = analyze_population_considerations(mapped_df)

        print("Comparing with other cohorts...")
        cohort_comparison = compare_with_other_cohorts()

        # Combine all analysis data
        analysis_data = {
            'overall': overall_analysis['overall'],
            'confidence_distribution': overall_analysis['confidence_distribution'],
            'category_coverage': category_analysis,
            'population_analysis': population_analysis,
            'cohort_comparison': cohort_comparison,
            'timestamp': datetime.now().isoformat()
        }

        # Generate and save report
        print("Generating coverage report...")
        report_text = generate_coverage_report(analysis_data)

        ANALYSIS_OUTPUT_DIR.mkdir(exist_ok=True)

        # Save text report
        with open(COVERAGE_REPORT_FILE, 'w') as f:
            f.write(report_text)

        # Save detailed statistics as JSON
        with open(DETAILED_STATS_FILE, 'w') as f:
            json.dump(analysis_data, f, indent=2)

        print(f"\nCoverage analysis completed!")
        print(f"Report saved to: {COVERAGE_REPORT_FILE}")
        print(f"Detailed statistics: {DETAILED_STATS_FILE}")

        # Print key summary to console
        print("\n" + "="*60)
        print("KEY FINDINGS")
        print("="*60)
        overall = analysis_data['overall']
        print(f"Mapping success rate: {overall['mapping_rate']:.1f}%")
        print(f"Fields successfully mapped: {overall['successfully_mapped']}/{overall['total_processed_fields']}")

        best_category = max(category_analysis.items(), key=lambda x: x[1]['mapping_rate'])
        print(f"Best category: {best_category[0]} ({best_category[1]['mapping_rate']:.1f}%)")

        print(f"\nDetailed analysis available in generated reports.")

    except Exception as e:
        print(f"Error during coverage analysis: {e}")
        raise

if __name__ == "__main__":
    main()
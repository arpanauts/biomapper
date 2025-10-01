#!/usr/bin/env python3
"""
Proto-action: Generate validation report for UKBB to Kraken mapping
This is a STANDALONE script, not a biomapper action

Creates comprehensive validation report with mapping statistics,
coverage analysis, and quality assessment.
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Input paths
RESULTS_DIR = Path(__file__).parent / "results"
DATA_DIR = Path(__file__).parent / "data"
MAPPINGS_FILE = RESULTS_DIR / "ukbb_kraken_mappings.tsv"
STATS_FILE = DATA_DIR / "mapping_stats.json"
REPORT_FILE = RESULTS_DIR / "mapping_validation_report.txt"

def analyze_unmapped_tests(df):
    """Analyze patterns in unmapped tests to identify improvement opportunities."""
    unmapped = df[df['kraken_mapped'] == False].copy()

    if unmapped.empty:
        return "No unmapped tests to analyze."

    analysis = []
    analysis.append(f"Unmapped Tests Analysis ({len(unmapped)} tests):")
    analysis.append("=" * 50)

    # Group by common patterns
    field_patterns = {}
    for _, row in unmapped.iterrows():
        field_name = str(row['ukbb_field_name']).lower()

        # Categorize by common patterns
        if 'freeze-thaw' in field_name or 'cycles' in field_name:
            category = 'metadata_freeze_thaw'
        elif 'acquisition' in field_name or 'device' in field_name:
            category = 'metadata_technical'
        elif 'date' in field_name or 'time' in field_name:
            category = 'metadata_temporal'
        elif 'invitation' in field_name:
            category = 'administrative'
        elif any(x in field_name for x in ['field', 'unknown', 'undefined']):
            category = 'generic_fields'
        else:
            category = 'potential_tests'

        if category not in field_patterns:
            field_patterns[category] = []
        field_patterns[category].append((row['ukbb_field_id'], row['ukbb_field_name']))

    for category, tests in field_patterns.items():
        analysis.append(f"\n{category.replace('_', ' ').title()}: {len(tests)} tests")
        # Show first few examples
        for field_id, field_name in tests[:3]:
            analysis.append(f"  {field_id}: {field_name}")
        if len(tests) > 3:
            analysis.append(f"  ... and {len(tests) - 3} more")

    return "\n".join(analysis)

def analyze_mapping_quality(df):
    """Analyze the quality of successful mappings."""
    mapped = df[df['kraken_mapped'] == True].copy()

    if mapped.empty:
        return "No successful mappings to analyze."

    analysis = []
    analysis.append(f"Mapping Quality Analysis ({len(mapped)} mapped tests):")
    analysis.append("=" * 50)

    # Confidence distribution
    confidence_stats = {
        'perfect (1.0)': len(mapped[mapped['mapping_confidence'] == 1.0]),
        'high (0.9-0.99)': len(mapped[(mapped['mapping_confidence'] >= 0.9) & (mapped['mapping_confidence'] < 1.0)]),
        'good (0.8-0.89)': len(mapped[(mapped['mapping_confidence'] >= 0.8) & (mapped['mapping_confidence'] < 0.9)]),
        'medium (0.5-0.79)': len(mapped[(mapped['mapping_confidence'] >= 0.5) & (mapped['mapping_confidence'] < 0.8)]),
        'low (<0.5)': len(mapped[mapped['mapping_confidence'] < 0.5])
    }

    analysis.append("\nConfidence Score Distribution:")
    for category, count in confidence_stats.items():
        if count > 0:
            pct = 100 * count / len(mapped)
            analysis.append(f"  {category}: {count} ({pct:.1f}%)")

    # Method breakdown
    method_counts = mapped['mapping_method'].value_counts()
    analysis.append("\nMapping Methods Used:")
    for method, count in method_counts.items():
        pct = 100 * count / len(mapped)
        analysis.append(f"  {method}: {count} ({pct:.1f}%)")

    # Show high-confidence mappings
    high_conf = mapped[mapped['mapping_confidence'] >= 0.9].copy()
    if not high_conf.empty:
        analysis.append(f"\nSample High-Confidence Mappings ({len(high_conf)} total):")
        for _, row in high_conf.head(5).iterrows():
            analysis.append(f"  {row['ukbb_field_id']}: {row['ukbb_field_name']}")
            analysis.append(f"    → LOINC:{row['assigned_loinc_code']} → {row['kraken_node_id']} (conf: {row['mapping_confidence']:.2f})")

    return "\n".join(analysis)

def generate_executive_summary(stats):
    """Generate executive summary of mapping results."""
    summary = []
    summary.append("EXECUTIVE SUMMARY")
    summary.append("=" * 50)

    summary.append(f"Total UKBB Chemistry Fields Processed: {stats['total_ukbb_tests']}")
    summary.append(f"Fields with LOINC Codes: {stats['tests_with_loinc']} ({100*stats['loinc_match_rate']:.1f}%)")
    summary.append(f"Fields Mapped to Kraken: {stats['tests_mapped_to_kraken']} ({100*stats['kraken_match_rate']:.1f}%)")

    if stats['tests_with_loinc'] > 0:
        summary.append(f"LOINC→Kraken Success Rate: {100*stats['loinc_to_kraken_rate']:.1f}%")

    # Overall assessment
    overall_rate = stats['kraken_match_rate']
    if overall_rate >= 0.75:
        assessment = "EXCELLENT - Exceeds expected range"
    elif overall_rate >= 0.60:
        assessment = "GOOD - Within expected range"
    elif overall_rate >= 0.40:
        assessment = "MODERATE - Below expected but acceptable"
    else:
        assessment = "LOW - Requires investigation"

    summary.append(f"\nOverall Assessment: {assessment}")

    return "\n".join(summary)

def main():
    """Generate comprehensive validation report."""
    print("Loading mapping results...")

    # Load the mapping results
    if not MAPPINGS_FILE.exists():
        print(f"Error: Mapping results file not found at {MAPPINGS_FILE}")
        return

    df = pd.read_csv(MAPPINGS_FILE, sep='\t')
    print(f"Loaded {len(df)} mapped tests")

    # Load statistics if available
    stats = {}
    if STATS_FILE.exists():
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)

    print("Generating validation report...")

    # Generate report sections
    report_sections = []

    # Header
    report_sections.append("UKBB Clinical Chemistry to Kraken 1.0.0 Mapping Report")
    report_sections.append("=" * 70)
    report_sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_sections.append("")

    # Executive summary
    if stats:
        report_sections.append(generate_executive_summary(stats))
        report_sections.append("")

    # Detailed statistics
    report_sections.append("DETAILED STATISTICS")
    report_sections.append("=" * 50)

    total_tests = len(df)
    mapped_tests = len(df[df['kraken_mapped'] == True])
    with_loinc = len(df[df['has_loinc'] == True])
    without_loinc = len(df[df['has_loinc'] == False])

    report_sections.append(f"Input Processing:")
    report_sections.append(f"  Total UKBB chemistry fields: {total_tests}")
    report_sections.append(f"  Successfully filtered to chemistry tests")
    report_sections.append(f"  Field names normalized and cleaned")

    report_sections.append(f"\nLOINC Code Assignment:")
    report_sections.append(f"  Tests with LOINC codes: {with_loinc} ({100*with_loinc/total_tests:.1f}%)")
    report_sections.append(f"  Tests without LOINC codes: {without_loinc} ({100*without_loinc/total_tests:.1f}%)")

    if stats.get('mapping_methods'):
        report_sections.append(f"\nLOINC Mapping Methods:")
        for method, count in stats['mapping_methods'].items():
            report_sections.append(f"  {method}: {count}")

    report_sections.append(f"\nKraken Node Mapping:")
    report_sections.append(f"  Successfully mapped: {mapped_tests} ({100*mapped_tests/total_tests:.1f}%)")
    report_sections.append(f"  Failed to map: {total_tests - mapped_tests}")

    if with_loinc > 0:
        loinc_to_kraken_rate = mapped_tests / with_loinc
        report_sections.append(f"  LOINC→Kraken success rate: {100*loinc_to_kraken_rate:.1f}%")

    report_sections.append("")

    # Quality analysis
    report_sections.append(analyze_mapping_quality(df))
    report_sections.append("")

    # Unmapped analysis
    report_sections.append(analyze_unmapped_tests(df))
    report_sections.append("")

    # Data validation
    report_sections.append("DATA VALIDATION")
    report_sections.append("=" * 50)

    # Check for required columns
    required_cols = ['ukbb_field_id', 'ukbb_field_name', 'assigned_loinc_code',
                    'kraken_node_id', 'mapping_method', 'mapping_confidence']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        report_sections.append(f"⚠️  Missing required columns: {missing_cols}")
    else:
        report_sections.append("✅ All required columns present")

    # Check data quality
    null_field_ids = df['ukbb_field_id'].isna().sum()
    null_field_names = df['ukbb_field_name'].isna().sum()

    report_sections.append(f"Data Quality Checks:")
    report_sections.append(f"  Null field IDs: {null_field_ids}")
    report_sections.append(f"  Null field names: {null_field_names}")
    report_sections.append(f"  Duplicate field IDs: {df['ukbb_field_id'].duplicated().sum()}")

    # Confidence score validation
    invalid_confidence = len(df[(df['mapping_confidence'] < 0) | (df['mapping_confidence'] > 1)])
    report_sections.append(f"  Invalid confidence scores: {invalid_confidence}")

    report_sections.append("")

    # Recommendations
    report_sections.append("RECOMMENDATIONS")
    report_sections.append("=" * 50)

    recommendations = []

    if stats.get('kraken_match_rate', 0) < 0.7:
        recommendations.append("• Consider expanding manual LOINC mappings for common chemistry tests")

    if stats.get('loinc_to_kraken_rate', 0) < 0.9:
        recommendations.append("• Investigate Kraken LOINC coverage for clinical chemistry tests")

    unmapped_potential = len(df[(df['kraken_mapped'] == False) & (~df['ukbb_field_name'].str.contains('freeze-thaw|acquisition|device|date|time|invitation', case=False, na=False))])
    if unmapped_potential > 0:
        recommendations.append(f"• Review {unmapped_potential} unmapped tests that may be legitimate chemistry tests")

    low_conf_count = len(df[df['mapping_confidence'] < 0.8])
    if low_conf_count > 0:
        recommendations.append(f"• Review {low_conf_count} mappings with confidence < 0.8 for accuracy")

    if not recommendations:
        recommendations.append("• No major issues identified. Mapping quality is satisfactory.")

    for rec in recommendations:
        report_sections.append(rec)

    # Combine all sections
    full_report = "\n".join(report_sections)

    # Save report
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(REPORT_FILE, 'w') as f:
        f.write(full_report)

    print(f"Validation report generated: {REPORT_FILE}")

    # Also print summary to console
    print("\n" + "="*60)
    print("MAPPING RESULTS SUMMARY")
    print("="*60)
    print(f"Total UKBB chemistry fields: {total_tests}")
    print(f"Successfully mapped to Kraken: {mapped_tests} ({100*mapped_tests/total_tests:.1f}%)")
    print(f"Report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
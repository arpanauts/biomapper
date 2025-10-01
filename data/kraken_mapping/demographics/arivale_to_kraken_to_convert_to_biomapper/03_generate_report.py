#!/usr/bin/env python3
"""
Proto-action: Generate comprehensive mapping coverage report
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# Direct file paths - no context/parameters
MAPPING_RESULTS = Path(__file__).parent / "results" / "arivale_demographics_to_kraken_kg.tsv"
OUTPUT_DIR = Path(__file__).parent / "results"

def generate_detailed_report(df):
    """Generate detailed text report of mapping results"""

    report_lines = [
        "=" * 80,
        "ARIVALE DEMOGRAPHICS TO KRAKEN KNOWLEDGE GRAPH MAPPING REPORT",
        "=" * 80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Input data: {len(df)} demographic fields",
        ""
    ]

    # Overall statistics
    total_fields = len(df)
    mapped_fields = df['kraken_node_id'].notna().sum()
    unmapped_fields = total_fields - mapped_fields
    mapping_rate = (mapped_fields / total_fields * 100) if total_fields > 0 else 0

    report_lines.extend([
        "OVERALL MAPPING STATISTICS",
        "-" * 40,
        f"Total demographic fields processed: {total_fields:,}",
        f"Successfully mapped to Kraken: {mapped_fields:,}",
        f"Unmapped fields: {unmapped_fields:,}",
        f"Overall mapping rate: {mapping_rate:.1f}%",
        ""
    ])

    # Confidence score statistics for mapped fields
    mapped_df = df[df['kraken_node_id'].notna()]
    if len(mapped_df) > 0:
        report_lines.extend([
            "CONFIDENCE SCORE STATISTICS (Mapped Fields)",
            "-" * 50,
            f"Mean confidence: {mapped_df['confidence_score'].mean():.3f}",
            f"Median confidence: {mapped_df['confidence_score'].median():.3f}",
            f"Min confidence: {mapped_df['confidence_score'].min():.3f}",
            f"Max confidence: {mapped_df['confidence_score'].max():.3f}",
            ""
        ])

    # Mapping by demographic category
    category_stats = df.groupby('demographic_category').agg({
        'kraken_node_id': ['count', lambda x: x.notna().sum()]
    })
    category_stats.columns = ['total', 'mapped']
    category_stats['unmapped'] = category_stats['total'] - category_stats['mapped']
    category_stats['rate'] = (category_stats['mapped'] / category_stats['total'] * 100).round(1)
    category_stats = category_stats.sort_values('mapped', ascending=False)

    report_lines.extend([
        "MAPPING SUCCESS BY DEMOGRAPHIC CATEGORY",
        "-" * 45,
        f"{'Category':<20} {'Total':<8} {'Mapped':<8} {'Unmapped':<10} {'Rate':<8}",
        f"{'-'*20} {'-'*7} {'-'*7} {'-'*9} {'-'*7}"
    ])

    for category, stats in category_stats.iterrows():
        report_lines.append(
            f"{category:<20} {stats['total']:<8.0f} {stats['mapped']:<8.0f} "
            f"{stats['unmapped']:<10.0f} {stats['rate']:<7.1f}%"
        )

    report_lines.append("")

    # Top successfully mapped fields by category
    report_lines.extend([
        "TOP SUCCESSFULLY MAPPED FIELDS BY CATEGORY",
        "-" * 50
    ])

    for category in category_stats.head(5).index:
        category_mapped = mapped_df[mapped_df['demographic_category'] == category]
        if len(category_mapped) > 0:
            report_lines.append(f"\n{category.upper()} ({len(category_mapped)} fields):")
            top_fields = category_mapped.nlargest(5, 'confidence_score')
            for idx, row in top_fields.iterrows():
                report_lines.append(
                    f"  • {row['field_name']} -> {row['loinc_code']} -> {row['kraken_node_id']}"
                )
                report_lines.append(
                    f"    LOINC: {row['loinc_name']}"
                )
                report_lines.append(
                    f"    Kraken: {row['kraken_name']} (confidence: {row['confidence_score']:.3f})"
                )

    # Unmapped fields analysis
    unmapped_df = df[df['kraken_node_id'].isna()]
    if len(unmapped_df) > 0:
        report_lines.extend([
            "",
            "UNMAPPED FIELDS ANALYSIS",
            "-" * 30,
            f"Total unmapped fields: {len(unmapped_df)}",
            ""
        ])

        # Unmapped by category
        unmapped_by_category = unmapped_df['demographic_category'].value_counts()
        report_lines.append("Unmapped fields by category:")
        for category, count in unmapped_by_category.items():
            report_lines.append(f"  • {category}: {count}")

        # Show fields that had high confidence LOINC mapping but no Kraken match
        high_conf_unmapped = unmapped_df[unmapped_df['confidence_score'] >= 0.8]
        if len(high_conf_unmapped) > 0:
            report_lines.extend([
                "",
                f"High-confidence LOINC mappings without Kraken matches ({len(high_conf_unmapped)}):",
            ])
            for idx, row in high_conf_unmapped.head(10).iterrows():
                report_lines.append(
                    f"  • {row['field_name']} -> {row['loinc_code']} (conf: {row['confidence_score']:.3f})"
                )

    # LOINC coverage analysis
    unique_loinc_codes = df[df['loinc_code'] != 'NO_MATCH']['loinc_code'].nunique()
    mapped_loinc_codes = mapped_df['loinc_code'].nunique()

    report_lines.extend([
        "",
        "LOINC COVERAGE ANALYSIS",
        "-" * 25,
        f"Unique LOINC codes in Arivale data: {unique_loinc_codes}",
        f"LOINC codes successfully mapped to Kraken: {mapped_loinc_codes}",
        f"LOINC code mapping rate: {(mapped_loinc_codes/unique_loinc_codes*100):.1f}%" if unique_loinc_codes > 0 else "N/A",
        ""
    ])

    # Query source analysis for mapped fields
    if 'query_source' in mapped_df.columns:
        query_source_stats = mapped_df['query_source'].value_counts()
        report_lines.extend([
            "MAPPING QUERY SOURCE DISTRIBUTION (Mapped Fields)",
            "-" * 55
        ])
        for source, count in query_source_stats.items():
            pct = (count / len(mapped_df) * 100)
            report_lines.append(f"  • {source}: {count} ({pct:.1f}%)")
        report_lines.append("")

    # Kraken category distribution for mapped fields
    if len(mapped_df) > 0 and 'kraken_category' in mapped_df.columns:
        kraken_categories = mapped_df['kraken_category'].value_counts()
        report_lines.extend([
            "KRAKEN CATEGORY DISTRIBUTION (Mapped Fields)",
            "-" * 45
        ])
        for category, count in kraken_categories.items():
            pct = (count / len(mapped_df) * 100)
            report_lines.append(f"  • {category}: {count} ({pct:.1f}%)")
        report_lines.append("")

    report_lines.extend([
        "=" * 80,
        "END OF REPORT",
        "=" * 80
    ])

    return "\n".join(report_lines)

def main():
    print("Generating comprehensive mapping coverage report...")

    # Load mapping results
    try:
        df = pd.read_csv(MAPPING_RESULTS, sep='\t')
        print(f"Loaded {len(df)} mapping results")
    except FileNotFoundError:
        print(f"Error: Mapping results not found: {MAPPING_RESULTS}")
        print("Please run 02_map_to_kraken.py first")
        return
    except Exception as e:
        print(f"Error loading mapping results: {e}")
        return

    # Generate detailed report
    print("Generating detailed text report...")
    report_content = generate_detailed_report(df)

    # Save report
    report_file = OUTPUT_DIR / "mapping_coverage_report.txt"
    with open(report_file, 'w') as f:
        f.write(report_content)

    print(f"Detailed report saved to: {report_file}")

    # Generate CSV summary for easy analysis
    print("Generating CSV summary...")
    category_summary = df.groupby('demographic_category').agg({
        'field_name': 'count',
        'kraken_node_id': lambda x: x.notna().sum(),
        'confidence_score': ['mean', 'median', 'std']
    }).round(3)

    category_summary.columns = [
        'total_fields', 'mapped_fields', 'mean_confidence', 'median_confidence', 'std_confidence'
    ]
    category_summary['unmapped_fields'] = category_summary['total_fields'] - category_summary['mapped_fields']
    category_summary['mapping_rate'] = (
        category_summary['mapped_fields'] / category_summary['total_fields'] * 100
    ).round(1)

    # Reorder columns
    category_summary = category_summary[[
        'total_fields', 'mapped_fields', 'unmapped_fields', 'mapping_rate',
        'mean_confidence', 'median_confidence', 'std_confidence'
    ]]

    summary_file = OUTPUT_DIR / "mapping_summary_by_category.csv"
    category_summary.to_csv(summary_file, index_label='demographic_category')
    print(f"Category summary saved to: {summary_file}")

    # Display key statistics
    total_fields = len(df)
    mapped_fields = df['kraken_node_id'].notna().sum()
    mapping_rate = (mapped_fields / total_fields * 100) if total_fields > 0 else 0

    print(f"\n" + "="*50)
    print("FINAL MAPPING STATISTICS")
    print("="*50)
    print(f"Total Arivale demographic fields: {total_fields:,}")
    print(f"Successfully mapped to Kraken: {mapped_fields:,}")
    print(f"Overall mapping rate: {mapping_rate:.1f}%")
    print("="*50)

    return df

if __name__ == "__main__":
    main()
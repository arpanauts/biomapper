#!/usr/bin/env python3
"""
Proto-strategy Step 3: Generate Israeli10K to Kraken Mapping Report

This script analyzes the mapping results and generates comprehensive statistics
and validation reports for the Israeli10K questionnaire to Kraken KG mapping.

Input: results/israeli10k_kraken_mappings.tsv
Output: results/mapping_summary.txt + statistics
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

def main():
    print("=== Israeli10K to Kraken Mapping Report Generator ===")

    # Input file
    mappings_file = Path(__file__).parent / "results" / "israeli10k_kraken_mappings.tsv"

    # Output files
    output_dir = Path(__file__).parent / "results"
    summary_file = output_dir / "mapping_summary.txt"
    stats_file = output_dir / "mapping_statistics.tsv"

    print(f"Loading mapping results from: {mappings_file}")

    try:
        # Load mapping results
        df = pd.read_csv(mappings_file, sep='\t', dtype=str)
        print(f"Loaded {len(df)} mapping results")

        # Convert mapping_success to boolean
        df['mapping_success'] = df['mapping_success'].map({'True': True, 'False': False, True: True, False: False})

        # Basic statistics
        total_fields = len(df)
        successful_mappings = df['mapping_success'].sum()
        failed_mappings = total_fields - successful_mappings
        success_rate = (successful_mappings / total_fields * 100) if total_fields > 0 else 0

        print(f"Analysis complete:")
        print(f"  Total fields: {total_fields}")
        print(f"  Successful mappings: {successful_mappings}")
        print(f"  Failed mappings: {failed_mappings}")
        print(f"  Success rate: {success_rate:.1f}%")

        # Generate comprehensive report
        print(f"\nGenerating detailed report...")

        report_content = []
        report_content.append("=" * 70)
        report_content.append("ISRAELI10K QUESTIONNAIRES TO KRAKEN KG MAPPING REPORT")
        report_content.append("=" * 70)
        report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("")

        # Executive Summary
        report_content.append("EXECUTIVE SUMMARY")
        report_content.append("-" * 20)
        report_content.append(f"Total Israeli10K questionnaire fields processed: {total_fields}")
        report_content.append(f"Successfully mapped to Kraken KG: {successful_mappings}")
        report_content.append(f"Failed to map: {failed_mappings}")
        report_content.append(f"Overall success rate: {success_rate:.1f}%")
        report_content.append("")

        # Data Sources
        report_content.append("DATA SOURCES")
        report_content.append("-" * 15)
        report_content.append("Israeli10K: /home/ubuntu/biomapper/data/harmonization/questionnaires/")
        report_content.append("            loinc_questionnaires_to_convert_to_biomapper/results/")
        report_content.append("            israeli10k_questionnaires_weighted_loinc.tsv")
        report_content.append("Kraken KG:  /procedure/data/local_data/MAPPING_ONTOLOGIES/")
        report_content.append("            kraken_1.0.0_ontologies/kraken_1.0.0_clinical_findings.csv")
        report_content.append("")

        # Domain Analysis
        if 'questionnaire_domain' in df.columns:
            report_content.append("QUESTIONNAIRE DOMAIN ANALYSIS")
            report_content.append("-" * 35)
            domain_stats = df.groupby('questionnaire_domain').agg({
                'mapping_success': ['count', 'sum']
            }).round(1)
            domain_stats.columns = ['total', 'mapped']
            domain_stats['success_rate'] = (domain_stats['mapped'] / domain_stats['total'] * 100).round(1)

            for domain, stats in domain_stats.iterrows():
                report_content.append(f"{domain:20} {stats['mapped']:3.0f}/{stats['total']:3.0f} ({stats['success_rate']:5.1f}%)")
            report_content.append("")

        # Confidence Score Analysis
        if 'confidence_score' in df.columns:
            report_content.append("LOINC CONFIDENCE SCORE ANALYSIS")
            report_content.append("-" * 35)

            # Convert to numeric
            df['confidence_score_num'] = pd.to_numeric(df['confidence_score'], errors='coerce')

            # Overall confidence statistics
            conf_stats = df['confidence_score_num'].describe()
            report_content.append(f"Mean confidence score: {conf_stats['mean']:.3f}")
            report_content.append(f"Median confidence score: {conf_stats['50%']:.3f}")
            report_content.append(f"Min confidence score: {conf_stats['min']:.3f}")
            report_content.append(f"Max confidence score: {conf_stats['max']:.3f}")

            # Confidence vs mapping success
            mapped_conf = df[df['mapping_success'] == True]['confidence_score_num'].mean()
            unmapped_conf = df[df['mapping_success'] == False]['confidence_score_num'].mean()
            report_content.append(f"Average confidence - mapped fields: {mapped_conf:.3f}")
            report_content.append(f"Average confidence - unmapped fields: {unmapped_conf:.3f}")
            report_content.append("")

        # Successful Mappings Examples
        successful_df = df[df['mapping_success'] == True]
        if len(successful_df) > 0:
            report_content.append("SUCCESSFUL MAPPING EXAMPLES")
            report_content.append("-" * 30)

            example_cols = ['field_name', 'loinc_code', 'kraken_name']
            available_example_cols = [col for col in example_cols if col in successful_df.columns]

            for i, (_, row) in enumerate(successful_df.head(10).iterrows()):
                report_content.append(f"Example {i+1}:")
                for col in available_example_cols:
                    report_content.append(f"  {col}: {row[col]}")
                report_content.append("")

        # Failed Mappings Analysis
        failed_df = df[df['mapping_success'] == False]
        if len(failed_df) > 0:
            report_content.append("FAILED MAPPING ANALYSIS")
            report_content.append("-" * 25)
            report_content.append(f"Total failed mappings: {len(failed_df)}")

            # Show sample failed mappings
            report_content.append("Sample failed mappings:")
            for i, (_, row) in enumerate(failed_df.head(5).iterrows()):
                report_content.append(f"  {i+1}. Field: {row['field_name']}")
                report_content.append(f"     LOINC: {row['loinc_code']}")
                if 'confidence_score' in row:
                    report_content.append(f"     Confidence: {row['confidence_score']}")
                report_content.append("")

        # Technical Notes
        report_content.append("TECHNICAL NOTES")
        report_content.append("-" * 15)
        report_content.append("- Mapping method: Direct LOINC code matching")
        report_content.append("- ID transformation: Added 'LOINC:' prefix to Israeli10K codes")
        report_content.append("- Join type: Left join (preserves all Israeli10K entries)")
        report_content.append("- No fuzzy matching or similarity algorithms used")
        report_content.append("")

        # Cultural Considerations
        report_content.append("CULTURAL & TRANSLATION CONSIDERATIONS")
        report_content.append("-" * 40)
        report_content.append("- Most Israeli10K questionnaire fields are in English")
        report_content.append("- Fields focus on medical symptoms and health assessments")
        report_content.append("- LOINC harmonization was performed with English medical terminology")
        report_content.append("- Cultural specificity: Questions may reflect Israeli healthcare context")
        report_content.append("")

        # Recommendations
        report_content.append("RECOMMENDATIONS")
        report_content.append("-" * 15)
        report_content.append("1. Review failed mappings for potential LOINC code issues")
        report_content.append("2. Consider manual validation of high-confidence mappings")
        report_content.append("3. Evaluate domain-specific mapping patterns for improvement")
        if success_rate < 50:
            report_content.append("4. Low success rate may indicate LOINC harmonization issues")
        report_content.append("")

        # Write summary report
        print(f"Writing summary report to: {summary_file}")
        with open(summary_file, 'w') as f:
            f.write('\n'.join(report_content))

        # Generate statistics TSV
        print(f"Writing statistics to: {stats_file}")

        stats_data = {
            'metric': [
                'total_fields', 'successful_mappings', 'failed_mappings',
                'success_rate_percent', 'avg_confidence_score'
            ],
            'value': [
                total_fields, successful_mappings, failed_mappings,
                round(success_rate, 1),
                round(df['confidence_score_num'].mean(), 3) if 'confidence_score_num' in df.columns else 'N/A'
            ]
        }

        stats_df = pd.DataFrame(stats_data)
        stats_df.to_csv(stats_file, sep='\t', index=False)

        # Summary output
        print(f"\n✅ Step 3 completed successfully!")
        print(f"   Generated comprehensive mapping report")
        print(f"   Key result: {successful_mappings}/{total_fields} fields mapped ({success_rate:.1f}%)")

        # Return success code based on mapping results
        if successful_mappings > 0:
            print(f"   ✅ Mapping successful - found {successful_mappings} matches")
        else:
            print(f"   ⚠️  No mappings found - may need investigation")

    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        print("Make sure to run step 2 (02_map_to_kraken.py) first")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
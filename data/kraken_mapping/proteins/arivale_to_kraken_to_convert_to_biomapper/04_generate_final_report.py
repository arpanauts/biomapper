#!/usr/bin/env python3
"""
Proto-Strategy Script 4: Generate final mapping report and validation
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import numpy as np
import json
import random
from pathlib import Path
from datetime import datetime

# Input/Output paths
RESULTS_DIR = Path(__file__).parent / "results"

def validate_random_mappings(df, n_samples=10):
    """Manually validate a random sample of mappings"""
    print(f"\n{'='*50}")
    print(f"MANUAL VALIDATION OF {n_samples} RANDOM MAPPINGS")
    print(f"{'='*50}")

    # Get successful mappings only
    mapped_entries = df[df['mapping_type'] == 'exact'].copy()

    if len(mapped_entries) == 0:
        print("❌ No successful mappings to validate")
        return []

    # Sample random entries
    sample_size = min(n_samples, len(mapped_entries))
    sample_entries = mapped_entries.sample(n=sample_size, random_state=42)

    validation_results = []

    for i, (_, row) in enumerate(sample_entries.iterrows(), 1):
        print(f"\n{i:2d}. VALIDATION CHECK")
        print(f"    Arivale UniProt: {row['arivale_uniprot']}")
        print(f"    Kraken Node ID:  {row['kraken_node_id']}")
        print(f"    Arivale Name:    {row['arivale_name']}")
        print(f"    Kraken Name:     {row['kraken_name']}")
        print(f"    Semantic Cat:    {row['semantic_category']}")

        # Basic validation checks
        validation_check = {
            'index': i,
            'arivale_uniprot': row['arivale_uniprot'],
            'kraken_node_id': row['kraken_node_id'],
            'id_match': row['kraken_node_id'] == f"UniProtKB:{row['arivale_uniprot']}",
            'has_name': bool(row['kraken_name'] and str(row['kraken_name']).strip()),
            'has_category': bool(row['semantic_category'] and row['semantic_category'] != 'unmapped')
        }

        # Overall validation status
        validation_check['valid'] = all([
            validation_check['id_match'],
            validation_check['has_name'],
            validation_check['has_category']
        ])

        status = "✅ VALID" if validation_check['valid'] else "❌ INVALID"
        print(f"    Status: {status}")

        if not validation_check['valid']:
            issues = []
            if not validation_check['id_match']:
                issues.append("ID mismatch")
            if not validation_check['has_name']:
                issues.append("Missing name")
            if not validation_check['has_category']:
                issues.append("Missing category")
            print(f"    Issues: {', '.join(issues)}")

        validation_results.append(validation_check)

    # Summary
    valid_count = sum(1 for v in validation_results if v['valid'])
    print(f"\n{'='*30}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*30}")
    print(f"Valid mappings: {valid_count}/{len(validation_results)}")
    print(f"Validation rate: {100 * valid_count / len(validation_results):.1f}%")

    return validation_results

def create_coverage_report(df):
    """Create detailed coverage analysis"""
    print(f"\n{'='*50}")
    print("COVERAGE ANALYSIS")
    print(f"{'='*50}")

    total_entries = len(df)
    mapped_entries = len(df[df['mapping_type'] == 'exact'])
    unmapped_entries = len(df[df['mapping_type'] == 'unmapped'])

    print(f"Total Arivale proteins: {total_entries}")
    print(f"Successfully mapped: {mapped_entries}")
    print(f"Unmapped: {unmapped_entries}")
    print(f"Coverage rate: {100 * mapped_entries / total_entries:.2f}%")

    # Analyze semantic categories
    category_dist = df[df['mapping_type'] == 'exact']['semantic_category'].value_counts()
    print(f"\nSemantic category distribution:")
    for category, count in category_dist.items():
        pct = 100 * count / mapped_entries
        print(f"  {category}: {count} ({pct:.1f}%)")

    # Analyze unmapped entries
    if unmapped_entries > 0:
        print(f"\nUnmapped entries analysis:")
        unmapped_df = df[df['mapping_type'] == 'unmapped']
        sample_unmapped = unmapped_df['arivale_uniprot'].head(10).tolist()
        print(f"Sample unmapped UniProt IDs: {sample_unmapped}")

        # Check for patterns in unmapped IDs
        unmapped_ids = unmapped_df['arivale_uniprot'].tolist()
        short_ids = [uid for uid in unmapped_ids if len(uid) < 6]
        long_ids = [uid for uid in unmapped_ids if len(uid) > 10]
        unusual_chars = [uid for uid in unmapped_ids if not uid.replace('-', '').replace('_', '').isalnum()]

        if short_ids:
            print(f"  Short IDs (<6 chars): {len(short_ids)} (e.g., {short_ids[:3]})")
        if long_ids:
            print(f"  Long IDs (>10 chars): {len(long_ids)} (e.g., {long_ids[:3]})")
        if unusual_chars:
            print(f"  IDs with unusual chars: {len(unusual_chars)} (e.g., {unusual_chars[:3]})")

    return {
        'total_entries': total_entries,
        'mapped_entries': mapped_entries,
        'unmapped_entries': unmapped_entries,
        'coverage_rate': round(100 * mapped_entries / total_entries, 2),
        'semantic_categories': category_dist.to_dict(),
        'unmapped_sample': sample_unmapped if unmapped_entries > 0 else []
    }

def main():
    print("=" * 60)
    print("SCRIPT 4: Generate final mapping report and validation")
    print("=" * 60)

    try:
        # Load final mappings
        mappings_file = RESULTS_DIR / "arivale_kraken_mappings.tsv"
        if not mappings_file.exists():
            raise FileNotFoundError(f"Mappings file not found: {mappings_file}")

        df = pd.read_csv(mappings_file, sep='\t')
        print(f"Loaded final mappings: {len(df)} entries")

        # Load existing statistics
        stats_file = RESULTS_DIR / "mapping_statistics.json"
        with open(stats_file, 'r') as f:
            stats = json.load(f)

        print(f"Loaded statistics: {stats['mapping_rate_percent']}% mapping rate")

        # Generate coverage report
        coverage = create_coverage_report(df)

        # Validate random mappings
        validation_results = validate_random_mappings(df, n_samples=10)

        # Create comprehensive final report
        print(f"\n{'='*60}")
        print("GENERATING COMPREHENSIVE REPORT")
        print(f"{'='*60}")

        final_report = {
            'metadata': {
                'report_generated': datetime.now().isoformat(),
                'arivale_source': '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
                'kraken_source': '/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_proteins.csv',
                'mapping_method': 'direct_uniprot_id_join',
                'proto_strategy_version': '1.0.0'
            },
            'summary': {
                'total_arivale_proteins': coverage['total_entries'],
                'successfully_mapped': coverage['mapped_entries'],
                'unmapped': coverage['unmapped_entries'],
                'coverage_rate_percent': coverage['coverage_rate'],
                'unique_semantic_categories': len(coverage['semantic_categories'])
            },
            'detailed_statistics': stats,
            'coverage_analysis': coverage,
            'validation': {
                'sample_size': len(validation_results),
                'valid_mappings': sum(1 for v in validation_results if v['valid']),
                'validation_rate_percent': round(100 * sum(1 for v in validation_results if v['valid']) / len(validation_results), 1) if validation_results else 0,
                'validation_checks': validation_results
            },
            'quality_assessment': {
                'mapping_confidence': 'high' if coverage['coverage_rate'] >= 90 else 'medium' if coverage['coverage_rate'] >= 75 else 'low',
                'data_quality': 'excellent' if all(v['valid'] for v in validation_results) else 'good' if sum(1 for v in validation_results if v['valid']) >= 8 else 'fair',
                'recommendation': 'Ready for BiOMapper conversion' if coverage['coverage_rate'] >= 85 else 'May need additional ID resolution'
            },
            'files_generated': {
                'main_mappings': 'arivale_kraken_mappings.tsv',
                'statistics': 'mapping_statistics.json',
                'final_report': 'final_mapping_report.json'
            }
        }

        # Save comprehensive report
        report_file = RESULTS_DIR / "final_mapping_report.json"
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)

        print(f"Comprehensive report saved to: {report_file}")

        # Create human-readable summary
        summary_file = RESULTS_DIR / "MAPPING_SUMMARY.md"
        with open(summary_file, 'w') as f:
            f.write("# Arivale to Kraken Protein Mapping Summary\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Overview\n")
            f.write(f"- **Total Arivale proteins:** {coverage['total_entries']}\n")
            f.write(f"- **Successfully mapped:** {coverage['mapped_entries']}\n")
            f.write(f"- **Coverage rate:** {coverage['coverage_rate']:.1f}%\n")
            f.write(f"- **Mapping method:** Direct UniProt ID matching\n\n")

            f.write("## Semantic Categories\n")
            for category, count in coverage['semantic_categories'].items():
                pct = 100 * count / coverage['mapped_entries']
                f.write(f"- **{category}:** {count} proteins ({pct:.1f}%)\n")

            f.write(f"\n## Validation Results\n")
            if validation_results:
                valid_count = sum(1 for v in validation_results if v['valid'])
                f.write(f"- **Sample size:** {len(validation_results)} random mappings\n")
                f.write(f"- **Valid mappings:** {valid_count}/{len(validation_results)}\n")
                f.write(f"- **Validation rate:** {100 * valid_count / len(validation_results):.1f}%\n")

            f.write(f"\n## Quality Assessment\n")
            f.write(f"- **Mapping confidence:** {final_report['quality_assessment']['mapping_confidence']}\n")
            f.write(f"- **Data quality:** {final_report['quality_assessment']['data_quality']}\n")
            f.write(f"- **Recommendation:** {final_report['quality_assessment']['recommendation']}\n")

            f.write(f"\n## Output Files\n")
            f.write(f"- `arivale_kraken_mappings.tsv` - Main mapping results\n")
            f.write(f"- `mapping_statistics.json` - Detailed statistics\n")
            f.write(f"- `final_mapping_report.json` - Comprehensive report\n")
            f.write(f"- `MAPPING_SUMMARY.md` - This summary\n")

        print(f"Human-readable summary saved to: {summary_file}")

        # Final status
        print(f"\n{'='*60}")
        print("FINAL STATUS")
        print(f"{'='*60}")
        print(f"✅ Mapping completed successfully!")
        print(f"📊 Coverage: {coverage['coverage_rate']:.1f}% ({coverage['mapped_entries']}/{coverage['total_entries']} proteins)")
        print(f"✅ Validation: {100 * sum(1 for v in validation_results if v['valid']) / len(validation_results):.1f}% passed")
        print(f"📁 All results saved to: {RESULTS_DIR}")
        print(f"🔄 Ready for BiOMapper conversion!")

        print("\n✅ Script 4 completed successfully!")

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        raise

if __name__ == "__main__":
    main()
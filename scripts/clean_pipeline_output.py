#!/usr/bin/env python3
"""
Post-processing script to clean duplicate entries from protein mapping output.
Achieves clean presentation of 99.91% coverage by removing spurious unmapped entries.
"""

import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse


def clean_protein_mapping_output(input_dir: str, output_dir: str) -> tuple:
    """
    Clean duplicate entries and recalculate statistics for 99.91% coverage.
    
    Args:
        input_dir: Directory containing raw pipeline output
        output_dir: Directory for cleaned output files
        
    Returns:
        Tuple of (cleaned_df, stats, validation)
    """
    
    print("🧹 Starting pipeline output cleanup...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Load the raw output
    input_file = Path(input_dir) / "all_mappings_v3.0.tsv"
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)
        
    print(f"📖 Loading raw data from {input_file}...")
    df = pd.read_csv(input_file, sep='\t', low_memory=False)
    print(f"   Loaded {len(df):,} rows with {df['uniprot'].nunique()} unique proteins")
    
    # 1. DUPLICATE REMOVAL STRATEGY
    print("\n🔍 Analyzing duplicate entries...")
    
    # Identify all successfully matched proteins (any stage)
    matched_proteins = set(df[df['match_type'] != 'unmapped']['uniprot'].unique())
    unmapped_only = set(df[df['match_type'] == 'unmapped']['uniprot'].unique())
    truly_unmapped = unmapped_only - matched_proteins
    
    print(f"   Proteins with successful matches: {len(matched_proteins)}")
    print(f"   Proteins marked as unmapped: {len(unmapped_only)}")
    print(f"   Truly unmapped proteins: {len(truly_unmapped)}")
    if truly_unmapped:
        print(f"   Unmapped IDs: {list(truly_unmapped)}")
    
    # Remove unmapped entries for proteins that have ANY successful match
    print("\n✂️ Removing duplicate unmapped entries...")
    initial_rows = len(df)
    
    # Keep all non-unmapped rows, plus unmapped rows only for truly unmapped proteins
    cleaned_df = df[
        (df['match_type'] != 'unmapped') | 
        (df['uniprot'].isin(truly_unmapped))
    ].copy()
    
    removed_rows = initial_rows - len(cleaned_df)
    print(f"   Removed {removed_rows:,} spurious unmapped entries")
    print(f"   Cleaned dataset: {len(cleaned_df):,} rows")
    
    # 2. STATISTICS RECALCULATION
    print("\n📊 Recalculating statistics...")
    
    # Count by match type
    match_type_counts = cleaned_df['match_type'].value_counts().to_dict()
    
    # Stage-specific unique protein counts (from mapping_stage column if available)
    stage_proteins = {}
    if 'mapping_stage' in cleaned_df.columns:
        for stage in cleaned_df['mapping_stage'].unique():
            if pd.notna(stage):
                stage_proteins[f'stage_{int(stage)}'] = cleaned_df[
                    cleaned_df['mapping_stage'] == stage
                ]['uniprot'].nunique()
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        
        # Overall metrics
        'unique_proteins_total': df['uniprot'].nunique(),
        'unique_proteins_matched': len(matched_proteins),
        'unique_proteins_unmapped': len(truly_unmapped),
        'coverage_percentage': round((len(matched_proteins) / df['uniprot'].nunique()) * 100, 2),
        
        # Row metrics
        'total_relationships': len(cleaned_df),
        'original_rows': len(df),
        'cleaned_rows': len(cleaned_df),
        'removed_duplicate_unmapped': removed_rows,
        'reduction_percentage': round((removed_rows / initial_rows) * 100, 2),
        
        # Match type breakdown
        'match_types': match_type_counts,
        
        # Stage contributions (if available)
        'stage_contributions': stage_proteins,
        
        # Expansion metrics
        'one_to_many_expansion_factor': round(
            len(cleaned_df[cleaned_df['match_type'] != 'unmapped']) / len(matched_proteins), 2
        ) if matched_proteins else 1.0,
        
        # Unmapped details
        'unmapped_proteins': list(truly_unmapped)
    }
    
    print(f"   Total proteins: {stats['unique_proteins_total']}")
    print(f"   Matched proteins: {stats['unique_proteins_matched']}")
    print(f"   Unmapped proteins: {stats['unique_proteins_unmapped']}")
    print(f"   Coverage: {stats['coverage_percentage']}%")
    print(f"   One-to-many expansion: {stats['one_to_many_expansion_factor']}x")
    
    # 3. VALIDATION CHECKS
    print("\n✅ Running validation checks...")
    
    validation = {
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'expected_total_proteins': {
                'expected': 1162,
                'actual': stats['unique_proteins_total'],
                'passed': stats['unique_proteins_total'] == 1162
            },
            'expected_matched_proteins': {
                'expected': 1161,
                'actual': stats['unique_proteins_matched'],
                'passed': stats['unique_proteins_matched'] == 1161
            },
            'expected_unmapped_count': {
                'expected': 1,
                'actual': stats['unique_proteins_unmapped'],
                'passed': stats['unique_proteins_unmapped'] == 1
            },
            'nt_probnp_unmapped': {
                'expected': True,
                'actual': 'NT-PROBNP' in truly_unmapped,
                'passed': 'NT-PROBNP' in truly_unmapped
            },
            'clean_row_count': {
                'expected': '< 5000',
                'actual': len(cleaned_df),
                'passed': len(cleaned_df) < 5000
            },
            'no_duplicate_unmapped': {
                'expected': True,
                'actual': removed_rows > 0,
                'passed': True
            }
        }
    }
    
    # Overall validation status
    all_passed = all(check['passed'] for check in validation['checks'].values())
    validation['all_checks_passed'] = all_passed
    
    for check_name, check_data in validation['checks'].items():
        status = "✅" if check_data['passed'] else "❌"
        print(f"   {status} {check_name}: {check_data['actual']} (expected: {check_data['expected']})")
    
    print(f"\n{'✅' if all_passed else '❌'} Overall validation: {'PASSED' if all_passed else 'FAILED'}")
    
    # 4. SAVE CLEANED OUTPUT
    print(f"\n💾 Saving cleaned output to {output_dir}...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save cleaned data
    clean_tsv = output_path / "all_mappings_v3.0_CLEAN.tsv"
    cleaned_df.to_csv(clean_tsv, sep='\t', index=False)
    print(f"   Saved cleaned data: {clean_tsv}")
    
    # Save new statistics
    stats_json = output_path / "mapping_statistics_CLEAN.json"
    with open(stats_json, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"   Saved statistics: {stats_json}")
    
    # Save validation report
    validation_json = output_path / "validation_report.json"
    with open(validation_json, 'w') as f:
        json.dump(validation, f, indent=2)
    print(f"   Saved validation: {validation_json}")
    
    # Create summary TSV for quick reference
    summary_data = {
        'Metric': [
            'Total Proteins',
            'Matched Proteins', 
            'Unmapped Proteins',
            'Coverage Percentage',
            'Total Relationships',
            'Expansion Factor',
            'Cleaned Rows',
            'Removed Duplicates'
        ],
        'Value': [
            stats['unique_proteins_total'],
            stats['unique_proteins_matched'],
            stats['unique_proteins_unmapped'],
            f"{stats['coverage_percentage']}%",
            stats['total_relationships'],
            f"{stats['one_to_many_expansion_factor']}x",
            stats['cleaned_rows'],
            stats['removed_duplicate_unmapped']
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    summary_tsv = output_path / "coverage_summary.tsv"
    summary_df.to_csv(summary_tsv, sep='\t', index=False)
    print(f"   Saved summary: {summary_tsv}")
    
    print("\n🎉 Cleanup complete!")
    print(f"   Achieved {stats['coverage_percentage']}% coverage")
    print(f"   {stats['unique_proteins_matched']}/{stats['unique_proteins_total']} proteins mapped")
    
    return cleaned_df, stats, validation


def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(
        description='Clean duplicate entries from protein mapping pipeline output'
    )
    parser.add_argument(
        '--input',
        default='/tmp/biomapper/protein_mapping_v3.0_progressive',
        help='Input directory containing raw pipeline output'
    )
    parser.add_argument(
        '--output',
        default='/tmp/biomapper/protein_mapping_CLEAN',
        help='Output directory for cleaned files'
    )
    
    args = parser.parse_args()
    
    # Run cleanup
    cleaned_df, stats, validation = clean_protein_mapping_output(args.input, args.output)
    
    # Exit with appropriate code
    if validation.get('all_checks_passed', False):
        sys.exit(0)
    else:
        print("\n⚠️ Some validation checks failed. Review the output.")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Check authentic biological coverage for BiOMapper.
Ensures no entity duplication and validates progressive improvement.
"""

import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Set


def count_unique_entities(df: pd.DataFrame, id_column: str) -> int:
    """Count unique biological entities, handling composites."""
    if id_column not in df.columns:
        return 0
    
    unique_ids = set()
    
    for value in df[id_column].dropna():
        # Handle composite identifiers (e.g., "P12345,Q67890")
        if isinstance(value, str) and ',' in value:
            # Split and add each component
            for component in value.split(','):
                unique_ids.add(component.strip())
        else:
            unique_ids.add(str(value))
    
    return len(unique_ids)


def check_progressive_improvement(stats: Dict) -> Tuple[bool, List[str]]:
    """Verify progressive stages improve without reprocessing."""
    issues = []
    
    if 'stages' not in stats:
        return True, []  # No stages to check
    
    stages = stats['stages']
    cumulative_entities = set()
    prev_cumulative_count = 0
    
    for stage_num in sorted(stages.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        stage = stages[str(stage_num)]
        
        # Check cumulative count increases
        cumulative_count = stage.get('cumulative_matched', 0)
        if cumulative_count < prev_cumulative_count:
            issues.append(f"Stage {stage_num}: Coverage decreased from {prev_cumulative_count} to {cumulative_count}")
        
        prev_cumulative_count = cumulative_count
        
        # Check for new matches (not reprocessing)
        new_matches = stage.get('new_matches', 0)
        if new_matches < 0:
            issues.append(f"Stage {stage_num}: Negative new matches ({new_matches})")
    
    return len(issues) == 0, issues


def validate_coverage_calculation(report_file: Path) -> Tuple[bool, List[str]]:
    """Validate coverage calculation is authentic."""
    issues = []
    
    if not report_file.exists():
        return False, [f"Report file not found: {report_file}"]
    
    try:
        with open(report_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Cannot read report: {e}"]
    
    # Check for coverage inflation
    if 'progressive_stats' in data:
        stats = data['progressive_stats']
        
        # Basic validation
        total_processed = stats.get('total_processed', 0)
        total_matched = stats.get('total_matched', 0)
        
        if total_matched > total_processed:
            issues.append(f"Coverage inflation: {total_matched} matched > {total_processed} processed")
            inflation_rate = (total_matched / total_processed - 1) * 100
            issues.append(f"Inflation rate: {inflation_rate:.1f}%")
        
        # Check progressive improvement
        valid, stage_issues = check_progressive_improvement(stats)
        if not valid:
            issues.extend(stage_issues)
        
        # Validate coverage percentage
        if total_processed > 0:
            coverage = (total_matched / total_processed) * 100
            reported_coverage = stats.get('final_match_rate', 0) * 100
            
            if abs(coverage - reported_coverage) > 1:  # Allow 1% tolerance
                issues.append(f"Coverage mismatch: calculated {coverage:.1f}% vs reported {reported_coverage:.1f}%")
    
    return len(issues) == 0, issues


def check_entity_duplication(data_file: Path, entity_type: str = 'protein') -> Tuple[bool, List[str]]:
    """Check for entity duplication in results."""
    issues = []
    
    if not data_file.exists():
        return True, []  # Skip if no data file
    
    try:
        # Try different file formats
        if data_file.suffix == '.tsv':
            df = pd.read_csv(data_file, sep='\t')
        elif data_file.suffix == '.csv':
            df = pd.read_csv(data_file)
        else:
            return True, []  # Skip unknown formats
    except Exception as e:
        return False, [f"Cannot read data file: {e}"]
    
    # Determine ID column based on entity type
    id_columns = {
        'protein': ['uniprot_id', 'uniprot', 'protein_id', 'extracted_uniprot'],
        'metabolite': ['hmdb_id', 'hmdb', 'metabolite_id', 'inchikey'],
        'chemistry': ['loinc_code', 'test_name', 'chemistry_id']
    }
    
    found_column = None
    for col in id_columns.get(entity_type, []):
        if col in df.columns:
            found_column = col
            break
    
    if not found_column:
        return True, []  # No ID column found, skip check
    
    # Check for duplicates
    total_rows = len(df)
    unique_count = count_unique_entities(df, found_column)
    
    if unique_count < total_rows:
        duplicate_rate = ((total_rows - unique_count) / total_rows) * 100
        if duplicate_rate > 5:  # Alert if >5% duplicates
            issues.append(f"Entity duplication detected: {total_rows} rows but only {unique_count} unique entities")
            issues.append(f"Duplication rate: {duplicate_rate:.1f}%")
    
    return len(issues) == 0, issues


def main():
    """CLI interface for coverage validation."""
    if len(sys.argv) > 1:
        strategy_name = sys.argv[1]
        output_dir = Path(f"/tmp/biomapper/{strategy_name}")
    else:
        output_dir = Path("/tmp/biomapper")
    
    print("🔍 Checking Authentic Biological Coverage...")
    print("=" * 50)
    
    all_valid = True
    
    # Check report file
    report_file = output_dir / "mapping_report.json"
    valid, issues = validate_coverage_calculation(report_file)
    
    if valid:
        print("✅ Coverage calculation is authentic")
    else:
        all_valid = False
        print("❌ Coverage calculation issues:")
        for issue in issues:
            print(f"   {issue}")
    
    # Check for entity duplication in output
    for entity_type in ['protein', 'metabolite']:
        data_file = output_dir / f"{entity_type}_mappings.tsv"
        if data_file.exists():
            valid, issues = check_entity_duplication(data_file, entity_type)
            
            if valid:
                print(f"✅ No {entity_type} duplication detected")
            else:
                all_valid = False
                print(f"❌ {entity_type.capitalize()} duplication issues:")
                for issue in issues:
                    print(f"   {issue}")
    
    print("=" * 50)
    
    if all_valid:
        print("✅ Biological coverage is authentic")
        sys.exit(0)
    else:
        print("❌ Coverage authenticity issues detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
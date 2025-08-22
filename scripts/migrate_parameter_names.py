#!/usr/bin/env python3
"""
Migrate YAML strategy files to use standard parameter names.

This script helps migrate existing YAML strategy files from old parameter
names to the new standard names defined in PARAMETER_NAMING_STANDARD.md.

Usage:
    python scripts/migrate_parameter_names.py path/to/strategy.yaml
    python scripts/migrate_parameter_names.py --check path/to/strategy.yaml
    python scripts/migrate_parameter_names.py --all src/configs/strategies/
"""

import yaml
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import shutil
from datetime import datetime
import re

# Parameter migration mappings
PARAMETER_MIGRATIONS = {
    # File paths
    'output_dir': 'directory_path',
    'output_directory': 'directory_path',
    'csv_path': 'file_path',
    'tsv_path': 'file_path',
    'input_file': 'file_path',
    'input_path': 'file_path',
    'filepath': 'file_path',
    'output_file': 'output_path',
    'output_filename': 'output_path',
    
    # Dataset keys
    'dataset_key': 'input_key',
    'dataset1_key': 'input_key',
    'dataset2_key': 'input_key_2',
    'dataset3_key': 'input_key_3',
    'source_dataset': 'source_key',
    'target_dataset': 'target_key',
    'source_dataset_key': 'source_key',
    'target_dataset_key': 'target_key',
    'output_context_key': 'output_key',
    'result_key': 'output_key',
    
    # Column names
    'id_column': 'identifier_column',
    'id_col': 'identifier_column',
    'identifier_col': 'identifier_column',
    'join_column': 'merge_column',
    'merge_on': 'merge_column',
    'join_on': 'merge_column',
    'name_col': 'name_column',
    'value_col': 'value_column',
    'desc_column': 'description_column',
    
    # Boolean flags (convert to standard format)
    'enable_stage_1': 'stage_1_enabled',
    'enable_stage_2': 'stage_2_enabled',
    'enable_stage_3': 'stage_3_enabled',
    'enable_stage_4': 'stage_4_enabled',
    'ignore_case': 'case_sensitive',  # Note: inverted logic
    'has_header': 'include_header',
    'with_header': 'include_header',
    'force': 'overwrite',
    'replace_existing': 'overwrite',
    'debug': 'verbose',
    'detailed_output': 'verbose',
    'strict_mode': 'strict',
    
    # API/Service parameters
    'apikey': 'api_key',
    'auth_key': 'api_key',
    'endpoint': 'api_endpoint',
    'api_url': 'api_endpoint',
    'service_url': 'api_endpoint',
    'api_timeout': 'request_timeout',
    'http_timeout': 'request_timeout',
    'retry_count': 'max_retries',
    'retries': 'max_retries',
    
    # Processing parameters
    'thresh': 'threshold',
    'cutoff': 'threshold',
    'min_threshold': 'threshold',
    'maximum': 'max_limit',
    'max_value': 'max_limit',
    'limit': 'max_limit',
    'minimum': 'min_limit',
    'min_value': 'min_limit',
    'chunk_size': 'batch_size',
    'batch_count': 'batch_size',
    'timeout': 'timeout_seconds',
    'max_timeout': 'timeout_seconds',
}

# Actions that commonly use these parameters
AFFECTED_ACTIONS = [
    'GENERATE_MAPPING_VISUALIZATIONS',
    'GENERATE_LLM_ANALYSIS',
    'SYNC_TO_GOOGLE_DRIVE_V2',
    'LOAD_DATASET_IDENTIFIERS',
    'EXPORT_DATASET',
    'MERGE_DATASETS',
    'CUSTOM_TRANSFORM',
]


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load a YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def save_yaml_file(file_path: Path, data: Dict[str, Any], backup: bool = True):
    """Save a YAML file with optional backup."""
    if backup and file_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.yaml.backup_{timestamp}')
        shutil.copy2(file_path, backup_path)
        print(f"  Created backup: {backup_path}")
    
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)


def find_parameters_to_migrate(data: Any, path: str = "") -> List[Tuple[str, str, str]]:
    """
    Recursively find parameters that need migration.
    Returns list of (path, old_name, new_name) tuples.
    """
    migrations = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if this key needs migration
            if key in PARAMETER_MIGRATIONS:
                migrations.append((current_path, key, PARAMETER_MIGRATIONS[key]))
            
            # Recurse into nested structures
            migrations.extend(find_parameters_to_migrate(value, current_path))
            
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            migrations.extend(find_parameters_to_migrate(item, current_path))
    
    return migrations


def migrate_parameters(data: Any, dry_run: bool = False) -> Tuple[Any, List[str]]:
    """
    Recursively migrate parameters in the data structure.
    Returns the migrated data and a list of changes made.
    """
    changes = []
    
    if isinstance(data, dict):
        migrated = {}
        for key, value in data.items():
            # Check if this is an action that commonly uses old parameters
            if key == 'type' and value in AFFECTED_ACTIONS:
                changes.append(f"  Found affected action: {value}")
            
            # Migrate the key if needed
            new_key = PARAMETER_MIGRATIONS.get(key, key)
            if new_key != key:
                changes.append(f"  Migrated parameter: {key} → {new_key}")
                if not dry_run:
                    key = new_key
            
            # Handle special case for inverted boolean logic
            if key == 'ignore_case' and new_key == 'case_sensitive':
                # Invert the boolean value
                if isinstance(value, bool):
                    value = not value
                    changes.append(f"    Inverted boolean value for case_sensitive")
            
            # Recurse into nested structures
            migrated_value, nested_changes = migrate_parameters(value, dry_run)
            migrated[key] = migrated_value
            changes.extend(nested_changes)
            
        return migrated, changes
        
    elif isinstance(data, list):
        migrated = []
        for item in data:
            migrated_item, nested_changes = migrate_parameters(item, dry_run)
            migrated.append(migrated_item)
            changes.extend(nested_changes)
        return migrated, changes
        
    else:
        return data, changes


def check_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """Check a file for parameters that need migration."""
    print(f"\nChecking: {file_path}")
    
    try:
        data = load_yaml_file(file_path)
        migrations = find_parameters_to_migrate(data)
        
        if migrations:
            print(f"  Found {len(migrations)} parameter(s) to migrate:")
            for path, old_name, new_name in migrations:
                print(f"    {path}: {old_name} → {new_name}")
        else:
            print("  ✓ No migrations needed")
        
        return migrations
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []


def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """Migrate a single YAML file."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating: {file_path}")
    
    try:
        # Load the file
        data = load_yaml_file(file_path)
        
        # Migrate parameters
        migrated_data, changes = migrate_parameters(data, dry_run)
        
        if changes:
            print(f"  Made {len(set(changes))} migration(s):")
            for change in set(changes):
                print(f"  {change}")
            
            if not dry_run:
                # Save the migrated file
                save_yaml_file(file_path, migrated_data, backup=True)
                print(f"  ✓ File migrated successfully")
        else:
            print("  ✓ No migrations needed")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def process_directory(directory: Path, check_only: bool = False, dry_run: bool = False) -> None:
    """Process all YAML files in a directory."""
    yaml_files = list(directory.rglob("*.yaml")) + list(directory.rglob("*.yml"))
    
    print(f"\nFound {len(yaml_files)} YAML file(s) in {directory}")
    
    if check_only:
        print("\n=== CHECKING FOR MIGRATIONS ===")
        total_migrations = 0
        for file_path in yaml_files:
            migrations = check_file(file_path)
            total_migrations += len(migrations)
        
        print(f"\n=== SUMMARY ===")
        print(f"Total files checked: {len(yaml_files)}")
        print(f"Total migrations needed: {total_migrations}")
        
    else:
        print(f"\n=== {'DRY RUN' if dry_run else 'MIGRATING'} FILES ===")
        success_count = 0
        for file_path in yaml_files:
            if migrate_file(file_path, dry_run):
                success_count += 1
        
        print(f"\n=== SUMMARY ===")
        print(f"Total files processed: {len(yaml_files)}")
        print(f"Successfully migrated: {success_count}")
        if len(yaml_files) > success_count:
            print(f"Failed: {len(yaml_files) - success_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate YAML strategy files to use standard parameter names",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a single file for needed migrations
  python scripts/migrate_parameter_names.py --check path/to/strategy.yaml
  
  # Migrate a single file (creates backup)
  python scripts/migrate_parameter_names.py path/to/strategy.yaml
  
  # Dry run on a single file (shows changes without applying)
  python scripts/migrate_parameter_names.py --dry-run path/to/strategy.yaml
  
  # Check all files in a directory
  python scripts/migrate_parameter_names.py --check --all src/configs/strategies/
  
  # Migrate all files in a directory
  python scripts/migrate_parameter_names.py --all src/configs/strategies/
  
  # Dry run on all files in a directory
  python scripts/migrate_parameter_names.py --dry-run --all src/configs/strategies/
        """
    )
    
    parser.add_argument('path', nargs='?', help='Path to YAML file or directory')
    parser.add_argument('--check', action='store_true', help='Check for migrations without applying')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--all', action='store_true', help='Process all YAML files in directory')
    
    args = parser.parse_args()
    
    if not args.path:
        parser.print_help()
        sys.exit(1)
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)
    
    print("=" * 60)
    print("YAML PARAMETER MIGRATION TOOL")
    print("=" * 60)
    print(f"Mode: {'CHECK' if args.check else 'DRY RUN' if args.dry_run else 'MIGRATE'}")
    print(f"Path: {path}")
    
    if args.all or path.is_dir():
        if not path.is_dir():
            print(f"Error: --all specified but path is not a directory: {path}")
            sys.exit(1)
        process_directory(path, check_only=args.check, dry_run=args.dry_run)
    else:
        if not path.is_file():
            print(f"Error: Path is not a file: {path}")
            sys.exit(1)
        if args.check:
            check_file(path)
        else:
            migrate_file(path, dry_run=args.dry_run)
    
    print("\n" + "=" * 60)
    print("Migration tool completed")
    print("=" * 60)


if __name__ == '__main__':
    main()
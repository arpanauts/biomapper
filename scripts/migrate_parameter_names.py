#!/usr/bin/env python3
"""
Migration script to standardize parameter names across all biomapper actions and strategies.
Creates backups and generates detailed reports of all changes.
"""

import os
import re
import ast
import json
import yaml
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

# Import the parameter validator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from biomapper.core.standards.parameter_validator import ParameterValidator


class ParameterMigrator:
    """Migrates parameter names to follow established standards."""
    
    # Migration mapping from old names to new names
    PARAM_MAPPING = {
        # Input dataset variations
        'dataset_key': 'input_key',
        'dataset1_key': 'input_key',
        'input_context_key': 'input_key',
        'source_dataset_key': 'input_key',
        'input_dataset': 'input_key',
        
        # Output dataset variations
        'output_context_key': 'output_key',
        'result_key': 'output_key',
        'output_dataset': 'output_key',
        
        # Source/target variations
        'source_dataset': 'source_key',
        'from_dataset': 'source_key',
        'target_dataset': 'target_key',
        'to_dataset': 'target_key',
        
        # File path variations
        'csv_path': 'file_path',
        'tsv_path': 'file_path',
        'filename': 'file_path',
        'input_file': 'file_path',
        'input_path': 'file_path',
        'filepath': 'file_path',
        
        # Output file variations
        'output_file': 'output_path',
        'output_filename': 'output_path',
        'output_filepath': 'output_path',
        'export_path': 'output_path',
    }
    
    def __init__(self, dry_run: bool = True, backup: bool = True, verbose: bool = False):
        """
        Initialize the migrator.
        
        Args:
            dry_run: If True, don't make actual changes
            backup: If True, create backups before modifying files
            verbose: If True, print detailed progress
        """
        self.dry_run = dry_run
        self.backup = backup
        self.verbose = verbose
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'dry_run' if dry_run else 'live',
            'python_files': {},
            'yaml_files': {},
            'summary': {
                'total_files_scanned': 0,
                'total_files_modified': 0,
                'total_parameters_migrated': 0,
                'python_changes': 0,
                'yaml_changes': 0,
                'errors': []
            }
        }
        self.backup_dir = Path.home() / '.biomapper_migration_backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def log(self, message: str, level: str = 'info'):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            prefix = {
                'info': '[INFO]',
                'warning': '[WARN]',
                'error': '[ERROR]',
                'success': '[OK]'
            }.get(level, '[INFO]')
            print(f"{prefix} {message}")
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file."""
        if not self.backup:
            return None
        
        backup_path = self.backup_dir / file_path.relative_to('/')
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        self.log(f"Backed up: {file_path} -> {backup_path}", 'success')
        return backup_path
    
    def migrate_python_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Migrate parameter names in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with migration details
        """
        changes = {
            'file': str(file_path),
            'changes': [],
            'error': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Parse the file
            tree = ast.parse(original_content)
            
            # Track if we made any changes
            modified = False
            
            # Find and update parameter names in Pydantic models
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's likely a Pydantic model
                    if self._is_pydantic_model(node):
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                old_name = item.target.id
                                if old_name in self.PARAM_MAPPING:
                                    new_name = self.PARAM_MAPPING[old_name]
                                    
                                    # Record the change
                                    changes['changes'].append({
                                        'class': node.name,
                                        'old_name': old_name,
                                        'new_name': new_name,
                                        'line': item.lineno
                                    })
                                    
                                    if not self.dry_run:
                                        # Use regex to replace in original content to preserve formatting
                                        pattern = rf'(\s+){re.escape(old_name)}(\s*:)'
                                        replacement = rf'\1{new_name}\2'
                                        
                                        # Find the line and replace
                                        lines = original_content.split('\n')
                                        if item.lineno - 1 < len(lines):
                                            line = lines[item.lineno - 1]
                                            new_line = re.sub(pattern, replacement, line)
                                            if line != new_line:
                                                lines[item.lineno - 1] = new_line
                                                modified = True
                                        
                                        if modified:
                                            original_content = '\n'.join(lines)
            
            # Save changes if not dry run and we made modifications
            if modified and not self.dry_run:
                self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                self.log(f"Updated: {file_path} ({len(changes['changes'])} changes)", 'success')
            
            if changes['changes']:
                self.report['summary']['python_changes'] += len(changes['changes'])
                self.report['summary']['total_parameters_migrated'] += len(changes['changes'])
                if not self.dry_run:
                    self.report['summary']['total_files_modified'] += 1
            
        except Exception as e:
            changes['error'] = str(e)
            self.report['summary']['errors'].append({
                'file': str(file_path),
                'error': str(e)
            })
            self.log(f"Error processing {file_path}: {e}", 'error')
        
        return changes
    
    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Check if a class is likely a Pydantic BaseModel."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                return True
        
        # Also check if class name ends with 'Params' (common pattern)
        return node.name.endswith('Params')
    
    def migrate_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Migrate parameter names in a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dictionary with migration details
        """
        changes = {
            'file': str(file_path),
            'changes': [],
            'error': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                data = yaml.safe_load(original_content)
            
            if data is None:
                return changes
            
            # Recursively update keys in the YAML structure
            modified_data, param_changes = self._migrate_yaml_keys(data)
            
            if param_changes:
                changes['changes'] = param_changes
                
                if not self.dry_run:
                    self.create_backup(file_path)
                    
                    # Write back with preserved formatting (as much as possible)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        yaml.dump(modified_data, f, 
                                default_flow_style=False,
                                allow_unicode=True,
                                sort_keys=False)
                    
                    self.log(f"Updated: {file_path} ({len(param_changes)} changes)", 'success')
                
                self.report['summary']['yaml_changes'] += len(param_changes)
                self.report['summary']['total_parameters_migrated'] += len(param_changes)
                if not self.dry_run:
                    self.report['summary']['total_files_modified'] += 1
            
        except Exception as e:
            changes['error'] = str(e)
            self.report['summary']['errors'].append({
                'file': str(file_path),
                'error': str(e)
            })
            self.log(f"Error processing {file_path}: {e}", 'error')
        
        return changes
    
    def _migrate_yaml_keys(self, data: Any, path: str = '') -> Tuple[Any, List[Dict]]:
        """
        Recursively migrate keys in YAML data structure.
        
        Args:
            data: The YAML data to process
            path: Current path in the structure (for reporting)
            
        Returns:
            Tuple of (modified data, list of changes)
        """
        changes = []
        
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                # Check if this key needs migration
                new_key = self.PARAM_MAPPING.get(key, key)
                
                if new_key != key:
                    changes.append({
                        'path': path,
                        'old_name': key,
                        'new_name': new_key
                    })
                
                # Recursively process the value
                new_value, sub_changes = self._migrate_yaml_keys(
                    value, 
                    f"{path}.{new_key}" if path else new_key
                )
                new_dict[new_key] = new_value
                changes.extend(sub_changes)
            
            return new_dict, changes
        
        elif isinstance(data, list):
            new_list = []
            for i, item in enumerate(data):
                new_item, sub_changes = self._migrate_yaml_keys(
                    item,
                    f"{path}[{i}]"
                )
                new_list.append(new_item)
                changes.extend(sub_changes)
            
            return new_list, changes
        
        else:
            # For string values, check if they reference parameter names
            if isinstance(data, str) and '${parameters.' in data:
                for old_name, new_name in self.PARAM_MAPPING.items():
                    old_ref = f'${{parameters.{old_name}}}'
                    new_ref = f'${{parameters.{new_name}}}'
                    if old_ref in data:
                        data = data.replace(old_ref, new_ref)
                        changes.append({
                            'path': path,
                            'old_ref': old_ref,
                            'new_ref': new_ref
                        })
            
            return data, changes
    
    def run_migration(self, python_dir: str, yaml_dir: str):
        """
        Run the complete migration.
        
        Args:
            python_dir: Directory containing Python files
            yaml_dir: Directory containing YAML files
        """
        print(f"\n{'='*60}")
        print(f"Parameter Name Migration")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Backup: {'Enabled' if self.backup else 'Disabled'}")
        print(f"{'='*60}\n")
        
        # Process Python files
        print("Processing Python files...")
        python_path = Path(python_dir)
        if python_path.exists():
            for file_path in python_path.rglob("*.py"):
                if '__pycache__' not in str(file_path):
                    self.report['summary']['total_files_scanned'] += 1
                    result = self.migrate_python_file(file_path)
                    if result['changes'] or result['error']:
                        self.report['python_files'][str(file_path)] = result
        
        # Process YAML files
        print("\nProcessing YAML files...")
        yaml_path = Path(yaml_dir)
        if yaml_path.exists():
            for file_path in yaml_path.rglob("*.yaml"):
                self.report['summary']['total_files_scanned'] += 1
                result = self.migrate_yaml_file(file_path)
                if result['changes'] or result['error']:
                    self.report['yaml_files'][str(file_path)] = result
            
            for file_path in yaml_path.rglob("*.yml"):
                self.report['summary']['total_files_scanned'] += 1
                result = self.migrate_yaml_file(file_path)
                if result['changes'] or result['error']:
                    self.report['yaml_files'][str(file_path)] = result
        
        # Save report
        self.save_report()
        
        # Print summary
        self.print_summary()
    
    def save_report(self):
        """Save the migration report to JSON."""
        report_path = Path('migration_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        if self.backup and not self.dry_run:
            print(f"Backups saved to: {self.backup_dir}")
    
    def print_summary(self):
        """Print migration summary."""
        summary = self.report['summary']
        
        print(f"\n{'='*60}")
        print("MIGRATION SUMMARY")
        print(f"{'='*60}")
        print(f"Files scanned: {summary['total_files_scanned']}")
        print(f"Files modified: {summary['total_files_modified']}")
        print(f"Parameters migrated: {summary['total_parameters_migrated']}")
        print(f"  - Python changes: {summary['python_changes']}")
        print(f"  - YAML changes: {summary['yaml_changes']}")
        
        if summary['errors']:
            print(f"\nErrors encountered: {len(summary['errors'])}")
            for error in summary['errors'][:5]:
                print(f"  - {error['file']}: {error['error']}")
        
        if self.dry_run:
            print("\n⚠️  This was a DRY RUN - no files were modified")
            print("Run with --apply to make actual changes")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate parameter names to follow established standards'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry-run)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backups'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--python-dir',
        default='/home/ubuntu/biomapper/biomapper/core/strategy_actions',
        help='Directory containing Python files'
    )
    parser.add_argument(
        '--yaml-dir',
        default='/home/ubuntu/biomapper/configs/strategies',
        help='Directory containing YAML strategy files'
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = ParameterMigrator(
        dry_run=not args.apply,
        backup=not args.no_backup,
        verbose=args.verbose
    )
    
    # Run migration
    migrator.run_migration(args.python_dir, args.yaml_dir)


if __name__ == '__main__':
    main()
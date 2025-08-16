#!/usr/bin/env python3
"""Audit all Pydantic models for configuration issues.

This script finds all Pydantic model definitions in the biomapper project
and checks their configuration, particularly focusing on the 'extra' setting
which determines whether models accept additional fields.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ModelInfo:
    """Information about a Pydantic model."""
    file_path: str
    class_name: str
    line_number: int
    base_classes: List[str]
    has_config: bool
    config_extra: Optional[str]
    has_model_config: bool
    inherits_from_standards: bool
    fields: List[str]
    
    @property
    def is_flexible(self) -> bool:
        """Check if model allows extra fields."""
        return (
            self.config_extra == 'allow' or 
            self.inherits_from_standards or
            any('Flexible' in base or 'ActionParams' in base or 'DatasetOperation' in base 
                or 'FileOperation' in base or 'APIOperation' in base 
                for base in self.base_classes)
        )
    
    @property
    def needs_migration(self) -> bool:
        """Check if model needs migration to flexible base."""
        return not self.is_flexible and 'BaseModel' in str(self.base_classes)


class PydanticModelAuditor:
    """Audits Pydantic models in the codebase."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.models: List[ModelInfo] = []
        self.standards_bases = {
            'FlexibleBaseModel', 'StrictBaseModel', 'ActionParamsBase',
            'DatasetOperationParams', 'FileOperationParams', 'APIOperationParams',
            'FlexibleParams', 'StrictParams', 'ActionParams',
            'DatasetParams', 'FileParams', 'APIParams'
        }
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        files = []
        for pattern in ['*.py']:
            files.extend(self.root_dir.rglob(pattern))
        
        # Filter out unwanted paths
        return [
            f for f in files
            if '__pycache__' not in str(f)
            and 'venv' not in str(f)
            and '.venv' not in str(f)
            and 'build' not in str(f)
            and 'dist' not in str(f)
        ]
    
    def extract_base_classes(self, node: ast.ClassDef) -> List[str]:
        """Extract base class names from a class definition."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))
            elif isinstance(base, ast.Subscript):
                # Handle generics like TypedStrategyAction[Params, Result]
                if isinstance(base.value, ast.Name):
                    bases.append(base.value.id)
        return bases
    
    def extract_config_extra(self, node: ast.ClassDef) -> Optional[str]:
        """Extract the 'extra' setting from Config class or model_config."""
        # Check for nested Config class
        for item in node.body:
            if isinstance(item, ast.ClassDef) and item.name == 'Config':
                for config_item in item.body:
                    if isinstance(config_item, ast.Assign):
                        for target in config_item.targets:
                            if isinstance(target, ast.Name) and target.id == 'extra':
                                if isinstance(config_item.value, ast.Constant):
                                    return config_item.value.value
        
        # Check for model_config with ConfigDict
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == 'model_config':
                        # Try to find extra='allow' or extra='forbid' in the assignment
                        if isinstance(item.value, ast.Call):
                            for keyword in item.value.keywords:
                                if keyword.arg == 'extra':
                                    if isinstance(keyword.value, ast.Constant):
                                        return keyword.value.value
        
        return None
    
    def extract_fields(self, node: ast.ClassDef) -> List[str]:
        """Extract field names from a model class."""
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
        return fields
    
    def analyze_file(self, file_path: Path) -> List[ModelInfo]:
        """Analyze a Python file for Pydantic models."""
        models = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_classes = self.extract_base_classes(node)
                    
                    # Check if it's a Pydantic model
                    is_pydantic = any(
                        'BaseModel' in base or 
                        base in self.standards_bases or
                        'Params' in base  # Common pattern for param classes
                        for base in base_classes
                    )
                    
                    if is_pydantic:
                        has_config = any(
                            isinstance(item, ast.ClassDef) and item.name == 'Config'
                            for item in node.body
                        )
                        
                        has_model_config = any(
                            isinstance(item, ast.Assign) and
                            any(isinstance(t, ast.Name) and t.id == 'model_config' 
                                for t in item.targets)
                            for item in node.body
                        )
                        
                        inherits_from_standards = any(
                            base in self.standards_bases for base in base_classes
                        )
                        
                        models.append(ModelInfo(
                            file_path=str(file_path.relative_to(self.root_dir)),
                            class_name=node.name,
                            line_number=node.lineno,
                            base_classes=base_classes,
                            has_config=has_config,
                            config_extra=self.extract_config_extra(node),
                            has_model_config=has_model_config,
                            inherits_from_standards=inherits_from_standards,
                            fields=self.extract_fields(node)
                        ))
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        
        return models
    
    def audit(self) -> None:
        """Run the audit on all Python files."""
        print("🔍 Auditing Pydantic models in biomapper project...\n")
        
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to analyze\n")
        
        for file_path in python_files:
            models = self.analyze_file(file_path)
            self.models.extend(models)
        
        print(f"Found {len(self.models)} Pydantic models total\n")
    
    def generate_report(self) -> None:
        """Generate a detailed report of the audit results."""
        # Categorize models
        flexible_models = [m for m in self.models if m.is_flexible]
        strict_models = [m for m in self.models if not m.is_flexible]
        needs_migration = [m for m in self.models if m.needs_migration]
        uses_standards = [m for m in self.models if m.inherits_from_standards]
        
        print("=" * 80)
        print("PYDANTIC MODEL AUDIT REPORT")
        print("=" * 80)
        print()
        
        # Summary statistics
        print("📊 SUMMARY")
        print("-" * 40)
        print(f"Total models found: {len(self.models)}")
        print(f"Flexible models (allow extra): {len(flexible_models)}")
        print(f"Strict models (forbid extra): {len(strict_models)}")
        print(f"Using standards base models: {len(uses_standards)}")
        print(f"Need migration: {len(needs_migration)}")
        print()
        
        # Models needing migration
        if needs_migration:
            print("🔴 MODELS NEEDING MIGRATION (High Priority)")
            print("-" * 40)
            for model in sorted(needs_migration, key=lambda m: m.file_path):
                print(f"\n📁 {model.file_path}:{model.line_number}")
                print(f"   Class: {model.class_name}")
                print(f"   Base: {', '.join(model.base_classes)}")
                print(f"   Fields: {', '.join(model.fields[:5])}{'...' if len(model.fields) > 5 else ''}")
                if model.config_extra:
                    print(f"   Config extra: {model.config_extra}")
                print(f"   ⚠️  Needs migration to flexible base model")
        
        # Already using standards
        if uses_standards:
            print("\n✅ MODELS USING STANDARDS (Good)")
            print("-" * 40)
            by_base = defaultdict(list)
            for model in uses_standards:
                for base in model.base_classes:
                    if base in self.standards_bases:
                        by_base[base].append(model)
            
            for base, models in sorted(by_base.items()):
                print(f"\n{base} ({len(models)} models):")
                for model in models[:3]:  # Show first 3 examples
                    print(f"  - {model.class_name} in {model.file_path}")
                if len(models) > 3:
                    print(f"  ... and {len(models) - 3} more")
        
        # Models by directory
        print("\n📂 MODELS BY DIRECTORY")
        print("-" * 40)
        by_dir = defaultdict(list)
        for model in self.models:
            dir_path = str(Path(model.file_path).parent)
            by_dir[dir_path].append(model)
        
        for dir_path in sorted(by_dir.keys()):
            models = by_dir[dir_path]
            flexible = sum(1 for m in models if m.is_flexible)
            strict = len(models) - flexible
            print(f"\n{dir_path}:")
            print(f"  Total: {len(models)} | Flexible: {flexible} | Strict: {strict}")
            
            # Show models needing migration in this directory
            need_fix = [m for m in models if m.needs_migration]
            if need_fix:
                print(f"  ⚠️  Need migration: {', '.join(m.class_name for m in need_fix)}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 40)
        if needs_migration:
            print(f"1. Migrate {len(needs_migration)} models to use flexible base models")
            print("   Priority files:")
            for model in needs_migration[:5]:
                print(f"   - {model.file_path} ({model.class_name})")
        else:
            print("✅ All models are properly configured!")
        
        print("\n2. Use the migration guide: standards/PYDANTIC_MIGRATION_GUIDE.md")
        print("3. Run tests after migration: poetry run pytest tests/test_model_flexibility.py")
        
        # Export results to file
        self.export_results(needs_migration)
    
    def export_results(self, needs_migration: List[ModelInfo]) -> None:
        """Export audit results to a file for tracking."""
        output_file = self.root_dir / "standards" / "pydantic_audit_results.txt"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("PYDANTIC MODEL AUDIT RESULTS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("MODELS NEEDING MIGRATION:\n")
            f.write("-" * 40 + "\n")
            for model in needs_migration:
                f.write(f"{model.file_path}:{model.line_number} - {model.class_name}\n")
            
            f.write(f"\nTotal models needing migration: {len(needs_migration)}\n")
            f.write(f"Total models analyzed: {len(self.models)}\n")
        
        print(f"\n📄 Results exported to: {output_file.relative_to(self.root_dir)}")


def main():
    """Main entry point for the audit script."""
    # Determine the root directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent  # Go up from scripts/ to biomapper/
    
    # Focus on the biomapper package
    biomapper_dir = root_dir / "biomapper"
    
    if not biomapper_dir.exists():
        print(f"Error: biomapper directory not found at {biomapper_dir}", file=sys.stderr)
        sys.exit(1)
    
    auditor = PydanticModelAuditor(biomapper_dir)
    auditor.audit()
    auditor.generate_report()


if __name__ == "__main__":
    main()
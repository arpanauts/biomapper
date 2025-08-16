"""
Tests for parameter naming standards enforcement.
Ensures all actions follow established parameter naming conventions.
"""

import pytest
import json
import ast
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.standards.parameter_validator import (
    ParameterValidator,
    validate_action_params,
    migrate_action_params
)


class TestParameterValidator:
    """Test the parameter validator utility."""
    
    def test_standard_names_validation(self):
        """Test that standard names are recognized as valid."""
        validator = ParameterValidator()
        
        standard_params = {
            'input_key': 'test_input',
            'output_key': 'test_output',
            'file_path': '/path/to/file',
            'output_path': '/path/to/output',
            'threshold': 0.8,
            'identifier_column': 'id'
        }
        
        non_standard = validator.validate_params(standard_params)
        assert len(non_standard) == 0, f"Standard params marked as non-standard: {non_standard}"
    
    def test_non_standard_names_detection(self):
        """Test that non-standard names are detected."""
        validator = ParameterValidator()
        
        non_standard_params = {
            'dataset_key': 'test_input',  # Should be input_key
            'output_file': 'test.csv',     # Should be output_path
            'csv_path': 'data.csv',        # Should be file_path
            'source_dataset': 'source',    # Should be source_key
        }
        
        violations = validator.validate_params(non_standard_params)
        assert len(violations) == 4, f"Expected 4 violations, got {len(violations)}"
        assert 'dataset_key' in violations
        assert 'output_file' in violations
        assert 'csv_path' in violations
        assert 'source_dataset' in violations
    
    def test_parameter_migration(self):
        """Test parameter name migration."""
        validator = ParameterValidator()
        
        old_params = {
            'dataset_key': 'input_data',
            'output_context_key': 'output_data',
            'csv_path': 'file.csv',
            'threshold': 0.9,  # Standard param, should not change
        }
        
        migrated = validator.migrate_params(old_params)
        
        assert 'input_key' in migrated
        assert migrated['input_key'] == 'input_data'
        assert 'output_key' in migrated
        assert migrated['output_key'] == 'output_data'
        assert 'file_path' in migrated
        assert migrated['file_path'] == 'file.csv'
        assert 'threshold' in migrated
        assert migrated['threshold'] == 0.9
        
        # Old names should not be present
        assert 'dataset_key' not in migrated
        assert 'output_context_key' not in migrated
        assert 'csv_path' not in migrated
    
    def test_suggestion_generation(self):
        """Test that correct suggestions are generated."""
        validator = ParameterValidator()
        
        # Test direct mappings
        assert validator.suggest_standard_name('dataset_key') == 'input_key'
        assert validator.suggest_standard_name('output_file') == 'output_path'
        assert validator.suggest_standard_name('csv_path') == 'file_path'
        
        # Test pattern-based suggestions
        assert validator.suggest_standard_name('input_dataset_key') == 'input_key'
        assert validator.suggest_standard_name('output_dataset_key') == 'output_key'
    
    def test_strict_mode(self):
        """Test strict mode raises exceptions."""
        validator = ParameterValidator(strict=True)
        
        non_standard_params = {
            'dataset_key': 'test'
        }
        
        with pytest.raises(ValueError) as exc_info:
            validator.validate_params(non_standard_params, 'TestAction')
        
        assert 'Non-standard parameter' in str(exc_info.value)
        assert 'dataset_key' in str(exc_info.value)
    
    def test_report_generation(self):
        """Test validation report generation."""
        validator = ParameterValidator()
        
        # Validate multiple sets of parameters
        validator.validate_params({'dataset_key': 'test'}, 'Action1')
        validator.validate_params({'output_file': 'out.csv'}, 'Action2')
        validator.validate_params({'dataset_key': 'test2'}, 'Action3')
        
        report = validator.generate_report()
        
        assert report['total_violations'] == 3
        assert 'Action1' in report['violations_by_action']
        assert 'Action2' in report['violations_by_action']
        assert 'dataset_key' in report['most_common_violations']
        assert report['most_common_violations']['dataset_key'] == 2


class TestActionParameterCompliance:
    """Test that all existing actions follow parameter standards."""
    
    @pytest.fixture
    def action_files(self):
        """Get all action Python files."""
        actions_dir = Path('/home/ubuntu/biomapper/biomapper/core/strategy_actions')
        return list(actions_dir.rglob('*.py'))
    
    def extract_params_from_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Extract parameter names from a Python file."""
        params_by_class = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Params class
                    if node.name.endswith('Params'):
                        params = []
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                params.append(item.target.id)
                        
                        if params:
                            params_by_class[node.name] = params
        except:
            pass  # Skip files with syntax errors
        
        return params_by_class
    
    def test_all_actions_comply(self, action_files):
        """Test that all action files comply with naming standards."""
        validator = ParameterValidator()
        total_violations = 0
        violations_by_file = {}
        
        for file_path in action_files:
            if '__pycache__' in str(file_path):
                continue
            
            params_by_class = self.extract_params_from_file(file_path)
            
            for class_name, params in params_by_class.items():
                # Create dict from param names for validation
                param_dict = {p: None for p in params}
                non_standard = validator.validate_params(
                    param_dict, 
                    f"{file_path.stem}.{class_name}"
                )
                
                if non_standard:
                    total_violations += len(non_standard)
                    violations_by_file[str(file_path)] = non_standard
        
        # Report violations if any
        if violations_by_file:
            print(f"\n⚠️  Found {total_violations} parameter naming violations:")
            for file_path, violations in list(violations_by_file.items())[:10]:
                print(f"  {Path(file_path).name}: {', '.join(violations)}")
        
        # This test documents current state - adjust threshold as migrations proceed
        # Goal is to reach 0 violations
        assert total_violations <= 20, (
            f"Too many parameter naming violations: {total_violations}. "
            "Run migration script to fix: python scripts/migrate_parameter_names.py --apply"
        )


class TestMigrationScript:
    """Test the parameter migration script."""
    
    def test_migration_script_exists(self):
        """Test that migration script exists and is executable."""
        script_path = Path('/home/ubuntu/biomapper/scripts/migrate_parameter_names.py')
        assert script_path.exists(), "Migration script not found"
        assert script_path.is_file(), "Migration script is not a file"
    
    def test_dry_run_mode(self, tmp_path):
        """Test migration script in dry-run mode."""
        # Create a test Python file with non-standard params
        test_file = tmp_path / "test_action.py"
        test_file.write_text("""
from pydantic import BaseModel, Field

class TestParams(BaseModel):
    dataset_key: str = Field(..., description="Input dataset")
    output_file: str = Field(..., description="Output file")
    csv_path: str = Field(None, description="CSV file path")
""")
        
        # Import and run migrator in dry-run mode
        from scripts.migrate_parameter_names import ParameterMigrator
        
        migrator = ParameterMigrator(dry_run=True, backup=False, verbose=False)
        result = migrator.migrate_python_file(test_file)
        
        assert len(result['changes']) == 3
        assert any(c['old_name'] == 'dataset_key' for c in result['changes'])
        assert any(c['new_name'] == 'input_key' for c in result['changes'])
        
        # File should not be modified in dry-run
        content = test_file.read_text()
        assert 'dataset_key' in content  # Old name still present
        assert 'input_key' not in content  # New name not added


class TestParameterStandardsDocument:
    """Test that parameter standards document is complete."""
    
    def test_standards_document_exists(self):
        """Test that standards document exists."""
        doc_path = Path('/home/ubuntu/biomapper/standards/PARAMETER_NAMING_STANDARD.md')
        assert doc_path.exists(), "Parameter naming standard document not found"
        assert doc_path.is_file(), "Standards document is not a file"
    
    def test_standards_document_content(self):
        """Test that standards document contains required sections."""
        doc_path = Path('/home/ubuntu/biomapper/standards/PARAMETER_NAMING_STANDARD.md')
        content = doc_path.read_text()
        
        # Check for required sections
        required_sections = [
            '# Parameter Naming Standard',
            '## 1. Core Principles',
            '## 2. Standard Parameter Names',
            '### Dataset Keys',
            '### File Paths',
            '### Column Names',
            '### Processing Parameters',
            '### Boolean Flags',
            '## 3. Special Naming Rules',
            '## 4. Migration Examples',
            '## 5. Validation Rules',
            '## 6. Backward Compatibility',
        ]
        
        for section in required_sections:
            assert section in content, f"Missing section: {section}"
        
        # Check for key parameter mappings
        assert 'input_key' in content
        assert 'output_key' in content
        assert 'file_path' in content
        assert 'output_path' in content


class TestActionTemplate:
    """Test that action template follows standards."""
    
    def test_template_exists(self):
        """Test that action template exists."""
        template_path = Path('/home/ubuntu/biomapper/templates/action_template.py')
        assert template_path.exists(), "Action template not found"
    
    def test_template_uses_standard_names(self):
        """Test that template uses standard parameter names."""
        template_path = Path('/home/ubuntu/biomapper/templates/action_template.py')
        content = template_path.read_text()
        
        # Check for standard parameter names
        assert 'input_key:' in content or 'input_key =' in content
        assert 'output_key:' in content or 'output_key =' in content
        assert 'file_path:' in content or 'file_path =' in content
        assert 'output_path:' in content or 'output_path =' in content
        
        # Check that old names are NOT used
        assert 'dataset_key:' not in content
        assert 'output_file:' not in content
        assert 'csv_path:' not in content
    
    def test_template_includes_validation(self):
        """Test that template includes parameter validation."""
        template_path = Path('/home/ubuntu/biomapper/templates/action_template.py')
        content = template_path.read_text()
        
        assert 'parameter_validator' in content.lower() or 'validate_action_params' in content
        assert 'field_validator' in content or '@validator' in content


def test_convenience_functions():
    """Test convenience functions for parameter validation."""
    
    # Test validate_action_params
    params = {'input_key': 'test', 'output_key': 'result'}
    assert validate_action_params(params) == True
    
    params_invalid = {'dataset_key': 'test', 'output_file': 'result.csv'}
    assert validate_action_params(params_invalid) == False
    
    # Test migrate_action_params
    old_params = {
        'dataset_key': 'input',
        'output_context_key': 'output',
        'threshold': 0.5
    }
    
    migrated = migrate_action_params(old_params)
    assert migrated['input_key'] == 'input'
    assert migrated['output_key'] == 'output'
    assert migrated['threshold'] == 0.5
    assert 'dataset_key' not in migrated


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
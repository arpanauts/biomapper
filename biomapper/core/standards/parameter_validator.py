"""
Parameter validation utility for enforcing naming standards.
Ensures all action parameters follow the established naming conventions.
"""

import warnings
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import json


class ParameterValidator:
    """Validates parameter names against established standards."""
    
    # Standard names mapping: category -> standard name
    STANDARD_NAMES = {
        # Dataset keys
        'input_dataset': 'input_key',
        'output_dataset': 'output_key',
        'source_dataset': 'source_key',
        'target_dataset': 'target_key',
        'input_dataset_2': 'input_key_2',
        'input_dataset_3': 'input_key_3',
        
        # File paths
        'input_file': 'file_path',
        'output_file': 'output_path',
        'directory': 'directory_path',
        'config_file': 'config_path',
        
        # Column names
        'identifier_col': 'identifier_column',
        'merge_col': 'merge_column',
        'value_col': 'value_column',
        'name_col': 'name_column',
        'description_col': 'description_column',
        
        # Processing parameters
        'threshold_value': 'threshold',
        'maximum': 'max_limit',
        'minimum': 'min_limit',
        'batch': 'batch_size',
        'timeout': 'timeout_seconds',
        
        # Boolean flags
        'case': 'case_sensitive',
        'header': 'include_header',
        'overwrite_existing': 'overwrite',
        'verbose_output': 'verbose',
        'strict_mode': 'strict',
        
        # API parameters
        'api_authentication': 'api_key',
        'endpoint': 'api_endpoint',
        'request_timeout_value': 'request_timeout',
        'retries': 'max_retries',
        
        # Format parameters
        'format': 'file_format',
        'separator': 'delimiter',
        'text_encoding': 'encoding',
    }
    
    # Mapping of old names to new standard names
    MIGRATION_MAP = {
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
        
        # Column variations
        'id_column': 'identifier_column',
        'id_col': 'identifier_column',
        'identifier_col': 'identifier_column',
        'join_column': 'merge_column',
        'merge_on': 'merge_column',
        'join_on': 'merge_column',
        
        # Other variations
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
    }
    
    # Parameters that are always valid (common across all actions)
    ALWAYS_VALID = {
        'description', 'name', 'enabled', 'priority', 'tags',
        'metadata', 'config', 'options', 'params', 'extra'
    }
    
    def __init__(self, strict: bool = False):
        """
        Initialize the parameter validator.
        
        Args:
            strict: If True, raises exceptions on violations. If False, logs warnings.
        """
        self.strict = strict
        self.violations: List[Dict[str, Any]] = []
        
    def validate_params(self, params: Dict[str, Any], action_name: str = None) -> List[str]:
        """
        Validate parameter names and return list of non-standard names.
        
        Args:
            params: Dictionary of parameter names to values
            action_name: Optional name of the action being validated
            
        Returns:
            List of non-standard parameter names
        """
        non_standard = []
        
        for param_name in params.keys():
            if not self.is_valid_param_name(param_name):
                non_standard.append(param_name)
                violation = {
                    'action': action_name,
                    'parameter': param_name,
                    'suggestion': self.suggest_standard_name(param_name),
                    'severity': 'error' if self.strict else 'warning'
                }
                self.violations.append(violation)
                
                if self.strict:
                    raise ValueError(
                        f"Non-standard parameter '{param_name}' in {action_name or 'action'}. "
                        f"Suggested: '{violation['suggestion']}'"
                    )
                else:
                    warnings.warn(
                        f"Non-standard parameter '{param_name}' in {action_name or 'action'}. "
                        f"Suggested: '{violation['suggestion']}'",
                        DeprecationWarning,
                        stacklevel=2
                    )
        
        return non_standard
    
    def is_valid_param_name(self, param_name: str) -> bool:
        """
        Check if a parameter name follows standards.
        
        Args:
            param_name: The parameter name to check
            
        Returns:
            True if the name is standard, False otherwise
        """
        # Always valid parameters
        if param_name in self.ALWAYS_VALID:
            return True
        
        # Check if it's a standard name
        if param_name in self.STANDARD_NAMES.values():
            return True
        
        # Check if it's in the migration map (non-standard)
        if param_name in self.MIGRATION_MAP:
            return False
        
        # Check basic naming rules
        if not param_name.islower():
            return False
        
        if not param_name.replace('_', '').isalnum():
            return False
        
        # If we don't recognize it, consider it valid (new parameter)
        return True
    
    def suggest_standard_name(self, param_name: str) -> str:
        """
        Suggest the standard name for a parameter.
        
        Args:
            param_name: The non-standard parameter name
            
        Returns:
            The suggested standard name, or the original if no suggestion
        """
        # Direct mapping
        if param_name in self.MIGRATION_MAP:
            return self.MIGRATION_MAP[param_name]
        
        # Try to infer from patterns
        param_lower = param_name.lower()
        
        # Check for input dataset patterns
        if 'input' in param_lower and ('key' in param_lower or 'dataset' in param_lower):
            return 'input_key'
        
        # Check for output dataset patterns
        if 'output' in param_lower and ('key' in param_lower or 'dataset' in param_lower):
            return 'output_key'
        
        # Check for file path patterns
        if 'path' in param_lower or 'file' in param_lower:
            if 'output' in param_lower:
                return 'output_path'
            else:
                return 'file_path'
        
        # Check for column patterns
        if 'column' in param_lower or '_col' in param_lower:
            if 'id' in param_lower:
                return 'identifier_column'
            elif 'merge' in param_lower or 'join' in param_lower:
                return 'merge_column'
        
        # No suggestion available
        return param_name
    
    def migrate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate parameter names to standard names.
        
        Args:
            params: Dictionary with potentially non-standard names
            
        Returns:
            Dictionary with standard parameter names
        """
        migrated = {}
        
        for key, value in params.items():
            if key in self.MIGRATION_MAP:
                new_key = self.MIGRATION_MAP[key]
                migrated[new_key] = value
                warnings.warn(
                    f"Parameter '{key}' has been migrated to '{new_key}'",
                    DeprecationWarning,
                    stacklevel=2
                )
            else:
                migrated[key] = value
        
        return migrated
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a validation report.
        
        Returns:
            Dictionary containing validation statistics and violations
        """
        report = {
            'total_violations': len(self.violations),
            'violations_by_action': {},
            'most_common_violations': {},
            'suggestions': []
        }
        
        # Group violations by action
        for violation in self.violations:
            action = violation.get('action', 'unknown')
            if action not in report['violations_by_action']:
                report['violations_by_action'][action] = []
            report['violations_by_action'][action].append(violation)
        
        # Count most common violations
        violation_counts = {}
        for violation in self.violations:
            param = violation['parameter']
            violation_counts[param] = violation_counts.get(param, 0) + 1
        
        report['most_common_violations'] = dict(
            sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        # Generate suggestions
        for param, count in report['most_common_violations'].items():
            suggestion = self.suggest_standard_name(param)
            report['suggestions'].append({
                'old_name': param,
                'new_name': suggestion,
                'occurrences': count
            })
        
        return report
    
    def save_report(self, file_path: str):
        """Save validation report to JSON file."""
        report = self.generate_report()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    
    @classmethod
    def load_standards(cls, file_path: str = None) -> 'ParameterValidator':
        """
        Load standards from a JSON file.
        
        Args:
            file_path: Path to standards JSON file
            
        Returns:
            ParameterValidator instance with loaded standards
        """
        if file_path and Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                standards = json.load(f)
                validator = cls()
                if 'standard_names' in standards:
                    validator.STANDARD_NAMES.update(standards['standard_names'])
                if 'migration_map' in standards:
                    validator.MIGRATION_MAP.update(standards['migration_map'])
                return validator
        return cls()


def validate_action_params(params: Dict[str, Any], action_name: str = None, strict: bool = False) -> bool:
    """
    Convenience function to validate action parameters.
    
    Args:
        params: Parameters to validate
        action_name: Optional action name for reporting
        strict: Whether to raise exceptions on violations
        
    Returns:
        True if all parameters are valid, False otherwise
    """
    validator = ParameterValidator(strict=strict)
    non_standard = validator.validate_params(params, action_name)
    return len(non_standard) == 0


def migrate_action_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to migrate parameters to standard names.
    
    Args:
        params: Parameters with potentially non-standard names
        
    Returns:
        Parameters with standard names
    """
    validator = ParameterValidator()
    return validator.migrate_params(params)
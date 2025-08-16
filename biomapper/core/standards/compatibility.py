"""Compatibility layer for handling parameter migrations and legacy support."""

import logging
from typing import Dict, Any, List, Optional, Tuple, Type
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)


class ParameterMigration:
    """Represents a parameter migration from old to new name."""
    
    def __init__(
        self,
        old_name: str,
        new_name: str,
        transform: Optional[callable] = None,
        deprecated_since: Optional[str] = None,
        remove_after: Optional[str] = None
    ):
        """Initialize a parameter migration.
        
        Args:
            old_name: The deprecated parameter name
            new_name: The new parameter name
            transform: Optional function to transform the value
            deprecated_since: Version when deprecated (e.g., "0.5.0")
            remove_after: Version when support will be removed
        """
        self.old_name = old_name
        self.new_name = new_name
        self.transform = transform
        self.deprecated_since = deprecated_since
        self.remove_after = remove_after


class ParameterCompatibility:
    """Handle parameter name changes and migrations across versions."""
    
    # Global parameter aliases that apply to all actions
    GLOBAL_PARAMETER_ALIASES = {
        # Common renamings
        'dataset_key': 'input_key',
        'output_file': 'output_path',
        'source_dataset': 'source_dataset_key',
        'target_dataset': 'target_dataset_key',
        
        # Debug/logging aliases
        'verbose': 'debug',
        'log_level': 'debug',
        'trace_mode': 'trace',
        
        # Timeout aliases
        'timeout_seconds': 'timeout',
        'max_timeout': 'timeout',
        
        # Retry aliases
        'retries': 'retry_count',
        'retry_attempts': 'retry_count',
        'retry_wait': 'retry_delay',
        
        # API aliases
        'api_endpoint': 'api_url',
        'api_token': 'api_key',
        'api_secret': 'api_key',
    }
    
    # Action-specific parameter migrations
    ACTION_SPECIFIC_MIGRATIONS: Dict[str, List[ParameterMigration]] = {
        'MERGE_WITH_UNIPROT_RESOLUTION': [
            ParameterMigration(
                'source_dataset', 'source_dataset_key',
                deprecated_since="0.4.0"
            ),
            ParameterMigration(
                'target_dataset', 'target_dataset_key',
                deprecated_since="0.4.0"
            ),
            ParameterMigration(
                'uniprot_column', 'source_id_column',
                deprecated_since="0.5.0"
            ),
        ],
        'EXPORT_DATASET': [
            ParameterMigration(
                'output_file', 'output_path',
                deprecated_since="0.3.0"
            ),
            ParameterMigration(
                'file_format', 'format',
                deprecated_since="0.4.0"
            ),
            ParameterMigration(
                'export_columns', 'columns',
                deprecated_since="0.4.5"
            ),
        ],
        'CUSTOM_TRANSFORM': [
            ParameterMigration(
                'transforms', 'transformations',
                deprecated_since="0.4.0"
            ),
            ParameterMigration(
                'validate', 'validate_schema',
                deprecated_since="0.4.2"
            ),
        ],
    }
    
    @classmethod
    def migrate_params(
        cls,
        params: Dict[str, Any],
        action_name: Optional[str] = None,
        warn: bool = True
    ) -> Dict[str, Any]:
        """Migrate old parameter names to new ones.
        
        Args:
            params: Original parameters dictionary
            action_name: Optional action name for specific migrations
            warn: Whether to log warnings for migrations
            
        Returns:
            Dictionary with migrated parameter names
        """
        migrated = params.copy()
        migrations_applied = []
        
        # Apply global aliases
        for old_name, new_name in cls.GLOBAL_PARAMETER_ALIASES.items():
            if old_name in migrated and new_name not in migrated:
                migrated[new_name] = migrated.pop(old_name)
                migrations_applied.append((old_name, new_name))
        
        # Apply action-specific migrations
        if action_name and action_name in cls.ACTION_SPECIFIC_MIGRATIONS:
            for migration in cls.ACTION_SPECIFIC_MIGRATIONS[action_name]:
                if migration.old_name in migrated and migration.new_name not in migrated:
                    value = migrated.pop(migration.old_name)
                    
                    # Apply transformation if provided
                    if migration.transform:
                        value = migration.transform(value)
                    
                    migrated[migration.new_name] = value
                    migrations_applied.append((migration.old_name, migration.new_name))
                    
                    if warn and migration.deprecated_since:
                        logger.warning(
                            f"Parameter '{migration.old_name}' is deprecated since v{migration.deprecated_since}. "
                            f"Use '{migration.new_name}' instead."
                        )
                    
                    if warn and migration.remove_after:
                        logger.warning(
                            f"Support for '{migration.old_name}' will be removed in v{migration.remove_after}."
                        )
        
        if warn and migrations_applied:
            logger.info(f"Migrated parameters: {migrations_applied}")
        
        return migrated
    
    @classmethod
    def check_unknown_params(
        cls,
        params: Dict[str, Any],
        model_class: Type[BaseModel],
        action_name: Optional[str] = None
    ) -> List[str]:
        """Check for unknown parameters that aren't in the model.
        
        Args:
            params: Parameters dictionary
            model_class: The Pydantic model class
            action_name: Optional action name for context
            
        Returns:
            List of unknown parameter names
        """
        model_fields = set(model_class.model_fields.keys())
        param_keys = set(params.keys())
        
        unknown = param_keys - model_fields
        
        if unknown:
            logger.debug(
                f"Unknown parameters for {action_name or model_class.__name__}: {unknown}. "
                f"These will be stored as extra fields."
            )
        
        return list(unknown)
    
    @classmethod
    def suggest_corrections(
        cls,
        unknown_params: List[str],
        model_class: Type[BaseModel]
    ) -> Dict[str, str]:
        """Suggest corrections for unknown parameters based on similarity.
        
        Args:
            unknown_params: List of unknown parameter names
            model_class: The Pydantic model class
            
        Returns:
            Dictionary mapping unknown params to suggested corrections
        """
        from difflib import get_close_matches
        
        model_fields = list(model_class.model_fields.keys())
        suggestions = {}
        
        for param in unknown_params:
            matches = get_close_matches(param, model_fields, n=1, cutoff=0.6)
            if matches:
                suggestions[param] = matches[0]
        
        if suggestions:
            logger.info(
                f"Did you mean? {', '.join(f'{k} -> {v}' for k, v in suggestions.items())}"
            )
        
        return suggestions
    
    @classmethod
    def create_migration_report(
        cls,
        action_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a report of all available parameter migrations.
        
        Args:
            action_name: Optional action name to filter report
            
        Returns:
            Dictionary containing migration information
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'global_aliases': cls.GLOBAL_PARAMETER_ALIASES,
            'action_specific': {}
        }
        
        if action_name:
            if action_name in cls.ACTION_SPECIFIC_MIGRATIONS:
                migrations = cls.ACTION_SPECIFIC_MIGRATIONS[action_name]
                report['action_specific'][action_name] = [
                    {
                        'old_name': m.old_name,
                        'new_name': m.new_name,
                        'deprecated_since': m.deprecated_since,
                        'remove_after': m.remove_after
                    }
                    for m in migrations
                ]
        else:
            for action, migrations in cls.ACTION_SPECIFIC_MIGRATIONS.items():
                report['action_specific'][action] = [
                    {
                        'old_name': m.old_name,
                        'new_name': m.new_name,
                        'deprecated_since': m.deprecated_since,
                        'remove_after': m.remove_after
                    }
                    for m in migrations
                ]
        
        return report


class ModelEvolution:
    """Track and handle model evolution over time."""
    
    @staticmethod
    def version_to_tuple(version: str) -> Tuple[int, ...]:
        """Convert version string to tuple for comparison.
        
        Args:
            version: Version string like "0.5.2"
            
        Returns:
            Tuple of integers for comparison
        """
        return tuple(map(int, version.split('.')))
    
    @classmethod
    def is_compatible(
        cls,
        model_version: str,
        required_version: str,
        max_version: Optional[str] = None
    ) -> bool:
        """Check if a model version is compatible.
        
        Args:
            model_version: Current model version
            required_version: Minimum required version
            max_version: Optional maximum version
            
        Returns:
            True if compatible, False otherwise
        """
        model_v = cls.version_to_tuple(model_version)
        required_v = cls.version_to_tuple(required_version)
        
        if model_v < required_v:
            return False
        
        if max_version:
            max_v = cls.version_to_tuple(max_version)
            if model_v > max_v:
                return False
        
        return True
    
    @staticmethod
    def get_migration_path(
        from_version: str,
        to_version: str,
        action_name: str
    ) -> List[callable]:
        """Get the migration functions needed to upgrade parameters.
        
        Args:
            from_version: Starting version
            to_version: Target version
            action_name: Action name for specific migrations
            
        Returns:
            List of migration functions to apply in order
        """
        # This would be expanded with actual migration functions
        # as the system evolves
        migrations = []
        
        # Example migration registry (would be more comprehensive)
        # if from_version < "0.4.0" and to_version >= "0.4.0":
        #     migrations.append(migrate_v3_to_v4)
        # if from_version < "0.5.0" and to_version >= "0.5.0":
        #     migrations.append(migrate_v4_to_v5)
        
        return migrations


class CompatibilityHelper:
    """Helper class for handling compatibility in actions."""
    
    def __init__(self, action_name: str):
        """Initialize compatibility helper for an action.
        
        Args:
            action_name: Name of the action
        """
        self.action_name = action_name
        self.compatibility = ParameterCompatibility()
        self.evolution = ModelEvolution()
    
    def prepare_params(
        self,
        params: Dict[str, Any],
        model_class: Type[BaseModel],
        warn: bool = True
    ) -> Dict[str, Any]:
        """Prepare parameters for model instantiation.
        
        Args:
            params: Raw parameters
            model_class: Target model class
            warn: Whether to show warnings
            
        Returns:
            Prepared parameters dictionary
        """
        # Migrate parameters
        migrated = self.compatibility.migrate_params(
            params,
            self.action_name,
            warn=warn
        )
        
        # Check for unknown parameters
        unknown = self.compatibility.check_unknown_params(
            migrated,
            model_class,
            self.action_name
        )
        
        if unknown and warn:
            # Suggest corrections
            self.compatibility.suggest_corrections(unknown, model_class)
        
        return migrated
    
    def validate_version_compatibility(
        self,
        params: Dict[str, Any],
        min_version: str = "0.3.0",
        max_version: Optional[str] = None
    ) -> bool:
        """Validate that parameters are compatible with version requirements.
        
        Args:
            params: Parameters to validate
            min_version: Minimum supported version
            max_version: Optional maximum version
            
        Returns:
            True if compatible, False otherwise
        """
        # Extract version from params if present
        param_version = params.get('_version', '0.5.2')  # Current version as default
        
        return self.evolution.is_compatible(
            param_version,
            min_version,
            max_version
        )


# Convenience function for quick parameter migration
def migrate_parameters(
    params: Dict[str, Any],
    action_name: Optional[str] = None
) -> Dict[str, Any]:
    """Quick function to migrate parameters.
    
    Args:
        params: Parameters to migrate
        action_name: Optional action name
        
    Returns:
        Migrated parameters
    """
    return ParameterCompatibility.migrate_params(params, action_name)


# Export main classes and functions
__all__ = [
    'ParameterCompatibility',
    'ParameterMigration',
    'ModelEvolution',
    'CompatibilityHelper',
    'migrate_parameters',
]
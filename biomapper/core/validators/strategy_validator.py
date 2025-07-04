"""
Strategy validation module for YAML-defined mapping strategies.

This module provides comprehensive validation of strategy configurations,
including action type validation and parameter schema checking.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import yaml

from biomapper.core.models.strategy import Strategy, StrategyStep, StepAction
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
from biomapper.core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class StrategyValidator:
    """Validates YAML strategy configurations against registered actions and schemas."""
    
    # Action parameter schemas
    # In a production system, these would be defined by each action class
    ACTION_SCHEMAS: Dict[str, Dict[str, List[str]]] = {
        "LOAD_ENDPOINT_IDENTIFIERS": {
            "required": ["endpoint_context", "input_ids_context_key"],
            "optional": ["endpoint_name"]
        },
        "UNIPROT_HISTORICAL_RESOLVER": {
            "required": [],
            "optional": [
                "input_context_key", "output_context_key", "output_ontology_type",
                "batch_size", "include_obsolete", "expand_composites"
            ]
        },
        "LOCAL_ID_CONVERTER": {
            "required": ["mapping_file", "source_column", "target_column"],
            "optional": ["output_ontology_type", "output_context_key", "delimiter"]
        },
        "API_RESOLVER": {
            "required": ["input_context_key", "output_context_key", "api_base_url", "endpoint_path"],
            "optional": [
                "batch_size", "rate_limit_delay", "max_retries", "timeout",
                "request_params", "response_id_field", "response_mapping_field"
            ]
        },
        "DATASET_OVERLAP_ANALYZER": {
            "required": ["dataset1_context_key", "dataset2_context_key"],
            "optional": [
                "output_context_key", "dataset1_name", "dataset2_name",
                "generate_statistics", "include_metadata"
            ]
        },
        "BIDIRECTIONAL_MATCH": {
            "required": ["forward_ids_context_key", "reverse_ids_context_key"],
            "optional": ["output_context_key", "match_threshold"]
        },
        "EXECUTE_MAPPING_PATH": {
            "required": ["mapping_path"],
            "optional": ["batch_size", "cache_results"]
        },
        "FILTER_BY_TARGET_PRESENCE": {
            "required": ["target_context_key"],
            "optional": ["output_context_key", "invert_filter"]
        },
        "RESOLVE_AND_MATCH_FORWARD": {
            "required": ["source_context_key"],
            "optional": ["output_context_key", "resolution_strategy"]
        },
        "RESOLVE_AND_MATCH_REVERSE": {
            "required": ["target_context_key"],
            "optional": ["output_context_key", "resolution_strategy"]
        },
        "GENERATE_MAPPING_SUMMARY": {
            "required": [],
            "optional": ["output_file", "format", "include_statistics"]
        },
        "GENERATE_DETAILED_REPORT": {
            "required": [],
            "optional": ["output_file", "include_sections", "format"]
        },
        "EXPORT_RESULTS": {
            "required": ["output_file"],
            "optional": ["format", "include_metadata", "compress"]
        },
        "VISUALIZE_MAPPING_FLOW": {
            "required": [],
            "optional": ["output_file", "format", "layout", "include_legend"]
        },
        "POPULATE_CONTEXT": {
            "required": ["context_updates"],
            "optional": []
        },
        "COLLECT_MATCHED_TARGETS": {
            "required": [],
            "optional": ["output_context_key", "merge_strategy"]
        },
        "RESULTS_SAVER": {
            "required": ["output_file"],
            "optional": ["format", "include_provenance", "compression"]
        }
    }
    
    def __init__(self, strict: bool = True):
        """
        Initialize the validator.
        
        Args:
            strict: If True, unknown parameters cause validation errors.
                   If False, unknown parameters generate warnings only.
        """
        self.strict = strict
    
    def validate_strategy(self, strategy: Strategy) -> Tuple[bool, List[str]]:
        """
        Validate a complete strategy.
        
        Args:
            strategy: Strategy object to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Basic validation
        if not strategy.name:
            errors.append("Strategy name is required")
        
        if not strategy.steps:
            errors.append("Strategy must have at least one step")
        
        # Validate each step
        for i, step in enumerate(strategy.steps):
            step_errors = self.validate_step(step, i + 1)
            errors.extend(step_errors)
        
        return len(errors) == 0, errors
    
    def validate_step(self, step: StrategyStep, step_number: int) -> List[str]:
        """
        Validate a single strategy step.
        
        Args:
            step: Step to validate
            step_number: Step number for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        prefix = f"Step {step_number} ({step.name})"
        
        # Validate step structure
        if not step.name:
            errors.append(f"Step {step_number}: Name is required")
        
        if not step.action:
            errors.append(f"{prefix}: Action is required")
            return errors
        
        # Validate action
        action_errors = self.validate_action(step.action, prefix)
        errors.extend(action_errors)
        
        return errors
    
    def validate_action(self, action: StepAction, prefix: str) -> List[str]:
        """
        Validate an action configuration.
        
        Args:
            action: Action to validate
            prefix: Prefix for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check action type
        if not action.type:
            errors.append(f"{prefix}: Action type is required")
            return errors
        
        # Check if action is registered
        if action.type not in ACTION_REGISTRY:
            errors.append(f"{prefix}: Unknown action type '{action.type}'")
            # Can't validate parameters for unknown action
            return errors
        
        # Validate parameters
        param_errors = self.validate_action_parameters(
            action.type,
            action.params or {},
            prefix
        )
        errors.extend(param_errors)
        
        return errors
    
    def validate_action_parameters(
        self,
        action_type: str,
        params: Dict[str, Any],
        prefix: str
    ) -> List[str]:
        """
        Validate parameters for a specific action type.
        
        Args:
            action_type: Type of action
            params: Parameters to validate
            prefix: Prefix for error messages
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Get schema for action
        schema = self.ACTION_SCHEMAS.get(action_type)
        if not schema:
            # No schema defined, skip parameter validation
            logger.debug(f"No parameter schema defined for action type '{action_type}'")
            return errors
        
        # Check required parameters
        for required_param in schema.get("required", []):
            if required_param not in params:
                errors.append(f"{prefix}: Missing required parameter '{required_param}'")
        
        # Check for unknown parameters
        if self.strict:
            all_params = set(schema.get("required", []) + schema.get("optional", []))
            for param in params:
                if param not in all_params:
                    errors.append(f"{prefix}: Unknown parameter '{param}'")
        
        # Type validation could be added here based on schema definitions
        
        return errors
    
    @classmethod
    def validate_yaml_file(cls, yaml_path: Path, strict: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate a strategy defined in a YAML file.
        
        Args:
            yaml_path: Path to YAML file
            strict: Whether to use strict validation
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        validator = cls(strict=strict)
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            strategy = Strategy(**data)
            return validator.validate_strategy(strategy)
            
        except yaml.YAMLError as e:
            return False, [f"Invalid YAML: {e}"]
        except ValueError as e:
            return False, [f"Invalid strategy structure: {e}"]
        except Exception as e:
            return False, [f"Unexpected error: {e}"]
    
    @classmethod
    def validate_yaml_string(cls, yaml_content: str, strict: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate a strategy defined as a YAML string.
        
        Args:
            yaml_content: YAML content as string
            strict: Whether to use strict validation
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        validator = cls(strict=strict)
        
        try:
            data = yaml.safe_load(yaml_content)
            strategy = Strategy(**data)
            return validator.validate_strategy(strategy)
            
        except yaml.YAMLError as e:
            return False, [f"Invalid YAML: {e}"]
        except ValueError as e:
            return False, [f"Invalid strategy structure: {e}"]
        except Exception as e:
            return False, [f"Unexpected error: {e}"]


def load_and_validate_strategy(yaml_path: Path) -> Strategy:
    """
    Load and validate a strategy from a YAML file.
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        Validated Strategy object
        
    Raises:
        ConfigurationError: If strategy is invalid
    """
    valid, errors = StrategyValidator.validate_yaml_file(yaml_path)
    
    if not valid:
        error_msg = f"Invalid strategy in {yaml_path}:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ConfigurationError(error_msg)
    
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return Strategy(**data)
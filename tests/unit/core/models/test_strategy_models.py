"""
Unit tests for YAML strategy model validation.

This module tests the Pydantic models used for loading and validating
YAML strategy configurations, ensuring that:
- Valid strategies are accepted
- Invalid action types are rejected
- Invalid parameters for valid actions are rejected
- Required fields are enforced
- Strategy metadata is properly validated
"""

import pytest
from pathlib import Path
from typing import Dict, Any
import yaml

from biomapper.core.models.strategy import (
    StepAction,
    StrategyStep,
    Strategy
)
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
from biomapper.core.exceptions import ConfigurationError


class TestStepActionValidation:
    """Test validation of StepAction models."""
    
    def test_valid_step_action(self):
        """Test creating a valid step action."""
        action = StepAction(
            type="LOAD_ENDPOINT_IDENTIFIERS",
            params={
                "endpoint_context": "SOURCE",
                "input_ids_context_key": "source_ids"
            }
        )
        assert action.type == "LOAD_ENDPOINT_IDENTIFIERS"
        assert action.params["endpoint_context"] == "SOURCE"
    
    def test_step_action_without_params(self):
        """Test creating a step action without parameters."""
        action = StepAction(type="SOME_ACTION")
        assert action.type == "SOME_ACTION"
        assert action.params is None
    
    def test_step_action_with_empty_params(self):
        """Test creating a step action with empty parameters."""
        action = StepAction(type="SOME_ACTION", params={})
        assert action.type == "SOME_ACTION"
        assert action.params == {}


class TestStrategyStepValidation:
    """Test validation of StrategyStep models."""
    
    def test_valid_strategy_step(self):
        """Test creating a valid strategy step."""
        step = StrategyStep(
            name="LOAD_DATA",
            action=StepAction(
                type="LOAD_ENDPOINT_IDENTIFIERS",
                params={"endpoint_context": "SOURCE"}
            )
        )
        assert step.name == "LOAD_DATA"
        assert step.action.type == "LOAD_ENDPOINT_IDENTIFIERS"
    
    def test_strategy_step_requires_name(self):
        """Test that strategy step requires a name."""
        with pytest.raises(ValueError):
            StrategyStep(
                action=StepAction(type="SOME_ACTION")
            )
    
    def test_strategy_step_requires_action(self):
        """Test that strategy step requires an action."""
        with pytest.raises(ValueError):
            StrategyStep(name="STEP_NAME")


class TestStrategyValidation:
    """Test validation of complete Strategy models."""
    
    def test_valid_strategy(self):
        """Test creating a valid strategy."""
        strategy = Strategy(
            name="TEST_STRATEGY",
            description="A test strategy",
            steps=[
                StrategyStep(
                    name="STEP_1",
                    action=StepAction(type="ACTION_1", params={"key": "value"})
                ),
                StrategyStep(
                    name="STEP_2",
                    action=StepAction(type="ACTION_2")
                )
            ]
        )
        assert strategy.name == "TEST_STRATEGY"
        assert strategy.description == "A test strategy"
        assert len(strategy.steps) == 2
    
    def test_strategy_without_description(self):
        """Test creating a strategy without description."""
        strategy = Strategy(
            name="TEST_STRATEGY",
            steps=[
                StrategyStep(
                    name="STEP_1",
                    action=StepAction(type="ACTION_1")
                )
            ]
        )
        assert strategy.name == "TEST_STRATEGY"
        assert strategy.description is None
    
    def test_strategy_requires_name(self):
        """Test that strategy requires a name."""
        with pytest.raises(ValueError):
            Strategy(
                steps=[
                    StrategyStep(
                        name="STEP_1",
                        action=StepAction(type="ACTION_1")
                    )
                ]
            )
    
    def test_strategy_with_empty_steps_allowed(self):
        """Test that strategy allows empty steps list (but should be validated separately)."""
        strategy = Strategy(name="TEST_STRATEGY", steps=[])
        assert strategy.name == "TEST_STRATEGY"
        assert strategy.steps == []
        
        # Empty steps should be caught during validation, not model creation
        # This is by design to allow partial strategy construction
    
    def test_strategy_requires_steps_list(self):
        """Test that strategy requires steps to be a list."""
        with pytest.raises(ValueError):
            Strategy(name="TEST_STRATEGY", steps=None)


class TestActionTypeValidation:
    """Test validation of action types against registered actions."""
    
    def validate_action_type(self, action_type: str) -> bool:
        """Check if an action type is registered."""
        return action_type in ACTION_REGISTRY
    
    def test_valid_registered_action_types(self):
        """Test that known action types are valid."""
        valid_actions = [
            "LOAD_ENDPOINT_IDENTIFIERS",
            "UNIPROT_HISTORICAL_RESOLVER",
            "LOCAL_ID_CONVERTER",
            "API_RESOLVER",
            "DATASET_OVERLAP_ANALYZER"
        ]
        
        for action_type in valid_actions:
            assert self.validate_action_type(action_type), f"{action_type} should be registered"
    
    def test_invalid_action_type(self):
        """Test that unknown action types are invalid."""
        invalid_actions = [
            "UNKNOWN_ACTION",
            "NOT_REGISTERED",
            "FAKE_ACTION"
        ]
        
        for action_type in invalid_actions:
            assert not self.validate_action_type(action_type), f"{action_type} should not be registered"


class TestActionParameterValidation:
    """Test validation of action parameters against expected schemas."""
    
    def get_required_params(self, action_type: str) -> Dict[str, Any]:
        """Get required parameters for an action type based on common patterns."""
        # This is a simplified version - in practice, each action would define its schema
        param_schemas = {
            "LOAD_ENDPOINT_IDENTIFIERS": {
                "required": ["endpoint_context", "input_ids_context_key"],
                "optional": []
            },
            "UNIPROT_HISTORICAL_RESOLVER": {
                "required": [],
                "optional": ["input_context_key", "output_context_key", "batch_size", "include_obsolete", "expand_composites"]
            },
            "LOCAL_ID_CONVERTER": {
                "required": ["mapping_file", "source_column", "target_column"],
                "optional": ["output_ontology_type", "output_context_key"]
            },
            "API_RESOLVER": {
                "required": ["input_context_key", "output_context_key", "api_base_url", "endpoint_path"],
                "optional": ["batch_size", "rate_limit_delay", "max_retries", "timeout"]
            },
            "DATASET_OVERLAP_ANALYZER": {
                "required": ["dataset1_context_key", "dataset2_context_key"],
                "optional": ["output_context_key", "dataset1_name", "dataset2_name", "generate_statistics"]
            }
        }
        return param_schemas.get(action_type, {"required": [], "optional": []})
    
    def validate_action_params(self, action_type: str, params: Dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate parameters for a given action type."""
        schema = self.get_required_params(action_type)
        errors = []
        
        # Check required parameters
        for required_param in schema["required"]:
            if required_param not in params:
                errors.append(f"Missing required parameter: {required_param}")
        
        # Check for unknown parameters
        all_params = set(schema["required"] + schema["optional"])
        for param in params:
            if param not in all_params and all_params:  # Only check if we have a schema
                errors.append(f"Unknown parameter: {param}")
        
        return len(errors) == 0, errors
    
    def test_valid_load_endpoint_params(self):
        """Test valid parameters for LOAD_ENDPOINT_IDENTIFIERS action."""
        params = {
            "endpoint_context": "SOURCE",
            "input_ids_context_key": "source_ids"
        }
        valid, errors = self.validate_action_params("LOAD_ENDPOINT_IDENTIFIERS", params)
        assert valid
        assert not errors
    
    def test_missing_required_params(self):
        """Test missing required parameters."""
        params = {
            "endpoint_context": "SOURCE"
            # Missing input_ids_context_key
        }
        valid, errors = self.validate_action_params("LOAD_ENDPOINT_IDENTIFIERS", params)
        assert not valid
        assert "Missing required parameter: input_ids_context_key" in errors
    
    def test_unknown_params(self):
        """Test unknown parameters are detected."""
        params = {
            "endpoint_context": "SOURCE",
            "input_ids_context_key": "source_ids",
            "unknown_param": "value"
        }
        valid, errors = self.validate_action_params("LOAD_ENDPOINT_IDENTIFIERS", params)
        assert not valid
        assert "Unknown parameter: unknown_param" in errors
    
    def test_valid_optional_params(self):
        """Test that optional parameters are accepted."""
        params = {
            "input_context_key": "historical_ids",
            "output_context_key": "current_ids",
            "batch_size": 200,
            "include_obsolete": False
        }
        valid, errors = self.validate_action_params("UNIPROT_HISTORICAL_RESOLVER", params)
        assert valid
        assert not errors


class TestYAMLStrategyLoading:
    """Test loading strategies from YAML files."""
    
    @pytest.fixture
    def fixtures_dir(self, tmp_path):
        """Create a temporary fixtures directory."""
        fixtures = tmp_path / "fixtures" / "strategies"
        fixtures.mkdir(parents=True)
        return fixtures
    
    def create_yaml_file(self, fixtures_dir: Path, filename: str, content: Dict[str, Any]):
        """Helper to create a YAML file."""
        file_path = fixtures_dir / filename
        with open(file_path, 'w') as f:
            yaml.dump(content, f)
        return file_path
    
    def load_strategy_from_yaml(self, file_path: Path) -> Strategy:
        """Load a strategy from a YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return Strategy(**data)
    
    def test_load_valid_strategy(self, fixtures_dir):
        """Test loading a valid strategy from YAML."""
        strategy_data = {
            "name": "VALID_STRATEGY",
            "description": "A valid test strategy",
            "steps": [
                {
                    "name": "LOAD_SOURCE",
                    "action": {
                        "type": "LOAD_ENDPOINT_IDENTIFIERS",
                        "params": {
                            "endpoint_context": "SOURCE",
                            "input_ids_context_key": "source_ids"
                        }
                    }
                },
                {
                    "name": "RESOLVE_IDS",
                    "action": {
                        "type": "UNIPROT_HISTORICAL_RESOLVER",
                        "params": {
                            "input_context_key": "source_ids",
                            "output_context_key": "resolved_ids",
                            "batch_size": 100
                        }
                    }
                }
            ]
        }
        
        file_path = self.create_yaml_file(fixtures_dir, "valid_strategy.yaml", strategy_data)
        strategy = self.load_strategy_from_yaml(file_path)
        
        assert strategy.name == "VALID_STRATEGY"
        assert strategy.description == "A valid test strategy"
        assert len(strategy.steps) == 2
        assert strategy.steps[0].name == "LOAD_SOURCE"
        assert strategy.steps[0].action.type == "LOAD_ENDPOINT_IDENTIFIERS"
        assert strategy.steps[1].name == "RESOLVE_IDS"
        assert strategy.steps[1].action.params["batch_size"] == 100
    
    def test_load_invalid_action_type(self, fixtures_dir):
        """Test loading a strategy with invalid action type."""
        strategy_data = {
            "name": "INVALID_ACTION_STRATEGY",
            "steps": [
                {
                    "name": "BAD_STEP",
                    "action": {
                        "type": "INVALID_ACTION_TYPE",
                        "params": {"key": "value"}
                    }
                }
            ]
        }
        
        file_path = self.create_yaml_file(fixtures_dir, "invalid_action.yaml", strategy_data)
        
        # The model itself will load, but validation should fail
        strategy = self.load_strategy_from_yaml(file_path)
        assert strategy.steps[0].action.type == "INVALID_ACTION_TYPE"
        
        # Validate action type
        validator = TestActionTypeValidation()
        assert not validator.validate_action_type(strategy.steps[0].action.type)
    
    def test_load_invalid_params(self, fixtures_dir):
        """Test loading a strategy with invalid parameters."""
        strategy_data = {
            "name": "INVALID_PARAMS_STRATEGY",
            "steps": [
                {
                    "name": "BAD_PARAMS",
                    "action": {
                        "type": "LOAD_ENDPOINT_IDENTIFIERS",
                        "params": {
                            "wrong_param": "value"
                            # Missing required params
                        }
                    }
                }
            ]
        }
        
        file_path = self.create_yaml_file(fixtures_dir, "invalid_params.yaml", strategy_data)
        strategy = self.load_strategy_from_yaml(file_path)
        
        # Validate parameters
        validator = TestActionParameterValidation()
        valid, errors = validator.validate_action_params(
            strategy.steps[0].action.type,
            strategy.steps[0].action.params or {}
        )
        assert not valid
        assert any("Missing required parameter" in e for e in errors)
    
    def test_load_missing_required_fields(self, fixtures_dir):
        """Test loading a strategy with missing required fields."""
        strategy_data = {
            # Missing 'name'
            "steps": [
                {
                    "name": "STEP",
                    "action": {"type": "SOME_ACTION"}
                }
            ]
        }
        
        file_path = self.create_yaml_file(fixtures_dir, "missing_name.yaml", strategy_data)
        
        with pytest.raises(ValueError):
            self.load_strategy_from_yaml(file_path)
    
    def test_load_strategy_with_metadata(self, fixtures_dir):
        """Test loading a strategy with additional metadata fields."""
        strategy_data = {
            "name": "METADATA_STRATEGY",
            "description": "Strategy with metadata",
            "version": "1.0.0",
            "author": "Test Author",
            "tags": ["protein", "mapping", "bidirectional"],
            "steps": [
                {
                    "name": "STEP",
                    "action": {"type": "SOME_ACTION"}
                }
            ]
        }
        
        file_path = self.create_yaml_file(fixtures_dir, "metadata_strategy.yaml", strategy_data)
        
        # Base model will ignore extra fields, but we can access raw data
        with open(file_path, 'r') as f:
            raw_data = yaml.safe_load(f)
        
        strategy = Strategy(**{k: v for k, v in raw_data.items() if k in ["name", "description", "steps"]})
        
        assert strategy.name == "METADATA_STRATEGY"
        assert raw_data.get("version") == "1.0.0"
        assert raw_data.get("author") == "Test Author"
        assert "protein" in raw_data.get("tags", [])


class TestStrategyValidationIntegration:
    """Integration tests for complete strategy validation workflow."""
    
    def validate_strategy(self, strategy: Strategy) -> tuple[bool, list[str]]:
        """Validate a complete strategy including action types and parameters."""
        errors = []
        
        # Check strategy has steps
        if not strategy.steps:
            errors.append("Strategy has no steps")
            return False, errors
        
        # Validate each step
        action_validator = TestActionTypeValidation()
        param_validator = TestActionParameterValidation()
        
        for i, step in enumerate(strategy.steps):
            # Validate action type
            if not action_validator.validate_action_type(step.action.type):
                errors.append(f"Step {i+1} ({step.name}): Unknown action type '{step.action.type}'")
            
            # Validate parameters
            valid, param_errors = param_validator.validate_action_params(
                step.action.type,
                step.action.params or {}
            )
            if not valid:
                for error in param_errors:
                    errors.append(f"Step {i+1} ({step.name}): {error}")
        
        return len(errors) == 0, errors
    
    def test_validate_complete_valid_strategy(self):
        """Test validating a complete valid strategy."""
        strategy = Strategy(
            name="COMPLETE_VALID_STRATEGY",
            description="A complete valid strategy",
            steps=[
                StrategyStep(
                    name="LOAD",
                    action=StepAction(
                        type="LOAD_ENDPOINT_IDENTIFIERS",
                        params={
                            "endpoint_context": "SOURCE",
                            "input_ids_context_key": "ids"
                        }
                    )
                ),
                StrategyStep(
                    name="CONVERT",
                    action=StepAction(
                        type="LOCAL_ID_CONVERTER",
                        params={
                            "mapping_file": "/path/to/file.csv",
                            "source_column": "col1",
                            "target_column": "col2"
                        }
                    )
                )
            ]
        )
        
        valid, errors = self.validate_strategy(strategy)
        assert valid
        assert not errors
    
    def test_validate_strategy_with_errors(self):
        """Test validating a strategy with multiple errors."""
        strategy = Strategy(
            name="INVALID_STRATEGY",
            steps=[
                StrategyStep(
                    name="BAD_ACTION",
                    action=StepAction(
                        type="UNKNOWN_ACTION",
                        params={"key": "value"}
                    )
                ),
                StrategyStep(
                    name="BAD_PARAMS",
                    action=StepAction(
                        type="LOAD_ENDPOINT_IDENTIFIERS",
                        params={"wrong": "params"}
                    )
                )
            ]
        )
        
        valid, errors = self.validate_strategy(strategy)
        assert not valid
        assert len(errors) >= 2
        assert any("Unknown action type" in e for e in errors)
        assert any("Missing required parameter" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
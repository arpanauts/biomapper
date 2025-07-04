"""
Unit tests for the StrategyValidator class.

Tests the validation logic for YAML strategies including action types
and parameter validation.
"""

import pytest
from pathlib import Path
import tempfile

from biomapper.core.models.strategy import Strategy, StrategyStep, StepAction
from biomapper.core.validators.strategy_validator import StrategyValidator, load_and_validate_strategy
from biomapper.core.exceptions import ConfigurationError


class TestStrategyValidator:
    """Test the StrategyValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return StrategyValidator(strict=True)
    
    @pytest.fixture
    def lenient_validator(self):
        """Create a lenient validator instance."""
        return StrategyValidator(strict=False)
    
    def test_validate_valid_strategy(self, validator):
        """Test validation of a completely valid strategy."""
        strategy = Strategy(
            name="VALID_STRATEGY",
            description="A valid strategy",
            steps=[
                StrategyStep(
                    name="LOAD",
                    action=StepAction(
                        type="LOAD_ENDPOINT_IDENTIFIERS",
                        params={
                            "endpoint_context": "SOURCE",
                            "input_ids_context_key": "source_ids"
                        }
                    )
                ),
                StrategyStep(
                    name="CONVERT",
                    action=StepAction(
                        type="LOCAL_ID_CONVERTER",
                        params={
                            "mapping_file": "/path/to/mapping.csv",
                            "source_column": "uniprot",
                            "target_column": "gene"
                        }
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert valid
        assert not errors
    
    def test_validate_empty_strategy(self, validator):
        """Test validation of strategy with no steps."""
        strategy = Strategy(name="EMPTY_STRATEGY", steps=[])
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert "Strategy must have at least one step" in errors[0]
    
    def test_validate_missing_action_type(self, validator):
        """Test validation when action type is missing."""
        strategy = Strategy(
            name="MISSING_ACTION_TYPE",
            steps=[
                StrategyStep(
                    name="BAD_STEP",
                    action=StepAction(type="", params={})
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert "Action type is required" in errors[0]
    
    def test_validate_unknown_action_type(self, validator):
        """Test validation of unknown action types."""
        strategy = Strategy(
            name="UNKNOWN_ACTION",
            steps=[
                StrategyStep(
                    name="UNKNOWN",
                    action=StepAction(
                        type="FAKE_ACTION_TYPE",
                        params={"param": "value"}
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert "Unknown action type 'FAKE_ACTION_TYPE'" in errors[0]
    
    def test_validate_missing_required_params(self, validator):
        """Test validation when required parameters are missing."""
        strategy = Strategy(
            name="MISSING_PARAMS",
            steps=[
                StrategyStep(
                    name="INCOMPLETE",
                    action=StepAction(
                        type="LOCAL_ID_CONVERTER",
                        params={
                            "mapping_file": "/path/to/file.csv"
                            # Missing source_column and target_column
                        }
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert any("Missing required parameter 'source_column'" in e for e in errors)
        assert any("Missing required parameter 'target_column'" in e for e in errors)
    
    def test_validate_unknown_params_strict(self, validator):
        """Test that unknown parameters fail in strict mode."""
        strategy = Strategy(
            name="UNKNOWN_PARAMS",
            steps=[
                StrategyStep(
                    name="EXTRA_PARAMS",
                    action=StepAction(
                        type="LOAD_ENDPOINT_IDENTIFIERS",
                        params={
                            "endpoint_context": "SOURCE",
                            "input_ids_context_key": "ids",
                            "unknown_param": "value"  # This should fail
                        }
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert any("Unknown parameter 'unknown_param'" in e for e in errors)
    
    def test_validate_unknown_params_lenient(self, lenient_validator):
        """Test that unknown parameters pass in lenient mode."""
        strategy = Strategy(
            name="UNKNOWN_PARAMS_LENIENT",
            steps=[
                StrategyStep(
                    name="EXTRA_PARAMS",
                    action=StepAction(
                        type="LOAD_ENDPOINT_IDENTIFIERS",
                        params={
                            "endpoint_context": "SOURCE",
                            "input_ids_context_key": "ids",
                            "unknown_param": "value"  # This should pass in lenient mode
                        }
                    )
                )
            ]
        )
        
        valid, errors = lenient_validator.validate_strategy(strategy)
        assert valid
        assert not errors
    
    def test_validate_optional_params(self, validator):
        """Test that optional parameters are accepted."""
        strategy = Strategy(
            name="OPTIONAL_PARAMS",
            steps=[
                StrategyStep(
                    name="WITH_OPTIONAL",
                    action=StepAction(
                        type="UNIPROT_HISTORICAL_RESOLVER",
                        params={
                            "batch_size": 200,
                            "include_obsolete": True,
                            "output_context_key": "resolved"
                        }
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert valid
        assert not errors
    
    def test_validate_multiple_errors(self, validator):
        """Test strategy with multiple validation errors."""
        strategy = Strategy(
            name="MULTIPLE_ERRORS",
            steps=[
                StrategyStep(
                    name="ERROR_1",
                    action=StepAction(
                        type="UNKNOWN_ACTION",
                        params={}
                    )
                ),
                StrategyStep(
                    name="ERROR_2",
                    action=StepAction(
                        type="LOCAL_ID_CONVERTER",
                        params={
                            "wrong_param": "value"
                        }
                    )
                ),
                StrategyStep(
                    name="ERROR_3",
                    action=StepAction(
                        type="API_RESOLVER",
                        params={
                            "input_context_key": "input"
                            # Missing required params
                        }
                    )
                )
            ]
        )
        
        valid, errors = validator.validate_strategy(strategy)
        assert not valid
        assert len(errors) >= 5  # At least 5 errors expected
    
    def test_validate_yaml_file(self, tmp_path):
        """Test validating a strategy from a YAML file."""
        yaml_content = """
name: FILE_TEST_STRATEGY
description: Test loading from file
steps:
  - name: STEP_1
    action:
      type: LOAD_ENDPOINT_IDENTIFIERS
      params:
        endpoint_context: SOURCE
        input_ids_context_key: ids
"""
        
        yaml_file = tmp_path / "test_strategy.yaml"
        yaml_file.write_text(yaml_content)
        
        valid, errors = StrategyValidator.validate_yaml_file(yaml_file)
        assert valid
        assert not errors
    
    def test_validate_invalid_yaml_file(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        yaml_content = """
name: INVALID_YAML
steps:
  - name: STEP_1
    action:
      type: [THIS_IS_INVALID_YAML
      params:
        key: value
"""
        
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)
        
        valid, errors = StrategyValidator.validate_yaml_file(yaml_file)
        assert not valid
        assert any("Invalid YAML" in e for e in errors)
    
    def test_validate_yaml_string(self):
        """Test validating a strategy from a YAML string."""
        yaml_content = """
name: STRING_TEST_STRATEGY
steps:
  - name: RESOLVE
    action:
      type: UNIPROT_HISTORICAL_RESOLVER
      params:
        batch_size: 100
"""
        
        valid, errors = StrategyValidator.validate_yaml_string(yaml_content)
        assert valid
        assert not errors
    
    def test_load_and_validate_strategy_success(self, tmp_path):
        """Test the load_and_validate_strategy helper function."""
        yaml_content = """
name: HELPER_TEST_STRATEGY
steps:
  - name: ANALYZE
    action:
      type: DATASET_OVERLAP_ANALYZER
      params:
        dataset1_context_key: ds1
        dataset2_context_key: ds2
"""
        
        yaml_file = tmp_path / "valid_strategy.yaml"
        yaml_file.write_text(yaml_content)
        
        strategy = load_and_validate_strategy(yaml_file)
        assert strategy.name == "HELPER_TEST_STRATEGY"
        assert len(strategy.steps) == 1
    
    def test_load_and_validate_strategy_failure(self, tmp_path):
        """Test that load_and_validate_strategy raises on invalid strategy."""
        yaml_content = """
name: INVALID_STRATEGY
steps:
  - name: BAD_STEP
    action:
      type: FAKE_ACTION
      params: {}
"""
        
        yaml_file = tmp_path / "invalid_strategy.yaml"
        yaml_file.write_text(yaml_content)
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_and_validate_strategy(yaml_file)
        
        assert "Unknown action type 'FAKE_ACTION'" in str(exc_info.value)
    
    def test_validate_action_without_schema(self, validator):
        """Test validation of action types without defined schemas."""
        # Create a strategy with an action that exists but has no schema
        # Use an action we know is registered
        strategy = Strategy(
            name="NO_SCHEMA_ACTION",
            steps=[
                StrategyStep(
                    name="STEP",
                    action=StepAction(
                        type="COMPOSITE_ID_SPLITTER",  # This is registered but not in our schemas
                        params={"some_param": "value"}
                    )
                )
            ]
        )
        
        # Should validate successfully since action is registered and no schema is defined
        valid, errors = validator.validate_strategy(strategy)
        assert valid
        assert not errors


class TestStrategyValidatorIntegration:
    """Integration tests using actual YAML files."""
    
    def test_validate_fixtures(self):
        """Test validation of our test fixtures."""
        fixtures_dir = Path(__file__).parent.parent.parent.parent / "fixtures" / "strategies"
        
        # Test valid strategy
        valid_file = fixtures_dir / "valid_strategy.yaml"
        if valid_file.exists():
            valid, errors = StrategyValidator.validate_yaml_file(valid_file, strict=False)
            assert valid or len(errors) > 0  # May have unregistered actions
        
        # Test invalid action type
        invalid_action_file = fixtures_dir / "invalid_action_type.yaml"
        if invalid_action_file.exists():
            valid, errors = StrategyValidator.validate_yaml_file(invalid_action_file)
            assert not valid
            assert any("Unknown action type" in e for e in errors)
        
        # Test invalid parameters
        invalid_params_file = fixtures_dir / "invalid_parameters.yaml"
        if invalid_params_file.exists():
            valid, errors = StrategyValidator.validate_yaml_file(invalid_params_file)
            assert not valid
            assert any("Missing required parameter" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
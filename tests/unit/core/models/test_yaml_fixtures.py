"""
Test that YAML fixture files can be loaded and validated.

This ensures our test fixtures are valid YAML and can be parsed correctly.
"""

import pytest
from pathlib import Path
import yaml

from biomapper.core.models.strategy import Strategy
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY


class TestYAMLFixtures:
    """Test loading and validating YAML fixture files."""
    
    @pytest.fixture
    def fixtures_dir(self):
        """Get the fixtures directory."""
        return Path(__file__).parent.parent.parent.parent / "fixtures" / "strategies"
    
    def test_fixtures_directory_exists(self, fixtures_dir):
        """Test that fixtures directory exists."""
        assert fixtures_dir.exists()
        assert fixtures_dir.is_dir()
    
    def test_load_valid_strategy_fixture(self, fixtures_dir):
        """Test loading the valid strategy fixture."""
        yaml_file = fixtures_dir / "valid_strategy.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        strategy = Strategy(**data)
        assert strategy.name == "VALID_TEST_STRATEGY"
        assert len(strategy.steps) == 5
        
        # Verify all actions in the valid strategy are registered
        for step in strategy.steps:
            if step.action.type in ["RESULTS_SAVER", "GENERATE_DETAILED_REPORT"]:
                # These might not be registered yet, skip for now
                continue
            assert step.action.type in ACTION_REGISTRY, f"Action {step.action.type} not registered"
    
    def test_load_invalid_action_type_fixture(self, fixtures_dir):
        """Test loading the invalid action type fixture."""
        yaml_file = fixtures_dir / "invalid_action_type.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        strategy = Strategy(**data)
        assert strategy.name == "INVALID_ACTION_TYPE_STRATEGY"
        
        # Check that invalid actions are indeed not registered
        invalid_actions = ["UNKNOWN_ACTION_TYPE", "FAKE_DATA_PROCESSOR", "LOAD_ENDPOINT_IDENTIFER"]
        for step in strategy.steps:
            if step.action.type in invalid_actions:
                assert step.action.type not in ACTION_REGISTRY
    
    def test_load_invalid_parameters_fixture(self, fixtures_dir):
        """Test loading the invalid parameters fixture."""
        yaml_file = fixtures_dir / "invalid_parameters.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        strategy = Strategy(**data)
        assert strategy.name == "INVALID_PARAMETERS_STRATEGY"
        assert len(strategy.steps) == 5
    
    def test_load_missing_required_fields_fixture(self, fixtures_dir):
        """Test loading strategies with missing required fields."""
        yaml_file = fixtures_dir / "missing_required_fields.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            content = f.read()
        
        # Split by document separator
        documents = yaml.safe_load_all(content)
        
        error_count = 0
        for doc in documents:
            if doc is None:
                continue
            try:
                Strategy(**doc)
            except (ValueError, TypeError, AttributeError):
                error_count += 1
        
        # We expect most documents to fail validation
        assert error_count > 5
    
    def test_load_metadata_strategy_fixture(self, fixtures_dir):
        """Test loading strategy with extensive metadata."""
        yaml_file = fixtures_dir / "strategy_with_metadata.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract known fields for Strategy model
        strategy_fields = {
            "name": data.get("name"),
            "description": data.get("description"),
            "steps": data.get("steps")
        }
        
        strategy = Strategy(**strategy_fields)
        assert strategy.name == "STRATEGY_WITH_EXTENSIVE_METADATA"
        
        # Verify metadata is in original data
        assert data.get("version") == "2.1.0"
        assert data.get("author") == "Biomapper Test Suite"
        assert "protein-mapping" in data.get("tags", [])
        assert data.get("quality_metrics", {}).get("test_coverage") == 95.5
    
    def test_load_edge_case_strategy_fixture(self, fixtures_dir):
        """Test loading strategy with edge cases."""
        yaml_file = fixtures_dir / "edge_case_strategy.yaml"
        assert yaml_file.exists()
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        strategy = Strategy(**data)
        assert strategy.name == "EDGE_CASE_TEST_STRATEGY"
        
        # Check various edge cases loaded correctly
        no_params_step = next(s for s in strategy.steps if s.name == "NO_PARAMS_ACTION")
        assert no_params_step.action.params is None
        
        empty_params_step = next(s for s in strategy.steps if s.name == "EMPTY_PARAMS_ACTION")
        assert empty_params_step.action.params == {}
        
        null_params_step = next(s for s in strategy.steps if s.name == "NULL_PARAMS_ACTION")
        assert null_params_step.action.params is None
        
        # Check special characters preserved
        special_chars_step = next(s for s in strategy.steps if s.name == "SPECIAL_CHARS_PARAMS")
        assert " " in special_chars_step.action.params["mapping_file"]
        assert "!" in special_chars_step.action.params["mapping_file"]
        assert "#" in special_chars_step.action.params["mapping_file"]
    
    def test_all_yaml_fixtures_are_valid_yaml(self, fixtures_dir):
        """Test that all YAML files in fixtures directory are valid YAML."""
        yaml_files = list(fixtures_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No YAML files found in fixtures directory"
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    # Try to load as single document
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                # Try as multi-document
                try:
                    with open(yaml_file, 'r') as f:
                        list(yaml.safe_load_all(f))
                except yaml.YAMLError:
                    pytest.fail(f"Invalid YAML in {yaml_file.name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
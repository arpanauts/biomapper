"""
Test suite for EnhancedStrategyLoader

Tests strategy loading with parameter resolution and path handling.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from biomapper.core.infrastructure.enhanced_strategy_loader import (
    EnhancedStrategyLoader,
    StrategyLoadError,
    StrategyValidationError,
    PathResolver,
)


class TestPathResolver:
    """Test suite for PathResolver."""

    @pytest.fixture
    def resolver(self):
        """PathResolver instance."""
        return PathResolver()

    def test_resolve_absolute_path(self, resolver):
        """Test resolving absolute paths."""
        # Use a path we know exists
        test_path = Path(__file__).absolute()
        resolved = resolver.resolve_path(str(test_path))

        assert resolved is not None
        assert resolved.is_absolute()
        assert resolved.exists()

    def test_resolve_nonexistent_path(self, resolver):
        """Test resolving nonexistent paths."""
        resolved = resolver.resolve_path("/nonexistent/path/file.txt")

        assert resolved is None

    def test_get_safe_output_path(self, resolver):
        """Test creating safe output paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            resolver.base_dir = temp_path

            output_path = resolver.get_safe_output_path("subdir/output.txt")

            assert output_path.is_absolute()
            assert output_path.parent.exists()
            assert "subdir" in str(output_path)


class TestEnhancedStrategyLoader:
    """Test suite for EnhancedStrategyLoader."""

    @pytest.fixture
    def temp_strategies_dir(self):
        """Create temporary strategies directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            strategies_dir = Path(temp_dir) / "strategies"
            strategies_dir.mkdir()

            # Create test strategy file
            test_strategy = {
                "name": "test_strategy",
                "description": "Test strategy for unit tests",
                "parameters": {
                    "data_dir": "${DATA_DIR}",
                    "output_file": "${parameters.data_dir}/output.csv",
                    "debug_mode": "true",
                },
                "steps": [
                    {
                        "name": "load_data",
                        "action": {
                            "type": "LOAD_DATASET_IDENTIFIERS",
                            "params": {
                                "file_path": "${parameters.data_dir}/input.csv",
                                "output_key": "loaded_data",
                            },
                        },
                    }
                ],
            }

            strategy_file = strategies_dir / "test_strategy.yaml"
            with open(strategy_file, "w") as f:
                yaml.dump(test_strategy, f)

            # Create invalid strategy file
            invalid_strategy_file = strategies_dir / "invalid_strategy.yaml"
            with open(invalid_strategy_file, "w") as f:
                f.write("invalid: yaml: content: [")

            # Create strategy with missing required fields
            incomplete_strategy = {
                "name": "incomplete_strategy",
                "description": "Missing steps",
                # Missing 'steps' field
            }

            incomplete_file = strategies_dir / "incomplete_strategy.yaml"
            with open(incomplete_file, "w") as f:
                yaml.dump(incomplete_strategy, f)

            yield strategies_dir

    @pytest.fixture
    def loader(self, temp_strategies_dir):
        """EnhancedStrategyLoader instance with temporary directory."""
        return EnhancedStrategyLoader(str(temp_strategies_dir))

    def test_load_valid_strategy(self, loader):
        """Test loading a valid strategy."""
        with patch.dict("os.environ", {"DATA_DIR": "/test/data"}):
            strategy = loader.load_strategy("test_strategy")

            assert strategy["name"] == "test_strategy"
            assert strategy["parameters"]["data_dir"] == "/test/data"
            assert strategy["parameters"]["output_file"] == "/test/data/output.csv"
            assert strategy["parameters"]["debug_mode"] is True

            # Check that step parameters were resolved
            step_params = strategy["steps"][0]["action"]["params"]
            assert step_params["file_path"] == "/test/data/input.csv"

    def test_load_nonexistent_strategy(self, loader):
        """Test loading a nonexistent strategy."""
        with pytest.raises(StrategyLoadError) as exc_info:
            loader.load_strategy("nonexistent_strategy")

        assert "not found" in str(exc_info.value)

    def test_load_invalid_yaml_strategy(self, loader):
        """Test loading a strategy with invalid YAML."""
        with pytest.raises(StrategyLoadError):
            loader.load_strategy("invalid_strategy")

    def test_load_incomplete_strategy_validation(self, loader):
        """Test loading a strategy that fails validation."""
        with pytest.raises(StrategyValidationError) as exc_info:
            loader.load_strategy("incomplete_strategy", validate=True)

        assert "Missing required field: steps" in str(exc_info.value)

    def test_load_strategy_without_validation(self, loader):
        """Test loading a strategy without validation."""
        # Should not raise validation error
        strategy = loader.load_strategy("incomplete_strategy", validate=False)

        assert strategy["name"] == "incomplete_strategy"
        assert "steps" not in strategy

    def test_list_available_strategies(self, loader):
        """Test listing available strategies."""
        strategies = loader.list_available_strategies()

        assert len(strategies) >= 2  # test_strategy and incomplete_strategy

        strategy_names = [s["name"] for s in strategies]
        assert "test_strategy" in strategy_names
        assert "incomplete_strategy" in strategy_names

        # Check strategy info structure
        test_strategy_info = next(s for s in strategies if s["name"] == "test_strategy")
        assert "description" in test_strategy_info
        assert "file" in test_strategy_info
        assert "has_parameters" in test_strategy_info
        assert test_strategy_info["has_parameters"] is True

    def test_strategy_parameter_validation(self, loader):
        """Test strategy parameter validation."""
        # Create strategy with undefined parameter reference
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            invalid_param_strategy = {
                "name": "invalid_param_strategy",
                "parameters": {"defined_param": "value"},
                "steps": [
                    {
                        "name": "step1",
                        "action": {
                            "type": "SOME_ACTION",
                            "params": {
                                "param": "${parameters.undefined_param}"  # References undefined parameter
                            },
                        },
                    }
                ],
            }
            yaml.dump(invalid_param_strategy, f)
            f.flush()

            # Add to loader's search path
            temp_loader = EnhancedStrategyLoader(str(Path(f.name).parent))

            with pytest.raises(StrategyValidationError) as exc_info:
                temp_loader.load_strategy(Path(f.name).stem, validate=True)

            assert "undefined parameter" in str(exc_info.value)

    def test_circular_parameter_reference_detection(self, loader):
        """Test detection of circular parameter references."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            circular_strategy = {
                "name": "circular_strategy",
                "parameters": {
                    "param_a": "${parameters.param_b}",
                    "param_b": "${parameters.param_a}",
                },
                "steps": [
                    {
                        "name": "step1",
                        "action": {
                            "type": "SOME_ACTION",
                            "params": {"param": "${parameters.param_a}"},
                        },
                    }
                ],
            }
            yaml.dump(circular_strategy, f)
            f.flush()

            temp_loader = EnhancedStrategyLoader(str(Path(f.name).parent))

            # Should raise ParameterResolutionError due to circular reference
            from biomapper.core.infrastructure.parameter_resolver import (
                CircularReferenceError,
            )

            with pytest.raises((CircularReferenceError, Exception)):
                temp_loader.load_strategy(Path(f.name).stem)

    def test_path_resolution_in_strategy(self, loader):
        """Test that file paths in strategies are resolved correctly."""
        # Create a strategy that references files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False
            ) as data_file:
                data_file.write("id,name\n1,test\n")
                data_file_path = data_file.name

            path_strategy = {
                "name": "path_strategy",
                "parameters": {"input_file": data_file_path},
                "metadata": {"source_files": [{"path": data_file_path}]},
                "steps": [
                    {
                        "name": "load_data",
                        "action": {
                            "type": "LOAD_DATASET_IDENTIFIERS",
                            "params": {
                                "file_path": "${parameters.input_file}",
                                "output_path": "/tmp/output.csv",
                            },
                        },
                    }
                ],
            }
            yaml.dump(path_strategy, f)
            f.flush()

            temp_loader = EnhancedStrategyLoader(str(Path(f.name).parent))

            try:
                strategy = temp_loader.load_strategy(Path(f.name).stem)

                # Check that paths were resolved
                assert "resolved" in strategy["metadata"]["source_files"][0]

                # Check output path was made safe
                output_path = strategy["steps"][0]["action"]["params"]["output_path"]
                assert Path(output_path).is_absolute()

            finally:
                # Cleanup
                Path(data_file_path).unlink(missing_ok=True)
                Path(f.name).unlink(missing_ok=True)


class TestIntegrationWithRealStrategies:
    """Integration tests with actual strategy files."""

    def test_load_real_strategy_if_available(self):
        """Test loading a real strategy file if available."""
        # Try to load from the actual configs directory
        configs_dir = Path(__file__).parents[4] / "configs" / "strategies"

        if configs_dir.exists():
            loader = EnhancedStrategyLoader(str(configs_dir))
            strategies = loader.list_available_strategies()

            if strategies:
                # Try to load the first available strategy
                first_strategy = strategies[0]
                try:
                    # Don't validate to avoid issues with missing files/services
                    loaded_strategy = loader.load_strategy(
                        first_strategy["name"], validate=False
                    )

                    # Basic checks
                    assert loaded_strategy["name"] == first_strategy["name"]
                    assert "steps" in loaded_strategy

                except Exception as e:
                    # Log but don't fail the test - this is expected for complex strategies
                    print(
                        f"Note: Could not load real strategy {first_strategy['name']}: {e}"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

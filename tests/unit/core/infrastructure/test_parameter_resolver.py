"""
Comprehensive test suite for ParameterResolver

Tests all aspects of parameter resolution including:
- Environment variable substitution
- Nested parameter references
- Circular reference detection
- Type conversion
- Complex pattern resolution
- Error handling
"""

import pytest
import os
from unittest.mock import patch

from biomapper.core.infrastructure.parameter_resolver import (
    ParameterResolver,
    ParameterResolutionError,
)


class TestParameterResolver:
    """Test suite for ParameterResolver."""

    @pytest.fixture
    def resolver(self):
        """ParameterResolver instance."""
        return ParameterResolver()

    @pytest.fixture
    def sample_strategy(self):
        """Sample strategy for testing."""
        return {
            "name": "test_strategy",
            "parameters": {
                "data_dir": "${DATA_DIR}",
                "output_file": "${parameters.data_dir}/output.tsv",
                "debug_mode": "true",
                "max_items": "100",
            },
            "metadata": {
                "source_files": [{"path": "${parameters.data_dir}/input.csv"}]
            },
            "steps": [
                {
                    "name": "load_data",
                    "action": {
                        "type": "LOAD_DATASET",
                        "params": {
                            "file_path": "${metadata.source_files[0].path}",
                            "output_key": "loaded_data",
                        },
                    },
                }
            ],
        }

    def test_simple_environment_variable_resolution(self, resolver):
        """Test simple environment variable resolution."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            strategy = {"parameters": {"test_param": "${TEST_VAR}"}}

            resolved = resolver.resolve_strategy_parameters(strategy)

            assert resolved["parameters"]["test_param"] == "test_value"

    def test_environment_variable_with_defaults(self, resolver):
        """Test environment variable resolution with defaults."""
        # Test that DATA_DIR gets default value when not set
        with patch.dict(os.environ, {}, clear=True):
            strategy = {"parameters": {"data_path": "${DATA_DIR}"}}

            resolved = resolver.resolve_strategy_parameters(strategy)

            # Should use default from resolver.env_defaults
            assert resolved["parameters"]["data_path"] == "/procedure/data/local_data"

    def test_parameter_reference_resolution(self, resolver):
        """Test parameter-to-parameter references."""
        strategy = {
            "parameters": {
                "base_dir": "/data",
                "input_file": "${parameters.base_dir}/input.csv",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["base_dir"] == "/data"
        assert resolved["parameters"]["input_file"] == "/data/input.csv"

    def test_nested_metadata_access(self, resolver):
        """Test nested metadata access."""
        strategy = {
            "metadata": {
                "source_files": [
                    {"path": "/data/file1.csv"},
                    {"path": "/data/file2.csv"},
                ]
            },
            "parameters": {
                "first_file": "${metadata.source_files[0].path}",
                "second_file": "${metadata.source_files[1].path}",
            },
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["first_file"] == "/data/file1.csv"
        assert resolved["parameters"]["second_file"] == "/data/file2.csv"

    def test_type_conversion(self, resolver):
        """Test automatic type conversion."""
        strategy = {
            "parameters": {
                "debug_flag": "true",
                "max_count": "100",
                "threshold": "0.85",
                "items_list": "item1,item2,item3",
                "false_flag": "false",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["debug_flag"] is True
        assert resolved["parameters"]["false_flag"] is False
        assert resolved["parameters"]["max_count"] == 100
        assert resolved["parameters"]["threshold"] == 0.85
        assert resolved["parameters"]["items_list"] == ["item1", "item2", "item3"]

    def test_circular_reference_detection(self, resolver):
        """Test circular reference detection."""
        strategy = {
            "parameters": {
                "param_a": "${parameters.param_b}",
                "param_b": "${parameters.param_a}",
            }
        }

        with pytest.raises(ParameterResolutionError) as exc_info:
            resolver.resolve_strategy_parameters(strategy)

        # Check that the underlying cause is circular dependency
        assert "Circular dependency detected" in str(exc_info.value)

    def test_complex_circular_reference(self, resolver):
        """Test detection of complex circular references."""
        strategy = {
            "parameters": {
                "param_a": "${parameters.param_b}",
                "param_b": "${parameters.param_c}",
                "param_c": "${parameters.param_a}",
            }
        }

        with pytest.raises(ParameterResolutionError) as exc_info:
            resolver.resolve_strategy_parameters(strategy)

        assert "Circular dependency detected" in str(exc_info.value)

    def test_complex_nested_resolution(self, resolver, sample_strategy):
        """Test complex nested parameter resolution."""
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            resolved = resolver.resolve_strategy_parameters(sample_strategy)

            assert resolved["parameters"]["data_dir"] == "/test/data"
            assert resolved["parameters"]["output_file"] == "/test/data/output.tsv"
            assert resolved["parameters"]["debug_mode"] is True
            assert resolved["parameters"]["max_items"] == 100

            # Check metadata resolution
            assert (
                resolved["metadata"]["source_files"][0]["path"]
                == "/test/data/input.csv"
            )

            # Check step parameter resolution
            step_params = resolved["steps"][0]["action"]["params"]
            assert step_params["file_path"] == "/test/data/input.csv"

    def test_missing_environment_variable(self, resolver):
        """Test handling of missing environment variables."""
        strategy = {"parameters": {"missing_var": "${COMPLETELY_MISSING_VAR}"}}

        # Should not raise error but return pattern as-is with warning
        resolved = resolver.resolve_strategy_parameters(strategy)

        # Check that it returns the unresolved pattern
        param_value = resolved["parameters"]["missing_var"]
        assert "${COMPLETELY_MISSING_VAR}" in str(param_value)

    def test_parameter_dependency_ordering(self, resolver):
        """Test that parameters are resolved in correct dependency order."""
        strategy = {
            "parameters": {
                "final_path": "${parameters.base_path}/final",
                "base_path": "${parameters.root}/base",
                "root": "/data",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["root"] == "/data"
        assert resolved["parameters"]["base_path"] == "/data/base"
        assert resolved["parameters"]["final_path"] == "/data/base/final"

    @patch("biomapper.core.infrastructure.parameter_resolver.datetime")
    def test_builtin_variables(self, mock_datetime, resolver):
        """Test built-in variable resolution."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"

        strategy = {
            "parameters": {
                "timestamp": "${builtin.current_time}",
                "base_dir": "${builtin.base_dir}",
                "user": "${builtin.user}",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["timestamp"] == "2023-01-01T12:00:00"
        assert "base_dir" in resolved["parameters"]
        assert "user" in resolved["parameters"]

    def test_array_index_access(self, resolver):
        """Test array index access in nested references."""
        strategy = {
            "metadata": {
                "files": [
                    {"name": "file1.csv", "size": 1000},
                    {"name": "file2.csv", "size": 2000},
                ]
            },
            "parameters": {
                "first_file_name": "${metadata.files[0].name}",
                "second_file_size": "${metadata.files[1].size}",
                "invalid_index": "${metadata.files[5].name}",  # Should return unresolved pattern
            },
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["first_file_name"] == "file1.csv"
        assert resolved["parameters"]["second_file_size"] == 2000
        # Invalid index should return unresolved pattern
        assert "${metadata.files[5].name}" in str(
            resolved["parameters"]["invalid_index"]
        )

    def test_mixed_substitution_patterns(self, resolver):
        """Test mixing different substitution patterns in one value."""
        with patch.dict(
            os.environ, {"BASE_URL": "https://api.example.com", "API_VERSION": "v1"}
        ):
            strategy = {
                "parameters": {"api_endpoint": "${BASE_URL}/${API_VERSION}/data"}
            }

            resolved = resolver.resolve_strategy_parameters(strategy)

            assert (
                resolved["parameters"]["api_endpoint"]
                == "https://api.example.com/v1/data"
            )

    def test_nested_substitution(self, resolver):
        """Test nested parameter substitutions."""
        strategy = {
            "parameters": {
                "env_name": "production",
                "config_key": "database_${parameters.env_name}",
                "full_config": "config.${parameters.config_key}.host",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["env_name"] == "production"
        assert resolved["parameters"]["config_key"] == "database_production"
        assert (
            resolved["parameters"]["full_config"] == "config.database_production.host"
        )

    def test_invalid_parameter_reference(self, resolver):
        """Test handling of invalid parameter references."""
        strategy = {
            "parameters": {
                "valid_param": "valid_value",
                "invalid_ref": "${parameters.nonexistent_param}",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        # Should handle gracefully
        assert resolved["parameters"]["valid_param"] == "valid_value"
        # Invalid reference should remain as unresolved pattern
        assert (
            resolved["parameters"]["invalid_ref"] == "${parameters.nonexistent_param}"
        )

    def test_max_substitution_limit(self, resolver):
        """Test that maximum substitution limit prevents infinite loops."""
        strategy = {
            "parameters": {
                # This creates a substitution that would loop indefinitely
                "param_a": "${parameters.param_b}_a",
                "param_b": "${parameters.param_a}_b",
            }
        }

        # Should detect circular dependency and raise error
        with pytest.raises(ParameterResolutionError) as exc_info:
            resolver.resolve_strategy_parameters(strategy)

        assert "Circular dependency detected" in str(exc_info.value)

    def test_empty_parameter_value(self, resolver):
        """Test handling of empty parameter values."""
        strategy = {
            "parameters": {
                "empty_param": "",
                "null_param": None,
                "whitespace_param": "   ",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["empty_param"] == ""
        assert resolved["parameters"]["null_param"] is None
        assert resolved["parameters"]["whitespace_param"] == "   "

    def test_special_characters_in_values(self, resolver):
        """Test parameter values containing special characters."""
        strategy = {
            "parameters": {
                "special_chars": "value with spaces and $pecial ch@rs!",
                "json_like": '{"key": "value", "number": 123}',
                "path_with_vars": "/path/with/${DATA_DIR}/subpath",
            }
        }

        with patch.dict(os.environ, {"DATA_DIR": "data"}):
            resolved = resolver.resolve_strategy_parameters(strategy)

        assert (
            resolved["parameters"]["special_chars"]
            == "value with spaces and $pecial ch@rs!"
        )
        assert resolved["parameters"]["json_like"] == '{"key": "value", "number": 123}'
        assert resolved["parameters"]["path_with_vars"] == "/path/with/data/subpath"


class TestParameterResolutionIntegration:
    """Integration tests for parameter resolution with real strategy patterns."""

    def test_environment_variable_patterns(self):
        """Test the actual environment variable patterns found in strategies."""
        resolver = ParameterResolver()

        strategy = {
            "parameters": {
                "data_dir": "${DATA_DIR}",
                "output_dir": "${OUTPUT_DIR}",
                "cache_dir": "${CACHE_DIR}",
            }
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        # Should use defaults since these vars likely aren't set
        assert resolved["parameters"]["data_dir"] == "/procedure/data/local_data"
        assert resolved["parameters"]["output_dir"] == "/tmp/biomapper/output"
        assert resolved["parameters"]["cache_dir"] == "/tmp/biomapper/cache"

    def test_complex_metadata_access_patterns(self):
        """Test complex metadata access patterns found in real strategies."""
        resolver = ParameterResolver()

        strategy = {
            "metadata": {
                "steps": {
                    "baseline_fuzzy_match": {
                        "metrics": {"matched_count": 150, "unmatched_count": 50}
                    },
                    "iterative_refinement": {"metrics": {"quality_score": 0.85}},
                }
            },
            "parameters": {
                "matched_count": "${metadata.steps.baseline_fuzzy_match.metrics.matched_count}",
                "quality_threshold": "${metadata.steps.iterative_refinement.metrics.quality_score}",
            },
        }

        resolved = resolver.resolve_strategy_parameters(strategy)

        assert resolved["parameters"]["matched_count"] == 150
        assert resolved["parameters"]["quality_threshold"] == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

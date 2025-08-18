"""Tests for parameter_resolver.py."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from core.infrastructure.parameter_resolver import (
    ParameterResolver,
    ParameterResolutionError,
    CircularReferenceError
)


class TestParameterResolver:
    """Test ParameterResolver functionality."""
    
    @pytest.fixture
    def resolver(self):
        """Create test resolver."""
        return ParameterResolver()
    
    @pytest.fixture
    def strategy_config(self):
        """Create basic strategy configuration."""
        return {
            "name": "test_strategy",
            "parameters": {
                "output_dir": "/tmp/test",
                "threshold": "0.85",
                "enable_logging": "true",
                "nested": {
                    "deep": {
                        "value": "deep_config"
                    }
                }
            },
            "metadata": {
                "version": "1.0.0",
                "source_files": [
                    {"path": "/data/proteins.tsv", "type": "protein"},
                    {"path": "/data/metabolites.csv", "type": "metabolite"}
                ]
            }
        }
    
    def test_basic_parameter_substitution(self, resolver, strategy_config):
        """Test basic parameter substitution."""
        test_strategy = {
            "parameters": {"base_path": "/tmp"},
            "steps": [
                {
                    "action": {
                        "params": {
                            "output_path": "${parameters.base_path}/output"
                        }
                    }
                }
            ]
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["steps"][0]["action"]["params"]["output_path"] == "/tmp/output"
    
    def test_environment_variable_substitution(self, resolver):
        """Test environment variable substitution."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            test_strategy = {
                "parameters": {
                    "env_path": "${env.TEST_VAR}/subdir"
                }
            }
            
            result = resolver.resolve_parameters(test_strategy)
            
            assert result["parameters"]["env_path"] == "test_value/subdir"
    
    def test_environment_variable_direct_access(self, resolver):
        """Test direct environment variable access without env prefix."""
        with patch.dict(os.environ, {"TEST_DIRECT": "direct_value"}):
            test_strategy = {
                "parameters": {
                    "direct_path": "${TEST_DIRECT}/path"
                }
            }
            
            result = resolver.resolve_parameters(test_strategy)
            
            assert result["parameters"]["direct_path"] == "direct_value/path"
    
    def test_metadata_array_access(self, resolver, strategy_config):
        """Test metadata array access with indices."""
        test_strategy = {
            "metadata": {
                "source_files": [
                    {"path": "/data/proteins.tsv"},
                    {"path": "/data/metabolites.csv"}
                ]
            },
            "parameters": {
                "first_file": "${metadata.source_files[0].path}",
                "second_file": "${metadata.source_files[1].path}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["first_file"] == "/data/proteins.tsv"
        assert result["parameters"]["second_file"] == "/data/metabolites.csv"
    
    def test_nested_object_access(self, resolver, strategy_config):
        """Test nested object access."""
        test_strategy = {
            "parameters": {
                "config": {
                    "nested": {
                        "value": "nested_data"
                    }
                },
                "extracted": "${parameters.config.nested.value}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["extracted"] == "nested_data"
    
    def test_default_value_handling(self, resolver):
        """Test default value handling for missing variables."""
        test_strategy = {
            "parameters": {
                "with_default": "${MISSING_VAR:-default_value}",
                "env_with_default": "${env.MISSING_ENV:-env_default}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["with_default"] == "default_value"
        assert result["parameters"]["env_with_default"] == "env_default"
    
    def test_circular_reference_detection(self, resolver):
        """Test circular reference detection."""
        test_strategy = {
            "parameters": {
                "a": "${parameters.b}",
                "b": "${parameters.a}"
            }
        }
        
        with pytest.raises(CircularReferenceError):
            resolver.resolve_parameters(test_strategy)
    
    def test_complex_circular_reference(self, resolver):
        """Test detection of complex circular references."""
        test_strategy = {
            "parameters": {
                "a": "${parameters.b}",
                "b": "${parameters.c}",
                "c": "${parameters.a}"
            }
        }
        
        with pytest.raises(CircularReferenceError):
            resolver.resolve_parameters(test_strategy)
    
    def test_invalid_syntax_handling(self, resolver):
        """Test handling of invalid placeholder syntax."""
        test_strategy = {
            "parameters": {
                "invalid2": "${malformed",  # Missing closing brace
                "invalid3": "normal_string"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        # Should preserve invalid placeholders and not raise errors
        assert result["parameters"]["invalid2"] == "${malformed"
        assert result["parameters"]["invalid3"] == "normal_string"
    
    def test_type_conversion_string_to_int(self, resolver):
        """Test type conversion from string to int."""
        test_strategy = {
            "parameters": {
                "count": "42"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["count"] == 42
        assert isinstance(result["parameters"]["count"], int)
    
    def test_type_conversion_string_to_float(self, resolver):
        """Test type conversion from string to float."""
        test_strategy = {
            "parameters": {
                "threshold": "0.85"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["threshold"] == 0.85
        assert isinstance(result["parameters"]["threshold"], float)
    
    def test_type_conversion_string_to_bool(self, resolver):
        """Test type conversion from string to boolean."""
        test_strategy = {
            "parameters": {
                "enable_feature": "true",
                "disable_feature": "false",
                "mixed_case": "True",
                "uppercase": "FALSE"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["enable_feature"] is True
        assert result["parameters"]["disable_feature"] is False
        assert result["parameters"]["mixed_case"] is True
        assert result["parameters"]["uppercase"] is False
    
    def test_complex_nested_structures(self, resolver):
        """Test complex nested dict/list combinations."""
        test_strategy = {
            "parameters": {
                "base_config": {
                    "settings": [
                        {"name": "setting1", "value": "val1"},
                        {"name": "setting2", "value": "val2"}
                    ]
                },
                "extracted_setting": "${parameters.base_config.settings[0].value}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["extracted_setting"] == "val1"
    
    def test_edge_cases_empty_strings(self, resolver):
        """Test edge cases with empty strings."""
        test_strategy = {
            "parameters": {
                "empty": "",
                "using_empty": "${parameters.empty}",
                "fallback": "${parameters.empty:-fallback_value}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["empty"] == ""
        assert result["parameters"]["using_empty"] == ""
        assert result["parameters"]["fallback"] == "fallback_value"
    
    def test_edge_cases_none_values(self, resolver):
        """Test edge cases with None values."""
        test_strategy = {
            "parameters": {
                "none_value": None,
                "list_with_none": [None, "value", None]
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["none_value"] is None
        assert result["parameters"]["list_with_none"] == [None, "value", None]
    
    def test_edge_cases_missing_keys(self, resolver):
        """Test edge cases with missing keys."""
        test_strategy = {
            "parameters": {
                "existing": "value"
            },
            "step": {
                "param": "${parameters.missing_key}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        # Should preserve the placeholder when key is missing
        assert result["step"]["param"] == "${parameters.missing_key}"
    
    def test_biological_data_patterns(self, resolver):
        """Test with realistic biological identifier patterns."""
        test_strategy = {
            "parameters": {
                "uniprot_base": "P12345",
                "hmdb_base": "HMDB0000001",
                "ensembl_base": "ENSP00000000233"
            },
            "datasets": {
                "protein_file": "/data/proteins_${parameters.uniprot_base}.tsv",
                "metabolite_file": "/data/metabolites_${parameters.hmdb_base}.csv",
                "gene_file": "/data/genes_${parameters.ensembl_base}.bed"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["datasets"]["protein_file"] == "/data/proteins_P12345.tsv"
        assert result["datasets"]["metabolite_file"] == "/data/metabolites_HMDB0000001.csv"
        assert result["datasets"]["gene_file"] == "/data/genes_ENSP00000000233.bed"
    
    def test_array_index_out_of_bounds(self, resolver):
        """Test array index out of bounds handling."""
        test_strategy = {
            "metadata": {
                "files": ["file1.txt", "file2.txt"]
            },
            "parameters": {
                "valid_index": "${metadata.files[0]}",
                "invalid_index": "${metadata.files[5]}"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["valid_index"] == "file1.txt"
        # Should preserve original placeholder for invalid index
        assert result["parameters"]["invalid_index"] == "${metadata.files[5]}"
    
    def test_multi_pass_resolution(self, resolver):
        """Test multi-pass resolution for dependent parameters."""
        test_strategy = {
            "parameters": {
                "base": "/tmp",
                "subdir": "${parameters.base}/data",
                "final_path": "${parameters.subdir}/output.txt"
            }
        }
        
        result = resolver.resolve_parameters(test_strategy)
        
        assert result["parameters"]["base"] == "/tmp"
        assert result["parameters"]["subdir"] == "/tmp/data"
        assert result["parameters"]["final_path"] == "/tmp/data/output.txt"
    
    def test_cache_efficiency(self, resolver):
        """Test caching efficiency for repeated resolutions."""
        test_strategy = {
            "parameters": {
                "repeated": "${parameters.base}",
                "base": "cached_value"
            }
        }
        
        # First resolution
        result1 = resolver.resolve_parameters(test_strategy)
        
        # Second resolution should use cache
        result2 = resolver.resolve_parameters(test_strategy)
        
        assert result1 == result2
        assert result1["parameters"]["repeated"] == "cached_value"


class TestParameterResolverPerformance:
    """Performance tests for ParameterResolver."""
    
    @pytest.mark.performance
    def test_large_configuration_performance(self):
        """Test performance with large configuration."""
        resolver = ParameterResolver()
        
        # Create large strategy with many parameters
        large_strategy = {
            "parameters": {f"param_{i}": f"value_{i}" for i in range(1000)},
            "steps": []
        }
        
        # Add references to parameters
        for i in range(100):
            large_strategy["steps"].append({
                "action": {
                    "params": {
                        "ref": f"${{parameters.param_{i * 10}}}"
                    }
                }
            })
        
        import time
        start_time = time.time()
        result = resolver.resolve_parameters(large_strategy)
        end_time = time.time()
        
        # Should complete within reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        assert len(result["parameters"]) == 1000
    
    @pytest.mark.performance
    def test_deep_nesting_performance(self):
        """Test performance with deep nesting scenarios."""
        resolver = ParameterResolver()
        
        # Create deeply nested structure
        nested_data = {"level_0": {}}
        current = nested_data["level_0"]
        
        for i in range(1, 20):
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]
        
        current["deep_value"] = "found_it"
        
        test_strategy = {
            "parameters": nested_data,
            "target": "${parameters.level_0.level_1.level_2.level_3.level_4.level_5.level_6.level_7.level_8.level_9.level_10.level_11.level_12.level_13.level_14.level_15.level_16.level_17.level_18.level_19.deep_value}"
        }
        
        import time
        start_time = time.time()
        result = resolver.resolve_parameters(test_strategy)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 0.5
        assert result["target"] == "found_it"
    
    @pytest.mark.performance
    def test_cache_efficiency_validation(self):
        """Test cache efficiency with repeated accesses."""
        resolver = ParameterResolver()
        
        test_strategy = {
            "parameters": {
                "shared_value": "cached_content"
            },
            "references": ["${parameters.shared_value}" for _ in range(100)]
        }
        
        import time
        start_time = time.time()
        result = resolver.resolve_parameters(test_strategy)
        end_time = time.time()
        
        # Should be fast due to caching
        assert end_time - start_time < 0.1
        assert all(ref == "cached_content" for ref in result["references"])


class TestParameterResolutionErrors:
    """Test error handling in parameter resolution."""
    
    def test_parameter_resolution_error_instantiation(self):
        """Test ParameterResolutionError instantiation."""
        error = ParameterResolutionError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_circular_reference_error_instantiation(self):
        """Test CircularReferenceError instantiation."""
        error = CircularReferenceError("Circular reference detected")
        assert str(error) == "Circular reference detected"
        assert isinstance(error, ParameterResolutionError)
    
    def test_circular_reference_error_inheritance(self):
        """Test CircularReferenceError inheritance."""
        error = CircularReferenceError("Test")
        assert isinstance(error, ParameterResolutionError)
        assert isinstance(error, Exception)
    
    def test_max_passes_circular_detection(self):
        """Test maximum passes circular reference detection."""
        resolver = ParameterResolver()
        
        # Create a strategy that would require more than max passes
        test_strategy = {
            "parameters": {
                "a": "${parameters.b}",
                "b": "${parameters.c}",
                "c": "${parameters.d}",
                "d": "${parameters.e}",
                "e": "${parameters.f}",
                "f": "${parameters.g}",
                "g": "${parameters.h}",
                "h": "${parameters.i}",
                "i": "${parameters.j}",
                "j": "${parameters.k}",
                "k": "${parameters.a}"  # Creates circular reference
            }
        }
        
        with pytest.raises(CircularReferenceError) as exc_info:
            resolver.resolve_parameters(test_strategy)
        
        assert "circular references detected" in str(exc_info.value).lower()


class TestParameterResolverInitialization:
    """Test ParameterResolver initialization."""
    
    def test_default_initialization(self):
        """Test default initialization."""
        resolver = ParameterResolver()
        assert resolver.base_dir == Path.cwd()
        assert resolver._resolution_cache == {}
        assert resolver._resolving == set()
    
    def test_custom_base_dir_initialization(self):
        """Test initialization with custom base directory."""
        test_dir = "/tmp/test_base"
        resolver = ParameterResolver(base_dir=test_dir)
        assert resolver.base_dir == Path(test_dir)
    
    def test_base_dir_path_conversion(self):
        """Test base directory path conversion."""
        resolver = ParameterResolver(base_dir="/tmp")
        assert isinstance(resolver.base_dir, Path)
        assert str(resolver.base_dir) == "/tmp"


class TestBuildResolutionContext:
    """Test _build_resolution_context method."""
    
    def test_build_context_with_all_sections(self):
        """Test building context with all sections."""
        resolver = ParameterResolver()
        strategy = {
            "parameters": {"param1": "value1"},
            "metadata": {"meta1": "metavalue1"}
        }
        
        with patch.dict(os.environ, {"ENV_VAR": "env_value"}):
            context = resolver._build_resolution_context(strategy)
        
        assert context["parameters"] == {"param1": "value1"}
        assert context["metadata"] == {"meta1": "metavalue1"}
        assert "ENV_VAR" in context["env"]
        assert context["env"]["ENV_VAR"] == "env_value"
    
    def test_build_context_missing_sections(self):
        """Test building context with missing sections."""
        resolver = ParameterResolver()
        strategy = {}
        
        context = resolver._build_resolution_context(strategy)
        
        assert context["parameters"] == {}
        assert context["metadata"] == {}
        assert isinstance(context["env"], dict)
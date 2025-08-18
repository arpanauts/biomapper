"""Tests for universal context handler standards component."""

import pytest
import threading
import time
from typing import Any

from src.core.standards.context_handler import UniversalContext


class TestUniversalContext:
    """Test UniversalContext functionality."""
    
    @pytest.fixture
    def sample_biological_data(self):
        """Create sample biological data for testing."""
        return {
            "datasets": {
                "arivale_proteins": ["P12345", "Q9Y6R4", "O00533"],
                "kg2c_proteins": ["P12345", "P54321", "Q1234"],
                "hmdb_metabolites": ["HMDB0000001", "HMDB0123456"]
            },
            "statistics": {
                "total_proteins": 6,
                "matched_proteins": 1,
                "match_rate": 0.167
            },
            "output_files": [
                "/tmp/results/protein_matches.csv",
                "/tmp/results/unmatched_proteins.txt"
            ],
            "current_identifiers": ["P12345", "Q9Y6R4"],
            "strategy_name": "protein_mapping",
            "strategy_version": "v1.0"
        }
    
    @pytest.fixture
    def dict_context(self, sample_biological_data):
        """Create dict-based context for testing."""
        return sample_biological_data.copy()
    
    @pytest.fixture
    def object_context(self, sample_biological_data):
        """Create object-based context for testing."""
        class ObjectContext:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        return ObjectContext(sample_biological_data)
    
    @pytest.fixture
    def adapter_context(self, sample_biological_data):
        """Create ContextAdapter-like context for testing."""
        class ContextAdapter:
            def __init__(self, data):
                self._data = data.copy()
            
            def get_action_data(self, key: str) -> Any:
                return self._data.get(key)
            
            def set_action_data(self, key: str, value: Any) -> None:
                self._data[key] = value
        
        return ContextAdapter(sample_biological_data)
    
    @pytest.fixture
    def dict_attr_context(self, sample_biological_data):
        """Create context with _dict attribute for testing."""
        class DictAttrContext:
            def __init__(self, data):
                self._dict = data.copy()
        
        return DictAttrContext(sample_biological_data)

    def test_dict_context_basic_functionality(self, dict_context):
        """Test basic functionality with dict context."""
        ctx = UniversalContext(dict_context)
        
        # Test getting values
        assert ctx.get("strategy_name") == "protein_mapping"
        assert ctx.get("strategy_version") == "v1.0"
        assert ctx.get("nonexistent", "default") == "default"
        
        # Test setting values
        ctx.set("new_field", "new_value")
        assert ctx.get("new_field") == "new_value"
        
        # Test has_key
        assert ctx.has_key("strategy_name") is True
        assert ctx.has_key("nonexistent") is False

    def test_object_context_basic_functionality(self, object_context):
        """Test basic functionality with object context."""
        ctx = UniversalContext(object_context)
        
        # Test getting values
        assert ctx.get("strategy_name") == "protein_mapping"
        assert ctx.get("strategy_version") == "v1.0"
        assert ctx.get("nonexistent", "default") == "default"
        
        # Test setting values
        ctx.set("new_field", "new_value")
        assert ctx.get("new_field") == "new_value"
        
        # Test has_key
        assert ctx.has_key("strategy_name") is True
        assert ctx.has_key("nonexistent") is False

    def test_adapter_context_basic_functionality(self, adapter_context):
        """Test basic functionality with ContextAdapter context."""
        ctx = UniversalContext(adapter_context)
        
        # Test getting values
        assert ctx.get("strategy_name") == "protein_mapping"
        assert ctx.get("strategy_version") == "v1.0"
        assert ctx.get("nonexistent", "default") == "default"
        
        # Test setting values
        ctx.set("new_field", "new_value")
        assert ctx.get("new_field") == "new_value"
        
        # Test has_key
        assert ctx.has_key("strategy_name") is True
        assert ctx.has_key("nonexistent") is False

    def test_dict_attr_context_basic_functionality(self, dict_attr_context):
        """Test basic functionality with _dict attribute context."""
        ctx = UniversalContext(dict_attr_context)
        
        # Test getting values
        assert ctx.get("strategy_name") == "protein_mapping"
        assert ctx.get("strategy_version") == "v1.0"
        assert ctx.get("nonexistent", "default") == "default"
        
        # Test setting values
        ctx.set("new_field", "new_value")
        assert ctx.get("new_field") == "new_value"
        
        # Test has_key
        assert ctx.has_key("strategy_name") is True
        assert ctx.has_key("nonexistent") is False

    def test_none_context_functionality(self):
        """Test functionality with None context (should default to empty dict)."""
        ctx = UniversalContext(None)
        
        # Should behave like empty dict
        assert ctx.get("nonexistent", "default") == "default"
        
        # Should be able to set values
        ctx.set("new_field", "value")
        assert ctx.get("new_field") == "value"

    def test_get_datasets_functionality(self, dict_context):
        """Test get_datasets method."""
        ctx = UniversalContext(dict_context)
        
        datasets = ctx.get_datasets()
        assert isinstance(datasets, dict)
        assert "arivale_proteins" in datasets
        assert "kg2c_proteins" in datasets
        assert "hmdb_metabolites" in datasets
        
        # Test with missing datasets
        ctx.set("datasets", None)
        datasets = ctx.get_datasets()
        assert datasets == {}

    def test_get_statistics_functionality(self, dict_context):
        """Test get_statistics method."""
        ctx = UniversalContext(dict_context)
        
        statistics = ctx.get_statistics()
        assert isinstance(statistics, dict)
        assert statistics["total_proteins"] == 6
        assert statistics["matched_proteins"] == 1
        assert statistics["match_rate"] == 0.167
        
        # Test with missing statistics
        ctx.set("statistics", "not_a_dict")
        statistics = ctx.get_statistics()
        assert statistics == {}

    def test_get_output_files_functionality(self, dict_context):
        """Test get_output_files method."""
        ctx = UniversalContext(dict_context)
        
        output_files = ctx.get_output_files()
        assert isinstance(output_files, list)
        assert len(output_files) == 2
        assert "/tmp/results/protein_matches.csv" in output_files
        
        # Test with missing output_files
        ctx.set("output_files", "not_a_list")
        output_files = ctx.get_output_files()
        assert output_files == []

    def test_get_current_identifiers_functionality(self, dict_context):
        """Test get_current_identifiers method."""
        ctx = UniversalContext(dict_context)
        
        identifiers = ctx.get_current_identifiers()
        assert identifiers == ["P12345", "Q9Y6R4"]
        
        # Test with missing current_identifiers
        ctx.set("current_identifiers", None)
        identifiers = ctx.get_current_identifiers()
        assert identifiers is None

    def test_wrap_static_method(self, dict_context, object_context):
        """Test static wrap method."""
        # Test wrapping dict context
        wrapped_dict = UniversalContext.wrap(dict_context)
        assert isinstance(wrapped_dict, UniversalContext)
        assert wrapped_dict.get("strategy_name") == "protein_mapping"
        
        # Test wrapping object context
        wrapped_obj = UniversalContext.wrap(object_context)
        assert isinstance(wrapped_obj, UniversalContext)
        assert wrapped_obj.get("strategy_name") == "protein_mapping"
        
        # Test wrapping already wrapped context
        already_wrapped = UniversalContext.wrap(wrapped_dict)
        assert already_wrapped is wrapped_dict  # Should return same instance
        
        # Test wrapping None
        wrapped_none = UniversalContext.wrap(None)
        assert isinstance(wrapped_none, UniversalContext)

    def test_unwrap_functionality(self, dict_context):
        """Test unwrap method."""
        ctx = UniversalContext(dict_context)
        unwrapped = ctx.unwrap()
        assert unwrapped is dict_context

    def test_to_dict_functionality(self, dict_context, object_context, adapter_context):
        """Test to_dict method with different context types."""
        # Test with dict context
        ctx_dict = UniversalContext(dict_context)
        result_dict = ctx_dict.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["strategy_name"] == "protein_mapping"
        assert result_dict is not dict_context  # Should be a copy
        
        # Test with object context
        ctx_obj = UniversalContext(object_context)
        result_obj = ctx_obj.to_dict()
        assert isinstance(result_obj, dict)
        assert result_obj["strategy_name"] == "protein_mapping"
        
        # Test with adapter context
        ctx_adapter = UniversalContext(adapter_context)
        result_adapter = ctx_adapter.to_dict()
        assert isinstance(result_adapter, dict)
        assert "datasets" in result_adapter

    def test_context_type_detection(self, dict_context, object_context, adapter_context, dict_attr_context):
        """Test context type detection and caching."""
        # Test dict context detection
        ctx_dict = UniversalContext(dict_context)
        assert ctx_dict._is_dict is True
        assert ctx_dict._is_object is False
        assert ctx_dict._is_adapter is False
        
        # Test object context detection
        ctx_obj = UniversalContext(object_context)
        assert ctx_obj._is_dict is False
        assert ctx_obj._is_object is True
        assert ctx_obj._is_adapter is False
        
        # Test adapter context detection
        ctx_adapter = UniversalContext(adapter_context)
        assert ctx_adapter._is_dict is False
        assert ctx_adapter._is_object is False
        assert ctx_adapter._is_adapter is True
        
        # Test dict attr context detection
        ctx_dict_attr = UniversalContext(dict_attr_context)
        assert ctx_dict_attr._is_dict is False
        assert ctx_dict_attr._has_dict_attr is True

    def test_fallback_handling(self):
        """Test fallback handling for unusual context types."""
        # Create unusual context that doesn't fit standard patterns
        class UnusualContext:
            def custom_method(self):
                return "custom"
        
        unusual = UnusualContext()
        ctx = UniversalContext(unusual)
        
        # Should handle gracefully
        assert ctx.get("nonexistent", "default") == "default"
        
        # Should be able to set values (using fallback)
        ctx.set("test_field", "test_value")
        # May not be retrievable depending on fallback mechanism, but shouldn't crash

    def test_error_handling_edge_cases(self):
        """Test error handling with edge cases."""
        # Test with object that raises errors on attribute access
        class ErrorProneContext:
            def __getattr__(self, name):
                if name == "problematic_attr":
                    raise AttributeError("Simulated error")
                return "safe_value"
        
        error_context = ErrorProneContext()
        ctx = UniversalContext(error_context)
        
        # Should handle errors gracefully
        assert ctx.get("problematic_attr", "default") == "default"
        assert ctx.get("safe_attr", "default") == "safe_value"

    def test_context_handler_performance(self, dict_context):
        """Test UniversalContext performance with large datasets."""
        # Create large biological dataset
        large_context = dict_context.copy()
        large_context["large_protein_dataset"] = [f"P{i:05d}" for i in range(10000)]
        large_context["large_metabolite_dataset"] = [f"HMDB{i:07d}" for i in range(5000)]
        
        ctx = UniversalContext(large_context)
        
        start_time = time.time()
        
        # Test multiple operations
        for i in range(1000):
            ctx.get("strategy_name")
            ctx.get("large_protein_dataset")
            ctx.has_key("strategy_name")
        
        execution_time = time.time() - start_time
        
        # Performance assertion
        assert execution_time < 0.1  # Should be very fast

    def test_context_handler_thread_safety(self, dict_context):
        """Test UniversalContext thread safety."""
        ctx = UniversalContext(dict_context)
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                # Each thread performs multiple operations
                for i in range(100):
                    value = ctx.get("strategy_name")
                    ctx.set(f"thread_{thread_id}_field_{i}", f"value_{i}")
                    has_key = ctx.has_key("strategy_name")
                    
                results.append({
                    "thread_id": thread_id,
                    "value": value,
                    "has_key": has_key
                })
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify all threads got consistent results
        for result in results:
            assert result["value"] == "protein_mapping"
            assert result["has_key"] is True


class TestPerformanceUniversalContext:
    """Performance tests for UniversalContext."""
    
    @pytest.mark.performance
    def test_large_context_performance(self):
        """Test performance with large context data."""
        # Create very large biological context
        large_datasets = {}
        for dataset_type in ["proteins", "metabolites", "genes", "pathways"]:
            for source in ["arivale", "kg2c", "hmdb", "kegg", "reactome"]:
                key = f"{source}_{dataset_type}"
                if dataset_type == "proteins":
                    large_datasets[key] = [f"P{i:05d}" for i in range(10000)]
                elif dataset_type == "metabolites":
                    large_datasets[key] = [f"HMDB{i:07d}" for i in range(5000)]
                else:
                    large_datasets[key] = [f"{dataset_type.upper()}{i:06d}" for i in range(2000)]
        
        large_context = {
            "datasets": large_datasets,
            "statistics": {f"stat_{i}": i * 0.1 for i in range(1000)},
            "output_files": [f"/tmp/file_{i}.csv" for i in range(100)],
            "metadata": {f"meta_{i}": f"value_{i}" for i in range(500)}
        }
        
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        ctx = UniversalContext(large_context)
        
        # Perform many operations
        for i in range(1000):
            datasets = ctx.get_datasets()
            stats = ctx.get_statistics()
            files = ctx.get_output_files()
            ctx.has_key("datasets")
        
        memory_after = self._get_memory_usage()
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 2.0  # Should complete in reasonable time
        assert (memory_after - memory_before) < 200 * 1024 * 1024  # < 200MB memory increase

    def _get_memory_usage(self):
        """Get current memory usage."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0  # Skip memory check if psutil not available


class TestBiologicalContextPatterns:
    """Test with realistic biological context patterns."""
    
    @pytest.fixture
    def protein_mapping_context(self):
        """Realistic protein mapping context."""
        return {
            "datasets": {
                "arivale_proteins": {
                    "data": ["P12345", "Q9Y6R4", "O00533", "Q6EMK4"],
                    "metadata": {"source": "Arivale", "total_count": 4}
                },
                "kg2c_proteins": {
                    "data": ["P12345", "P54321", "Q1234"],
                    "metadata": {"source": "KG2c", "total_count": 3}
                }
            },
            "current_identifiers": ["P12345", "Q9Y6R4"],
            "statistics": {
                "total_source": 4,
                "total_target": 3,
                "matched": 1,
                "source_only": 3,
                "target_only": 2,
                "match_rate": 0.25
            },
            "mapping_results": {
                "P12345": {"target": "P12345", "confidence": 1.0},
                "Q9Y6R4": {"target": None, "confidence": 0.0},
                "O00533": {"target": None, "confidence": 0.0},
                "Q6EMK4": {"target": None, "confidence": 0.0, "issue": "known_edge_case"}
            },
            "output_files": [
                "/tmp/biomapper_results/protein_mapping_results.csv",
                "/tmp/biomapper_results/unmatched_proteins.txt",
                "/tmp/biomapper_results/mapping_statistics.json"
            ],
            "strategy_name": "arivale_to_kg2c_protein_mapping",
            "strategy_version": "v2.1",
            "execution_metadata": {
                "start_time": "2024-01-15T10:30:00Z",
                "duration_seconds": 45.2,
                "memory_usage_mb": 128
            }
        }
    
    @pytest.fixture
    def metabolite_analysis_context(self):
        """Realistic metabolite analysis context."""
        return {
            "datasets": {
                "hmdb_metabolites": {
                    "data": ["HMDB0000001", "HMDB0000002", "HMDB0123456"],
                    "metadata": {"source": "HMDB", "version": "5.0"}
                },
                "user_metabolites": {
                    "data": ["glucose", "lactate", "pyruvate"],
                    "metadata": {"source": "user_input", "format": "common_names"}
                }
            },
            "enrichment_results": {
                "pathway_analysis": {
                    "glycolysis": {"p_value": 0.001, "metabolites": 3},
                    "tca_cycle": {"p_value": 0.05, "metabolites": 1}
                },
                "chemical_classification": {
                    "carbohydrates": ["HMDB0000001"],
                    "organic_acids": ["HMDB0000002"]
                }
            },
            "semantic_matches": {
                "glucose": {"hmdb_id": "HMDB0000122", "confidence": 0.98},
                "lactate": {"hmdb_id": "HMDB0000190", "confidence": 0.95},
                "pyruvate": {"hmdb_id": "HMDB0000243", "confidence": 0.92}
            },
            "statistics": {
                "total_input_metabolites": 3,
                "successful_matches": 3,
                "match_rate": 1.0,
                "average_confidence": 0.95
            }
        }

    def test_protein_mapping_context_handling(self, protein_mapping_context):
        """Test handling of realistic protein mapping context."""
        ctx = UniversalContext(protein_mapping_context)
        
        # Test accessing nested biological data
        datasets = ctx.get_datasets()
        assert "arivale_proteins" in datasets
        assert "kg2c_proteins" in datasets
        
        arivale_data = datasets["arivale_proteins"]["data"]
        assert "P12345" in arivale_data
        assert "Q6EMK4" in arivale_data  # Known edge case
        
        # Test mapping results access
        mapping_results = ctx.get("mapping_results")
        assert mapping_results["P12345"]["confidence"] == 1.0
        assert mapping_results["Q6EMK4"]["issue"] == "known_edge_case"
        
        # Test statistics access
        stats = ctx.get_statistics()
        assert stats["match_rate"] == 0.25
        assert stats["source_only"] == 3
        
        # Test output files
        output_files = ctx.get_output_files()
        assert len(output_files) == 3
        assert any("protein_mapping_results.csv" in f for f in output_files)

    def test_metabolite_analysis_context_handling(self, metabolite_analysis_context):
        """Test handling of realistic metabolite analysis context."""
        ctx = UniversalContext(metabolite_analysis_context)
        
        # Test accessing metabolite datasets
        datasets = ctx.get_datasets()
        assert "hmdb_metabolites" in datasets
        assert "user_metabolites" in datasets
        
        hmdb_data = datasets["hmdb_metabolites"]["data"]
        assert "HMDB0000001" in hmdb_data
        
        # Test enrichment results
        enrichment = ctx.get("enrichment_results")
        assert "pathway_analysis" in enrichment
        assert enrichment["pathway_analysis"]["glycolysis"]["p_value"] == 0.001
        
        # Test semantic matching
        semantic_matches = ctx.get("semantic_matches")
        assert semantic_matches["glucose"]["confidence"] == 0.98
        assert semantic_matches["lactate"]["hmdb_id"] == "HMDB0000190"
        
        # Test statistics
        stats = ctx.get_statistics()
        assert stats["match_rate"] == 1.0
        assert stats["average_confidence"] == 0.95

    def test_context_modification_with_biological_data(self, protein_mapping_context):
        """Test context modification with biological data."""
        ctx = UniversalContext(protein_mapping_context)
        
        # Add new biological dataset
        new_dataset = {
            "data": ["ENSP00000269305", "ENSP00000350283"],
            "metadata": {"source": "Ensembl", "type": "protein_ids"}
        }
        
        datasets = ctx.get_datasets()
        datasets["ensembl_proteins"] = new_dataset
        ctx.set("datasets", datasets)
        
        # Verify addition
        updated_datasets = ctx.get_datasets()
        assert "ensembl_proteins" in updated_datasets
        assert updated_datasets["ensembl_proteins"]["metadata"]["source"] == "Ensembl"
        
        # Update statistics
        stats = ctx.get_statistics()
        stats["ensembl_count"] = len(new_dataset["data"])
        ctx.set("statistics", stats)
        
        updated_stats = ctx.get_statistics()
        assert updated_stats["ensembl_count"] == 2

    def test_edge_case_identifier_handling(self, protein_mapping_context):
        """Test handling of edge case identifiers in context."""
        ctx = UniversalContext(protein_mapping_context)
        
        # Access edge case identifier (Q6EMK4)
        mapping_results = ctx.get("mapping_results")
        q6emk4_result = mapping_results.get("Q6EMK4")
        
        assert q6emk4_result is not None
        assert q6emk4_result["target"] is None
        assert q6emk4_result["confidence"] == 0.0
        assert q6emk4_result["issue"] == "known_edge_case"
        
        # Add additional edge case information
        edge_cases = ctx.get("edge_cases", {})
        edge_cases["Q6EMK4"] = {
            "description": "Q6EMK4 shows as source_only despite being in KG2c xrefs",
            "workaround": "Manual mapping to NCBIGene:114990 (OTUD5)",
            "investigation_status": "open"
        }
        ctx.set("edge_cases", edge_cases)
        
        # Verify edge case information
        updated_edge_cases = ctx.get("edge_cases")
        assert "Q6EMK4" in updated_edge_cases
        assert "workaround" in updated_edge_cases["Q6EMK4"]

    def test_multi_omics_context_integration(self):
        """Test context handling with multi-omics data integration."""
        multi_omics_context = {
            "datasets": {
                "proteomics": {
                    "arivale": ["P12345", "Q9Y6R4"],
                    "metadata": {"platform": "mass_spec", "samples": 1000}
                },
                "metabolomics": {
                    "hmdb": ["HMDB0000001", "HMDB0000002"],
                    "metadata": {"platform": "nmr", "samples": 800}
                },
                "genomics": {
                    "ensembl": ["ENSG00000141510", "ENSG00000012048"],
                    "metadata": {"assembly": "GRCh38", "samples": 1200}
                }
            },
            "pathway_integration": {
                "glycolysis": {
                    "proteins": ["P12345"],
                    "metabolites": ["HMDB0000001"],
                    "genes": ["ENSG00000141510"]
                }
            },
            "correlation_analysis": {
                "protein_metabolite": {
                    "P12345_HMDB0000001": {"correlation": 0.75, "p_value": 0.001}
                }
            }
        }
        
        ctx = UniversalContext(multi_omics_context)
        
        # Test accessing multi-omics datasets
        datasets = ctx.get_datasets()
        assert len(datasets) == 3
        assert "proteomics" in datasets
        assert "metabolomics" in datasets
        assert "genomics" in datasets
        
        # Test pathway integration
        pathways = ctx.get("pathway_integration")
        glycolysis = pathways["glycolysis"]
        assert "P12345" in glycolysis["proteins"]
        assert "HMDB0000001" in glycolysis["metabolites"]
        
        # Test correlation data
        correlations = ctx.get("correlation_analysis")
        protein_metabolite_corr = correlations["protein_metabolite"]
        assert protein_metabolite_corr["P12345_HMDB0000001"]["correlation"] == 0.75
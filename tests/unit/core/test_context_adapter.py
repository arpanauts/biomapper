"""Tests for context_adapter.py."""

import pytest
from unittest.mock import Mock, patch

from core.context_adapter import (
    StrategyExecutionContextAdapter,
    adapt_context
)


class TestStrategyExecutionContextAdapter:
    """Test StrategyExecutionContextAdapter functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock StrategyExecutionContext."""
        context = Mock()
        context.initial_identifier = "P12345"
        context.current_identifier = "Q9Y6R4"
        context.ontology_type = "protein"
        context.step_results = []
        context.provenance = []
        context.custom_action_data = {
            "custom_key": "custom_value",
            "biological_data": {"uniprot_ids": ["P12345", "Q9Y6R4"]}
        }
        
        # Mock methods
        context.get_action_data = Mock(return_value=None)
        context.set_action_data = Mock()
        
        return context
    
    @pytest.fixture
    def adapter(self, mock_context):
        """Create StrategyExecutionContextAdapter instance."""
        return StrategyExecutionContextAdapter(mock_context)
    
    def test_initialization_with_context_attributes(self, adapter, mock_context):
        """Test adapter initialization with context attributes."""
        assert adapter._context == mock_context
        assert adapter["initial_identifier"] == "P12345"
        assert adapter["current_identifier"] == "Q9Y6R4"
        assert adapter["ontology_type"] == "protein"
        assert adapter["step_results"] == []
        assert adapter["provenance"] == []
    
    def test_initialization_standard_dict_keys(self, adapter):
        """Test initialization of standard dict keys."""
        assert "datasets" in adapter._dict_cache
        assert "statistics" in adapter._dict_cache
        assert "output_files" in adapter._dict_cache
        assert "current_identifiers" in adapter._dict_cache
        
        assert adapter._dict_cache["datasets"] == {}
        assert adapter._dict_cache["statistics"] == {}
        assert adapter._dict_cache["output_files"] == {}
        assert adapter._dict_cache["current_identifiers"] == []
    
    def test_initialization_custom_action_data(self, adapter):
        """Test initialization with custom action data."""
        assert adapter["custom_key"] == "custom_value"
        assert adapter["biological_data"] == {"uniprot_ids": ["P12345", "Q9Y6R4"]}
    
    def test_getitem_from_cache(self, adapter):
        """Test dict-like getitem access from cache."""
        adapter._dict_cache["test_key"] = "test_value"
        
        assert adapter["test_key"] == "test_value"
    
    def test_getitem_from_context_action_data(self, adapter, mock_context):
        """Test getitem access from context's action data."""
        mock_context.get_action_data.return_value = "action_data_value"
        
        result = adapter["action_key"]
        
        mock_context.get_action_data.assert_called_once_with("action_key")
        assert result == "action_data_value"
    
    def test_getitem_from_context_attribute(self, adapter, mock_context):
        """Test getitem access from context attribute."""
        mock_context.test_attribute = "attribute_value"
        mock_context.get_action_data.return_value = None
        
        result = adapter["test_attribute"]
        
        assert result == "attribute_value"
    
    def test_getitem_key_error(self, adapter, mock_context):
        """Test getitem raises KeyError for missing keys."""
        mock_context.get_action_data.return_value = None
        
        # Mock hasattr to return False for nonexistent key
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            
            with pytest.raises(KeyError) as exc_info:
                adapter["nonexistent_key"]
            
            assert "Key 'nonexistent_key' not found in context" in str(exc_info.value)
    
    def test_setitem_updates_cache_and_context(self, adapter, mock_context):
        """Test dict-like setitem access."""
        adapter["new_key"] = "new_value"
        
        assert adapter._dict_cache["new_key"] == "new_value"
        mock_context.set_action_data.assert_called_once_with("new_key", "new_value")
    
    def test_setitem_without_context_method(self, adapter, mock_context):
        """Test setitem when context doesn't have set_action_data."""
        delattr(mock_context, "set_action_data")
        
        adapter["test_key"] = "test_value"
        
        assert adapter._dict_cache["test_key"] == "test_value"
    
    def test_contains_in_cache(self, adapter):
        """Test dict-like contains check in cache."""
        adapter._dict_cache["cached_key"] = "value"
        
        assert "cached_key" in adapter
    
    def test_contains_in_context_action_data(self, adapter, mock_context):
        """Test contains check in context action data."""
        mock_context.get_action_data.return_value = "some_value"
        
        assert "action_key" in adapter
        mock_context.get_action_data.assert_called_with("action_key")
    
    def test_contains_as_context_attribute(self, adapter, mock_context):
        """Test contains check as context attribute."""
        mock_context.attribute_key = "attribute_value"
        mock_context.get_action_data.return_value = None
        
        assert "attribute_key" in adapter
    
    def test_contains_not_found(self, adapter, mock_context):
        """Test contains returns False for missing keys."""
        mock_context.get_action_data.return_value = None
        
        # Mock hasattr to prevent mock attributes from being detected
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            assert "nonexistent_key" not in adapter
    
    def test_get_method_with_existing_key(self, adapter):
        """Test dict-like get method with existing key."""
        adapter._dict_cache["existing"] = "value"
        
        result = adapter.get("existing", "default")
        
        assert result == "value"
    
    def test_get_method_with_missing_key(self, adapter, mock_context):
        """Test get method with missing key returns default."""
        mock_context.get_action_data.return_value = None
        
        # Mock hasattr to return False for the missing key
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            result = adapter.get("missing", "default_value")
        
        assert result == "default_value"
    
    def test_get_method_no_default(self, adapter, mock_context):
        """Test get method without default returns None."""
        mock_context.get_action_data.return_value = None
        
        # Mock hasattr to return False for the missing key
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            result = adapter.get("missing")
        
        assert result is None
    
    def test_setdefault_existing_key(self, adapter):
        """Test setdefault with existing key."""
        adapter._dict_cache["existing"] = "existing_value"
        
        result = adapter.setdefault("existing", "default_value")
        
        assert result == "existing_value"
        assert adapter._dict_cache["existing"] == "existing_value"
    
    def test_setdefault_missing_key(self, adapter, mock_context):
        """Test setdefault with missing key."""
        mock_context.get_action_data.return_value = None
        
        # Mock hasattr to return False for the missing key
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            result = adapter.setdefault("missing", "default_value")
        
        assert result == "default_value"
        assert adapter._dict_cache["missing"] == "default_value"
    
    def test_update_method(self, adapter, mock_context):
        """Test dict-like update method."""
        update_data = {
            "key1": "value1",
            "key2": "value2",
            "biological_id": "HMDB0000123"
        }
        
        adapter.update(update_data)
        
        for key, value in update_data.items():
            assert adapter[key] == value
    
    def test_keys_method(self, adapter, mock_context):
        """Test keys method returns all available keys."""
        adapter._dict_cache["cache_key"] = "cache_value"
        
        # Configure mock context attributes properly
        mock_context.configure_mock(**{"context_attr": "context_value"})
        mock_context.configure_mock(**{"custom_action_data": {"action_key": "action_value"}})
        
        keys = adapter.keys()
        
        assert "cache_key" in keys
        assert "context_attr" in keys
        assert "action_key" in keys
        assert "initial_identifier" in keys  # From initialization
    
    def test_values_method(self, adapter):
        """Test values method returns all values."""
        adapter._dict_cache["test_key"] = "test_value"
        
        values = adapter.values()
        
        assert "test_value" in values
        assert "P12345" in values  # initial_identifier
    
    def test_items_method(self, adapter):
        """Test items method returns all key-value pairs."""
        adapter._dict_cache["test_key"] = "test_value"
        
        items = list(adapter.items())
        
        assert ("test_key", "test_value") in items
        assert ("initial_identifier", "P12345") in items
    
    def test_set_action_data_proxy(self, adapter, mock_context):
        """Test set_action_data proxy method."""
        adapter.set_action_data("proxy_key", "proxy_value")
        
        mock_context.set_action_data.assert_called_once_with("proxy_key", "proxy_value")
        assert adapter._dict_cache["proxy_key"] == "proxy_value"
    
    def test_set_action_data_without_context_method(self, adapter, mock_context):
        """Test set_action_data when context doesn't have the method."""
        delattr(mock_context, "set_action_data")
        
        adapter.set_action_data("test_key", "test_value")
        
        assert adapter._dict_cache["test_key"] == "test_value"
    
    def test_get_action_data_proxy(self, adapter, mock_context):
        """Test get_action_data proxy method."""
        mock_context.get_action_data.return_value = "retrieved_value"
        
        result = adapter.get_action_data("data_key", "default")
        
        mock_context.get_action_data.assert_called_once_with("data_key", "default")
        assert result == "retrieved_value"
    
    def test_get_action_data_fallback_to_cache(self, adapter, mock_context):
        """Test get_action_data fallback to cache."""
        delattr(mock_context, "get_action_data")
        adapter._dict_cache["cache_key"] = "cache_value"
        
        result = adapter.get_action_data("cache_key", "default")
        
        assert result == "cache_value"
    
    def test_custom_action_data_property(self, adapter, mock_context):
        """Test custom_action_data property proxy."""
        expected_data = {"custom": "data"}
        mock_context.custom_action_data = expected_data
        
        result = adapter.custom_action_data
        
        assert result == expected_data
    
    def test_custom_action_data_property_missing_attribute(self, adapter, mock_context):
        """Test custom_action_data property when context doesn't have it."""
        delattr(mock_context, "custom_action_data")
        
        result = adapter.custom_action_data
        
        assert result == {}
    
    def test_repr_method(self, adapter):
        """Test string representation."""
        repr_str = repr(adapter)
        
        assert "StrategyExecutionContextAdapter" in repr_str
        assert "keys=" in repr_str
    
    def test_biological_data_patterns(self, adapter):
        """Test with realistic biological data patterns."""
        biological_data = {
            "uniprot_ids": ["P12345", "Q9Y6R4", "O15552"],
            "hmdb_ids": ["HMDB0000001", "HMDB0000123", "HMDB0006456"],
            "ensembl_ids": ["ENSP00000000233", "ENSP00000000412"],
            "gene_symbols": ["TP53", "BRCA1", "EGFR"],
            "loinc_codes": ["33747-0", "718-7"]
        }
        
        adapter.update(biological_data)
        
        assert adapter["uniprot_ids"] == ["P12345", "Q9Y6R4", "O15552"]
        assert adapter["hmdb_ids"] == ["HMDB0000001", "HMDB0000123", "HMDB0006456"]
        assert adapter["ensembl_ids"] == ["ENSP00000000233", "ENSP00000000412"]
        assert adapter["gene_symbols"] == ["TP53", "BRCA1", "EGFR"]
        assert adapter["loinc_codes"] == ["33747-0", "718-7"]
    
    def test_nested_context_access(self, adapter):
        """Test nested context access patterns."""
        nested_data = {
            "mapping_results": {
                "proteins": {
                    "matched": ["P12345", "Q9Y6R4"],
                    "unmatched": ["O15552"]
                },
                "metabolites": {
                    "matched": ["HMDB0000001"],
                    "unmatched": ["HMDB0000123"]
                }
            }
        }
        
        adapter.update(nested_data)
        
        assert adapter["mapping_results"]["proteins"]["matched"] == ["P12345", "Q9Y6R4"]
        assert adapter["mapping_results"]["metabolites"]["unmatched"] == ["HMDB0000123"]
    
    def test_context_modification_operations(self, adapter, mock_context):
        """Test context modification operations."""
        # Test adding new datasets
        adapter["datasets"]["protein_data"] = {"P12345": {"name": "Tumor protein p53"}}
        adapter["datasets"]["metabolite_data"] = {"HMDB0000001": {"name": "1-Methylhistidine"}}
        
        # Test updating statistics
        adapter["statistics"]["total_matches"] = 42
        adapter["statistics"]["match_rate"] = 0.85
        
        # Test tracking output files
        adapter["output_files"]["results"] = "/tmp/results.tsv"
        adapter["output_files"]["report"] = "/tmp/report.html"
        
        assert len(adapter["datasets"]) == 2
        assert adapter["statistics"]["total_matches"] == 42
        assert adapter["output_files"]["results"] == "/tmp/results.tsv"
    
    def test_error_handling_invalid_contexts(self, mock_context):
        """Test error handling for invalid contexts."""
        # Context with no attributes should still work
        minimal_context = Mock()
        minimal_context.__dict__ = {}
        
        adapter = StrategyExecutionContextAdapter(minimal_context)
        
        # Should still have standard dict keys
        assert "datasets" in adapter._dict_cache
        assert "statistics" in adapter._dict_cache


class TestAdaptContextFunction:
    """Test adapt_context function."""
    
    def test_adapt_dict_context(self):
        """Test adapting a dict context returns as-is."""
        dict_context = {
            "datasets": {"test": "data"},
            "statistics": {"count": 5}
        }
        
        result = adapt_context(dict_context)
        
        assert result is dict_context  # Should return the same object
        assert isinstance(result, dict)
    
    def test_adapt_strategy_execution_context(self):
        """Test adapting StrategyExecutionContext."""
        # Create a mock that will pass isinstance check
        from core.models.execution_context import StrategyExecutionContext
        
        # Create a real instance we can test with
        real_context = StrategyExecutionContext(
            initial_identifier="test", 
            current_identifier="test",
            ontology_type="protein"
        )
        
        result = adapt_context(real_context)
        
        assert isinstance(result, StrategyExecutionContextAdapter)
    
    def test_adapt_other_context_types(self):
        """Test adapting other context types."""
        custom_context = Mock()
        custom_context.__class__.__name__ = "CustomContext"
        custom_context.custom_action_data = {"test_key": "test_value"}
        
        result = adapt_context(custom_context)
        
        assert isinstance(result, StrategyExecutionContextAdapter)
    
    def test_adapt_context_with_biological_data(self):
        """Test adapting context with biological data patterns."""
        biological_context = {
            "current_identifiers": ["P12345", "Q9Y6R4"],
            "datasets": {
                "uniprot_mapping": {
                    "P12345": {"gene_name": "TP53"},
                    "Q9Y6R4": {"gene_name": "BRCA1"}
                }
            },
            "statistics": {
                "total_proteins": 2,
                "mapping_success_rate": 1.0
            }
        }
        
        result = adapt_context(biological_context)
        
        assert result is biological_context
        assert result["current_identifiers"] == ["P12345", "Q9Y6R4"]
        assert result["datasets"]["uniprot_mapping"]["P12345"]["gene_name"] == "TP53"


class TestContextAdapterThreadSafety:
    """Test thread safety considerations."""
    
    def test_concurrent_access_patterns(self):
        """Test concurrent access patterns (basic thread safety)."""
        mock_context = Mock()
        mock_context.custom_action_data = {}
        mock_context.get_action_data = Mock(return_value=None)
        mock_context.set_action_data = Mock()
        
        adapter = StrategyExecutionContextAdapter(mock_context)
        
        # Simulate concurrent operations
        for i in range(100):
            adapter[f"key_{i}"] = f"value_{i}"
            assert adapter[f"key_{i}"] == f"value_{i}"
        
        # All keys should be present
        for i in range(100):
            assert f"key_{i}" in adapter
            assert adapter[f"key_{i}"] == f"value_{i}"
    
    def test_cache_consistency(self):
        """Test cache consistency during modifications."""
        mock_context = Mock()
        mock_context.custom_action_data = {"initial": "data"}
        mock_context.get_action_data = Mock(return_value=None)
        mock_context.set_action_data = Mock()
        
        adapter = StrategyExecutionContextAdapter(mock_context)
        
        # Initial state
        assert adapter["initial"] == "data"
        
        # Modify through different methods
        adapter["direct"] = "direct_value"
        adapter.set_action_data("action", "action_value")
        adapter.update({"update": "update_value"})
        
        # All should be accessible
        assert adapter["direct"] == "direct_value"
        assert adapter["action"] == "action_value"
        assert adapter["update"] == "update_value"
        assert adapter["initial"] == "data"


class TestContextAdapterEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_context(self):
        """Test with None context."""
        adapter = StrategyExecutionContextAdapter(None)
        
        # Should still work with minimal functionality
        adapter["test"] = "value"
        assert adapter["test"] == "value"
    
    def test_context_without_dict(self):
        """Test context without __dict__ attribute."""
        class MinimalContext:
            pass
        
        context = MinimalContext()
        adapter = StrategyExecutionContextAdapter(context)
        
        # Should still initialize properly
        assert "datasets" in adapter._dict_cache
    
    def test_context_with_properties(self):
        """Test context with properties instead of attributes."""
        class PropertyContext:
            @property
            def dynamic_property(self):
                return "dynamic_value"
        
        context = PropertyContext()
        adapter = StrategyExecutionContextAdapter(context)
        
        # Should handle properties
        assert adapter["dynamic_property"] == "dynamic_value"
    
    def test_large_data_handling(self):
        """Test handling of large datasets."""
        mock_context = Mock()
        mock_context.custom_action_data = {}
        mock_context.get_action_data = Mock(return_value=None)
        mock_context.set_action_data = Mock()
        
        adapter = StrategyExecutionContextAdapter(mock_context)
        
        # Large biological dataset
        large_dataset = {
            f"protein_{i}": f"P{str(i).zfill(5)}" 
            for i in range(10000)
        }
        
        adapter["large_proteins"] = large_dataset
        
        assert len(adapter["large_proteins"]) == 10000
        assert adapter["large_proteins"]["protein_0"] == "P00000"
        assert adapter["large_proteins"]["protein_9999"] == "P09999"
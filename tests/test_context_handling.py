"""Comprehensive tests for UniversalContext handling system."""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from biomapper.core.standards.context_handler import UniversalContext
from biomapper.core.standards.context_detector import (
    detect_context_type,
    get_context_accessor,
    is_dict_context,
    is_object_context,
    is_adapter_context,
    get_context_info,
)


class TestUniversalContext:
    """Test the UniversalContext wrapper."""

    def test_dict_context(self):
        """Test with dictionary context."""
        context_data = {
            "datasets": {"input": [{"id": 1}], "output": [{"id": 2}]},
            "statistics": {"count": 10, "success_rate": 0.95},
            "output_files": ["file1.txt", "file2.csv"],
            "current_identifiers": ["id1", "id2"],
        }
        
        ctx = UniversalContext(context_data)
        
        # Test get operations
        assert ctx.get("datasets") == context_data["datasets"]
        assert ctx.get("missing_key", "default") == "default"
        assert ctx.get("missing_key") is None
        
        # Test helper methods
        assert ctx.get_datasets() == context_data["datasets"]
        assert ctx.get_statistics() == context_data["statistics"]
        assert ctx.get_output_files() == context_data["output_files"]
        assert ctx.get_current_identifiers() == context_data["current_identifiers"]
        
        # Test set operations
        ctx.set("new_key", "new_value")
        assert ctx.get("new_key") == "new_value"
        
        # Test has_key
        assert ctx.has_key("datasets") is True
        assert ctx.has_key("missing_key") is False

    def test_object_context(self):
        """Test with object context."""
        class MockContext:
            def __init__(self):
                self.datasets = {"input": [{"id": 1}]}
                self.statistics = {"count": 5}
                self.output_files = []
                self.current_identifiers = None
        
        context_obj = MockContext()
        ctx = UniversalContext(context_obj)
        
        # Test get operations
        assert ctx.get("datasets") == {"input": [{"id": 1}]}
        assert ctx.get("statistics") == {"count": 5}
        assert ctx.get("missing_attr", "default") == "default"
        
        # Test helper methods
        assert ctx.get_datasets() == {"input": [{"id": 1}]}
        assert ctx.get_statistics() == {"count": 5}
        assert ctx.get_output_files() == []
        assert ctx.get_current_identifiers() is None
        
        # Test set operations
        ctx.set("new_attr", "new_value")
        assert hasattr(context_obj, "new_attr")
        assert context_obj.new_attr == "new_value"
        
        # Test has_key
        assert ctx.has_key("datasets") is True
        assert ctx.has_key("missing_attr") is False

    def test_adapter_context(self):
        """Test with ContextAdapter pattern."""
        class MockAdapter:
            def __init__(self):
                self._data = {
                    "datasets": {"test": [{"id": 1}]},
                    "statistics": {"total": 100},
                    "output_files": ["result.json"],
                }
            
            def get_action_data(self, key, default=None):
                return self._data.get(key, default)
            
            def set_action_data(self, key, value):
                self._data[key] = value
        
        adapter = MockAdapter()
        ctx = UniversalContext(adapter)
        
        # Test get operations
        assert ctx.get("datasets") == {"test": [{"id": 1}]}
        assert ctx.get("statistics") == {"total": 100}
        assert ctx.get("missing_key", "default") == "default"
        
        # Test helper methods
        assert ctx.get_datasets() == {"test": [{"id": 1}]}
        assert ctx.get_statistics() == {"total": 100}
        assert ctx.get_output_files() == ["result.json"]
        
        # Test set operations
        ctx.set("new_data", "new_value")
        assert adapter._data["new_data"] == "new_value"

    def test_object_with_dict_attr(self):
        """Test with object that has _dict attribute."""
        class MockContextWithDict:
            def __init__(self):
                self._dict = {
                    "datasets": {"data": [{"id": 1}]},
                    "statistics": {"processed": 50},
                    "output_files": [],
                }
        
        context_obj = MockContextWithDict()
        ctx = UniversalContext(context_obj)
        
        # Test get operations
        assert ctx.get("datasets") == {"data": [{"id": 1}]}
        assert ctx.get("statistics") == {"processed": 50}
        
        # Test helper methods
        assert ctx.get_datasets() == {"data": [{"id": 1}]}
        assert ctx.get_statistics() == {"processed": 50}
        assert ctx.get_output_files() == []
        
        # Test set operations
        ctx.set("new_key", "new_value")
        assert context_obj._dict["new_key"] == "new_value"

    def test_none_context(self):
        """Test with None context (should default to empty dict)."""
        ctx = UniversalContext(None)
        
        # Should provide empty defaults
        assert ctx.get_datasets() == {}
        assert ctx.get_statistics() == {}
        assert ctx.get_output_files() == []
        assert ctx.get_current_identifiers() is None
        
        # Should allow setting values
        ctx.set("test_key", "test_value")
        assert ctx.get("test_key") == "test_value"

    def test_wrap_factory_method(self):
        """Test the static wrap factory method."""
        # Test with dict
        dict_ctx = {"key": "value"}
        wrapped = UniversalContext.wrap(dict_ctx)
        assert isinstance(wrapped, UniversalContext)
        assert wrapped.get("key") == "value"
        
        # Test with already wrapped context
        double_wrapped = UniversalContext.wrap(wrapped)
        assert double_wrapped is wrapped  # Should return same instance
        
        # Test with None
        none_wrapped = UniversalContext.wrap(None)
        assert isinstance(none_wrapped, UniversalContext)
        assert none_wrapped.get_datasets() == {}

    def test_unwrap_method(self):
        """Test getting the underlying context."""
        original_context = {"test": "data"}
        ctx = UniversalContext(original_context)
        
        unwrapped = ctx.unwrap()
        assert unwrapped is original_context

    def test_to_dict_method(self):
        """Test converting context to dictionary format."""
        # Test with dict context
        dict_context = {"datasets": {"a": 1}, "statistics": {"b": 2}}
        ctx = UniversalContext(dict_context)
        result_dict = ctx.to_dict()
        assert result_dict == dict_context
        assert result_dict is not dict_context  # Should be a copy
        
        # Test with object context
        class MockObject:
            def __init__(self):
                self.datasets = {"a": 1}
                self.statistics = {"b": 2}
                self._private = "hidden"
        
        obj_context = MockObject()
        ctx = UniversalContext(obj_context)
        result_dict = ctx.to_dict()
        
        # Should include public attributes, exclude private ones
        assert "datasets" in result_dict
        assert "statistics" in result_dict
        assert "_private" not in result_dict

    def test_error_handling(self):
        """Test error handling for edge cases."""
        # Test with unsupported context type
        class UnsupportedContext:
            pass
        
        unsupported = UnsupportedContext()
        ctx = UniversalContext(unsupported)
        
        # Should handle gracefully with defaults
        assert ctx.get("any_key", "default") == "default"
        assert ctx.get_datasets() == {}
        
        # Should allow setting with fallback mechanism
        ctx.set("test_key", "test_value")
        # Should not raise an exception

    def test_performance_caching(self):
        """Test that context type detection is cached for performance."""
        context = {"test": "data"}
        ctx = UniversalContext(context)
        
        # Access the cached flags to ensure they're set
        assert ctx._is_dict is True
        assert ctx._is_object is False
        assert ctx._is_adapter is False
        
        # Multiple access should use cached values
        assert ctx.get("test") == "data"
        assert ctx.get("test") == "data"  # Second call uses cache


class TestContextDetector:
    """Test context type detection utilities."""

    def test_detect_dict_context(self):
        """Test detection of dictionary contexts."""
        context = {"key": "value"}
        assert detect_context_type(context) == "dict"
        assert is_dict_context(context) is True
        assert is_object_context(context) is False
        assert is_adapter_context(context) is False

    def test_detect_object_context(self):
        """Test detection of object contexts."""
        class MockObject:
            def __init__(self):
                self.attr = "value"
        
        context = MockObject()
        assert detect_context_type(context) == "object"
        assert is_dict_context(context) is False
        assert is_object_context(context) is True
        assert is_adapter_context(context) is False

    def test_detect_adapter_context(self):
        """Test detection of adapter contexts."""
        class MockAdapter:
            def get_action_data(self, key, default=None):
                return default
            
            def set_action_data(self, key, value):
                pass
        
        context = MockAdapter()
        assert detect_context_type(context) == "adapter"
        assert is_dict_context(context) is False
        assert is_object_context(context) is True  # Has __dict__
        assert is_adapter_context(context) is True

    def test_detect_object_with_dict(self):
        """Test detection of objects with _dict attribute."""
        class MockWithDict:
            def __init__(self):
                self._dict = {"key": "value"}
        
        context = MockWithDict()
        assert detect_context_type(context) == "object_with_dict"

    def test_detect_unknown_context(self):
        """Test detection of unknown context types."""
        assert detect_context_type(None) == "unknown"
        assert detect_context_type("string") == "unknown"
        assert detect_context_type(123) == "unknown"

    def test_get_context_accessor(self):
        """Test getting appropriate accessor for context types."""
        # Dict context
        dict_context = {"key": "value"}
        accessor = get_context_accessor(dict_context)
        assert accessor is not None
        assert accessor.get("key") == "value"
        
        # Object context
        class MockObject:
            def __init__(self):
                self.key = "value"
        
        obj_context = MockObject()
        accessor = get_context_accessor(obj_context)
        assert accessor is not None
        assert accessor.get("key") == "value"
        
        # Unknown context
        unknown_accessor = get_context_accessor("unknown")
        assert unknown_accessor is None

    def test_get_context_info(self):
        """Test getting detailed context information."""
        context = {"key": "value"}
        info = get_context_info(context)
        
        assert info["type"] == "dict"
        assert info["is_dict"] is True
        assert info["is_object"] is False
        assert info["is_adapter"] is False
        assert "key" in info["keys"]


class TestContextIntegration:
    """Test integration between different context handling components."""

    def test_universal_context_with_all_types(self):
        """Test UniversalContext works with all detected context types."""
        # Test all context types that detector can identify
        contexts = [
            # Dict context
            {"datasets": {"a": 1}, "statistics": {"b": 2}},
            
            # Object context
            type("MockObject", (), {
                "datasets": {"a": 1}, 
                "statistics": {"b": 2}
            })(),
            
            # Adapter context
            type("MockAdapter", (), {
                "get_action_data": lambda self, k, d=None: {"datasets": {"a": 1}}.get(k, d),
                "set_action_data": lambda self, k, v: None
            })(),
        ]
        
        for context in contexts:
            ctx = UniversalContext.wrap(context)
            
            # Should work with all context types
            datasets = ctx.get_datasets()
            assert isinstance(datasets, dict)
            
            # Should allow setting values
            ctx.set("test_integration", "success")
            
            # Type detection should work
            context_type = detect_context_type(context)
            assert context_type in ["dict", "object", "adapter"]

    def test_real_world_usage_patterns(self):
        """Test patterns commonly used in biomapper actions."""
        # Simulate a typical action context
        context = {
            "datasets": {
                "input": [{"id": "P12345", "name": "protein1"}],
                "reference": [{"id": "P12345", "description": "test protein"}]
            },
            "statistics": {
                "input_count": 1,
                "reference_count": 1,
                "matched_count": 0,
                "success_rate": 0.0
            },
            "output_files": [],
            "current_identifiers": ["P12345"],
            "strategy_name": "test_strategy",
            "strategy_version": "1.0.0"
        }
        
        ctx = UniversalContext.wrap(context)
        
        # Test typical action operations
        input_data = ctx.get_datasets()["input"]
        assert len(input_data) == 1
        assert input_data[0]["id"] == "P12345"
        
        # Update statistics
        stats = ctx.get_statistics()
        stats["matched_count"] = 1
        stats["success_rate"] = 1.0
        ctx.set("statistics", stats)
        
        # Add output file
        output_files = ctx.get_output_files()
        output_files.append("/tmp/results.tsv")
        ctx.set("output_files", output_files)
        
        # Verify changes
        assert ctx.get("statistics")["matched_count"] == 1
        assert "/tmp/results.tsv" in ctx.get("output_files")

    def test_error_scenarios(self):
        """Test handling of error scenarios."""
        # Empty context
        empty_ctx = UniversalContext.wrap({})
        assert empty_ctx.get_datasets() == {}
        assert empty_ctx.get_output_files() == []
        
        # Context with wrong data types
        wrong_types_ctx = UniversalContext.wrap({
            "datasets": "not_a_dict",
            "statistics": ["not", "a", "dict"],
            "output_files": "not_a_list"
        })
        
        # Should handle gracefully
        assert wrong_types_ctx.get_datasets() == {}  # Returns empty dict for non-dict
        assert wrong_types_ctx.get_statistics() == {}  # Returns empty dict for non-dict
        assert wrong_types_ctx.get_output_files() == []  # Returns empty list for non-list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
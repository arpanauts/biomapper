"""
Context adapter to bridge dict-based and StrategyExecutionContext-based actions.

This adapter allows actions expecting dict-like context to work with
StrategyExecutionContext and vice versa.
"""

from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class StrategyExecutionContextAdapter:
    """
    Adapter that makes StrategyExecutionContext behave like a dict for backward compatibility.
    
    This adapter wraps a StrategyExecutionContext and provides dict-like access
    while maintaining the context's methods and properties.
    """
    
    def __init__(self, execution_context: Any):
        """
        Initialize the adapter with a StrategyExecutionContext.
        
        Args:
            execution_context: The StrategyExecutionContext to wrap
        """
        self._context = execution_context
        self._dict_cache: Dict[str, Any] = {}
        
        # Initialize common dict keys from context
        self._initialize_dict_cache()
    
    def _initialize_dict_cache(self):
        """Initialize the dict cache with common keys from the context."""
        # Map context attributes to dict keys
        self._dict_cache["initial_identifier"] = getattr(self._context, "initial_identifier", "")
        self._dict_cache["current_identifier"] = getattr(self._context, "current_identifier", "")
        self._dict_cache["ontology_type"] = getattr(self._context, "ontology_type", "")
        self._dict_cache["step_results"] = getattr(self._context, "step_results", [])
        self._dict_cache["provenance"] = getattr(self._context, "provenance", [])
        
        # Initialize standard dict keys
        if not hasattr(self, "_datasets_initialized"):
            self._dict_cache["datasets"] = {}
            self._dict_cache["statistics"] = {}
            self._dict_cache["output_files"] = {}
            self._dict_cache["current_identifiers"] = []
            self._datasets_initialized = True
        
        # Copy custom action data
        if hasattr(self._context, "custom_action_data"):
            for key, value in self._context.custom_action_data.items():
                if key not in self._dict_cache:
                    self._dict_cache[key] = value
    
    def __getitem__(self, key: str) -> Any:
        """Dict-like getitem access."""
        # Check cache first
        if key in self._dict_cache:
            return self._dict_cache[key]
        
        # Try to get from context's custom_action_data
        if hasattr(self._context, "get_action_data"):
            value = self._context.get_action_data(key)
            if value is not None:
                return value
        
        # Try to get as attribute from context
        if hasattr(self._context, key):
            return getattr(self._context, key)
        
        # If key doesn't exist, raise KeyError like a dict would
        raise KeyError(f"Key '{key}' not found in context")
    
    def __setitem__(self, key: str, value: Any):
        """Dict-like setitem access."""
        # Update cache
        self._dict_cache[key] = value
        
        # Also update context's custom_action_data if possible
        if hasattr(self._context, "set_action_data"):
            self._context.set_action_data(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Dict-like contains check."""
        # Check cache
        if key in self._dict_cache:
            return True
        
        # Check context's custom_action_data
        if hasattr(self._context, "get_action_data"):
            if self._context.get_action_data(key) is not None:
                return True
        
        # Check as attribute
        return hasattr(self._context, key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def setdefault(self, key: str, default: Any = None) -> Any:
        """Dict-like setdefault method."""
        if key not in self:
            self[key] = default
        return self[key]
    
    def update(self, other: Dict[str, Any]):
        """Dict-like update method."""
        for key, value in other.items():
            self[key] = value
    
    def keys(self):
        """Return all available keys."""
        all_keys = set(self._dict_cache.keys())
        
        # Add context attributes
        if hasattr(self._context, "__dict__"):
            all_keys.update(self._context.__dict__.keys())
        
        # Add custom_action_data keys
        if hasattr(self._context, "custom_action_data"):
            all_keys.update(self._context.custom_action_data.keys())
        
        return all_keys
    
    def values(self):
        """Return all values."""
        return [self[key] for key in self.keys()]
    
    def items(self):
        """Return all key-value pairs."""
        return [(key, self[key]) for key in self.keys()]
    
    # Proxy methods to the underlying context
    def set_action_data(self, key: str, value: Any):
        """Proxy to context's set_action_data if available."""
        if hasattr(self._context, "set_action_data"):
            self._context.set_action_data(key, value)
        self._dict_cache[key] = value
    
    def get_action_data(self, key: str, default: Any = None) -> Any:
        """Proxy to context's get_action_data if available."""
        if hasattr(self._context, "get_action_data"):
            return self._context.get_action_data(key, default)
        return self._dict_cache.get(key, default)
    
    @property
    def custom_action_data(self):
        """Proxy to context's custom_action_data if available."""
        if hasattr(self._context, "custom_action_data"):
            return self._context.custom_action_data
        return {}
    
    def __repr__(self) -> str:
        """String representation."""
        return f"StrategyExecutionContextAdapter(keys={list(self.keys())})"


def adapt_context(context: Any) -> Any:
    """
    Adapt a context to work with both dict-based and StrategyExecutionContext-based actions.
    
    Args:
        context: Either a dict or StrategyExecutionContext
        
    Returns:
        An adapted context that works with both interfaces
    """
    # If it's already a dict, return as-is
    # Actions can modify dict directly
    if isinstance(context, dict):
        return context
    
    # If it's a StrategyExecutionContext, wrap it
    from .models.execution_context import StrategyExecutionContext
    if isinstance(context, StrategyExecutionContext):
        return StrategyExecutionContextAdapter(context)
    
    # For other types, try to wrap them
    return StrategyExecutionContextAdapter(context)
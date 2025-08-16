"""Universal context handler for biomapper strategy actions.

This module provides a robust context handling system that works with both dict and 
object contexts, preventing the failures encountered with Google Drive sync and other actions.
"""

from typing import Any, Dict, Optional, Union


class UniversalContext:
    """Wrapper that handles both dict and object contexts uniformly.
    
    This class provides a consistent interface for accessing and modifying context data
    regardless of its underlying structure (dict, object with attributes, or ContextAdapter).
    
    Attributes:
        _context: The wrapped context object (dict, object, or None)
        _is_dict: Cached flag indicating if context is dict-like
        _is_object: Cached flag indicating if context is object-like
        _is_adapter: Cached flag indicating if context is ContextAdapter-like
    """

    def __init__(self, context: Union[Dict, Any, None] = None):
        """Initialize the UniversalContext with the given context.
        
        Args:
            context: The context to wrap (dict, object, ContextAdapter, or None).
                    If None, defaults to an empty dictionary.
        """
        self._context = context if context is not None else {}
        
        # Cache context type for performance
        self._is_dict = isinstance(self._context, dict)
        self._is_object = False
        self._is_adapter = False
        self._has_dict_attr = False
        
        if not self._is_dict:
            # Check for ContextAdapter patterns
            if hasattr(self._context, "get_action_data") and hasattr(self._context, "set_action_data"):
                self._is_adapter = True
            elif hasattr(self._context, "_dict") and isinstance(getattr(self._context, "_dict", None), dict):
                self._has_dict_attr = True
            elif hasattr(self._context, "__dict__"):
                self._is_object = True

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the context regardless of context type.
        
        Handles multiple context patterns:
        - Dict: context.get(key, default)
        - Object: getattr(context, key, default)
        - ContextAdapter: context.get_action_data(key) or context._dict.get(key)
        
        Args:
            key: The key to retrieve
            default: The default value to return if the key is not found
            
        Returns:
            The value associated with the key, or the default value if not found
        """
        try:
            if self._is_dict:
                return self._context.get(key, default)
            elif self._is_adapter:
                # Try get_action_data first
                result = self._context.get_action_data(key)
                return result if result is not None else default
            elif self._has_dict_attr:
                # Access through _dict attribute
                return self._context._dict.get(key, default)
            elif self._is_object:
                # Try direct attribute access
                return getattr(self._context, key, default)
            else:
                # Fallback: try dict-like access first, then attribute access
                if hasattr(self._context, "get"):
                    return self._context.get(key, default)
                elif hasattr(self._context, key):
                    return getattr(self._context, key, default)
                else:
                    return default
        except (AttributeError, KeyError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context regardless of context type.
        
        Handles multiple context patterns:
        - Dict: context[key] = value
        - Object: setattr(context, key, value)
        - ContextAdapter: context.set_action_data(key, value) or context._dict[key] = value
        
        Args:
            key: The key to set
            value: The value to set
        """
        try:
            if self._is_dict:
                self._context[key] = value
            elif self._is_adapter:
                # Use set_action_data if available
                self._context.set_action_data(key, value)
            elif self._has_dict_attr:
                # Set through _dict attribute
                self._context._dict[key] = value
            elif self._is_object:
                # Set as attribute
                setattr(self._context, key, value)
            else:
                # Fallback: try dict-like access first, then attribute access
                if hasattr(self._context, "__setitem__"):
                    self._context[key] = value
                else:
                    setattr(self._context, key, value)
        except (AttributeError, TypeError) as e:
            # If all else fails, create a fallback dict attribute
            if not hasattr(self._context, "_fallback_dict"):
                self._context._fallback_dict = {}
            self._context._fallback_dict[key] = value

    def get_datasets(self) -> Dict:
        """Safely get datasets dictionary from context.
        
        Returns:
            The datasets dictionary, or an empty dict if not found or not a dict
        """
        datasets = self.get("datasets", {})
        return datasets if isinstance(datasets, dict) else {}

    def get_statistics(self) -> Dict:
        """Safely get statistics dictionary from context.
        
        Returns:
            The statistics dictionary, or an empty dict if not found or not a dict
        """
        statistics = self.get("statistics", {})
        return statistics if isinstance(statistics, dict) else {}

    def get_output_files(self) -> list:
        """Safely get output_files list from context.
        
        Returns:
            The output_files list, or an empty list if not found or not a list
        """
        output_files = self.get("output_files", [])
        return output_files if isinstance(output_files, list) else []

    def get_current_identifiers(self) -> Any:
        """Safely get current_identifiers from context.
        
        Returns:
            The current_identifiers value, or None if not found
        """
        return self.get("current_identifiers", None)

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the context.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        sentinel = object()
        return self.get(key, sentinel) is not sentinel

    @staticmethod
    def wrap(context: Union[Dict, Any, None] = None) -> "UniversalContext":
        """Factory method to wrap any context type.
        
        Args:
            context: The context to wrap
            
        Returns:
            A new UniversalContext instance wrapping the provided context
        """
        # If already wrapped, return as is
        if isinstance(context, UniversalContext):
            return context
        return UniversalContext(context)

    def unwrap(self) -> Union[Dict, Any]:
        """Get the underlying wrapped context.
        
        Returns:
            The original context object
        """
        return self._context

    def to_dict(self) -> Dict:
        """Convert the context to a dictionary format.
        
        Returns:
            A dictionary representation of the context
        """
        if self._is_dict:
            return self._context.copy()
        elif self._has_dict_attr:
            return self._context._dict.copy()
        elif self._is_adapter:
            # Try to extract from adapter
            result = {}
            for key in ["datasets", "statistics", "output_files", "current_identifiers", "strategy_name", "strategy_version"]:
                val = self.get(key)
                if val is not None:
                    result[key] = val
            return result
        elif self._is_object:
            # Convert object attributes to dict
            return {k: v for k, v in self._context.__dict__.items() if not k.startswith("_")}
        else:
            return {}
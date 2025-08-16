"""Context type detection and accessor utilities for biomapper strategy actions.

This module provides utilities to detect different context types and create
appropriate accessors for uniform interaction with context data.
"""

from typing import Protocol, Any, Dict, Optional, List, runtime_checkable


@runtime_checkable
class ContextAccessor(Protocol):
    """Protocol for consistent access to context data."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        ...

    def keys(self) -> List[str]:
        """Return a list of keys in the context."""
        ...

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the context."""
        ...


class DictContextAccessor:
    """Accessor for dictionary contexts."""
    
    def __init__(self, context: Dict):
        self.context = context

    def get(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.context[key] = value

    def keys(self) -> List[str]:
        return list(self.context.keys())

    def has_key(self, key: str) -> bool:
        return key in self.context


class ObjectContextAccessor:
    """Accessor for object contexts with attributes."""
    
    def __init__(self, context: Any):
        self.context = context

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.context, key, default)

    def set(self, key: str, value: Any) -> None:
        setattr(self.context, key, value)

    def keys(self) -> List[str]:
        if hasattr(self.context, "__dict__"):
            return [k for k in self.context.__dict__.keys() if not k.startswith("_")]
        return []

    def has_key(self, key: str) -> bool:
        return hasattr(self.context, key)


class AdapterContextAccessor:
    """Accessor for ContextAdapter-style contexts."""
    
    def __init__(self, context: Any):
        self.context = context

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self.context, "get_action_data"):
            result = self.context.get_action_data(key)
            return result if result is not None else default
        return default

    def set(self, key: str, value: Any) -> None:
        if hasattr(self.context, "set_action_data"):
            self.context.set_action_data(key, value)

    def keys(self) -> List[str]:
        # Try to access _dict if available
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            return list(self.context._dict.keys())
        # Otherwise return common keys
        return ["datasets", "statistics", "output_files", "current_identifiers"]

    def has_key(self, key: str) -> bool:
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            return key in self.context._dict
        # Try to get the value to check existence
        sentinel = object()
        return self.get(key, sentinel) is not sentinel


class ObjectWithDictAccessor:
    """Accessor for objects with a _dict attribute."""
    
    def __init__(self, context: Any):
        self.context = context

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            return self.context._dict.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            self.context._dict[key] = value
        else:
            # Create _dict if it doesn't exist
            if not hasattr(self.context, "_dict"):
                self.context._dict = {}
            self.context._dict[key] = value

    def keys(self) -> List[str]:
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            return list(self.context._dict.keys())
        return []

    def has_key(self, key: str) -> bool:
        if hasattr(self.context, "_dict") and isinstance(self.context._dict, dict):
            return key in self.context._dict
        return False


def detect_context_type(context: Any) -> str:
    """Detect the type of context object.

    Args:
        context: The context object to analyze

    Returns:
        One of: 'dict', 'adapter', 'object_with_dict', 'object', or 'unknown'
    """
    if context is None:
        return 'unknown'
    
    # Check for dictionary first (most common)
    if isinstance(context, dict):
        return 'dict'
    
    # Check for ContextAdapter pattern
    if hasattr(context, 'get_action_data') and hasattr(context, 'set_action_data'):
        return 'adapter'
    
    # Check for object with _dict attribute
    if hasattr(context, '_dict') and isinstance(getattr(context, '_dict', None), dict):
        return 'object_with_dict'
    
    # Check for regular object with __dict__
    if hasattr(context, '__dict__'):
        return 'object'
    
    return 'unknown'


def get_context_accessor(context: Any) -> Optional[ContextAccessor]:
    """Get an appropriate ContextAccessor for the given context.

    Args:
        context: The context object to create an accessor for

    Returns:
        An appropriate ContextAccessor instance, or None if type is unknown
    """
    context_type = detect_context_type(context)
    
    if context_type == 'dict':
        return DictContextAccessor(context)
    elif context_type == 'adapter':
        return AdapterContextAccessor(context)
    elif context_type == 'object_with_dict':
        return ObjectWithDictAccessor(context)
    elif context_type == 'object':
        return ObjectContextAccessor(context)
    else:
        return None


def is_dict_context(context: Any) -> bool:
    """Check if the context is a dictionary.
    
    Args:
        context: The context to check
        
    Returns:
        True if context is a dictionary, False otherwise
    """
    return isinstance(context, dict)


def is_object_context(context: Any) -> bool:
    """Check if the context is an object with attributes.
    
    Args:
        context: The context to check
        
    Returns:
        True if context has __dict__ attribute, False otherwise
    """
    return hasattr(context, '__dict__')


def is_adapter_context(context: Any) -> bool:
    """Check if the context is a ContextAdapter.
    
    Args:
        context: The context to check
        
    Returns:
        True if context has adapter methods, False otherwise
    """
    return hasattr(context, 'get_action_data') and hasattr(context, 'set_action_data')


def is_object_with_dict_context(context: Any) -> bool:
    """Check if the context is an object with _dict attribute.
    
    Args:
        context: The context to check
        
    Returns:
        True if context has _dict attribute that is a dict, False otherwise
    """
    return hasattr(context, '_dict') and isinstance(getattr(context, '_dict', None), dict)


def get_context_info(context: Any) -> Dict[str, Any]:
    """Get detailed information about the context type.
    
    Args:
        context: The context to analyze
        
    Returns:
        Dictionary with detailed type information including:
        - type: The detected context type
        - is_dict: Whether it's a dictionary
        - is_object: Whether it's an object with __dict__
        - is_adapter: Whether it's a ContextAdapter
        - is_object_with_dict: Whether it's an object with _dict
        - attributes: List of available attributes (if applicable)
        - keys: List of available keys (if applicable)
    """
    info = {
        'type': detect_context_type(context),
        'is_dict': is_dict_context(context),
        'is_object': is_object_context(context),
        'is_adapter': is_adapter_context(context),
        'is_object_with_dict': is_object_with_dict_context(context),
        'attributes': [],
        'keys': []
    }
    
    # Add attributes if object
    if hasattr(context, '__dict__'):
        info['attributes'] = [k for k in dir(context) if not k.startswith('_')]
    
    # Add keys if dict-like
    if isinstance(context, dict):
        info['keys'] = list(context.keys())
    elif hasattr(context, '_dict') and isinstance(context._dict, dict):
        info['keys'] = list(context._dict.keys())
    
    return info
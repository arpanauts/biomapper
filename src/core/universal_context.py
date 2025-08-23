"""
Universal Context Wrapper for Pipeline Orchestration
====================================================

🔄 Circuitous Framework Solution
This wrapper enables smooth context flow through the pipeline by providing
a unified interface that works with both dict-style and object-style access patterns.

Key Design Principles:
1. Preserves action boundaries - no internal logic modification required
2. Handles context handoffs transparently between pipeline stages
3. Maintains backward compatibility with existing actions
4. Enables smooth parameter flow through the orchestration layer
"""

import logging
from typing import Any, Dict, Optional, Union
from collections.abc import MutableMapping

logger = logging.getLogger(__name__)


class UniversalContext(MutableMapping):
    """
    Universal context wrapper that provides both dict-like and object-like interfaces.
    
    This enables seamless context flow through pipeline stages regardless of whether
    actions expect dict access (context.get(), context['key']) or object access
    (context.datasets, context.parameters).
    
    🔄 Circuitous Design: Acts as a transparent orchestration layer without
    modifying action internals.
    """
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize with optional dict data."""
        self._data = initial_data or {}
        self._ensure_core_structure()
    
    def _ensure_core_structure(self):
        """Ensure core pipeline structures exist."""
        # Core structures required by pipeline orchestration
        if 'datasets' not in self._data:
            self._data['datasets'] = {}
        if 'parameters' not in self._data:
            self._data['parameters'] = {}
        if 'statistics' not in self._data:
            self._data['statistics'] = {}
        if 'output_files' not in self._data:
            self._data['output_files'] = []
        if 'current_identifiers' not in self._data:
            self._data['current_identifiers'] = []
    
    # Dict-like interface for actions expecting dict context
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get method."""
        return self._data.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Dict-style bracket access."""
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style bracket assignment."""
        self._data[key] = value
    
    def __delitem__(self, key: str) -> None:
        """Dict-style deletion."""
        del self._data[key]
    
    def __iter__(self):
        """Dict-style iteration."""
        return iter(self._data)
    
    def __len__(self) -> int:
        """Dict-style length."""
        return len(self._data)
    
    def __contains__(self, key: str) -> bool:
        """Dict-style membership test."""
        return key in self._data
    
    def keys(self):
        """Dict-style keys access."""
        return self._data.keys()
    
    def values(self):
        """Dict-style values access."""
        return self._data.values()
    
    def items(self):
        """Dict-style items access."""
        return self._data.items()
    
    def update(self, other: Union[Dict, 'UniversalContext'], **kwargs) -> None:
        """Dict-style update."""
        if isinstance(other, UniversalContext):
            self._data.update(other._data)
        else:
            self._data.update(other)
        self._data.update(kwargs)
    
    # Object-like interface for actions expecting object context
    def __getattr__(self, name: str) -> Any:
        """Object-style attribute access."""
        if name.startswith('_'):
            # Avoid infinite recursion for private attributes
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Object-style attribute assignment."""
        if name.startswith('_'):
            # Set private attributes normally
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    # Specialized methods for pipeline orchestration
    def get_datasets(self) -> Dict[str, Any]:
        """Get datasets dict for pipeline handoffs."""
        return self._data.get('datasets', {})
    
    def set_dataset(self, key: str, data: Any) -> None:
        """Set a dataset for pipeline handoffs."""
        if 'datasets' not in self._data:
            self._data['datasets'] = {}
        self._data['datasets'][key] = data
        logger.debug(f"🔄 Dataset '{key}' stored in context (circuitous handoff)")
    
    def get_dataset(self, key: str, default: Any = None) -> Any:
        """Get a dataset from context."""
        return self._data.get('datasets', {}).get(key, default)
    
    def has_dataset(self, key: str) -> bool:
        """Check if dataset exists."""
        return key in self._data.get('datasets', {})
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get parameters for action configuration."""
        return self._data.get('parameters', {})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for pipeline metrics."""
        return self._data.get('statistics', {})
    
    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """Update statistics with new metrics."""
        if 'statistics' not in self._data:
            self._data['statistics'] = {}
        self._data['statistics'].update(stats)
    
    # Conversion methods for interoperability
    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for serialization."""
        return dict(self._data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversalContext':
        """Create from plain dict."""
        return cls(data)
    
    @classmethod
    def wrap(cls, context: Any) -> 'UniversalContext':
        """
        Wrap any context type into UniversalContext.
        
        🔄 Circuitous Pattern: Transparently wraps existing contexts
        without breaking compatibility.
        """
        if isinstance(context, cls):
            return context
        elif isinstance(context, dict):
            return cls(context)
        elif hasattr(context, '__dict__'):
            # Object with attributes
            return cls(context.__dict__)
        elif hasattr(context, 'to_dict'):
            # Object with to_dict method
            return cls(context.to_dict())
        else:
            # Create minimal context
            logger.warning(f"🔄 Creating minimal context from type: {type(context)}")
            return cls()
    
    def sync_to(self, target: Any) -> None:
        """
        Sync changes back to original context format.
        
        🔄 Circuitous Pattern: Maintains bidirectional flow without
        breaking existing context patterns.
        """
        if isinstance(target, dict):
            target.clear()
            target.update(self._data)
        elif hasattr(target, '__dict__'):
            for key, value in self._data.items():
                setattr(target, key, value)
    
    def __repr__(self) -> str:
        """String representation."""
        datasets = list(self._data.get('datasets', {}).keys())
        return f"UniversalContext(datasets={datasets}, keys={list(self._data.keys())})"
    
    # Pipeline orchestration helpers
    def checkpoint(self, stage_name: str) -> Dict[str, Any]:
        """
        Create checkpoint for pipeline stage.
        
        🔄 Circuitous Pattern: Enables stage recovery without
        modifying action implementations.
        """
        return {
            'stage': stage_name,
            'datasets': list(self.get_datasets().keys()),
            'statistics': dict(self.get_statistics()),
            'parameters': dict(self.get_parameters())
        }
    
    def validate_handoff(self, required_keys: list) -> bool:
        """
        Validate context has required data for handoff.
        
        🔄 Circuitous Pattern: Pre-flight check for smooth transitions.
        """
        datasets = self.get_datasets()
        missing = [key for key in required_keys if key not in datasets]
        if missing:
            logger.warning(f"🔄 Context handoff validation failed. Missing: {missing}")
            return False
        return True


# 🔄 Circuitous Framework Helper Functions

def ensure_universal_context(context: Any) -> UniversalContext:
    """
    Ensure context is wrapped in UniversalContext.
    
    This is the primary entry point for pipeline orchestration to ensure
    smooth context flow regardless of action expectations.
    """
    return UniversalContext.wrap(context)


def create_pipeline_context(**kwargs) -> UniversalContext:
    """
    Create a new UniversalContext with pipeline defaults.
    
    🔄 Circuitous Pattern: Standardized context creation for pipelines.
    """
    context = UniversalContext()
    context.update(kwargs)
    return context
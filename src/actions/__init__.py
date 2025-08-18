"""
Strategy action handlers for YAML-defined mapping strategies (Streamlined).

This module provides essential biomapper actions for protein mapping with
Nightingale NMR support and core biological data harmonization.

Organization Structure:
- entities/: Entity-specific actions (proteins, metabolites, chemistry)
- utils/: General utility functions
- io/: Data input/output actions

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

# Import registry first (required for action registration)

# Import base classes

# Import organizational modules (triggers action registration)

# Import essential actions for backward compatibility

# Export registry components for backward compatibility
from .registry import ACTION_REGISTRY, register_action

__all__ = ['ACTION_REGISTRY', 'register_action']

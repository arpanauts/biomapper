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
from .registry import ACTION_REGISTRY, register_action

# Import base classes
from .typed_base import TypedStrategyAction

# Import core actions (triggers registration)
from . import load_dataset_identifiers
from . import export_dataset
from . import merge_datasets
from . import semantic_metabolite_match

# Import organizational modules (triggers action registration)
from . import entities
from . import utils
from . import io
from . import reports

# Export registry components for backward compatibility
__all__ = ['ACTION_REGISTRY', 'register_action', 'TypedStrategyAction']

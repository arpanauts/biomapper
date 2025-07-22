"""
Strategy action handlers for YAML-defined mapping strategies.

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

from .base import BaseStrategyAction, StrategyAction, ActionContext
from .typed_base import TypedStrategyAction, StandardActionResult
from .load_dataset_identifiers import LoadDatasetIdentifiersAction, LoadDatasetIdentifiersParams
from .merge_with_uniprot_resolution import MergeWithUniprotResolutionAction, MergeWithUniprotResolutionParams
from .calculate_set_overlap import CalculateSetOverlapAction, CalculateSetOverlapParams

__all__ = [
    # Base classes
    "BaseStrategyAction",
    "StrategyAction",
    "ActionContext",
    "TypedStrategyAction",
    "StandardActionResult",
    # MVP Action implementations
    "LoadDatasetIdentifiersAction",
    "LoadDatasetIdentifiersParams",
    "MergeWithUniprotResolutionAction",
    "MergeWithUniprotResolutionParams",
    "CalculateSetOverlapAction",
    "CalculateSetOverlapParams"
]
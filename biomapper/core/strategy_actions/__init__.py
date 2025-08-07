"""
Strategy action handlers for YAML-defined mapping strategies (Enhanced Organization).

This module provides biomapper actions organized by entity type and function
for scalable biological data harmonization.

Enhanced Organization Structure:
- entities/: Entity-specific actions (proteins, metabolites, chemistry)
- algorithms/: Reusable computational algorithms  
- utils/: General utility functions
- workflows/: High-level orchestration actions
- io/: Data input/output actions
- reports/: Analysis and reporting actions

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

# Import registry first (required for action registration)
from . import registry

# Import base classes
from .base import BaseStrategyAction, StrategyAction, ActionContext
from .typed_base import TypedStrategyAction, StandardActionResult

# Import enhanced organizational modules (triggers action registration)
from . import entities
from . import algorithms
from . import utils
from . import workflows
from . import io
from . import reports

# Import existing actions for backward compatibility
# (These will be migrated to appropriate entity directories)
from .load_dataset_identifiers import (
    LoadDatasetIdentifiersAction,
    LoadDatasetIdentifiersParams,
)
from .merge_with_uniprot_resolution import (
    MergeWithUniprotResolutionAction,
    MergeWithUniprotResolutionParams,
)
from .calculate_set_overlap import CalculateSetOverlapAction, CalculateSetOverlapParams
from .merge_datasets import MergeDatasetsAction, MergeDatasetsParams

# Import metabolomics actions (to be migrated to entities/metabolites/)
from .baseline_fuzzy_match import BaselineFuzzyMatchAction
from .build_nightingale_reference import BuildNightingaleReferenceAction
from .cts_enriched_match import CtsEnrichedMatchAction
from .generate_enhancement_report import GenerateEnhancementReport
from .nightingale_nmr_match import NightingaleNmrMatchAction
from .vector_enhanced_match import VectorEnhancedMatchAction
from .semantic_metabolite_match import SemanticMetaboliteMatchAction
from .metabolite_api_enrichment import MetaboliteApiEnrichmentAction
from .combine_metabolite_matches import CombineMetaboliteMatchesAction
from .calculate_three_way_overlap import CalculateThreeWayOverlapAction

__all__ = [
    # Base classes
    "BaseStrategyAction",
    "StrategyAction",
    "ActionContext",
    "TypedStrategyAction",
    "StandardActionResult",
    # Enhanced Organization Modules
    # (Actions auto-register when these are imported)
    "entities",  # Entity-specific actions (proteins, metabolites, chemistry)
    "algorithms",  # Reusable algorithms (fuzzy_matching, normalization)
    "utils",  # General utilities (data_processing, logging)
    "workflows",  # High-level orchestration actions
    "io",  # Data input/output actions
    "reports",  # Analysis and reporting actions
    "registry",  # Action registry
    # Legacy Action Classes (for backward compatibility)
    # TODO: Migrate these to appropriate entity directories
    "LoadDatasetIdentifiersAction",
    "LoadDatasetIdentifiersParams",
    "MergeWithUniprotResolutionAction",
    "MergeWithUniprotResolutionParams",
    "CalculateSetOverlapAction",
    "CalculateSetOverlapParams",
    "MergeDatasetsAction",
    "MergeDatasetsParams",
    # Metabolomics Actions (to be migrated to entities/metabolites/)
    "BaselineFuzzyMatchAction",
    "BuildNightingaleReferenceAction",
    "CtsEnrichedMatchAction",
    "GenerateEnhancementReport",
    "NightingaleNmrMatchAction",
    "VectorEnhancedMatchAction",
    "SemanticMetaboliteMatchAction",
    "MetaboliteApiEnrichmentAction",
    "CombineMetaboliteMatchesAction",
    "CalculateThreeWayOverlapAction",
]

# Create metabolomics-specific aliases for existing actions
import logging
from .registry import ACTION_REGISTRY

logger = logging.getLogger(__name__)

# Alias for metabolite name matching (uses fuzzy match)
ACTION_REGISTRY["METABOLITE_NAME_MATCH"] = ACTION_REGISTRY["BASELINE_FUZZY_MATCH"]

# Alias for enriched metabolite matching (uses vector match)
ACTION_REGISTRY["ENRICHED_METABOLITE_MATCH"] = ACTION_REGISTRY["VECTOR_ENHANCED_MATCH"]

# Log successful aliasing
logger.info("Created metabolomics action aliases:")
logger.info("  METABOLITE_NAME_MATCH -> BASELINE_FUZZY_MATCH")
logger.info("  ENRICHED_METABOLITE_MATCH -> VECTOR_ENHANCED_MATCH")
logger.info("  METABOLITE_API_ENRICHMENT -> CTS_ENRICHED_MATCH (extended version)")

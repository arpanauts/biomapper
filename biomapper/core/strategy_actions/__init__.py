"""
Strategy action handlers for YAML-defined mapping strategies.

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

from .bidirectional_match import BidirectionalMatchAction
from .convert_identifiers_local import ConvertIdentifiersLocalAction
from .execute_mapping_path import ExecuteMappingPathAction
from .filter_by_target_presence import FilterByTargetPresenceAction
from .resolve_and_match_forward import ResolveAndMatchForwardAction
from .resolve_and_match_reverse import ResolveAndMatchReverse
from .generate_mapping_summary import GenerateMappingSummaryAction
from .generate_detailed_report import GenerateDetailedReportAction
from .export_results import ExportResultsAction
from .visualize_mapping_flow import VisualizeMappingFlowAction
from .populate_context import PopulateContextAction
from .collect_matched_targets import CollectMatchedTargetsAction

__all__ = [
    "BidirectionalMatchAction",
    "ConvertIdentifiersLocalAction",
    "ExecuteMappingPathAction", 
    "FilterByTargetPresenceAction",
    "ResolveAndMatchForwardAction",
    "ResolveAndMatchReverse",
    "GenerateMappingSummaryAction",
    "GenerateDetailedReportAction",
    "ExportResultsAction",
    "VisualizeMappingFlowAction",
    "PopulateContextAction",
    "CollectMatchedTargetsAction"
]
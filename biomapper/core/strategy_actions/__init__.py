"""
Strategy action handlers for YAML-defined mapping strategies.

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

from .base import BaseStrategyAction, StrategyAction, ActionContext
from .typed_base import TypedStrategyAction, StandardActionResult
from .bidirectional_match import BidirectionalMatchAction
from .execute_mapping_path import ExecuteMappingPathAction
from .execute_mapping_path_typed import ExecuteMappingPathTypedAction, ExecuteMappingPathParams, ExecuteMappingPathResult
from .filter_by_target_presence import FilterByTargetPresenceAction
from .resolve_and_match_forward import ResolveAndMatchForwardAction
from .resolve_and_match_reverse import ResolveAndMatchReverse
from .generate_mapping_summary import GenerateMappingSummaryAction
from .generate_detailed_report import GenerateDetailedReportAction
from .export_results import ExportResultsAction
from .visualize_mapping_flow import VisualizeMappingFlowAction
from .populate_context import PopulateContextAction
from .collect_matched_targets import CollectMatchedTargetsAction
from .load_endpoint_identifiers_action import LoadEndpointIdentifiersAction
from .reconcile_bidirectional_action import ReconcileBidirectionalAction
from .save_bidirectional_results_action import SaveBidirectionalResultsAction
from .composite_id_splitter import CompositeIdSplitter
from .overlap_analyzer import DatasetOverlapAnalyzer
from .api_resolver import ApiResolver
from .local_id_converter import LocalIdConverter
from .results_saver import ResultsSaver
from .uniprot_historical_resolver import UniProtHistoricalResolver

__all__ = [
    # Base classes
    "BaseStrategyAction",
    "StrategyAction",
    "ActionContext",
    "TypedStrategyAction",
    "StandardActionResult",
    # Action implementations
    "BidirectionalMatchAction",
    "ExecuteMappingPathAction",
    "ExecuteMappingPathTypedAction",
    "ExecuteMappingPathParams",
    "ExecuteMappingPathResult", 
    "FilterByTargetPresenceAction",
    "ResolveAndMatchForwardAction",
    "ResolveAndMatchReverse",
    "GenerateMappingSummaryAction",
    "GenerateDetailedReportAction",
    "ExportResultsAction",
    "VisualizeMappingFlowAction",
    "PopulateContextAction",
    "CollectMatchedTargetsAction",
    "LoadEndpointIdentifiersAction",
    "ReconcileBidirectionalAction",
    "SaveBidirectionalResultsAction",
    "CompositeIdSplitter",
    "DatasetOverlapAnalyzer",
    "ApiResolver",
    "LocalIdConverter",
    "ResultsSaver",
    "UniProtHistoricalResolver"
]
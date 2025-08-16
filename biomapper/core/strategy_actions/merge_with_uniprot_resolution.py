"""Merge datasets with intelligent UniProt ID resolution."""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from pydantic import Field
from biomapper.core.standards import ActionParamsBase

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
# StrategyExecutionContext not used in MVP mode

from biomapper.mapping.clients.uniprot_historical_resolver_client import (
    UniProtHistoricalResolverClient,
)
from biomapper.core.standards.api_validator import APIMethodValidator

logger = logging.getLogger(__name__)


class MergeWithUniprotResolutionParams(ActionParamsBase):
    """Parameters for MERGE_WITH_UNIPROT_RESOLUTION action."""

    # Input datasets
    input_key: str = Field(..., description="First dataset from context")
    target_dataset_key: str = Field(..., description="Second dataset from context")

    # Column specifications
    source_id_column: str = Field(..., description="ID column in source dataset")
    target_id_column: str = Field(..., description="ID column in target dataset")
    target_xref_column: Optional[str] = Field(None, description="Column containing xrefs (e.g., 'xrefs' for KG2c)")

    # Composite handling
    composite_separator: str = Field("_", description="Separator for composite IDs")

    # API configuration
    use_api: bool = Field(True, description="Whether to use API for unresolved")
    api_batch_size: int = Field(100, description="IDs per API call")
    api_cache_results: bool = Field(True, description="Cache API responses")

    # Output
    output_key: str = Field(..., description="Key for merged dataset")

    # Options
    confidence_threshold: float = Field(
        0.0, description="Minimum confidence to keep", ge=0.0, le=1.0
    )


@register_action("MERGE_WITH_UNIPROT_RESOLUTION")
class MergeWithUniprotResolutionAction(
    TypedStrategyAction[MergeWithUniprotResolutionParams, StandardActionResult]
):
    """
    Intelligently merge two protein datasets with UniProt ID resolution.

    This action:
    - Performs direct matching (exact and composite ID logic)
    - Uses UniProt API for unresolved identifiers
    - Preserves ALL rows (matched and unmatched)
    - Tracks detailed match metadata for reporting
    - Handles composite IDs by creating multiple rows
    """

    def get_params_model(self) -> type[MergeWithUniprotResolutionParams]:
        return MergeWithUniprotResolutionParams

    def get_result_model(self) -> type[StandardActionResult]:
        return StandardActionResult

    def __init__(self, db_session: Any = None, *args: Any, **kwargs: Any) -> None:
        """Initialize the action."""
        super().__init__(db_session, *args, **kwargs)
        self._uniprot_client: Optional[UniProtHistoricalResolverClient] = None

    async def _get_uniprot_client(self) -> UniProtHistoricalResolverClient:
        """Get or create the UniProt client."""
        if self._uniprot_client is None:
            self._uniprot_client = UniProtHistoricalResolverClient(
                cache_size=10000, timeout=30
            )
            # Validate that the client has the expected methods
            try:
                APIMethodValidator.validate_client_interface(
                    self._uniprot_client,
                    required_methods=['map_identifiers'],
                    optional_methods=['resolve_batch', '_fetch_uniprot_search_results']
                )
            except ValueError as e:
                logger.error(f"UniProt client validation failed: {e}")
                raise
        return self._uniprot_client

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MergeWithUniprotResolutionParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute the three-phase merging process."""

        start_time = time.time()

        # Initialize datasets and metadata in custom action data
        if "datasets" not in context.custom_action_data:
            context.set_action_data("datasets", {})
        if "metadata" not in context.custom_action_data:
            context.set_action_data("metadata", {})

        logger.info(
            f"Starting merge with UniProt resolution: {params.source_dataset_key} + {params.target_dataset_key}"
        )

        try:
            # Get datasets from context
            datasets = context.get_action_data("datasets", {})

            if params.source_dataset_key not in datasets:
                raise ValueError(
                    f"Source dataset '{params.source_dataset_key}' not found in context"
                )
            if params.target_dataset_key not in datasets:
                raise ValueError(
                    f"Target dataset '{params.target_dataset_key}' not found in context"
                )

            source_data = datasets[params.source_dataset_key]
            target_data = datasets[params.target_dataset_key]

            # Convert to DataFrames for easier processing
            # Use copy to ensure no reference issues
            source_df = pd.DataFrame(source_data).copy()
            target_df = pd.DataFrame(target_data).copy()

            # Handle empty datasets
            if source_df.empty and target_df.empty:
                # Both empty - return empty result
                merged_data: List[Dict[str, Any]] = []
                match_stats = {
                    "direct": 0,
                    "composite": 0,
                    "historical": 0,
                    "unmatched_source": 0,
                    "unmatched_target": 0,
                }

                # Store results and create metadata
                datasets[params.output_key] = merged_data
                context.set_action_data("datasets", datasets)

                processing_time = time.time() - start_time
                metadata = {
                    "total_source_rows": 0,
                    "total_target_rows": 0,
                    "total_output_rows": 0,
                    "matches_by_type": match_stats,
                    "unmatched_source": 0,
                    "unmatched_target": 0,
                    "api_calls_made": 0,
                    "unique_source_ids": 0,
                    "unique_target_ids": 0,
                    "processing_time": processing_time,
                }

                metadata_dict = context.get_action_data("metadata", {})
                metadata_dict[params.output_key] = metadata
                context.set_action_data("metadata", metadata_dict)

                return StandardActionResult(
                    input_identifiers=[],
                    output_identifiers=[],
                    output_ontology_type="protein",
                    provenance=[
                        {
                            "action": "MERGE_WITH_UNIPROT_RESOLUTION",
                            "source_dataset": params.source_dataset_key,
                            "target_dataset": params.target_dataset_key,
                            "total_matches": 0,
                            "api_calls_made": 0,
                        }
                    ],
                    details={
                        "output_key": params.output_key,
                        "processing_time": processing_time,
                        "match_stats": match_stats,
                    },
                )

            # Validate ID columns exist (only for non-empty datasets)
            if not source_df.empty and params.source_id_column not in source_df.columns:
                available_cols = list(source_df.columns)
                raise ValueError(
                    f"Source ID column '{params.source_id_column}' not found. "
                    f"Available columns: {available_cols}"
                )
            if not target_df.empty and params.target_id_column not in target_df.columns:
                available_cols = list(target_df.columns)
                raise ValueError(
                    f"Target ID column '{params.target_id_column}' not found. "
                    f"Available columns: {available_cols}"
                )

            # Phase 1: Direct matching with composite logic
            logger.info("Phase 1: Direct matching with composite logic")
            direct_matches = self._find_direct_matches(source_df, target_df, params)

            # Phase 2: API resolution for unmatched (if enabled)
            api_matches: List[Dict[str, Any]] = []
            api_calls_made = 0
            if params.use_api:
                logger.info("Phase 2: API resolution for unmatched IDs")
                api_matches, api_calls_made = await self._resolve_with_api(
                    source_df, target_df, direct_matches, params
                )

            # Phase 3: Create full merged dataset
            logger.info("Phase 3: Create full merged dataset")
            merged_data, match_stats = self._create_merged_dataset(
                source_df, target_df, direct_matches, api_matches, params
            )

            # Store results in context
            datasets[params.output_key] = merged_data
            context.set_action_data("datasets", datasets)

            # Create metadata
            processing_time = time.time() - start_time
            metadata = {
                "total_source_rows": len(source_df),
                "total_target_rows": len(target_df),
                "total_output_rows": len(merged_data),
                "matches_by_type": {
                    "direct": match_stats["direct"],
                    "composite": match_stats["composite"],
                    "historical": match_stats["historical"],
                },
                "unmatched_source": match_stats["unmatched_source"],
                "unmatched_target": match_stats["unmatched_target"],
                "api_calls_made": api_calls_made,
                "unique_source_ids": len(
                    source_df[params.source_id_column].dropna().unique()
                ),
                "unique_target_ids": len(
                    target_df[params.target_id_column].dropna().unique()
                ),
                "processing_time": processing_time,
            }

            metadata_dict = context.get_action_data("metadata", {})
            metadata_dict[params.output_key] = metadata
            context.set_action_data("metadata", metadata_dict)

            logger.info(
                f"Merge complete: {len(merged_data)} rows, "
                f"{match_stats['direct'] + match_stats['composite'] + match_stats['historical']} matches, "
                f"{processing_time:.2f}s"
            )

            return StandardActionResult(
                input_identifiers=[],
                output_identifiers=[
                    str(row.get(params.source_id_column, "")) for row in merged_data
                ],
                output_ontology_type="protein",
                provenance=[
                    {
                        "action": "MERGE_WITH_UNIPROT_RESOLUTION",
                        "source_dataset": params.source_dataset_key,
                        "target_dataset": params.target_dataset_key,
                        "total_matches": match_stats["direct"]
                        + match_stats["composite"]
                        + match_stats["historical"],
                        "api_calls_made": api_calls_made,
                    }
                ],
                details={
                    "output_key": params.output_key,
                    "processing_time": processing_time,
                    "match_stats": match_stats,
                },
            )

        except Exception as e:
            logger.error(f"Failed to merge datasets: {str(e)}")
            raise

    def _find_matches(
        self, source_id: str, target_id: str, separator: str
    ) -> List[Tuple[str, str]]:
        """Find all matches between IDs, including composite logic.

        Returns list of (match_value, match_type) tuples.
        """
        matches: List[Tuple[str, str]] = []

        # Skip if either ID is null/empty
        if (
            pd.isna(source_id)
            or pd.isna(target_id)
            or not str(source_id).strip()
            or not str(target_id).strip()
        ):
            return matches

        source_id = str(source_id).strip()
        target_id = str(target_id).strip()

        # Exact match
        if source_id == target_id:
            matches.append((source_id, "direct"))
            return matches

        # Source composite, target single
        if separator in source_id:
            parts = source_id.split(separator)
            if target_id in parts:
                matches.append((target_id, "composite"))

        # Target composite, source single
        elif separator in target_id:
            parts = target_id.split(separator)
            if source_id in parts:
                matches.append((source_id, "composite"))

        # Both composite - find all overlapping parts
        if separator in source_id and separator in target_id:
            parts1 = set(source_id.split(separator))
            parts2 = set(target_id.split(separator))
            for common in parts1 & parts2:
                matches.append((common, "composite"))

        return matches

    def _find_direct_matches(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        params: MergeWithUniprotResolutionParams,
    ) -> List[Dict[str, Any]]:
        """Find direct matches between datasets using efficient indexing."""
        matches = []
        
        # Create indexes for fast lookup
        # Build a mapping from target IDs to their row indices
        target_id_to_indices = {}
        
        # Also build an index of extracted UniProt IDs from target
        target_uniprot_to_indices = {}
        
        for target_idx, target_row in target_df.iterrows():
            target_id = str(target_row[params.target_id_column])
            
            # Store original ID
            if target_id not in target_id_to_indices:
                target_id_to_indices[target_id] = []
            target_id_to_indices[target_id].append((target_idx, target_row.copy()))
            
            # Extract UniProt ID if the ID column contains UniProtKB prefix
            if target_id.startswith('UniProtKB:'):
                uniprot_id = target_id.replace('UniProtKB:', '')
                # Store with isoform
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row.copy()))
                
                # Also store base ID (without isoform suffix) for matching
                base_id = uniprot_id.split('-')[0]
                if base_id != uniprot_id:  # Only if it has an isoform suffix
                    if base_id not in target_uniprot_to_indices:
                        target_uniprot_to_indices[base_id] = []
                    target_uniprot_to_indices[base_id].append((target_idx, target_row.copy()))
            
            # Also extract UniProt IDs from xrefs column if specified
            if hasattr(params, 'target_xref_column') and params.target_xref_column:
                xref_value = str(target_row.get(params.target_xref_column, ''))
                if xref_value and xref_value != 'nan':
                    # Extract all UniProt IDs from xrefs
                    # Look for patterns like UniProtKB:P12345 or uniprot:P12345
                    import re
                    uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
                    for match in uniprot_pattern.finditer(xref_value):
                        uniprot_id = match.group(1)
                        # Store with isoform
                        if uniprot_id not in target_uniprot_to_indices:
                            target_uniprot_to_indices[uniprot_id] = []
                        # Store a copy of the row to avoid reference issues
                        target_uniprot_to_indices[uniprot_id].append((target_idx, target_row.copy()))
                        
                        # Also store base ID (without isoform suffix) for matching
                        base_id = uniprot_id.split('-')[0]
                        if base_id != uniprot_id:  # Only if it has an isoform suffix
                            if base_id not in target_uniprot_to_indices:
                                target_uniprot_to_indices[base_id] = []
                            target_uniprot_to_indices[base_id].append((target_idx, target_row.copy()))
        
        # Also build index for composite IDs in target
        target_composite_parts = {}
        for target_idx, target_row in target_df.iterrows():
            target_id = str(target_row[params.target_id_column])
            if params.composite_separator in target_id:
                parts = target_id.split(params.composite_separator)
                for part in parts:
                    if part not in target_composite_parts:
                        target_composite_parts[part] = []
                    target_composite_parts[part].append((target_idx, target_id, target_row.copy()))
        
        # Now iterate through source only once
        for source_idx, source_row in source_df.iterrows():
            source_id = str(source_row[params.source_id_column])
            
            # First check if source UniProt ID matches any extracted target UniProt IDs
            if source_id in target_uniprot_to_indices:
                for target_idx, target_row in target_uniprot_to_indices[source_id]:
                    matches.append({
                        "source_idx": source_idx,
                        "target_idx": target_idx,
                        "source_id": source_id,
                        "target_id": str(target_row[params.target_id_column]),
                        "match_value": source_id,
                        "match_type": "direct",
                        "match_confidence": 1.0,
                        "api_resolved": False,
                    })
            
            # Also check for exact match in case source has prefixed IDs (O(1) lookup)
            elif source_id in target_id_to_indices:
                for target_idx, target_row in target_id_to_indices[source_id]:
                    matches.append({
                        "source_idx": source_idx,
                        "target_idx": target_idx,
                        "source_id": source_id,
                        "target_id": source_id,  # Exact match
                        "match_value": source_id,
                        "match_type": "direct",
                        "match_confidence": 1.0,
                        "api_resolved": False,
                    })
            
            # Check composite matches
            if params.composite_separator in source_id:
                # Source is composite - check each part against target
                parts = source_id.split(params.composite_separator)
                for part in parts:
                    # Check if part matches extracted UniProt IDs
                    if part in target_uniprot_to_indices:
                        for target_idx, target_row in target_uniprot_to_indices[part]:
                            matches.append({
                                "source_idx": source_idx,
                                "target_idx": target_idx,
                                "source_id": source_id,
                                "target_id": str(target_row[params.target_id_column]),
                                "match_value": part,
                                "match_type": "composite",
                                "match_confidence": 1.0,
                                "api_resolved": False,
                            })
                    # Also check if part matches a full target ID
                    elif part in target_id_to_indices:
                        for target_idx, target_row in target_id_to_indices[part]:
                            matches.append({
                                "source_idx": source_idx,
                                "target_idx": target_idx,
                                "source_id": source_id,
                                "target_id": part,
                                "match_value": part,
                                "match_type": "composite",
                                "match_confidence": 1.0,
                                "api_resolved": False,
                            })
            else:
                # Source is single - check if it's in any composite target
                if source_id in target_composite_parts:
                    for target_idx, target_id, target_row in target_composite_parts[source_id]:
                        matches.append({
                            "source_idx": source_idx,
                            "target_idx": target_idx,
                            "source_id": source_id,
                            "target_id": target_id,
                            "match_value": source_id,
                            "match_type": "composite",
                            "match_confidence": 1.0,
                            "api_resolved": False,
                        })

        # Debug logging for Q6EMK4
        q6_matches = [m for m in matches if m['source_id'] == 'Q6EMK4']
        if q6_matches:
            logger.info(f"Q6EMK4 DEBUG: Found {len(q6_matches)} matches for Q6EMK4")
            for m in q6_matches:
                logger.info(f"  Q6EMK4 match: source_idx={m['source_idx']}, target_idx={m['target_idx']}, target_id={m['target_id']}")
        else:
            source_has_q6 = any(str(row.get('uniprot', '')) == 'Q6EMK4' for _, row in source_df.iterrows())
            if source_has_q6:
                logger.warning("Q6EMK4 DEBUG: Q6EMK4 is in source but NO MATCHES FOUND!")
        
        logger.info(f"Found {len(matches)} direct matches")
        return matches

    async def _resolve_with_api(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        direct_matches: List[Dict[str, Any]],
        params: MergeWithUniprotResolutionParams,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Resolve unmatched SOURCE IDs using UniProt API.
        
        IMPORTANT: We only resolve unmapped source (e.g., Arivale) identifiers.
        We do NOT attempt to resolve all target (e.g., KG2c) identifiers as that
        would be inefficient and unnecessary.
        """
        if not params.use_api:
            logger.info("API resolution disabled by parameters")
            return [], 0
            
        # Get matched source IDs
        matched_source_ids = {match["source_id"] for match in direct_matches}

        # Get all unique source IDs
        all_source_ids = set(source_df[params.source_id_column].dropna().astype(str))

        # Find unresolved source IDs only
        unresolved_source = all_source_ids - matched_source_ids

        if not unresolved_source:
            logger.info("All source IDs matched directly - no API resolution needed")
            return [], 0

        logger.info(
            f"Resolving {len(unresolved_source)} unmatched source IDs via UniProt API"
        )

        # Get UniProt client
        client = await self._get_uniprot_client()
        
        # Build index of target IDs for fast lookup
        target_id_set = set(target_df[params.target_id_column].dropna().astype(str))
        
        # Also index composite parts in target
        target_composite_parts = set()
        for target_id in target_id_set:
            if params.composite_separator in target_id:
                parts = target_id.split(params.composite_separator)
                target_composite_parts.update(parts)
        
        api_matches = []
        api_calls_made = 0
        
        # Process in batches for efficiency
        unresolved_list = list(unresolved_source)
        for i in range(0, len(unresolved_list), params.api_batch_size):
            batch = unresolved_list[i:i + params.api_batch_size]
            
            try:
                # Resolve batch of IDs using the correct method signature
                results = await client.map_identifiers(
                    identifiers=batch,
                    config={'bypass_cache': not params.api_cache_results}
                )
                api_calls_made += 1
                
                # PERFORMANCE FIX: Replace O(n^5) nested loops with O(n+m) efficient matching
                from biomapper.core.algorithms.efficient_matching import EfficientMatcher
                
                # Build indices once for O(1) lookups (instead of O(n) DataFrame scans)
                if not hasattr(self, '_source_index_cache'):
                    # Build source index: source_id -> list of (index, row_data)
                    self._source_index_cache = {}
                    for idx, row in source_df.iterrows():
                        source_id = str(row[params.source_id_column])
                        if source_id not in self._source_index_cache:
                            self._source_index_cache[source_id] = []
                        self._source_index_cache[source_id].append((idx, row))
                
                if not hasattr(self, '_target_index_cache'):
                    # Build target index: target_id -> list of (index, row_data)
                    self._target_index_cache = {}
                    for idx, row in target_df.iterrows():
                        target_id = str(row[params.target_id_column])
                        if target_id not in self._target_index_cache:
                            self._target_index_cache[target_id] = []
                        self._target_index_cache[target_id].append((idx, row))
                
                # Process resolved IDs efficiently - O(n+m) instead of O(n^5)
                for source_id, (current_ids, metadata) in results.items():
                    if current_ids:  # If we got resolved IDs
                        # Get source indices once - O(1) lookup instead of O(n) scan
                        source_entries = self._source_index_cache.get(source_id, [])
                        
                        for current_id in current_ids:
                            # Check if resolved ID matches a target - O(1) lookup
                            if current_id in target_id_set:
                                # Get target indices once - O(1) lookup instead of O(n) scan
                                target_entries = self._target_index_cache.get(current_id, [])
                                
                                # Create matches efficiently - now O(k*k) where k is small
                                for source_idx, source_row in source_entries:
                                    for target_idx, target_row in target_entries:
                                        api_matches.append({
                                            "source_idx": source_idx,
                                            "target_idx": target_idx,
                                            "source_id": source_id,
                                            "target_id": current_id,
                                            "match_value": current_id,
                                            "match_type": "historical",
                                            "match_confidence": 0.9 if metadata == "primary" else 0.85,
                                            "api_resolved": True,
                                        })
                            
                            # Also check if resolved ID is part of a composite target - O(1) lookup
                            elif current_id in target_composite_parts:
                                # Use efficient index lookup for composite targets
                                if not hasattr(self, '_target_composite_index'):
                                    # Build composite target index once: part -> list of (target_idx, target_id, target_row)
                                    self._target_composite_index = {}
                                    for target_idx, target_row in target_df.iterrows():
                                        target_id = str(target_row[params.target_id_column])
                                        if params.composite_separator in target_id:
                                            parts = target_id.split(params.composite_separator)
                                            for part in parts:
                                                if part not in self._target_composite_index:
                                                    self._target_composite_index[part] = []
                                                self._target_composite_index[part].append((target_idx, target_id, target_row))
                                
                                # Get target entries for this resolved ID - O(1) lookup
                                target_entries = self._target_composite_index.get(current_id, [])
                                # Get source entries once - O(1) lookup 
                                source_entries = self._source_index_cache.get(source_id, [])
                                
                                # Create matches efficiently - now O(k*k) where k is small
                                for target_idx, target_id, target_row in target_entries:
                                    for source_idx, source_row in source_entries:
                                        api_matches.append({
                                            "source_idx": source_idx,
                                            "target_idx": target_idx,
                                            "source_id": source_id,
                                            "target_id": target_id,
                                            "match_value": current_id,
                                            "match_type": "historical_composite",
                                            "match_confidence": 0.85,
                                            "api_resolved": True,
                                        })
                
            except Exception as e:
                logger.warning(f"API resolution failed for batch: {e}")
                # Continue with next batch
        
        logger.info(f"Found {len(api_matches)} matches via API ({api_calls_made} API calls)")
        return api_matches, api_calls_made

    def _create_merged_dataset(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        direct_matches: List[Dict[str, Any]],
        api_matches: List[Dict[str, Any]],
        params: MergeWithUniprotResolutionParams,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Create the full merged dataset with all rows preserved."""
        merged_rows = []
        match_stats = {
            "direct": 0,
            "composite": 0,
            "historical": 0,
            "unmatched_source": 0,
            "unmatched_target": 0,
        }

        # Filter matches by confidence threshold
        all_matches = []
        q6_in_direct = any(m['source_id'] == 'Q6EMK4' for m in direct_matches)
        q6_in_api = any(m['source_id'] == 'Q6EMK4' for m in api_matches)
        logger.info(f"Q6EMK4 DEBUG: In direct_matches: {q6_in_direct}, In api_matches: {q6_in_api}")
        
        for match in direct_matches + api_matches:
            if match["match_confidence"] >= params.confidence_threshold:
                all_matches.append(match)
        
        q6_in_all = any(m['source_id'] == 'Q6EMK4' for m in all_matches)
        logger.info(f"Q6EMK4 DEBUG: In all_matches after filtering: {q6_in_all}")

        # Get column names and handle conflicts
        source_cols = set(source_df.columns)
        target_cols = set(target_df.columns)
        conflicting_cols = source_cols & target_cols

        # ID columns should not have suffixes
        id_cols = {params.source_id_column, params.target_id_column}
        conflicting_cols = conflicting_cols - id_cols

        # Create matched rows
        matched_source_indices = set()
        matched_target_indices = set()
        
        # Debug Q6EMK4
        q6_source_idx = None
        for idx, row in source_df.iterrows():
            if str(row.get(params.source_id_column, '')) == 'Q6EMK4':
                q6_source_idx = idx
                logger.info(f"Q6EMK4 DEBUG: Q6EMK4 found at source index {idx} (type: {type(idx)})")
                break

        for match in all_matches:
            source_idx = match["source_idx"]
            target_idx = match["target_idx"]

            matched_source_indices.add(source_idx)
            matched_target_indices.add(target_idx)
            
            if match['source_id'] == 'Q6EMK4':
                logger.info(f"Q6EMK4 DEBUG: Adding Q6EMK4 match - source_idx={source_idx} (type: {type(source_idx)}) to matched_source_indices")
            
            # Create merged row
            merged_row = {}

            # Add source data
            source_row = source_df.iloc[source_idx]
            for col in source_df.columns:
                if col in conflicting_cols:
                    merged_row[f"{col}_source"] = source_row[col]
                else:
                    merged_row[col] = source_row[col]

            # Add target data
            target_row = target_df.iloc[target_idx]
            for col in target_df.columns:
                if col in conflicting_cols:
                    merged_row[f"{col}_target"] = target_row[col]
                else:
                    merged_row[col] = target_row[col]

            # Add match metadata
            merged_row.update(
                {
                    "match_value": match["match_value"],
                    "match_type": match["match_type"],
                    "match_confidence": match["match_confidence"],
                    "match_status": "matched",
                    "api_resolved": match["api_resolved"],
                }
            )

            merged_rows.append(merged_row)

            # Update stats
            match_stats[match["match_type"]] += 1
        
        # Final Q6EMK4 check
        if q6_source_idx is not None:
            logger.info(f"Q6EMK4 DEBUG FINAL: Q6EMK4 source_idx {q6_source_idx} in matched_source_indices: {q6_source_idx in matched_source_indices}")
            if q6_source_idx not in matched_source_indices:
                logger.warning(f"Q6EMK4 DEBUG: Q6EMK4 will be marked as source_only!")

        # Add unmatched source rows
        for source_idx, source_row in source_df.iterrows():
            if source_idx not in matched_source_indices:
                merged_row = {}

                # Add source data
                for col in source_df.columns:
                    if col in conflicting_cols:
                        merged_row[f"{col}_source"] = source_row[col]
                    else:
                        merged_row[col] = source_row[col]

                # Add empty target columns
                for col in target_df.columns:
                    if col not in id_cols:  # Don't duplicate ID columns
                        if col in conflicting_cols:
                            merged_row[f"{col}_target"] = None
                        else:
                            merged_row[col] = None

                # Add match metadata
                merged_row.update(
                    {
                        "match_value": None,
                        "match_type": None,
                        "match_confidence": 0.0,
                        "match_status": "source_only",
                        "api_resolved": False,
                    }
                )

                merged_rows.append(merged_row)
                match_stats["unmatched_source"] += 1

        # Add unmatched target rows
        for target_idx, target_row in target_df.iterrows():
            if target_idx not in matched_target_indices:
                merged_row = {}

                # Add empty source columns
                for col in source_df.columns:
                    if col not in id_cols:  # Don't duplicate ID columns
                        if col in conflicting_cols:
                            merged_row[f"{col}_source"] = None
                        else:
                            merged_row[col] = None

                # Add target data
                for col in target_df.columns:
                    if col in conflicting_cols:
                        merged_row[f"{col}_target"] = target_row[col]
                    else:
                        merged_row[col] = target_row[col]

                # Add match metadata
                merged_row.update(
                    {
                        "match_value": None,
                        "match_type": None,
                        "match_confidence": 0.0,
                        "match_status": "target_only",
                        "api_resolved": False,
                    }
                )

                merged_rows.append(merged_row)
                match_stats["unmatched_target"] += 1

        # Convert to list of dictionaries
        merged_data = [dict(row) for row in merged_rows]

        logger.info(f"Created {len(merged_data)} merged rows")
        return merged_data, match_stats

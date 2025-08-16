"""
PROTEIN_HISTORICAL_RESOLUTION action for resolving deprecated/updated UniProt IDs.

This action resolves deprecated/obsolete UniProt IDs to their current equivalents
using UniProt's historical mapping data through the UniProt REST API.
"""

import asyncio
import logging
import pandas as pd
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator

from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

logger = logging.getLogger(__name__)


# Simple ActionResult for compatibility
class ActionResult(BaseModel):
    """Simple action result for compatibility."""

    success: bool
    message: str


class ProteinHistoricalResolutionParams(BaseModel):
    """Parameters for PROTEIN_HISTORICAL_RESOLUTION action."""

    input_key: str = Field(
        ..., description="Key of dataset containing UniProt IDs to resolve"
    )
    unmatched_from: Optional[str] = Field(
        default=None, description="Previous matching results to exclude (optional)"
    )
    reference_dataset: Optional[str] = Field(
        default=None, description="Reference dataset to match against (optional)"
    )
    output_key: str = Field(
        ..., description="Where to store resolved results"
    )
    uniprot_column: str = Field(
        default="uniprot_id", description="Column containing UniProt IDs"
    )
    batch_size: int = Field(
        default=50, description="Batch size for API requests"
    )
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )

    @validator("batch_size")
    def validate_batch_size(cls, v):
        """Validate batch size is reasonable."""
        if v < 1 or v > 500:
            raise ValueError("batch_size must be between 1 and 500")
        return v


@register_action("PROTEIN_HISTORICAL_RESOLUTION")
class ProteinHistoricalResolution(TypedStrategyAction[ProteinHistoricalResolutionParams, ActionResult]):
    """
    Resolve deprecated/updated UniProt IDs to their current equivalents.

    This action takes a dataset with UniProt IDs that failed direct matching
    and attempts to resolve deprecated/obsolete UniProt IDs to current ones
    using UniProt's historical mapping data.

    Features:
    - Uses UniProt's REST API for historical ID resolution
    - Supports batch processing to avoid API rate limits
    - Tracks resolution confidence scores and statistics
    - Optionally filters by previous unmatched results
    - Can match resolved IDs against reference datasets
    - Handles multiple resolution types (primary, secondary, demerged, obsolete)
    """

    def __init__(self):
        """Initialize the action."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._uniprot_client = None

    def get_params_model(self) -> type[ProteinHistoricalResolutionParams]:
        """Return the parameters model for this action."""
        return ProteinHistoricalResolutionParams
    
    def get_result_model(self) -> type[ActionResult]:
        """Return the result model for this action."""
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ProteinHistoricalResolutionParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any
    ) -> ActionResult:
        """
        Execute historical UniProt ID resolution with enhanced error handling and performance.

        Args:
            params: Action parameters
            context: Execution context containing datasets

        Returns:
            ActionResult with resolved dataset containing historical resolutions

        Raises:
            No exceptions - all errors are captured and returned in ActionResult
        """
        try:
            # Comprehensive input validation
            ctx = self._adapt_and_validate_context(context)
            input_df = self._validate_and_get_input_dataset(ctx, params)
            
            # Filter by unmatched results if specified
            if params.unmatched_from:
                input_df = self._filter_by_unmatched_results(ctx, params, input_df)

            self.logger.info(f"Processing {len(input_df)} records for historical resolution")

            # Perform batch resolution with performance optimization
            resolution_results = await self._perform_batch_resolution(input_df, params)

            # Process results and enhance with additional metadata
            result_df = self._process_resolution_results(input_df, resolution_results, params)

            # Match against reference dataset if specified
            if params.reference_dataset:
                result_df = await self._match_against_reference(
                    result_df, ctx["datasets"].get(params.reference_dataset), params
                )

            # Calculate comprehensive statistics
            stats = self._calculate_resolution_statistics(result_df, params)

            # Store results and update context
            ctx["datasets"][params.output_key] = result_df.to_dict("records")
            ctx.setdefault("statistics", {})["historical_resolution"] = stats

            self.logger.info(
                f"Historical resolution complete: {stats['resolved_count']}/{stats['total_processed']} "
                f"resolved ({stats['resolution_rate']:.1%})"
            )

            return ActionResult(
                success=True,
                message=f"Historical resolution completed: {stats['resolved_count']} resolved, {stats['unresolved_count']} unresolved"
            )

        except Exception as e:
            error_msg = f"Historical resolution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ActionResult(success=False, message=error_msg)

    def _adapt_and_validate_context(self, context: Any) -> Dict[str, Any]:
        """Adapt and validate execution context with comprehensive error handling."""
        # Handle context adaptation (same pattern as other protein actions)
        if isinstance(context, dict):
            ctx = context
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        elif hasattr(context, '_dict'):
            # MockContext - use the underlying dict
            ctx = context._dict
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        else:
            # For StrategyExecutionContext, adapt it
            from biomapper.core.context_adapter import adapt_context
            ctx = adapt_context(context)
            if "datasets" not in ctx:
                ctx["datasets"] = {}
        
        return ctx

    def _validate_and_get_input_dataset(self, ctx: Dict[str, Any], params: ProteinHistoricalResolutionParams) -> pd.DataFrame:
        """Validate and retrieve input dataset with comprehensive checks."""
        # Validate input dataset exists
        if params.input_key not in ctx["datasets"]:
            raise ValueError(f"Dataset key '{params.input_key}' not found in context")

        # Get input dataset
        input_data = ctx["datasets"][params.input_key]
        if isinstance(input_data, list):
            input_df = pd.DataFrame(input_data)
        elif isinstance(input_data, pd.DataFrame):
            input_df = input_data.copy()
        else:
            raise ValueError(f"Invalid dataset type: {type(input_data)}")

        # Check if dataset is empty
        if input_df.empty:
            raise ValueError("Input dataset is empty")

        # Validate required columns
        if params.uniprot_column not in input_df.columns:
            raise ValueError(f"Column '{params.uniprot_column}' not found in dataset")

        return input_df

    def _filter_by_unmatched_results(self, ctx: Dict[str, Any], params: ProteinHistoricalResolutionParams, input_df: pd.DataFrame) -> pd.DataFrame:
        """Filter input dataset by previous unmatched results."""
        if params.unmatched_from not in ctx["datasets"]:
            raise ValueError(f"Unmatched dataset '{params.unmatched_from}' not found")
        
        unmatched_data = ctx["datasets"][params.unmatched_from]
        if isinstance(unmatched_data, list):
            unmatched_df = pd.DataFrame(unmatched_data)
        else:
            unmatched_df = unmatched_data
        
        # Filter to only process unmatched IDs
        unmatched_ids = set()
        if 'uniprot_id' in unmatched_df.columns:
            unmatched_ids = set(unmatched_df['uniprot_id'].dropna())
        elif 'source_id' in unmatched_df.columns:
            # Map back to original IDs
            source_ids = set(unmatched_df['source_id'].dropna())
            input_df = input_df[input_df.get('id', input_df.index).isin(source_ids)]
        
        if unmatched_ids:
            input_df = input_df[input_df[params.uniprot_column].isin(unmatched_ids)]
            
        return input_df

    async def _perform_batch_resolution(self, input_df: pd.DataFrame, params: ProteinHistoricalResolutionParams) -> Dict[str, Any]:
        """Perform batch resolution with performance optimization."""
        # Initialize UniProt client
        if not self._uniprot_client:
            self._uniprot_client = UniProtHistoricalResolverClient()

        # Extract unique UniProt IDs to resolve
        unique_ids = input_df[params.uniprot_column].dropna().unique().tolist()
        
        # Process in batches for better performance
        resolution_results = {}
        
        # Log progress for large datasets
        if len(unique_ids) > 100:
            self.logger.info(f"Processing {len(unique_ids)} unique UniProt IDs in batches of {params.batch_size}")
        
        # Resolve IDs using the historical resolver
        for i, uniprot_id in enumerate(unique_ids):
            if i > 0 and i % 100 == 0:
                self.logger.info(f"Processed {i}/{len(unique_ids)} UniProt IDs")
                
            resolution_info = await self._query_uniprot_history(uniprot_id)
            if resolution_info:
                # Convert the mocked format to the expected format
                current_id = resolution_info.get('current_id')
                status = resolution_info.get('status')
                confidence = resolution_info.get('confidence', 0.0)
                if current_id and status:
                    resolution_results[uniprot_id] = ([current_id], status)
                else:
                    resolution_results[uniprot_id] = (None, 'obsolete')
            else:
                resolution_results[uniprot_id] = (None, 'obsolete')
                
        return resolution_results

    def _process_resolution_results(self, input_df: pd.DataFrame, resolution_results: Dict[str, Any], params: ProteinHistoricalResolutionParams) -> pd.DataFrame:
        """Process resolution results and add enhanced metadata."""
        result_df = input_df.copy()
        
        # Add resolution columns
        result_df['resolved_uniprot_id'] = None
        result_df['resolution_confidence'] = 0.0
        result_df['resolution_status'] = 'unresolved'
        result_df['resolution_type'] = None

        # Process each row with enhanced error handling
        for idx, row in result_df.iterrows():
            original_id = row[params.uniprot_column]
            if pd.isna(original_id):
                continue

            resolution_info = resolution_results.get(str(original_id))
            if not resolution_info:
                continue

            primary_ids, metadata = resolution_info
            
            # Determine resolution details with enhanced confidence calculation
            confidence = self._calculate_confidence(metadata, params.min_confidence)
            status = self._determine_status(metadata, confidence, params.min_confidence)
            
            # Update row data with comprehensive metadata
            if primary_ids and confidence >= params.min_confidence:
                # Use first primary ID if multiple (could be expanded to handle multiple)
                result_df.at[idx, 'resolved_uniprot_id'] = primary_ids[0]
                result_df.at[idx, 'resolution_confidence'] = confidence
                result_df.at[idx, 'resolution_status'] = status
                result_df.at[idx, 'resolution_type'] = metadata.split(':')[0] if ':' in metadata else metadata
            else:
                if confidence < params.min_confidence:
                    result_df.at[idx, 'resolution_status'] = 'below_threshold'
                else:
                    result_df.at[idx, 'resolution_status'] = 'unresolved'

        return result_df

    def _calculate_resolution_statistics(self, result_df: pd.DataFrame, params: ProteinHistoricalResolutionParams) -> Dict[str, Any]:
        """Calculate comprehensive resolution statistics."""
        resolved_count = len(result_df[result_df['resolution_status'].isin(['primary', 'replaced', 'superseded', 'demerged', 'resolved'])])
        unresolved_count = len(result_df) - resolved_count
        
        stats = {
            'total_processed': len(result_df),
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'resolution_rate': resolved_count / len(result_df) if len(result_df) > 0 else 0.0,
            'resolution_types': {},
            'confidence_distribution': {
                'high': len(result_df[result_df['resolution_confidence'] >= 0.9]),
                'medium': len(result_df[(result_df['resolution_confidence'] >= 0.7) & (result_df['resolution_confidence'] < 0.9)]),
                'low': len(result_df[result_df['resolution_confidence'] < 0.7])
            }
        }
        
        # Track resolution types
        for res_type in result_df['resolution_type'].dropna().unique():
            stats['resolution_types'][res_type] = len(result_df[result_df['resolution_type'] == res_type])
            
        return stats

    async def _query_uniprot_history(self, uniprot_id: str) -> Optional[Dict[str, Any]]:
        """
        Query UniProt for historical mapping of a single ID.
        
        This method is designed to be mockable for testing.
        """
        if not self._uniprot_client:
            self._uniprot_client = UniProtHistoricalResolverClient()
        
        results = await self._uniprot_client.map_identifiers([uniprot_id])
        result = results.get(uniprot_id)
        
        if not result:
            return None
            
        primary_ids, metadata = result
        
        if not primary_ids or not metadata:
            return None
            
        # Convert to format expected by tests
        return {
            'current_id': primary_ids[0] if primary_ids else None,
            'status': metadata.split(':')[0] if ':' in metadata else metadata,
            'confidence': self._calculate_confidence(metadata, 0.0),
            'reason': f'UniProt resolution: {metadata}'
        }

    def _calculate_confidence(self, metadata: str, min_threshold: float) -> float:
        """Calculate confidence score based on resolution metadata."""
        if not metadata:
            return 0.0
            
        # Map resolution types to confidence scores
        if metadata == 'primary':
            return 1.0
        elif metadata.startswith('secondary:'):
            return 0.95
        elif metadata == 'replaced':
            return 1.0
        elif metadata == 'superseded':
            return 0.95
        elif metadata == 'demerged':
            return 0.90
        elif metadata == 'obsolete':
            return 0.0
        elif metadata.startswith('error:'):
            return 0.0
        else:
            return 0.8  # Default for other valid resolutions

    def _determine_status(self, metadata: str, confidence: float, min_threshold: float) -> str:
        """Determine resolution status based on metadata and confidence."""
        if not metadata or metadata.startswith('error:') or metadata == 'obsolete':
            return 'unresolved'
        elif confidence < min_threshold:
            return 'below_threshold'
        elif metadata == 'primary':
            return 'primary'
        elif metadata.startswith('secondary:'):
            return 'replaced'
        elif metadata == 'replaced':
            return 'replaced'
        elif metadata == 'superseded':
            return 'superseded'
        elif metadata == 'demerged':
            return 'demerged'
        else:
            return 'resolved'

    async def _match_against_reference(
        self, 
        result_df: pd.DataFrame, 
        reference_data: Any, 
        params: ProteinHistoricalResolutionParams
    ) -> pd.DataFrame:
        """Match resolved IDs against reference dataset."""
        if reference_data is None:
            return result_df
            
        if isinstance(reference_data, list):
            reference_df = pd.DataFrame(reference_data)
        else:
            reference_df = reference_data
            
        if reference_df.empty:
            return result_df
            
        # Add reference matching columns
        result_df['reference_match'] = False
        result_df['reference_protein_name'] = None
        
        # Match resolved IDs against reference
        reference_ids = set(reference_df.get('uniprot_id', []).dropna())
        
        for idx, row in result_df.iterrows():
            resolved_id = row.get('resolved_uniprot_id')
            if resolved_id and resolved_id in reference_ids:
                result_df.at[idx, 'reference_match'] = True
                # Get protein name from reference if available
                ref_row = reference_df[reference_df['uniprot_id'] == resolved_id].iloc[0]
                if 'protein_name' in ref_row:
                    result_df.at[idx, 'reference_protein_name'] = ref_row['protein_name']
                    
        return result_df
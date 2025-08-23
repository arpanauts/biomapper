"""
Filter unmatched entities after a mapping stage.
This action identifies entities that didn't get matched in a previous stage.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import logging
from pydantic import BaseModel, Field

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class ActionResult(BaseModel):
    """Standard action result."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class FilterUnmatchedParams(BaseModel):
    """Parameters for filtering unmatched entities."""
    
    all_entities_key: str = Field(
        ...,
        description="Dataset key containing all original entities"
    )
    matched_entities_key: str = Field(
        ...,
        description="Dataset key containing matched entities from previous stage"
    )
    entity_id_column: str = Field(
        "uniprot",
        description="Column name for entity identifier"
    )
    output_key: str = Field(
        ...,
        description="Output dataset key for unmatched entities"
    )


@register_action("FILTER_UNMATCHED")
class FilterUnmatchedAction(TypedStrategyAction[FilterUnmatchedParams, ActionResult]):
    """
    Filter entities that didn't match in a previous stage.
    Essential for proper progressive/waterfall mapping.
    """
    
    def get_params_model(self) -> type[FilterUnmatchedParams]:
        return FilterUnmatchedParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self, params: FilterUnmatchedParams, context: Any, **kwargs
    ) -> ActionResult:
        """Execute the filter unmatched action."""
        try:
            # Get context
            ctx = UniversalContext.wrap(context)
            
            # Get datasets from context
            datasets = ctx.get('datasets', {})
            
            # Get all entities dataset
            all_entities = datasets.get(params.all_entities_key)
            if all_entities is None:
                return ActionResult(
                    success=False,
                    error=f"Dataset '{params.all_entities_key}' not found in context"
                )
            
            # Convert to DataFrame if needed
            if isinstance(all_entities, list):
                all_df = pd.DataFrame(all_entities)
            else:
                all_df = all_entities
            
            # Get matched entities dataset
            matched_entities = datasets.get(params.matched_entities_key)
            if matched_entities is None:
                # No matches yet, all are unmatched
                unmatched_df = all_df.copy()
            else:
                # Convert to DataFrame if needed
                if isinstance(matched_entities, list):
                    matched_df = pd.DataFrame(matched_entities)
                else:
                    matched_df = matched_entities
                
                # Get unique matched entity IDs
                matched_ids = set(matched_df[params.entity_id_column].dropna().unique())
                logger.info(f"Found {len(matched_ids)} unique matched entities")
                
                # Filter for unmatched entities
                unmatched_df = all_df[~all_df[params.entity_id_column].isin(matched_ids)].copy()
            
            logger.info(
                f"Filtered {len(all_df)} total entities -> "
                f"{len(unmatched_df)} unmatched entities"
            )
            
            # Store unmatched entities
            datasets[params.output_key] = unmatched_df
            ctx.set('datasets', datasets)
            
            return ActionResult(
                success=True,
                message=f"Identified {len(unmatched_df)} unmatched entities",
                data={
                    "total_entities": len(all_df),
                    "unmatched_count": len(unmatched_df),
                    "match_rate": 1 - (len(unmatched_df) / len(all_df)) if len(all_df) > 0 else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error filtering unmatched entities: {e}", exc_info=True)
            return ActionResult(
                success=False,
                error=str(e)
            )
"""PROTEIN_HISTORICAL_RESOLUTION action for resolving deprecated/obsolete UniProt IDs.

This action uses the UniProt REST API to resolve:
1. Secondary accessions to primary IDs
2. Demerged accessions (one ID split into multiple)
3. Obsolete/deleted accessions

Integrates with the progressive mapping framework for Stage 3 resolution.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class ProteinHistoricalResolutionParams(BaseModel):
    """Parameters for PROTEIN_HISTORICAL_RESOLUTION action."""
    
    input_key: str = Field(..., description="Dataset key containing unmapped proteins")
    output_key: str = Field(..., description="Where to store resolved proteins")
    id_column: str = Field(default="uniprot", description="Column containing UniProt IDs")
    
    # Confidence scoring
    confidence_scores: Dict[str, float] = Field(
        default={
            "primary": 1.0,
            "secondary": 0.90,
            "demerged": 0.85,
            "obsolete": 0.0
        },
        description="Confidence scores for different resolution types"
    )
    
    # Processing options
    batch_size: int = Field(default=50, description="Batch size for API calls")
    max_retries: int = Field(default=3, description="Maximum retries for failed API calls")
    bypass_cache: bool = Field(default=False, description="Bypass cache for fresh lookups")
    add_resolution_log: bool = Field(default=True, description="Add columns showing resolution details")
    
    # Debug options
    debug_mode: bool = Field(default=False, description="Enable detailed debug logging")


class ActionResult(BaseModel):
    """Standard action result for historical resolution."""
    
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@register_action("PROTEIN_HISTORICAL_RESOLUTION")
class ProteinHistoricalResolutionAction(
    TypedStrategyAction[ProteinHistoricalResolutionParams, ActionResult]
):
    """Resolve deprecated/obsolete UniProt IDs using the UniProt historical resolver."""
    
    def get_params_model(self) -> type[ProteinHistoricalResolutionParams]:
        return ProteinHistoricalResolutionParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self, params: ProteinHistoricalResolutionParams, context: Any, **kwargs
    ) -> ActionResult:
        """Execute the historical resolution action."""
        
        try:
            logger.info(f"Starting PROTEIN_HISTORICAL_RESOLUTION with params: {params}")
            
            # Get context using UniversalContext
            ctx = UniversalContext.wrap(context)
            datasets = ctx.get_datasets()
            
            # Get input dataset
            if params.input_key not in datasets:
                return ActionResult(
                    success=False,
                    error=f"Dataset '{params.input_key}' not found in context"
                )
            
            input_data = datasets[params.input_key]
            
            # Convert to DataFrame
            if isinstance(input_data, list):
                input_df = pd.DataFrame(input_data)
            else:
                input_df = input_data
            
            if input_df.empty:
                logger.info("No unmapped proteins to resolve")
                datasets[params.output_key] = input_df
                ctx.set("datasets", datasets)
                return ActionResult(
                    success=True,
                    message="No proteins to resolve",
                    data={"resolved_count": 0}
                )
            
            # Get unique IDs to resolve
            unique_ids = input_df[params.id_column].dropna().unique().tolist()
            logger.info(f"Attempting to resolve {len(unique_ids)} unmapped proteins")
            
            if params.debug_mode:
                logger.debug(f"IDs to resolve: {unique_ids}")
            
            # Import the historical resolver client
            from integrations.clients.uniprot_historical_resolver_client import (
                UniProtHistoricalResolverClient
            )
            
            # Initialize client
            client = UniProtHistoricalResolverClient()
            
            # Resolve identifiers
            resolution_config = {"bypass_cache": params.bypass_cache} if params.bypass_cache else None
            resolution_results = await client.map_identifiers(unique_ids, config=resolution_config)
            
            # Process results
            resolved_rows = []
            stats = {
                "total_input": len(unique_ids),
                "resolved_primary": 0,
                "resolved_secondary": 0,
                "resolved_demerged": 0,
                "unresolved_obsolete": 0,
                "errors": 0
            }
            
            for _, row in input_df.iterrows():
                protein_id = row[params.id_column]
                
                if pd.isna(protein_id) or protein_id not in resolution_results:
                    # Keep unresolved row as-is
                    resolved_rows.append(row.to_dict())
                    continue
                
                primary_ids, metadata = resolution_results[protein_id]
                
                if primary_ids:
                    # Successfully resolved
                    if metadata == "primary":
                        # Already was primary (shouldn't happen for unmapped)
                        stats["resolved_primary"] += 1
                        confidence = params.confidence_scores.get("primary", 1.0)
                        resolution_type = "primary"
                    elif metadata.startswith("secondary:"):
                        # Secondary accession resolved to primary
                        stats["resolved_secondary"] += 1
                        confidence = params.confidence_scores.get("secondary", 0.90)
                        resolution_type = "secondary"
                    elif metadata == "demerged":
                        # Demerged ID (maps to multiple primaries)
                        stats["resolved_demerged"] += 1
                        confidence = params.confidence_scores.get("demerged", 0.85)
                        resolution_type = "demerged"
                    else:
                        # Other resolution type
                        confidence = 0.80
                        resolution_type = "other"
                    
                    # Create row(s) for resolved ID(s)
                    for primary_id in primary_ids:
                        resolved_row = row.to_dict()
                        
                        # Store original ID if adding resolution log
                        if params.add_resolution_log:
                            resolved_row[f"{params.id_column}_original"] = protein_id
                            resolved_row[f"{params.id_column}_resolution_type"] = resolution_type
                            resolved_row[f"{params.id_column}_resolution_metadata"] = metadata
                        
                        # Update with resolved ID
                        resolved_row[params.id_column] = primary_id
                        resolved_row["confidence_score"] = confidence
                        resolved_row["match_type"] = "historical"
                        resolved_row["mapping_stage"] = 3
                        
                        resolved_rows.append(resolved_row)
                    
                    if params.debug_mode:
                        logger.debug(f"Resolved {protein_id} → {primary_ids} ({metadata})")
                        
                else:
                    # Could not resolve (obsolete or error)
                    if metadata == "obsolete":
                        stats["unresolved_obsolete"] += 1
                    elif metadata.startswith("error:"):
                        stats["errors"] += 1
                    
                    # Keep unresolved row
                    unresolved_row = row.to_dict()
                    if params.add_resolution_log:
                        unresolved_row[f"{params.id_column}_resolution_metadata"] = metadata
                    resolved_rows.append(unresolved_row)
                    
                    if params.debug_mode:
                        logger.debug(f"Could not resolve {protein_id}: {metadata}")
            
            # Create output DataFrame
            output_df = pd.DataFrame(resolved_rows)
            
            # Store results
            datasets[params.output_key] = output_df.to_dict("records")
            ctx.set("datasets", datasets)
            
            # Update statistics
            statistics = ctx.get_statistics()
            if "historical_resolution_stats" not in statistics:
                statistics["historical_resolution_stats"] = {}
            statistics["historical_resolution_stats"].update(stats)
            ctx.set("statistics", statistics)
            
            # Calculate totals
            total_resolved = (
                stats["resolved_primary"] + 
                stats["resolved_secondary"] + 
                stats["resolved_demerged"]
            )
            
            logger.info(
                f"Historical resolution complete: {total_resolved}/{stats['total_input']} resolved "
                f"(secondary: {stats['resolved_secondary']}, "
                f"demerged: {stats['resolved_demerged']}, "
                f"obsolete: {stats['unresolved_obsolete']})"
            )
            
            return ActionResult(
                success=True,
                message=f"Resolved {total_resolved} proteins via historical API",
                data={
                    "input_count": stats["total_input"],
                    "resolved_count": total_resolved,
                    "statistics": stats,
                    "output_key": params.output_key
                }
            )
            
        except ImportError as e:
            logger.error(f"Failed to import UniProtHistoricalResolverClient: {e}")
            return ActionResult(
                success=False,
                error=f"UniProt historical client not available: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error in historical resolution: {e}", exc_info=True)
            return ActionResult(
                success=False,
                error=str(e)
            )
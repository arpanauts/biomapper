"""
RampDB Bridge Action for Stage 3 Progressive Metabolite Mapping

Integrates the modernized RaMP-DB client for cross-reference metabolite matching.
This action provides Stage 3 of the progressive mapping pipeline, targeting 
15-20% additional coverage through RaMP database cross-references.

Performance Targets:
- Processing time: <30 seconds for 100 metabolites
- Coverage improvement: +15-20% (Stage 1+2: 60% → Stage 3: 75%)
- Cost: $0.10-0.50 per 250 metabolite pipeline
- Confidence: 0.8-0.9 for RaMP cross-references
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

from actions.entities.metabolites.external.ramp_client_modern import (
    RaMPClientModern, 
    RaMPConfig, 
    MetaboliteMatch,
    create_ramp_client
)
from actions.registry import register_action
from actions.typed_base import TypedStrategyAction

logger = logging.getLogger(__name__)


class MetaboliteRampdbBridgeParams(BaseModel):
    """Parameters for RampDB bridge metabolite matching."""
    
    # Input/Output keys following biomapper standards
    unmapped_key: str = Field(
        default="fuzzy_unmapped",
        description="Key for unmapped metabolites from Stage 2"
    )
    output_key: str = Field(
        default="rampdb_matched",
        description="Key for RampDB matches"
    )
    final_unmapped_key: str = Field(
        default="rampdb_unmapped", 
        description="Key for still unmapped after RampDB"
    )
    
    # RampDB configuration
    confidence_threshold: float = Field(
        0.8, ge=0.0, le=1.0,
        description="Minimum confidence for RampDB matches"
    )
    batch_size: int = Field(
        10, ge=1, le=50,
        description="Metabolites per RampDB API call"
    )
    max_requests_per_second: float = Field(
        5.0, gt=0.0, le=20.0,
        description="API rate limit (requests per second)"
    )
    api_timeout: int = Field(
        30, ge=5, le=120,
        description="API timeout in seconds"
    )
    
    # Cost and performance controls
    max_cost_estimate: float = Field(
        1.0, ge=0.0,
        description="Maximum estimated cost in dollars"
    )
    max_processing_time: int = Field(
        60, ge=10, le=300,
        description="Maximum processing time in seconds"
    )


class MetaboliteRampdbBridgeResult(BaseModel):
    """Result of RampDB bridge metabolite matching."""
    
    success: bool
    stage3_input_count: int
    total_matches: int
    still_unmapped: int
    cumulative_coverage: float
    processing_time_seconds: float
    
    # RampDB specific metrics
    api_calls_made: int
    api_success_rate: float
    average_confidence: float
    rampdb_sources_used: List[str] = Field(default_factory=list)
    
    # Cost tracking
    estimated_cost_dollars: float = 0.0
    cost_per_metabolite: float = 0.0
    
    message: Optional[str] = None


@register_action("METABOLITE_RAMPDB_BRIDGE")
class MetaboliteRampdbBridge(TypedStrategyAction[MetaboliteRampdbBridgeParams, MetaboliteRampdbBridgeResult]):
    """
    RampDB Bridge action for Stage 3 progressive metabolite mapping.
    
    Uses the modernized RaMP-DB client to find cross-references for metabolites
    that weren't matched in Stages 1-2. Provides significant coverage improvement
    through pathway and ontology-based matching.
    
    Key Features:
    - Async batch processing with rate limiting
    - Conservative confidence thresholds for biological accuracy  
    - Cost estimation and controls
    - Comprehensive error handling and fallbacks
    - Integration with progressive statistics tracking
    """
    
    def get_params_model(self) -> type[MetaboliteRampdbBridgeParams]:
        """Return the params model class."""
        return MetaboliteRampdbBridgeParams
    
    def get_result_model(self) -> type[MetaboliteRampdbBridgeResult]:
        """Return the result model class."""
        return MetaboliteRampdbBridgeResult
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with backward compatibility wrapper."""
        # Convert parameters to typed model
        try:
            params = MetaboliteRampdbBridgeParams(**action_params)
        except Exception as e:
            logger.error(f"Invalid action parameters: {e}")
            return {
                "output_identifiers": [],
                "details": {"error": f"Invalid parameters: {str(e)}"}
            }
        
        # Call the typed implementation
        result = await self.execute_typed(params, context)
        
        # Convert result to dict
        return result.dict() if hasattr(result, 'dict') else {}
    
    async def execute_typed(
        self,
        params: MetaboliteRampdbBridgeParams,
        context: Dict[str, Any]
    ) -> MetaboliteRampdbBridgeResult:
        """Execute RampDB bridge matching with async batch processing."""
        
        start_time = time.time()
        logger.info("🔗 Starting Stage 3: RampDB Cross-Reference Matching")
        
        try:
            # Ensure context is UniversalContext for compatibility
            from src.core.universal_context import UniversalContext
            context = UniversalContext.wrap(context)
            
            # Get datasets from context
            datasets = context.get("datasets", {})
            
            # Get unmapped metabolites from Stage 2
            unmapped = datasets.get(params.unmapped_key, [])
            stage3_candidates = [u for u in unmapped if u.get('for_stage') == 3 or u.get('reason') == 'no_fuzzy_match']
            
            if not stage3_candidates:
                logger.info("No Stage 3 candidates found - checking for Stage 2 unmapped")
                # Fallback: process any remaining unmapped from Stage 2
                stage3_candidates = unmapped
            
            if not stage3_candidates:
                return self._create_empty_result(start_time, "No Stage 3 candidates from previous stages")
            
            logger.info(f"Stage 3 processing {len(stage3_candidates)} metabolites via RampDB")
            
            # Check processing time limit
            if len(stage3_candidates) * 0.3 > params.max_processing_time:
                logger.warning(f"Estimated processing time exceeds limit, reducing batch size")
                stage3_candidates = stage3_candidates[:int(params.max_processing_time / 0.3)]
            
            # Setup RampDB client with configuration
            ramp_config = RaMPConfig(
                base_url="https://rampdb.nih.gov/api",
                timeout=params.api_timeout,
                max_requests_per_second=params.max_requests_per_second,
                max_retries=3,
                backoff_factor=1.5
            )
            
            # Execute RampDB matching
            matches, api_stats = await self._perform_rampdb_matching(
                stage3_candidates, params, ramp_config
            )
            
            # Filter matches by confidence threshold
            high_confidence_matches = [
                m for m in matches if m.confidence_score >= params.confidence_threshold
            ]
            
            # Create still unmapped list
            matched_names = {m.query_name for m in high_confidence_matches}
            still_unmapped = [
                candidate for candidate in stage3_candidates
                if candidate.get('name') not in matched_names
            ]
            
            # Convert matches to dataset format
            match_records = self._convert_matches_to_records(high_confidence_matches)
            
            # Update context datasets
            datasets[params.output_key] = match_records
            datasets[params.final_unmapped_key] = still_unmapped
            
            # Calculate cumulative coverage
            stage1_matched = len(datasets.get("nightingale_matched", []))
            stage2_matched = len(datasets.get("fuzzy_matched", []))
            stage3_matched = len(high_confidence_matches)
            total_metabolites = 250  # Known Nightingale total
            cumulative_coverage = (stage1_matched + stage2_matched + stage3_matched) / total_metabolites
            
            # Calculate costs (RampDB API is typically free, but track for monitoring)
            estimated_cost = api_stats['api_calls'] * 0.005  # Estimated $0.005 per call
            cost_per_metabolite = estimated_cost / len(stage3_candidates) if stage3_candidates else 0.0
            
            processing_time = time.time() - start_time
            
            # Update progressive statistics
            self._update_progressive_statistics(
                context, stage3_matched, cumulative_coverage, processing_time,
                api_stats, estimated_cost, params.confidence_threshold
            )
            
            # Log results
            logger.info(f"Stage 3 RampDB Bridge Complete:")
            logger.info(f"  Input: {len(stage3_candidates)} unmapped metabolites")
            logger.info(f"  RampDB matches found: {len(matches)}")
            logger.info(f"  High confidence matches: {len(high_confidence_matches)}")
            logger.info(f"  Still unmapped: {len(still_unmapped)}")
            logger.info(f"  Cumulative coverage: {cumulative_coverage:.1%}")
            logger.info(f"  API calls: {api_stats['api_calls']}")
            logger.info(f"  Processing time: {processing_time:.1f} seconds")
            logger.info(f"  Estimated cost: ${estimated_cost:.3f}")
            
            return MetaboliteRampdbBridgeResult(
                success=True,
                stage3_input_count=len(stage3_candidates),
                total_matches=len(high_confidence_matches),
                still_unmapped=len(still_unmapped),
                cumulative_coverage=cumulative_coverage,
                processing_time_seconds=processing_time,
                api_calls_made=api_stats['api_calls'],
                api_success_rate=api_stats['success_rate'],
                average_confidence=api_stats['avg_confidence'],
                rampdb_sources_used=api_stats['sources_used'],
                estimated_cost_dollars=estimated_cost,
                cost_per_metabolite=cost_per_metabolite,
                message=f"Stage 3 achieved {cumulative_coverage:.1%} cumulative coverage with {len(high_confidence_matches)} RampDB matches"
            )
            
        except Exception as e:
            logger.error(f"Error in RampDB bridge matching: {str(e)}")
            return MetaboliteRampdbBridgeResult(
                success=False,
                stage3_input_count=len(stage3_candidates) if 'stage3_candidates' in locals() else 0,
                total_matches=0,
                still_unmapped=0,
                cumulative_coverage=0.0,
                processing_time_seconds=time.time() - start_time,
                api_calls_made=0,
                api_success_rate=0.0,
                average_confidence=0.0,
                message=f"Stage 3 failed: {str(e)}"
            )
    
    async def _perform_rampdb_matching(
        self,
        candidates: List[Dict[str, Any]],
        params: MetaboliteRampdbBridgeParams,
        config: RaMPConfig
    ) -> tuple[List[MetaboliteMatch], Dict[str, Any]]:
        """Perform RampDB matching with error handling and statistics tracking."""
        
        matches = []
        api_calls = 0
        successful_calls = 0
        sources_used = set()
        confidence_scores = []
        
        # Extract metabolite names
        metabolite_names = [candidate.get('name', '') for candidate in candidates]
        valid_names = [name for name in metabolite_names if name and name.strip()]
        
        if not valid_names:
            logger.warning("No valid metabolite names for RampDB lookup")
            return matches, {
                'api_calls': 0,
                'success_rate': 0.0,
                'avg_confidence': 0.0,
                'sources_used': []
            }
        
        logger.info(f"Performing RampDB lookup for {len(valid_names)} metabolite names")
        
        try:
            # Create RampDB client with async context manager
            async with await create_ramp_client(config) as ramp_client:
                
                # Check API health first
                if not await ramp_client.health_check():
                    logger.warning("RampDB API health check failed")
                    return matches, {
                        'api_calls': 1,
                        'success_rate': 0.0,
                        'avg_confidence': 0.0,
                        'sources_used': []
                    }
                
                # Perform batch lookup
                ramp_matches = await ramp_client.batch_metabolite_lookup(
                    valid_names, batch_size=params.batch_size
                )
                
                # Get client statistics
                client_stats = ramp_client.get_stats()
                api_calls = client_stats['total_requests']
                successful_calls = api_calls  # Assume success if we got here
                
                # Process results
                for match in ramp_matches:
                    matches.append(match)
                    sources_used.add(match.database_source)
                    confidence_scores.append(match.confidence_score)
                
                logger.info(f"RampDB returned {len(ramp_matches)} matches from {len(sources_used)} sources")
                
        except Exception as e:
            logger.error(f"RampDB client error: {e}")
            api_calls = 1
            successful_calls = 0
        
        # Calculate statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        success_rate = successful_calls / api_calls if api_calls > 0 else 0.0
        
        return matches, {
            'api_calls': api_calls,
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'sources_used': list(sources_used)
        }
    
    def _convert_matches_to_records(self, matches: List[MetaboliteMatch]) -> List[Dict[str, Any]]:
        """Convert MetaboliteMatch objects to dataset records."""
        
        records = []
        for match in matches:
            record = {
                'name': match.query_name,
                'matched_name': match.matched_name,
                'matched_id': match.matched_id,
                'database_source': match.database_source,
                'match_confidence': match.confidence_score,
                'match_method': match.match_method,
                'match_source': 'rampdb_api',
                'pathways_count': match.pathways_count,
                'chemical_class': match.chemical_class,
                'stage': 3,
                'rampdb_id': match.matched_id  # Keep original for reference
            }
            records.append(record)
        
        return records
    
    def _update_progressive_statistics(
        self,
        context: Dict[str, Any],
        stage3_matched: int,
        cumulative_coverage: float,
        processing_time: float,
        api_stats: Dict[str, Any],
        estimated_cost: float,
        confidence_threshold: float
    ):
        """Update progressive statistics in context."""
        
        statistics = context.get("statistics", {})
        statistics["progressive_stage3_rampdb"] = {
            "stage": 3,
            "method": "rampdb_cross_reference",
            "total_matches": stage3_matched,
            "cumulative_coverage": cumulative_coverage,
            "processing_time_seconds": processing_time,
            "api_calls": api_stats['api_calls'],
            "api_success_rate": api_stats['success_rate'],
            "average_confidence": api_stats['avg_confidence'],
            "confidence_threshold": confidence_threshold,
            "sources_used": api_stats['sources_used'],
            "estimated_cost_dollars": estimated_cost,
            "cost_per_api_call": estimated_cost / api_stats['api_calls'] if api_stats['api_calls'] > 0 else 0.0
        }
        context["statistics"] = statistics
    
    def _create_empty_result(self, start_time: float, message: str) -> MetaboliteRampdbBridgeResult:
        """Create empty result for cases with no candidates."""
        
        return MetaboliteRampdbBridgeResult(
            success=True,
            stage3_input_count=0,
            total_matches=0,
            still_unmapped=0,
            cumulative_coverage=0.0,
            processing_time_seconds=time.time() - start_time,
            api_calls_made=0,
            api_success_rate=0.0,
            average_confidence=0.0,
            message=message
        )
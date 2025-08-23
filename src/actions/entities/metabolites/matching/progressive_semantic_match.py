"""
PROGRESSIVE_SEMANTIC_MATCH wrapper for Stage 2 of progressive metabolite mapping.
Wraps SEMANTIC_METABOLITE_MATCH with conservative thresholds for biological accuracy.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from actions.semantic_metabolite_match import (
    SemanticMetaboliteMatchAction,
    SemanticMetaboliteMatchParams,
)

logger = logging.getLogger(__name__)


class ProgressiveSemanticMatchParams(BaseModel):
    """Parameters for progressive semantic matching wrapper."""
    
    # Input/Output keys
    unmapped_key: str = Field(
        default="nightingale_unmapped",
        description="Key for unmapped metabolites from Stage 1"
    )
    reference_key: str = Field(
        default="reference_metabolites",
        description="Key for reference metabolites to match against"
    )
    output_key: str = Field(
        default="semantic_matched",
        description="Key for semantic matches"
    )
    final_unmapped_key: str = Field(
        default="semantic_unmapped",
        description="Key for still unmapped after semantic matching"
    )
    
    # Conservative thresholds for biological accuracy
    confidence_threshold: float = Field(
        0.85,  # Higher than default 0.75 for accuracy
        ge=0.0, le=1.0,
        description="Minimum LLM confidence for accepting matches"
    )
    embedding_similarity_threshold: float = Field(
        0.90,  # Higher than default 0.85 for accuracy
        ge=0.0, le=1.0,
        description="Minimum embedding similarity for LLM validation"
    )
    
    # Cost control
    max_llm_calls: int = Field(
        50,  # Conservative limit for Stage 2
        description="Maximum LLM API calls to prevent costs"
    )
    
    # Fallback options
    enable_fuzzy_fallback: bool = Field(
        True,
        description="Enable fuzzy matching for metabolites without API access"
    )
    fuzzy_threshold: float = Field(
        0.85,  # High threshold for fuzzy matching
        ge=0.0, le=1.0,
        description="Minimum fuzzy match score"
    )
    
    # Caching
    cache_dir: Optional[str] = Field(
        "/home/ubuntu/biomapper/cache/semantic_embeddings",
        description="Directory for embedding cache"
    )
    
    # Context fields for semantic matching
    context_fields: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "nightingale": ["name", "original_name", "csv_name"],
            "reference": ["name", "description", "synonyms", "category"]
        },
        description="Fields to use for context per dataset"
    )


class ProgressiveSemanticMatchResult(BaseModel):
    """Result of progressive semantic matching."""
    
    success: bool
    stage2_input_count: int
    semantic_matched: int
    fuzzy_matched: int
    still_unmapped: int
    cumulative_coverage: float
    llm_calls_made: int
    cache_hits: int
    confidence_distribution: Dict[str, int]
    message: Optional[str] = None


@register_action("PROGRESSIVE_SEMANTIC_MATCH")
class ProgressiveSemanticMatch(TypedStrategyAction[ProgressiveSemanticMatchParams, ProgressiveSemanticMatchResult]):
    """
    Stage 2 of progressive metabolite mapping using semantic matching.
    
    This wrapper applies conservative thresholds to SEMANTIC_METABOLITE_MATCH
    to prioritize biological accuracy over coverage percentage.
    
    Key features:
    - Higher confidence thresholds (0.85+) for biological accuracy
    - Fuzzy matching fallback for non-API metabolites
    - Cost-controlled LLM usage
    - Embedding cache for efficiency
    """
    
    def get_params_model(self) -> type[ProgressiveSemanticMatchParams]:
        """Return the params model class."""
        return ProgressiveSemanticMatchParams
    
    def get_result_model(self) -> type[ProgressiveSemanticMatchResult]:
        """Return the result model class."""
        return ProgressiveSemanticMatchResult
    
    async def apply_fuzzy_fallback(
        self,
        unmapped: List[Dict[str, Any]],
        reference: List[Dict[str, Any]],
        threshold: float
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apply fuzzy matching as fallback for metabolites without semantic matching."""
        
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            from rapidfuzz import fuzz
        
        matched = []
        still_unmapped = []
        
        # Build reference name lookup
        ref_by_name = {r.get('name', '').lower(): r for r in reference}
        
        for metabolite in unmapped:
            name = metabolite.get('name', '')
            if not name:
                still_unmapped.append(metabolite)
                continue
            
            best_match = None
            best_score = 0.0
            
            # Try fuzzy matching against reference names
            for ref_name, ref_data in ref_by_name.items():
                score = fuzz.token_sort_ratio(name.lower(), ref_name) / 100.0
                
                if score > best_score and score >= threshold:
                    best_match = ref_data
                    best_score = score
            
            if best_match:
                matched.append({
                    **metabolite,
                    'matched_name': best_match.get('name'),
                    'matched_id': best_match.get('id'),
                    'match_confidence': best_score * 0.8,  # Scale down fuzzy confidence
                    'match_method': 'fuzzy_fallback',
                    'match_source': 'reference'
                })
            else:
                still_unmapped.append(metabolite)
        
        return matched, still_unmapped
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ProgressiveSemanticMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any
    ) -> ProgressiveSemanticMatchResult:
        """Execute progressive semantic matching for Stage 2."""
        
        try:
            # Get datasets from context
            datasets = context.get("datasets", {})
            
            # Get unmapped from Stage 1
            unmapped = datasets.get(params.unmapped_key, [])
            stage2_candidates = [u for u in unmapped if u.get('for_stage') == 2]
            
            if not stage2_candidates:
                return ProgressiveSemanticMatchResult(
                    success=True,
                    stage2_input_count=0,
                    semantic_matched=0,
                    fuzzy_matched=0,
                    still_unmapped=0,
                    cumulative_coverage=0.0,
                    llm_calls_made=0,
                    cache_hits=0,
                    confidence_distribution={},
                    message="No Stage 2 candidates from Stage 1"
                )
            
            # Get reference metabolites
            reference = datasets.get(params.reference_key, [])
            if not reference:
                logger.warning(f"No reference metabolites found in {params.reference_key}")
                # Could load a default reference set here
                reference = []
            
            logger.info(f"Stage 2: Processing {len(stage2_candidates)} name-only metabolites")
            
            # Set up cache directory
            import os
            if params.cache_dir:
                os.makedirs(params.cache_dir, exist_ok=True)
                os.environ["SEMANTIC_MATCH_CACHE_DIR"] = params.cache_dir
            
            # Create semantic matching params with conservative thresholds
            semantic_params = SemanticMetaboliteMatchParams(
                unmatched_dataset=params.unmapped_key + "_stage2",
                reference_map=params.reference_key,
                context_fields=params.context_fields,
                confidence_threshold=params.confidence_threshold,
                embedding_similarity_threshold=params.embedding_similarity_threshold,
                max_llm_calls=params.max_llm_calls,
                include_reasoning=True,  # Important for validation
                output_key=params.output_key + "_semantic",
                unmatched_key=params.output_key + "_semantic_unmapped"
            )
            
            # Store Stage 2 candidates temporarily
            datasets[params.unmapped_key + "_stage2"] = stage2_candidates
            
            # Execute semantic matching
            semantic_action = SemanticMetaboliteMatchAction()
            semantic_result = await semantic_action.execute_typed(
                current_identifiers=current_identifiers,
                current_ontology_type=current_ontology_type,
                params=semantic_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Get semantic results
            semantic_matched = datasets.get(params.output_key + "_semantic", [])
            semantic_unmapped = datasets.get(params.output_key + "_semantic_unmapped", [])
            
            # Apply fuzzy fallback if enabled
            fuzzy_matched = []
            if params.enable_fuzzy_fallback and semantic_unmapped:
                logger.info(f"Applying fuzzy fallback for {len(semantic_unmapped)} unmapped")
                fuzzy_matched, still_unmapped = await self.apply_fuzzy_fallback(
                    semantic_unmapped,
                    reference,
                    params.fuzzy_threshold
                )
            else:
                still_unmapped = semantic_unmapped
            
            # Combine all matches
            all_matched = semantic_matched + fuzzy_matched
            
            # Store final results
            datasets[params.output_key] = all_matched
            datasets[params.final_unmapped_key] = still_unmapped
            
            # Calculate statistics
            stage1_matched = len(datasets.get("nightingale_matched", []))
            stage2_matched = len(all_matched)
            total_metabolites = 250  # Known total from Nightingale
            cumulative_coverage = (stage1_matched + stage2_matched) / total_metabolites
            
            # Confidence distribution
            confidence_dist = {
                "high_0.9+": sum(1 for m in all_matched if m.get('match_confidence', 0) >= 0.9),
                "medium_0.85-0.9": sum(1 for m in all_matched if 0.85 <= m.get('match_confidence', 0) < 0.9),
                "low_0.8-0.85": sum(1 for m in all_matched if 0.8 <= m.get('match_confidence', 0) < 0.85),
                "fuzzy_fallback": len(fuzzy_matched)
            }
            
            # Update progressive statistics
            statistics = context.get("statistics", {})
            statistics["progressive_stage2"] = {
                "stage": 2,
                "input_count": len(stage2_candidates),
                "semantic_matched": len(semantic_matched),
                "fuzzy_matched": len(fuzzy_matched),
                "still_unmapped": len(still_unmapped),
                "cumulative_coverage": cumulative_coverage,
                "llm_calls": semantic_result.data.get("llm_calls", 0),
                "cache_hits": semantic_result.data.get("cache_hits", 0),
                "confidence_distribution": confidence_dist
            }
            context["statistics"] = statistics
            
            # Log results
            logger.info(f"Stage 2 Complete:")
            logger.info(f"  Input: {len(stage2_candidates)} name-only metabolites")
            logger.info(f"  Semantic matched: {len(semantic_matched)}")
            logger.info(f"  Fuzzy matched: {len(fuzzy_matched)}")
            logger.info(f"  Still unmapped: {len(still_unmapped)}")
            logger.info(f"  Cumulative coverage: {cumulative_coverage:.1%}")
            logger.info(f"  Confidence distribution: {confidence_dist}")
            
            return ProgressiveSemanticMatchResult(
                success=True,
                stage2_input_count=len(stage2_candidates),
                semantic_matched=len(semantic_matched),
                fuzzy_matched=len(fuzzy_matched),
                still_unmapped=len(still_unmapped),
                cumulative_coverage=cumulative_coverage,
                llm_calls_made=semantic_result.data.get("llm_calls", 0),
                cache_hits=semantic_result.data.get("cache_hits", 0),
                confidence_distribution=confidence_dist,
                message=f"Stage 2 achieved {cumulative_coverage:.1%} cumulative coverage"
            )
            
        except Exception as e:
            logger.error(f"Error in progressive semantic matching: {str(e)}")
            return ProgressiveSemanticMatchResult(
                success=False,
                stage2_input_count=0,
                semantic_matched=0,
                fuzzy_matched=0,
                still_unmapped=0,
                cumulative_coverage=0.0,
                llm_calls_made=0,
                cache_hits=0,
                confidence_distribution={},
                message=f"Error: {str(e)}"
            )
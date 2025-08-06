"""Baseline fuzzy matching action for metabolites."""

import logging
import time
from typing import Dict, Any, List, Type, Optional
from enum import Enum

from pydantic import BaseModel, Field
from thefuzz import fuzz

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction, StandardActionResult
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.execution_context import StrategyExecutionContext

logger = logging.getLogger(__name__)


class FuzzyAlgorithm(str, Enum):
    """Available fuzzy matching algorithms."""

    RATIO = "ratio"
    PARTIAL_RATIO = "partial_ratio"
    TOKEN_SORT_RATIO = "token_sort_ratio"
    TOKEN_SET_RATIO = "token_set_ratio"


class BaselineFuzzyMatchParams(BaseModel):
    """Parameters for baseline fuzzy matching."""

    source_dataset_key: str = Field(description="Key for source dataset")
    target_dataset_key: str = Field(description="Key for target dataset")
    source_column: str = Field(description="Column with source metabolite names")
    target_column: str = Field(description="Column with target metabolite names")
    threshold: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Minimum score threshold for matches"
    )
    algorithm: FuzzyAlgorithm = Field(
        default=FuzzyAlgorithm.TOKEN_SET_RATIO,
        description="Fuzzy matching algorithm to use",
    )
    output_key: str = Field(description="Key to store matched results")
    track_metrics: bool = Field(
        default=True, description="Track detailed metrics for analysis"
    )
    limit_per_source: int = Field(
        default=1, ge=1, description="Maximum matches per source item"
    )
    unmatched_key: Optional[str] = Field(
        None,
        description="Key for storing unmatched items for progressive enhancement"
    )
    metrics_key: Optional[str] = Field(
        None,
        description="Key for storing metrics in context"
    )


class MatchMetrics(BaseModel):
    """Metrics for matching performance."""

    stage: str = "baseline"
    total_source: int
    total_target: int
    matched: int
    unmatched: int
    precision: float = Field(description="To be calculated with ground truth")
    recall: float
    execution_time: float
    avg_confidence: float
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of confidence scores"
    )
    algorithm_used: str




@register_action("BASELINE_FUZZY_MATCH")
class BaselineFuzzyMatchAction(
    TypedStrategyAction[BaselineFuzzyMatchParams, StandardActionResult]
):
    """Baseline fuzzy matching for progressive enhancement comparison."""
    
    def get_params_model(self) -> Type[BaselineFuzzyMatchParams]:
        """Return the Pydantic model class for action parameters."""
        return BaselineFuzzyMatchParams
    
    def get_result_model(self) -> Type[StandardActionResult]:
        """Return the Pydantic model class for action results."""
        return StandardActionResult

    def _get_fuzzy_score(
        self, source: str, target: str, algorithm: FuzzyAlgorithm
    ) -> float:
        """Calculate fuzzy match score using specified algorithm."""
        if not source or not target:
            return 0.0

        if algorithm == FuzzyAlgorithm.RATIO:
            return fuzz.ratio(source, target) / 100.0
        elif algorithm == FuzzyAlgorithm.PARTIAL_RATIO:
            return fuzz.partial_ratio(source, target) / 100.0
        elif algorithm == FuzzyAlgorithm.TOKEN_SORT_RATIO:
            return fuzz.token_sort_ratio(source, target) / 100.0
        elif algorithm == FuzzyAlgorithm.TOKEN_SET_RATIO:
            return fuzz.token_set_ratio(source, target) / 100.0
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def _preprocess_metabolite_name(self, name: str) -> str:
        """Preprocess metabolite name for better matching.

        Handles common variations in metabolite naming:
        - Removes extra whitespace
        - Converts to lowercase for comparison
        - Handles common punctuation
        """
        if not name:
            return ""

        # Convert to lowercase and strip
        processed = name.lower().strip()

        # Replace common separators with spaces
        for sep in ["-", "_", "/", "\\"]:
            processed = processed.replace(sep, " ")

        # Remove parentheses content (often contains additional info)
        if "(" in processed and ")" in processed:
            start = processed.find("(")
            end = processed.find(")")
            if start < end:
                processed = processed[:start] + processed[end + 1 :]

        # Normalize whitespace
        processed = " ".join(processed.split())

        return processed

    def _calculate_confidence_bucket(self, score: float) -> str:
        """Categorize confidence score into buckets."""
        if score >= 0.95:
            return "very_high"
        elif score >= 0.90:
            return "high"
        elif score >= 0.85:
            return "medium"
        elif score >= 0.80:
            return "low"
        else:
            return "very_low"

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: BaselineFuzzyMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any  # Can be StrategyExecutionContext or mock context
    ) -> StandardActionResult:
        """Execute baseline fuzzy matching."""

        start_time = time.time()

        # Get datasets from context - using get_action_data method
        datasets = context.get_action_data("datasets", {})
        source_data = datasets.get(params.source_dataset_key, [])
        target_data = datasets.get(params.target_dataset_key, [])

        if not source_data:
            raise ValueError(f"Source dataset '{params.source_dataset_key}' not found")
        if not target_data:
            raise ValueError(f"Target dataset '{params.target_dataset_key}' not found")

        logger.info(
            f"Starting baseline fuzzy matching: "
            f"{len(source_data)} source items, {len(target_data)} target items, "
            f"algorithm: {params.algorithm}"
        )

        matches = []
        unmatched = []
        confidence_dist: Dict[str, int] = {}
        total_confidence = 0.0

        # Preprocess target names for efficiency
        target_processed = []
        for target_item in target_data:
            target_name = target_item.get(params.target_column, "")
            processed = self._preprocess_metabolite_name(target_name)
            target_processed.append(
                {
                    "original": target_item,
                    "processed": processed,
                    "raw_name": target_name,
                }
            )

        # Match each source item
        for source_item in source_data:
            source_name = source_item.get(params.source_column, "")
            if not source_name:
                unmatched.append(source_item)
                continue

            source_processed = self._preprocess_metabolite_name(source_name)

            # Find best matches
            candidates = []
            for target_info in target_processed:
                # Calculate score on processed names
                score = self._get_fuzzy_score(
                    source_processed, target_info["processed"], params.algorithm
                )

                if score >= params.threshold:
                    candidates.append(
                        {
                            "target": target_info["original"],
                            "score": score,
                            "target_name": target_info["raw_name"],
                        }
                    )

            # Sort by score and take top matches
            candidates.sort(key=lambda x: x["score"], reverse=True)
            candidates = candidates[: params.limit_per_source]

            if candidates:
                for candidate in candidates:
                    match_record = {
                        "source": source_item,
                        "target": candidate["target"],
                        "score": candidate["score"],
                        "method": f"fuzzy_{params.algorithm.value}",
                        "stage": "baseline",
                        "source_name": source_name,
                        "target_name": candidate["target_name"],
                        "preprocessed_source": source_processed,
                        "preprocessed_target": self._preprocess_metabolite_name(
                            candidate["target_name"]
                        ),
                    }
                    matches.append(match_record)

                    # Track confidence distribution
                    bucket = self._calculate_confidence_bucket(candidate["score"])
                    confidence_dist[bucket] = confidence_dist.get(bucket, 0) + 1
                    total_confidence += candidate["score"]
            else:
                unmatched.append(source_item)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Calculate metrics
        total_matched = len(matches)
        total_unmatched = len(unmatched)
        avg_confidence = total_confidence / total_matched if total_matched > 0 else 0.0
        recall = total_matched / len(source_data) if source_data else 0.0

        # Create metrics object
        metrics = MatchMetrics(
            stage="baseline",
            total_source=len(source_data),
            total_target=len(target_data),
            matched=total_matched,
            unmatched=total_unmatched,
            precision=0.0,  # Will be calculated with ground truth
            recall=recall,
            execution_time=execution_time,
            avg_confidence=avg_confidence,
            confidence_distribution=confidence_dist,
            algorithm_used=params.algorithm.value,
        )

        # Store results in context using set_action_data
        datasets = context.get_action_data("datasets", {})
        datasets[params.output_key] = matches
        context.set_action_data("datasets", datasets)

        # Store unmatched for next stage
        unmatched_key = params.unmatched_key or f"unmatched.baseline.{params.source_dataset_key}"
        datasets[unmatched_key] = unmatched
        context.set_action_data("datasets", datasets)

        # Store metrics if tracking
        if params.track_metrics:
            metrics_dict = context.get_action_data("metrics", {})
            metrics_key = params.metrics_key or "baseline"
            metrics_dict[metrics_key] = metrics.dict()
            context.set_action_data("metrics", metrics_dict)

        logger.info(
            f"Baseline matching complete: {total_matched} matches "
            f"({recall:.1%} recall), avg confidence: {avg_confidence:.3f}, "
            f"time: {execution_time:.2f}s"
        )

        # Return StandardActionResult
        return StandardActionResult(
            input_identifiers=current_identifiers,
            output_identifiers=[match['source_name'] for match in matches],  # Return matched source names
            output_ontology_type=current_ontology_type,
            provenance=[{
                'action': 'BASELINE_FUZZY_MATCH',
                'algorithm': params.algorithm.value,
                'matched_count': total_matched,
                'unmatched_count': total_unmatched,
                'avg_confidence': avg_confidence,
                'execution_time': execution_time
            }],
            details={
                "success": True,
                "message": f"Matched {total_matched} metabolites using {params.algorithm.value}",
                "metrics": metrics.dict(),
                "matched_count": total_matched,
                "unmatched_count": total_unmatched,
                "execution_time": execution_time,
            }
        )

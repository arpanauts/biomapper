"""Calculate mapping quality metrics for biological identifier mappings."""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import DatasetNotFoundError, MappingQualityError


class ActionResult(BaseModel):
    """Simple action result for mapping quality operations."""

    success: bool
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class QualityMetric(BaseModel):
    """Single quality metric specification."""

    name: str = Field(..., description="Name of the quality metric")
    weight: float = Field(
        default=1.0, description="Weight of this metric in overall score"
    )
    higher_is_better: bool = Field(
        default=True, description="Whether higher values indicate better quality"
    )


class CalculateMappingQualityParams(BaseModel):
    """Parameters for CALCULATE_MAPPING_QUALITY action."""

    source_key: str = Field(..., description="Key of source dataset")
    mapped_key: str = Field(..., description="Key of mapped dataset")
    output_key: str = Field(..., description="Key for quality metrics output")

    source_id_column: str = Field(
        ..., description="Column containing source identifiers"
    )
    mapped_id_column: str = Field(
        ..., description="Column containing mapped identifiers"
    )
    confidence_column: Optional[str] = Field(
        default=None, description="Column containing mapping confidence scores"
    )

    metrics_to_calculate: List[
        Literal[
            "match_rate",
            "coverage",
            "precision",
            "recall",
            "f1_score",
            "confidence_distribution",
            "duplicate_rate",
            "ambiguity_rate",
            "identifier_quality",
            "semantic_similarity",
        ]
    ] = Field(
        default=["match_rate", "coverage", "precision"],
        description="Quality metrics to calculate",
    )

    confidence_threshold: float = Field(
        default=0.8, description="Minimum confidence threshold for high-quality matches"
    )

    reference_dataset_key: Optional[str] = Field(
        default=None,
        description="Key of reference dataset for precision/recall calculation",
    )

    include_detailed_report: bool = Field(
        default=True, description="Whether to include detailed per-identifier analysis"
    )


class MappingQualityResult(ActionResult):
    """Result of CALCULATE_MAPPING_QUALITY action."""

    total_source_identifiers: int = 0
    total_mapped_identifiers: int = 0
    successful_mappings: int = 0
    failed_mappings: int = 0

    overall_quality_score: float = 0.0
    individual_metrics: Dict[str, float] = Field(default_factory=dict)
    quality_distribution: Dict[str, int] = Field(default_factory=dict)

    high_confidence_mappings: int = 0
    low_confidence_mappings: int = 0
    ambiguous_mappings: int = 0

    detailed_report: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)


@register_action("CALCULATE_MAPPING_QUALITY")
class CalculateMappingQualityAction(
    TypedStrategyAction[CalculateMappingQualityParams, MappingQualityResult]
):
    """
    Calculate comprehensive quality metrics for biological identifier mappings.

    Provides detailed analysis of mapping success rates, confidence distributions,
    and quality scores to help validate and optimize mapping strategies.
    """

    def get_params_model(self) -> type[CalculateMappingQualityParams]:
        return CalculateMappingQualityParams

    def get_result_model(self) -> type[MappingQualityResult]:
        return MappingQualityResult

    async def execute_typed(  # type: ignore[override]
        self, params: CalculateMappingQualityParams, context: Dict[str, Any]
    ) -> MappingQualityResult:
        """Calculate mapping quality metrics."""

        # Validate required datasets
        datasets = context.get("datasets", {})
        if params.source_key not in datasets:
            raise DatasetNotFoundError(
                f"Source dataset '{params.source_key}' not found"
            )
        if params.mapped_key not in datasets:
            raise DatasetNotFoundError(
                f"Mapped dataset '{params.mapped_key}' not found"
            )

        source_df = datasets[params.source_key]
        mapped_df = datasets[params.mapped_key]

        # Validate required columns
        if params.source_id_column not in source_df.columns:
            raise MappingQualityError(
                f"Source ID column '{params.source_id_column}' not found"
            )
        if params.mapped_id_column not in mapped_df.columns:
            raise MappingQualityError(
                f"Mapped ID column '{params.mapped_id_column}' not found"
            )

        # Calculate basic counts
        total_source = len(source_df)
        total_mapped = len(mapped_df)

        # Identify successful mappings (non-null mapped identifiers)
        successful_mask = (
            mapped_df[params.mapped_id_column].notna()
            & (mapped_df[params.mapped_id_column] != "")
            & (mapped_df[params.mapped_id_column] != "unknown")
        )

        successful_mappings = successful_mask.sum()
        failed_mappings = total_mapped - successful_mappings

        # Calculate individual metrics
        individual_metrics = {}

        if "match_rate" in params.metrics_to_calculate:
            individual_metrics["match_rate"] = (
                successful_mappings / total_source if total_source > 0 else 0
            )

        if "coverage" in params.metrics_to_calculate:
            individual_metrics["coverage"] = (
                successful_mappings / total_mapped if total_mapped > 0 else 0
            )

        # Calculate confidence-based metrics
        high_confidence_mappings = 0
        low_confidence_mappings = 0
        confidence_scores = []

        if params.confidence_column and params.confidence_column in mapped_df.columns:
            confidence_scores = mapped_df[params.confidence_column].dropna()
            high_confidence_mappings = (
                confidence_scores >= params.confidence_threshold
            ).sum()
            low_confidence_mappings = (
                confidence_scores < params.confidence_threshold
            ).sum()

            if "confidence_distribution" in params.metrics_to_calculate:
                individual_metrics["avg_confidence"] = confidence_scores.mean()
                individual_metrics["min_confidence"] = confidence_scores.min()
                individual_metrics["max_confidence"] = confidence_scores.max()

        # Calculate duplicate and ambiguity rates
        ambiguous_mappings = 0
        if "duplicate_rate" in params.metrics_to_calculate:
            mapped_ids = mapped_df[mapped_df[params.mapped_id_column].notna()][
                params.mapped_id_column
            ]
            duplicate_count = len(mapped_ids) - len(mapped_ids.unique())
            individual_metrics["duplicate_rate"] = (
                duplicate_count / len(mapped_ids) if len(mapped_ids) > 0 else 0
            )

        if "ambiguity_rate" in params.metrics_to_calculate:
            # Count how many source IDs map to multiple targets
            mapping_counts = mapped_df.groupby(params.source_id_column)[
                params.mapped_id_column
            ].nunique()
            ambiguous_mappings = (mapping_counts > 1).sum()
            individual_metrics["ambiguity_rate"] = (
                ambiguous_mappings / total_source if total_source > 0 else 0
            )

        # Precision and recall (if reference dataset provided)
        if params.reference_dataset_key and params.reference_dataset_key in datasets:
            reference_df = datasets[params.reference_dataset_key]

            if (
                "precision" in params.metrics_to_calculate
                or "recall" in params.metrics_to_calculate
            ):
                precision, recall, f1 = self._calculate_precision_recall(
                    mapped_df, reference_df, params
                )

                if "precision" in params.metrics_to_calculate:
                    individual_metrics["precision"] = precision
                if "recall" in params.metrics_to_calculate:
                    individual_metrics["recall"] = recall
                if "f1_score" in params.metrics_to_calculate:
                    individual_metrics["f1_score"] = f1

        # Calculate identifier quality metrics
        if "identifier_quality" in params.metrics_to_calculate:
            id_quality = self._assess_identifier_quality(
                mapped_df, params.mapped_id_column
            )
            individual_metrics.update(id_quality)

        # Calculate overall quality score (weighted average)
        overall_quality_score = self._calculate_overall_quality(individual_metrics)

        # Quality distribution
        quality_distribution = {
            "high_quality": high_confidence_mappings,
            "medium_quality": successful_mappings
            - high_confidence_mappings
            - low_confidence_mappings,
            "low_quality": low_confidence_mappings,
            "failed": failed_mappings,
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(
            individual_metrics, total_source, successful_mappings, params
        )

        # Detailed report (if requested)
        detailed_report = None
        if params.include_detailed_report:
            detailed_report = self._generate_detailed_report(
                source_df, mapped_df, params, individual_metrics
            )

        # Store quality metrics in context
        context.setdefault("statistics", {}).update(
            {
                f"{params.output_key}_overall_quality": overall_quality_score,
                f"{params.output_key}_match_rate": individual_metrics.get(
                    "match_rate", 0
                ),
                f"{params.output_key}_successful_mappings": successful_mappings,
            }
        )

        # Store detailed metrics dataset
        quality_df = pd.DataFrame(
            [
                {"metric": k, "value": v, "category": "mapping_quality"}
                for k, v in individual_metrics.items()
            ]
        )

        context.setdefault("datasets", {})[params.output_key] = quality_df

        return MappingQualityResult(
            success=True,
            total_source_identifiers=total_source,
            total_mapped_identifiers=total_mapped,
            successful_mappings=successful_mappings,
            failed_mappings=failed_mappings,
            overall_quality_score=overall_quality_score,
            individual_metrics=individual_metrics,
            quality_distribution=quality_distribution,
            high_confidence_mappings=high_confidence_mappings,
            low_confidence_mappings=low_confidence_mappings,
            ambiguous_mappings=ambiguous_mappings,
            detailed_report=detailed_report,
            recommendations=recommendations,
            data={
                "output_key": params.output_key,
                "overall_quality_score": overall_quality_score,
                "successful_mappings": successful_mappings,
                "total_source_identifiers": total_source,
            },
        )

    def _calculate_precision_recall(
        self,
        mapped_df: pd.DataFrame,
        reference_df: pd.DataFrame,
        params: CalculateMappingQualityParams,
    ) -> tuple[float, float, float]:
        """Calculate precision, recall, and F1 score against reference."""

        # Extract mapped pairs
        mapped_pairs = set()
        for _, row in mapped_df.iterrows():
            source_id = row[params.source_id_column]
            mapped_id = row[params.mapped_id_column]
            if pd.notna(mapped_id) and mapped_id != "":
                mapped_pairs.add((source_id, mapped_id))

        # Extract reference pairs (assuming same column structure)
        reference_pairs = set()
        for _, row in reference_df.iterrows():
            source_id = row[params.source_id_column]
            ref_id = row[params.mapped_id_column]
            if pd.notna(ref_id) and ref_id != "":
                reference_pairs.add((source_id, ref_id))

        # Calculate metrics
        true_positives = len(mapped_pairs & reference_pairs)
        precision = true_positives / len(mapped_pairs) if mapped_pairs else 0
        recall = true_positives / len(reference_pairs) if reference_pairs else 0
        f1_score = (
            (2 * precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return precision, recall, f1_score

    def _assess_identifier_quality(
        self, df: pd.DataFrame, id_column: str
    ) -> Dict[str, float]:
        """Assess quality of identifiers themselves."""

        ids = df[id_column].dropna()
        if len(ids) == 0:
            return {"id_format_consistency": 0, "id_completeness": 0}

        # Check format consistency (example for UniProt-like IDs)
        format_scores = []
        for id_val in ids:
            id_str = str(id_val)
            score = 0.0

            # Length consistency
            if len(id_str) >= 6:
                score += 0.3

            # Alphanumeric pattern
            if id_str.isalnum():
                score += 0.3

            # No spaces or special characters
            if not any(c in id_str for c in [" ", "\t", "\n", "|", ";"]):
                score += 0.4

            format_scores.append(score)

        return {
            "id_format_consistency": float(np.mean(format_scores)),
            "id_completeness": len(ids) / len(df),
        }

    def _calculate_overall_quality(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted overall quality score."""

        # Default weights for common metrics
        weights = {
            "match_rate": 0.3,
            "coverage": 0.2,
            "precision": 0.2,
            "avg_confidence": 0.15,
            "id_format_consistency": 0.1,
            "f1_score": 0.05,
        }

        total_score = 0.0
        total_weight = 0.0

        for metric, value in metrics.items():
            if metric in weights:
                total_score += value * weights[metric]
                total_weight += weights[metric]

        return total_score / total_weight if total_weight > 0 else 0

    def _generate_recommendations(
        self,
        metrics: Dict[str, float],
        total_source: int,
        successful_mappings: int,
        params: CalculateMappingQualityParams,
    ) -> List[str]:
        """Generate actionable recommendations based on quality metrics."""

        recommendations = []

        match_rate = metrics.get("match_rate", 0)
        if match_rate < 0.7:
            recommendations.append(
                f"Low match rate ({match_rate:.1%}). Consider using additional identifier types or fuzzy matching."
            )

        if "duplicate_rate" in metrics and metrics["duplicate_rate"] > 0.1:
            recommendations.append(
                f"High duplicate rate ({metrics['duplicate_rate']:.1%}). Review mapping logic for one-to-many relationships."
            )

        if "ambiguity_rate" in metrics and metrics["ambiguity_rate"] > 0.05:
            recommendations.append(
                f"High ambiguity rate ({metrics['ambiguity_rate']:.1%}). Consider adding disambiguation criteria."
            )

        if (
            "avg_confidence" in metrics
            and metrics["avg_confidence"] < params.confidence_threshold
        ):
            recommendations.append(
                f"Low average confidence ({metrics['avg_confidence']:.2f}). Review confidence scoring algorithm."
            )

        if successful_mappings < total_source * 0.8:
            recommendations.append(
                "Consider preprocessing source identifiers (normalization, cleaning) to improve match rates."
            )

        return recommendations

    def _generate_detailed_report(
        self,
        source_df: pd.DataFrame,
        mapped_df: pd.DataFrame,
        params: CalculateMappingQualityParams,
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate detailed per-identifier analysis."""

        # Per-identifier success analysis
        identifier_analysis = []

        for _, row in mapped_df.iterrows():
            source_id = row[params.source_id_column]
            mapped_id = row[params.mapped_id_column]
            confidence = (
                row.get(params.confidence_column, None)
                if params.confidence_column
                else None
            )

            analysis = {
                "source_id": source_id,
                "mapped_id": mapped_id,
                "success": pd.notna(mapped_id) and mapped_id != "",
                "confidence": confidence,
            }

            identifier_analysis.append(analysis)

        return {
            "identifier_analysis": identifier_analysis[:100],  # Limit for performance
            "summary_stats": metrics,
            "data_quality": {
                "source_completeness": (
                    source_df[params.source_id_column].notna()
                ).sum()
                / len(source_df),
                "mapped_completeness": (
                    mapped_df[params.mapped_id_column].notna()
                ).sum()
                / len(mapped_df),
            },
        }

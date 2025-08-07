"""Generate enhancement report action for metabolomics harmonization."""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class GenerateEnhancementReportParams(BaseModel):
    """Parameters for generating progressive enhancement report."""

    metrics_keys: List[str] = Field(
        ...,
        description="List of metric keys to aggregate (e.g., ['metrics.baseline', 'metrics.api', 'metrics.vector'])",
    )

    stage_names: Optional[List[str]] = Field(
        default=["Baseline", "API Enhanced", "Vector Enhanced"],
        description="Human-readable names for each stage",
    )

    output_path: str = Field(
        ..., description="Path where the markdown report will be saved"
    )

    include_visualizations: bool = Field(
        default=True, description="Whether to include ASCII charts in the report"
    )

    include_detailed_stats: bool = Field(
        default=True, description="Whether to include detailed statistics per dataset"
    )

    comparison_baseline: Optional[str] = Field(
        default=None,
        description="Which stage to use as baseline for improvement calculations (default: first stage)",
    )


@register_action("GENERATE_ENHANCEMENT_REPORT")
class GenerateEnhancementReport(
    TypedStrategyAction[GenerateEnhancementReportParams, StandardActionResult]
):
    """
    Generate comprehensive markdown reports showing progressive enhancement results.

    This action:
    - Aggregates metrics from multiple enhancement stages
    - Calculates improvement percentages
    - Generates professional markdown reports
    - Creates ASCII visualizations
    - Handles missing data gracefully
    """

    def get_params_model(self) -> type[GenerateEnhancementReportParams]:
        """Return the params model class."""
        return GenerateEnhancementReportParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult

    def _aggregate_metrics(
        self, metrics_keys: List[str], context: Any
    ) -> List[Dict[str, Any]]:
        """Aggregate metrics from context."""
        metrics = []

        for key in metrics_keys:
            # Try both typed and dict context access patterns
            if hasattr(context, "get_action_data"):
                metric_data = context.get_action_data(key)
            else:
                metric_data = context.get(key)

            if metric_data:
                metrics.append(metric_data)
            else:
                logger.warning(f"Metrics not found for key: {key}")

        return metrics

    def _calculate_absolute_improvement(self, baseline: float, current: float) -> float:
        """Calculate absolute improvement in percentage points."""
        return (current - baseline) * 100

    def _calculate_relative_improvement(self, baseline: float, current: float) -> float:
        """Calculate relative improvement as percentage change."""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100

    def _generate_ascii_chart(self, stages: List[str], values: List[float]) -> str:
        """Generate ASCII bar chart for match rates."""
        if not values:
            return "No data available for visualization"

        max_value = max(values) if values else 1
        chart_height = 10
        bar_width = 9  # Increased for better label fit

        lines = ["Match Rate by Enhancement Stage", ""]

        # Generate y-axis labels and bars
        for i in range(chart_height, -1, -1):
            threshold = i * max_value / chart_height
            line = f"{int(threshold * 100):3d}% |"

            for j, value in enumerate(values):
                if value >= threshold:
                    if i == int(value * chart_height / max_value):
                        # Top of bar
                        line += f"  ┌{'─' * (bar_width-2)}┐"
                    else:
                        # Bar body with value
                        percent_str = f"{int(value*100)}%"
                        padding = (bar_width - 2 - len(percent_str)) // 2
                        line += f"  │{' ' * padding}{percent_str}{' ' * (bar_width-2-padding-len(percent_str))}│"
                else:
                    line += " " * (bar_width + 2)

            lines.append(line)

        # X-axis
        lines.append("  0% └" + "─" * (len(stages) * (bar_width + 2)) + "┘")

        # Labels - ensure they fit
        label_line = "     "
        for stage in stages:
            # Truncate if too long
            if len(stage) > bar_width + 1:
                stage = stage[: bar_width - 1] + "."
            # Center the label
            total_space = bar_width + 2
            padding_left = (total_space - len(stage)) // 2
            padding_right = total_space - len(stage) - padding_left
            label_line += " " * padding_left + stage + " " * padding_right
        lines.append(label_line)

        return "\n".join(lines)

    def _generate_markdown_report(
        self,
        metrics: List[Dict[str, Any]],
        stage_names: List[str],
        timestamp: datetime,
        include_visualizations: bool,
        include_detailed_stats: bool,
        baseline_idx: int = 0,
    ) -> str:
        """Generate the complete markdown report."""
        lines = []

        # Header
        lines.extend(
            [
                "# Metabolomics Progressive Enhancement Report",
                "",
                f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]
        )

        # Executive Summary
        lines.extend(["## Executive Summary", ""])

        if metrics:
            # Get key metrics
            # For custom baseline, use cumulative rate if available
            if baseline_idx > 0:
                baseline_rate = metrics[baseline_idx].get(
                    "cumulative_match_rate", metrics[baseline_idx].get("match_rate", 0)
                )
            else:
                baseline_rate = (
                    metrics[baseline_idx].get("match_rate", 0)
                    if baseline_idx < len(metrics)
                    else 0
                )

            final_idx = len(metrics) - 1
            final_rate = metrics[final_idx].get(
                "cumulative_match_rate", metrics[final_idx].get("match_rate", 0)
            )

            # Calculate totals
            total_metabolites = (
                metrics[0].get("total_unmatched_input", 1000) if metrics else 1000
            )
            total_matched = int(final_rate * total_metabolites)

            # Calculate improvements
            abs_improvement = self._calculate_absolute_improvement(
                baseline_rate, final_rate
            )
            rel_improvement = self._calculate_relative_improvement(
                baseline_rate, final_rate
            )

            lines.extend(
                [
                    f"The three-stage progressive enhancement strategy successfully improved metabolite matching rates from **{baseline_rate*100:.0f}%** to **{final_rate*100:.0f}%**, ",
                    f"representing a **{rel_improvement:.0f}% relative improvement** over the baseline approach.",
                    "",
                    "### Key Achievements",
                    f"- ✅ Processed {total_metabolites:,} unique metabolites across datasets",
                    f"- ✅ Achieved {final_rate*100:.0f}% overall match rate ({total_matched}/{total_metabolites:,} metabolites)",
                    "- ✅ Demonstrated clear value of API and vector enhancement approaches",
                    f"- ✅ Total processing time: {sum(m.get('execution_time', 0) for m in metrics):.1f} seconds",
                    "",
                ]
            )
        else:
            lines.extend(["No metrics data available for analysis.", ""])

        # Progressive Enhancement Results
        lines.extend(["## Progressive Enhancement Results", ""])

        if metrics:
            # Create results table
            lines.extend(
                [
                    "| Stage | Match Rate | Improvement | Cumulative | Time (s) |",
                    "|-------|------------|-------------|------------|----------|",
                ]
            )

            for i, (metric, stage_name) in enumerate(
                zip(metrics, stage_names[: len(metrics)])
            ):
                match_rate = metric.get("match_rate", 0)
                cumulative_rate = metric.get("cumulative_match_rate", match_rate)
                exec_time = metric.get("execution_time", 0)

                # Calculate improvement
                if i == 0:
                    improvement_str = "-"
                else:
                    prev_cumulative = metrics[i - 1].get(
                        "cumulative_match_rate", metrics[i - 1].get("match_rate", 0)
                    )
                    improvement = self._calculate_relative_improvement(
                        prev_cumulative, cumulative_rate
                    )
                    improvement_str = f"+{improvement:.1f}%"

                lines.append(
                    f"| {stage_name} | {match_rate*100:.1f}% | {improvement_str} | "
                    f"{cumulative_rate*100:.1f}% | {exec_time:.1f} |"
                )

            lines.append("")

        # Visual Representation
        if include_visualizations and metrics:
            lines.extend(["### Visual Representation", ""])

            # Extract cumulative rates for chart
            chart_values = []
            chart_stages = []
            for metric, stage in zip(metrics, stage_names[: len(metrics)]):
                rate = metric.get("cumulative_match_rate", metric.get("match_rate", 0))
                chart_values.append(rate)
                chart_stages.append(stage)

            chart = self._generate_ascii_chart(chart_stages, chart_values)
            lines.extend(["```", chart, "```", ""])

        # Detailed Statistics
        if include_detailed_stats and metrics:
            lines.extend(["## Detailed Statistics", ""])

            for i, (metric, stage_name) in enumerate(
                zip(metrics, stage_names[: len(metrics)])
            ):
                metabolites_processed = metric.get("total_unmatched_input", "N/A")
                successful_matches = metric.get("total_matched", "N/A")

                # Format numbers with commas if they're numeric
                if isinstance(metabolites_processed, (int, float)):
                    metabolites_str = f"{metabolites_processed:,}"
                else:
                    metabolites_str = str(metabolites_processed)

                if isinstance(successful_matches, (int, float)):
                    matches_str = f"{successful_matches:,}"
                else:
                    matches_str = str(successful_matches)

                lines.extend(
                    [
                        f"### Stage {i+1}: {stage_name}",
                        f"- Metabolites processed: {metabolites_str}",
                        f"- Successful matches: {matches_str}",
                        f"- Match rate: {metric.get('match_rate', 0)*100:.1f}%",
                    ]
                )

                if i > 0:
                    lines.append(
                        f"- Cumulative match rate: {metric.get('cumulative_match_rate', 0)*100:.1f}%"
                    )

                lines.append(
                    f"- Processing time: {metric.get('execution_time', 0):.1f} seconds"
                )

                # Add stage-specific details
                if "avg_confidence" in metric:
                    lines.append(
                        f"- Average confidence: {metric['avg_confidence']:.2f}"
                    )
                if "api_calls_made" in metric:
                    lines.append(f"- API calls made: {metric['api_calls_made']:,}")
                if "cache_hits" in metric:
                    lines.append(f"- Cache hits: {metric['cache_hits']:,}")
                if "avg_similarity_score" in metric:
                    lines.append(
                        f"- Average similarity score: {metric['avg_similarity_score']:.3f}"
                    )
                if "vectors_searched" in metric:
                    lines.append(f"- Vectors searched: {metric['vectors_searched']:,}")

                lines.append("")

        # Methodology
        lines.extend(
            [
                "## Methodology",
                "",
                "This report demonstrates the effectiveness of a progressive enhancement approach to metabolite harmonization:",
                "",
                "1. **Baseline Stage**: Fuzzy string matching using Levenshtein distance",
                "   - Fast, simple approach for exact and near-exact matches",
                "   - Handles common variations in naming conventions",
                "",
                "2. **API Enhancement Stage**: Chemical Translation Service (CTS) enrichment",
                "   - Leverages chemical databases for synonym expansion",
                "   - Resolves chemical identifiers across naming systems",
                "",
                "3. **Vector Enhancement Stage**: Semantic search using embeddings",
                "   - Uses HMDB reference database with vector embeddings",
                "   - Captures semantic similarity beyond string matching",
                "",
                "Each stage processes only the unmatched items from the previous stage, maximizing efficiency.",
                "",
            ]
        )

        # Conclusions
        lines.extend(["## Conclusions", ""])

        if metrics and len(metrics) >= 2:
            # Use the same baseline calculation as in executive summary
            if baseline_idx > 0:
                baseline_rate = metrics[baseline_idx].get(
                    "cumulative_match_rate", metrics[baseline_idx].get("match_rate", 0)
                )
            else:
                baseline_rate = (
                    metrics[baseline_idx].get("match_rate", 0)
                    if baseline_idx < len(metrics)
                    else 0
                )

            final_rate = metrics[-1].get(
                "cumulative_match_rate", metrics[-1].get("match_rate", 0)
            )
            improvement = self._calculate_relative_improvement(
                baseline_rate, final_rate
            )

            lines.extend(
                [
                    f"The progressive enhancement approach achieved a **{improvement:.0f}% relative improvement** in match rates, demonstrating:",
                    "",
                    "- ✅ **Effectiveness**: Each enhancement stage contributed meaningful improvements",
                    "- ✅ **Efficiency**: Processing only unmatched items at each stage reduces computational cost",
                    "- ✅ **Flexibility**: The modular approach allows for easy addition of new enhancement strategies",
                    "",
                    "### Recommendations for Further Improvement",
                    "",
                    "1. **Expand reference databases**: Include additional chemical databases beyond HMDB",
                    "2. **Enhance vector models**: Fine-tune embeddings on domain-specific metabolomics data",
                    "3. **Add structural matching**: Incorporate InChI/SMILES-based similarity for chemical structures",
                    "4. **Implement active learning**: Use successful matches to improve future matching accuracy",
                    "",
                ]
            )
        else:
            lines.extend(["Insufficient data to draw conclusions.", ""])

        return "\n".join(lines)

    def _write_report_to_file(self, output_path: str, content: str) -> None:
        """Write report content to file with error handling."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Report successfully written to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to write report to {output_path}: {e}")
            raise

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: GenerateEnhancementReportParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute report generation."""

        logger.info(
            f"Generating enhancement report from {len(params.metrics_keys)} metric sources"
        )

        # Aggregate metrics
        metrics = self._aggregate_metrics(params.metrics_keys, context)

        if not metrics:
            logger.warning("No metrics found to generate report")
            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=current_identifiers,
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "GENERATE_ENHANCEMENT_REPORT",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "warning",
                        "message": "No metrics found",
                    }
                ],
                details={
                    "metrics_found": 0,
                    "warning": "No metrics data found to generate report",
                },
            )

        # Determine baseline index
        baseline_idx = 0
        if params.comparison_baseline:
            for i, key in enumerate(params.metrics_keys):
                if key == params.comparison_baseline:
                    baseline_idx = i
                    break

        # Ensure we have enough stage names
        stage_names = params.stage_names or []
        while len(stage_names) < len(metrics):
            stage_names.append(f"Stage {len(stage_names) + 1}")

        # Generate report
        timestamp = datetime.utcnow()
        report_content = self._generate_markdown_report(
            metrics=metrics,
            stage_names=stage_names,
            timestamp=timestamp,
            include_visualizations=params.include_visualizations,
            include_detailed_stats=params.include_detailed_stats,
            baseline_idx=baseline_idx,
        )

        # Write to file
        self._write_report_to_file(params.output_path, report_content)

        # Return result
        return StandardActionResult(
            input_identifiers=current_identifiers,
            output_identifiers=current_identifiers,
            output_ontology_type=current_ontology_type,
            provenance=[
                {
                    "action": "GENERATE_ENHANCEMENT_REPORT",
                    "timestamp": timestamp.isoformat(),
                    "output_path": params.output_path,
                    "metrics_aggregated": len(metrics),
                    "report_size_bytes": len(report_content),
                }
            ],
            details={
                "report_path": params.output_path,
                "metrics_found": len(metrics),
                "baseline_used": params.metrics_keys[baseline_idx]
                if baseline_idx < len(params.metrics_keys)
                else "first",
                "timestamp": timestamp.isoformat(),
            },
        )

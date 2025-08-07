"""Calculate overlap statistics from merged datasets with match metadata."""

import csv
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
from matplotlib_venn import venn2  # type: ignore

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
# StrategyExecutionContext not used in MVP mode

logger = logging.getLogger(__name__)


class CalculateSetOverlapParams(BaseModel):
    """Parameters for CALCULATE_SET_OVERLAP action."""

    # Input
    input_key: str = Field(..., description="Merged dataset with match metadata")

    # Dataset identification
    source_name: str = Field(..., description="Source dataset name (e.g., 'UKBB')")
    target_name: str = Field(..., description="Target dataset name (e.g., 'HPA')")
    mapping_combo_id: str = Field(
        ..., description="Unique mapping identifier (e.g., 'UKBB_HPA')"
    )

    # Analysis configuration
    confidence_threshold: float = Field(
        0.8, description="Minimum confidence for 'high quality' stats", ge=0.0, le=1.0
    )

    # Output
    output_dir: str = Field("results", description="Base output directory")
    output_key: str = Field(..., description="Context key for statistics")


@register_action("CALCULATE_SET_OVERLAP")
class CalculateSetOverlapAction(
    TypedStrategyAction[CalculateSetOverlapParams, StandardActionResult]
):
    """
    Calculate overlap statistics from merged datasets with match metadata.

    This action:
    - Analyzes merged dataset from MERGE_WITH_UNIPROT_RESOLUTION
    - Calculates comprehensive overlap statistics
    - Generates 5 output files: statistics CSV, breakdown CSV, SVG/PNG Venn diagrams, merged dataset CSV
    - Creates standardized directory structure: results/[mapping_combo_id]/
    - Handles match metadata columns: match_value, match_type, match_confidence, match_status
    - Calculates perspective-based statistics (source/target match rates, Jaccard index, etc.)
    - Generates professional Venn diagrams using matplotlib-venn
    """

    def get_params_model(self) -> type[CalculateSetOverlapParams]:
        return CalculateSetOverlapParams

    def get_result_model(self) -> type[StandardActionResult]:
        return StandardActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: CalculateSetOverlapParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute the action to calculate set overlap statistics."""

        import time

        action_start_time = time.time()

        # Initialize context data structures
        if "datasets" not in context.custom_action_data:
            context.set_action_data("datasets", {})
        if "statistics" not in context.custom_action_data:
            context.set_action_data("statistics", {})
        if "output_files" not in context.custom_action_data:
            context.set_action_data("output_files", {})

        logger.info(f"Calculating overlap statistics for {params.mapping_combo_id}")

        try:
            # Get merged dataset from context
            datasets = context.get_action_data("datasets", {})

            if params.input_key not in datasets:
                raise ValueError(
                    f"Input dataset '{params.input_key}' not found in context"
                )

            merged_data = datasets[params.input_key]

            if not merged_data:
                # Handle empty dataset
                logger.warning(f"Empty merged dataset for {params.mapping_combo_id}")
                empty_stats = self._create_empty_statistics(params)
                context.set_action_data("statistics", {params.output_key: empty_stats})
                self._create_output_files([], empty_stats, params, context)

                return StandardActionResult(
                    input_identifiers=current_identifiers,
                    output_identifiers=[],
                    output_ontology_type=current_ontology_type,
                    provenance=[
                        {
                            "action": "CALCULATE_SET_OVERLAP",
                            "mapping_combo_id": params.mapping_combo_id,
                            "total_rows": 0,
                            "matched_rows": 0,
                        }
                    ],
                    details={
                        "output_key": params.output_key,
                        "mapping_combo_id": params.mapping_combo_id,
                        "total_rows": 0,
                    },
                )

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(merged_data)

            # Validate required columns
            required_columns = ["match_status", "match_type", "match_confidence"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Calculate statistics
            logger.info("Calculating overlap statistics")
            statistics = self._calculate_statistics(
                df, params, action_start_time, context
            )

            # Store statistics in context
            context.set_action_data("statistics", {params.output_key: statistics})

            # Create output files
            logger.info("Creating output files")
            self._create_output_files(merged_data, statistics, params, context)

            logger.info(
                f"Overlap analysis complete for {params.mapping_combo_id}: "
                f"{statistics['total_rows']} rows, {statistics['matched_rows']} matches"
            )

            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "CALCULATE_SET_OVERLAP",
                        "mapping_combo_id": params.mapping_combo_id,
                        "total_rows": statistics["total_rows"],
                        "matched_rows": statistics["matched_rows"],
                    }
                ],
                details={
                    "output_key": params.output_key,
                    "mapping_combo_id": params.mapping_combo_id,
                    "statistics": statistics,
                },
            )

        except Exception as e:
            logger.error(f"Failed to calculate overlap statistics: {str(e)}")
            raise

    def _create_empty_statistics(
        self, params: CalculateSetOverlapParams
    ) -> Dict[str, Any]:
        """Create empty statistics structure for empty datasets."""
        return {
            "mapping_combo_id": params.mapping_combo_id,
            "source_name": params.source_name,
            "target_name": params.target_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_rows": 0,
            "matched_rows": 0,
            "source_only_rows": 0,
            "target_only_rows": 0,
            "direct_matches": 0,
            "composite_matches": 0,
            "historical_matches": 0,
            "source_match_rate": 0.0,
            "target_match_rate": 0.0,
            "jaccard_index": 0.0,
            "dice_coefficient": 0.0,
            "avg_match_confidence": 0.0,
            "high_confidence_matches": 0,
            "confidence_threshold": params.confidence_threshold,
            "analysis_time_seconds": 0.0,
            "merge_time_seconds": 0.0,
            "total_mapping_time_seconds": 0.0,
        }

    def _calculate_statistics(
        self,
        df: pd.DataFrame,
        params: CalculateSetOverlapParams,
        action_start_time: float = None,
        context: Any = None,
    ) -> Dict[str, Any]:
        """Calculate comprehensive overlap statistics with timing information."""

        # Core statistics
        total_rows = len(df)
        matched_rows = len(df[df["match_status"] == "matched"])
        source_only_rows = len(df[df["match_status"] == "source_only"])
        target_only_rows = len(df[df["match_status"] == "target_only"])

        # Match type breakdown
        direct_matches = len(df[df["match_type"] == "direct"])
        composite_matches = len(df[df["match_type"] == "composite"])
        historical_matches = len(df[df["match_type"] == "historical"])

        # Quality metrics
        matched_df = df[df["match_status"] == "matched"]
        high_conf_matches = len(
            matched_df[matched_df["match_confidence"] >= params.confidence_threshold]
        )

        # Calculate average confidence (only for matched rows)
        avg_match_confidence = (
            float(matched_df["match_confidence"].mean()) if len(matched_df) > 0 else 0.0
        )

        # Perspective-based statistics
        source_total = source_only_rows + matched_rows
        source_match_rate = matched_rows / source_total if source_total > 0 else 0.0

        target_total = target_only_rows + matched_rows
        target_match_rate = matched_rows / target_total if target_total > 0 else 0.0

        # Set theory statistics
        union_total = source_only_rows + target_only_rows + matched_rows
        jaccard_index = matched_rows / union_total if union_total > 0 else 0.0
        dice_coefficient = (
            (2 * matched_rows) / (source_total + target_total)
            if (source_total + target_total) > 0
            else 0.0
        )

        statistics = {
            "mapping_combo_id": params.mapping_combo_id,
            "source_name": params.source_name,
            "target_name": params.target_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_rows": total_rows,
            "matched_rows": matched_rows,
            "source_only_rows": source_only_rows,
            "target_only_rows": target_only_rows,
            "direct_matches": direct_matches,
            "composite_matches": composite_matches,
            "historical_matches": historical_matches,
            "source_match_rate": source_match_rate,
            "target_match_rate": target_match_rate,
            "jaccard_index": jaccard_index,
            "dice_coefficient": dice_coefficient,
            "avg_match_confidence": avg_match_confidence,
            "high_confidence_matches": high_conf_matches,
            "confidence_threshold": params.confidence_threshold,
        }

        # Add timing information if available
        import time

        if action_start_time is not None:
            statistics["analysis_time_seconds"] = round(
                time.time() - action_start_time, 2
            )

        # Try to get merge timing from context (set by MERGE_WITH_UNIPROT_RESOLUTION)
        if context:
            metadata = context.get_action_data("metadata", {})
            # Look for timing from the most recent merge operation
            for key in metadata:
                if (
                    key.endswith("_merged")
                    and "processing_time_seconds" in metadata[key]
                ):
                    statistics["merge_time_seconds"] = metadata[key][
                        "processing_time_seconds"
                    ]
                    # Calculate total mapping time (merge + analysis)
                    if action_start_time is not None:
                        statistics["total_mapping_time_seconds"] = round(
                            statistics.get("merge_time_seconds", 0)
                            + statistics.get("analysis_time_seconds", 0),
                            2,
                        )
                    break

        return statistics

    def _create_output_files(
        self,
        merged_data: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        params: CalculateSetOverlapParams,
        context: Any,
    ) -> None:
        """Create all 5 output files."""

        # Create output directory
        output_path = Path(params.output_dir) / params.mapping_combo_id
        output_path.mkdir(parents=True, exist_ok=True)

        # File paths
        stats_file = output_path / "overlap_statistics.csv"
        breakdown_file = output_path / "match_type_breakdown.csv"
        venn_svg_file = output_path / "venn_diagram.svg"
        venn_png_file = output_path / "venn_diagram.png"
        merged_file = output_path / "merged_dataset.csv"

        # 1. Main statistics CSV
        self._create_statistics_csv(stats_file, statistics)

        # 2. Match type breakdown CSV
        self._create_breakdown_csv(breakdown_file, statistics)

        # 3. & 4. Venn diagrams (SVG and PNG)
        self._create_venn_diagrams(venn_svg_file, venn_png_file, statistics, params)

        # 5. Complete merged dataset CSV
        self._create_merged_dataset_csv(merged_file, merged_data)

        # Store file paths in context
        output_files = context.get_action_data("output_files", {})
        output_files.update(
            {
                f"{params.output_key}_statistics": str(stats_file),
                f"{params.output_key}_breakdown": str(breakdown_file),
                f"{params.output_key}_venn_svg": str(venn_svg_file),
                f"{params.output_key}_venn_png": str(venn_png_file),
                f"{params.output_key}_merged_data": str(merged_file),
            }
        )
        context.set_action_data("output_files", output_files)

    def _create_statistics_csv(
        self, file_path: Path, statistics: Dict[str, Any]
    ) -> None:
        """Create main statistics CSV file."""
        columns = [
            "mapping_combo_id",
            "source_name",
            "target_name",
            "analysis_timestamp",
            "total_rows",
            "matched_rows",
            "source_only_rows",
            "target_only_rows",
            "direct_matches",
            "composite_matches",
            "historical_matches",
            "source_match_rate",
            "target_match_rate",
            "jaccard_index",
            "dice_coefficient",
            "avg_match_confidence",
            "high_confidence_matches",
            "confidence_threshold",
            "analysis_time_seconds",
            "merge_time_seconds",
            "total_mapping_time_seconds",
        ]

        with open(file_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerow(statistics)

    def _create_breakdown_csv(
        self, file_path: Path, statistics: Dict[str, Any]
    ) -> None:
        """Create match type breakdown CSV file."""
        breakdown_data = [
            {"match_type": "direct", "count": statistics["direct_matches"]},
            {"match_type": "composite", "count": statistics["composite_matches"]},
            {"match_type": "historical", "count": statistics["historical_matches"]},
            {"match_type": "source_only", "count": statistics["source_only_rows"]},
            {"match_type": "target_only", "count": statistics["target_only_rows"]},
        ]

        with open(file_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["match_type", "count"])
            writer.writeheader()
            writer.writerows(breakdown_data)

    def _create_venn_diagrams(
        self,
        svg_file: Path,
        png_file: Path,
        statistics: Dict[str, Any],
        params: CalculateSetOverlapParams,
    ) -> None:
        """Create Venn diagrams in SVG and PNG formats."""

        # Set up professional plot style
        plt.style.use("seaborn-v0_8")

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create Venn diagram
        venn2(
            subsets=(
                statistics["source_only_rows"],
                statistics["target_only_rows"],
                statistics["matched_rows"],
            ),
            set_labels=(params.source_name, params.target_name),
            ax=ax,
        )

        # Add title with key statistics
        title = (
            f'{params.mapping_combo_id} Protein Mapping Overlap\n'
            f'Jaccard Index: {statistics["jaccard_index"]:.3f} | '
            f'Total Matches: {statistics["matched_rows"]:,}'
        )
        plt.title(title, fontsize=14, fontweight="bold")

        # Save both formats
        plt.savefig(svg_file, format="svg", dpi=300, bbox_inches="tight")
        plt.savefig(png_file, format="png", dpi=300, bbox_inches="tight")
        plt.close()

    def _create_merged_dataset_csv(
        self, file_path: Path, merged_data: List[Dict[str, Any]]
    ) -> None:
        """Create complete merged dataset CSV file."""
        if not merged_data:
            # Create empty file with just headers
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["empty_dataset"])
            return

        # Get all column names
        all_columns: set[str] = set()
        for row in merged_data:
            all_columns.update(row.keys())

        # Sort columns for consistent output
        sorted_columns = sorted(all_columns)

        with open(file_path, "w", newline="") as csvfile:
            dict_writer = csv.DictWriter(csvfile, fieldnames=sorted_columns)
            dict_writer.writeheader()
            dict_writer.writerows(merged_data)

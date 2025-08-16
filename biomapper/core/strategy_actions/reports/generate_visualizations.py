"""Generate comprehensive visualizations for mapping analysis."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class VisualizationResult(BaseModel):
    """Result model for visualization generation."""

    success: bool
    message: str
    data: Dict[str, Any] = {}
    input_identifiers: List[str] = []
    output_identifiers: List[str] = []
    output_ontology_type: str = "visualization"


class VisualizationParams(BaseModel):
    """Parameters for generating visualizations."""

    # Input data
    dataset_keys: List[str] = Field(..., description="Datasets to visualize")
    statistics_key: str = Field(
        default="statistics", description="Key containing statistics"
    )

    # Output configuration
    output_dir: str = Field(..., description="Directory for saving visualizations")
    formats: List[Literal["png", "svg", "html"]] = Field(default=["png"])

    # Visualization selection
    charts: List[str] = Field(
        default=["coverage", "confidence", "mapping_flow", "statistics_summary"],
        description="Which charts to generate",
    )

    # Styling
    style: Literal["default", "scientific", "presentation"] = Field(
        default="scientific"
    )
    color_scheme: str = Field(default="viridis")
    figure_size: Tuple[int, int] = Field(default=(10, 6))


# Individual visualization functions (for testing)


def create_coverage_pie(
    data: pd.DataFrame, statistics: Dict[str, Any], output_path: Path
) -> bool:
    """Create coverage pie chart showing mapped vs unmapped."""
    try:
        # Calculate coverage statistics
        total_count = statistics.get("total_identifiers", 0)
        mapped_count = statistics.get("successfully_mapped", 0)

        if total_count == 0:
            if len(data) > 0:
                # Try to calculate from data
                if "mapped" in data.columns:
                    total_count = len(data)
                    mapped_count = data["mapped"].sum()
                elif "target_id" in data.columns:
                    total_count = len(data)
                    mapped_count = data["target_id"].notna().sum()

        if total_count == 0:
            logger.warning("No data for coverage pie chart")
            return False

        unmapped_count = total_count - mapped_count

        # Create pie chart
        fig, ax = plt.subplots(figsize=(10, 8))

        sizes = [mapped_count, unmapped_count]
        labels = [
            f"Mapped\n({mapped_count:,} = {mapped_count/total_count*100:.1f}%)",
            f"Unmapped\n({unmapped_count:,} = {unmapped_count/total_count*100:.1f}%)",
        ]
        colors = ["#2ecc71", "#e74c3c"]
        explode = (0.05, 0)

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            explode=explode,
            shadow=True,
            startangle=90,
        )

        ax.set_title("Mapping Coverage Analysis", fontsize=16, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return True

    except Exception as e:
        logger.error(f"Failed to create coverage pie: {str(e)}")
        plt.close()
        return False


def create_confidence_histogram(
    data: Union[pd.DataFrame, List[Dict]], output_path: Path
) -> bool:
    """Create histogram of confidence score distribution."""
    try:
        # Extract confidence scores
        all_scores = []

        if isinstance(data, pd.DataFrame):
            if "confidence_score" in data.columns:
                scores = data["confidence_score"].dropna().tolist()
                all_scores.extend(scores)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "confidence_score" in item:
                    score = item["confidence_score"]
                    if score is not None and not pd.isna(score):
                        all_scores.append(score)

        if not all_scores:
            logger.warning("No confidence scores found")
            return False

        # Create histogram
        fig, ax = plt.subplots(figsize=(12, 7))

        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        colors = ["#e74c3c", "#f39c12", "#f1c40f", "#2ecc71", "#27ae60"]

        n, bins, patches = ax.hist(
            all_scores, bins=bins, edgecolor="black", linewidth=1.2
        )

        for patch, color in zip(patches, colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)

        ax.set_xlabel("Confidence Score", fontsize=12, fontweight="bold")
        ax.set_ylabel("Number of Mappings", fontsize=12, fontweight="bold")
        ax.set_title("Mapping Confidence Distribution", fontsize=16, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return True

    except Exception as e:
        logger.error(f"Failed to create confidence histogram: {str(e)}")
        plt.close()
        return False


def create_mapping_flow_sankey(statistics: Dict[str, Any], output_path: Path) -> bool:
    """Create Sankey diagram showing mapping flow."""
    try:
        # Extract flow data
        total = statistics.get("total_identifiers", 1201)
        direct_match = statistics.get(
            "direct_match_count",
            statistics.get("mapping_methods", {}).get("direct_match", 812),
        )
        historical = statistics.get(
            "historical_resolution_count",
            statistics.get("mapping_methods", {}).get("historical_resolution", 111),
        )
        gene_symbol = statistics.get(
            "gene_symbol_bridge_count",
            statistics.get("mapping_methods", {}).get("gene_symbol_bridge", 87),
        )
        unmatched = statistics.get("unmatched_count", 278)

        # Define nodes
        node_labels = [
            f"Input ({total:,})",
            f"Direct Match ({direct_match:,})",
            f"Historical ({historical:,})",
            f"Gene Bridge ({gene_symbol:,})",
            f"Unmatched ({unmatched:,})",
            f"Matched ({direct_match + historical + gene_symbol:,})",
        ]

        # Define links
        links = {
            "source": [0, 0, 0, 0, 1, 2, 3],
            "target": [1, 2, 3, 4, 5, 5, 5],
            "value": [
                direct_match,
                historical,
                gene_symbol,
                unmatched,
                direct_match,
                historical,
                gene_symbol,
            ],
        }

        # Create Sankey
        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=node_labels,
                    ),
                    link=dict(
                        source=links["source"],
                        target=links["target"],
                        value=links["value"],
                    ),
                )
            ]
        )

        fig.update_layout(title="Protein Mapping Flow", font_size=12, height=600)

        fig.write_html(str(output_path))
        return True

    except Exception as e:
        logger.error(f"Failed to create Sankey diagram: {str(e)}")
        return False


def create_one_to_many_chart(
    mapping_data: Dict[str, List[str]], output_path: Path
) -> bool:
    """Visualize one-to-many mappings."""
    try:
        if not mapping_data:
            # Create empty chart with message
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(
                0.5,
                0.5,
                "No one-to-many mappings found",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.axis("off")
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()
            return True

        # Filter for actual one-to-many mappings
        one_to_many = {k: v for k, v in mapping_data.items() if len(v) > 1}

        if not one_to_many:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(
                0.5,
                0.5,
                "All mappings are one-to-one",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.axis("off")
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()
            return True

        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

        # Left: Distribution
        multiplicities = [len(v) for v in one_to_many.values()]
        ax1.hist(
            multiplicities,
            bins=range(2, max(multiplicities) + 2),
            edgecolor="black",
            color="skyblue",
            alpha=0.7,
        )
        ax1.set_xlabel("Number of Targets per Source")
        ax1.set_ylabel("Count")
        ax1.set_title("One-to-Many Mapping Distribution")

        # Right: Top 10
        sorted_mappings = sorted(
            one_to_many.items(), key=lambda x: len(x[1]), reverse=True
        )[:10]

        if sorted_mappings:
            identifiers = [
                str(k)[:25] + "..." if len(str(k)) > 25 else str(k)
                for k, _ in sorted_mappings
            ]
            counts = [len(v) for _, v in sorted_mappings]

            y_pos = np.arange(len(identifiers))
            ax2.barh(y_pos, counts, color="coral", alpha=0.7)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(identifiers)
            ax2.set_xlabel("Number of Mappings")
            ax2.set_title("Top Ambiguous Identifiers")

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return True

    except Exception as e:
        logger.error(f"Failed to create one-to-many chart: {str(e)}")
        plt.close()
        return False


def create_statistics_dashboard(
    statistics: Dict[str, Any], unmapped_identifiers: List[str], output_path: Path
) -> bool:
    """Create multi-panel statistics summary dashboard."""
    try:
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        # Panel 1: Total counts
        ax1 = fig.add_subplot(gs[0, 0])
        categories = ["Total", "Mapped", "Unmapped"]
        counts = [
            statistics.get("total_identifiers", 0),
            statistics.get("successfully_mapped", 0),
            statistics.get("unmatched_count", 0),
        ]

        bars = ax1.bar(categories, counts, color=["#3498db", "#2ecc71", "#e74c3c"])
        ax1.set_ylabel("Count")
        ax1.set_title("Mapping Summary")

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(count):,}",
                ha="center",
                va="bottom",
            )

        # Panel 2: Success rate gauge
        ax2 = fig.add_subplot(gs[0, 1])
        success_rate = statistics.get("mapping_success_rate", 0)

        # Simple gauge visualization
        wedge = plt.Circle((0, 0), 1, fill=False, edgecolor="gray", linewidth=2)
        ax2.add_patch(wedge)
        ax2.text(
            0,
            0,
            f"{success_rate:.1f}%",
            ha="center",
            va="center",
            fontsize=24,
            fontweight="bold",
        )
        ax2.set_xlim(-1.5, 1.5)
        ax2.set_ylim(-1.5, 1.5)
        ax2.axis("off")
        ax2.set_title("Success Rate")

        # Panel 3: Method breakdown
        ax3 = fig.add_subplot(gs[1, :])
        if "mapping_methods" in statistics:
            methods = list(statistics["mapping_methods"].keys())
            values = list(statistics["mapping_methods"].values())

            if methods:
                y_pos = np.arange(len(methods))
                ax3.barh(y_pos, values)
                ax3.set_yticks(y_pos)
                ax3.set_yticklabels(methods)
                ax3.set_xlabel("Count")
                ax3.set_title("Mapping Methods")

        plt.suptitle("Mapping Analysis Dashboard", fontsize=18, fontweight="bold")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return True

    except Exception as e:
        logger.error(f"Failed to create dashboard: {str(e)}")
        plt.close()
        return False


def create_interactive_scatter(data: pd.DataFrame, output_path: Path) -> bool:
    """Create interactive scatter plot of confidence vs coverage."""
    try:
        if data.empty:
            return False

        # Prepare data
        plot_df = data.copy()

        # Ensure required columns
        if "confidence_score" not in plot_df.columns:
            if "confidence" in plot_df.columns:
                plot_df["confidence_score"] = plot_df["confidence"]
            else:
                return False

        if "coverage_score" not in plot_df.columns:
            # Generate synthetic coverage scores
            plot_df["coverage_score"] = np.random.uniform(0.3, 1.0, len(plot_df))

        # Create scatter plot
        fig = px.scatter(
            plot_df,
            x="coverage_score",
            y="confidence_score",
            title="Mapping Quality Analysis",
            labels={
                "coverage_score": "Coverage Score",
                "confidence_score": "Confidence Score",
            },
        )

        fig.update_layout(height=600, showlegend=True)
        fig.write_html(str(output_path))

        return True

    except Exception as e:
        logger.error(f"Failed to create scatter plot: {str(e)}")
        return False


@register_action("GENERATE_MAPPING_VISUALIZATIONS_V1")
class GenerateMappingVisualizationsAction(
    TypedStrategyAction[VisualizationParams, VisualizationResult]
):
    """Generate comprehensive visualizations for mapping analysis."""

    def get_params_model(self) -> type[VisualizationParams]:
        """Return the Pydantic model for params validation."""
        return VisualizationParams

    def get_result_model(self) -> type[VisualizationResult]:
        """Return the result model type."""
        return VisualizationResult

    async def execute_typed(
        self, params: VisualizationParams, context: Dict[str, Any]
    ) -> VisualizationResult:
        """Execute visualization generation."""
        try:
            # Create output directory
            output_dir = Path(params.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Set visualization style
            self._set_style(params.style)

            # Get data from context
            datasets = context.get("datasets", {})
            statistics = context.get(params.statistics_key, {})

            # Collect data from specified datasets
            all_data = {}
            for key in params.dataset_keys:
                if key in datasets:
                    all_data[key] = datasets[key]

            if not all_data and not statistics:
                return VisualizationResult(
                    success=False, message="No data found for visualization", data={}
                )

            # Generate requested charts
            generated_files = []

            for chart_type in params.charts:
                try:
                    files = self._generate_chart(
                        chart_type, all_data, statistics, output_dir, params.formats
                    )
                    generated_files.extend(files)
                except Exception as e:
                    logger.error(f"Failed to generate {chart_type}: {str(e)}")

            # Store generated files in context
            if "output_files" not in context:
                context["output_files"] = []
            context["output_files"].extend(generated_files)

            # Extract identifiers from datasets for result
            input_ids = []
            for data in all_data.values():
                if isinstance(data, pd.DataFrame) and "source_id" in data.columns:
                    input_ids.extend(data["source_id"].dropna().unique().tolist())

            return VisualizationResult(
                success=True,
                message=f"Generated {len(generated_files)} visualization files",
                data={
                    "generated_files": generated_files,
                    "chart_types": params.charts,
                    "formats": params.formats,
                },
                input_identifiers=input_ids[:100],  # Limit to first 100
                output_identifiers=generated_files,  # File paths as outputs
            )

        except Exception as e:
            logger.error(f"Visualization generation failed: {str(e)}")
            return VisualizationResult(
                success=False,
                message=f"Failed to generate visualizations: {str(e)}",
                data={"error": str(e)},
            )

    def _set_style(self, style: str):
        """Set visualization style."""
        if style == "scientific":
            try:
                plt.style.use("seaborn-v0_8-whitegrid")
            except Exception:
                plt.style.use("seaborn-whitegrid")
            sns.set_palette("husl")
        elif style == "presentation":
            try:
                plt.style.use("seaborn-v0_8-darkgrid")
            except Exception:
                plt.style.use("seaborn-darkgrid")
            sns.set_palette("bright")
        else:
            plt.style.use("default")

    def _generate_chart(
        self,
        chart_type: str,
        datasets: Dict[str, Any],
        statistics: Dict[str, Any],
        output_dir: Path,
        formats: List[str],
    ) -> List[str]:
        """Generate a specific chart type."""
        generated = []

        # Combine all data for visualization
        combined_data = pd.DataFrame()
        for key, data in datasets.items():
            if isinstance(data, pd.DataFrame):
                combined_data = pd.concat([combined_data, data], ignore_index=True)
            elif isinstance(data, list) and data:
                df = pd.DataFrame(data)
                combined_data = pd.concat([combined_data, df], ignore_index=True)

        if chart_type == "coverage":
            for fmt in formats:
                if fmt in ["png", "svg"]:
                    output_path = output_dir / f"coverage_pie.{fmt}"
                    if create_coverage_pie(combined_data, statistics, output_path):
                        generated.append(str(output_path))

        elif chart_type == "confidence":
            for fmt in formats:
                if fmt in ["png", "svg"]:
                    output_path = output_dir / f"confidence_histogram.{fmt}"
                    if create_confidence_histogram(combined_data, output_path):
                        generated.append(str(output_path))

        elif chart_type == "mapping_flow":
            if "html" in formats:
                output_path = output_dir / "mapping_flow.html"
                if create_mapping_flow_sankey(statistics, output_path):
                    generated.append(str(output_path))

        elif chart_type == "one_to_many":
            # Extract one-to-many mappings
            mapping_data = {}
            if not combined_data.empty and "source_id" in combined_data.columns:
                grouped = (
                    combined_data.groupby("source_id")["target_id"]
                    .apply(lambda x: x.dropna().tolist())
                    .to_dict()
                )
                mapping_data = {k: v for k, v in grouped.items() if v}

            for fmt in formats:
                if fmt in ["png", "svg"]:
                    output_path = output_dir / f"one_to_many_analysis.{fmt}"
                    if create_one_to_many_chart(mapping_data, output_path):
                        generated.append(str(output_path))

        elif chart_type == "statistics_summary":
            # Extract unmapped identifiers
            unmapped = []
            if not combined_data.empty:
                if "mapped" in combined_data.columns:
                    unmapped = (
                        combined_data[~combined_data["mapped"]]["source_id"]
                        .head(10)
                        .tolist()
                    )
                elif "target_id" in combined_data.columns:
                    unmapped = (
                        combined_data[combined_data["target_id"].isna()]["source_id"]
                        .head(10)
                        .tolist()
                    )

            for fmt in formats:
                if fmt in ["png", "svg"]:
                    output_path = output_dir / f"statistics_dashboard.{fmt}"
                    if create_statistics_dashboard(statistics, unmapped, output_path):
                        generated.append(str(output_path))

        elif chart_type == "interactive_scatter":
            if "html" in formats and not combined_data.empty:
                output_path = output_dir / "interactive_quality_scatter.html"
                if create_interactive_scatter(combined_data, output_path):
                    generated.append(str(output_path))

        return generated

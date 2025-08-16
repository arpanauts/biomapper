"""
Generate interactive visualizations from mapping results with progressive analysis support.

This module provides comprehensive visualization capabilities for biological mapping results,
including traditional charts and progressive mapping analysis with waterfall charts, 
stage comparisons, and detailed statistics export.

Enhanced Features (2025):
- Progressive waterfall charts showing cumulative mapping improvement
- Stage-by-stage comparison visualizations
- Confidence score distribution analysis  
- Mapping method breakdown charts
- TSV statistics export with detailed metrics
- Machine-readable JSON summary reports
- Publication-quality SVG/PNG static exports

Progressive Visualization Support:
The action can generate specialized charts for multi-stage mapping workflows by processing
`context["progressive_stats"]` data. This enables analysis of how mapping rates improve
across different stages (e.g., direct matching, composite parsing, API resolution).

Example progressive data structure:
```python
progressive_stats = {
    "total_processed": 10000,
    "stages": {
        1: {
            "name": "Direct Match",
            "method": "Direct UniProt", 
            "new_matches": 6500,
            "confidence_avg": 1.00,
            "computation_time": "0.5s"
        },
        2: {
            "name": "Historical Resolution",
            "method": "Historical API",
            "new_matches": 1500, 
            "confidence_avg": 0.90,
            "computation_time": "12.3s"
        }
    }
}
```

Generated visualizations include:
- Waterfall chart: Cumulative improvement across stages
- Stage bars: New matches contributed by each stage
- Confidence distribution: Confidence scores across stages  
- Method breakdown: Proportion of matches by method type
- Statistics TSV: Detailed tabular data for further analysis
- JSON summary: Machine-readable metrics and metadata
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from pathlib import Path
from datetime import datetime
import json
import random
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)

# Optional imports - graceful degradation if not available
try:
    import plotly.graph_objects as go
    import plotly.io as pio

    PLOTLY_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints
    class go:
        class Figure:
            pass

    PLOTLY_AVAILABLE = False
    # Silently degrade - warning will be shown only if visualization is attempted
    pass


class ChartConfig(BaseModel):
    """Configuration for a single chart."""

    type: Literal[
        "bar",
        "line",
        "pie",
        "scatter",
        "histogram",
        "heatmap",
        "treemap",
        "summary_cards",
        "waterfall",
        "stage_bars",
        "confidence_distribution",
        "method_breakdown",
    ] = Field(
        ...,
        description="Chart type: bar, line, pie, scatter, histogram, heatmap, treemap, summary_cards, waterfall, stage_bars, confidence_distribution, method_breakdown",
    )
    title: str = Field(..., description="Chart title")
    data_key: str = Field(..., description="Dot-notation path to data")
    file_path: str = Field(..., description="Output filename")
    x_field: Optional[str] = Field(None, description="X-axis field")
    y_field: Optional[str] = Field(None, description="Y-axis field")
    color_field: Optional[str] = Field(None, description="Color grouping field")
    size_field: Optional[str] = Field(None, description="Size field for bubbles")
    group_by: Optional[str] = Field(None, description="Field to group data by")
    aggregation: str = Field(
        "sum", description="Aggregation method: sum, mean, count, max, min"
    )
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    limit: Optional[int] = Field(None, description="Limit number of data points")
    sampling_rate: Optional[float] = Field(
        None, description="Sample rate for large datasets (0.0-1.0)"
    )
    custom_style: Optional[Dict[str, Any]] = Field(
        None, description="Custom styling options"
    )
    interactive_features: Optional[Dict[str, Any]] = Field(
        None, description="Interactive feature configuration"
    )


class ProgressiveVisualizationParams(BaseModel):
    """Parameters for progressive mapping visualizations."""

    progressive_mode: bool = Field(
        False, description="Generate progressive mapping visualizations"
    )
    export_statistics_tsv: bool = Field(
        False, description="Export progressive statistics as TSV"
    )
    waterfall_chart: bool = Field(
        False, description="Generate waterfall progression chart"
    )
    stage_comparison: bool = Field(
        False, description="Generate stage-by-stage comparison charts"
    )
    confidence_distribution: bool = Field(
        False, description="Generate confidence distribution charts"
    )
    method_breakdown: bool = Field(
        False, description="Generate mapping method breakdown pie chart"
    )
    stage_prefix: str = Field("Stage", description="Prefix for stage names in charts")
    show_percentages: bool = Field(True, description="Show percentages in charts")
    show_improvements: bool = Field(
        True, description="Show improvement values in waterfall"
    )


class GenerateMappingVisualizationsParams(BaseModel):
    """Parameters for visualization generation."""

    charts: List[ChartConfig] = Field(..., description="List of charts to generate")
    output_directory: str = Field(..., description="Output directory for charts")
    format: str = Field(
        "plotly", description="Visualization format: plotly, chartjs, static"
    )
    theme: str = Field("plotly", description="Chart theme")
    custom_css: Optional[str] = Field(None, description="Custom CSS styles")
    create_dashboard: bool = Field(False, description="Create combined dashboard")
    dashboard_title: str = Field(
        "Mapping Analysis Dashboard", description="Dashboard title"
    )
    include_statistics: bool = Field(
        True, description="Include statistics in dashboard"
    )
    responsive: bool = Field(True, description="Make charts responsive")
    export_json: bool = Field(False, description="Export chart data as JSON")
    export_static: bool = Field(False, description="Export static image files")
    static_formats: List[str] = Field(["png"], description="Static export formats")
    plotly_config: Optional[Dict[str, Any]] = Field(
        None, description="Plotly-specific configuration"
    )
    embed_options: Optional[Dict[str, Any]] = Field(
        None, description="Chart embedding options"
    )
    progressive_params: Optional[ProgressiveVisualizationParams] = Field(
        None, description="Progressive visualization parameters"
    )


class GenerateMappingVisualizationsResult(BaseModel):
    """Result of visualization generation."""

    success: bool
    message: str
    charts_generated: int = 0
    file_paths: List[str] = Field(default_factory=list)
    dashboard_created: bool = False
    dashboard_path: Optional[str] = None
    data_points_processed: int = 0
    json_exports_created: bool = False
    static_exports_attempted: bool = False
    progressive_charts_created: int = 0
    progressive_tsv_exported: bool = False
    progressive_json_exported: bool = False
    warnings: List[str] = Field(default_factory=list)


@register_action("GENERATE_MAPPING_VISUALIZATIONS_V2")
class GenerateMappingVisualizationsAction(
    TypedStrategyAction[
        GenerateMappingVisualizationsParams, GenerateMappingVisualizationsResult
    ]
):
    """
    Generate interactive visualizations from biological mapping results with progressive analysis.

    Creates comprehensive charts, graphs, and interactive dashboards using Plotly or Chart.js
    to visualize mapping statistics, performance metrics, and data distributions. Enhanced
    with progressive mapping analysis capabilities for multi-stage workflows.

    Key Features:
    - Traditional chart types: bar, line, pie, scatter, histogram, heatmap, treemap
    - Progressive chart types: waterfall, stage_bars, confidence_distribution, method_breakdown
    - Multiple export formats: HTML (interactive), PNG, SVG (static), TSV (data), JSON (metadata)
    - Dashboard generation with embedded charts and statistics
    - Progressive analysis with stage-by-stage metrics tracking

    Progressive Mode Usage:
    When `progressive_params.progressive_mode=True`, the action automatically processes
    `context["progressive_stats"]` to generate:
    1. Waterfall chart showing cumulative mapping improvement across stages
    2. Stage comparison bars showing new matches per stage
    3. Confidence distribution line chart across stages
    4. Method breakdown pie chart showing contribution by method type
    5. TSV export with detailed stage-by-stage statistics
    6. JSON summary with computed metrics and metadata

    Chart Configuration:
    Traditional charts use ChartConfig objects specifying type, data source, styling, etc.
    Progressive charts are auto-generated based on progressive_params settings.

    Output Files (Progressive Mode):
    - progressive_waterfall.html/png/svg: Waterfall improvement chart
    - stage_comparison.html/png/svg: Stage contribution bars
    - confidence_distribution.html/png/svg: Confidence trend line
    - method_breakdown.html/png/svg: Method distribution pie
    - progressive_statistics.tsv: Detailed tabular statistics
    - progressive_summary.json: Computed metrics and metadata
    - dashboard.html: Combined interactive dashboard

    Example Strategy Usage:
    ```yaml
    - name: generate_progressive_visualizations
      action:
        type: GENERATE_MAPPING_VISUALIZATIONS_V2
        params:
          charts: []  # Traditional charts (optional)
          output_directory: "/results/visualizations"
          export_static: true
          static_formats: ["png", "svg"]
          progressive_params:
            progressive_mode: true
            export_statistics_tsv: true
            waterfall_chart: true
            stage_comparison: true
            confidence_distribution: true
            method_breakdown: true
    ```
    """

    def get_params_model(self) -> type[GenerateMappingVisualizationsParams]:
        """Get the parameters model."""
        return GenerateMappingVisualizationsParams

    def get_result_model(self) -> type[GenerateMappingVisualizationsResult]:
        """Get the result model."""
        return GenerateMappingVisualizationsResult

    async def execute_typed(
        self, params: GenerateMappingVisualizationsParams, context: Dict[str, Any]
    ) -> GenerateMappingVisualizationsResult:
        """Execute visualization generation."""
        try:
            # Handle different context types
            ctx = self._get_context_dict(context)

            # Check format availability
            if params.format == "plotly" and not PLOTLY_AVAILABLE:
                return GenerateMappingVisualizationsResult(
                    success=False,
                    message="Plotly not available. Install with: pip install plotly",
                )

            # Create output directory
            output_dir = Path(params.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Handle progressive visualizations
            progressive_data = []
            if params.progressive_params and params.progressive_params.progressive_mode:
                progressive_stats = ctx.get("progressive_stats")
                if progressive_stats:
                    progressive_data = self._process_progressive_stats(
                        progressive_stats
                    )

                    # Generate progressive charts if requested
                    if params.progressive_params.waterfall_chart and progressive_data:
                        waterfall_config = ChartConfig(
                            type="waterfall",
                            title="Progressive Mapping Improvement",
                            data_key="progressive_data",  # We'll inject this data
                            file_path="progressive_waterfall.html",
                        )
                        # Temporarily inject progressive data for chart generation
                        ctx["progressive_data"] = progressive_data
                        params.charts.append(waterfall_config)

                    if params.progressive_params.stage_comparison and progressive_data:
                        stage_config = ChartConfig(
                            type="stage_bars",
                            title="Stage-by-Stage Comparison",
                            data_key="progressive_data",
                            file_path="stage_comparison.html",
                        )
                        params.charts.append(stage_config)

                    if (
                        params.progressive_params.confidence_distribution
                        and progressive_data
                    ):
                        confidence_config = ChartConfig(
                            type="confidence_distribution",
                            title="Confidence Score Distribution",
                            data_key="progressive_data",
                            file_path="confidence_distribution.html",
                        )
                        params.charts.append(confidence_config)

                    if params.progressive_params.method_breakdown and progressive_data:
                        method_config = ChartConfig(
                            type="method_breakdown",
                            title="Mapping Method Breakdown",
                            data_key="progressive_data",
                            file_path="method_breakdown.html",
                        )
                        params.charts.append(method_config)

            # Generate charts
            charts_generated = 0
            file_paths = []
            total_data_points = 0
            warnings = []

            for chart_config in params.charts:
                try:
                    # Get chart data
                    chart_data = self._get_chart_data(chart_config, ctx)

                    if chart_data is None:
                        warnings.append(
                            f"Data not found for chart '{chart_config.title}'"
                        )
                        continue

                    # Process and prepare data
                    processed_data, data_points = self._process_chart_data(
                        chart_config, chart_data
                    )
                    total_data_points += data_points

                    # Generate chart based on format
                    if params.format == "plotly":
                        file_path = await self._generate_plotly_chart(
                            chart_config, processed_data, output_dir, params
                        )
                    elif params.format == "chartjs":
                        file_path = await self._generate_chartjs_chart(
                            chart_config, processed_data, output_dir, params
                        )
                    else:
                        warnings.append(f"Unsupported format: {params.format}")
                        continue

                    if file_path:
                        file_paths.append(str(file_path))
                        charts_generated += 1

                        # Export JSON if requested
                        if params.export_json:
                            await self._export_chart_json(
                                chart_config, processed_data, output_dir
                            )

                except Exception as e:
                    warnings.append(
                        f"Failed to generate chart '{chart_config.title}': {str(e)}"
                    )
                    logger.error(f"Chart generation error: {str(e)}")

            # Export progressive data if requested
            if params.progressive_params and progressive_data:
                if params.progressive_params.export_statistics_tsv:
                    await self._export_progressive_tsv(progressive_data, output_dir)

                # Always export JSON summary for progressive mode
                await self._export_progressive_json_summary(
                    progressive_data, output_dir
                )

            # Create dashboard if requested
            dashboard_created = False
            dashboard_path = None

            if params.create_dashboard and file_paths:
                dashboard_path = await self._create_dashboard(
                    params, file_paths, output_dir, ctx
                )
                dashboard_created = dashboard_path is not None

            # Store results in context
            if "output_files" not in ctx:
                ctx["output_files"] = {}

            ctx["output_files"]["visualizations"] = {
                "charts": file_paths,
                "dashboard": dashboard_path,
                "directory": str(output_dir),
            }

            if "statistics" not in ctx:
                ctx["statistics"] = {}

            ctx["statistics"]["visualization_generation"] = {
                "charts_generated": charts_generated,
                "data_points_processed": total_data_points,
                "formats_used": [params.format],
                "warnings_count": len(warnings),
            }

            # Count progressive charts
            progressive_charts_count = 0
            if params.progressive_params and progressive_data:
                if params.progressive_params.waterfall_chart:
                    progressive_charts_count += 1
                if params.progressive_params.stage_comparison:
                    progressive_charts_count += 1
                if params.progressive_params.confidence_distribution:
                    progressive_charts_count += 1
                if params.progressive_params.method_breakdown:
                    progressive_charts_count += 1

            logger.info(
                f"Generated {charts_generated} visualizations "
                f"({total_data_points} data points) in {output_dir}"
                + (
                    f" including {progressive_charts_count} progressive charts"
                    if progressive_charts_count > 0
                    else ""
                )
            )

            return GenerateMappingVisualizationsResult(
                success=True,
                message=f"Generated {charts_generated} visualizations successfully"
                + (
                    f" including {progressive_charts_count} progressive charts"
                    if progressive_charts_count > 0
                    else ""
                ),
                charts_generated=charts_generated,
                file_paths=file_paths,
                dashboard_created=dashboard_created,
                dashboard_path=dashboard_path,
                data_points_processed=total_data_points,
                json_exports_created=params.export_json,
                static_exports_attempted=params.export_static,
                progressive_charts_created=progressive_charts_count,
                progressive_tsv_exported=params.progressive_params.export_statistics_tsv
                if params.progressive_params
                else False,
                progressive_json_exported=bool(
                    params.progressive_params and progressive_data
                ),
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            return GenerateMappingVisualizationsResult(
                success=False, message=f"Error: {str(e)}"
            )

    def _get_context_dict(self, context: Any) -> Dict[str, Any]:
        """Get dictionary from context."""
        if isinstance(context, dict):
            return context
        elif hasattr(context, "_dict"):
            return context._dict
        else:
            return {"datasets": {}, "statistics": {}}

    def _process_progressive_stats(
        self, progressive_stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process progressive statistics for visualization."""
        if not progressive_stats or "stages" not in progressive_stats:
            return []

        stages = progressive_stats["stages"]
        total_processed = progressive_stats.get("total_processed", 1)

        results = []
        cumulative_matched = 0
        prev_rate = 0.0

        for stage_num in sorted(stages.keys()):
            stage = stages[stage_num]

            # Calculate metrics
            new_matches = stage.get("new_matches", stage.get("matched", 0))
            cumulative_matched += new_matches
            cumulative_rate = (
                (cumulative_matched / total_processed) * 100
                if total_processed > 0
                else 0
            )
            improvement = cumulative_rate - prev_rate

            stage_data = {
                "stage_number": stage_num,
                "stage_name": stage.get("name", f"Stage {stage_num}"),
                "method": stage.get("method", "Unknown"),
                "new_matches": new_matches,
                "cumulative_matched": cumulative_matched,
                "cumulative_rate": cumulative_rate,
                "improvement": improvement,
                "computation_time": stage.get("computation_time", "0s"),
                "confidence_avg": stage.get("confidence_avg", 1.0),
                "total_processed": total_processed,
            }

            results.append(stage_data)
            prev_rate = cumulative_rate

        return results

    def _get_chart_data(
        self, chart_config: ChartConfig, context: Dict[str, Any]
    ) -> Any:
        """Get data for chart using dot notation path."""
        keys = chart_config.data_key.split(".")
        data = context

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None

        return data

    def _process_chart_data(
        self, chart_config: ChartConfig, data: Any
    ) -> tuple[Any, int]:
        """Process and prepare data for chart generation."""
        if not data:
            return None, 0

        # Count original data points
        if isinstance(data, list):
            original_count = len(data)
        elif isinstance(data, dict):
            original_count = len(data)
        else:
            original_count = 1

        # Apply sampling if specified
        if chart_config.sampling_rate and isinstance(data, list):
            sample_size = max(1, int(len(data) * chart_config.sampling_rate))
            data = random.sample(data, sample_size)

        # Apply limit if specified
        if chart_config.limit and isinstance(data, list):
            data = data[: chart_config.limit]

        # Apply sorting if specified
        if chart_config.sort_by and isinstance(data, list):
            if all(
                isinstance(item, dict) and chart_config.sort_by in item for item in data
            ):
                data = sorted(data, key=lambda x: x[chart_config.sort_by])

        # Apply grouping and aggregation if specified
        if chart_config.group_by and isinstance(data, list):
            data = self._apply_grouping(data, chart_config)

        return data, original_count

    def _apply_grouping(
        self, data: List[Dict], chart_config: ChartConfig
    ) -> List[Dict]:
        """Apply grouping and aggregation to data."""
        if not chart_config.group_by:
            return data

        # Group data
        groups = {}
        for item in data:
            if chart_config.group_by in item:
                group_key = item[chart_config.group_by]
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(item)

        # Aggregate groups
        aggregated = []
        for group_key, group_items in groups.items():
            agg_item = {chart_config.group_by: group_key}

            # Apply aggregation to numeric fields
            for field in [
                chart_config.x_field,
                chart_config.y_field,
                chart_config.size_field,
            ]:
                if field and field != chart_config.group_by:
                    values = [
                        item.get(field, 0)
                        for item in group_items
                        if isinstance(item.get(field), (int, float))
                    ]
                    if values:
                        if chart_config.aggregation == "sum":
                            agg_item[field] = sum(values)
                        elif chart_config.aggregation == "mean":
                            agg_item[field] = sum(values) / len(values)
                        elif chart_config.aggregation == "count":
                            agg_item[field] = len(values)
                        elif chart_config.aggregation == "max":
                            agg_item[field] = max(values)
                        elif chart_config.aggregation == "min":
                            agg_item[field] = min(values)
                        else:
                            agg_item[field] = sum(values)

            aggregated.append(agg_item)

        return aggregated

    async def _generate_plotly_chart(
        self,
        chart_config: ChartConfig,
        data: Any,
        output_dir: Path,
        params: GenerateMappingVisualizationsParams,
    ) -> Optional[Path]:
        """Generate chart using Plotly."""
        if not PLOTLY_AVAILABLE:
            return None

        try:
            # Create figure based on chart type
            if chart_config.type == "bar":
                fig = self._create_plotly_bar(chart_config, data)
            elif chart_config.type == "line":
                fig = self._create_plotly_line(chart_config, data)
            elif chart_config.type == "pie":
                fig = self._create_plotly_pie(chart_config, data)
            elif chart_config.type == "scatter":
                fig = self._create_plotly_scatter(chart_config, data)
            elif chart_config.type == "histogram":
                fig = self._create_plotly_histogram(chart_config, data)
            elif chart_config.type == "heatmap":
                fig = self._create_plotly_heatmap(chart_config, data)
            elif chart_config.type == "treemap":
                fig = self._create_plotly_treemap(chart_config, data)
            elif chart_config.type == "summary_cards":
                fig = self._create_plotly_summary_cards(chart_config, data)
            elif chart_config.type == "waterfall":
                fig = self._create_plotly_waterfall(chart_config, data)
            elif chart_config.type == "stage_bars":
                fig = self._create_plotly_stage_bars(chart_config, data)
            elif chart_config.type == "confidence_distribution":
                fig = self._create_plotly_confidence_distribution(chart_config, data)
            elif chart_config.type == "method_breakdown":
                fig = self._create_plotly_method_breakdown(chart_config, data)
            else:
                logger.warning(f"Unsupported chart type: {chart_config.type}")
                return None

            if not fig:
                return None

            # Apply theme and styling
            self._apply_plotly_styling(fig, chart_config, params)

            # Configure interactivity
            if chart_config.interactive_features:
                self._configure_plotly_interactivity(
                    fig, chart_config.interactive_features
                )

            # Set up Plotly configuration
            plotly_config = params.plotly_config or {}
            plotly_config.update(
                {
                    "displayModeBar": True,
                    "displaylogo": False,
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": chart_config.filename.replace(".html", ""),
                        "height": 500,
                        "width": 700,
                        "scale": 1,
                    },
                }
            )

            # Save chart
            output_file = output_dir / chart_config.filename

            if params.embed_options:
                fig.write_html(
                    output_file,
                    config=plotly_config,
                    include_plotlyjs=params.embed_options.get("include_plotlyjs", True),
                    div_id=params.embed_options.get("div_id"),
                    full_html=True,
                )
            else:
                fig.write_html(output_file, config=plotly_config)

            # Export static images if requested
            if params.export_static:
                await self._export_static_images(
                    fig, chart_config, output_dir, params.static_formats
                )

            return output_file

        except Exception as e:
            logger.error(f"Error creating Plotly chart: {str(e)}")
            return None

    def _create_plotly_bar(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly bar chart."""
        if isinstance(data, dict):
            # Dictionary data - keys as x, values as y
            x_values = list(data.keys())
            y_values = list(data.values())
        elif isinstance(data, list) and data:
            # List of dictionaries
            x_values = [
                item.get(chart_config.x_field, str(i)) for i, item in enumerate(data)
            ]
            y_values = [item.get(chart_config.y_field, 1) for item in data]
        else:
            return None

        fig = go.Figure(data=[go.Bar(x=x_values, y=y_values, name=chart_config.title)])

        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "Category",
            yaxis_title=chart_config.y_field or "Value",
        )

        return fig

    def _create_plotly_line(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly line chart."""
        if isinstance(data, list) and data:
            x_values = [
                item.get(chart_config.x_field, i) for i, item in enumerate(data)
            ]
            y_values = [item.get(chart_config.y_field, 0) for item in data]
        else:
            return None

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines+markers",
                    name=chart_config.title,
                )
            ]
        )

        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "X",
            yaxis_title=chart_config.y_field or "Y",
        )

        return fig

    def _create_plotly_pie(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly pie chart."""
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        elif isinstance(data, list) and data:
            labels = [
                item.get(chart_config.x_field, f"Item {i}")
                for i, item in enumerate(data)
            ]
            values = [item.get(chart_config.y_field, 1) for item in data]
        else:
            return None

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,  # Donut chart
                )
            ]
        )

        fig.update_layout(title=chart_config.title)

        return fig

    def _create_plotly_scatter(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly scatter plot."""
        if not isinstance(data, list) or not data:
            return None

        x_values = [item.get(chart_config.x_field, 0) for item in data]
        y_values = [item.get(chart_config.y_field, 0) for item in data]

        scatter_kwargs = {
            "x": x_values,
            "y": y_values,
            "mode": "markers",
            "name": chart_config.title,
        }

        # Add size if specified
        if chart_config.size_field:
            sizes = [item.get(chart_config.size_field, 10) for item in data]
            scatter_kwargs["marker"] = {"size": sizes}

        # Add color if specified
        if chart_config.color_field:
            colors = [item.get(chart_config.color_field, "blue") for item in data]
            if "marker" not in scatter_kwargs:
                scatter_kwargs["marker"] = {}
            scatter_kwargs["marker"]["color"] = colors

        fig = go.Figure(data=[go.Scatter(**scatter_kwargs)])

        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "X",
            yaxis_title=chart_config.y_field or "Y",
        )

        return fig

    def _create_plotly_histogram(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly histogram."""
        if isinstance(data, dict):
            # Histogram from binned data
            x_values = list(data.keys())
            y_values = list(data.values())
            fig = go.Figure(data=[go.Bar(x=x_values, y=y_values)])
        elif isinstance(data, list) and data:
            # Histogram from raw data
            values = [
                item.get(chart_config.x_field, 0)
                for item in data
                if chart_config.x_field in item
            ]
            fig = go.Figure(data=[go.Histogram(x=values)])
        else:
            return None

        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "Value",
            yaxis_title="Count",
        )

        return fig

    def _create_plotly_heatmap(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly heatmap."""
        # This is a placeholder - real implementation would need matrix data
        fig = go.Figure(
            data=go.Heatmap(
                z=[[1, 20, 30], [20, 1, 60], [30, 60, 1]],
                x=["Method A", "Method B", "Method C"],
                y=["Category 1", "Category 2", "Category 3"],
                colorscale="Viridis",
            )
        )

        fig.update_layout(title=chart_config.title)

        return fig

    def _create_plotly_treemap(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly treemap."""
        if not isinstance(data, dict):
            return None

        labels = list(data.keys())
        values = list(data.values())

        fig = go.Figure(
            go.Treemap(labels=labels, values=values, parents=[""] * len(labels))
        )

        fig.update_layout(title=chart_config.title)

        return fig

    def _create_plotly_summary_cards(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create summary cards visualization."""
        if not isinstance(data, dict):
            return None

        # Create a simple table-like visualization for summary data
        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(values=["Metric", "Value"]),
                    cells=dict(
                        values=[
                            list(data.keys()),
                            [
                                f"{v:.3f}" if isinstance(v, float) else str(v)
                                for v in data.values()
                            ],
                        ]
                    ),
                )
            ]
        )

        fig.update_layout(title=chart_config.title)

        return fig

    def _create_plotly_waterfall(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create Plotly waterfall chart for progressive mapping improvement."""
        if not isinstance(data, list) or not data:
            return None

        # Extract waterfall data
        stages = [
            item.get("stage_name", f"Stage {item.get('stage_number', i)}")
            for i, item in enumerate(data)
        ]
        improvements = [item.get("improvement", 0) for item in data]
        cumulative_rates = [item.get("cumulative_rate", 0) for item in data]

        # Create measure types - first is absolute, rest are relative
        measures = ["absolute"] + ["relative"] * (len(improvements) - 1)

        # Create hover text
        hover_text = [
            f"Stage: {stages[i]}<br>Improvement: +{improvements[i]:.1f}%<br>Cumulative: {cumulative_rates[i]:.1f}%"
            for i in range(len(stages))
        ]

        fig = go.Figure(
            go.Waterfall(
                name="Mapping Progress",
                orientation="v",
                measure=measures,
                x=stages,
                y=improvements,
                text=[
                    f"+{imp:.1f}%" if imp > 0 else f"{imp:.1f}%" for imp in improvements
                ],
                textposition="outside",
                hovertext=hover_text,
                hoverinfo="text",
                increasing={"marker": {"color": "#2E8B57"}},
                decreasing={"marker": {"color": "#DC143C"}},
                totals={"marker": {"color": "#4682B4"}},
            )
        )

        fig.update_layout(
            title=chart_config.title,
            xaxis_title="Mapping Stage",
            yaxis_title="Improvement (%)",
            showlegend=False,
            yaxis={"ticksuffix": "%"},
        )

        return fig

    def _create_plotly_stage_bars(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create stage comparison bar chart."""
        if not isinstance(data, list) or not data:
            return None

        stages = [
            item.get("stage_name", f"Stage {item.get('stage_number', i)}")
            for i, item in enumerate(data)
        ]
        new_matches = [item.get("new_matches", 0) for item in data]
        methods = [item.get("method", "Unknown") for item in data]

        # Create hover text
        hover_text = [
            f"Stage: {stages[i]}<br>Method: {methods[i]}<br>New Matches: {new_matches[i]:,}"
            for i in range(len(stages))
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=stages,
                    y=new_matches,
                    text=[f"{val:,}" for val in new_matches],
                    textposition="auto",
                    hovertext=hover_text,
                    hoverinfo="text",
                    marker={"color": "#4682B4"},
                )
            ]
        )

        fig.update_layout(
            title=chart_config.title,
            xaxis_title="Mapping Stage",
            yaxis_title="New Matches",
            showlegend=False,
        )

        return fig

    def _create_plotly_confidence_distribution(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create confidence score distribution chart."""
        if not isinstance(data, list) or not data:
            return None

        stages = [
            item.get("stage_name", f"Stage {item.get('stage_number', i)}")
            for i, item in enumerate(data)
        ]
        confidences = [item.get("confidence_avg", 1.0) for item in data]

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=stages,
                    y=confidences,
                    mode="lines+markers",
                    name="Average Confidence",
                    line={"color": "#FF6B6B", "width": 3},
                    marker={"size": 10, "color": "#FF6B6B"},
                )
            ]
        )

        fig.update_layout(
            title=chart_config.title,
            xaxis_title="Mapping Stage",
            yaxis_title="Average Confidence Score",
            yaxis={"range": [0, 1.1]},
            showlegend=False,
        )

        return fig

    def _create_plotly_method_breakdown(
        self, chart_config: ChartConfig, data: Any
    ) -> Optional[go.Figure]:
        """Create method breakdown pie chart."""
        if not isinstance(data, list) or not data:
            return None

        # Group by method and sum matches
        method_totals = {}
        for item in data:
            method = item.get("method", "Unknown")
            matches = item.get("new_matches", 0)
            method_totals[method] = method_totals.get(method, 0) + matches

        methods = list(method_totals.keys())
        totals = list(method_totals.values())

        # Calculate percentages
        total_matches = sum(totals) if totals else 1
        percentages = [total / total_matches * 100 for total in totals]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=methods,
                    values=totals,
                    text=[f"{pct:.1f}%" for pct in percentages],
                    textinfo="label+text",
                    hole=0.3,
                    marker={
                        "colors": [
                            "#FF9999",
                            "#66B2FF",
                            "#99FF99",
                            "#FFCC99",
                            "#FF99CC",
                        ]
                    },
                )
            ]
        )

        fig.update_layout(title=chart_config.title, showlegend=True)

        return fig

    def _apply_plotly_styling(
        self,
        fig: go.Figure,
        chart_config: ChartConfig,
        params: GenerateMappingVisualizationsParams,
    ):
        """Apply styling to Plotly figure."""
        # Apply theme
        if hasattr(pio, "templates") and params.theme in pio.templates:
            fig.update_layout(template=params.theme)

        # Apply custom styling
        if chart_config.custom_style:
            style = chart_config.custom_style

            layout_updates = {}

            if "background_color" in style:
                layout_updates["plot_bgcolor"] = style["background_color"]
                layout_updates["paper_bgcolor"] = style["background_color"]

            if "font_family" in style:
                layout_updates["font"] = {"family": style["font_family"]}

            if layout_updates:
                fig.update_layout(**layout_updates)

            # Apply color palette
            if "color_palette" in style and hasattr(fig, "data"):
                for i, trace in enumerate(fig.data):
                    if i < len(style["color_palette"]):
                        if hasattr(trace, "marker"):
                            trace.marker.color = style["color_palette"][i]
                        elif hasattr(trace, "line"):
                            trace.line.color = style["color_palette"][i]

        # Make responsive if requested
        if params.responsive:
            fig.update_layout(autosize=True, margin=dict(l=0, r=0, t=30, b=0))

    def _configure_plotly_interactivity(self, fig: go.Figure, features: Dict[str, Any]):
        """Configure interactive features for Plotly chart."""
        config_updates = {}

        if features.get("zoom", True):
            config_updates["scrollZoom"] = True

        if not features.get("pan", True):
            config_updates["scrollZoom"] = False

        # Note: This would be applied via the config parameter in write_html
        # Store for later use
        fig._config_updates = config_updates

    async def _generate_chartjs_chart(
        self,
        chart_config: ChartConfig,
        data: Any,
        output_dir: Path,
        params: GenerateMappingVisualizationsParams,
    ) -> Optional[Path]:
        """Generate chart using Chart.js."""
        # Create HTML with Chart.js
        chart_data = self._prepare_chartjs_data(chart_config, data)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{chart_config.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {{
            position: relative;
            height: 400px;
            width: 100%;
        }}
        {params.custom_css or ''}
    </style>
</head>
<body>
    <div class="chart-container">
        <canvas id="chart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('chart').getContext('2d');
        new Chart(ctx, {chart_data});
    </script>
</body>
</html>
"""

        output_file = output_dir / chart_config.filename
        output_file.write_text(html_content)

        return output_file

    def _prepare_chartjs_data(self, chart_config: ChartConfig, data: Any) -> str:
        """Prepare data for Chart.js format."""
        # Convert data to Chart.js format
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        elif isinstance(data, list) and data:
            labels = [
                item.get(chart_config.x_field, f"Item {i}")
                for i, item in enumerate(data)
            ]
            values = [item.get(chart_config.y_field, 1) for item in data]
        else:
            labels = []
            values = []

        chart_type = chart_config.type
        if chart_type == "bar":
            chartjs_type = "bar"
        elif chart_type == "line":
            chartjs_type = "line"
        elif chart_type == "pie":
            chartjs_type = "pie"
        else:
            chartjs_type = "bar"

        chart_data = {
            "type": chartjs_type,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": chart_config.title,
                        "data": values,
                        "backgroundColor": [
                            "rgba(255, 99, 132, 0.2)",
                            "rgba(54, 162, 235, 0.2)",
                            "rgba(255, 205, 86, 0.2)",
                            "rgba(75, 192, 192, 0.2)",
                        ],
                        "borderColor": [
                            "rgba(255, 99, 132, 1)",
                            "rgba(54, 162, 235, 1)",
                            "rgba(255, 205, 86, 1)",
                            "rgba(75, 192, 192, 1)",
                        ],
                        "borderWidth": 1,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "plugins": {"title": {"display": True, "text": chart_config.title}},
            },
        }

        return json.dumps(chart_data)

    async def _export_chart_json(
        self, chart_config: ChartConfig, data: Any, output_dir: Path
    ):
        """Export chart data as JSON."""
        json_file = output_dir / chart_config.filename.replace(".html", ".json")

        export_data = {
            "title": chart_config.title,
            "type": chart_config.type,
            "data": data,
            "config": chart_config.dict(),
            "exported": datetime.now().isoformat(),
        }

        json_file.write_text(json.dumps(export_data, indent=2))

    async def _export_progressive_tsv(
        self, progressive_data: List[Dict[str, Any]], output_dir: Path
    ):
        """Export progressive statistics as TSV."""
        if not progressive_data:
            return

        tsv_file = output_dir / "progressive_statistics.tsv"

        # Convert to DataFrame for easy TSV export
        df = pd.DataFrame(progressive_data)

        # Format the data for TSV
        df["cumulative_rate"] = df["cumulative_rate"].apply(lambda x: f"{x:.1f}%")
        df["improvement"] = df["improvement"].apply(lambda x: f"{x:.1f}%")
        df["confidence_avg"] = df["confidence_avg"].apply(lambda x: f"{x:.3f}")

        # Export to TSV
        df.to_csv(tsv_file, sep="\t", index=False)
        logger.info(f"Exported progressive statistics to {tsv_file}")

    async def _export_progressive_json_summary(
        self, progressive_data: List[Dict[str, Any]], output_dir: Path
    ):
        """Export machine-readable JSON summary."""
        if not progressive_data:
            return

        json_file = output_dir / "progressive_summary.json"

        # Calculate summary metrics
        total_stages = len(progressive_data)
        final_rate = progressive_data[-1]["cumulative_rate"] if progressive_data else 0
        total_improvement = sum(item["improvement"] for item in progressive_data)
        avg_confidence = (
            sum(item["confidence_avg"] for item in progressive_data)
            / len(progressive_data)
            if progressive_data
            else 0
        )

        summary = {
            "summary": {
                "total_stages": total_stages,
                "final_mapping_rate": f"{final_rate:.1f}%",
                "total_improvement": f"{total_improvement:.1f}%",
                "average_confidence": f"{avg_confidence:.3f}",
                "total_processed": progressive_data[0]["total_processed"]
                if progressive_data
                else 0,
            },
            "stage_details": progressive_data,
            "exported": datetime.now().isoformat(),
        }

        json_file.write_text(json.dumps(summary, indent=2))
        logger.info(f"Exported progressive summary to {json_file}")

    async def _export_static_images(
        self,
        fig: go.Figure,
        chart_config: ChartConfig,
        output_dir: Path,
        formats: List[str],
    ):
        """Export static image files."""
        try:
            base_name = chart_config.filename.replace(".html", "")

            for fmt in formats:
                if hasattr(fig, "write_image"):
                    output_file = output_dir / f"{base_name}.{fmt}"
                    fig.write_image(output_file, format=fmt)
                else:
                    logger.warning(
                        "Static export not available - install kaleido: pip install kaleido"
                    )
                    break
        except Exception as e:
            logger.warning(f"Static export failed: {str(e)}")

    async def _create_dashboard(
        self,
        params: GenerateMappingVisualizationsParams,
        chart_files: List[str],
        output_dir: Path,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Create combined dashboard with all charts."""
        try:
            dashboard_file = output_dir / "dashboard.html"

            # Generate chart iframes
            chart_iframes = []
            for chart_file in chart_files:
                chart_name = Path(chart_file).name
                chart_iframes.append(
                    f"""
                    <div class="chart-frame">
                        <iframe src="{chart_name}" width="100%" height="500" frameborder="0"></iframe>
                    </div>
                """
                )

            # Generate statistics if requested
            stats_section = ""
            if params.include_statistics and "statistics" in context:
                stats = context["statistics"]
                stats_section = f"""
                <div class="statistics-section">
                    <h2>Analysis Statistics</h2>
                    <pre>{json.dumps(stats, indent=2)}</pre>
                </div>
                """

            # Create dashboard HTML
            dashboard_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{params.dashboard_title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
        .chart-frame {{
            background: white;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .statistics-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        {params.custom_css or ''}
    </style>
</head>
<body>
    <div class="container">
        <h1>{params.dashboard_title}</h1>
        {stats_section}
        {''.join(chart_iframes)}
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

            dashboard_file.write_text(dashboard_content)
            return str(dashboard_file)

        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return None

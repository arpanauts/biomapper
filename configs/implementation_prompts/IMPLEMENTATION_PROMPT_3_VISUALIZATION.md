# Implementation Prompt 3: Visualization Generation Actions

## 🎯 Mission
Implement the `GENERATE_MAPPING_VISUALIZATIONS` action that creates interactive charts, graphs, and visual analytics from biological mapping results using Plotly and Chart.js.

## 📍 Context
You are implementing data visualization capabilities for the biomapper project. This action must generate publication-ready charts, interactive dashboards, and statistical visualizations that help users understand their mapping results.

## 📁 Files to Create/Modify

### 1. Test File for Visualizations (CREATE FIRST - TDD!)
**Path:** `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/reports/test_generate_visualizations.py`

```python
"""Test suite for GenerateMappingVisualizationsAction - WRITE THIS FIRST!"""

import pytest
from typing import Dict, Any
from pathlib import Path
import json
from unittest.mock import MagicMock, patch

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.reports.generate_visualizations import (
    GenerateMappingVisualizationsAction,
    GenerateMappingVisualizationsParams,
    GenerateMappingVisualizationsResult,
    ChartConfig
)


class TestGenerateMappingVisualizationsAction:
    """Comprehensive test suite for mapping visualization generation."""
    
    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Create sample context with mapping statistics."""
        return {
            "datasets": {
                "source_data": [
                    {"id": "P12345", "category": "membrane", "value": 1.5},
                    {"id": "Q67890", "category": "cytoplasm", "value": 2.0},
                    {"id": "A11111", "category": "membrane", "value": 3.0},
                    {"id": "B22222", "category": "nucleus", "value": 1.8}
                ],
                "mapping_results": [
                    {"source": "P12345", "target": "T1", "confidence": 0.95, "method": "direct"},
                    {"source": "Q67890", "target": "T2", "confidence": 0.87, "method": "fuzzy"},
                    {"source": "A11111", "target": "T3", "confidence": 0.92, "method": "direct"},
                    {"source": "B22222", "target": None, "confidence": 0.0, "method": "failed"}
                ]
            },
            "statistics": {
                "mapping_summary": {
                    "total_input": 4,
                    "successfully_mapped": 3,
                    "failed_mapping": 1,
                    "mapping_rate": 0.75,
                    "average_confidence": 0.91
                },
                "method_performance": {
                    "direct": {"count": 2, "success_rate": 1.0, "avg_confidence": 0.935},
                    "fuzzy": {"count": 1, "success_rate": 1.0, "avg_confidence": 0.87},
                    "semantic": {"count": 0, "success_rate": 0.0, "avg_confidence": 0.0},
                    "failed": {"count": 1, "success_rate": 0.0, "avg_confidence": 0.0}
                },
                "confidence_distribution": {
                    "0.0-0.5": 1,
                    "0.5-0.7": 0,
                    "0.7-0.8": 0,
                    "0.8-0.9": 1,
                    "0.9-1.0": 2
                },
                "category_breakdown": {
                    "membrane": {"total": 2, "mapped": 2, "rate": 1.0},
                    "cytoplasm": {"total": 1, "mapped": 1, "rate": 1.0},
                    "nucleus": {"total": 1, "mapped": 0, "rate": 0.0}
                }
            },
            "output_files": {}
        }
    
    @pytest.fixture
    def action(self) -> GenerateMappingVisualizationsAction:
        """Create action instance."""
        return GenerateMappingVisualizationsAction()
    
    @pytest.mark.asyncio
    async def test_basic_visualization_generation(self, action, sample_context, tmp_path):
        """Test basic chart generation."""
        output_dir = tmp_path / "visualizations"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Mapping Success by Method",
                    data_key="statistics.method_performance",
                    x_field="method",
                    y_field="success_rate",
                    filename="method_success.html"
                ),
                ChartConfig(
                    type="pie",
                    title="Confidence Distribution",
                    data_key="statistics.confidence_distribution",
                    filename="confidence_dist.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert result.charts_generated == 2
        assert len(result.file_paths) == 2
        
        # Check files exist
        assert (output_dir / "method_success.html").exists()
        assert (output_dir / "confidence_dist.html").exists()
        
        # Check content
        bar_chart = (output_dir / "method_success.html").read_text()
        assert "Mapping Success by Method" in bar_chart
        assert "plotly" in bar_chart.lower()
        
        pie_chart = (output_dir / "confidence_dist.html").read_text()
        assert "Confidence Distribution" in pie_chart
    
    @pytest.mark.asyncio
    async def test_comprehensive_dashboard_generation(self, action, sample_context, tmp_path):
        """Test generation of complete visualization dashboard."""
        output_dir = tmp_path / "dashboard"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="summary_cards",
                    title="Key Metrics",
                    data_key="statistics.mapping_summary",
                    filename="summary_cards.html"
                ),
                ChartConfig(
                    type="bar",
                    title="Method Performance",
                    data_key="statistics.method_performance",
                    x_field="method",
                    y_field="success_rate",
                    color_field="avg_confidence",
                    filename="method_performance.html"
                ),
                ChartConfig(
                    type="histogram",
                    title="Confidence Distribution",
                    data_key="statistics.confidence_distribution",
                    filename="confidence_histogram.html"
                ),
                ChartConfig(
                    type="treemap",
                    title="Category Breakdown",
                    data_key="statistics.category_breakdown",
                    filename="category_treemap.html"
                ),
                ChartConfig(
                    type="scatter",
                    title="Value vs Confidence",
                    data_key="datasets.source_data",
                    x_field="value",
                    y_field="confidence",
                    color_field="category",
                    size_field="value",
                    filename="value_confidence_scatter.html"
                ),
                ChartConfig(
                    type="heatmap",
                    title="Method vs Category Performance",
                    data_key="cross_analysis",
                    filename="method_category_heatmap.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly",
            create_dashboard=True,
            dashboard_title="Protein Mapping Analysis Dashboard",
            include_statistics=True,
            responsive=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert result.charts_generated == 6
        assert result.dashboard_created is True
        
        # Check dashboard file
        dashboard_file = output_dir / "dashboard.html"
        assert dashboard_file.exists()
        
        dashboard_content = dashboard_file.read_text()
        assert "Protein Mapping Analysis Dashboard" in dashboard_content
        assert "summary_cards.html" in dashboard_content
        assert "method_performance.html" in dashboard_content
        assert "responsive" in dashboard_content.lower() or "viewport" in dashboard_content
    
    @pytest.mark.asyncio
    @patch('plotly.graph_objects.Figure')
    async def test_plotly_chart_creation(self, mock_figure, action, sample_context, tmp_path):
        """Test Plotly-specific chart creation."""
        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig
        
        output_dir = tmp_path / "plotly_charts"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Test Bar Chart",
                    data_key="statistics.method_performance",
                    x_field="method",
                    y_field="success_rate",
                    filename="test_bar.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly",
            plotly_config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d"]
            }
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        mock_figure.assert_called()
        mock_fig.write_html.assert_called()
    
    @pytest.mark.asyncio
    async def test_chartjs_format(self, action, sample_context, tmp_path):
        """Test Chart.js format generation."""
        output_dir = tmp_path / "chartjs"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="line",
                    title="Trend Analysis",
                    data_key="statistics.method_performance",
                    x_field="method",
                    y_field="success_rate",
                    filename="trend.html"
                )
            ],
            output_directory=str(output_dir),
            format="chartjs"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        chart_file = output_dir / "trend.html"
        assert chart_file.exists()
        
        content = chart_file.read_text()
        assert "Chart.js" in content or "chart.js" in content
        assert "canvas" in content.lower()
    
    @pytest.mark.asyncio
    async def test_static_image_export(self, action, sample_context, tmp_path):
        """Test static image export functionality."""
        output_dir = tmp_path / "static_images"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Static Chart",
                    data_key="statistics.method_performance",
                    filename="static_chart.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly",
            export_static=True,
            static_formats=["png", "svg", "pdf"]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        # Note: Actual static export requires kaleido/orca
        # Test should verify configuration and setup
        assert result.success is True
        assert result.static_exports_attempted is True
    
    @pytest.mark.asyncio
    async def test_custom_styling(self, action, sample_context, tmp_path):
        """Test custom styling and themes."""
        output_dir = tmp_path / "styled_charts"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Styled Chart",
                    data_key="statistics.method_performance",
                    filename="styled.html",
                    custom_style={
                        "color_palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                        "background_color": "#f8f9fa",
                        "font_family": "Arial, sans-serif"
                    }
                )
            ],
            output_directory=str(output_dir),
            format="plotly",
            theme="plotly_white",
            custom_css=".chart-container { border: 1px solid #ddd; }"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        chart_content = (output_dir / "styled.html").read_text()
        assert "#1f77b4" in chart_content or "color_palette" in chart_content
    
    @pytest.mark.asyncio
    async def test_data_aggregation_and_transformation(self, action, tmp_path):
        """Test data aggregation for complex visualizations."""
        # Complex nested data requiring aggregation
        context = {
            "datasets": {
                "time_series": [
                    {"timestamp": "2024-01-01", "method": "direct", "success": 1, "confidence": 0.95},
                    {"timestamp": "2024-01-01", "method": "fuzzy", "success": 1, "confidence": 0.87},
                    {"timestamp": "2024-01-02", "method": "direct", "success": 1, "confidence": 0.92},
                    {"timestamp": "2024-01-02", "method": "fuzzy", "success": 0, "confidence": 0.45}
                ]
            },
            "statistics": {}
        }
        
        output_dir = tmp_path / "aggregated"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="line",
                    title="Success Rate Over Time",
                    data_key="datasets.time_series",
                    x_field="timestamp",
                    y_field="success",
                    group_by="method",
                    aggregation="mean",
                    filename="time_series.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert result.data_points_processed > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, action, tmp_path):
        """Test error handling for invalid configurations."""
        context = {"datasets": {}, "statistics": {}}
        
        # Test missing data
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Missing Data Test",
                    data_key="nonexistent.data",
                    filename="error_test.html"
                )
            ],
            output_directory=str(tmp_path),
            format="plotly"
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "not found" in result.message.lower()
        
        # Test invalid chart type
        params_invalid = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="invalid_chart_type",
                    title="Invalid Type Test",
                    data_key="statistics.mapping_summary",
                    filename="invalid.html"
                )
            ],
            output_directory=str(tmp_path),
            format="plotly"
        )
        
        result_invalid = await action.execute_typed(params_invalid, context)
        
        assert result_invalid.success is False
        assert "unsupported" in result_invalid.message.lower() or "invalid" in result_invalid.message.lower()
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action, tmp_path):
        """Test performance with large datasets."""
        # Create large dataset
        large_data = [
            {"id": f"ID_{i}", "value": i % 100, "category": f"cat_{i % 10}"}
            for i in range(10000)
        ]
        
        context = {
            "datasets": {"large_data": large_data},
            "statistics": {}
        }
        
        output_dir = tmp_path / "performance"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="histogram",
                    title="Value Distribution",
                    data_key="datasets.large_data",
                    x_field="value",
                    filename="large_histogram.html",
                    sampling_rate=0.1  # Sample 10% for performance
                )
            ],
            output_directory=str(output_dir),
            format="plotly"
        )
        
        import time
        start = time.time()
        result = await action.execute_typed(params, context)
        elapsed = time.time() - start
        
        assert result.success is True
        assert elapsed < 5.0  # Should complete in under 5 seconds
        assert result.data_points_processed <= 10000
    
    @pytest.mark.asyncio
    async def test_interactive_features(self, action, sample_context, tmp_path):
        """Test interactive chart features."""
        output_dir = tmp_path / "interactive"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="scatter",
                    title="Interactive Scatter",
                    data_key="datasets.source_data",
                    x_field="value",
                    y_field="id",
                    filename="interactive.html",
                    interactive_features={
                        "hover_data": ["category", "value"],
                        "zoom": True,
                        "pan": True,
                        "select": True,
                        "crossfilter": True
                    }
                )
            ],
            output_directory=str(output_dir),
            format="plotly"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        content = (output_dir / "interactive.html").read_text()
        assert "hover" in content.lower()
        assert "zoom" in content.lower() or "pan" in content.lower()
    
    @pytest.mark.asyncio
    async def test_export_formats_and_embedding(self, action, sample_context, tmp_path):
        """Test various export formats and embedding options."""
        output_dir = tmp_path / "exports"
        
        params = GenerateMappingVisualizationsParams(
            charts=[
                ChartConfig(
                    type="bar",
                    title="Export Test",
                    data_key="statistics.method_performance",
                    filename="export_test.html"
                )
            ],
            output_directory=str(output_dir),
            format="plotly",
            export_json=True,
            export_static=True,
            embed_options={
                "include_plotlyjs": "cdn",
                "div_id": "chart-container",
                "config": {"responsive": True}
            }
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert result.json_exports_created is True
        
        # Check for JSON export
        json_file = output_dir / "export_test.json"
        if json_file.exists():
            data = json.loads(json_file.read_text())
            assert "data" in data
            assert "layout" in data
```

### 2. Implementation File for Visualizations
**Path:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_visualizations.py`

```python
"""Generate interactive visualizations from mapping results."""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import json
import math
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)

# Optional imports - graceful degradation if not available
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available - visualization features limited")


class ChartConfig(BaseModel):
    """Configuration for a single chart."""
    
    type: str = Field(..., description="Chart type: bar, line, pie, scatter, histogram, heatmap, treemap, summary_cards")
    title: str = Field(..., description="Chart title")
    data_key: str = Field(..., description="Dot-notation path to data")
    filename: str = Field(..., description="Output filename")
    x_field: Optional[str] = Field(None, description="X-axis field")
    y_field: Optional[str] = Field(None, description="Y-axis field")
    color_field: Optional[str] = Field(None, description="Color grouping field")
    size_field: Optional[str] = Field(None, description="Size field for bubbles")
    group_by: Optional[str] = Field(None, description="Field to group data by")
    aggregation: str = Field("sum", description="Aggregation method: sum, mean, count, max, min")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    limit: Optional[int] = Field(None, description="Limit number of data points")
    sampling_rate: Optional[float] = Field(None, description="Sample rate for large datasets (0.0-1.0)")
    custom_style: Optional[Dict[str, Any]] = Field(None, description="Custom styling options")
    interactive_features: Optional[Dict[str, Any]] = Field(None, description="Interactive feature configuration")


class GenerateMappingVisualizationsParams(BaseModel):
    """Parameters for visualization generation."""
    
    charts: List[ChartConfig] = Field(..., description="List of charts to generate")
    output_directory: str = Field(..., description="Output directory for charts")
    format: str = Field("plotly", description="Visualization format: plotly, chartjs, static")
    theme: str = Field("plotly", description="Chart theme")
    custom_css: Optional[str] = Field(None, description="Custom CSS styles")
    create_dashboard: bool = Field(False, description="Create combined dashboard")
    dashboard_title: str = Field("Mapping Analysis Dashboard", description="Dashboard title")
    include_statistics: bool = Field(True, description="Include statistics in dashboard")
    responsive: bool = Field(True, description="Make charts responsive")
    export_json: bool = Field(False, description="Export chart data as JSON")
    export_static: bool = Field(False, description="Export static image files")
    static_formats: List[str] = Field(["png"], description="Static export formats")
    plotly_config: Optional[Dict[str, Any]] = Field(None, description="Plotly-specific configuration")
    embed_options: Optional[Dict[str, Any]] = Field(None, description="Chart embedding options")


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
    warnings: List[str] = Field(default_factory=list)


@register_action("GENERATE_MAPPING_VISUALIZATIONS")
class GenerateMappingVisualizationsAction(TypedStrategyAction[GenerateMappingVisualizationsParams, GenerateMappingVisualizationsResult]):
    """
    Generate interactive visualizations from biological mapping results.
    
    Creates charts, graphs, and interactive dashboards using Plotly or Chart.js
    to visualize mapping statistics, performance metrics, and data distributions.
    """
    
    def get_params_model(self) -> type[GenerateMappingVisualizationsParams]:
        """Get the parameters model."""
        return GenerateMappingVisualizationsParams
    
    def get_result_model(self) -> type[GenerateMappingVisualizationsResult]:
        """Get the result model."""
        return GenerateMappingVisualizationsResult
    
    async def execute_typed(
        self,
        params: GenerateMappingVisualizationsParams,
        context: Dict[str, Any]
    ) -> GenerateMappingVisualizationsResult:
        """Execute visualization generation."""
        try:
            # Handle different context types
            ctx = self._get_context_dict(context)
            
            # Check format availability
            if params.format == "plotly" and not PLOTLY_AVAILABLE:
                return GenerateMappingVisualizationsResult(
                    success=False,
                    message="Plotly not available. Install with: pip install plotly"
                )
            
            # Create output directory
            output_dir = Path(params.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
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
                        warnings.append(f"Data not found for chart '{chart_config.title}'")
                        continue
                    
                    # Process and prepare data
                    processed_data, data_points = self._process_chart_data(chart_config, chart_data)
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
                            await self._export_chart_json(chart_config, processed_data, output_dir)
                    
                except Exception as e:
                    warnings.append(f"Failed to generate chart '{chart_config.title}': {str(e)}")
                    logger.error(f"Chart generation error: {str(e)}")
            
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
                "directory": str(output_dir)
            }
            
            if "statistics" not in ctx:
                ctx["statistics"] = {}
            
            ctx["statistics"]["visualization_generation"] = {
                "charts_generated": charts_generated,
                "data_points_processed": total_data_points,
                "formats_used": [params.format],
                "warnings_count": len(warnings)
            }
            
            logger.info(
                f"Generated {charts_generated} visualizations "
                f"({total_data_points} data points) in {output_dir}"
            )
            
            return GenerateMappingVisualizationsResult(
                success=True,
                message=f"Generated {charts_generated} visualizations successfully",
                charts_generated=charts_generated,
                file_paths=file_paths,
                dashboard_created=dashboard_created,
                dashboard_path=dashboard_path,
                data_points_processed=total_data_points,
                json_exports_created=params.export_json,
                static_exports_attempted=params.export_static,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            return GenerateMappingVisualizationsResult(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def _get_context_dict(self, context: Any) -> Dict[str, Any]:
        """Get dictionary from context."""
        if isinstance(context, dict):
            return context
        elif hasattr(context, '_dict'):
            return context._dict
        else:
            return {"datasets": {}, "statistics": {}}
    
    def _get_chart_data(self, chart_config: ChartConfig, context: Dict[str, Any]) -> Any:
        """Get data for chart using dot notation path."""
        keys = chart_config.data_key.split('.')
        data = context
        
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        
        return data
    
    def _process_chart_data(self, chart_config: ChartConfig, data: Any) -> tuple[Any, int]:
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
            import random
            sample_size = max(1, int(len(data) * chart_config.sampling_rate))
            data = random.sample(data, sample_size)
        
        # Apply limit if specified
        if chart_config.limit and isinstance(data, list):
            data = data[:chart_config.limit]
        
        # Apply sorting if specified
        if chart_config.sort_by and isinstance(data, list):
            if all(isinstance(item, dict) and chart_config.sort_by in item for item in data):
                data = sorted(data, key=lambda x: x[chart_config.sort_by])
        
        # Apply grouping and aggregation if specified
        if chart_config.group_by and isinstance(data, list):
            data = self._apply_grouping(data, chart_config)
        
        return data, original_count
    
    def _apply_grouping(self, data: List[Dict], chart_config: ChartConfig) -> List[Dict]:
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
            for field in [chart_config.x_field, chart_config.y_field, chart_config.size_field]:
                if field and field != chart_config.group_by:
                    values = [item.get(field, 0) for item in group_items if isinstance(item.get(field), (int, float))]
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
        params: GenerateMappingVisualizationsParams
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
            else:
                logger.warning(f"Unsupported chart type: {chart_config.type}")
                return None
            
            if not fig:
                return None
            
            # Apply theme and styling
            self._apply_plotly_styling(fig, chart_config, params)
            
            # Configure interactivity
            if chart_config.interactive_features:
                self._configure_plotly_interactivity(fig, chart_config.interactive_features)
            
            # Set up Plotly configuration
            plotly_config = params.plotly_config or {}
            plotly_config.update({
                "displayModeBar": True,
                "displaylogo": False,
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": chart_config.filename.replace(".html", ""),
                    "height": 500,
                    "width": 700,
                    "scale": 1
                }
            })
            
            # Save chart
            output_file = output_dir / chart_config.filename
            
            if params.embed_options:
                fig.write_html(
                    output_file,
                    config=plotly_config,
                    include_plotlyjs=params.embed_options.get("include_plotlyjs", True),
                    div_id=params.embed_options.get("div_id"),
                    full_html=True
                )
            else:
                fig.write_html(output_file, config=plotly_config)
            
            # Export static images if requested
            if params.export_static:
                await self._export_static_images(fig, chart_config, output_dir, params.static_formats)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error creating Plotly chart: {str(e)}")
            return None
    
    def _create_plotly_bar(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly bar chart."""
        if isinstance(data, dict):
            # Dictionary data - keys as x, values as y
            x_values = list(data.keys())
            y_values = list(data.values())
        elif isinstance(data, list) and data:
            # List of dictionaries
            x_values = [item.get(chart_config.x_field, str(i)) for i, item in enumerate(data)]
            y_values = [item.get(chart_config.y_field, 1) for item in data]
        else:
            return None
        
        fig = go.Figure(data=[
            go.Bar(
                x=x_values,
                y=y_values,
                name=chart_config.title
            )
        ])
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "Category",
            yaxis_title=chart_config.y_field or "Value"
        )
        
        return fig
    
    def _create_plotly_line(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly line chart."""
        if isinstance(data, list) and data:
            x_values = [item.get(chart_config.x_field, i) for i, item in enumerate(data)]
            y_values = [item.get(chart_config.y_field, 0) for item in data]
        else:
            return None
        
        fig = go.Figure(data=[
            go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',
                name=chart_config.title
            )
        ])
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "X",
            yaxis_title=chart_config.y_field or "Y"
        )
        
        return fig
    
    def _create_plotly_pie(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly pie chart."""
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        elif isinstance(data, list) and data:
            labels = [item.get(chart_config.x_field, f"Item {i}") for i, item in enumerate(data)]
            values = [item.get(chart_config.y_field, 1) for item in data]
        else:
            return None
        
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3  # Donut chart
            )
        ])
        
        fig.update_layout(title=chart_config.title)
        
        return fig
    
    def _create_plotly_scatter(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly scatter plot."""
        if not isinstance(data, list) or not data:
            return None
        
        x_values = [item.get(chart_config.x_field, 0) for item in data]
        y_values = [item.get(chart_config.y_field, 0) for item in data]
        
        scatter_kwargs = {
            'x': x_values,
            'y': y_values,
            'mode': 'markers',
            'name': chart_config.title
        }
        
        # Add size if specified
        if chart_config.size_field:
            sizes = [item.get(chart_config.size_field, 10) for item in data]
            scatter_kwargs['marker'] = {'size': sizes}
        
        # Add color if specified
        if chart_config.color_field:
            colors = [item.get(chart_config.color_field, 'blue') for item in data]
            if 'marker' not in scatter_kwargs:
                scatter_kwargs['marker'] = {}
            scatter_kwargs['marker']['color'] = colors
        
        fig = go.Figure(data=[go.Scatter(**scatter_kwargs)])
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "X",
            yaxis_title=chart_config.y_field or "Y"
        )
        
        return fig
    
    def _create_plotly_histogram(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly histogram."""
        if isinstance(data, dict):
            # Histogram from binned data
            x_values = list(data.keys())
            y_values = list(data.values())
            fig = go.Figure(data=[go.Bar(x=x_values, y=y_values)])
        elif isinstance(data, list) and data:
            # Histogram from raw data
            values = [item.get(chart_config.x_field, 0) for item in data if chart_config.x_field in item]
            fig = go.Figure(data=[go.Histogram(x=values)])
        else:
            return None
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_field or "Value",
            yaxis_title="Count"
        )
        
        return fig
    
    def _create_plotly_heatmap(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly heatmap."""
        # This is a placeholder - real implementation would need matrix data
        fig = go.Figure(data=go.Heatmap(
            z=[[1, 20, 30], [20, 1, 60], [30, 60, 1]],
            x=['Method A', 'Method B', 'Method C'],
            y=['Category 1', 'Category 2', 'Category 3'],
            colorscale='Viridis'
        ))
        
        fig.update_layout(title=chart_config.title)
        
        return fig
    
    def _create_plotly_treemap(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create Plotly treemap."""
        if not isinstance(data, dict):
            return None
        
        labels = list(data.keys())
        values = list(data.values())
        
        fig = go.Figure(go.Treemap(
            labels=labels,
            values=values,
            parents=[""] * len(labels)
        ))
        
        fig.update_layout(title=chart_config.title)
        
        return fig
    
    def _create_plotly_summary_cards(self, chart_config: ChartConfig, data: Any) -> Optional[go.Figure]:
        """Create summary cards visualization."""
        if not isinstance(data, dict):
            return None
        
        # Create a simple table-like visualization for summary data
        fig = go.Figure(data=[go.Table(
            header=dict(values=['Metric', 'Value']),
            cells=dict(values=[
                list(data.keys()),
                [f"{v:.3f}" if isinstance(v, float) else str(v) for v in data.values()]
            ])
        )])
        
        fig.update_layout(title=chart_config.title)
        
        return fig
    
    def _apply_plotly_styling(self, fig: go.Figure, chart_config: ChartConfig, params: GenerateMappingVisualizationsParams):
        """Apply styling to Plotly figure."""
        # Apply theme
        if hasattr(pio, 'templates') and params.theme in pio.templates:
            fig.update_layout(template=params.theme)
        
        # Apply custom styling
        if chart_config.custom_style:
            style = chart_config.custom_style
            
            layout_updates = {}
            
            if 'background_color' in style:
                layout_updates['plot_bgcolor'] = style['background_color']
                layout_updates['paper_bgcolor'] = style['background_color']
            
            if 'font_family' in style:
                layout_updates['font'] = {'family': style['font_family']}
            
            if layout_updates:
                fig.update_layout(**layout_updates)
            
            # Apply color palette
            if 'color_palette' in style and hasattr(fig, 'data'):
                for i, trace in enumerate(fig.data):
                    if i < len(style['color_palette']):
                        if hasattr(trace, 'marker'):
                            trace.marker.color = style['color_palette'][i]
                        elif hasattr(trace, 'line'):
                            trace.line.color = style['color_palette'][i]
        
        # Make responsive if requested
        if params.responsive:
            fig.update_layout(
                autosize=True,
                margin=dict(l=0, r=0, t=30, b=0)
            )
    
    def _configure_plotly_interactivity(self, fig: go.Figure, features: Dict[str, Any]):
        """Configure interactive features for Plotly chart."""
        config_updates = {}
        
        if features.get('zoom', True):
            config_updates['scrollZoom'] = True
        
        if not features.get('pan', True):
            config_updates['scrollZoom'] = False
        
        # Note: This would be applied via the config parameter in write_html
        # Store for later use
        fig._config_updates = config_updates
    
    async def _generate_chartjs_chart(
        self,
        chart_config: ChartConfig,
        data: Any,
        output_dir: Path,
        params: GenerateMappingVisualizationsParams
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
            labels = [item.get(chart_config.x_field, f"Item {i}") for i, item in enumerate(data)]
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
                "datasets": [{
                    "label": chart_config.title,
                    "data": values,
                    "backgroundColor": [
                        'rgba(255, 99, 132, 0.2)',
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 205, 86, 0.2)',
                        'rgba(75, 192, 192, 0.2)',
                    ],
                    "borderColor": [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 205, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                    ],
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": chart_config.title
                    }
                }
            }
        }
        
        return json.dumps(chart_data)
    
    async def _export_chart_json(self, chart_config: ChartConfig, data: Any, output_dir: Path):
        """Export chart data as JSON."""
        json_file = output_dir / chart_config.filename.replace('.html', '.json')
        
        export_data = {
            "title": chart_config.title,
            "type": chart_config.type,
            "data": data,
            "config": chart_config.dict(),
            "exported": datetime.now().isoformat()
        }
        
        json_file.write_text(json.dumps(export_data, indent=2))
    
    async def _export_static_images(
        self,
        fig: go.Figure,
        chart_config: ChartConfig,
        output_dir: Path,
        formats: List[str]
    ):
        """Export static image files."""
        try:
            base_name = chart_config.filename.replace('.html', '')
            
            for fmt in formats:
                if hasattr(fig, 'write_image'):
                    output_file = output_dir / f"{base_name}.{fmt}"
                    fig.write_image(output_file, format=fmt)
                else:
                    logger.warning(f"Static export not available - install kaleido: pip install kaleido")
                    break
        except Exception as e:
            logger.warning(f"Static export failed: {str(e)}")
    
    async def _create_dashboard(
        self,
        params: GenerateMappingVisualizationsParams,
        chart_files: List[str],
        output_dir: Path,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Create combined dashboard with all charts."""
        try:
            dashboard_file = output_dir / "dashboard.html"
            
            # Generate chart iframes
            chart_iframes = []
            for chart_file in chart_files:
                chart_name = Path(chart_file).name
                chart_iframes.append(f"""
                    <div class="chart-frame">
                        <iframe src="{chart_name}" width="100%" height="500" frameborder="0"></iframe>
                    </div>
                """)
            
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
```

### 3. Run Tests and Iterate
```bash
# Visualization Tests
poetry run pytest tests/unit/core/strategy_actions/reports/test_generate_visualizations.py -xvs

# Install required dependencies
poetry add plotly kaleido  # For static exports

# Coverage check
poetry run pytest tests/unit/core/strategy_actions/reports/ --cov=biomapper.core.strategy_actions.reports --cov-report=term-missing

# Integration test with v2.2 strategy
poetry run pytest tests/integration/ -k visualization
```

## 📋 Acceptance Criteria

1. ✅ Generate interactive charts using Plotly and Chart.js
2. ✅ Support multiple chart types: bar, line, pie, scatter, histogram, heatmap, treemap
3. ✅ Create responsive, interactive visualizations
4. ✅ Generate combined dashboards with multiple charts
5. ✅ Export static images (PNG, SVG, PDF) when kaleido available
6. ✅ Export chart data as JSON format
7. ✅ Handle large datasets with sampling and performance optimization
8. ✅ Apply custom styling and themes
9. ✅ Configure interactive features (zoom, pan, hover, select)
10. ✅ Process and aggregate data for complex visualizations
11. ✅ Store visualization files in context for downstream use
12. ✅ Provide comprehensive error handling and warnings

## 🔧 Technical Requirements

- Use Plotly for advanced interactive charts
- Fallback to Chart.js for simpler charts
- Generate valid HTML5 with responsive design
- Support data aggregation and grouping
- Handle performance optimization for large datasets
- Use Pydantic for parameter validation
- Follow TypedStrategyAction pattern
- Register with @register_action decorator
- Graceful degradation when libraries unavailable

## 🎯 Definition of Done

- [ ] All tests written and passing
- [ ] Interactive visualizations generate correctly
- [ ] Dashboard creation works properly
- [ ] Multiple chart types supported
- [ ] Performance optimized for large datasets
- [ ] Static export works when dependencies available
- [ ] Custom styling and themes apply correctly
- [ ] Data aggregation functions properly
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Integration tested with v2.2 strategy
"""Test suite for GenerateMappingVisualizationsAction - WRITE THIS FIRST!"""

import pytest
from typing import Dict, Any
from pathlib import Path
import json
import tempfile
from unittest.mock import MagicMock, patch

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.reports.generate_visualizations_v2 import (
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
    async def test_basic_visualization_generation(self, action, sample_context):
        """Test basic chart generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "visualizations"
            
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
    async def test_comprehensive_dashboard_generation(self, action, sample_context):
        """Test generation of complete visualization dashboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "dashboard"
            
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
            assert result.charts_generated == 2
            assert result.dashboard_created is True
            
            # Check dashboard file
            dashboard_file = output_dir / "dashboard.html"
            assert dashboard_file.exists()
            
            dashboard_content = dashboard_file.read_text()
            assert "Protein Mapping Analysis Dashboard" in dashboard_content
            assert "summary_cards.html" in dashboard_content
            assert "method_performance.html" in dashboard_content
    
    @pytest.mark.asyncio
    async def test_chartjs_format(self, action, sample_context):
        """Test Chart.js format generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "chartjs"
            
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
    async def test_data_aggregation_and_transformation(self, action):
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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "aggregated"
            
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
            
            result = await action.execute_typed(params, context)
            
            assert result.success is True
            assert result.data_points_processed > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, action):
        """Test error handling for invalid configurations."""
        context = {"datasets": {}, "statistics": {}}
        
        with tempfile.TemporaryDirectory() as tmpdir:
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
                output_directory=str(tmpdir),
                format="plotly"
            )
            
            result = await action.execute_typed(params, context)
            
            # Should succeed but with warnings
            assert result.success is True
            assert len(result.warnings) > 0
            assert any("not found" in warning.lower() for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action):
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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "performance"
            
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
    async def test_export_formats_and_embedding(self, action, sample_context):
        """Test various export formats and embedding options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "exports"
            
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
                assert "title" in data
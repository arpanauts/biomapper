"""Tests for progressive visualization enhancements in generate_visualizations_v2.py"""

import pytest
from pathlib import Path
from typing import Dict, Any
import json
import pandas as pd
from unittest.mock import Mock, patch

from biomapper.core.strategy_actions.reports.generate_visualizations_v2 import (
    GenerateMappingVisualizationsAction,
    GenerateMappingVisualizationsParams,
    ProgressiveVisualizationParams,
    ChartConfig,
    GenerateMappingVisualizationsResult
)


class TestProgressiveVisualizationEnhancements:
    """Test suite for progressive visualization enhancements."""

    @pytest.fixture
    def sample_progressive_stats(self) -> Dict[str, Any]:
        """Sample progressive statistics data."""
        return {
            "total_processed": 1000,
            "stages": {
                1: {
                    "name": "Direct Match",
                    "method": "Direct UniProt",
                    "matched": 650,
                    "new_matches": 650,
                    "computation_time": "0.5s",
                    "confidence_avg": 1.00
                },
                2: {
                    "name": "Composite Parsing",
                    "method": "Composite parsing",
                    "matched": 0,
                    "new_matches": 0,
                    "computation_time": "0.2s",
                    "confidence_avg": 0.95
                },
                3: {
                    "name": "Historical Resolution",
                    "method": "Historical API",
                    "matched": 150,
                    "new_matches": 150,
                    "computation_time": "12.3s",
                    "confidence_avg": 0.90
                },
                4: {
                    "name": "Final Stage",
                    "method": "Ensemble",
                    "matched": 40,
                    "new_matches": 40,
                    "computation_time": "5.1s",
                    "confidence_avg": 0.85
                }
            }
        }

    @pytest.fixture
    def progressive_params(self) -> ProgressiveVisualizationParams:
        """Progressive visualization parameters."""
        return ProgressiveVisualizationParams(
            progressive_mode=True,
            export_statistics_tsv=True,
            waterfall_chart=True,
            stage_comparison=True,
            confidence_distribution=True,
            method_breakdown=True
        )

    @pytest.fixture
    def visualization_action(self) -> GenerateMappingVisualizationsAction:
        """Create visualization action instance."""
        return GenerateMappingVisualizationsAction()

    def test_process_progressive_stats(self, visualization_action, sample_progressive_stats):
        """Test processing of progressive statistics."""
        processed = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        assert len(processed) == 4
        
        # Check first stage
        stage1 = processed[0]
        assert stage1["stage_number"] == 1
        assert stage1["stage_name"] == "Direct Match"
        assert stage1["method"] == "Direct UniProt"
        assert stage1["new_matches"] == 650
        assert stage1["cumulative_matched"] == 650
        assert stage1["cumulative_rate"] == 65.0
        assert stage1["improvement"] == 65.0
        
        # Check cumulative progression
        stage2 = processed[1]
        assert stage2["cumulative_matched"] == 650  # No new matches
        assert stage2["cumulative_rate"] == 65.0
        assert stage2["improvement"] == 0.0
        
        stage3 = processed[2]
        assert stage3["cumulative_matched"] == 800  # 650 + 150
        assert stage3["cumulative_rate"] == 80.0
        assert stage3["improvement"] == 15.0
        
        stage4 = processed[3]
        assert stage4["cumulative_matched"] == 840  # 800 + 40
        assert stage4["cumulative_rate"] == 84.0
        assert stage4["improvement"] == 4.0

    def test_process_progressive_stats_empty(self, visualization_action):
        """Test processing with empty progressive stats."""
        result = visualization_action._process_progressive_stats({})
        assert result == []
        
        result = visualization_action._process_progressive_stats({"stages": {}})
        assert result == []

    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.PLOTLY_AVAILABLE', True)
    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.go')
    def test_create_waterfall_chart(self, mock_go, visualization_action, sample_progressive_stats):
        """Test waterfall chart creation."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        chart_config = ChartConfig(
            type="waterfall",
            title="Test Waterfall",
            data_key="test",
            file_path="test.html"
        )
        
        # Mock Plotly Figure
        mock_figure = Mock()
        mock_go.Figure.return_value = mock_figure
        mock_go.Waterfall = Mock()
        
        result = visualization_action._create_plotly_waterfall(chart_config, processed_data)
        
        assert result == mock_figure
        mock_go.Figure.assert_called_once()
        mock_figure.update_layout.assert_called_once()

    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.PLOTLY_AVAILABLE', True)
    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.go')
    def test_create_stage_bars_chart(self, mock_go, visualization_action, sample_progressive_stats):
        """Test stage comparison bar chart creation."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        chart_config = ChartConfig(
            type="stage_bars",
            title="Test Stage Bars",
            data_key="test",
            file_path="test.html"
        )
        
        mock_figure = Mock()
        mock_go.Figure.return_value = mock_figure
        mock_go.Bar = Mock()
        
        result = visualization_action._create_plotly_stage_bars(chart_config, processed_data)
        
        assert result == mock_figure
        mock_go.Figure.assert_called_once()

    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.PLOTLY_AVAILABLE', True)
    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.go')
    def test_create_confidence_distribution_chart(self, mock_go, visualization_action, sample_progressive_stats):
        """Test confidence distribution chart creation."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        chart_config = ChartConfig(
            type="confidence_distribution",
            title="Test Confidence",
            data_key="test",
            file_path="test.html"
        )
        
        mock_figure = Mock()
        mock_go.Figure.return_value = mock_figure
        mock_go.Scatter = Mock()
        
        result = visualization_action._create_plotly_confidence_distribution(chart_config, processed_data)
        
        assert result == mock_figure
        mock_go.Figure.assert_called_once()

    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.PLOTLY_AVAILABLE', True)
    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.go')
    def test_create_method_breakdown_chart(self, mock_go, visualization_action, sample_progressive_stats):
        """Test method breakdown pie chart creation."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        chart_config = ChartConfig(
            type="method_breakdown",
            title="Test Method Breakdown",
            data_key="test",
            file_path="test.html"
        )
        
        mock_figure = Mock()
        mock_go.Figure.return_value = mock_figure
        mock_go.Pie = Mock()
        
        result = visualization_action._create_plotly_method_breakdown(chart_config, processed_data)
        
        assert result == mock_figure
        mock_go.Figure.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_progressive_tsv(self, visualization_action, sample_progressive_stats, tmp_path):
        """Test TSV export functionality."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        await visualization_action._export_progressive_tsv(processed_data, tmp_path)
        
        tsv_file = tmp_path / "progressive_statistics.tsv"
        assert tsv_file.exists()
        
        # Read and verify TSV content
        df = pd.read_csv(tsv_file, sep='\t')
        assert len(df) == 4
        assert "stage_number" in df.columns
        assert "stage_name" in df.columns
        assert "method" in df.columns
        assert "cumulative_rate" in df.columns
        
        # Check data formatting
        assert df.iloc[0]["cumulative_rate"] == "65.0%"
        assert df.iloc[2]["cumulative_rate"] == "80.0%"

    @pytest.mark.asyncio
    async def test_export_progressive_json_summary(self, visualization_action, sample_progressive_stats, tmp_path):
        """Test JSON summary export functionality."""
        processed_data = visualization_action._process_progressive_stats(sample_progressive_stats)
        
        await visualization_action._export_progressive_json_summary(processed_data, tmp_path)
        
        json_file = tmp_path / "progressive_summary.json"
        assert json_file.exists()
        
        # Read and verify JSON content
        with open(json_file) as f:
            summary = json.load(f)
        
        assert "summary" in summary
        assert "stage_details" in summary
        assert "exported" in summary
        
        # Check summary metrics
        assert summary["summary"]["total_stages"] == 4
        assert summary["summary"]["final_mapping_rate"] == "84.0%"
        assert summary["summary"]["total_processed"] == 1000
        
        # Check stage details
        assert len(summary["stage_details"]) == 4

    @pytest.mark.asyncio
    @patch('biomapper.core.strategy_actions.reports.generate_visualizations_v2.PLOTLY_AVAILABLE', True)
    async def test_execute_with_progressive_mode(self, visualization_action, sample_progressive_stats, progressive_params, tmp_path):
        """Test full execution with progressive mode enabled."""
        params = GenerateMappingVisualizationsParams(
            charts=[],
            output_directory=str(tmp_path),
            progressive_params=progressive_params
        )
        
        context = {
            "progressive_stats": sample_progressive_stats,
            "datasets": {},
            "statistics": {}
        }
        
        with patch.object(visualization_action, '_generate_plotly_chart') as mock_generate:
            mock_generate.return_value = tmp_path / "test.html"
            
            result = await visualization_action.execute_typed(params, context)
        
        assert result.success
        assert result.progressive_charts_created == 4  # waterfall + stage_bars + confidence + method
        assert result.progressive_tsv_exported
        assert result.progressive_json_exported
        
        # Check that TSV and JSON files were created
        assert (tmp_path / "progressive_statistics.tsv").exists()
        assert (tmp_path / "progressive_summary.json").exists()

    @pytest.mark.asyncio
    async def test_execute_without_progressive_mode(self, visualization_action, tmp_path):
        """Test execution without progressive mode."""
        params = GenerateMappingVisualizationsParams(
            charts=[],
            output_directory=str(tmp_path)
        )
        
        context = {"datasets": {}, "statistics": {}}
        
        result = await visualization_action.execute_typed(params, context)
        
        assert result.success
        assert result.progressive_charts_created == 0
        assert not result.progressive_tsv_exported
        assert not result.progressive_json_exported

    def test_progressive_params_validation(self):
        """Test progressive parameters validation."""
        # Test default values
        params = ProgressiveVisualizationParams()
        assert not params.progressive_mode
        assert not params.export_statistics_tsv
        assert not params.waterfall_chart
        assert params.stage_prefix == "Stage"
        assert params.show_percentages
        
        # Test custom values
        params = ProgressiveVisualizationParams(
            progressive_mode=True,
            export_statistics_tsv=True,
            waterfall_chart=True,
            stage_prefix="Phase",
            show_percentages=False
        )
        assert params.progressive_mode
        assert params.export_statistics_tsv
        assert params.waterfall_chart
        assert params.stage_prefix == "Phase"
        assert not params.show_percentages

    def test_chart_config_new_types(self):
        """Test that new chart types are accepted in ChartConfig."""
        # Test all new chart types
        for chart_type in ["waterfall", "stage_bars", "confidence_distribution", "method_breakdown"]:
            config = ChartConfig(
                type=chart_type,
                title=f"Test {chart_type}",
                data_key="test_data",
                file_path=f"test_{chart_type}.html"
            )
            assert config.type == chart_type

    @pytest.mark.asyncio
    async def test_error_handling_missing_progressive_stats(self, visualization_action, progressive_params, tmp_path):
        """Test error handling when progressive stats are missing."""
        params = GenerateMappingVisualizationsParams(
            charts=[],
            output_directory=str(tmp_path),
            progressive_params=progressive_params
        )
        
        # Context without progressive_stats
        context = {"datasets": {}, "statistics": {}}
        
        result = await visualization_action.execute_typed(params, context)
        
        # Should still succeed but without progressive features
        assert result.success
        assert result.progressive_charts_created == 0

    def test_chart_data_validation(self, visualization_action):
        """Test chart creation with invalid data."""
        chart_config = ChartConfig(
            type="waterfall",
            title="Test",
            data_key="test",
            file_path="test.html"
        )
        
        # Test with None data
        result = visualization_action._create_plotly_waterfall(chart_config, None)
        assert result is None
        
        # Test with empty list
        result = visualization_action._create_plotly_waterfall(chart_config, [])
        assert result is None
        
        # Test with non-list data
        result = visualization_action._create_plotly_waterfall(chart_config, "invalid")
        assert result is None
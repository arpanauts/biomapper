"""Unit tests for GENERATE_ENHANCEMENT_REPORT action."""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from biomapper.core.strategy_actions.generate_enhancement_report import (
    GenerateEnhancementReport,
    GenerateEnhancementReportParams
)
from biomapper.core.models.execution_context import StrategyExecutionContext


class TestGenerateEnhancementReport:
    """Test suite for GENERATE_ENHANCEMENT_REPORT action."""
    
    @pytest.fixture
    def action(self):
        """Create action instance."""
        return GenerateEnhancementReport()
    
    @pytest.fixture
    def sample_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Sample metrics data for testing."""
        return {
            "metrics.baseline": {
                "total_unmatched_input": 1000,
                "total_matched": 450,
                "match_rate": 0.45,
                "avg_confidence": 0.82,
                "execution_time": 5.2
            },
            "metrics.api": {
                "total_unmatched_input": 550,
                "total_matched": 150,
                "match_rate": 0.273,
                "cumulative_match_rate": 0.60,
                "api_calls_made": 275,
                "cache_hits": 125,
                "execution_time": 12.5
            },
            "metrics.vector": {
                "total_unmatched_input": 400,
                "total_matched": 100,
                "match_rate": 0.25,
                "cumulative_match_rate": 0.70,
                "vectors_searched": 400,
                "avg_similarity_score": 0.78,
                "execution_time": 8.3
            }
        }
    
    @pytest.fixture
    def params(self) -> GenerateEnhancementReportParams:
        """Create test parameters."""
        return GenerateEnhancementReportParams(
            metrics_keys=["metrics.baseline", "metrics.api", "metrics.vector"],
            stage_names=["Baseline", "API Enhanced", "Vector Enhanced"],
            output_path="/tmp/test_report.md",
            include_visualizations=True,
            include_detailed_stats=True
        )
    
    @pytest.fixture
    def mock_context(self, sample_metrics):
        """Create mock context with metrics."""
        context = MagicMock()
        # Set up the context to return our sample metrics
        def get_action_data_side_effect(key, default=None):
            return sample_metrics.get(key, default)
        
        context.get_action_data.side_effect = get_action_data_side_effect
        context.get.side_effect = lambda key, default=None: sample_metrics.get(key, default)
        return context
    
    async def test_params_validation(self):
        """Test that parameters are properly validated."""
        # Valid params should work
        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.test"],
            output_path="/tmp/output.md"
        )
        assert params.metrics_keys == ["metrics.test"]
        assert params.output_path == "/tmp/output.md"
        assert params.include_visualizations is True  # default
        
        # Missing required fields should fail
        with pytest.raises(ValueError):
            GenerateEnhancementReportParams()
    
    async def test_metrics_aggregation(self, action, params, mock_context, sample_metrics):
        """Test that metrics are correctly aggregated from context."""
        # Execute aggregation
        metrics = action._aggregate_metrics(params.metrics_keys, mock_context)
        
        # Assert
        assert len(metrics) == 3
        assert metrics[0]["match_rate"] == 0.45
        assert metrics[1]["cumulative_match_rate"] == 0.60
        assert metrics[2]["cumulative_match_rate"] == 0.70
    
    async def test_improvement_calculation(self, action):
        """Test calculation of improvement between stages."""
        # Test data
        baseline_rate = 0.45
        enhanced_rate = 0.60
        final_rate = 0.70
        
        # Calculate improvements
        abs_improvement_1 = action._calculate_absolute_improvement(baseline_rate, enhanced_rate)
        rel_improvement_1 = action._calculate_relative_improvement(baseline_rate, enhanced_rate)
        
        abs_improvement_2 = action._calculate_absolute_improvement(baseline_rate, final_rate)
        rel_improvement_2 = action._calculate_relative_improvement(baseline_rate, final_rate)
        
        # Assert absolute improvements (percentage points)
        assert abs_improvement_1 == pytest.approx(15.0, 0.1)
        assert abs_improvement_2 == pytest.approx(25.0, 0.1)
        
        # Assert relative improvements (percentage change)
        assert rel_improvement_1 == pytest.approx(33.3, 0.1)
        assert rel_improvement_2 == pytest.approx(55.6, 0.1)
    
    async def test_ascii_chart_generation(self, action):
        """Test ASCII visualization generation."""
        stages = ["Baseline", "API", "Vector"]
        values = [0.45, 0.60, 0.70]
        
        chart = action._generate_ascii_chart(stages, values)
        
        # Assert chart contains expected elements
        assert "Match Rate by Enhancement Stage" in chart
        assert "Baseline" in chart
        assert "API" in chart
        assert "Vector" in chart
        assert "45%" in chart
        assert "60%" in chart
        assert "70%" in chart
        assert "│" in chart  # Box drawing characters
        assert "┌" in chart
        assert "─" in chart
    
    async def test_markdown_generation(self, action, params, sample_metrics):
        """Test that markdown report is properly formatted."""
        # Generate markdown
        timestamp = datetime.utcnow()
        metrics = [
            sample_metrics["metrics.baseline"],
            sample_metrics["metrics.api"],
            sample_metrics["metrics.vector"]
        ]
        
        markdown = action._generate_markdown_report(
            metrics=metrics,
            stage_names=params.stage_names,
            timestamp=timestamp,
            include_visualizations=True,
            include_detailed_stats=True
        )
        
        # Assert structure
        assert "# Metabolomics Progressive Enhancement Report" in markdown
        assert "## Executive Summary" in markdown
        assert "## Progressive Enhancement Results" in markdown
        assert "| Stage | Match Rate |" in markdown  # Table header
        assert "### Visual Representation" in markdown
        assert "## Detailed Statistics" in markdown
        assert "## Methodology" in markdown
        assert "## Conclusions" in markdown
        
        # Assert data presence
        assert "45%" in markdown or "45.0%" in markdown
        assert "60%" in markdown or "60.0%" in markdown
        assert "70%" in markdown or "70.0%" in markdown
        assert "700/1,000" in markdown  # Total matched with comma
    
    async def test_missing_metrics_handling(self, action, params):
        """Test graceful handling of missing metric keys."""
        # Create context with only partial metrics
        partial_context = MagicMock()
        partial_metrics = {
            "metrics.baseline": {"match_rate": 0.45},
            # "metrics.api" is missing
            "metrics.vector": {"cumulative_match_rate": 0.70}
        }
        
        def get_side_effect(key, default=None):
            return partial_metrics.get(key, default)
        
        partial_context.get_action_data.side_effect = get_side_effect
        partial_context.get.side_effect = get_side_effect
        
        # Should handle gracefully
        metrics = action._aggregate_metrics(params.metrics_keys, partial_context)
        
        # Should have only found 2 metrics
        assert len(metrics) == 2
        assert metrics[0]["match_rate"] == 0.45
        assert metrics[1]["cumulative_match_rate"] == 0.70
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("os.path.dirname", return_value="/tmp")
    async def test_file_writing(self, mock_dirname, mock_makedirs, mock_file, action, params):
        """Test report file is written correctly."""
        # Prepare test data
        test_content = "# Test Report Content"
        
        # Write file
        action._write_report_to_file(params.output_path, test_content)
        
        # Assert file operations
        mock_makedirs.assert_called_once_with("/tmp", exist_ok=True)
        mock_file.assert_called_once_with(params.output_path, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(test_content)
    
    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("os.makedirs")
    async def test_file_write_error_handling(self, mock_makedirs, mock_file, action, params):
        """Test handling of file write errors."""
        test_content = "# Test Report"
        
        # Should raise with clear error message
        with pytest.raises(IOError) as exc_info:
            action._write_report_to_file(params.output_path, test_content)
        
        assert "Permission denied" in str(exc_info.value)
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    async def test_full_report_generation(self, mock_makedirs, mock_file, action, params, mock_context):
        """Test complete report generation workflow."""
        # Execute the action
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Assert result structure
        assert result.input_identifiers == []
        assert result.output_identifiers == []
        assert result.output_ontology_type == "metabolite"
        assert "report_path" in result.details
        assert "metrics_found" in result.details
        assert result.details["metrics_found"] == 3
        assert result.details["report_path"] == params.output_path
        
        # Assert file was written
        mock_file.assert_called_once()
        written_content = mock_file().write.call_args[0][0]
        
        # Verify report content
        assert "# Metabolomics Progressive Enhancement Report" in written_content
        assert "45%" in written_content or "45.0%" in written_content
        assert "70%" in written_content or "70.0%" in written_content
    
    async def test_empty_metrics_handling(self, action, params):
        """Test behavior with no metrics found."""
        # Create empty context
        empty_context = MagicMock()
        empty_context.get_action_data.return_value = None
        empty_context.get.return_value = None
        
        # Should still generate a report
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=empty_context
        )
        
        # Should indicate no metrics found
        assert result.details["metrics_found"] == 0
        assert "warning" in result.details
    
    async def test_context_compatibility(self, action, params, sample_metrics):
        """Test that action works with both dict and typed contexts."""
        # Test with dict context
        dict_context = sample_metrics.copy()
        
        # Mock file writing
        with patch("builtins.open", mock_open()):
            with patch("os.makedirs"):
                result = await action.execute_typed(
                    current_identifiers=[],
                    current_ontology_type="metabolite",
                    params=params,
                    source_endpoint=None,
                    target_endpoint=None,
                    context=dict_context
                )
        
        assert result.details["metrics_found"] == 3
    
    async def test_custom_baseline_calculation(self, action, params, mock_context):
        """Test improvement calculation with custom baseline."""
        # Set custom baseline to second stage
        params.comparison_baseline = "metrics.api"
        
        # Execute
        with patch("builtins.open", mock_open()):
            with patch("os.makedirs"):
                result = await action.execute_typed(
                    current_identifiers=[],
                    current_ontology_type="metabolite",
                    params=params,
                    source_endpoint=None,
                    target_endpoint=None,
                    context=mock_context
                )
        
        # Should calculate improvements relative to API stage
        assert result.details["metrics_found"] == 3
        assert result.details["baseline_used"] == "metrics.api"
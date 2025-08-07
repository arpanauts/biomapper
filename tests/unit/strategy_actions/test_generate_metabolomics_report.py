"""Unit tests for GenerateMetabolomicsReportAction."""

import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch

from biomapper.core.strategy_actions.generate_metabolomics_report import (
    GenerateMetabolomicsReportAction,
    GenerateMetabolomicsReportParams,
)
from biomapper.core.models import StrategyExecutionContext


class TestGenerateMetabolomicsReportAction:
    """Test suite for metabolomics report generation."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return GenerateMetabolomicsReportAction()

    @pytest.fixture
    def mock_context(self):
        """Create mock execution context with test data."""
        context = Mock(spec=StrategyExecutionContext)

        # Mock statistics data
        stats_data = {
            "total_unique_metabolites": 500,
            "three_way_overlap": {"count": 150, "percentage": 30.0},
            "pairwise_overlaps": {
                "Israeli10K_UKBB": {"overlap_count": 200, "jaccard_index": 0.4},
                "Israeli10K_Arivale": {"overlap_count": 180, "jaccard_index": 0.35},
                "UKBB_Arivale": {"overlap_count": 190, "jaccard_index": 0.38},
            },
            "dataset_counts": {
                "Israeli10K": {"total": 250, "unique": 230},
                "UKBB": {"total": 260, "unique": 240},
                "Arivale": {"total": 300, "unique": 280},
            },
            "overlap_summary": {
                "three_datasets": 150,
                "two_datasets": 100,
                "only_one_dataset": 250,
            },
            "visualization_files": {
                "venn_diagram": "/path/to/venn.png",
                "confidence_dist": "/path/to/conf.png",
            },
        }

        # Mock matches data
        matches_data = [
            {
                "metabolite_name": "Glucose",
                "Israeli10K_id": "GLU_001",
                "UKBB_id": "GLUCOSE_NMR",
                "Arivale_id": "glucose_blood",
                "confidence_score": 0.95,
                "match_method": "fuzzy_match",
            },
            {
                "metabolite_name": "Cholesterol",
                "Israeli10K_id": "CHOL_001",
                "UKBB_id": "CHOLESTEROL_NMR",
                "Arivale_id": "cholesterol_total",
                "confidence_score": 0.88,
                "match_method": "api_enriched",
            },
            {
                "metabolite_name": "Alanine",
                "Israeli10K_id": "ALA_001",
                "UKBB_id": "ALANINE_NMR",
                "Arivale_id": "alanine",
                "confidence_score": 0.72,
                "match_method": "semantic",
            },
        ]

        # Mock metrics data
        metrics_data = {
            "metrics.baseline": {
                "total_matches": 100,
                "success_rate": 95.0,
                "average_confidence": 0.92,
            },
            "metrics.api_enriched": {
                "total_matches": 50,
                "success_rate": 88.0,
                "average_confidence": 0.85,
            },
            "metrics.semantic": {
                "total_matches": 30,
                "success_rate": 82.0,
                "average_confidence": 0.78,
            },
        }

        # Setup context methods
        def get_action_data(category, default=None):
            if category == "results":
                return {"three_way_statistics": stats_data}
            elif category == "datasets":
                return {
                    "three_way_combined_matches": matches_data,
                    "nightingale_reference_map": {"ref": "data"},
                }
            elif category == "metrics":
                return metrics_data
            return default or {}

        context.get_action_data = Mock(side_effect=get_action_data)
        return context

    @pytest.fixture
    def params(self, tmp_path):
        """Create test parameters."""
        return GenerateMetabolomicsReportParams(
            statistics_key="three_way_statistics",
            matches_key="three_way_combined_matches",
            nightingale_reference="nightingale_reference_map",
            metrics_keys=[
                "metrics.baseline",
                "metrics.api_enriched",
                "metrics.semantic",
            ],
            output_dir=str(tmp_path),
            report_format="markdown",
            include_sections=[
                "executive_summary",
                "methodology_overview",
                "dataset_overview",
                "three_way_overlap_analysis",
                "confidence_distribution",
                "quality_metrics",
                "recommendations",
            ],
            export_formats=["markdown", "html", "json"],
            include_visualizations=True,
            max_examples=5,
        )

    @pytest.mark.asyncio
    async def test_data_collection(self, action, mock_context, params):
        """Test collecting data from context."""
        report_data = action._collect_report_data(mock_context, params)

        assert "metadata" in report_data
        assert "statistics" in report_data
        assert "matches" in report_data
        assert "metrics" in report_data
        assert "visualizations" in report_data

        # Check statistics
        assert report_data["statistics"]["total_unique_metabolites"] == 500
        assert report_data["statistics"]["three_way_overlap"]["count"] == 150

        # Check matches analysis
        assert report_data["matches"]["total"] == 3
        assert report_data["matches"]["by_confidence"]["high"] == 1  # 0.95
        assert report_data["matches"]["by_confidence"]["medium"] == 2  # 0.88 and 0.72
        assert report_data["matches"]["by_confidence"]["low"] == 0  # none below 0.7

        # Check metrics
        assert "metrics.baseline" in report_data["metrics"]
        assert report_data["metrics"]["metrics.baseline"]["total_matches"] == 100

    @pytest.mark.asyncio
    async def test_section_generation(self, action, mock_context, params):
        """Test each section generator."""
        report_data = action._collect_report_data(mock_context, params)

        # Test executive summary
        exec_summary = action._generate_executive_summary(report_data)
        assert "# Executive Summary" in exec_summary
        assert "500" in exec_summary  # total metabolites
        assert "30.0%" in exec_summary  # three-way percentage
        assert "Key Achievements" in exec_summary

        # Test methodology
        methodology = action._generate_methodology_overview(report_data)
        assert "# Methodology Overview" in methodology
        assert "Three-Stage Progressive Enhancement" in methodology
        assert "Nightingale Platform" in methodology

        # Test dataset overview
        dataset_overview = action._generate_dataset_overview(report_data)
        assert "# Dataset Overview" in dataset_overview
        assert "Israeli10K" in dataset_overview
        assert "UKBB" in dataset_overview
        assert "Arivale" in dataset_overview

        # Test overlap analysis
        overlap_analysis = action._generate_three_way_overlap_analysis(report_data)
        assert "# Three-Way Overlap Analysis" in overlap_analysis
        assert "500" in overlap_analysis  # total unique
        assert "150" in overlap_analysis  # three-way count
        assert "Pairwise Overlaps" in overlap_analysis

    @pytest.mark.asyncio
    async def test_markdown_formatting(self, action, mock_context, params):
        """Test markdown output is valid."""
        report_data = action._collect_report_data(mock_context, params)

        # Generate a section
        exec_summary = action._generate_executive_summary(report_data)

        # Check markdown elements
        assert exec_summary.count("#") >= 2  # Headers
        assert "|" in exec_summary  # Tables
        assert "**" in exec_summary  # Bold text
        assert "-" in exec_summary  # List items

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Markdown module not installed in CI environment")
    async def test_html_conversion(self, action, mock_context, params):
        """Test HTML generation and styling."""
        report_data = action._collect_report_data(mock_context, params)
        markdown_content = "# Test Report\n\n**Bold text**\n\n| Col1 | Col2 |\n|------|------|\n| A | B |"

        with patch("markdown.Markdown") as mock_markdown:
            mock_md_instance = Mock()
            mock_md_instance.convert.return_value = "<h1>Test Report</h1>"
            mock_markdown.return_value = mock_md_instance

            html_content = action._convert_to_html(markdown_content, report_data)

            assert "<!DOCTYPE html>" in html_content
            assert "<style>" in html_content
            assert "Test Report" in html_content
            assert "font-family" in html_content

    @pytest.mark.asyncio
    async def test_visualization_embedding(self, action, mock_context, params):
        """Test embedding of charts/images."""
        report_data = action._collect_report_data(mock_context, params)

        # Check visualization data was collected
        assert "visualizations" in report_data
        assert report_data["visualizations"].get("venn_diagram") == "/path/to/venn.png"

        # Generate overlap analysis with visualizations
        overlap_section = action._generate_three_way_overlap_analysis(report_data)

        # Should reference visualization files
        assert (
            "Visualization" in overlap_section
            or "accompanying visualization" in overlap_section
        )

    @pytest.mark.asyncio
    async def test_export_formats(self, action, mock_context, params, tmp_path):
        """Test all export formats."""
        # Execute the action
        result = await action.execute_typed(params, mock_context)

        # Check that details contain the expected data
        assert "exported_files" in result.details

        exported = result.details["exported_files"]

        # Check markdown was exported
        assert "markdown" in exported
        md_path = Path(exported["markdown"])
        assert md_path.exists()
        assert md_path.suffix == ".md"

        # Check JSON was exported
        assert "json" in exported
        json_path = Path(exported["json"])
        assert json_path.exists()
        assert json_path.suffix == ".json"

        # Verify JSON content
        with open(json_path) as f:
            json_data = json.load(f)
            assert "metadata" in json_data
            assert "statistics" in json_data

    @pytest.mark.asyncio
    async def test_missing_data_handling(self, action, params, tmp_path):
        """Test graceful handling of missing data."""
        # Create context with missing data
        context = Mock(spec=StrategyExecutionContext)
        context.get_action_data = Mock(return_value={})

        # Should still generate report without errors
        result = await action.execute_typed(params, context)

        assert result.details.get("sections_generated", 0) > 0

        # Check report was created
        assert "markdown" in result.details.get("exported_files", {})

    @pytest.mark.asyncio
    async def test_template_customization(self, action, mock_context, params, tmp_path):
        """Test custom template usage."""
        # Create custom template directory
        template_dir = tmp_path / "custom_templates"
        template_dir.mkdir()

        # Update params with custom template dir
        params.template_dir = str(template_dir)

        # Execute action
        result = await action.execute_typed(params, mock_context)

        assert result.details.get("exported_files") is not None
        # Custom templates would be loaded if they existed

    @pytest.mark.asyncio
    async def test_error_handling(self, action, params):
        """Test error handling in report generation."""
        # Create context that will cause errors
        context = Mock(spec=StrategyExecutionContext)
        context.get_action_data = Mock(side_effect=Exception("Test error"))

        result = await action.execute_typed(params, context)

        assert result.details.get("success") is False
        assert "error" in result.details
        assert "Test error" in str(result.details["error"])

    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, action, mock_context, params):
        """Test quality metrics calculation."""
        report_data = action._collect_report_data(mock_context, params)
        metrics = action._calculate_quality_metrics(report_data)

        assert "high_confidence_count" in metrics
        assert "medium_confidence_count" in metrics
        assert "low_confidence_count" in metrics
        assert metrics["high_confidence_count"] == 1
        assert metrics["medium_confidence_count"] == 2
        assert metrics["low_confidence_count"] == 0

        # Check percentages
        assert metrics["high_confidence_percent"] == pytest.approx(33.3, rel=0.1)
        assert metrics["medium_confidence_percent"] == pytest.approx(66.7, rel=0.1)
        assert metrics["low_confidence_percent"] == pytest.approx(0.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_report_assembly(self, action, mock_context, params):
        """Test report assembly with all sections."""
        sections = {
            "executive_summary": "# Executive Summary\nTest content",
            "methodology_overview": "# Methodology\nTest methodology",
            "dataset_overview": "# Dataset Overview\nTest datasets",
            "three_way_overlap_analysis": "# Three-Way Analysis\nTest analysis",
            "recommendations": "# Recommendations\nTest recommendations",
        }

        report = action._assemble_report(sections, params)

        # Check structure
        assert "# Three-Way Metabolomics Mapping Report" in report
        assert "Generated:" in report
        assert "Table of Contents" in report
        assert "Executive Summary" in report
        assert "---" in report  # Section separators
        assert "automatically by the Biomapper" in report  # Footer

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, action, mock_context, params):
        """Test that action tracks appropriate metrics."""
        result = await action.execute_typed(params, mock_context)

        assert "exported_files" in result.details

        # Get metrics from details
        metrics = result.details
        assert "report_size_kb" in metrics
        assert "sections_success_rate" in metrics
        assert "formats_exported" in metrics

        assert metrics["report_size_kb"] > 0
        assert metrics["sections_success_rate"] > 0
        assert metrics["formats_exported"] >= 2  # At least markdown and json

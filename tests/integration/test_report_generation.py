"""Integration tests for report generation workflow."""

import os
import tempfile
import pytest

from biomapper.core.strategy_actions.generate_enhancement_report import (
    GenerateEnhancementReport,
    GenerateEnhancementReportParams,
)


class TestReportGenerationIntegration:
    """Integration tests for complete report generation workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def realistic_metrics(self):
        """Realistic metrics data from a three-stage enhancement."""
        return {
            "metrics.baseline": {
                "stage": "baseline",
                "total_unmatched_input": 2500,
                "total_matched": 1125,
                "match_rate": 0.45,
                "avg_confidence": 0.85,
                "execution_time": 12.7,
                "match_distribution": {"exact": 875, "fuzzy": 250},
            },
            "metrics.api": {
                "stage": "api_enhanced",
                "total_unmatched_input": 1375,
                "total_matched": 412,
                "match_rate": 0.30,
                "cumulative_match_rate": 0.615,
                "api_calls_made": 687,
                "cache_hits": 298,
                "execution_time": 34.2,
                "enrichment_sources": {"pubchem": 215, "chebi": 127, "hmdb": 70},
            },
            "metrics.vector": {
                "stage": "vector_enhanced",
                "total_unmatched_input": 963,
                "total_matched": 241,
                "match_rate": 0.25,
                "cumulative_match_rate": 0.711,
                "vectors_searched": 963,
                "avg_similarity_score": 0.793,
                "execution_time": 18.5,
                "similarity_distribution": {
                    "very_high": 45,
                    "high": 89,
                    "medium": 75,
                    "low": 32,
                },
            },
        }

    async def test_full_workflow_with_realistic_data(self, temp_dir, realistic_metrics):
        """Test complete workflow with realistic metabolomics data."""
        # Setup
        output_path = os.path.join(temp_dir, "metabolomics_enhancement_report.md")

        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.baseline", "metrics.api", "metrics.vector"],
            stage_names=[
                "Baseline Fuzzy Matching",
                "CTS API Enhancement",
                "Vector Similarity Search",
            ],
            output_path=output_path,
            include_visualizations=True,
            include_detailed_stats=True,
        )

        # Create action
        action = GenerateEnhancementReport()

        # Create context with metrics
        context = realistic_metrics

        # Execute
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        # Verify result
        assert result.details["metrics_found"] == 3
        assert result.details["report_path"] == output_path

        # Verify file exists and has content
        assert os.path.exists(output_path)

        with open(output_path, "r") as f:
            content = f.read()

        # Verify content structure
        assert "# Metabolomics Progressive Enhancement Report" in content
        assert "## Executive Summary" in content
        assert "45%" in content or "45.0%" in content  # Baseline
        assert "71.1%" in content  # Final cumulative
        assert "58% relative improvement" in content  # Improvement

        # Verify table
        assert "| Baseline Fuzzy Matching |" in content
        assert "| CTS API Enhancement |" in content
        assert "| Vector Similarity Search |" in content

        # Verify ASCII chart
        assert "Match Rate by Enhancement Stage" in content
        assert "│" in content  # Box drawing characters

        # Verify detailed stats
        assert "2,500" in content  # Formatted number
        assert "API calls made: 687" in content
        assert "Average similarity score: 0.793" in content

    async def test_report_with_missing_stages(self, temp_dir):
        """Test report generation when some stages are missing."""
        # Only baseline and vector metrics (API stage missing)
        partial_metrics = {
            "metrics.baseline": {
                "total_unmatched_input": 1000,
                "total_matched": 400,
                "match_rate": 0.40,
                "execution_time": 5.0,
            },
            # API metrics missing
            "metrics.vector": {
                "total_unmatched_input": 600,
                "total_matched": 180,
                "match_rate": 0.30,
                "cumulative_match_rate": 0.58,
                "execution_time": 8.0,
            },
        }

        output_path = os.path.join(temp_dir, "partial_report.md")

        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.baseline", "metrics.api", "metrics.vector"],
            output_path=output_path,
        )

        action = GenerateEnhancementReport()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=partial_metrics,
        )

        # Should handle gracefully
        assert result.details["metrics_found"] == 2
        assert os.path.exists(output_path)

    async def test_report_with_custom_baseline(self, temp_dir, realistic_metrics):
        """Test improvement calculations with custom baseline."""
        output_path = os.path.join(temp_dir, "custom_baseline_report.md")

        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.baseline", "metrics.api", "metrics.vector"],
            output_path=output_path,
            comparison_baseline="metrics.api",  # Use API stage as baseline
        )

        action = GenerateEnhancementReport()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=realistic_metrics,
        )

        assert result.details["baseline_used"] == "metrics.api"

        # Verify file content uses API as baseline
        with open(output_path, "r") as f:
            content = f.read()

        # Should calculate improvement from 61.5% to 71.1%
        assert "61.5%" in content or "62%" in content  # API baseline
        assert (
            "15.6% relative improvement" in content
            or "16% relative improvement" in content
        )

    async def test_minimal_report_without_visualizations(self, temp_dir):
        """Test minimal report generation without charts or detailed stats."""
        minimal_metrics = {
            "metrics.single": {
                "match_rate": 0.75,
                "total_matched": 750,
                "total_unmatched_input": 1000,
            }
        }

        output_path = os.path.join(temp_dir, "minimal_report.md")

        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.single"],
            stage_names=["Single Stage"],
            output_path=output_path,
            include_visualizations=False,
            include_detailed_stats=False,
        )

        action = GenerateEnhancementReport()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=minimal_metrics,
        )

        # Verify minimal content
        with open(output_path, "r") as f:
            content = f.read()

        # Should not include visualizations or detailed stats
        assert "Match Rate by Enhancement Stage" not in content
        assert "## Detailed Statistics" not in content

        # Should still have summary
        assert "## Executive Summary" in content
        assert "75%" in content

    async def test_report_directory_creation(self, temp_dir):
        """Test that nested directories are created if needed."""
        nested_path = os.path.join(
            temp_dir, "reports", "metabolomics", "enhancement_report.md"
        )

        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.test"], output_path=nested_path
        )

        action = GenerateEnhancementReport()

        # Create simple metrics
        context = {"metrics.test": {"match_rate": 0.5, "total_matched": 50}}

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        # Verify nested directories were created
        assert os.path.exists(nested_path)
        assert os.path.isfile(nested_path)

    async def test_error_handling_for_invalid_path(self):
        """Test error handling for invalid output paths."""
        params = GenerateEnhancementReportParams(
            metrics_keys=["metrics.test"],
            output_path="/invalid/path/that/cannot/be/created/report.md",
        )

        action = GenerateEnhancementReport()
        context = {"metrics.test": {"match_rate": 0.5}}

        # Should raise an error for invalid path
        with pytest.raises(Exception):
            await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context,
            )

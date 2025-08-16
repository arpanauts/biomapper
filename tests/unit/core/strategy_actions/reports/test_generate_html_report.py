"""Test suite for HTML report generation - WRITE FIRST!"""

import pytest
from pathlib import Path
import tempfile
from typing import Dict, Any, List
from unittest.mock import MagicMock

# This may fail initially - expected in TDD
from biomapper.core.strategy_actions.reports.generate_html_report import (
    GenerateHtmlReportAction,
    GenerateHtmlReportParams,
    ReportSection
)


class MockContext:
    """Mock context for testing."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def get_action_data(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set_action_data(self, key: str, value: Any):
        self._data[key] = value


class TestGenerateHtmlReport:
    """Test HTML report generation."""
    
    @pytest.fixture
    def sample_context(self):
        """Create context with statistics and data."""
        return MockContext({
            "datasets": {
                "final_results": [
                    {"source": "P12345", "target": "ENSG001", "confidence": 0.95},
                    {"source": "Q67890", "target": "ENSG002", "confidence": 0.80},
                    {"source": "A12345", "target": None, "confidence": 0.0}
                ]
            },
            "statistics": {
                "mapping_summary": {
                    "total_input": 1201,
                    "direct_match": 812,
                    "normalized_match": 111,
                    "unmapped": 278,
                    "success_rate": 0.769
                },
                "confidence_distribution": {
                    "high": 723,
                    "medium": 134,
                    "low": 66
                },
                "merge_statistics": {
                    "datasets_merged": 3,
                    "total_rows": 923,
                    "duplicates_removed": 0,
                    "one_to_many_relationships": {
                        "arivale-kg2c": {
                            "type": "one-to-many",
                            "expansion_factor": 1.05,
                            "duplicated_keys": 47
                        }
                    }
                }
            },
            "output_files": []
        })
    
    @pytest.mark.asyncio
    async def test_basic_report_generation(self, sample_context):
        """Test basic HTML report creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Test Protein Mapping Report",
                output_path=str(output_path),
                sections=[
                    ReportSection(
                        title="Executive Summary",
                        type="summary",
                        data=sample_context.get_action_data("statistics")["mapping_summary"]
                    ),
                    ReportSection(
                        title="Results Table",
                        type="table",
                        data=sample_context.get_action_data("datasets")["final_results"]
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            assert result.details.get("success") == True
            assert output_path.exists()
            
            # Check HTML content
            html_content = output_path.read_text()
            assert "Test Protein Mapping Report" in html_content
            assert "Executive Summary" in html_content
            assert "76.9" in html_content or "769" in html_content  # Success rate percentage
            
            # Check that output file was tracked
            output_files = sample_context.get_action_data("output_files", [])
            assert str(output_path) in output_files
            
    @pytest.mark.asyncio
    async def test_statistics_inclusion(self, sample_context):
        """Test that statistics are properly included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "stats_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Statistics Report",
                output_path=str(output_path),
                include_statistics=True,
                sections=[
                    ReportSection(
                        title="Confidence Distribution",
                        type="statistics",
                        data=sample_context.get_action_data("statistics")["confidence_distribution"]
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            assert result.details.get("success") == True
            
            html_content = output_path.read_text()
            assert "high" in html_content.lower() or "High" in html_content
            assert "723" in html_content  # High confidence count
            
    @pytest.mark.asyncio
    async def test_one_to_many_reporting(self, sample_context):
        """Test that one-to-many relationships are reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "one_to_many_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="One-to-Many Analysis",
                output_path=str(output_path),
                sections=[
                    ReportSection(
                        title="Merge Statistics",
                        type="statistics",
                        data=sample_context.get_action_data("statistics")["merge_statistics"]
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            html_content = output_path.read_text()
            assert "one-to-many" in html_content.lower() or "47" in html_content
            
    @pytest.mark.asyncio
    async def test_chart_section(self, sample_context):
        """Test chart section rendering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "chart_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Chart Test",
                output_path=str(output_path),
                sections=[
                    ReportSection(
                        title="Confidence Chart",
                        type="chart",
                        data={
                            "labels": ["High", "Medium", "Low"],
                            "values": [723, 134, 66],
                            "chart_type": "bar"
                        }
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            html_content = output_path.read_text()
            # Check for chart-related content (canvas or chart.js reference)
            assert "canvas" in html_content.lower() or "chart" in html_content.lower()
            
    @pytest.mark.asyncio
    async def test_text_section(self, sample_context):
        """Test text section rendering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "text_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Text Report",
                output_path=str(output_path),
                sections=[
                    ReportSection(
                        title="Analysis Notes",
                        type="text",
                        data="This analysis successfully mapped 76.9% of input proteins."
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            html_content = output_path.read_text()
            assert "76.9%" in html_content
            
    @pytest.mark.asyncio
    async def test_custom_template(self, sample_context):
        """Test using a custom template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "custom_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="custom_template",  # Will fall back to default if not found
                title="Custom Template Test",
                output_path=str(output_path),
                sections=[
                    ReportSection(
                        title="Summary",
                        type="summary",
                        data={"test": "data"}
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            # Should handle missing template gracefully
            assert output_path.exists() or not result.details.get("success")
            
    @pytest.mark.asyncio
    async def test_timestamp_inclusion(self, sample_context):
        """Test timestamp inclusion in reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "timestamp_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Timestamp Test",
                output_path=str(output_path),
                include_timestamp=True,
                sections=[]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            if output_path.exists():
                html_content = output_path.read_text()
                # Check for date/time patterns
                assert "202" in html_content  # Year 202x
                
    @pytest.mark.asyncio
    async def test_comprehensive_report(self, sample_context):
        """Test comprehensive report with all section types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "comprehensive_report.html"
            
            action = GenerateHtmlReportAction()
            params = GenerateHtmlReportParams(
                template_name="protein_mapping_report",
                title="Arivale to KG2C Protein Mapping Report",
                output_path=str(output_path),
                include_timestamp=True,
                include_statistics=True,
                sections=[
                    ReportSection(
                        title="Executive Summary",
                        type="summary",
                        data=sample_context.get_action_data("statistics")["mapping_summary"]
                    ),
                    ReportSection(
                        title="Mapping Statistics",
                        type="statistics",
                        data=sample_context.get_action_data("statistics")["confidence_distribution"]
                    ),
                    ReportSection(
                        title="High Confidence Matches",
                        type="table",
                        data=[r for r in sample_context.get_action_data("datasets")["final_results"] 
                              if r["confidence"] > 0.8]
                    ),
                    ReportSection(
                        title="Analysis Notes",
                        type="text",
                        data="Progressive mapping completed with three stages: direct, historical, and gene symbol bridge."
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context
            )
            
            assert result.details.get("success") == True
            assert output_path.exists()
            
            html_content = output_path.read_text()
            # Check all sections are present
            assert "Executive Summary" in html_content
            assert "Mapping Statistics" in html_content
            assert "High Confidence Matches" in html_content
            assert "Analysis Notes" in html_content
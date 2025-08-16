"""Test suite for GenerateHtmlReportAction - Enhanced Version with all requirements!"""

import pytest
from typing import Dict, Any

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.reports.generate_html_report import (
    GenerateHtmlReportAction,
    GenerateHtmlReportParams,
    ReportSection,
)


class TestGenerateHtmlReportActionEnhanced:
    """Comprehensive test suite for HTML report generation."""

    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Create sample context with mapping results."""
        return {
            "datasets": {
                "source_proteins": [
                    {"id": "P12345", "name": "Protein A", "organism": "Human"},
                    {"id": "Q67890", "name": "Protein B", "organism": "Human"},
                    {"id": "A11111", "name": "Protein C", "organism": "Mouse"},
                ],
                "mapped_proteins": [
                    {
                        "source_id": "P12345",
                        "target_id": "UNIPROT:P12345",
                        "confidence": 1.0,
                    },
                    {
                        "source_id": "Q67890",
                        "target_id": "UNIPROT:Q67890",
                        "confidence": 0.95,
                    },
                ],
                "unmapped_proteins": [{"id": "A11111", "reason": "No match found"}],
            },
            "statistics": {
                "mapping_summary": {
                    "total_input": 3,
                    "successfully_mapped": 2,
                    "failed_mapping": 1,
                    "mapping_rate": 0.667,
                    "average_confidence": 0.975,
                },
                "stage_metrics": {
                    "direct_match": {"count": 1, "success_rate": 1.0},
                    "fuzzy_match": {"count": 1, "success_rate": 0.95},
                    "semantic_match": {"count": 0, "success_rate": 0.0},
                },
                "composite_expansion": {
                    "total_input_rows": 10,
                    "total_output_rows": 15,
                    "expansion_factor": 1.5,
                },
            },
            "output_files": {},
        }

    @pytest.fixture
    def action(self) -> GenerateHtmlReportAction:
        """Create action instance."""
        return GenerateHtmlReportAction()

    @pytest.mark.asyncio
    async def test_basic_report_generation(self, action, sample_context, tmp_path):
        """Test basic HTML report generation."""
        output_file = tmp_path / "test_report.html"

        params = GenerateHtmlReportParams(
            title="Protein Mapping Report",
            sections=[
                ReportSection(
                    type="summary",
                    title="Executive Summary",
                    data_key="statistics.mapping_summary",
                ),
                ReportSection(
                    type="table",
                    title="Mapped Proteins",
                    data_key="datasets.mapped_proteins",
                    columns=["source_id", "target_id", "confidence"],
                ),
            ],
            output_file=str(output_file),
            style_theme="professional",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True
        assert output_file.exists()
        assert result.file_size > 0
        assert result.sections_generated == 2

        # Check HTML content
        html_content = output_file.read_text()
        assert "<html" in html_content
        assert "Protein Mapping Report" in html_content
        assert "Executive Summary" in html_content
        assert "Mapped Proteins" in html_content
        assert "P12345" in html_content
        assert "UNIPROT:P12345" in html_content

    @pytest.mark.asyncio
    async def test_complete_report_with_all_sections(
        self, action, sample_context, tmp_path
    ):
        """Test generation of complete report with all section types."""
        output_file = tmp_path / "complete_report.html"

        params = GenerateHtmlReportParams(
            title="Complete Biomapper Analysis Report",
            subtitle="Arivale to KG2C Protein Mapping",
            sections=[
                ReportSection(
                    type="metadata",
                    title="Report Information",
                    data={
                        "Generated": "2024-01-15",
                        "Strategy": "prot_arv_to_kg2c_v2.2",
                        "Version": "2.2.0",
                    },
                ),
                ReportSection(
                    type="summary",
                    title="Mapping Summary",
                    data_key="statistics.mapping_summary",
                ),
                ReportSection(
                    type="metrics",
                    title="Stage Performance",
                    data_key="statistics.stage_metrics",
                ),
                ReportSection(
                    type="table",
                    title="Successfully Mapped",
                    data_key="datasets.mapped_proteins",
                    columns=["source_id", "target_id", "confidence"],
                    sort_by="confidence",
                    sort_order="desc",
                ),
                ReportSection(
                    type="table",
                    title="Failed Mappings",
                    data_key="datasets.unmapped_proteins",
                    columns=["id", "reason"],
                    highlight_rows=True,
                ),
                ReportSection(
                    type="statistics",
                    title="Composite ID Expansion",
                    data_key="statistics.composite_expansion",
                ),
            ],
            output_file=str(output_file),
            style_theme="professional",
            include_toc=True,
            include_footer=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True
        assert result.sections_generated == 6

        html_content = output_file.read_text()

        # Check all sections present
        assert "Report Information" in html_content
        assert "Mapping Summary" in html_content
        assert "Stage Performance" in html_content
        assert "Successfully Mapped" in html_content
        assert "Failed Mappings" in html_content
        assert "Composite ID Expansion" in html_content

        # Check TOC
        assert 'class="toc"' in html_content or "Table of Contents" in html_content

        # Check footer
        assert "Generated" in html_content

    @pytest.mark.asyncio
    async def test_custom_styling(self, action, sample_context, tmp_path):
        """Test custom CSS styling options."""
        output_file = tmp_path / "styled_report.html"

        params = GenerateHtmlReportParams(
            title="Styled Report",
            sections=[
                ReportSection(
                    type="summary",
                    title="Summary",
                    data_key="statistics.mapping_summary",
                )
            ],
            output_file=str(output_file),
            style_theme="dark",
            custom_css="""
                .custom-highlight {
                    background-color: #ffeb3b;
                    font-weight: bold;
                }
            """,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True

        html_content = output_file.read_text()
        assert ".custom-highlight" in html_content
        assert "background-color: #ffeb3b" in html_content

    @pytest.mark.asyncio
    async def test_large_dataset_pagination(self, action, tmp_path):
        """Test handling of large datasets with pagination."""
        # Create large dataset
        large_data = [
            {"id": f"P{i:05d}", "name": f"Protein {i}", "value": i} for i in range(1000)
        ]

        context = {"datasets": {"large_table": large_data}, "statistics": {}}

        output_file = tmp_path / "large_report.html"

        params = GenerateHtmlReportParams(
            title="Large Dataset Report",
            sections=[
                ReportSection(
                    type="table",
                    title="Large Protein Table",
                    data_key="datasets.large_table",
                    columns=["id", "name", "value"],
                    max_rows=100,
                    enable_search=True,
                    enable_export=True,
                )
            ],
            output_file=str(output_file),
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.success is True
        assert result.rows_processed == 1000
        assert len([w for w in result.warnings if "truncated" in w]) > 0

        html_content = output_file.read_text()
        assert "100" in html_content  # Should show limited rows

    @pytest.mark.asyncio
    async def test_chart_integration_placeholder(
        self, action, sample_context, tmp_path
    ):
        """Test chart placeholder generation for visualization."""
        output_file = tmp_path / "chart_report.html"

        params = GenerateHtmlReportParams(
            title="Report with Charts",
            sections=[
                ReportSection(
                    type="chart",
                    title="Mapping Success Rate",
                    chart_type="bar",
                    data_key="statistics.stage_metrics",
                    chart_id="success_rate_chart",
                )
            ],
            output_file=str(output_file),
            include_chart_js=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True

        html_content = output_file.read_text()
        assert 'id="success_rate_chart"' in html_content
        assert "Chart.js" in html_content or "chart" in html_content.lower()

    @pytest.mark.asyncio
    async def test_export_formats(self, action, sample_context, tmp_path):
        """Test multiple export format support."""
        base_path = tmp_path / "report"

        params = GenerateHtmlReportParams(
            title="Multi-Format Report",
            sections=[
                ReportSection(
                    type="table", title="Results", data_key="datasets.mapped_proteins"
                )
            ],
            output_file=str(base_path.with_suffix(".html")),
            export_formats=["html", "json", "csv"],
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True
        assert base_path.with_suffix(".html").exists()

        # Check for export data preparation
        assert result.exports_prepared or "export_data" in sample_context.get(
            "report_data", {}
        )

    @pytest.mark.asyncio
    async def test_error_handling(self, action):
        """Test error handling for invalid inputs."""
        # Test missing data key
        context = {"datasets": {}, "statistics": {}}
        params = GenerateHtmlReportParams(
            title="Error Test",
            sections=[
                ReportSection(
                    type="table", title="Missing Data", data_key="datasets.nonexistent"
                )
            ],
            output_file="/tmp/error_report.html",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        # Should succeed but with warnings about missing data
        assert result.success is True or "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_nested_data_access(self, action, tmp_path):
        """Test accessing nested data structures."""
        context = {
            "datasets": {
                "nested": {
                    "level1": {
                        "level2": [{"id": "1", "value": "A"}, {"id": "2", "value": "B"}]
                    }
                }
            },
            "statistics": {},
        }

        output_file = tmp_path / "nested_report.html"

        params = GenerateHtmlReportParams(
            title="Nested Data Report",
            sections=[
                ReportSection(
                    type="table",
                    title="Nested Table",
                    data_key="datasets.nested.level1.level2",
                    columns=["id", "value"],
                )
            ],
            output_file=str(output_file),
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.success is True

        html_content = output_file.read_text()
        assert "A" in html_content
        assert "B" in html_content

    @pytest.mark.asyncio
    async def test_template_customization(self, action, sample_context, tmp_path):
        """Test HTML template customization."""
        output_file = tmp_path / "custom_template.html"

        params = GenerateHtmlReportParams(
            title="Custom Template Report",
            sections=[
                ReportSection(
                    type="custom",
                    title="Custom Section",
                    template="<div class='custom'>{{ data }}</div>",
                    data={"message": "Custom content"},
                )
            ],
            output_file=str(output_file),
            template_engine="string",  # Use simple string replacement
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True

        html_content = output_file.read_text()
        assert (
            "Custom content" in html_content or "<div class='custom'>" in html_content
        )

    @pytest.mark.asyncio
    async def test_all_themes(self, action, sample_context, tmp_path):
        """Test all available styling themes."""
        themes = ["professional", "dark", "light", "minimal"]

        for theme in themes:
            output_file = tmp_path / f"{theme}_report.html"

            params = GenerateHtmlReportParams(
                title=f"{theme.title()} Theme Report",
                sections=[
                    ReportSection(
                        type="summary",
                        title="Summary",
                        data_key="statistics.mapping_summary",
                    )
                ],
                output_file=str(output_file),
                style_theme=theme,
            )

            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=sample_context,
            )
            assert result.success is True
            assert output_file.exists()

    @pytest.mark.asyncio
    async def test_metrics_section_generation(self, action, sample_context, tmp_path):
        """Test metrics section with card layout."""
        output_file = tmp_path / "metrics_report.html"

        params = GenerateHtmlReportParams(
            title="Metrics Report",
            sections=[
                ReportSection(
                    type="metrics",
                    title="Performance Metrics",
                    data_key="statistics.stage_metrics",
                )
            ],
            output_file=str(output_file),
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context,
        )

        assert result.success is True
        html_content = output_file.read_text()
        assert "metric-card" in html_content or "metrics-grid" in html_content
        assert "direct_match" in html_content or "Direct Match" in html_content

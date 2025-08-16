# Implementation Prompt 2: HTML Report Generation & Dataset Merging

## 🎯 Mission
Implement two critical actions:
1. `GENERATE_HTML_REPORT` - Create professional HTML reports with tables, statistics, and styling
2. Fix `MERGE_DATASETS` - Ensure proper handling of one-to-many mappings and composite identifiers

## 📍 Context
You are implementing report generation capabilities for the biomapper project. These actions must produce professional, readable reports that visualize mapping results and statistics.

## 📁 Files to Create/Modify

### 1. Test File for HTML Report (CREATE FIRST - TDD!)
**Path:** `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/reports/test_generate_html_report.py`

```python
"""Test suite for GenerateHtmlReportAction - WRITE THIS FIRST!"""

import pytest
from typing import Dict, Any
from pathlib import Path
import tempfile
import json
from unittest.mock import MagicMock, patch

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.reports.generate_html_report import (
    GenerateHtmlReportAction,
    GenerateHtmlReportParams,
    GenerateHtmlReportResult
)


class TestGenerateHtmlReportAction:
    """Comprehensive test suite for HTML report generation."""
    
    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Create sample context with mapping results."""
        return {
            "datasets": {
                "source_proteins": [
                    {"id": "P12345", "name": "Protein A", "organism": "Human"},
                    {"id": "Q67890", "name": "Protein B", "organism": "Human"},
                    {"id": "A11111", "name": "Protein C", "organism": "Mouse"}
                ],
                "mapped_proteins": [
                    {"source_id": "P12345", "target_id": "UNIPROT:P12345", "confidence": 1.0},
                    {"source_id": "Q67890", "target_id": "UNIPROT:Q67890", "confidence": 0.95}
                ],
                "unmapped_proteins": [
                    {"id": "A11111", "reason": "No match found"}
                ]
            },
            "statistics": {
                "mapping_summary": {
                    "total_input": 3,
                    "successfully_mapped": 2,
                    "failed_mapping": 1,
                    "mapping_rate": 0.667,
                    "average_confidence": 0.975
                },
                "stage_metrics": {
                    "direct_match": {"count": 1, "success_rate": 1.0},
                    "fuzzy_match": {"count": 1, "success_rate": 0.95},
                    "semantic_match": {"count": 0, "success_rate": 0.0}
                },
                "composite_expansion": {
                    "total_input_rows": 10,
                    "total_output_rows": 15,
                    "expansion_factor": 1.5
                }
            },
            "output_files": {}
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
                {
                    "type": "summary",
                    "title": "Executive Summary",
                    "data_key": "statistics.mapping_summary"
                },
                {
                    "type": "table",
                    "title": "Mapped Proteins",
                    "data_key": "datasets.mapped_proteins",
                    "columns": ["source_id", "target_id", "confidence"]
                }
            ],
            output_file=str(output_file),
            style_theme="professional"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert output_file.exists()
        assert result.file_size > 0
        assert result.sections_generated == 2
        
        # Check HTML content
        html_content = output_file.read_text()
        assert "<html>" in html_content
        assert "Protein Mapping Report" in html_content
        assert "Executive Summary" in html_content
        assert "Mapped Proteins" in html_content
        assert "P12345" in html_content
        assert "UNIPROT:P12345" in html_content
    
    @pytest.mark.asyncio
    async def test_complete_report_with_all_sections(self, action, sample_context, tmp_path):
        """Test generation of complete report with all section types."""
        output_file = tmp_path / "complete_report.html"
        
        params = GenerateHtmlReportParams(
            title="Complete Biomapper Analysis Report",
            subtitle="Arivale to KG2C Protein Mapping",
            sections=[
                {
                    "type": "metadata",
                    "title": "Report Information",
                    "data": {
                        "Generated": "2024-01-15",
                        "Strategy": "prot_arv_to_kg2c_v2.2",
                        "Version": "2.2.0"
                    }
                },
                {
                    "type": "summary",
                    "title": "Mapping Summary",
                    "data_key": "statistics.mapping_summary"
                },
                {
                    "type": "metrics",
                    "title": "Stage Performance",
                    "data_key": "statistics.stage_metrics"
                },
                {
                    "type": "table",
                    "title": "Successfully Mapped",
                    "data_key": "datasets.mapped_proteins",
                    "columns": ["source_id", "target_id", "confidence"],
                    "sort_by": "confidence",
                    "sort_order": "desc"
                },
                {
                    "type": "table",
                    "title": "Failed Mappings",
                    "data_key": "datasets.unmapped_proteins",
                    "columns": ["id", "reason"],
                    "highlight_rows": True
                },
                {
                    "type": "statistics",
                    "title": "Composite ID Expansion",
                    "data_key": "statistics.composite_expansion"
                }
            ],
            output_file=str(output_file),
            style_theme="professional",
            include_toc=True,
            include_footer=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
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
        assert '<div class="toc">' in html_content or 'Table of Contents' in html_content
        
        # Check footer
        assert "Generated" in html_content
    
    @pytest.mark.asyncio
    async def test_custom_styling(self, action, sample_context, tmp_path):
        """Test custom CSS styling options."""
        output_file = tmp_path / "styled_report.html"
        
        params = GenerateHtmlReportParams(
            title="Styled Report",
            sections=[
                {
                    "type": "summary",
                    "title": "Summary",
                    "data_key": "statistics.mapping_summary"
                }
            ],
            output_file=str(output_file),
            style_theme="dark",
            custom_css="""
                .custom-highlight {
                    background-color: #ffeb3b;
                    font-weight: bold;
                }
            """
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        html_content = output_file.read_text()
        assert ".custom-highlight" in html_content
        assert "background-color: #ffeb3b" in html_content
    
    @pytest.mark.asyncio
    async def test_large_dataset_pagination(self, action, tmp_path):
        """Test handling of large datasets with pagination."""
        # Create large dataset
        large_data = [
            {"id": f"P{i:05d}", "name": f"Protein {i}", "value": i}
            for i in range(1000)
        ]
        
        context = {
            "datasets": {"large_table": large_data},
            "statistics": {}
        }
        
        output_file = tmp_path / "large_report.html"
        
        params = GenerateHtmlReportParams(
            title="Large Dataset Report",
            sections=[
                {
                    "type": "table",
                    "title": "Large Protein Table",
                    "data_key": "datasets.large_table",
                    "columns": ["id", "name", "value"],
                    "max_rows": 100,
                    "enable_search": True,
                    "enable_export": True
                }
            ],
            output_file=str(output_file)
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert result.rows_processed == 1000
        assert result.warnings == ["Table 'Large Protein Table' truncated to 100 rows"]
        
        html_content = output_file.read_text()
        assert "Showing 100 of 1000 rows" in html_content or "100 rows" in html_content
    
    @pytest.mark.asyncio
    async def test_chart_integration_placeholder(self, action, sample_context, tmp_path):
        """Test chart placeholder generation for visualization."""
        output_file = tmp_path / "chart_report.html"
        
        params = GenerateHtmlReportParams(
            title="Report with Charts",
            sections=[
                {
                    "type": "chart",
                    "title": "Mapping Success Rate",
                    "chart_type": "bar",
                    "data_key": "statistics.stage_metrics",
                    "chart_id": "success_rate_chart"
                }
            ],
            output_file=str(output_file),
            include_chart_js=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        html_content = output_file.read_text()
        assert '<canvas id="success_rate_chart">' in html_content or '<div id="success_rate_chart">' in html_content
        assert "Chart.js" in html_content or "chart placeholder" in html_content.lower()
    
    @pytest.mark.asyncio
    async def test_export_formats(self, action, sample_context, tmp_path):
        """Test multiple export format support."""
        base_path = tmp_path / "report"
        
        params = GenerateHtmlReportParams(
            title="Multi-Format Report",
            sections=[
                {
                    "type": "table",
                    "title": "Results",
                    "data_key": "datasets.mapped_proteins"
                }
            ],
            output_file=str(base_path.with_suffix('.html')),
            export_formats=["html", "json", "csv"]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert base_path.with_suffix('.html').exists()
        
        # Check for export data preparation
        assert "export_data" in sample_context.get("report_data", {}) or result.exports_prepared
    
    @pytest.mark.asyncio
    async def test_error_handling(self, action):
        """Test error handling for invalid inputs."""
        # Test missing data key
        context = {"datasets": {}, "statistics": {}}
        params = GenerateHtmlReportParams(
            title="Error Test",
            sections=[
                {
                    "type": "table",
                    "title": "Missing Data",
                    "data_key": "datasets.nonexistent"
                }
            ],
            output_file="/tmp/error_report.html"
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_nested_data_access(self, action, tmp_path):
        """Test accessing nested data structures."""
        context = {
            "datasets": {
                "nested": {
                    "level1": {
                        "level2": [
                            {"id": "1", "value": "A"},
                            {"id": "2", "value": "B"}
                        ]
                    }
                }
            },
            "statistics": {}
        }
        
        output_file = tmp_path / "nested_report.html"
        
        params = GenerateHtmlReportParams(
            title="Nested Data Report",
            sections=[
                {
                    "type": "table",
                    "title": "Nested Table",
                    "data_key": "datasets.nested.level1.level2",
                    "columns": ["id", "value"]
                }
            ],
            output_file=str(output_file)
        )
        
        result = await action.execute_typed(params, context)
        
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
                {
                    "type": "custom",
                    "title": "Custom Section",
                    "template": "<div class='custom'>{{ data }}</div>",
                    "data": {"message": "Custom content"}
                }
            ],
            output_file=str(output_file),
            template_engine="jinja2"  # or "string"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        
        html_content = output_file.read_text()
        assert "Custom content" in html_content or "<div class='custom'>" in html_content
```

### 2. Implementation File for HTML Report
**Path:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_html_report.py`

```python
"""Generate HTML reports from mapping results."""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import json
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Configuration for a report section."""
    
    type: str = Field(..., description="Section type: summary, table, metrics, chart, custom")
    title: str = Field(..., description="Section title")
    data_key: Optional[str] = Field(None, description="Dot-notation path to data")
    data: Optional[Dict[str, Any]] = Field(None, description="Direct data for section")
    columns: Optional[List[str]] = Field(None, description="Table columns to display")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_order: Optional[str] = Field("asc", description="Sort order: asc or desc")
    max_rows: Optional[int] = Field(None, description="Maximum rows to display")
    highlight_rows: bool = Field(False, description="Highlight alternate rows")
    chart_type: Optional[str] = Field(None, description="Chart type for visualization")
    chart_id: Optional[str] = Field(None, description="Chart element ID")
    template: Optional[str] = Field(None, description="Custom HTML template")
    enable_search: bool = Field(False, description="Enable table search")
    enable_export: bool = Field(False, description="Enable data export")


class GenerateHtmlReportParams(BaseModel):
    """Parameters for HTML report generation."""
    
    title: str = Field(..., description="Report title")
    subtitle: Optional[str] = Field(None, description="Report subtitle")
    sections: List[Union[ReportSection, Dict[str, Any]]] = Field(
        ..., description="Report sections configuration"
    )
    output_file: str = Field(..., description="Output HTML file path")
    style_theme: str = Field(
        "professional",
        description="Style theme: professional, dark, light, minimal"
    )
    custom_css: Optional[str] = Field(None, description="Custom CSS styles")
    include_toc: bool = Field(False, description="Include table of contents")
    include_footer: bool = Field(True, description="Include footer with metadata")
    include_chart_js: bool = Field(False, description="Include Chart.js library")
    export_formats: Optional[List[str]] = Field(
        None,
        description="Additional export formats: json, csv"
    )
    template_engine: str = Field("string", description="Template engine: string or jinja2")


class GenerateHtmlReportResult(BaseModel):
    """Result of HTML report generation."""
    
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size: int = 0
    sections_generated: int = 0
    rows_processed: int = 0
    warnings: List[str] = Field(default_factory=list)
    exports_prepared: bool = False


@register_action("GENERATE_HTML_REPORT")
class GenerateHtmlReportAction(TypedStrategyAction[GenerateHtmlReportParams, GenerateHtmlReportResult]):
    """
    Generate professional HTML reports from mapping results.
    
    Creates formatted HTML reports with tables, statistics, charts,
    and custom styling based on the mapping results and statistics.
    """
    
    def get_params_model(self) -> type[GenerateHtmlReportParams]:
        """Get the parameters model."""
        return GenerateHtmlReportParams
    
    def get_result_model(self) -> type[GenerateHtmlReportResult]:
        """Get the result model."""
        return GenerateHtmlReportResult
    
    async def execute_typed(
        self,
        params: GenerateHtmlReportParams,
        context: Dict[str, Any]
    ) -> GenerateHtmlReportResult:
        """Execute HTML report generation."""
        try:
            # Handle different context types
            ctx = self._get_context_dict(context)
            
            # Initialize HTML components
            html_parts = []
            warnings = []
            sections_generated = 0
            total_rows = 0
            
            # Generate HTML header
            html_parts.append(self._generate_header(params))
            
            # Generate table of contents if requested
            if params.include_toc:
                html_parts.append(self._generate_toc(params.sections))
            
            # Process each section
            for section_config in params.sections:
                # Convert dict to ReportSection if needed
                if isinstance(section_config, dict):
                    section = ReportSection(**section_config)
                else:
                    section = section_config
                
                # Get section data
                section_data = self._get_section_data(section, ctx)
                
                if section_data is None and section.data_key:
                    warnings.append(f"Data not found for section '{section.title}'")
                    continue
                
                # Generate section HTML based on type
                section_html, rows = self._generate_section(section, section_data, params, warnings)
                
                if section_html:
                    html_parts.append(section_html)
                    sections_generated += 1
                    total_rows += rows
            
            # Generate footer if requested
            if params.include_footer:
                html_parts.append(self._generate_footer(params, ctx))
            
            # Generate closing HTML
            html_parts.append(self._generate_closing())
            
            # Combine all parts
            html_content = "\n".join(html_parts)
            
            # Write to file
            output_path = Path(params.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding='utf-8')
            
            # Prepare export formats if requested
            if params.export_formats:
                self._prepare_exports(params, ctx)
            
            # Store in context
            if "output_files" not in ctx:
                ctx["output_files"] = {}
            ctx["output_files"]["html_report"] = str(output_path)
            
            logger.info(
                f"Generated HTML report with {sections_generated} sections "
                f"({total_rows} total rows) at {output_path}"
            )
            
            return GenerateHtmlReportResult(
                success=True,
                message=f"Successfully generated HTML report at {output_path}",
                file_path=str(output_path),
                file_size=output_path.stat().st_size,
                sections_generated=sections_generated,
                rows_processed=total_rows,
                warnings=warnings,
                exports_prepared=bool(params.export_formats)
            )
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return GenerateHtmlReportResult(
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
    
    def _get_section_data(self, section: ReportSection, context: Dict[str, Any]) -> Any:
        """Get data for a section using dot notation path."""
        if section.data:
            return section.data
        
        if not section.data_key:
            return None
        
        # Navigate through nested structure
        keys = section.data_key.split('.')
        data = context
        
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        
        return data
    
    def _generate_header(self, params: GenerateHtmlReportParams) -> str:
        """Generate HTML header with styles."""
        styles = self._get_styles(params.style_theme)
        if params.custom_css:
            styles += f"\n{params.custom_css}"
        
        chart_js = ""
        if params.include_chart_js:
            chart_js = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
        
        subtitle_html = ""
        if params.subtitle:
            subtitle_html = f"<h2>{params.subtitle}</h2>"
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{params.title}</title>
    <style>
{styles}
    </style>
    {chart_js}
</head>
<body>
    <div class="container">
        <h1>{params.title}</h1>
        {subtitle_html}
"""
    
    def _generate_section(
        self,
        section: ReportSection,
        data: Any,
        params: GenerateHtmlReportParams,
        warnings: List[str]
    ) -> tuple[str, int]:
        """Generate HTML for a section based on its type."""
        rows_count = 0
        
        if section.type == "summary":
            html = self._generate_summary_section(section, data)
        elif section.type == "table":
            html, rows_count = self._generate_table_section(section, data, warnings)
        elif section.type == "metrics":
            html = self._generate_metrics_section(section, data)
        elif section.type == "statistics":
            html = self._generate_statistics_section(section, data)
        elif section.type == "metadata":
            html = self._generate_metadata_section(section, data)
        elif section.type == "chart":
            html = self._generate_chart_section(section, data)
        elif section.type == "custom":
            html = self._generate_custom_section(section, data)
        else:
            html = f"<div class='section'><h3>{section.title}</h3><p>Unknown section type: {section.type}</p></div>"
        
        return html, rows_count
    
    def _generate_summary_section(self, section: ReportSection, data: Dict[str, Any]) -> str:
        """Generate summary section HTML."""
        if not data:
            return ""
        
        rows = []
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                formatted_value = f"{value:.3f}" if value < 1 else f"{value:,.0f}"
            else:
                formatted_value = str(value)
            rows.append(f"<tr><td class='label'>{formatted_key}:</td><td class='value'>{formatted_value}</td></tr>")
        
        return f"""
        <div class="section">
            <h3>{section.title}</h3>
            <table class="summary-table">
                {''.join(rows)}
            </table>
        </div>
        """
    
    def _generate_table_section(
        self,
        section: ReportSection,
        data: List[Dict[str, Any]],
        warnings: List[str]
    ) -> tuple[str, int]:
        """Generate table section HTML."""
        if not data:
            return "", 0
        
        # Apply row limit if specified
        original_count = len(data)
        if section.max_rows and len(data) > section.max_rows:
            data = data[:section.max_rows]
            warnings.append(f"Table '{section.title}' truncated to {section.max_rows} rows")
        
        # Determine columns
        columns = section.columns or list(data[0].keys()) if data else []
        
        # Generate header
        header_cells = ''.join(f"<th>{col}</th>" for col in columns)
        
        # Generate rows
        row_html = []
        for i, row in enumerate(data):
            cells = []
            for col in columns:
                value = row.get(col, "")
                if isinstance(value, float):
                    value = f"{value:.3f}"
                cells.append(f"<td>{value}</td>")
            
            row_class = "highlight" if section.highlight_rows and i % 2 else ""
            row_html.append(f"<tr class='{row_class}'>{''.join(cells)}</tr>")
        
        # Add row count info
        count_info = ""
        if section.max_rows and original_count > section.max_rows:
            count_info = f"<p class='info'>Showing {section.max_rows} of {original_count} rows</p>"
        
        return f"""
        <div class="section">
            <h3>{section.title}</h3>
            {count_info}
            <table class="data-table">
                <thead>
                    <tr>{header_cells}</tr>
                </thead>
                <tbody>
                    {''.join(row_html)}
                </tbody>
            </table>
        </div>
        """, len(data)
    
    def _generate_metrics_section(self, section: ReportSection, data: Dict[str, Any]) -> str:
        """Generate metrics section with cards."""
        if not data:
            return ""
        
        cards = []
        for metric_name, metric_data in data.items():
            if isinstance(metric_data, dict):
                count = metric_data.get('count', 0)
                rate = metric_data.get('success_rate', 0)
                cards.append(f"""
                    <div class="metric-card">
                        <h4>{metric_name.replace('_', ' ').title()}</h4>
                        <div class="metric-value">{count}</div>
                        <div class="metric-rate">{rate:.1%} success</div>
                    </div>
                """)
        
        return f"""
        <div class="section">
            <h3>{section.title}</h3>
            <div class="metrics-grid">
                {''.join(cards)}
            </div>
        </div>
        """
    
    def _generate_statistics_section(self, section: ReportSection, data: Dict[str, Any]) -> str:
        """Generate statistics section."""
        return self._generate_summary_section(section, data)
    
    def _generate_metadata_section(self, section: ReportSection, data: Dict[str, Any]) -> str:
        """Generate metadata section."""
        return self._generate_summary_section(section, data)
    
    def _generate_chart_section(self, section: ReportSection, data: Any) -> str:
        """Generate chart placeholder section."""
        chart_id = section.chart_id or f"chart_{section.title.replace(' ', '_').lower()}"
        
        return f"""
        <div class="section">
            <h3>{section.title}</h3>
            <div class="chart-container">
                <canvas id="{chart_id}"></canvas>
            </div>
            <script>
                // Chart data would be rendered here
                // Data: {json.dumps(data) if data else 'null'}
            </script>
        </div>
        """
    
    def _generate_custom_section(self, section: ReportSection, data: Any) -> str:
        """Generate custom section."""
        if section.template:
            # Simple template replacement
            content = section.template.replace("{{ data }}", str(data))
        else:
            content = f"<pre>{json.dumps(data, indent=2)}</pre>"
        
        return f"""
        <div class="section">
            <h3>{section.title}</h3>
            {content}
        </div>
        """
    
    def _generate_toc(self, sections: List[Union[ReportSection, Dict[str, Any]]]) -> str:
        """Generate table of contents."""
        toc_items = []
        for section_config in sections:
            if isinstance(section_config, dict):
                title = section_config.get('title', 'Section')
            else:
                title = section_config.title
            
            anchor = title.replace(' ', '_').lower()
            toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')
        
        return f"""
        <div class="toc">
            <h2>Table of Contents</h2>
            <ul>
                {''.join(toc_items)}
            </ul>
        </div>
        """
    
    def _generate_footer(self, params: GenerateHtmlReportParams, context: Dict[str, Any]) -> str:
        """Generate report footer."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""
        <div class="footer">
            <p>Generated: {timestamp}</p>
            <p>Report: {params.title}</p>
        </div>
        """
    
    def _generate_closing(self) -> str:
        """Generate closing HTML tags."""
        return """
    </div>
</body>
</html>
"""
    
    def _get_styles(self, theme: str) -> str:
        """Get CSS styles for the theme."""
        base_styles = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #333;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .data-table th,
        .data-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .data-table th {
            background: #f0f0f0;
            font-weight: bold;
        }
        .summary-table {
            width: auto;
            margin: 20px 0;
        }
        .summary-table td {
            padding: 8px 15px;
        }
        .summary-table .label {
            font-weight: bold;
            text-align: right;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2196F3;
        }
        .metric-rate {
            color: #666;
            margin-top: 10px;
        }
        .toc {
            background: #f0f0f0;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
        }
        .toc ul {
            list-style-type: none;
            padding-left: 20px;
        }
        .toc a {
            color: #2196F3;
            text-decoration: none;
        }
        .footer {
            margin-top: 50px;
            padding: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
        }
        .info {
            color: #666;
            font-style: italic;
        }
        .highlight {
            background: #fffbf0;
        }
        .chart-container {
            position: relative;
            height: 400px;
            margin: 20px 0;
        }
        """
        
        if theme == "dark":
            return base_styles + """
            body { background: #1a1a1a; color: #e0e0e0; }
            h1, h2, h3 { color: #f0f0f0; }
            .section { background: #2a2a2a; }
            .data-table th { background: #3a3a3a; }
            """
        
        return base_styles
    
    def _prepare_exports(self, params: GenerateHtmlReportParams, context: Dict[str, Any]):
        """Prepare export formats."""
        # Store export data in context for later use
        if "report_data" not in context:
            context["report_data"] = {}
        
        context["report_data"]["export_data"] = {
            "title": params.title,
            "sections": params.sections,
            "generated": datetime.now().isoformat()
        }
```

### 3. Test File for MERGE_DATASETS Fix
**Path:** `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/utils/test_merge_datasets_fix.py`

```python
"""Test suite for MERGE_DATASETS fix with one-to-many support."""

import pytest
from typing import Dict, Any

from biomapper.core.strategy_actions.utils.merge_datasets import MergeDatasets


class TestMergeDatasetsOneToMany:
    """Test one-to-many mapping support in MERGE_DATASETS."""
    
    @pytest.mark.asyncio
    async def test_one_to_many_expansion(self):
        """Test that one-to-many mappings are properly handled."""
        context = {
            "datasets": {
                "source": [
                    {"id": "P12345", "name": "Protein A"},
                    {"id": "Q67890,Q11111", "name": "Protein B"}  # Composite
                ],
                "expanded": [
                    {"id": "P12345", "name": "Protein A", "_original_composite": None},
                    {"id": "Q67890", "name": "Protein B", "_original_composite": "Q67890,Q11111"},
                    {"id": "Q11111", "name": "Protein B", "_original_composite": "Q67890,Q11111"}
                ],
                "mappings": [
                    {"source_id": "P12345", "target_id": "TARGET1"},
                    {"source_id": "Q67890", "target_id": "TARGET2"},
                    {"source_id": "Q11111", "target_id": "TARGET3"}
                ]
            }
        }
        
        action = MergeDatasets()
        params = {
            "input_keys": ["expanded", "mappings"],
            "output_key": "merged",
            "merge_on": "id",
            "merge_with": "source_id",
            "keep_all": True,
            "track_one_to_many": True
        }
        
        result = await action.execute(params, context)
        
        assert result["success"] is True
        merged = context["datasets"]["merged"]
        
        # Check that all mappings are preserved
        assert len(merged) == 3
        
        # Check one-to-many tracking
        assert "one_to_many_stats" in context.get("statistics", {})
        stats = context["statistics"]["one_to_many_stats"]
        assert stats["total_source_records"] == 2
        assert stats["total_mapped_records"] == 3
        assert stats["expansion_factor"] == 1.5
```

### 4. Run Tests and Iterate
```bash
# HTML Report Tests
poetry run pytest tests/unit/core/strategy_actions/reports/test_generate_html_report.py -xvs

# MERGE_DATASETS Fix Tests  
poetry run pytest tests/unit/core/strategy_actions/utils/test_merge_datasets_fix.py -xvs

# Coverage check
poetry run pytest tests/unit/core/strategy_actions/reports/ --cov=biomapper.core.strategy_actions.reports --cov-report=term-missing
```

## 📋 Acceptance Criteria

### HTML Report Generation:
1. ✅ Generate professional HTML reports with multiple section types
2. ✅ Support tables, summaries, metrics, charts, and custom sections
3. ✅ Apply styling themes (professional, dark, light, minimal)
4. ✅ Include table of contents and footer
5. ✅ Handle large datasets with pagination/truncation
6. ✅ Support nested data access with dot notation
7. ✅ Provide export format preparation
8. ✅ Generate valid, well-formatted HTML
9. ✅ Store output file path in context
10. ✅ Handle errors gracefully with clear messages

### MERGE_DATASETS Fix:
1. ✅ Properly handle one-to-many mappings
2. ✅ Track expansion statistics
3. ✅ Preserve all mapped records
4. ✅ Support composite identifier tracking
5. ✅ Maintain data integrity during merge

## 🔧 Technical Requirements

- Use standard HTML5 structure
- Include responsive CSS styling
- Support Chart.js integration
- Handle large datasets efficiently
- Use Pydantic for parameter validation
- Follow TypedStrategyAction pattern
- Register actions with decorators
- Maintain backward compatibility

## 🎯 Definition of Done

- [ ] All tests written and passing
- [ ] HTML reports generate correctly
- [ ] Styling themes work properly
- [ ] Large datasets handled efficiently
- [ ] One-to-many merges work correctly
- [ ] Statistics tracked accurately
- [ ] Documentation complete
- [ ] Error handling comprehensive
- [ ] Performance validated
- [ ] Integration tested with v2.2 strategy
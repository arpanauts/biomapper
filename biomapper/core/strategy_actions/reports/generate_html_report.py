"""Generate HTML reports from mapping results - Enhanced Version."""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import json
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Configuration for a report section."""

    type: str = Field(
        ...,
        description="Section type: summary, table, metrics, chart, custom, metadata, statistics",
    )
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
    output_path: str = Field(..., description="Output HTML file path")
    style_theme: str = Field(
        "professional", description="Style theme: professional, dark, light, minimal"
    )
    custom_css: Optional[str] = Field(None, description="Custom CSS styles")
    include_toc: bool = Field(False, description="Include table of contents")
    include_footer: bool = Field(True, description="Include footer with metadata")
    include_chart_js: bool = Field(False, description="Include Chart.js library")
    export_formats: Optional[List[str]] = Field(
        None, description="Additional export formats: json, csv"
    )
    template_engine: str = Field(
        "string", description="Template engine: string or jinja2"
    )


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
class GenerateHtmlReportAction(
    TypedStrategyAction[GenerateHtmlReportParams, GenerateHtmlReportResult]
):
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
        current_identifiers: List[str],
        current_ontology_type: str,
        params: GenerateHtmlReportParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> GenerateHtmlReportResult:
        """Execute HTML report generation."""
        try:
            # Wrap context for uniform access
            context_wrapper = UniversalContext.wrap(context)
            ctx = self._get_context_dict(context_wrapper)

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
                section_html, rows = self._generate_section(
                    section, section_data, params, warnings
                )

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
            output_path.write_text(html_content, encoding="utf-8")

            # Prepare export formats if requested
            exports_prepared = False
            if params.export_formats:
                self._prepare_exports(params, ctx)
                exports_prepared = True

            # Store in context
            if "output_files" not in ctx:
                ctx["output_files"] = {}
            ctx["output_files"]["html_report"] = str(output_path)

            # Update context with output files
            output_files = context_wrapper.get_output_files()
            output_files.append(str(output_path))
            context_wrapper.set("output_files", output_files)

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
                exports_prepared=exports_prepared,
            )

        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return GenerateHtmlReportResult(success=False, message=f"Error: {str(e)}")

    def _get_context_dict(self, context: UniversalContext) -> Dict[str, Any]:
        """Get dictionary from wrapped context."""
        return {
            "datasets": context.get_datasets(),
            "statistics": context.get_statistics(),
            "output_files": context.get_output_files(),
        }

    def _get_section_data(self, section: ReportSection, context: Dict[str, Any]) -> Any:
        """Get data for a section using dot notation path."""
        if section.data:
            return section.data

        if not section.data_key:
            return None

        # Navigate through nested structure using dot notation
        keys = section.data_key.split(".")
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
            subtitle_html = f"<h2 class='subtitle'>{params.subtitle}</h2>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{params.title}</title>
    <style>
{styles}
    </style>
    {chart_js}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{params.title}</h1>
            {subtitle_html}
        </div>
"""

    def _generate_section(
        self,
        section: ReportSection,
        data: Any,
        params: GenerateHtmlReportParams,
        warnings: List[str],
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
            html = f"<div class='section'><h3>{section.title}</h3><p class='error'>Unknown section type: {section.type}</p></div>"

        return html, rows_count

    def _generate_summary_section(
        self, section: ReportSection, data: Dict[str, Any]
    ) -> str:
        """Generate summary section HTML."""
        if not data:
            return f"<div class='section'><h3>{section.title}</h3><p class='warning'>No data available</p></div>"

        cards = []
        for key, value in data.items():
            formatted_key = key.replace("_", " ").title()

            # Format values appropriately
            if isinstance(value, float):
                if value < 1:
                    formatted_value = f"{value:.1%}"
                elif value < 10:
                    formatted_value = f"{value:.3f}"
                else:
                    formatted_value = f"{value:,.0f}"
            elif isinstance(value, int):
                formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)

            cards.append(
                f"""
                <div class="summary-card">
                    <div class="summary-value">{formatted_value}</div>
                    <div class="summary-label">{formatted_key}</div>
                </div>
            """
            )

        return f"""
        <div class="section" id="{section.title.replace(' ', '_').lower()}">
            <h3>{section.title}</h3>
            <div class="summary-grid">
                {''.join(cards)}
            </div>
        </div>
        """

    def _generate_table_section(
        self, section: ReportSection, data: List[Dict[str, Any]], warnings: List[str]
    ) -> tuple[str, int]:
        """Generate table section HTML."""
        if not data:
            return (
                f"<div class='section'><h3>{section.title}</h3><p class='warning'>No data available</p></div>",
                0,
            )

        # Apply row limit if specified
        original_count = len(data)
        if section.max_rows and len(data) > section.max_rows:
            data = data[: section.max_rows]
            warnings.append(
                f"Table '{section.title}' truncated to {section.max_rows} rows"
            )

        # Determine columns
        columns = section.columns or list(data[0].keys()) if data else []

        # Sort data if requested
        if section.sort_by and section.sort_by in columns:
            reverse_sort = section.sort_order == "desc"
            sort_key = section.sort_by
            data = sorted(
                data, key=lambda x: x.get(sort_key, ""), reverse=reverse_sort
            )

        # Generate header
        header_cells = "".join(
            f"<th>{col.replace('_', ' ').title()}</th>" for col in columns
        )

        # Generate rows
        row_html = []
        for i, row in enumerate(data):
            cells = []
            for col in columns:
                value = row.get(col, "")

                # Format values
                if isinstance(value, float):
                    if col.lower() in ["confidence", "score", "rate", "probability"]:
                        # Color-code confidence scores
                        if value >= 0.8:
                            formatted = (
                                f'<span class="high-confidence">{value:.3f}</span>'
                            )
                        elif value >= 0.6:
                            formatted = (
                                f'<span class="medium-confidence">{value:.3f}</span>'
                            )
                        else:
                            formatted = (
                                f'<span class="low-confidence">{value:.3f}</span>'
                            )
                    else:
                        formatted = f"{value:.3f}"
                elif value is None:
                    formatted = '<span class="null-value">-</span>'
                else:
                    formatted = str(value)

                cells.append(f"<td>{formatted}</td>")

            row_class = "highlight-row" if section.highlight_rows and i % 2 else ""
            row_html.append(f"<tr class='{row_class}'>{''.join(cells)}</tr>")

        # Add row count info
        count_info = ""
        if section.max_rows and original_count > section.max_rows:
            count_info = f"<p class='table-info'>Showing {section.max_rows} of {original_count:,} rows</p>"

        return (
            f"""
        <div class="section" id="{section.title.replace(' ', '_').lower()}">
            <h3>{section.title}</h3>
            {count_info}
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>{header_cells}</tr>
                    </thead>
                    <tbody>
                        {''.join(row_html)}
                    </tbody>
                </table>
            </div>
        </div>
        """,
            original_count,
        )

    def _generate_metrics_section(
        self, section: ReportSection, data: Dict[str, Any]
    ) -> str:
        """Generate metrics section with cards."""
        if not data:
            return f"<div class='section'><h3>{section.title}</h3><p class='warning'>No data available</p></div>"

        cards = []
        for metric_name, metric_data in data.items():
            if isinstance(metric_data, dict):
                count = metric_data.get("count", 0)
                rate = metric_data.get("success_rate", 0)

                # Format rate as percentage
                rate_display = f"{rate:.1%}" if isinstance(rate, float) else str(rate)

                cards.append(
                    f"""
                    <div class="metric-card">
                        <h4 class="metric-title">{metric_name.replace('_', ' ').title()}</h4>
                        <div class="metric-value">{count:,}</div>
                        <div class="metric-rate">{rate_display} success</div>
                    </div>
                """
                )

        return f"""
        <div class="section" id="{section.title.replace(' ', '_').lower()}">
            <h3>{section.title}</h3>
            <div class="metrics-grid">
                {''.join(cards)}
            </div>
        </div>
        """

    def _generate_statistics_section(
        self, section: ReportSection, data: Dict[str, Any]
    ) -> str:
        """Generate statistics section."""
        return self._generate_summary_section(section, data)

    def _generate_metadata_section(
        self, section: ReportSection, data: Dict[str, Any]
    ) -> str:
        """Generate metadata section."""
        return self._generate_summary_section(section, data)

    def _generate_chart_section(self, section: ReportSection, data: Any) -> str:
        """Generate chart placeholder section."""
        chart_id = (
            section.chart_id or f"chart_{section.title.replace(' ', '_').lower()}"
        )
        chart_type = section.chart_type or "bar"

        return f"""
        <div class="section" id="{section.title.replace(' ', '_').lower()}">
            <h3>{section.title}</h3>
            <div class="chart-container">
                <canvas id="{chart_id}" width="400" height="200"></canvas>
            </div>
            <script>
                // Chart.js code would be rendered here
                // Chart type: {chart_type}
                // Data: {json.dumps(data) if data else 'null'}
                console.log('Chart placeholder for {chart_id}');
            </script>
        </div>
        """

    def _generate_custom_section(self, section: ReportSection, data: Any) -> str:
        """Generate custom section."""
        if section.template:
            # Simple template replacement for now
            content = section.template.replace(
                "{{ data }}", json.dumps(data) if data else "null"
            )
        else:
            content = f"<pre class='custom-data'>{json.dumps(data, indent=2) if data else 'No data'}</pre>"

        return f"""
        <div class="section" id="{section.title.replace(' ', '_').lower()}">
            <h3>{section.title}</h3>
            <div class="custom-content">
                {content}
            </div>
        </div>
        """

    def _generate_toc(
        self, sections: List[Union[ReportSection, Dict[str, Any]]]
    ) -> str:
        """Generate table of contents."""
        toc_items = []
        for section_config in sections:
            if isinstance(section_config, dict):
                title = section_config.get("title", "Section")
            else:
                title = section_config.title

            anchor = title.replace(" ", "_").lower()
            toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')

        return f"""
        <div class="toc">
            <h2>Table of Contents</h2>
            <ul class="toc-list">
                {''.join(toc_items)}
            </ul>
        </div>
        """

    def _generate_footer(
        self, params: GenerateHtmlReportParams, context: Dict[str, Any]
    ) -> str:
        """Generate report footer."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""
        <div class="footer">
            <div class="footer-content">
                <div class="footer-left">
                    <p><strong>Report:</strong> {params.title}</p>
                    {f'<p><strong>Subtitle:</strong> {params.subtitle}</p>' if params.subtitle else ''}
                </div>
                <div class="footer-right">
                    <p><strong>Generated:</strong> {timestamp}</p>
                    <p><strong>Theme:</strong> {params.style_theme}</p>
                </div>
            </div>
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
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            margin: -20px -20px 30px -20px;
            border-radius: 0 0 10px 10px;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 300;
        }
        
        .subtitle {
            margin: 10px 0 0 0;
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 300;
        }
        
        .section {
            background: white;
            margin: 30px 0;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .section h3 {
            margin-top: 0;
            margin-bottom: 20px;
            color: #2c3e50;
            font-size: 1.4rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        
        .summary-value {
            font-size: 2.2rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .summary-label {
            color: #7f8c8d;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        
        .data-table th,
        .data-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        .data-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
        }
        
        .data-table tr:hover {
            background: #f8f9fa;
        }
        
        .highlight-row {
            background: #fff8e1 !important;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            border-top: 3px solid #667eea;
        }
        
        .metric-title {
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 1rem;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .metric-rate {
            color: #7f8c8d;
            font-size: 0.9rem;
        }
        
        .toc {
            background: #e9ecef;
            padding: 25px;
            border-radius: 10px;
            margin: 30px 0;
        }
        
        .toc h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        
        .toc-list {
            list-style: none;
            padding: 0;
        }
        
        .toc-list li {
            margin: 8px 0;
        }
        
        .toc-list a {
            color: #667eea;
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 5px;
            transition: background 0.2s;
        }
        
        .toc-list a:hover {
            background: #fff;
            text-decoration: none;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            margin: 40px -20px -20px -20px;
            padding: 25px 30px;
            border-radius: 10px 10px 0 0;
        }
        
        .footer-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .footer-left, .footer-right {
            flex: 1;
        }
        
        .footer-right {
            text-align: right;
        }
        
        .footer p {
            margin: 5px 0;
            font-size: 0.9rem;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .custom-content {
            margin: 20px 0;
        }
        
        .custom-data {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }
        
        .table-info {
            color: #6c757d;
            font-style: italic;
            margin: 10px 0;
        }
        
        .warning {
            color: #856404;
            background: #fff3cd;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ffeeba;
        }
        
        .error {
            color: #721c24;
            background: #f8d7da;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #f5c6cb;
        }
        
        .high-confidence {
            color: #28a745;
            font-weight: bold;
        }
        
        .medium-confidence {
            color: #ffc107;
            font-weight: bold;
        }
        
        .low-confidence {
            color: #dc3545;
            font-weight: bold;
        }
        
        .null-value {
            color: #6c757d;
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                margin: -10px -10px 20px -10px;
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .footer {
                margin: 30px -10px -10px -10px;
            }
            
            .footer-content {
                flex-direction: column;
                text-align: center;
            }
            
            .footer-right {
                text-align: center;
                margin-top: 10px;
            }
        }
        """

        if theme == "dark":
            return (
                base_styles
                + """
            body { background: #1a1a1a; }
            .section { background: #2d2d2d; color: #e0e0e0; }
            .section h3 { color: #f0f0f0; }
            .data-table th { background: #3a3a3a; color: #e0e0e0; }
            .data-table tr:hover { background: #3a3a3a; }
            .summary-card { background: #3a3a3a; color: #e0e0e0; }
            .metric-card { background: #2d2d2d; color: #e0e0e0; }
            .toc { background: #3a3a3a; color: #e0e0e0; }
            .custom-data { background: #3a3a3a; color: #e0e0e0; }
            .chart-container { background: #3a3a3a; }
            """
            )
        elif theme == "light":
            return (
                base_styles
                + """
            .header { background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%); }
            .section { box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            """
            )
        elif theme == "minimal":
            return (
                base_styles
                + """
            .header { background: #2c3e50; }
            .section { box-shadow: none; border: 1px solid #e9ecef; }
            .summary-card { border-left: none; border: 1px solid #e9ecef; }
            .metric-card { box-shadow: none; border: 1px solid #e9ecef; border-top: 1px solid #e9ecef; }
            """
            )

        return base_styles

    def _prepare_exports(
        self, params: GenerateHtmlReportParams, context: Dict[str, Any]
    ) -> None:
        """Prepare export formats."""
        # Store export data in context for later use
        if "report_data" not in context:
            context["report_data"] = {}

        export_data = {
            "title": params.title,
            "subtitle": params.subtitle,
            "sections": [
                section.dict() if isinstance(section, ReportSection) else section
                for section in params.sections
            ],
            "generated": datetime.now().isoformat(),
            "theme": params.style_theme,
        }

        context["report_data"]["export_data"] = export_data

        # Could extend this to actually generate CSV/JSON files
        logger.info(f"Prepared export data for formats: {params.export_formats}")

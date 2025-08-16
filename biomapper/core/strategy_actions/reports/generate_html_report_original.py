"""Generate HTML reports for biomapper analysis results."""

from typing import List, Any, Optional, Dict, Literal
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
import logging

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Definition of a report section."""

    title: str = Field(..., description="Section title")
    type: Literal["summary", "statistics", "table", "chart", "text"] = Field(
        ..., description="Type of section"
    )
    data: Any = Field(..., description="Data for the section")


class GenerateHtmlReportParams(BaseModel):
    """Parameters for GENERATE_HTML_REPORT action."""

    template_name: str = Field(
        "protein_mapping_report", description="Name of the template to use"
    )
    title: str = Field(..., description="Report title")
    output_path: str = Field(..., description="Path to save the HTML report")
    sections: List[ReportSection] = Field(
        default_factory=list, description="List of report sections"
    )
    include_timestamp: bool = Field(True, description="Include generation timestamp")
    include_statistics: bool = Field(
        True, description="Include overall statistics from context"
    )
    export_pdf: bool = Field(
        False, description="Also export as PDF (requires weasyprint)"
    )
    pdf_path: Optional[str] = Field(
        None, description="Path for PDF export (defaults to output_path with .pdf)"
    )


@register_action("GENERATE_HTML_REPORT")
class GenerateHtmlReportAction(
    TypedStrategyAction[GenerateHtmlReportParams, StandardActionResult]
):
    """Generate comprehensive HTML reports from analysis results.

    This action creates beautiful, self-contained HTML reports with statistics,
    tables, and visualizations from biomapper analysis results.

    Example:
        ```yaml
        - name: generate_report
          action:
            type: GENERATE_HTML_REPORT
            params:
              title: "Protein Mapping Report"
              output_path: "${parameters.output_dir}/report.html"
              sections:
                - title: "Executive Summary"
                  type: "summary"
                - title: "Mapping Statistics"
                  type: "statistics"
        ```
    """

    def get_params_model(self) -> type[GenerateHtmlReportParams]:
        """Get the Pydantic model for action parameters."""
        return GenerateHtmlReportParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Get the Pydantic model for action results."""
        return StandardActionResult

    def _generate_html_content(
        self, params: GenerateHtmlReportParams, context: Any
    ) -> str:
        """Generate HTML content from parameters and context."""

        # Try to use Jinja2 if available, otherwise use simple HTML generation
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            template_dir = (
                Path(__file__).parent.parent.parent.parent.parent
                / "templates"
                / "reports"
            )

            if template_dir.exists():
                env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=select_autoescape(["html", "xml"]),
                )

                # Try to load the specific template
                try:
                    template = env.get_template(f"{params.template_name}.html")
                    return template.render(
                        title=params.title,
                        timestamp=datetime.now().isoformat()
                        if params.include_timestamp
                        else None,
                        sections=params.sections,
                        statistics=context.get_action_data("statistics", {})
                        if params.include_statistics
                        else {},
                        include_timestamp=params.include_timestamp,
                        include_statistics=params.include_statistics,
                    )
                except Exception as e:
                    logger.warning(
                        f"Template {params.template_name}.html not found, using fallback: {e}"
                    )
        except ImportError:
            logger.warning("Jinja2 not available, using simple HTML generation")

        # Fallback to simple HTML generation
        return self._generate_simple_html(params, context)

    def _generate_simple_html(
        self, params: GenerateHtmlReportParams, context: Any
    ) -> str:
        """Generate simple HTML without templates."""

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{params.title}</title>",
            "<style>",
            self._get_default_css(),
            "</style>",
            "</head>",
            "<body>",
            '<div class="header">',
            f"<h1>{params.title}</h1>",
        ]

        if params.include_timestamp:
            html_parts.append(
                f'<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
            )

        html_parts.append("</div>")

        # Add sections
        for section in params.sections:
            html_parts.append('<div class="section">')
            html_parts.append(f"<h2>{section.title}</h2>")
            html_parts.append(self._render_section(section))
            html_parts.append("</div>")

        # Add overall statistics if requested
        if params.include_statistics:
            stats = context.get_action_data("statistics", {})
            if stats:
                html_parts.append('<div class="section">')
                html_parts.append("<h2>Overall Statistics</h2>")
                html_parts.append(self._render_statistics(stats))
                html_parts.append("</div>")

        html_parts.extend(["</body>", "</html>"])

        return "\n".join(html_parts)

    def _get_default_css(self) -> str:
        """Get default CSS styles."""
        return """
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: #f5f5f5;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px 40px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
            }
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
            }
            .section { 
                margin: 20px 40px;
                padding: 25px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .section h2 {
                margin-top: 0;
                color: #333;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            .statistics { 
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .stat-card { 
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .stat-value { 
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
            .stat-label { 
                color: #7f8c8d;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            table { 
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td { 
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }
            th { 
                background: #f8f9fa;
                font-weight: 600;
                color: #555;
            }
            tr:hover {
                background: #f8f9fa;
            }
            .success { color: #27ae60; font-weight: bold; }
            .warning { color: #f39c12; font-weight: bold; }
            .error { color: #e74c3c; font-weight: bold; }
            .text-content {
                line-height: 1.6;
                color: #555;
            }
        """

    def _render_section(self, section: ReportSection) -> str:
        """Render a section based on its type."""
        if section.type == "summary":
            return self._render_summary(section.data)
        elif section.type == "statistics":
            return self._render_statistics(section.data)
        elif section.type == "table":
            return self._render_table(section.data)
        elif section.type == "chart":
            return self._render_chart(section.data)
        elif section.type == "text":
            return self._render_text(section.data)
        else:
            return f"<p>Unknown section type: {section.type}</p>"

    def _render_summary(self, data: Dict[str, Any]) -> str:
        """Render a summary section."""
        if not isinstance(data, dict):
            return "<p>Invalid summary data</p>"

        html = ['<div class="statistics">']

        for key, value in data.items():
            # Format the label
            label = key.replace("_", " ").title()

            # Format the value
            if isinstance(value, float):
                if value < 1:
                    formatted_value = f"{value * 100:.1f}%"
                else:
                    formatted_value = f"{value:,.1f}"
            elif isinstance(value, int):
                formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)

            html.append(
                f"""
                <div class="stat-card">
                    <div class="stat-value">{formatted_value}</div>
                    <div class="stat-label">{label}</div>
                </div>
            """
            )

        html.append("</div>")
        return "".join(html)

    def _render_statistics(self, data: Dict[str, Any]) -> str:
        """Render statistics section."""
        if not isinstance(data, dict):
            return "<p>Invalid statistics data</p>"

        # Handle nested statistics
        if "merge_statistics" in data and isinstance(data["merge_statistics"], dict):
            merge_stats = data["merge_statistics"]
            if "one_to_many_relationships" in merge_stats:
                one_to_many = merge_stats["one_to_many_relationships"]
                if one_to_many:
                    data["One-to-Many Mappings"] = len(one_to_many)

        return self._render_summary(data)

    def _render_table(self, data: List[Dict[str, Any]]) -> str:
        """Render a table section."""
        if not data or not isinstance(data, list):
            return "<p>No data available</p>"

        if not isinstance(data[0], dict):
            return "<p>Invalid table data format</p>"

        # Get column names from first row
        columns = list(data[0].keys())

        html = ["<table>"]

        # Header
        html.append("<thead><tr>")
        for col in columns:
            label = col.replace("_", " ").title()
            html.append(f"<th>{label}</th>")
        html.append("</tr></thead>")

        # Body
        html.append("<tbody>")
        for row in data[:100]:  # Limit to first 100 rows for performance
            html.append("<tr>")
            for col in columns:
                value = row.get(col, "")

                # Format special values
                if value is None:
                    formatted = '<span class="error">-</span>'
                elif isinstance(value, float):
                    if col.lower() in ["confidence", "score", "probability"]:
                        if value >= 0.8:
                            formatted = f'<span class="success">{value:.3f}</span>'
                        elif value >= 0.6:
                            formatted = f'<span class="warning">{value:.3f}</span>'
                        else:
                            formatted = f'<span class="error">{value:.3f}</span>'
                    else:
                        formatted = f"{value:.3f}"
                else:
                    formatted = str(value)

                html.append(f"<td>{formatted}</td>")
            html.append("</tr>")

        if len(data) > 100:
            html.append(
                f'<tr><td colspan="{len(columns)}"><em>... and {len(data) - 100} more rows</em></td></tr>'
            )

        html.append("</tbody>")
        html.append("</table>")

        return "".join(html)

    def _render_chart(self, data: Dict[str, Any]) -> str:
        """Render a chart section (placeholder for now)."""
        html = ['<div class="chart-container">']

        if isinstance(data, dict):
            chart_type = data.get("chart_type", "bar")
            labels = data.get("labels", [])
            values = data.get("values", [])

            html.append(f'<canvas id="chart-{id(data)}"></canvas>')
            html.append("<script>")
            html.append(f"// Chart.js code would go here for {chart_type} chart")
            html.append(f"// Labels: {labels}")
            html.append(f"// Values: {values}")
            html.append("</script>")

            # For now, render as a simple table
            if labels and values and len(labels) == len(values):
                html.append('<table style="margin-top: 20px;">')
                for label, value in zip(labels, values):
                    html.append(
                        f"<tr><td>{label}</td><td><strong>{value}</strong></td></tr>"
                    )
                html.append("</table>")
        else:
            html.append("<p>Invalid chart data</p>")

        html.append("</div>")
        return "".join(html)

    def _render_text(self, data: Any) -> str:
        """Render a text section."""
        if isinstance(data, str):
            return f'<div class="text-content">{data}</div>'
        elif isinstance(data, list):
            html = ['<div class="text-content"><ul>']
            for item in data:
                html.append(f"<li>{item}</li>")
            html.append("</ul></div>")
            return "".join(html)
        else:
            return f'<div class="text-content">{str(data)}</div>'

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: GenerateHtmlReportParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute HTML report generation.

        Args:
            current_identifiers: Current list of identifiers (not used)
            current_ontology_type: Current ontology type
            params: Typed parameters for the action
            source_endpoint: Source endpoint (not used)
            target_endpoint: Target endpoint (not used)
            context: Execution context containing datasets and statistics

        Returns:
            StandardActionResult with report generation details
        """
        logger.info(f"Generating HTML report: {params.title}")

        try:
            # Generate HTML content
            html_content = self._generate_html_content(params, context)

            # Write HTML file
            output_path = Path(params.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding="utf-8")

            logger.info(f"HTML report saved to: {output_path}")

            # Track output file
            output_files = context.get_action_data("output_files", [])
            output_files.append(str(output_path))
            context.set_action_data("output_files", output_files)

            # Generate PDF if requested
            pdf_generated = False
            if params.export_pdf:
                try:
                    import weasyprint

                    pdf_path = (
                        Path(params.pdf_path)
                        if params.pdf_path
                        else output_path.with_suffix(".pdf")
                    )
                    weasyprint.HTML(string=html_content).write_pdf(str(pdf_path))
                    output_files.append(str(pdf_path))
                    context.set_action_data("output_files", output_files)
                    pdf_generated = True
                    logger.info(f"PDF report saved to: {pdf_path}")
                except ImportError:
                    logger.warning("PDF export requested but weasyprint not installed")
                except Exception as e:
                    logger.warning(f"PDF export failed: {e}")

            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "GENERATE_HTML_REPORT",
                        "status": "success",
                        "report_title": params.title,
                        "output_path": str(output_path),
                        "sections": len(params.sections),
                        "pdf_generated": pdf_generated,
                    }
                ],
                details={
                    "success": True,
                    "output_path": str(output_path),
                    "sections": len(params.sections),
                    "pdf_generated": pdf_generated,
                    "file_size": output_path.stat().st_size,
                },
            )

        except Exception as e:
            error_msg = f"Error generating HTML report: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "GENERATE_HTML_REPORT",
                        "status": "failed",
                        "error": error_msg,
                    }
                ],
                details={
                    "success": False,
                    "error": error_msg,
                },
            )

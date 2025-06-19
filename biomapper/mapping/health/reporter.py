"""
Health reporting system for endpoint configurations.

This module provides components for generating reports on the health of
endpoint property extraction configurations, including success rates,
failure patterns, and recommendations for improvement.
"""

import json
import logging
import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.session import get_session

logger = logging.getLogger(__name__)


class HealthReportGenerator:
    """Generates reports on endpoint configuration health."""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the report generator.

        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        self.session_owner = db_session is None

    def generate_endpoint_health_report(
        self, endpoint_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a health report for one or all endpoints.

        Args:
            endpoint_id: Optional specific endpoint ID to report on

        Returns:
            Dictionary with the health report
        """
        session = self.db_session or get_session()
        session_owner = self.db_session is None

        try:
            # Base query joining health records with configs and endpoints
            query = """
                SELECT 
                    h.*, 
                    c.extraction_method,
                    c.extraction_pattern,
                    e.name as endpoint_name,
                    e.endpoint_type,
                    e.parent_endpoint_id,
                    e.endpoint_subtype
                FROM 
                    endpoint_property_health h
                JOIN 
                    endpoint_property_configs c 
                    ON (h.endpoint_id = c.endpoint_id 
                        AND h.ontology_type = c.ontology_type 
                        AND h.property_name = c.property_name)
                JOIN 
                    endpoints e 
                    ON h.endpoint_id = e.endpoint_id
            """

            params = {}
            if endpoint_id:
                query += " WHERE h.endpoint_id = :endpoint_id"
                params["endpoint_id"] = endpoint_id

            query += " ORDER BY e.name, h.ontology_type, h.property_name"

            results = session.execute(query, params).fetchall()

            # Process results into a report
            report = {
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "total_configs": len(results),
                "endpoints": {},
            }

            for record in results:
                if record.endpoint_name not in report["endpoints"]:
                    report["endpoints"][record.endpoint_name] = {
                        "endpoint_id": record.endpoint_id,
                        "endpoint_type": record.endpoint_type,
                        "parent_endpoint_id": record.parent_endpoint_id,
                        "endpoint_subtype": record.endpoint_subtype,
                        "total_configs": 0,
                        "healthy_configs": 0,
                        "at_risk_configs": 0,
                        "failed_configs": 0,
                        "ontologies": {},
                    }

                endpoint_report = report["endpoints"][record.endpoint_name]
                endpoint_report["total_configs"] += 1

                # Calculate health score
                total_attempts = (
                    record.extraction_success_count + record.extraction_failure_count
                )
                success_rate = (
                    record.extraction_success_count / total_attempts
                    if total_attempts > 0
                    else 0
                )

                config_status = "healthy"
                if success_rate < 0.5:
                    config_status = "failed"
                    endpoint_report["failed_configs"] += 1
                elif success_rate < 0.9:
                    config_status = "at_risk"
                    endpoint_report["at_risk_configs"] += 1
                else:
                    endpoint_report["healthy_configs"] += 1

                # Add ontology details
                if record.ontology_type not in endpoint_report["ontologies"]:
                    endpoint_report["ontologies"][record.ontology_type] = []

                # Parse error types
                error_types = []
                if record.extraction_error_types:
                    try:
                        error_types = json.loads(record.extraction_error_types)
                    except json.JSONDecodeError:
                        error_types = []

                # Add property details
                endpoint_report["ontologies"][record.ontology_type].append(
                    {
                        "property_name": record.property_name,
                        "status": config_status,
                        "success_rate": success_rate,
                        "sample_size": record.sample_size,
                        "avg_extraction_time_ms": record.avg_extraction_time_ms,
                        "last_success": record.last_success_time.isoformat()
                        if record.last_success_time
                        else None,
                        "last_failure": record.last_failure_time.isoformat()
                        if record.last_failure_time
                        else None,
                        "common_errors": error_types,
                        "extraction_method": record.extraction_method,
                        "success_count": record.extraction_success_count,
                        "failure_count": record.extraction_failure_count,
                    }
                )

            # Add summary statistics
            report["summary"] = {
                "total_endpoints": len(report["endpoints"]),
                "total_configs": report["total_configs"],
                "healthy_endpoints": sum(
                    1
                    for e in report["endpoints"].values()
                    if e["total_configs"] > 0
                    and e["healthy_configs"] / e["total_configs"] >= 0.8
                ),
                "at_risk_endpoints": sum(
                    1
                    for e in report["endpoints"].values()
                    if e["total_configs"] > 0
                    and 0.5 <= e["healthy_configs"] / e["total_configs"] < 0.8
                ),
                "failed_endpoints": sum(
                    1
                    for e in report["endpoints"].values()
                    if e["total_configs"] > 0
                    and e["healthy_configs"] / e["total_configs"] < 0.5
                ),
                "healthy_configs": sum(
                    e["healthy_configs"] for e in report["endpoints"].values()
                ),
                "at_risk_configs": sum(
                    e["at_risk_configs"] for e in report["endpoints"].values()
                ),
                "failed_configs": sum(
                    e["failed_configs"] for e in report["endpoints"].values()
                ),
            }

            return report

        except SQLAlchemyError as e:
            logger.error(f"Database error generating report: {e}")
            return {"error": f"Database error: {str(e)}"}

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}

        finally:
            if session_owner:
                session.close()

    def get_health_trends(
        self,
        days: int = 30,
        endpoint_id: Optional[int] = None,
        ontology_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get health trends over time.

        Args:
            days: Number of days to include in the trend
            endpoint_id: Optional specific endpoint to report on
            ontology_type: Optional specific ontology type to report on

        Returns:
            Dictionary with trend data
        """
        session = self.db_session or get_session()
        session_owner = self.db_session is None

        try:
            # Get health check logs for the period
            query = """
                SELECT * FROM health_check_logs
                WHERE check_time >= :start_date
                ORDER BY check_time
            """

            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            logs = session.execute(query, {"start_date": start_date}).fetchall()

            # Process logs
            trend_data = {
                "dates": [],
                "success_rates": [],
                "avg_times": [],
                "check_counts": [],
            }

            for log in logs:
                trend_data["dates"].append(log.check_time.isoformat())

                if log.configs_checked > 0:
                    success_rate = log.success_count / log.configs_checked
                    trend_data["success_rates"].append(success_rate)
                else:
                    trend_data["success_rates"].append(None)

                trend_data["avg_times"].append(log.duration_ms)
                trend_data["check_counts"].append(log.configs_checked)

            # Get current health by ontology
            if endpoint_id:
                # Get ontology breakdown for specific endpoint
                query = """
                    SELECT 
                        h.ontology_type,
                        SUM(h.extraction_success_count) as success_count,
                        SUM(h.extraction_failure_count) as failure_count
                    FROM 
                        endpoint_property_health h
                    WHERE 
                        h.endpoint_id = :endpoint_id
                """

                if ontology_type:
                    query += " AND h.ontology_type = :ontology_type"

                query += " GROUP BY h.ontology_type"

                params = {"endpoint_id": endpoint_id}
                if ontology_type:
                    params["ontology_type"] = ontology_type

                ontology_stats = session.execute(query, params).fetchall()

                trend_data["ontology_breakdown"] = [
                    {
                        "ontology_type": stat.ontology_type,
                        "success_count": stat.success_count,
                        "failure_count": stat.failure_count,
                        "success_rate": stat.success_count
                        / (stat.success_count + stat.failure_count)
                        if (stat.success_count + stat.failure_count) > 0
                        else 0,
                    }
                    for stat in ontology_stats
                ]

            return trend_data

        except SQLAlchemyError as e:
            logger.error(f"Database error generating trends: {e}")
            return {"error": f"Database error: {str(e)}"}

        except Exception as e:
            logger.error(f"Error generating trends: {e}")
            return {"error": str(e)}

        finally:
            if session_owner:
                session.close()


class ReportFormatter:
    """Formats health reports in various output formats."""

    @staticmethod
    def to_json(report: Dict[str, Any], pretty: bool = True) -> str:
        """
        Format a report as JSON.

        Args:
            report: The report to format
            pretty: Whether to pretty-print the JSON

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(report, indent=2)
        return json.dumps(report)

    @staticmethod
    def to_text(report: Dict[str, Any]) -> str:
        """
        Format a report as plain text.

        Args:
            report: The report to format

        Returns:
            Text string
        """
        lines = []
        lines.append(f"Endpoint Health Report - Generated at {report['generated_at']}")
        lines.append("-" * 80)

        # Summary
        if "summary" in report:
            summary = report["summary"]
            lines.append("SUMMARY:")
            lines.append(f"  Total endpoints: {summary['total_endpoints']}")
            lines.append(f"  Total configs:  {summary['total_configs']}")
            lines.append(
                f"  Healthy: {summary['healthy_configs']} configs, {summary['healthy_endpoints']} endpoints"
            )
            lines.append(
                f"  At risk: {summary['at_risk_configs']} configs, {summary['at_risk_endpoints']} endpoints"
            )
            lines.append(
                f"  Failed:  {summary['failed_configs']} configs, {summary['failed_endpoints']} endpoints"
            )
            lines.append("")

        # Details by endpoint
        lines.append("ENDPOINT DETAILS:")
        for endpoint_name, endpoint in report.get("endpoints", {}).items():
            lines.append(f"  Endpoint: {endpoint_name} (ID: {endpoint['endpoint_id']})")
            lines.append(
                f"    Type: {endpoint['endpoint_type']}, Subtype: {endpoint['endpoint_subtype'] or 'N/A'}"
            )

            if endpoint["total_configs"] > 0:
                health_rate = endpoint["healthy_configs"] / endpoint["total_configs"]
                status = "Healthy"
                if health_rate < 0.5:
                    status = "FAILING"
                elif health_rate < 0.8:
                    status = "At Risk"

                lines.append(
                    f"    Status: {status} ({endpoint['healthy_configs']} of {endpoint['total_configs']} configs healthy)"
                )
            else:
                lines.append("    Status: No configs")

            lines.append("")

            # Ontology details
            for ontology, properties in endpoint.get("ontologies", {}).items():
                lines.append(f"    Ontology: {ontology}")

                for prop in properties:
                    status = (
                        prop["status"].upper()
                        if prop["status"] == "failed"
                        else prop["status"]
                    )
                    lines.append(
                        f"      {prop['property_name']} - {status} (Success rate: {prop['success_rate']:.2f})"
                    )

                    if prop["common_errors"]:
                        lines.append(
                            f"        Common errors: {', '.join(prop['common_errors'])}"
                        )

                lines.append("")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_html(report: Dict[str, Any]) -> str:
        """
        Format a report as HTML.

        Args:
            report: The report to format

        Returns:
            HTML string
        """
        # Basic HTML report implementation
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <title>Endpoint Health Report</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 20px; }",
            "    h1, h2, h3 { color: #333; }",
            "    .healthy { color: green; }",
            "    .at-risk { color: orange; }",
            "    .failed { color: red; }",
            "    table { border-collapse: collapse; width: 100%; }",
            "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "    th { background-color: #f2f2f2; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>Endpoint Health Report</h1>",
            f"  <p>Generated at: {report['generated_at']}</p>",
        ]

        # Summary
        if "summary" in report:
            summary = report["summary"]
            html.extend(
                [
                    "  <h2>Summary</h2>",
                    "  <table>",
                    "    <tr>",
                    "      <th>Category</th>",
                    "      <th>Endpoints</th>",
                    "      <th>Configurations</th>",
                    "    </tr>",
                    "    <tr class='healthy'>",
                    "      <td>Healthy</td>",
                    f"      <td>{summary['healthy_endpoints']}</td>",
                    f"      <td>{summary['healthy_configs']}</td>",
                    "    </tr>",
                    "    <tr class='at-risk'>",
                    "      <td>At Risk</td>",
                    f"      <td>{summary['at_risk_endpoints']}</td>",
                    f"      <td>{summary['at_risk_configs']}</td>",
                    "    </tr>",
                    "    <tr class='failed'>",
                    "      <td>Failed</td>",
                    f"      <td>{summary['failed_endpoints']}</td>",
                    f"      <td>{summary['failed_configs']}</td>",
                    "    </tr>",
                    "    <tr>",
                    "      <td><strong>Total</strong></td>",
                    f"      <td>{summary['total_endpoints']}</td>",
                    f"      <td>{summary['total_configs']}</td>",
                    "    </tr>",
                    "  </table>",
                ]
            )

        # Endpoint details
        html.append("  <h2>Endpoint Details</h2>")

        for endpoint_name, endpoint in report.get("endpoints", {}).items():
            # Determine endpoint status class
            status_class = "healthy"
            if endpoint["total_configs"] > 0:
                health_rate = endpoint["healthy_configs"] / endpoint["total_configs"]
                if health_rate < 0.5:
                    status_class = "failed"
                elif health_rate < 0.8:
                    status_class = "at-risk"

            html.extend(
                [
                    f"  <h3 class='{status_class}'>{endpoint_name} (ID: {endpoint['endpoint_id']})</h3>",
                    f"  <p>Type: {endpoint['endpoint_type']}, Subtype: {endpoint['endpoint_subtype'] or 'N/A'}</p>",
                    "  <table>",
                    "    <tr>",
                    "      <th>Ontology</th>",
                    "      <th>Property</th>",
                    "      <th>Status</th>",
                    "      <th>Success Rate</th>",
                    "      <th>Sample Size</th>",
                    "      <th>Common Errors</th>",
                    "    </tr>",
                ]
            )

            # Add rows for each property
            for ontology, properties in endpoint.get("ontologies", {}).items():
                for prop in properties:
                    prop_class = prop["status"]

                    html.append("    <tr class='" + prop_class + "'>")
                    html.append(f"      <td>{ontology}</td>")
                    html.append(f"      <td>{prop['property_name']}</td>")
                    html.append(f"      <td>{prop['status']}</td>")
                    html.append(f"      <td>{prop['success_rate']:.2f}</td>")
                    html.append(f"      <td>{prop['sample_size']}</td>")
                    html.append(
                        f"      <td>{', '.join(prop['common_errors']) if prop['common_errors'] else 'None'}</td>"
                    )
                    html.append("    </tr>")

            html.append("  </table>")

        html.extend(["</body>", "</html>"])

        return "\n".join(html)

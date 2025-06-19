"""
Command-line interface for the Endpoint Health Monitoring System.

This module provides commands for checking, analyzing, and reporting on
the health of endpoint property extraction configurations.
"""

import json
import click
import asyncio
import logging

from biomapper.db.session import DatabaseManager
from biomapper.mapping.health.monitor import EndpointHealthMonitor
from biomapper.mapping.health.reporter import HealthReportGenerator, ReportFormatter
from biomapper.mapping.health.analyzer import ConfigImprover

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group("health")
def health_cli():
    """Commands for managing endpoint property health."""
    pass


@health_cli.command("check")
@click.option("--endpoint", help="Optional endpoint ID to check", type=int)
@click.option("--ontology", help="Optional ontology type to check", multiple=True)
def health_check(endpoint, ontology):
    """Run a health check on endpoint configurations."""
    click.echo("Running health check...")

    monitor = EndpointHealthMonitor()
    result = asyncio.run(
        monitor.run_health_check(
            endpoint_id=endpoint, ontology_types=ontology if ontology else None
        )
    )

    if "error" in result:
        click.echo(f"Error running health check: {result['error']}")
        return

    # Print summary
    click.echo(f"\nHealth Check Results (ID: {result['log_id']}):")
    click.echo(f"  Endpoints checked: {result['endpoints_checked']}")
    click.echo(f"  Configs checked: {result['configs_checked']}")
    click.echo(
        f"  Success: {result['success_count']} ({result['success_count']/result['configs_checked']*100:.1f}%)"
    )
    click.echo(
        f"  Failures: {result['failure_count']} ({result['failure_count']/result['configs_checked']*100:.1f}%)"
    )
    click.echo(f"  Duration: {result['duration_ms']} ms")

    # Print details for each endpoint
    click.echo("\nDetails by endpoint:")
    for endpoint in result.get("endpoints", []):
        status_symbol = "✓" if endpoint.get("status") == "healthy" else "!"
        if endpoint.get("status") == "failing":
            status_symbol = "✗"

        click.echo(
            f"  {status_symbol} {endpoint['name']} (ID: {endpoint['endpoint_id']})"
        )

        if endpoint.get("configs_checked", 0) > 0:
            success_rate = (
                endpoint.get("success_count", 0) / endpoint["configs_checked"]
            )
            click.echo(
                f"    Status: {endpoint.get('status', 'unknown')} ({success_rate*100:.1f}% success)"
            )
            click.echo(
                f"    Configs: {endpoint['configs_checked']} checked, {endpoint['success_count']} success, {endpoint['failure_count']} failure"
            )

            # List failing configs
            failed = [
                c for c in endpoint.get("configs", []) if not c.get("success", False)
            ]
            if failed:
                click.echo("\n    Failed configurations:")
                for config in failed:
                    click.echo(
                        f"      {config['ontology_type']}:{config['property_name']}"
                    )
                    if config.get("error_message"):
                        click.echo(f"        Error: {config['error_message']}")

        else:
            click.echo("    No configurations to check")

        click.echo("")


@health_cli.command("report")
@click.option("--endpoint", help="Optional endpoint ID to report on", type=int)
@click.option(
    "--format",
    help="Output format",
    type=click.Choice(["json", "text", "html"]),
    default="text",
)
@click.option("--output", help="Optional output file", type=click.Path())
def health_report(endpoint, format, output):
    """Generate a health report for endpoint configurations."""
    click.echo("Generating health report...")

    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        # Create report generator
        generator = HealthReportGenerator(session)

        # Generate report
        report = generator.generate_endpoint_health_report(endpoint_id=endpoint)

        if "error" in report:
            click.echo(f"Error generating report: {report['error']}")
            return

        # Format report
        if format == "json":
            formatted = ReportFormatter.to_json(report)
        elif format == "html":
            formatted = ReportFormatter.to_html(report)
        else:  # text is default
            formatted = ReportFormatter.to_text(report)

        # Output report
        if output:
            with open(output, "w") as f:
                f.write(formatted)
            click.echo(f"Report saved to {output}")
        else:
            click.echo(formatted)

    except Exception as e:
        click.echo(f"Error generating report: {e}")
    finally:
        session.close()


@health_cli.command("analyze")
@click.option("--endpoint", help="Optional endpoint ID to analyze", type=int)
@click.option("--json-output", is_flag=True, help="Output suggestions as JSON")
def health_analyze(endpoint, json_output):
    """Analyze and suggest improvements for endpoints."""
    click.echo("Analyzing configurations...")

    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        improver = ConfigImprover(session)

        # Get suggestions
        suggestions = improver.suggest_improvements(endpoint_id=endpoint)

        if not suggestions:
            click.echo("No improvement suggestions found.")
            return

        # Check for errors
        if len(suggestions) == 1 and "error" in suggestions[0]:
            click.echo(f"Error analyzing configurations: {suggestions[0]['error']}")
            return

        # Output suggestions
        if json_output:
            click.echo(json.dumps(suggestions, indent=2))
        else:
            click.echo(f"\nFound {len(suggestions)} possible improvements:")

            for i, suggestion in enumerate(suggestions, 1):
                click.echo(
                    f"\n{i}. {suggestion['ontology_type']}:{suggestion['property_name']} "
                    + f"(Endpoint ID: {suggestion['endpoint_id']})"
                )
                click.echo(f"   Method: {suggestion['extraction_method']}")
                click.echo(f"   Issues: {suggestion['reason']}")
                click.echo(f"   Confidence: {suggestion['confidence']:.2f}")

                click.echo("\n   Current pattern:")
                click.echo(f"   {json.dumps(suggestion['current_pattern'], indent=2)}")

                click.echo("\n   Suggested pattern:")
                click.echo(
                    f"   {json.dumps(suggestion['suggested_pattern'], indent=2)}"
                )

                if "comment" in suggestion.get("suggested_pattern", {}):
                    click.echo(
                        f"\n   Note: {suggestion['suggested_pattern']['comment']}"
                    )

    except Exception as e:
        click.echo(f"Error during analysis: {e}")
    finally:
        session.close()


@health_cli.command("test")
@click.option("--endpoint", help="Endpoint ID", type=int, required=True)
@click.option("--ontology", help="Ontology type", required=True)
@click.option("--property", help="Property name", required=True)
def health_test(endpoint, ontology, property):
    """Test a specific property extraction configuration."""
    click.echo(f"Testing configuration: {endpoint}/{ontology}/{property}...")

    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        # Create session and tester
        monitor = EndpointHealthMonitor(session)

        try:
            # Get property config details
            config = session.execute(
                """SELECT * FROM endpoint_property_configs 
                   WHERE endpoint_id = :endpoint_id 
                   AND ontology_type = :ontology_type 
                   AND property_name = :property_name""",
                {
                    "endpoint_id": endpoint,
                    "ontology_type": ontology,
                    "property_name": property,
                },
            ).fetchone()

            if not config:
                click.echo(f"Configuration not found: {endpoint}/{ontology}/{property}")
                return

            # Run test
            result = asyncio.run(
                monitor.run_health_check(
                    endpoint_id=endpoint, ontology_types=[ontology]
                )
            )

            # Find specific test result
            test_result = None
            for ep in result.get("endpoints", []):
                if ep["endpoint_id"] == endpoint:
                    for config in ep.get("configs", []):
                        if (
                            config["ontology_type"] == ontology
                            and config["property_name"] == property
                        ):
                            test_result = config
                            break

            if not test_result:
                click.echo("Test completed but no results found.")
                return

            # Show results
            click.echo("\nTest Results:")
            status = "Passed" if test_result["success"] else "Failed"
            click.echo(f"  Status: {status}")
            click.echo(f"  Execution time: {test_result['execution_time_ms']} ms")

            if test_result["success"]:
                click.echo(f"  Extracted {test_result['extracted_count']} values")
                if test_result.get("sample_values"):
                    click.echo(
                        f"  Sample values: {', '.join(str(v) for v in test_result['sample_values'])}"
                    )
            else:
                click.echo(
                    f"  Error: {test_result.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            click.echo(f"Error testing configuration: {str(e)}")

    except Exception as e:
        click.echo(f"Error testing configuration: {str(e)}")
    finally:
        session.close()


# Add this function to register the command group
def register_commands(cli):
    cli.add_command(health_cli)


if __name__ == "__main__":
    health_cli()

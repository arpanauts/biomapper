"""Command-line interface for Biomapper client."""

import json
import sys
from pathlib import Path

import click
import yaml

from .client_v2 import BiomapperClient
from .exceptions import BiomapperClientError
from .models import ExecutionContext


@click.group()
@click.option(
    "--api-url",
    envvar="BIOMAPPER_API_URL",
    default="http://localhost:8000",
    help="Biomapper API URL",
)
@click.option(
    "--api-key", envvar="BIOMAPPER_API_KEY", help="API key for authentication"
)
@click.option("--timeout", default=300, help="Request timeout in seconds")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, api_url, api_key, timeout, debug):
    """Biomapper command-line interface.

    Execute biological data harmonization strategies via the Biomapper API.
    """
    ctx.ensure_object(dict)
    ctx.obj["client"] = BiomapperClient(
        base_url=api_url, api_key=api_key, timeout=timeout
    )
    ctx.obj["debug"] = debug


@cli.command()
@click.argument("strategy")
@click.option("--parameters", "-p", help="Parameters as JSON string or file path")
@click.option("--context", "-c", help="Context as JSON string or file path")
@click.option("--output-dir", "-o", type=Path, help="Output directory for results")
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--no-wait", is_flag=True, help="Don't wait for completion")
@click.option("--checkpoint", is_flag=True, help="Enable checkpointing")
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "table"]),
    default="json",
    help="Output format",
)
@click.pass_context
def run(
    ctx, strategy, parameters, context, output_dir, watch, no_wait, checkpoint, format
):
    """Run a strategy.

    STRATEGY can be:
    - A strategy name (e.g., "metabolomics_harmonization")
    - Path to a YAML strategy file
    - Path to a JSON strategy file

    Examples:

        # Run a named strategy
        biomapper run metabolomics_harmonization

        # Run with parameters
        biomapper run my_strategy -p '{"threshold": 0.9}'

        # Run from YAML file with output directory
        biomapper run strategy.yaml -o ./results

        # Watch progress
        biomapper run my_strategy --watch

        # Run without waiting (returns job ID)
        biomapper run my_strategy --no-wait
    """
    client = ctx.obj["client"]
    debug = ctx.obj["debug"]

    # Parse parameters
    params = {}
    if parameters:
        params = _parse_json_or_file(parameters, "parameters")

    # Parse context
    exec_context = None
    if context:
        context_data = _parse_json_or_file(context, "context")
        exec_context = ExecutionContext(**context_data)
    else:
        exec_context = ExecutionContext()

    # Set output directory
    if output_dir:
        exec_context.set_output_dir(output_dir)

    # Enable checkpointing
    if checkpoint:
        exec_context.enable_checkpoints()

    # Enable debug mode
    if debug:
        exec_context.enable_debug()

    try:
        # Run strategy
        result = client.run(
            strategy=strategy,
            parameters=params,
            context=exec_context,
            wait=not no_wait,
            watch=watch,
        )

        # Format and display output
        if no_wait:
            # Job was returned
            click.echo(f"Job started: {result.id}")
            click.echo(f"Status: {result.status}")
        else:
            # Result was returned
            if result.success:
                click.secho("✅ Execution successful!", fg="green")
            else:
                click.secho(f"❌ Execution failed: {result.error}", fg="red")
                sys.exit(1)

            # Display results based on format
            if format == "json":
                click.echo(json.dumps(result.dict(), indent=2))
            elif format == "yaml":
                click.echo(yaml.dump(result.dict(), default_flow_style=False))
            elif format == "table":
                _display_result_table(result)

    except BiomapperClientError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--status", help="Filter by status")
@click.option("--limit", default=10, help="Maximum number of strategies to list")
@click.pass_context
def list(ctx, status, limit):
    """List available strategies.

    Examples:

        # List all strategies
        biomapper list

        # List with status filter
        biomapper list --status active
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        strategies = asyncio.run(client.list_strategies())
        click.echo("Available strategies:")
        for name in strategies[:limit]:
            click.echo(f"  • {name}")

        if len(strategies) > limit:
            click.echo(f"  ... and {len(strategies) - limit} more")

    except NotImplementedError:
        click.secho("Strategy listing not yet implemented in API", fg="yellow")
        click.echo("\nYou can find available strategies in the configs/ directory")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("job_id")
@click.pass_context
def status(ctx, job_id):
    """Check job status.

    Examples:

        # Check job status
        biomapper status job-123-456
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        job_status = asyncio.run(client.get_job_status(job_id))

        click.echo(f"Job ID: {job_id}")
        click.echo(f"Status: {job_status.status}")
        click.echo(f"Progress: {job_status.progress:.1f}%")

        if job_status.current_action:
            click.echo(f"Current Action: {job_status.current_action}")

        if job_status.message:
            click.echo(f"Message: {job_status.message}")

        click.echo(f"Updated: {job_status.updated_at}")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("job_id")
@click.option("--tail", "-n", default=100, help="Number of log lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.pass_context
def logs(ctx, job_id, tail, follow):
    """Show job logs.

    Examples:

        # Show last 100 log lines
        biomapper logs job-123-456

        # Show last 50 lines
        biomapper logs job-123-456 -n 50

        # Follow logs (not yet implemented)
        biomapper logs job-123-456 -f
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        log_entries = asyncio.run(client.get_job_logs(job_id, tail=tail))

        for entry in log_entries:
            level_color = {
                "DEBUG": "white",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }.get(entry.level, "white")

            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            click.echo(
                click.style(f"[{timestamp}] ", fg="white", dim=True)
                + click.style(f"{entry.level:8} ", fg=level_color)
                + entry.message
            )

        if follow:
            click.secho("Note: Log following not yet implemented", fg="yellow")

    except NotImplementedError:
        click.secho("Job logs not yet implemented in API", fg="yellow")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("job_id")
@click.option("--output", "-o", type=Path, help="Output file path")
@click.option(
    "--format",
    type=click.Choice(["json", "csv", "tsv"]),
    default="json",
    help="Output format",
)
@click.pass_context
def results(ctx, job_id, output, format):
    """Get job results.

    Examples:

        # Display results
        biomapper results job-123-456

        # Save to file
        biomapper results job-123-456 -o results.json

        # Export as CSV
        biomapper results job-123-456 --format csv -o results.csv
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        results = asyncio.run(client.get_job_results(job_id))

        # Format results
        if format == "json":
            output_data = json.dumps(results, indent=2)
        elif format in ["csv", "tsv"]:
            # Convert to CSV/TSV if results contain tabular data
            import csv
            import io

            if isinstance(results, dict) and "data" in results:
                data = results["data"]
            elif isinstance(results, list):
                data = results
            else:
                click.secho("Results are not in tabular format", fg="yellow")
                output_data = json.dumps(results, indent=2)
                format = "json"

            if format in ["csv", "tsv"]:
                delimiter = "\t" if format == "tsv" else ","
                output_buffer = io.StringIO()
                if data and isinstance(data, list):
                    writer = csv.DictWriter(
                        output_buffer, fieldnames=data[0].keys(), delimiter=delimiter
                    )
                    writer.writeheader()
                    writer.writerows(data)
                    output_data = output_buffer.getvalue()
                else:
                    output_data = ""

        # Output results
        if output:
            output.write_text(output_data)
            click.echo(f"Results saved to {output}")
        else:
            click.echo(output_data)

    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=Path)
@click.option("--session-id", help="Session ID for resuming upload")
@click.pass_context
def upload(ctx, file_path, session_id):
    """Upload a file to the API.

    Examples:

        # Upload a new file
        biomapper upload data.csv

        # Resume upload with session
        biomapper upload data.csv --session-id sess-123
    """
    client = ctx.obj["client"]

    if not file_path.exists():
        click.secho(f"File not found: {file_path}", fg="red")
        sys.exit(1)

    try:
        import asyncio

        response = asyncio.run(client.upload_file(file_path, session_id))

        click.secho("✅ File uploaded successfully!", fg="green")
        click.echo(f"Session ID: {response.session_id}")
        click.echo(f"Filename: {response.filename}")
        click.echo(f"Size: {response.file_size:,} bytes")

        if response.columns:
            click.echo(f"Columns: {', '.join(response.columns)}")

        if response.row_count:
            click.echo(f"Rows: {response.row_count:,}")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("strategy")
@click.option("--output", "-o", type=Path, help="Output file for validation report")
@click.pass_context
def validate(ctx, strategy, output):
    """Validate a strategy without executing.

    Examples:

        # Validate a strategy file
        biomapper validate strategy.yaml

        # Save validation report
        biomapper validate strategy.yaml -o report.json
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        result = asyncio.run(client.validate_strategy(strategy))

        if result.is_valid:
            click.secho("✅ Strategy is valid!", fg="green")
        else:
            click.secho("❌ Strategy validation failed!", fg="red")

        # Display errors
        if result.errors:
            click.echo("\nErrors:")
            for error in result.errors:
                click.echo(f"  • {error}")

        # Display warnings
        if result.warnings:
            click.echo("\nWarnings:")
            for warning in result.warnings:
                click.echo(f"  • {warning}")

        # Display suggestions
        if result.suggestions:
            click.echo("\nSuggestions:")
            for suggestion in result.suggestions:
                click.echo(f"  • {suggestion}")

        # Save report if requested
        if output:
            report = result.dict()
            output.write_text(json.dumps(report, indent=2))
            click.echo(f"\nValidation report saved to {output}")

    except NotImplementedError:
        click.secho("Strategy validation not yet implemented in API", fg="yellow")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health status.

    Examples:

        # Check API health
        biomapper health
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        health = asyncio.run(client.health_check())

        click.secho("✅ API is healthy!", fg="green")

        if isinstance(health, dict):
            for key, value in health.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        click.secho(f"❌ API health check failed: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.pass_context
def endpoints(ctx, format):
    """List available API endpoints.

    Examples:

        # List endpoints as table
        biomapper endpoints

        # List as JSON
        biomapper endpoints --format json
    """
    client = ctx.obj["client"]

    try:
        import asyncio

        endpoints = asyncio.run(client.list_endpoints())

        if format == "json":
            data = [e.dict() for e in endpoints]
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo("Available API endpoints:\n")
            for endpoint in endpoints:
                click.echo(f"  {endpoint.method:6} {endpoint.path}")
                if endpoint.description:
                    click.echo(f"         {endpoint.description}")
                click.echo()

    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


# Helper functions


def _parse_json_or_file(value: str, name: str) -> dict:
    """Parse JSON string or load from file.

    Args:
        value: JSON string or file path
        name: Name for error messages

    Returns:
        Parsed dictionary

    Raises:
        click.ClickException: If parsing fails
    """
    # Try as JSON string first
    if value.startswith("{") or value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"Invalid JSON for {name}: {e}")

    # Try as file path
    path = Path(value)
    if not path.exists():
        raise click.ClickException(f"File not found for {name}: {value}")

    try:
        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        raise click.ClickException(f"Error loading {name} from {value}: {e}")


def _display_result_table(result):
    """Display result as a formatted table.

    Args:
        result: StrategyResult object
    """
    click.echo("\n" + "=" * 60)
    click.echo(f"Job ID: {result.job_id}")
    click.echo(f"Success: {'✅ Yes' if result.success else '❌ No'}")
    click.echo(f"Execution Time: {result.execution_time_seconds:.2f} seconds")

    if result.statistics:
        click.echo("\nStatistics:")
        for key, value in result.statistics.items():
            click.echo(f"  {key}: {value}")

    if result.output_files:
        click.echo("\nOutput Files:")
        for file in result.output_files:
            click.echo(f"  • {file}")

    if result.warnings:
        click.echo("\nWarnings:")
        for warning in result.warnings:
            click.echo(f"  ⚠️  {warning}")

    if result.error:
        click.echo(f"\nError: {result.error}")

    click.echo("=" * 60 + "\n")


if __name__ == "__main__":
    cli()

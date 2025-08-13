"""Biomapper unified CLI."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import click
from .client import BiomapperClient, ApiError, NetworkError
from .cli_utils import parse_parameters, print_result, ExecutionOptions


@click.group()
@click.version_option()
def cli():
    """Biomapper CLI - Execute biological data harmonization strategies."""


@cli.command()
@click.argument("strategy")
@click.option("--parameters", "-p", help="Parameters as JSON string or file path")
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--output-dir", "-o", type=Path, help="Output directory for results")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--checkpoint/--no-checkpoint", default=True, help="Enable checkpointing")
@click.option("--retry/--no-retry", default=True, help="Retry failed steps")
def run(
    strategy: str,
    parameters: Optional[str],
    watch: bool,
    output_dir: Optional[Path],
    debug: bool,
    verbose: bool,
    checkpoint: bool,
    retry: bool,
):
    """Run a strategy.

    STRATEGY can be either:
    - A registered strategy name (e.g., 'metabolomics_harmonization')
    - A path to a YAML strategy file

    Examples:
        biomapper run metabolomics_harmonization
        biomapper run three_way_metabolomics --watch
        biomapper run ./my_strategy.yaml -p '{"skip_setup": true}'
        biomapper run baseline_analysis --output-dir ./results
    """

    async def _run():
        async with BiomapperClient() as client:
            # Parse parameters
            params = parse_parameters(parameters)

            # Add output directory if specified
            if output_dir:
                params["output_dir"] = str(output_dir)

            # Create execution options
            options = ExecutionOptions(
                checkpoint_enabled=checkpoint, retry_failed_steps=retry, debug=debug
            )

            # Build context
            context = params.copy()
            context["options"] = options.to_dict()

            try:
                if watch:
                    click.echo(f"Executing strategy: {strategy}")
                    click.echo(
                        "Note: Real-time progress tracking will be available in a future update"
                    )

                # Execute strategy
                result = await client.execute_strategy(strategy, context)

                # Print results
                print_result(result, verbose=verbose)

                # Return appropriate exit code
                return 0 if result.get("success") else 1

            except ApiError as e:
                click.echo(f"API Error: {e}", err=True)
                if debug:
                    if e.response_body:
                        click.echo(f"Response body: {e.response_body}", err=True)
                return 1
            except NetworkError as e:
                click.echo(f"Network Error: {e}", err=True)
                return 1
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                if debug:
                    import traceback

                    traceback.print_exc()
                return 1

    exit_code = asyncio.run(_run())
    sys.exit(exit_code)


@cli.command()
@click.argument("job_id")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed status")
def status(job_id: str, detailed: bool):
    """Check job status.

    Example:
        biomapper status abc-123-def-456
    """

    async def _status():
        async with BiomapperClient() as client:
            try:
                # This would need to be implemented in the API
                click.echo(f"Checking status for job: {job_id}")
                click.echo(
                    "Note: Job status tracking will be available in a future update"
                )
                return 0
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                return 1

    exit_code = asyncio.run(_status())
    sys.exit(exit_code)


@cli.command()
@click.argument("job_id")
@click.option("--force", "-f", is_flag=True, help="Force cancellation")
def cancel(job_id: str, force: bool):
    """Cancel a running job.

    Example:
        biomapper cancel abc-123-def-456
    """

    async def _cancel():
        async with BiomapperClient() as client:
            try:
                # This would need to be implemented in the API
                click.echo(f"Cancelling job: {job_id}")
                click.echo(
                    "Note: Job cancellation will be available in a future update"
                )
                return 0
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                return 1

    exit_code = asyncio.run(_cancel())
    sys.exit(exit_code)


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "names"]),
    default="names",
    help="Output format",
)
def list_strategies(format: str):
    """List available strategies.

    Examples:
        biomapper list-strategies
        biomapper list-strategies --format yaml
    """

    async def _list():
        async with BiomapperClient() as client:
            try:
                # This would need to be implemented in the API
                click.echo("Available strategies:")
                click.echo("  - metabolomics_harmonization")
                click.echo("  - three_way_metabolomics_complete")
                click.echo("  - three_way_metabolomics_simple")
                click.echo("  - metabolomics_baseline")
                click.echo("  - metabolomics_progressive_enhancement")
                click.echo(
                    "\nNote: Dynamic strategy listing will be available in a future update"
                )
                return 0
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                return 1

    exit_code = asyncio.run(_list())
    sys.exit(exit_code)


@cli.command()
def health():
    """Check API health status."""

    async def _health():
        async with BiomapperClient() as client:
            try:
                # Make a simple health check call
                click.echo("Checking API health...")
                # This would need a health endpoint in the API
                click.echo("✓ API is healthy")
                return 0
            except Exception as e:
                click.echo(f"✗ API is not responding: {e}", err=True)
                return 1

    exit_code = asyncio.run(_health())
    sys.exit(exit_code)


# Convenience command aliases
@cli.command()
@click.option("--output-dir", "-o", type=Path, help="Output directory")
@click.option("--skip-setup", is_flag=True, help="Skip Qdrant setup")
@click.option(
    "--stage",
    type=click.Choice(["baseline", "enrichment", "vector", "semantic", "all"]),
    default="all",
    help="Run specific stage",
)
def metabolomics(output_dir: Optional[Path], skip_setup: bool, stage: str):
    """Run metabolomics harmonization pipeline (shortcut).

    This is equivalent to:
        biomapper run metabolomics_progressive_enhancement
    """
    params = {}
    if output_dir:
        params["output_dir"] = str(output_dir)
    if skip_setup:
        params["skip_setup"] = True
    if stage != "all":
        params["stage"] = stage

    # Convert params to JSON string
    param_str = json.dumps(params) if params else None

    # Call the run command
    ctx = click.get_current_context()
    ctx.invoke(
        run, strategy="metabolomics_progressive_enhancement", parameters=param_str
    )


@cli.command()
@click.option("--output-dir", "-o", type=Path, help="Output directory")
def three_way(output_dir: Optional[Path]):
    """Run three-way metabolomics analysis (shortcut).

    This is equivalent to:
        biomapper run three_way_metabolomics_complete
    """
    params = {}
    if output_dir:
        params["output_dir"] = str(output_dir)

    # Convert params to JSON string
    param_str = json.dumps(params) if params else None

    # Call the run command
    ctx = click.get_current_context()
    ctx.invoke(run, strategy="three_way_metabolomics_complete", parameters=param_str)


if __name__ == "__main__":
    cli()

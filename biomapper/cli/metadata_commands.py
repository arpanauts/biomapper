"""
Command-line interface for the Resource Metadata System.

This module provides commands for initializing, configuring, and managing
the Resource Metadata System through a command-line interface.
"""

import os
import json
import yaml
import click
import logging

from biomapper.mapping.metadata.initialize import (
    initialize_metadata_system,
    verify_metadata_schema,
    get_metadata_db_path,
)
from biomapper.mapping.metadata.manager import ResourceMetadataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group("metadata")
def metadata_cli():
    """Commands for managing the Resource Metadata System."""
    pass


@metadata_cli.command("init")
@click.option("--db-path", help="Path to SQLite database", default=None)
@click.option("--force", is_flag=True, help="Overwrite existing database if it exists")
def init_metadata(db_path, force):
    """Initialize the metadata system database."""
    db_path = db_path or get_metadata_db_path()

    # Check if db file already exists
    if os.path.exists(db_path) and not force:
        click.echo(f"Database already exists at {db_path}. Use --force to overwrite.")
        return

    click.echo(f"Initializing metadata system at {db_path}...")
    success = initialize_metadata_system(db_path)

    if success:
        click.echo("Metadata system initialized successfully.")
    else:
        click.echo("Failed to initialize metadata system.")


@metadata_cli.command("verify")
@click.option("--db-path", help="Path to SQLite database", default=None)
def verify_metadata(db_path):
    """Verify the metadata system database schema."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}.")
        return

    click.echo(f"Verifying metadata system at {db_path}...")
    missing = verify_metadata_schema(db_path)

    if not missing:
        click.echo("Metadata schema is valid.")
    else:
        click.echo("Metadata schema is invalid:")
        for item in missing:
            click.echo(f"  - {item}")


@metadata_cli.command("register")
@click.option("--db-path", help="Path to SQLite database", default=None)
@click.option(
    "--config-file", required=True, help="Path to resource configuration file"
)
def register_resources(db_path, config_file):
    """Register resources from a configuration file."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}. Run 'metadata init' first.")
        return

    if not os.path.exists(config_file):
        click.echo(f"Configuration file does not exist at {config_file}.")
        return

    # Load configuration
    with open(config_file, "r") as f:
        if config_file.endswith(".yaml") or config_file.endswith(".yml"):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    # Initialize metadata manager
    manager = ResourceMetadataManager(db_path)
    manager.connect()

    # Register resources
    for name, resource_config in config.get("resources", {}).items():
        click.echo(f"Registering resource: {name}")

        # Register the resource
        resource_id = manager.register_resource(
            name=name,
            resource_type=resource_config.get("type"),
            connection_info=resource_config.get("connection_info", {}),
            priority=resource_config.get("priority", 0),
        )

        if resource_id is None:
            click.echo(f"  Failed to register resource {name}")
            continue

        # Register ontology coverage
        for ontology, details in resource_config.get("ontologies", {}).items():
            support_level = details.get("support_level", "unknown")
            entity_count = details.get("entity_count")

            click.echo(f"  Registering ontology: {ontology} ({support_level})")
            success = manager.register_ontology_coverage(
                resource_name=name,
                ontology_type=ontology,
                support_level=support_level,
                entity_count=entity_count,
            )

            if not success:
                click.echo(f"  Failed to register ontology {ontology} for {name}")

    manager.close()
    click.echo(f"Registered {len(config.get('resources', {}))} resources")


@metadata_cli.command("list")
@click.option("--db-path", help="Path to SQLite database", default=None)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def list_resources(db_path, format):
    """List registered resources."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}. Run 'metadata init' first.")
        return

    # Initialize metadata manager
    manager = ResourceMetadataManager(db_path)
    manager.connect()

    # Get resources by priority
    resources = manager.get_resources_by_priority()

    if not resources:
        click.echo("No resources registered.")
        return

    if format == "json":
        click.echo(json.dumps(resources, indent=2))
    else:
        # Table format
        click.echo("\nRegistered Resources:\n")
        click.echo(
            f"{'Name':<20} {'Type':<10} {'Priority':<10} {'Success Rate':<15} {'Avg Time (ms)':<15}"
        )
        click.echo("-" * 70)

        for resource in resources:
            success_rate = resource.get("success_rate")
            success_str = f"{success_rate:.2f}" if success_rate is not None else "N/A"

            avg_time = resource.get("avg_response_time_ms")
            time_str = f"{avg_time:.2f}" if avg_time is not None else "N/A"

            click.echo(
                f"{resource['name']:<20} {resource['type']:<10} {resource['priority']:<10} "
                f"{success_str:<15} {time_str:<15}"
            )

        click.echo("\n")

    # Get ontology coverage for each resource
    if format == "table":
        click.echo("Ontology Coverage:\n")
        click.echo(f"{'Resource':<20} {'Ontology Type':<15} {'Support Level':<15}")
        click.echo("-" * 50)

        for resource in resources:
            coverage = manager.get_ontology_coverage(resource["name"])

            if not coverage:
                click.echo(f"{resource['name']:<20} {'No coverage information':<30}")
                continue

            for ontology, support in coverage.items():
                click.echo(f"{resource['name']:<20} {ontology:<15} {support:<15}")

        click.echo("\n")

    manager.close()


@metadata_cli.command("stats")
@click.option("--db-path", help="Path to SQLite database", default=None)
@click.option("--resource", help="Resource name to filter by", default=None)
def show_statistics(db_path, resource):
    """Show performance statistics for resources."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}. Run 'metadata init' first.")
        return

    # Initialize metadata manager
    manager = ResourceMetadataManager(db_path)
    manager.connect()

    # Get performance summary
    metrics = manager.get_performance_summary(resource)

    if not metrics:
        click.echo("No performance metrics available.")
        return

    click.echo("\nPerformance Metrics:\n")
    click.echo(
        f"{'Resource':<20} {'Operation':<10} {'Source':<10} {'Target':<10} "
        f"{'Avg Time (ms)':<15} {'Success Rate':<15} {'Samples':<10}"
    )
    click.echo("-" * 90)

    for metric in metrics:
        source = metric.get("source_type") or "N/A"
        target = metric.get("target_type") or "N/A"

        click.echo(
            f"{metric['resource_name']:<20} {metric['operation_type']:<10} "
            f"{source:<10} {target:<10} {metric['avg_response_time_ms']:<15.2f} "
            f"{metric['success_rate']:<15.2f} {metric['sample_count']:<10}"
        )

    click.echo("\n")
    manager.close()


@metadata_cli.command("map")
@click.option("--db-path", help="Path to SQLite database", default=None)
@click.option("--source-id", required=True, help="Source identifier")
@click.option("--source-type", required=True, help="Source ontology type")
@click.option("--target-type", required=True, help="Target ontology type")
@click.option("--resource", help="Preferred resource name", default=None)
def map_entity(db_path, source_id, source_type, target_type, resource):
    """Map an entity using the dispatcher."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}. Run 'metadata init' first.")
        return

    # Initialize metadata manager
    manager = ResourceMetadataManager(db_path)

    # This is just a demo, in practice you would load the proper adapters
    click.echo("NOTE: This command requires properly configured resource adapters.")
    click.echo("      It's meant as an example of how the dispatcher would be used.")

    # Show the mapping request
    click.echo("\nMapping request:")
    click.echo(f"  Source ID:    {source_id}")
    click.echo(f"  Source Type:  {source_type}")
    click.echo(f"  Target Type:  {target_type}")
    click.echo(f"  Resource:     {resource or 'Auto-select'}")

    # Get resources that would be used
    resources = manager.get_resources_by_priority(source_type, target_type)

    if not resources:
        click.echo("\nNo suitable resources found for this mapping.")
    else:
        click.echo("\nResources that would be used (in order):")
        for res in resources:
            click.echo(f"  - {res['name']} (Priority: {res['priority']})")

    manager.close()


@metadata_cli.command("optimize")
@click.option("--db-path", help="Path to SQLite database", default=None)
def optimize_priorities(db_path):
    """Optimize resource priorities based on performance metrics."""
    db_path = db_path or get_metadata_db_path()

    if not os.path.exists(db_path):
        click.echo(f"Database does not exist at {db_path}. Run 'metadata init' first.")
        return

    # Initialize metadata manager
    manager = ResourceMetadataManager(db_path)
    manager.connect()

    # Get resources
    resources = manager.get_resources_by_priority()

    if not resources:
        click.echo("No resources registered.")
        return

    click.echo("\nCurrent Priorities:")
    for resource in resources:
        click.echo(f"  {resource['name']}: {resource['priority']}")

    # Get performance metrics
    metrics = manager.get_performance_summary()

    if not metrics:
        click.echo("\nNo performance metrics available for optimization.")
        return

    click.echo(
        "\nThis would analyze performance metrics and suggest optimized priorities."
    )
    click.echo("Optimization not implemented in this demo version.")

    manager.close()


# Add this function to register the command group
def register_commands(cli):
    cli.add_command(metadata_cli)


if __name__ == "__main__":
    metadata_cli()

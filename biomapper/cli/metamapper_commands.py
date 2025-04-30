"""
Command-line interface for the MetaMapping System.

This module provides commands for discovering, testing, and executing
mapping paths between endpoints.
"""

import os
import json
import click
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional

from biomapper.db.session import get_session
from biomapper.mapping.metadata.pathfinder import RelationshipPathFinder
from biomapper.mapping.metadata.mapper import RelationshipMappingExecutor
from biomapper.mapping.health import PropertyHealthTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group("metamapper")
def metamapper_cli():
    """Commands for managing endpoint mapping relationships."""
    pass


@metamapper_cli.command("create-relationship")
@click.option("--name", required=True, help="Relationship name")
@click.option("--description", help="Relationship description")
@click.option("--source", required=True, help="Source endpoint ID", type=int)
@click.option("--target", required=True, help="Target endpoint ID", type=int)
def create_relationship(name, description, source, target):
    """Create a relationship between endpoints."""
    db_session = get_session()

    try:
        # Insert relationship
        result = db_session.execute(
            """INSERT INTO endpoint_relationships (name, description, created_at)
               VALUES (:name, :description, CURRENT_TIMESTAMP)
               RETURNING relationship_id""",
            {"name": name, "description": description or f"Maps {source} to {target}"},
        )
        relationship_id = result.fetchone()[0]

        # Add endpoints as members
        db_session.execute(
            """INSERT INTO endpoint_relationship_members 
               (relationship_id, endpoint_id, role, priority)
               VALUES (:relationship_id, :endpoint_id, :role, :priority)""",
            {
                "relationship_id": relationship_id,
                "endpoint_id": source,
                "role": "source",
                "priority": 1,
            },
        )

        db_session.execute(
            """INSERT INTO endpoint_relationship_members 
               (relationship_id, endpoint_id, role, priority)
               VALUES (:relationship_id, :endpoint_id, :role, :priority)""",
            {
                "relationship_id": relationship_id,
                "endpoint_id": target,
                "role": "target",
                "priority": 1,
            },
        )

        db_session.commit()

        click.echo(f"Created relationship '{name}' with ID {relationship_id}")
        click.echo(f"Added endpoints {source} (source) and {target} (target)")

    except Exception as e:
        db_session.rollback()
        click.echo(f"Error creating relationship: {e}")
    finally:
        db_session.close()


@metamapper_cli.command("list-relationships")
def list_relationships():
    """List all endpoint relationships."""
    db_session = get_session()

    try:
        # Get relationships
        relationships = db_session.execute(
            """SELECT r.*, 
                      COUNT(DISTINCT m.endpoint_id) as member_count
               FROM endpoint_relationships r
               LEFT JOIN endpoint_relationship_members m ON r.relationship_id = m.relationship_id
               GROUP BY r.relationship_id
               ORDER BY r.relationship_id"""
        ).fetchall()

        if not relationships:
            click.echo("No relationships found")
            return

        click.echo("\nEndpoint Relationships:\n")
        click.echo(f"{'ID':<5} {'Name':<30} {'Members':<10} {'Created':<20}")
        click.echo("-" * 70)

        for r in relationships:
            click.echo(
                f"{r.relationship_id:<5} {r.name:<30} {r.member_count:<10} {r.created_at}"
            )

            # Get members
            members = db_session.execute(
                """SELECT m.*, e.name as endpoint_name
                   FROM endpoint_relationship_members m
                   JOIN endpoints e ON m.endpoint_id = e.endpoint_id
                   WHERE m.relationship_id = :relationship_id
                   ORDER BY m.role""",
                {"relationship_id": r.relationship_id},
            ).fetchall()

            for m in members:
                click.echo(
                    f"    - {m.endpoint_name} (ID: {m.endpoint_id}, Role: {m.role})"
                )

            click.echo("")

    except Exception as e:
        click.echo(f"Error listing relationships: {e}")
    finally:
        db_session.close()


@metamapper_cli.command("discover-paths")
@click.option("--relationship", required=True, help="Relationship ID", type=int)
@click.option("--force", is_flag=True, help="Force rediscovery of paths")
def discover_paths(relationship: int, force: bool = False):
    """Discover mapping paths between endpoints for a relationship."""

    async def _discover_paths():
        async with await get_session() as session:
            pathfinder = RelationshipPathFinder(session)
            paths = await pathfinder.discover_relationship_paths(
                relationship, force_rediscover=force
            )

            if not paths:
                click.echo("No paths discovered")
                return

            click.echo(f"Discovered {len(paths)} mapping paths:")
            for path in paths:
                click.echo(f"  {path['source_ontology']} -> {path['target_ontology']}")

                # Get full mapping path details
                full_path = await pathfinder.get_best_mapping_path(
                    relationship, path["source_ontology"], path["target_ontology"]
                )

                if full_path and "path_steps" in full_path:
                    steps = full_path["path_steps"]
                    click.echo(f"    Steps: {len(steps)}")
                    for i, step in enumerate(steps):
                        click.echo(
                            f"      Step {i+1}: Resource: {step.get('resource')}"
                        )

    asyncio.run(_discover_paths())


@metamapper_cli.command("map-value")
@click.option("--relationship", required=True, help="Relationship ID", type=int)
@click.option("--value", required=True, help="Source value to map")
@click.option("--source-type", required=True, help="Source ontology type")
@click.option("--target-type", required=True, help="Target ontology type")
@click.option("--force", is_flag=True, help="Force refresh, bypass cache")
def map_value(
    relationship: int,
    value: str,
    source_type: str,
    target_type: str,
    force: bool = False,
):
    """Map a value using a relationship path."""
    click.echo(
        f"Mapping {value} ({source_type} -> {target_type}) for relationship {relationship}"
    )

    async def _map_value():
        async with await get_session() as session:
            mapper = RelationshipMappingExecutor(session)
            results = await mapper.map_with_relationship(
                relationship, value, source_type, target_type, force_refresh=force
            )

            if not results:
                click.echo("No mapping results found")
                return

            click.echo(f"Found {len(results)} mapping results:")
            for result in results:
                click.echo(
                    f"  {result['target_id']} ({result['target_type']}) [confidence: {result['confidence']}]"
                )

    asyncio.run(_map_value())


@metamapper_cli.command("map-endpoint-value")
@click.option("--relationship", required=True, help="Relationship ID", type=int)
@click.option("--value", required=True, help="Source value to map")
@click.option("--force", is_flag=True, help="Force refresh, bypass cache")
def map_endpoint_value(relationship: int, value: str, force: bool = False):
    """Map a value from source endpoint to target endpoint using a relationship."""
    click.echo(f"Mapping {value} between endpoints for relationship {relationship}")

    async def _map_endpoint_value():
        async with await get_session() as session:
            pathfinder = RelationshipPathFinder(session)
            mapper = RelationshipMappingExecutor(session, pathfinder)

            # Get relationship details
            relationship_info = await pathfinder.get_relationship_by_id(relationship)
            if not relationship_info:
                click.echo(f"Relationship {relationship} not found")
                return

            # Get source and target endpoint IDs from relationship
            stmt = """
                SELECT 
                    r.relationship_id, 
                    r.source_endpoint_id,
                    r.target_endpoint_id 
                FROM endpoint_relationships r
                WHERE r.relationship_id = :relationship_id
            """
            result = await session.execute(stmt, {"relationship_id": relationship})
            rel_data = result.fetchone()

            if not rel_data:
                click.echo(
                    f"Relationship {relationship} not found or missing endpoint data"
                )
                return

            source_endpoint_id = rel_data.source_endpoint_id
            target_endpoint_id = rel_data.target_endpoint_id

            # Execute the mapping
            results = await mapper.map_endpoint_value(
                relationship,
                value,
                source_endpoint_id,
                target_endpoint_id,
                force_refresh=force,
            )

            if not results:
                click.echo("No mapping results found")
                return

            click.echo(f"Found {len(results)} mapping results:")
            for result in results:
                click.echo(
                    f"  {result['source_id']} ({result['source_type']}) -> {result['target_id']} ({result['target_type']}) [confidence: {result['confidence']}]"
                )

    asyncio.run(_map_endpoint_value())


@metamapper_cli.command("check-cache")
@click.option("--source-id", required=True, help="Source ID")
@click.option("--source-type", required=True, help="Source ontology type")
@click.option("--target-type", required=True, help="Target ontology type")
@click.option("--relationship", help="Relationship ID", type=int)
def check_cache(
    source_id: str,
    source_type: str,
    target_type: str,
    relationship: Optional[int] = None,
):
    """Check cache for existing mappings."""
    click.echo(f"Checking cache for {source_id} ({source_type} -> {target_type})")

    async def _check_cache():
        async with await get_session() as session:
            mapper = RelationshipMappingExecutor(session)
            results = await mapper.check_cache(
                source_id, source_type, target_type, relationship
            )

            if not results:
                click.echo("No cached mappings found")
                return

            click.echo(f"Found {len(results)} cached mappings:")
            for result in results:
                click.echo(
                    f"  {result['target_id']} ({result['target_type']}) [confidence: {result['confidence']}]"
                )

    asyncio.run(_check_cache())


# Add this function to register the command group
def register_commands(cli):
    cli.add_command(metamapper_cli)


if __name__ == "__main__":
    metamapper_cli()

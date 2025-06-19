"""
CLI commands for endpoint relationship mapping.

This module provides commands for discovering, managing, and executing
endpoint relationship mappings.
"""

import click
import asyncio
import logging

from biomapper.db.session import DatabaseManager
from biomapper.mapping.relationships.path_finder import RelationshipPathFinder
from biomapper.mapping.relationships.executor import RelationshipMappingExecutor

logger = logging.getLogger(__name__)


@click.group("relationship")
def relationship_group():
    """Commands for managing endpoint relationships."""
    pass


@relationship_group.command("list")
def list_relationships():
    """List all defined endpoint relationships."""
    db_manager = DatabaseManager()
    session = db_manager.get_session()

    try:
        rows = session.execute(
            """
            SELECT r.relationship_id, r.name, r.description, COUNT(m.endpoint_id) as members
            FROM endpoint_relationships r
            LEFT JOIN endpoint_relationship_members m ON r.relationship_id = m.relationship_id
            GROUP BY r.relationship_id
        """
        ).fetchall()

        if not rows:
            click.echo("No relationships found.")
            return

        click.echo("\nEndpoint Relationships:")
        click.echo("======================")

        for row in rows:
            click.echo(f"ID: {row[0]} | Name: {row[1]}")
            click.echo(f"Description: {row[2]}")
            click.echo(f"Members: {row[3]}")

            # Get relationship members
            members = session.execute(
                """
                SELECT m.role, e.endpoint_id, e.name
                FROM endpoint_relationship_members m
                JOIN endpoints e ON m.endpoint_id = e.endpoint_id
                WHERE m.relationship_id = :relationship_id
            """,
                {"relationship_id": row[0]},
            ).fetchall()

            for member in members:
                click.echo(f"  {member[0]}: {member[2]} (ID: {member[1]})")

            click.echo("")

    finally:
        session.close()


@relationship_group.command("create")
@click.option("--name", required=True, help="Relationship name")
@click.option("--description", help="Relationship description")
@click.option("--source", type=int, required=True, help="Source endpoint ID")
@click.option("--target", type=int, required=True, help="Target endpoint ID")
def create_relationship(name, description, source, target):
    """Create a new endpoint relationship."""
    db_manager = DatabaseManager()
    session = db_manager.get_session()

    try:
        # Check if endpoints exist
        source_endpoint = session.execute(
            """
            SELECT name FROM endpoints WHERE endpoint_id = :endpoint_id
        """,
            {"endpoint_id": source},
        ).fetchone()

        target_endpoint = session.execute(
            """
            SELECT name FROM endpoints WHERE endpoint_id = :endpoint_id
        """,
            {"endpoint_id": target},
        ).fetchone()

        if not source_endpoint:
            click.echo(f"Error: Source endpoint with ID {source} not found.")
            return

        if not target_endpoint:
            click.echo(f"Error: Target endpoint with ID {target} not found.")
            return

        # Create the relationship
        result = session.execute(
            """
            INSERT INTO endpoint_relationships (name, description)
            VALUES (:name, :description)
            RETURNING relationship_id
        """,
            {"name": name, "description": description or ""},
        )

        relationship_id = result.fetchone()[0]

        # Add members
        session.execute(
            """
            INSERT INTO endpoint_relationship_members 
            (relationship_id, endpoint_id, role)
            VALUES (:relationship_id, :source_id, 'source'),
                   (:relationship_id, :target_id, 'target')
        """,
            {
                "relationship_id": relationship_id,
                "source_id": source,
                "target_id": target,
            },
        )

        session.commit()
        click.echo(f"Created relationship: {name} (ID: {relationship_id})")
        click.echo(f"Source: {source_endpoint[0]} (ID: {source})")
        click.echo(f"Target: {target_endpoint[0]} (ID: {target})")

    except Exception as e:
        session.rollback()
        click.echo(f"Error creating relationship: {e}")

    finally:
        session.close()


@relationship_group.command("discover-paths")
@click.option("--relationship-id", type=int, required=True, help="Relationship ID")
@click.option("--force", is_flag=True, help="Force rediscovery of paths")
def discover_relationship_paths(relationship_id, force):
    """Discover mapping paths for a relationship."""

    async def run():
        db_manager = DatabaseManager()
        session = db_manager.get_session()

        try:
            path_finder = RelationshipPathFinder(session)
            paths = await path_finder.discover_paths_for_relationship(relationship_id)

            click.echo(
                f"Discovered {len(paths)} mapping paths for relationship {relationship_id}"
            )
            for i, path in enumerate(paths):
                source_ont = path["path"]["source_type"]
                target_ont = path["path"]["target_type"]
                score = path["score"]
                click.echo(
                    f"Path {i+1}: {source_ont} → {target_ont} (score: {score:.2f})"
                )

                # Show path steps
                steps = path["path"].get("path_steps", [])
                for j, step in enumerate(steps):
                    click.echo(
                        f"  Step {j+1}: {step.get('source_type', step.get('from_type'))} → {step.get('target_type', step.get('to_type'))}"
                    )

        except Exception as e:
            click.echo(f"Error discovering paths: {e}")

        finally:
            session.close()

    asyncio.run(run())


@relationship_group.command("map")
@click.option("--relationship-id", type=int, required=True, help="Relationship ID")
@click.option("--source-id", required=True, help="Source entity ID")
@click.option("--source-ontology", help="Source ontology type")
def execute_relationship_mapping(relationship_id, source_id, source_ontology):
    """Execute a mapping for a relationship."""

    async def run():
        db_manager = DatabaseManager()
        session = db_manager.get_session()

        try:
            executor = RelationshipMappingExecutor(session)
            results = await executor.map_entity(
                relationship_id=relationship_id,
                source_entity=source_id,
                source_ontology=source_ontology,
            )

            if not results:
                click.echo(f"No mapping results found for {source_id}")
                return

            click.echo(f"Mapping results for {source_id}:")
            for result in results:
                source_type = result.get("source_type", "unknown")
                target_id = result.get("target_id", "unknown")
                target_type = result.get("target_type", "unknown")
                confidence = result.get("confidence", "unknown")
                click.echo(
                    f"  {source_type}:{source_id} → {target_type}:{target_id} (confidence: {confidence})"
                )

        except Exception as e:
            click.echo(f"Error executing mapping: {e}")

        finally:
            session.close()

    asyncio.run(run())


@relationship_group.command("map-data")
@click.option("--relationship-id", type=int, required=True, help="Relationship ID")
@click.option("--hmdb", help="HMDB identifier")
@click.option("--chebi", help="ChEBI identifier")
@click.option("--pubchem", help="PubChem identifier")
@click.option("--kegg", help="KEGG identifier")
@click.option("--name", help="Compound name")
@click.option("--cas", help="CAS identifier")
def map_from_data(relationship_id, hmdb, chebi, pubchem, kegg, name, cas):
    """Map data directly from provided values."""

    # Collect data
    source_data = {}
    if hmdb:
        source_data["HMDB"] = hmdb
    if chebi:
        source_data["CHEBI"] = chebi
    if pubchem:
        source_data["PUBCHEM"] = pubchem
    if kegg:
        source_data["KEGG"] = kegg
    if name:
        source_data["BIOCHEMICAL_NAME"] = name
    if cas:
        source_data["CAS"] = cas

    if not source_data:
        click.echo("Error: At least one identifier type must be provided.")
        return

    async def run():
        db_manager = DatabaseManager()

        # Use async context manager for session
        async with await db_manager.create_async_session() as session:
            # Discover paths first (if needed, or assume they exist for mapping)
            pathfinder = RelationshipPathFinder(session)
            await pathfinder.discover_paths_for_relationship(relationship_id)

            # Execute mapping
            mapper = RelationshipMappingExecutor(session)
            source_data = {
                "hmdb": hmdb,
                "chebi": chebi,
                "pubchem": pubchem,
                "kegg": kegg,
                "name": name,
                "cas": cas,
            }
            click.echo(f"Attempting to map data for relationship {relationship_id}:")
            click.echo(f"Source data: {source_data}")

            results = await mapper.map_from_endpoint_data(
                relationship_id=relationship_id, source_data=source_data
            )

            if results:
                click.echo("\nMapping Results:")
                for item in results:
                    click.echo(
                        f"  Input: {item['source_id']} ({item['source_type']}) -> "
                        f"Output: {item['target_id']} ({item['target_type']}) "
                        f"[Confidence: {item['confidence']:.2f}]"
                    )
            else:
                click.echo("\nNo mapping results found.")

    # Execute the async function
    asyncio.run(run())


# Add the command group to biomapper CLI
def register_commands(cli):
    cli.add_command(relationship_group)

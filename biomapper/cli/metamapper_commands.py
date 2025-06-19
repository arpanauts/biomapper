"""
Command-line interface for the MetaMapping System.

This module provides commands for discovering, testing, and executing
mapping paths between endpoints.
"""

import click
import asyncio
import logging
from typing import Optional

from biomapper.db.session import get_session
from biomapper.mapping.metadata.pathfinder import RelationshipPathFinder
from biomapper.mapping.metadata.mapper import RelationshipMappingExecutor
from sqlalchemy import text
from biomapper.config import settings
from biomapper.db.session import DatabaseManager # Import session utilities

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


async def _list_relationships_async():
    """Async logic for listing all endpoint relationships."""
    # Ensure we are using the metamapper_db for relationship metadata
    logger.info(f"_list_relationships_async: settings.metamapper_db_url is {settings.metamapper_db_url}")
    manager = DatabaseManager(db_url=settings.metamapper_db_url, echo=(settings.log_level.upper() == "DEBUG"))
    logger.info(f"_list_relationships_async: manager.db_url is {manager.db_url}")
    logger.info(f"_list_relationships_async: manager.async_engine.url is {manager.async_engine.url}")
    
    try:
        async with await manager.create_async_session() as db_session:
            # Diagnostic: List all tables
            try:
                stmt_diag = text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                all_tables_result = await db_session.execute(stmt_diag)
                all_tables = all_tables_result.fetchall()
                logger.info(f"_list_relationships_async: Tables in connected DB: {all_tables}")
            except Exception as e_diag:
                logger.error(f"_list_relationships_async: Error querying sqlite_master: {e_diag}")

            # Get relationships
            result = await db_session.execute(
                text("""SELECT r.*, 
                          COUNT(DISTINCT m.endpoint_id) as member_count
                   FROM endpoint_relationships r
                   LEFT JOIN endpoint_relationship_members m ON r.id = m.relationship_id
                   GROUP BY r.id
                   ORDER BY r.id"""          
                )
            )
            relationships = result.fetchall()

            if not relationships:
                click.echo("No relationships found")
                return

            click.echo("\nEndpoint Relationships:\n")
            click.echo(f"{'ID':<5} {'Description':<60} {'Members':<10}")
            click.echo("-" * 80)

            for rel in relationships:
                # Access the actual available attributes from the query
                description = rel.description if rel.description else ''
                member_count = rel.member_count

                click.echo(
                    f"{str(rel.id):<5} {str(description):<60} {str(member_count):<10}"
                )

                # Get members using the same session
                member_result = await db_session.execute(
                    text("""SELECT m.*, e.name as endpoint_name
                       FROM endpoint_relationship_members m
                       JOIN endpoints e ON m.endpoint_id = e.id  
                       WHERE m.relationship_id = :relationship_id
                       ORDER BY m.role"""        
                    ),
                    {"relationship_id": rel.id},
                )
                members = member_result.fetchall()

                for m in members:
                    click.echo(
                        f"    - {m.endpoint_name} (ID: {m.endpoint_id}, Role: {m.role}, Priority: {m.priority})"
                    )
                click.echo("")

    except Exception as e:
        # Log the full traceback for debugging
        logger.error(f"Error listing relationships: {e}", exc_info=True)
        click.echo(f"Error listing relationships: {e}")


@metamapper_cli.command("list-relationships")
def list_relationships():
    """List all endpoint relationships."""
    asyncio.run(_list_relationships_async())


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

#!/usr/bin/env python3
"""Script to test relationship mapping path discovery and execution."""

import os
import sys
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
import time
from sqlalchemy import text

# Add the parent directory to Python path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from biomapper.db.session import async_engine, async_session_maker, init_db_manager
from biomapper.mapping.metadata.pathfinder import RelationshipPathFinder
from biomapper.mapping.metadata.mapper import RelationshipMappingExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def test_relationship_path_discovery():
    """Test relationship mapping path discovery."""
    logger.info("Testing relationship mapping path discovery")

    # Get a session
    session = await async_session_maker()

    # Initialize a path finder
    pathfinder = RelationshipPathFinder(session)

    # Find MetabolitesCSV to SPOKE relationship
    relationship_id = None
    source_id = None
    target_id = None

    # Query endpoint_relationships table for test relationship
    query = """
        SELECT r.relationship_id,
               s.endpoint_id as source_id,
               t.endpoint_id as target_id
        FROM endpoint_relationships r
        JOIN endpoint_relationship_members srm ON r.relationship_id = srm.relationship_id AND srm.role = 'source'
        JOIN endpoint_relationship_members trm ON r.relationship_id = trm.relationship_id AND trm.role = 'target'
        JOIN endpoints s ON srm.endpoint_id = s.endpoint_id
        JOIN endpoints t ON trm.endpoint_id = t.endpoint_id
        WHERE s.name = 'MetabolitesCSV' AND t.name = 'SPOKE'
    """
    result = await session.execute(text(query))
    relationship = result.fetchone()

    if relationship:
        relationship_id = relationship.relationship_id
        source_id = relationship.source_id
        target_id = relationship.target_id
        logger.info(f"Found relationship ID: {relationship_id}")
    else:
        # Create a test relationship for demo purposes
        logger.info("Creating test relationship for MetabolitesCSV to SPOKE")
        # Get endpoint IDs
        query = "SELECT endpoint_id, name FROM endpoints WHERE name IN ('MetabolitesCSV', 'SPOKE')"
        result = await session.execute(text(query))
        endpoints = {row.name: row.endpoint_id for row in result.fetchall()}

        if "MetabolitesCSV" in endpoints and "SPOKE" in endpoints:
            source_id = endpoints["MetabolitesCSV"]
            target_id = endpoints["SPOKE"]

            query = """
                INSERT INTO endpoint_relationships 
                (name, description, source_endpoint_id, target_endpoint_id, created_at)
                VALUES 
                ('Test-MetabolitesCSV-to-SPOKE', 'Test relationship for mapping', :source_id, :target_id, CURRENT_TIMESTAMP)
                RETURNING relationship_id
            """
            result = await session.execute(
                text(query), {"source_id": source_id, "target_id": target_id}
            )
            relationship_id = result.fetchone()[0]
            await session.commit()
            logger.info(f"Created test relationship with ID: {relationship_id}")
        else:
            logger.error("Could not find MetabolitesCSV and SPOKE endpoints")
            return

    # Discover mapping paths for the relationship
    paths = await pathfinder.discover_relationship_paths(
        relationship_id, force_rediscover=True
    )

    if not paths:
        logger.warning(
            f"No mapping paths discovered for relationship {relationship_id}"
        )
    else:
        logger.info(
            f"Discovered {len(paths)} mapping paths for relationship {relationship_id}"
        )

        # Print path details
        for path in paths:
            source_ontology = path["source_ontology"]
            target_ontology = path["target_ontology"]
            logger.info(f"  Path {path['id']}: {source_ontology} -> {target_ontology}")

            # Get full mapping path details
            full_path = await pathfinder.get_best_mapping_path(
                relationship_id, source_ontology, target_ontology
            )

            if full_path and "path_steps" in full_path:
                steps = full_path["path_steps"]
                logger.info(f"    Steps: {len(steps)}")
                for i, step in enumerate(steps):
                    logger.info(f"      Step {i+1}: Resource: {step.get('resource')}")


async def test_relationship_mapping_execution():
    """Test relationship mapping execution."""
    logger.info("Testing relationship mapping execution")

    # Get a session
    session = await async_session_maker()

    # Initialize a path finder and mapper
    pathfinder = RelationshipPathFinder(session)
    mapper = RelationshipMappingExecutor(session, pathfinder)

    # Find MetabolitesCSV to SPOKE relationship
    relationship_id = None

    # Query endpoint_relationships table for MetabolitesCSV to SPOKE
    query = """
        SELECT r.relationship_id, 
               srm.endpoint_id as source_endpoint_id, 
               trm.endpoint_id as target_endpoint_id,
               s.name as source_name, 
               t.name as target_name
        FROM endpoint_relationships r
        JOIN endpoint_relationship_members srm ON r.relationship_id = srm.relationship_id AND srm.role = 'source'
        JOIN endpoint_relationship_members trm ON r.relationship_id = trm.relationship_id AND trm.role = 'target'
        JOIN endpoints s ON srm.endpoint_id = s.endpoint_id
        JOIN endpoints t ON trm.endpoint_id = t.endpoint_id
        WHERE s.name = 'MetabolitesCSV' AND t.name = 'SPOKE'
        LIMIT 1
    """
    result = await session.execute(text(query))
    relationship = result.fetchone()

    if not relationship:
        logger.error("MetabolitesCSV to SPOKE relationship not found")
        return

    relationship_id = relationship.relationship_id
    source_endpoint_id = relationship.source_endpoint_id
    target_endpoint_id = relationship.target_endpoint_id

    logger.info(f"Found relationship ID: {relationship_id}")
    logger.info(
        f"Source endpoint: {relationship.source_name} (ID: {source_endpoint_id})"
    )
    logger.info(
        f"Target endpoint: {relationship.target_name} (ID: {target_endpoint_id})"
    )

    # Test mapping a simple value
    test_value = "HMDB0000001"  # Example HMDB ID
    logger.info(f"Mapping value: {test_value}")

    # Map using hmdb -> pubchem
    results = await mapper.map_with_relationship(
        relationship_id, test_value, "hmdb", "pubchem", force_refresh=True
    )

    if not results:
        logger.warning(f"No mapping results for {test_value} (hmdb -> pubchem)")
    else:
        logger.info(f"Found {len(results)} mapping results:")
        for result in results:
            logger.info(
                f"  {result['source_id']} ({result['source_type']}) -> {result['target_id']} ({result['target_type']}) [confidence: {result['confidence']}]"
            )

    # Test endpoint value mapping
    results = await mapper.map_endpoint_value(
        relationship_id,
        test_value,
        source_endpoint_id,
        target_endpoint_id,
        force_refresh=True,
    )

    if not results:
        logger.warning(f"No endpoint mapping results for {test_value}")
    else:
        logger.info(f"Found {len(results)} endpoint mapping results:")
        for result in results:
            logger.info(
                f"  {result['source_id']} ({result['source_type']}) -> {result['target_id']} ({result['target_type']}) [confidence: {result['confidence']}]"
            )


async def check_cache_entries():
    """Check mapping cache entries."""
    logger.info("Checking mapping cache entries")

    # Get a session
    session = await async_session_maker()

    # Query the mapping cache
    query = """
        SELECT mc.*, rm.relationship_id
        FROM mapping_cache mc
        LEFT JOIN relationship_mappings rm ON mc.mapping_id = rm.mapping_id
        LIMIT 10
    """
    result = await session.execute(text(query))
    entries = result.fetchall()

    if not entries:
        logger.warning("No entries found in mapping cache")
        return

    logger.info(f"Found {len(entries)} entries in mapping cache:")
    for entry in entries:
        rel_id = entry.relationship_id if hasattr(entry, "relationship_id") else None
        logger.info(
            f"  {entry.source_id} ({entry.source_type}) -> {entry.target_id} ({entry.target_type}) [confidence: {entry.confidence}, relationship: {rel_id}]"
        )


async def main():
    """Main execution function."""
    # Use the existing metamapper.db database
    db_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
        "data/metamapper.db",
    )
    os.environ["BIOMAPPER_DB_PATH"] = db_path

    # Connect directly to the database to check tables
    import sqlite3

    logger.info(f"Directly checking database at: {db_path}")

    try:
        # Connect directly to the SQLite database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Check for tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        logger.info(f"Tables in database: {tables}")

        if "endpoint_relationships" in tables:
            c.execute("SELECT COUNT(*) FROM endpoint_relationships")
            count = c.fetchone()[0]
            logger.info(f"Number of endpoint relationships: {count}")

            # If no relationships exist, create one
            if count == 0:
                logger.info("Creating a test relationship")
                c.execute(
                    """
                    INSERT INTO endpoint_relationships 
                    (relationship_id, name, description, created_at)
                    VALUES (1, 'Test-Relationship', 'A test relationship', CURRENT_TIMESTAMP)
                """
                )

                # Also make sure we have endpoints
                c.execute("SELECT COUNT(*) FROM endpoints")
                count = c.fetchone()[0]

                if count == 0:
                    logger.info("Creating test endpoints")
                    c.execute(
                        """
                        INSERT INTO endpoints
                        (endpoint_id, name, description, endpoint_type, created_at)
                        VALUES (1, 'MetabolitesCSV', 'Test CSV source', 'file', CURRENT_TIMESTAMP)
                    """
                    )

                    c.execute(
                        """
                        INSERT INTO endpoints
                        (endpoint_id, name, description, endpoint_type, created_at)
                        VALUES (2, 'SPOKE', 'Test SPOKE target', 'graph', CURRENT_TIMESTAMP)
                    """
                    )

                conn.commit()
                logger.info("Test data created")
        else:
            logger.error(
                "The endpoint_relationships table does not exist. Running db setup first"
            )
            # Run the table creation script
            import subprocess

            setup_path = os.path.join(
                os.path.dirname(__file__),
                "../db_management/create_endpoint_mapping_tables.py",
            )
            subprocess.run(["python", setup_path])

        conn.close()
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")

    # Now set the environment variable for the session
    os.environ["BIOMAPPER_DB_PATH"] = db_path

    # Reinitialize the database manager with the correct path
    init_db_manager()

    # Test relationship path discovery
    await test_relationship_path_discovery()

    # Test relationship mapping execution
    await test_relationship_mapping_execution()

    # Check cache entries
    await check_cache_entries()


if __name__ == "__main__":
    asyncio.run(main())

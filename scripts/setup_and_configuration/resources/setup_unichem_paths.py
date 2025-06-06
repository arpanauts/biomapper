#!/usr/bin/env python3
"""
Setup mapping paths for UniChem database in the Metamapper system.

This script registers the UniChem resource in the Metamapper database and
defines mapping paths between various chemical identifiers.
"""

import os
import sys
import sqlite3
import logging
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the database configuration
from biomapper.mapping.metadata.config import get_metadata_db_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_unichem_resource():
    """Register the UniChem resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'UniChem'")
        existing = cursor.fetchone()

        if existing:
            logger.info(f"UniChem resource already exists with ID {existing[0]}")
            return existing[0]

        # Resource configuration
        config = {
            "base_url": "https://www.ebi.ac.uk/unichem/rest",
            "timeout": 30,
            "max_retries": 3,
            "backoff_factor": 0.5,
        }

        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "UniChem",
                "EBI's compound identifier mapping service",
                "UniChemClient",
                json.dumps(config),
                "active",
            ),
        )

        resource_id = cursor.lastrowid
        logger.info(f"Added UniChem resource with ID {resource_id}")

        # Commit changes
        conn.commit()
        return resource_id

    except Exception as e:
        logger.error(f"Error setting up UniChem resource: {e}")
        conn.rollback()
        return None

    finally:
        # Close the database connection
        conn.close()


def setup_unichem_paths(resource_id):
    """Setup mapping paths for UniChem."""
    if not resource_id:
        logger.error("Cannot setup paths without a valid resource ID")
        return False

    # Get database path
    db_path = get_metadata_db_path()

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Define mapping paths
        paths = [
            # PUBCHEM to CHEBI direct path
            {
                "source_type": "PUBCHEM",
                "target_type": "CHEBI",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "PUBCHEM",
                            "target": "CHEBI",
                            "method": "lookup_direct_mapping",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 90,
            },
            # CHEBI to PUBCHEM direct path
            {
                "source_type": "CHEBI",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "CHEBI",
                            "target": "PUBCHEM",
                            "method": "lookup_direct_mapping",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 90,
            },
            # INCHIKEY to PUBCHEM path
            {
                "source_type": "INCHIKEY",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "INCHIKEY",
                            "target": "PUBCHEM",
                            "method": "structure_search",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 95,
            },
            # INCHIKEY to CHEBI path
            {
                "source_type": "INCHIKEY",
                "target_type": "CHEBI",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "INCHIKEY",
                            "target": "CHEBI",
                            "method": "structure_search",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 90,
            },
            # INCHIKEY to HMDB path
            {
                "source_type": "INCHIKEY",
                "target_type": "HMDB",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "INCHIKEY",
                            "target": "HMDB",
                            "method": "structure_search",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 85,
            },
            # HMDB to PUBCHEM path
            {
                "source_type": "HMDB",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "HMDB",
                            "target": "PUBCHEM",
                            "method": "lookup_direct_mapping",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 85,
            },
            # NAME to HMDB via UniChem path
            {
                "source_type": "NAME",
                "target_type": "HMDB",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "NAME",
                            "target": "HMDB",
                            "method": "search_by_name",
                            "resources": ["UniChem"],
                        }
                    ]
                ),
                "performance_score": 60,
            },
        ]

        # Insert paths
        for path in paths:
            cursor.execute(
                """INSERT OR IGNORE INTO mapping_paths 
                   (source_type, target_type, path_steps, performance_score) 
                   VALUES (?, ?, ?, ?)""",
                (
                    path["source_type"],
                    path["target_type"],
                    path["path_steps"],
                    path["performance_score"],
                ),
            )
            if cursor.rowcount > 0:
                logger.info(
                    f"Added mapping path: {path['source_type']} -> {path['target_type']}"
                )
            else:
                logger.info(
                    f"Path already exists: {path['source_type']} -> {path['target_type']}"
                )

        # Commit changes
        conn.commit()
        logger.info("UniChem mapping paths setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting up UniChem paths: {e}")
        conn.rollback()
        return False

    finally:
        # Close the database connection
        conn.close()


if __name__ == "__main__":
    # Register UniChem resource
    resource_id = setup_unichem_resource()

    if resource_id:
        # Setup mapping paths
        setup_unichem_paths(resource_id)
    else:
        logger.error("Failed to setup UniChem resource")
        sys.exit(1)

#!/usr/bin/env python3
"""
Setup mapping paths for KEGG database in the Metamapper system.

This script registers the KEGG resource in the Metamapper database and
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


def setup_kegg_resource():
    """Register the KEGG resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'KEGG'")
        existing = cursor.fetchone()

        if existing:
            logger.info(f"KEGG resource already exists with ID {existing[0]}")
            return existing[0]

        # Resource configuration
        config = {"base_url": "https://rest.kegg.jp", "timeout": 30, "retry_count": 3}

        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "KEGG",
                "KEGG API for metabolic pathway and compound information",
                "KEGGClient",
                json.dumps(config),
                "active",
            ),
        )

        resource_id = cursor.lastrowid
        logger.info(f"Added KEGG resource with ID {resource_id}")

        # Commit changes
        conn.commit()
        return resource_id

    except Exception as e:
        logger.error(f"Error setting up KEGG resource: {e}")
        conn.rollback()
        return None

    finally:
        # Close the database connection
        conn.close()


def setup_kegg_paths(resource_id):
    """Setup mapping paths for KEGG."""
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
            # NAME to KEGG direct path
            {
                "source_type": "NAME",
                "target_type": "KEGG",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "NAME",
                            "target": "KEGG",
                            "method": "search_by_name",
                            "resources": ["KEGG"],
                        }
                    ]
                ),
                "performance_score": 50,
                "description": "Direct search of compound name in KEGG",
            },
            # KEGG to FORMULA path
            {
                "source_type": "KEGG",
                "target_type": "FORMULA",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "KEGG",
                            "target": "FORMULA",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        }
                    ]
                ),
                "performance_score": 70,
                "description": "Extract molecular formula from KEGG compound",
            },
            # KEGG to CHEBI path
            {
                "source_type": "KEGG",
                "target_type": "CHEBI",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "KEGG",
                            "target": "CHEBI",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        }
                    ]
                ),
                "performance_score": 60,
                "description": "Extract ChEBI ID from KEGG compound",
            },
            # KEGG to PUBCHEM path
            {
                "source_type": "KEGG",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "KEGG",
                            "target": "PUBCHEM",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        }
                    ]
                ),
                "performance_score": 60,
                "description": "Extract PubChem ID from KEGG compound",
            },
            # NAME to FORMULA through KEGG
            {
                "source_type": "NAME",
                "target_type": "FORMULA",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "NAME",
                            "target": "KEGG",
                            "method": "search_by_name",
                            "resources": ["KEGG"],
                        },
                        {
                            "source": "KEGG",
                            "target": "FORMULA",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        },
                    ]
                ),
                "performance_score": 40,
                "description": "Convert NAME to FORMULA via KEGG",
            },
            # NAME to CHEBI through KEGG
            {
                "source_type": "NAME",
                "target_type": "CHEBI",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "NAME",
                            "target": "KEGG",
                            "method": "search_by_name",
                            "resources": ["KEGG"],
                        },
                        {
                            "source": "KEGG",
                            "target": "CHEBI",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        },
                    ]
                ),
                "performance_score": 30,
                "description": "Convert NAME to CHEBI via KEGG",
            },
            # NAME to PUBCHEM through KEGG
            {
                "source_type": "NAME",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps(
                    [
                        {
                            "source": "NAME",
                            "target": "KEGG",
                            "method": "search_by_name",
                            "resources": ["KEGG"],
                        },
                        {
                            "source": "KEGG",
                            "target": "PUBCHEM",
                            "method": "extract_property",
                            "resources": ["KEGG"],
                        },
                    ]
                ),
                "performance_score": 30,
                "description": "Convert NAME to PUBCHEM via KEGG",
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
        logger.info("KEGG mapping paths setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting up KEGG paths: {e}")
        conn.rollback()
        return False

    finally:
        # Close the database connection
        conn.close()


if __name__ == "__main__":
    # Register KEGG resource
    resource_id = setup_kegg_resource()

    if resource_id:
        # Setup mapping paths
        setup_kegg_paths(resource_id)
    else:
        logger.error("Failed to setup KEGG resource")
        sys.exit(1)

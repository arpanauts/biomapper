#!/usr/bin/env python3
"""
Setup mapping paths for Extension Graph in the Metamapper system.

This script registers the Extension Graph resource in the Metamapper database and
defines mapping paths for custom relationships and FDA UNII data.
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

def setup_extension_graph_resource():
    """Register the Extension Graph resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'ExtensionGraph'")
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Extension Graph resource already exists with ID {existing[0]}")
            return existing[0]
        
        # Resource configuration
        config = {
            "host": "localhost",
            "port": 8529,
            "database": "extension_graph",
            "username": "extension_user",
            "password": "",
            "timeout": 30
        }
        
        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "ExtensionGraph",
                "Supplementary knowledge graph with custom relationships and FDA UNII data",
                "ArangoDBClient",
                json.dumps(config),
                "active"
            )
        )
        
        resource_id = cursor.lastrowid
        logger.info(f"Added Extension Graph resource with ID {resource_id}")
        
        # Commit changes
        conn.commit()
        return resource_id
        
    except Exception as e:
        logger.error(f"Error setting up Extension Graph resource: {e}")
        conn.rollback()
        return None
    
    finally:
        # Close the database connection
        conn.close()

def setup_extension_graph_paths(resource_id):
    """Setup mapping paths for Extension Graph."""
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
            # NAME to UNII (FDA Unique Ingredient Identifier)
            {
                "source_type": "NAME",
                "target_type": "UNII",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "UNII",
                        "method": "search_by_name",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 75,
            },
            
            # UNII to PUBCHEM direct path
            {
                "source_type": "UNII",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "UNII",
                        "target": "PUBCHEM",
                        "method": "direct_mapping",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 85,
            },
            
            # UNII to CHEBI path
            {
                "source_type": "UNII",
                "target_type": "CHEBI",
                "path_steps": json.dumps([
                    {
                        "source": "UNII",
                        "target": "CHEBI",
                        "method": "direct_mapping",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 80,
            },
            
            # FOODID to PUBCHEM mapping
            {
                "source_type": "FOODID",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "FOODID",
                        "target": "PUBCHEM",
                        "method": "food_component_mapping",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 65,
            },
            
            # NAME to FOODID mapping
            {
                "source_type": "NAME",
                "target_type": "FOODID",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "FOODID",
                        "method": "search_by_name",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 60,
            },
            
            # NAME to PUBCHEM via food component
            {
                "source_type": "NAME",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "FOODID",
                        "method": "search_by_name",
                        "resources": ["ExtensionGraph"]
                    },
                    {
                        "source": "FOODID",
                        "target": "PUBCHEM",
                        "method": "food_component_mapping",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 50,
            },
            
            # UNII to ATCID (Anatomical Therapeutic Chemical Classification)
            {
                "source_type": "UNII",
                "target_type": "ATCID",
                "path_steps": json.dumps([
                    {
                        "source": "UNII",
                        "target": "ATCID",
                        "method": "drug_classification",
                        "resources": ["ExtensionGraph"]
                    }
                ]),
                "performance_score": 80,
            }
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
                    path["performance_score"]
                )
            )
            if cursor.rowcount > 0:
                logger.info(f"Added mapping path: {path['source_type']} -> {path['target_type']}")
            else:
                logger.info(f"Path already exists: {path['source_type']} -> {path['target_type']}")
        
        # Commit changes
        conn.commit()
        logger.info("Extension Graph mapping paths setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up Extension Graph paths: {e}")
        conn.rollback()
        return False
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Register Extension Graph resource
    resource_id = setup_extension_graph_resource()
    
    if resource_id:
        # Setup mapping paths
        setup_extension_graph_paths(resource_id)
    else:
        logger.error("Failed to setup Extension Graph resource")
        sys.exit(1)

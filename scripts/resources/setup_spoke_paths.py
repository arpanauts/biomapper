#!/usr/bin/env python3
"""
Setup mapping paths for SPOKE Knowledge Graph in the Metamapper system.

This script registers the SPOKE resource in the Metamapper database and
defines mapping paths between various biomedical entities.
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

def setup_spoke_resource():
    """Register the SPOKE resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'SPOKE'")
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"SPOKE resource already exists with ID {existing[0]}")
            return existing[0]
        
        # Resource configuration - update with actual connection details
        config = {
            "host": "localhost",
            "port": 8529,
            "database": "spoke",
            "username": "spoke_user",
            "password": "",
            "timeout": 30
        }
        
        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "SPOKE",
                "Scalable Precision Medicine Open Knowledge Engine - comprehensive biomedical knowledge graph",
                "ArangoDBClient",
                json.dumps(config),
                "active"
            )
        )
        
        resource_id = cursor.lastrowid
        logger.info(f"Added SPOKE resource with ID {resource_id}")
        
        # Commit changes
        conn.commit()
        return resource_id
        
    except Exception as e:
        logger.error(f"Error setting up SPOKE resource: {e}")
        conn.rollback()
        return None
    
    finally:
        # Close the database connection
        conn.close()

def setup_spoke_paths(resource_id):
    """Setup mapping paths for SPOKE Knowledge Graph."""
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
            # NAME to CHEBI via SPOKE
            {
                "source_type": "NAME",
                "target_type": "CHEBI",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "CHEBI",
                        "method": "search_by_name",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 55,
            },
            
            # PUBCHEM to DOID (disease ontology) mapping
            {
                "source_type": "PUBCHEM",
                "target_type": "DOID",
                "path_steps": json.dumps([
                    {
                        "source": "PUBCHEM",
                        "target": "DOID",
                        "method": "graph_traversal",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 60,
            },
            
            # CHEBI to GENEID mapping
            {
                "source_type": "CHEBI",
                "target_type": "GENEID",
                "path_steps": json.dumps([
                    {
                        "source": "CHEBI",
                        "target": "GENEID",
                        "method": "graph_traversal",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 70,
            },
            
            # GENEID to UNIPROT mapping
            {
                "source_type": "GENEID",
                "target_type": "UNIPROT",
                "path_steps": json.dumps([
                    {
                        "source": "GENEID",
                        "target": "UNIPROT",
                        "method": "direct_mapping",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 90,
            },
            
            # NAME to GENEID via compound interaction
            {
                "source_type": "NAME",
                "target_type": "GENEID",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "CHEBI",
                        "method": "search_by_name",
                        "resources": ["SPOKE"]
                    },
                    {
                        "source": "CHEBI",
                        "target": "GENEID",
                        "method": "graph_traversal",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 50,
            },
            
            # GENEID to PATHWAY mapping
            {
                "source_type": "GENEID",
                "target_type": "PATHWAY",
                "path_steps": json.dumps([
                    {
                        "source": "GENEID",
                        "target": "PATHWAY",
                        "method": "graph_traversal",
                        "resources": ["SPOKE"]
                    }
                ]),
                "performance_score": 85,
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
                    path["performance_score"]
                )
            )
            if cursor.rowcount > 0:
                logger.info(f"Added mapping path: {path['source_type']} -> {path['target_type']}")
            else:
                logger.info(f"Path already exists: {path['source_type']} -> {path['target_type']}")
        
        # Commit changes
        conn.commit()
        logger.info("SPOKE mapping paths setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up SPOKE paths: {e}")
        conn.rollback()
        return False
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Register SPOKE resource
    resource_id = setup_spoke_resource()
    
    if resource_id:
        # Setup mapping paths
        setup_spoke_paths(resource_id)
    else:
        logger.error("Failed to setup SPOKE resource")
        sys.exit(1)

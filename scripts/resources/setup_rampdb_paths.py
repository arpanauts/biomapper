#!/usr/bin/env python3
"""
Setup mapping paths for RaMP DB in the Metamapper system.

This script registers the RaMP DB resource in the Metamapper database and
defines mapping paths between various metabolites, pathways, and genes.
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

def setup_rampdb_resource():
    """Register the RaMP DB resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'RaMP'")
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"RaMP DB resource already exists with ID {existing[0]}")
            return existing[0]
        
        # Resource configuration
        config = {
            "db_path": "/path/to/rampdb.sqlite",  # Update with actual path
            "timeout": 30,
            "max_retries": 3
        }
        
        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "RaMP",
                "Rapid Mapping Database for metabolites and pathways",
                "RaMPClient",
                json.dumps(config),
                "active"
            )
        )
        
        resource_id = cursor.lastrowid
        logger.info(f"Added RaMP DB resource with ID {resource_id}")
        
        # Commit changes
        conn.commit()
        return resource_id
        
    except Exception as e:
        logger.error(f"Error setting up RaMP DB resource: {e}")
        conn.rollback()
        return None
    
    finally:
        # Close the database connection
        conn.close()

def setup_rampdb_paths(resource_id):
    """Setup mapping paths for RaMP DB."""
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
            # NAME to HMDB path
            {
                "source_type": "NAME",
                "target_type": "HMDB",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "HMDB",
                        "method": "search_by_name",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 65,
            },
            
            # NAME to KEGG path via RaMP
            {
                "source_type": "NAME",
                "target_type": "KEGG",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "KEGG",
                        "method": "search_by_name",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 65,
            },
            
            # NAME to PATHWAYID path
            {
                "source_type": "NAME",
                "target_type": "PATHWAYID",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "HMDB",
                        "method": "search_by_name",
                        "resources": ["RaMP"]
                    },
                    {
                        "source": "HMDB",
                        "target": "PATHWAYID",
                        "method": "lookup_pathway",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 60,
            },
            
            # HMDB to PATHWAYID direct path
            {
                "source_type": "HMDB",
                "target_type": "PATHWAYID",
                "path_steps": json.dumps([
                    {
                        "source": "HMDB",
                        "target": "PATHWAYID",
                        "method": "lookup_pathway",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 80,
            },
            
            # KEGG to PATHWAYID direct path
            {
                "source_type": "KEGG",
                "target_type": "PATHWAYID",
                "path_steps": json.dumps([
                    {
                        "source": "KEGG",
                        "target": "PATHWAYID",
                        "method": "lookup_pathway",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 85,
            },
            
            # PATHWAYID to GENEID path
            {
                "source_type": "PATHWAYID",
                "target_type": "GENEID",
                "path_steps": json.dumps([
                    {
                        "source": "PATHWAYID",
                        "target": "GENEID",
                        "method": "lookup_genes_in_pathway",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 90,
            },
            
            # HMDB to KEGG direct path via RaMP
            {
                "source_type": "HMDB",
                "target_type": "KEGG",
                "path_steps": json.dumps([
                    {
                        "source": "HMDB",
                        "target": "KEGG",
                        "method": "lookup_direct_mapping",
                        "resources": ["RaMP"]
                    }
                ]),
                "performance_score": 85,
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
        logger.info("RaMP DB mapping paths setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up RaMP DB paths: {e}")
        conn.rollback()
        return False
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Register RaMP DB resource
    resource_id = setup_rampdb_resource()
    
    if resource_id:
        # Setup mapping paths
        setup_rampdb_paths(resource_id)
    else:
        logger.error("Failed to setup RaMP DB resource")
        sys.exit(1)

#!/usr/bin/env python3
"""
Setup mapping paths for RefMet database in the Metamapper system.

This script registers the RefMet resource in the Metamapper database and
defines mapping paths between various metabolite identifiers.
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

def setup_refmet_resource():
    """Register the RefMet resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'RefMet'")
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"RefMet resource already exists with ID {existing[0]}")
            return existing[0]
        
        # Resource configuration
        config = {
            "base_url": "https://www.metabolomicsworkbench.org/rest/refmet",
            "timeout": 30,
            "max_retries": 3
        }
        
        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "RefMet",
                "Reference list of Metabolite nomenclature from Metabolomics Workbench",
                "RefMetClient",
                json.dumps(config),
                "active"
            )
        )
        
        resource_id = cursor.lastrowid
        logger.info(f"Added RefMet resource with ID {resource_id}")
        
        # Commit changes
        conn.commit()
        return resource_id
        
    except Exception as e:
        logger.error(f"Error setting up RefMet resource: {e}")
        conn.rollback()
        return None
    
    finally:
        # Close the database connection
        conn.close()

def setup_refmet_paths(resource_id):
    """Setup mapping paths for RefMet."""
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
            # NAME to REFMET direct path
            {
                "source_type": "NAME",
                "target_type": "REFMET",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "REFMET",
                        "method": "search_by_name",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 70,
            },
            
            # REFMET to PUBCHEM path
            {
                "source_type": "REFMET",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "REFMET",
                        "target": "PUBCHEM",
                        "method": "extract_property",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 75,
            },
            
            # REFMET to INCHI path
            {
                "source_type": "REFMET",
                "target_type": "INCHI",
                "path_steps": json.dumps([
                    {
                        "source": "REFMET",
                        "target": "INCHI",
                        "method": "extract_property",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 75,
            },
            
            # REFMET to SMILES path
            {
                "source_type": "REFMET",
                "target_type": "SMILES",
                "path_steps": json.dumps([
                    {
                        "source": "REFMET",
                        "target": "SMILES",
                        "method": "extract_property",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 75,
            },
            
            # NAME to PUBCHEM via RefMet
            {
                "source_type": "NAME",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "REFMET",
                        "method": "search_by_name",
                        "resources": ["RefMet"]
                    },
                    {
                        "source": "REFMET",
                        "target": "PUBCHEM",
                        "method": "extract_property",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 60,
            },
            
            # NAME to INCHI via RefMet
            {
                "source_type": "NAME",
                "target_type": "INCHI",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "REFMET",
                        "method": "search_by_name",
                        "resources": ["RefMet"]
                    },
                    {
                        "source": "REFMET",
                        "target": "INCHI",
                        "method": "extract_property",
                        "resources": ["RefMet"]
                    }
                ]),
                "performance_score": 60,
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
        logger.info("RefMet mapping paths setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up RefMet paths: {e}")
        conn.rollback()
        return False
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Register RefMet resource
    resource_id = setup_refmet_resource()
    
    if resource_id:
        # Setup mapping paths
        setup_refmet_paths(resource_id)
    else:
        logger.error("Failed to setup RefMet resource")
        sys.exit(1)

#!/usr/bin/env python3
"""
Setup mapping paths for PubChem database in the Metamapper system.

This script registers the PubChem resource in the Metamapper database and
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

def setup_pubchem_resource():
    """Register the PubChem resource in the metamapper database."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if resource already exists
        cursor.execute("SELECT id FROM resources WHERE name = 'PubChem'")
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"PubChem resource already exists with ID {existing[0]}")
            return existing[0]
        
        # Resource configuration
        config = {
            "base_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
            "timeout": 30,
            "retry_count": 3
        }
        
        # Insert the resource
        cursor.execute(
            """INSERT INTO resources 
               (name, description, client_type, config, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "PubChem",
                "PubChem API for chemical compound information",
                "PubChemClient",
                json.dumps(config),
                "active"
            )
        )
        
        resource_id = cursor.lastrowid
        logger.info(f"Added PubChem resource with ID {resource_id}")
        
        # Commit changes
        conn.commit()
        return resource_id
        
    except Exception as e:
        logger.error(f"Error setting up PubChem resource: {e}")
        conn.rollback()
        return None
    
    finally:
        # Close the database connection
        conn.close()

def setup_pubchem_paths(resource_id):
    """Setup mapping paths for PubChem."""
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
            # NAME to PUBCHEM direct path
            {
                "source_type": "NAME",
                "target_type": "PUBCHEM",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "PUBCHEM",
                        "method": "search_by_name",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 50,
                "description": "Direct search of compound name in PubChem"
            },
            
            # PUBCHEM to INCHI path
            {
                "source_type": "PUBCHEM",
                "target_type": "INCHI",
                "path_steps": json.dumps([
                    {
                        "source": "PUBCHEM",
                        "target": "INCHI",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 80,
                "description": "Extract InChI from PubChem compound"
            },
            
            # PUBCHEM to INCHIKEY path
            {
                "source_type": "PUBCHEM",
                "target_type": "INCHIKEY",
                "path_steps": json.dumps([
                    {
                        "source": "PUBCHEM",
                        "target": "INCHIKEY",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 80,
                "description": "Extract InChIKey from PubChem compound"
            },
            
            # PUBCHEM to SMILES path
            {
                "source_type": "PUBCHEM",
                "target_type": "SMILES",
                "path_steps": json.dumps([
                    {
                        "source": "PUBCHEM",
                        "target": "SMILES",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 80,
                "description": "Extract SMILES from PubChem compound"
            },
            
            # PUBCHEM to FORMULA path
            {
                "source_type": "PUBCHEM",
                "target_type": "FORMULA",
                "path_steps": json.dumps([
                    {
                        "source": "PUBCHEM",
                        "target": "FORMULA",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 70,
                "description": "Extract molecular formula from PubChem compound"
            },
            
            # NAME to INCHI through PubChem
            {
                "source_type": "NAME",
                "target_type": "INCHI",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "PUBCHEM",
                        "method": "search_by_name",
                        "resources": ["PubChem"]
                    },
                    {
                        "source": "PUBCHEM",
                        "target": "INCHI",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 40,
                "description": "Convert NAME to INCHI via PubChem"
            },
            
            # NAME to CHEBI through PubChem
            {
                "source_type": "NAME",
                "target_type": "CHEBI",
                "path_steps": json.dumps([
                    {
                        "source": "NAME",
                        "target": "PUBCHEM",
                        "method": "search_by_name",
                        "resources": ["PubChem"]
                    },
                    {
                        "source": "PUBCHEM",
                        "target": "CHEBI",
                        "method": "extract_property",
                        "resources": ["PubChem"]
                    }
                ]),
                "performance_score": 30,
                "description": "Convert NAME to CHEBI via PubChem"
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
        logger.info("PubChem mapping paths setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up PubChem paths: {e}")
        conn.rollback()
        return False
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # Register PubChem resource
    resource_id = setup_pubchem_resource()
    
    if resource_id:
        # Setup mapping paths
        setup_pubchem_paths(resource_id)
    else:
        logger.error("Failed to setup PubChem resource")
        sys.exit(1)

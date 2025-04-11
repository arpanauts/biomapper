#!/usr/bin/env python3
"""
Fix resources in the Metamapper database:
1. Remove duplicate PubChem resource (ID 9)
2. Standardize client_type formatting
"""

import sqlite3
import json
import logging
import sys
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from biomapper.mapping.metadata.config import get_metadata_db_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def remove_duplicate_pubchem():
    """Remove the duplicate PubChem resource (ID 9)."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First check if both resources exist
        cursor.execute("SELECT id, name FROM resources WHERE id IN (6, 9)")
        resources = cursor.fetchall()
        resource_ids = [r[0] for r in resources]
        
        if 9 not in resource_ids:
            logger.info("Resource ID 9 not found - no action needed")
            return
            
        # Before removing, check if any mapping paths are using resource ID 9
        cursor.execute(
            """SELECT id, source_type, target_type, path_steps FROM mapping_paths
               WHERE path_steps LIKE '%pubchem_api%' OR path_steps LIKE '%PubChem API%'"""
        )
        affected_paths = cursor.fetchall()
        
        if affected_paths:
            logger.info(f"Found {len(affected_paths)} mapping paths using the duplicate resource")
            
            # Update mapping paths to use the original PubChem resource
            for path_id, src_type, tgt_type, path_steps in affected_paths:
                logger.info(f"Updating mapping path {path_id} ({src_type} -> {tgt_type})")
                
                try:
                    # Parse path steps
                    steps = json.loads(path_steps)
                    updated = False
                    
                    # Replace "pubchem_api" and "PubChem API" with "pubchem" in resources lists
                    for step in steps:
                        if "resources" in step:
                            new_resources = []
                            for res in step["resources"]:
                                if res.lower() in ("pubchem_api", "pubchem api"):
                                    new_resources.append("pubchem")
                                    updated = True
                                else:
                                    new_resources.append(res)
                            step["resources"] = new_resources
                    
                    if updated:
                        # Update the mapping path
                        cursor.execute(
                            "UPDATE mapping_paths SET path_steps = ? WHERE id = ?",
                            (json.dumps(steps), path_id)
                        )
                        logger.info(f"  Updated path steps for path ID {path_id}")
                except Exception as e:
                    logger.error(f"Error updating mapping path {path_id}: {e}")
        
        # Now remove the duplicate resource
        cursor.execute("DELETE FROM resources WHERE id = 9")
        logger.info(f"Removed duplicate PubChem resource (ID 9)")
        
        # Commit changes
        conn.commit()
    
    finally:
        # Close the database connection
        conn.close()

def standardize_client_types():
    """Standardize client_type formatting across resources."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all client_types
        cursor.execute("SELECT id, name, client_type FROM resources")
        resources = cursor.fetchall()
        
        updates = []
        for resource_id, name, client_type in resources:
            # Clean up the client type
            if not client_type:
                continue
                
            # If ends with "Client", keep that format
            if client_type.endswith("Client"):
                # Just ensure the "Client" part is properly capitalized
                if client_type != client_type[:-6] + "Client":
                    new_client_type = client_type[:-6] + "Client"
                    updates.append((resource_id, client_type, new_client_type))
            
            # If just has the resource name without "Client"
            elif "_" in client_type or client_type.lower() == client_type:
                # Extract the base name
                base_name = client_type.replace("_client", "").replace("_api", "")
                
                # Handle special cases
                if base_name.lower() == "chebi":
                    new_client_type = "ChEBIClient"
                elif base_name.lower() == "pubchem":
                    new_client_type = "PubChemClient"
                elif base_name.lower() == "kegg":
                    new_client_type = "KEGGClient"
                elif base_name.lower() == "arango" or base_name.lower() == "arangodb":
                    new_client_type = "ArangoDBClient"
                elif base_name.lower() == "csv":
                    new_client_type = "CSVClient"
                else:
                    # Capitalize each word and add Client
                    words = re.split(r'[_\s]+', base_name)
                    new_client_type = ''.join(word.capitalize() for word in words) + "Client"
                
                updates.append((resource_id, client_type, new_client_type))
        
        # Apply updates
        if updates:
            logger.info(f"Found {len(updates)} client_types to update:")
            for resource_id, old_type, new_type in updates:
                logger.info(f"  {old_type} -> {new_type}")
                cursor.execute(
                    "UPDATE resources SET client_type = ? WHERE id = ?",
                    (new_type, resource_id)
                )
            
            conn.commit()
            logger.info("Client types updated successfully")
        else:
            logger.info("All client types are already consistent")
    
    finally:
        # Close the database connection
        conn.close()

def check_resources():
    """Check resources in the database and print information."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all resources
        cursor.execute("SELECT id, name, description, client_type, config, status FROM resources")
        resources = cursor.fetchall()
        
        logger.info(f"Found {len(resources)} resources in the database:")
        
        for resource in resources:
            resource_id, name, description, client_type, config, status = resource
            print(f"\nResource ID: {resource_id}")
            print(f"Name: {name}")
            print(f"Description: {description}")
            print(f"Client Type: {client_type}")
            
            try:
                config_json = json.loads(config) if config else {}
                print(f"Config: {json.dumps(config_json, indent=2)}")
            except:
                print(f"Config: {config}")
                
            print(f"Status: {status}")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # First check current resources
    print("Current Resources:")
    check_resources()
    
    # Remove duplicate PubChem resource
    print("\nRemoving duplicate PubChem resource:")
    remove_duplicate_pubchem()
    
    # Standardize client types
    print("\nStandardizing client types:")
    standardize_client_types()
    
    # Show updated resources
    print("\nUpdated Resources:")
    check_resources()

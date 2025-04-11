#!/usr/bin/env python3
"""
Check the resources table in the Metamapper database and ensure style consistency.
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

def check_duplicates():
    """Check for duplicate resources and suggest how to handle them."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Look for potential duplicates based on similar names
        cursor.execute(
            """SELECT r1.id, r1.name, r1.description, r1.client_type, r2.id, r2.name, r2.description, r2.client_type 
               FROM resources r1 JOIN resources r2 
               ON lower(r1.name) LIKE '%' || lower(substr(r2.name, 1, 4)) || '%'
               AND r1.id != r2.id"""
        )
        duplicates = cursor.fetchall()
        
        if duplicates:
            print("\nPotential duplicate resources detected:")
            for dup in duplicates:
                id1, name1, desc1, type1, id2, name2, desc2, type2 = dup
                print(f"\nPossible Duplicate Set:")
                print(f"  Resource 1: [{id1}] {name1} ({type1})")
                print(f"    {desc1}")
                print(f"  Resource 2: [{id2}] {name2} ({type2})")
                print(f"    {desc2}")
            
            print("\nTo handle duplicates, you can use one of these approaches:")
            print("1. Update mapping paths to consistently use one resource")
            print("2. Merge the resources by combining their configurations")
            print("3. Keep both if they serve different purposes (e.g., different API versions)")
        else:
            print("\nNo potential duplicates found.")
    
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

def fix_resource_names():
    """Fix resource names for consistency."""
    # Get database path
    db_path = get_metadata_db_path()
    logger.info(f"Using database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Style standard: Proper capitalization for UI readability
        # with special cases for known database names
        cursor.execute("SELECT id, name, description FROM resources")
        resources = cursor.fetchall()
        
        # Special case capitalization for well-known databases and terms
        special_cases = {
            'chebi': 'ChEBI',
            'pubchem': 'PubChem',
            'kegg': 'KEGG',
            'hmdb': 'HMDB',
            'refmet': 'RefMet',
            'spoke': 'SPOKE',
            'metabolitescsv': 'Metabolites CSV',
            'unichem': 'UniChem',
            'api': 'API',  # Proper capitalization for API
        }
        
        updates = []
        for resource_id, name, description in resources:
            # Check for name that needs to be standardized
            lower_name = name.lower()
            
            # Check if this is a special case full name match
            if lower_name in special_cases:
                new_name = special_cases[lower_name]
                if name != new_name:
                    updates.append((resource_id, name, new_name))
                continue
                
            # Handle composite names with standard components
            if '_' in name or ' ' in name:
                # Split on both underscores and spaces
                words = re.split(r'[_ ]+', name.lower())
                result_words = []
                
                # Process each word
                for word in words:
                    # Check if the word is a special case
                    if word in special_cases:
                        result_words.append(special_cases[word])
                    elif word.upper() == word and len(word) <= 4:  # Likely an acronym
                        result_words.append(word.upper())
                    else:
                        result_words.append(word.capitalize())
                
                new_name = ' '.join(result_words)
                if name != new_name:
                    updates.append((resource_id, name, new_name))
            # Handle other cases
            elif name.lower() == name or name.title() == name:
                # For fully lowercase or simple title case names that aren't in special cases,
                # just capitalize first letter of each word
                new_name = ' '.join(w.capitalize() for w in name.split())
                if name != new_name:
                    updates.append((resource_id, name, new_name))
        
        # Apply updates if needed
        if updates:
            logger.info(f"Found {len(updates)} resource names to update:")
            for resource_id, old_name, new_name in updates:
                logger.info(f"  {old_name} -> {new_name}")
                cursor.execute(
                    "UPDATE resources SET name = ? WHERE id = ?",
                    (new_name, resource_id)
                )
            
            conn.commit()
            logger.info("Resource names updated successfully")
        else:
            logger.info("All resource names are already consistent")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    # First check current resources
    check_resources()
    
    # Then fix resource names if needed
    if len(sys.argv) > 1:
        if sys.argv[1] == "--fix":
            fix_resource_names()
            # Show updated resources
            print("\nUpdated resources:")
            check_resources()
        elif sys.argv[1] == "--check-duplicates":
            check_duplicates()

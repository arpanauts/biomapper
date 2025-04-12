#!/usr/bin/env python3
"""
Update resources with appropriate entity types in the metamapper database.
This script adds an entity_type column to the resources table and assigns
appropriate entity types to each resource.
"""

import sqlite3
import sys
import json
from pathlib import Path

# Define entity type mappings for existing resources
ENTITY_TYPE_MAPPINGS = {
    "metabolite": [
        "ChEBI", "PubChem", "KEGG", "UniChem", "RefMet", "RaMP-DB", "MetabolitesCSV"
    ],
    "protein": [
        # These will be added in future
    ],
    "gene": [
        # These will be added in future
    ],
    "disease": [
        # These will be added in future
    ],
    "pathway": [
        # These will be added in future
    ],
    "all": [
        "SPOKE"  # SPOKE contains all entity types
    ]
}

# Valid entity types (for constraint checking)
VALID_ENTITY_TYPES = ["metabolite", "protein", "gene", "disease", "pathway", "all"]

# Get database path
db_path = Path('data/metamapper.db')
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Return rows as dictionaries
cursor = conn.cursor()

try:
    # Check if resources table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resources'")
    if not cursor.fetchone():
        print("Resources table does not exist in the database!")
        sys.exit(1)
        
    # Add entity_type column if it doesn't exist
    cursor.execute("PRAGMA table_info(resources)")
    columns = [col['name'] for col in cursor.fetchall()]
    
    if "entity_type" not in columns:
        print("Adding entity_type column to resources table...")
        cursor.execute("ALTER TABLE resources ADD COLUMN entity_type TEXT DEFAULT 'metabolite'")
        print("Column added successfully")
    else:
        print("entity_type column already exists in resources table")
    
    # Add constraint check for valid entity types (SQLite doesn't support ADD CONSTRAINT in ALTER TABLE)
    # Instead, we'll validate values when updating
    
    # Update existing resources with appropriate entity types
    update_count = 0
    for entity_type, resource_names in ENTITY_TYPE_MAPPINGS.items():
        if not resource_names:
            continue
            
        resources_placeholders = ', '.join(['?'] * len(resource_names))
        cursor.execute(
            f"UPDATE resources SET entity_type = ? WHERE name IN ({resources_placeholders})",
            [entity_type] + resource_names
        )
        affected_rows = cursor.rowcount
        update_count += affected_rows
        print(f"Updated {affected_rows} resources with entity_type = '{entity_type}'")
    
    # Verify the updates
    cursor.execute("""
        SELECT id, name, entity_type 
        FROM resources 
        ORDER BY entity_type, name
    """)
    resources = cursor.fetchall()
    
    print("\nCurrent resources with entity types:")
    print("===================================")
    
    current_type = None
    for resource in resources:
        if resource['entity_type'] != current_type:
            current_type = resource['entity_type']
            print(f"\n{current_type.upper()} RESOURCES:")
            
        print(f"  - {resource['name']} (ID: {resource['id']})")
    
    # Check for any resources with NULL entity_type
    cursor.execute("SELECT id, name FROM resources WHERE entity_type IS NULL")
    null_resources = cursor.fetchall()
    
    if null_resources:
        print("\nWARNING: The following resources have NULL entity_type:")
        for resource in null_resources:
            print(f"  - {resource['name']} (ID: {resource['id']})")
        
        # Set default entity_type for any NULL values
        cursor.execute("UPDATE resources SET entity_type = 'metabolite' WHERE entity_type IS NULL")
        print(f"Updated {cursor.rowcount} resources with default entity_type = 'metabolite'")
    
    # Commit changes
    conn.commit()
    print(f"\nEntity type mappings updated successfully ({update_count} resources updated)")
    
except Exception as e:
    print(f"Error updating entity types: {e}")
    conn.rollback()
    sys.exit(1)

finally:
    # Close connection
    conn.close()

print("\nNext steps:")
print("1. Review current property configurations for compatibility with multiple entity types")
print("2. Consider adding entity_type column to property_configs table")
print("3. Update resource verification scripts to consider entity types")

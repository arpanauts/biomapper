#!/usr/bin/env python3
"""
Show property extraction configurations for resources.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Get database path
db_path = Path("data/metamapper.db")
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Use row factory for named columns
cursor = conn.cursor()

# Check if the property_extraction_configs table exists
cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='property_extraction_configs'"
)
if not cursor.fetchone():
    print("Table 'property_extraction_configs' does not exist!")
    print("\nChecking for other tables that might contain property configurations:")
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%property%' OR name LIKE '%config%'"
    )
    tables = cursor.fetchall()
    for table in tables:
        print(f"- {table['name']}")
    sys.exit(1)

# Check the schema of the property_extraction_configs table
cursor.execute("PRAGMA table_info(property_extraction_configs)")
columns = cursor.fetchall()
print("\nColumns in property_extraction_configs table:")
for col in columns:
    print(f"- {col['name']} ({col['type']})")


def show_resource_property_config(resource_name):
    """Show property extraction configurations for a specific resource."""
    # Get resource ID
    cursor.execute("SELECT id FROM resources WHERE name = ?", (resource_name,))
    result = cursor.fetchone()
    if not result:
        print(f"Resource '{resource_name}' not found!")
        return

    resource_id = result["id"]
    print(
        f"\nProperty extraction configurations for {resource_name} (ID: {resource_id}):"
    )
    print("=" * 70)

    # Get property extraction configurations
    cursor.execute(
        """SELECT id, ontology_type, property_name, extraction_method, 
           extraction_pattern, result_type, transform_function, 
           priority, is_active, ns_prefix, ns_uri 
           FROM property_extraction_configs 
           WHERE resource_id = ? 
           ORDER BY priority DESC""",
        (resource_id,),
    )
    configs = cursor.fetchall()

    if not configs:
        print(f"No property extraction configurations found for {resource_name}")
        return

    for config in configs:
        print(f"ID: {config['id']}")
        print(f"Ontology Type: {config['ontology_type']}")
        print(f"Property Name: {config['property_name']}")
        print(f"Extraction Method: {config['extraction_method']}")
        print(f"Extraction Pattern: {config['extraction_pattern']}")
        print(f"Result Type: {config['result_type']}")
        print(f"Transform Function: {config['transform_function']}")
        print(f"Priority: {config['priority']}")
        print(f"Is Active: {config['is_active']}")
        print(f"Namespace Prefix: {config['ns_prefix']}")
        print(f"Namespace URI: {config['ns_uri']}")
        print("-" * 50)


# List all resources
cursor.execute("SELECT id, name FROM resources ORDER BY id")
resources = cursor.fetchall()

print("\nAvailable resources:")
for resource in resources:
    print(f"{resource['id']}: {resource['name']}")

# Ask which resource to show config for
resource_name = input(
    "\nEnter resource name to view configs (or 'all' for all resources): "
)

if resource_name.lower() == "all":
    for resource in resources:
        show_resource_property_config(resource["name"])
else:
    show_resource_property_config(resource_name)

# Close the connection
conn.close()

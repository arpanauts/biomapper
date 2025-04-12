#!/usr/bin/env python3
"""
Update RaMP-DB resource configuration in the metamapper database to use the API client.
"""

import sqlite3
import sys
import json
from pathlib import Path

# Get database path
db_path = Path('data/metamapper.db')
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Define RaMP API configuration based on actual client implementation
ramp_config = {
    "base_url": "https://rampdb.nih.gov/api",
    "timeout": 30
}

# Update RaMP-DB configuration
try:
    # Check if resource exists
    cursor.execute("SELECT id, name, client_type, config FROM resources WHERE name = 'RaMP-DB'")
    resource = cursor.fetchone()
    
    if resource:
        resource_id, name, client_type, current_config_json = resource
        
        # Update resource configuration
        updated_client_type = "RaMPClient"
        
        # Update the resource
        cursor.execute(
            "UPDATE resources SET client_type = ?, config = ? WHERE id = ?",
            (updated_client_type, json.dumps(ramp_config), resource_id)
        )
        print(f"Updated configuration for '{name}' (ID: {resource_id})")
        print(f"Set client_type to '{updated_client_type}'")
        print(f"Updated config to: {json.dumps(ramp_config, indent=2)}")
    else:
        print(f"Resource 'RaMP-DB' not found in database")
    
    # Commit changes
    conn.commit()
    
    # Verify the changes
    cursor.execute("SELECT id, name, description, client_type, config FROM resources WHERE name = 'RaMP-DB'")
    resource = cursor.fetchone()
    
    if resource:
        print("\nUpdated RaMP-DB resource in the database:")
        print("==========================================")
        print(f"ID: {resource[0]}, Name: {resource[1]}")
        print(f"Description: {resource[2]}")
        print(f"Client Type: {resource[3]}")
        try:
            config = json.loads(resource[4]) if resource[4] else {}
            print(f"Configuration: {json.dumps(config, indent=2)}")
        except json.JSONDecodeError:
            print(f"Configuration: {resource[4]} (invalid JSON)")
    
except Exception as e:
    print(f"Error updating RaMP-DB configuration: {e}")
    conn.rollback()

finally:
    # Close connection
    conn.close()

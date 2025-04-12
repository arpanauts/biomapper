#!/usr/bin/env python3
"""
Check the resources currently registered in the metamapper database.
"""

import sqlite3
import sys
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

# Get resources
cursor.execute("SELECT id, name, description, client_type, status FROM resources")
resources = cursor.fetchall()

print("\nResources in the database:")
print("=========================")
for resource in resources:
    print(f"ID: {resource[0]}, Name: {resource[1]}, Type: {resource[3]}, Status: {resource[4]}")
    print(f"Description: {resource[2]}")
    print("-" * 50)

# Check mapping paths for each resource
print("\nMapping paths by resource:")
print("========================")
cursor.execute("SELECT DISTINCT source_type, target_type FROM mapping_paths")
mapping_types = cursor.fetchall()
print(f"Mapping types: {mapping_types}")

# Close connection
conn.close()

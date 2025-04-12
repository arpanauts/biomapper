#!/usr/bin/env python3
"""
Update the name of the RaMP resource to RaMP-DB in the metamapper database.
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

try:
    # Update the name
    cursor.execute("UPDATE resources SET name = 'RaMP-DB' WHERE name = 'RaMP'")
    
    if cursor.rowcount > 0:
        print(f"Updated resource name from 'RaMP' to 'RaMP-DB'")
    else:
        print("No resource with name 'RaMP' found")
    
    # Commit changes
    conn.commit()
    
    # Verify the change
    cursor.execute("SELECT id, name, description FROM resources WHERE name = 'RaMP-DB'")
    resource = cursor.fetchone()
    
    if resource:
        print(f"Resource ID {resource[0]} is now named '{resource[1]}': {resource[2]}")

except Exception as e:
    print(f"Error updating resource name: {e}")
    conn.rollback()

finally:
    # Close connection
    conn.close()

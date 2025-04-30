#!/usr/bin/env python3
"""
Check the schema of the mapping_paths table in the metamapper database.
"""

import sqlite3
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
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(mapping_paths)")
columns = cursor.fetchall()
print("\nColumns in mapping_paths table:")
for column in columns:
    print(f"  {column}")

# Check if there are any rows
cursor.execute("SELECT COUNT(*) FROM mapping_paths")
count = cursor.fetchone()[0]
print(f"\nTotal rows in mapping_paths table: {count}")

# Get a sample row
if count > 0:
    cursor.execute("SELECT * FROM mapping_paths LIMIT 1")
    row = cursor.fetchone()
    cursor.execute("PRAGMA table_info(mapping_paths)")
    column_names = [info[1] for info in cursor.fetchall()]
    print("\nSample row:")
    for i, value in enumerate(row):
        print(f"  {column_names[i]}: {value}")

# Close connection
conn.close()

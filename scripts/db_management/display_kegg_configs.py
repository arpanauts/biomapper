#!/usr/bin/env python3
"""
Display current KEGG property extraction configurations.
"""

import sqlite3
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get database path
db_path = Path("data/metamapper.db")
if not db_path.exists():
    logger.error(f"Database file {db_path} not found!")
    sys.exit(1)

logger.info(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Use row factory for named columns
cursor = conn.cursor()


def get_resource_id(name):
    """Get resource ID by name."""
    cursor.execute("SELECT id FROM resources WHERE name = ?", (name,))
    result = cursor.fetchone()
    if not result:
        logger.error(f"Resource '{name}' not found!")
        return None
    return result["id"]


def get_kegg_property_configs():
    """Get KEGG property extraction configurations."""
    resource_id = get_resource_id("KEGG")
    if not resource_id:
        return []

    cursor.execute(
        """SELECT id, ontology_type, property_name, extraction_method, 
           extraction_pattern, result_type, transform_function, 
           priority, is_active
           FROM property_extraction_configs 
           WHERE resource_id = ?
           ORDER BY property_name""",
        (resource_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def display_kegg_configs():
    """Display KEGG property extraction configurations."""
    configs = get_kegg_property_configs()

    if not configs:
        logger.error("No KEGG property extraction configurations found!")
        return

    print(f"\nFound {len(configs)} KEGG property extraction configurations:\n")
    print(
        f"{'ID':<5} {'Property Name':<20} {'Method':<15} {'Pattern':<50} {'Active':<8}"
    )
    print("-" * 100)

    for config in configs:
        # Truncate pattern if it's too long
        pattern = config["extraction_pattern"]
        if len(pattern) > 50:
            pattern = pattern[:47] + "..."

        print(
            f"{config['id']:<5} {config['property_name']:<20} {config['extraction_method']:<15} "
            f"{pattern:<50} {'Yes' if config['is_active'] else 'No':<8}"
        )


if __name__ == "__main__":
    try:
        display_kegg_configs()
    except Exception as e:
        logger.error(f"Error displaying KEGG configurations: {str(e)}")
    finally:
        # Close the connection
        conn.close()

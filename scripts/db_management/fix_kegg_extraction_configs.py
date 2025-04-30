#!/usr/bin/env python3
"""
Fix KEGG property extraction configurations to match the actual API responses.
"""

import sqlite3
import sys
import datetime
from pathlib import Path
import logging

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


def update_property_config(config_id, method, pattern, is_active=True):
    """Update a property extraction configuration."""
    now = datetime.datetime.utcnow().isoformat()

    cursor.execute(
        """UPDATE property_extraction_configs 
           SET extraction_method = ?, extraction_pattern = ?, is_active = ?, updated_at = ?
           WHERE id = ?""",
        (method, pattern, is_active, now, config_id),
    )

    logger.info(f"Updated KEGG property extraction config ID {config_id}")
    return cursor.rowcount


def fix_kegg_extractions():
    """Fix KEGG property extraction configurations."""
    configs = get_kegg_property_configs()
    if not configs:
        logger.error("No KEGG property extraction configurations found!")
        return

    # Define correct extraction methods and patterns for KEGG
    # These are based on the actual KEGG text response format
    extraction_configs = {
        "compound_name": {"method": "regex", "pattern": r"^NAME\s+(.+?)(?=;|\n|$)"},
        "formula": {"method": "regex", "pattern": r"^FORMULA\s+(.+?)(?=\n|$)"},
        "exact_mass": {"method": "regex", "pattern": r"^EXACT_MASS\s+(.+?)(?=\n|$)"},
        "mol_weight": {"method": "regex", "pattern": r"^MOL_WEIGHT\s+(.+?)(?=\n|$)"},
        "kegg_id": {"method": "regex", "pattern": r"^ENTRY\s+(\w+)"},
        "pubchem_id": {"method": "regex", "pattern": r"PubChem:\s+(\d+)"},
        "chebi_id": {"method": "regex", "pattern": r"ChEBI:\s+(\d+)"},
        "hmdb_id": {"method": "regex", "pattern": r"HMDB:\s+(HMDB\d+)"},
        "pathway_ids": {"method": "regex_all", "pattern": r"(map\d+)"},
        "smiles": {"method": "regex", "pattern": r"SMILES:\s+(.+?)(?=\n|$)"},
        "inchi": {"method": "regex", "pattern": r"InChI=(.+?)(?=\n|$)"},
    }

    updated_count = 0
    for config in configs:
        property_name = config["property_name"]
        if property_name in extraction_configs:
            new_method = extraction_configs[property_name]["method"]
            new_pattern = extraction_configs[property_name]["pattern"]

            # Check if update is needed
            if (
                config["extraction_method"] != new_method
                or config["extraction_pattern"] != new_pattern
            ):
                updated_count += update_property_config(
                    config["id"], new_method, new_pattern
                )

    conn.commit()
    logger.info(f"Updated {updated_count} KEGG property extraction configurations")


if __name__ == "__main__":
    try:
        fix_kegg_extractions()
        logger.info("KEGG extraction configurations updated successfully")
    except Exception as e:
        logger.error(f"Error updating KEGG extraction configurations: {str(e)}")
    finally:
        # Close the connection
        conn.close()

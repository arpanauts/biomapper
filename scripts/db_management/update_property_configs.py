#!/usr/bin/env python3
"""
Update property_configs table to support entity_types in the metamapper database.
This script adds an entity_type column to the property_configs table and ensures
property extraction configurations are properly associated with their entity types.
"""

import sqlite3
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Valid entity types (for constraint checking)
VALID_ENTITY_TYPES = ["metabolite", "protein", "gene", "disease", "pathway", "all"]

# Default entity type mappings for existing property configurations
# Format: { property_name: entity_type }
DEFAULT_PROPERTY_ENTITY_TYPES = {
    # Metabolite identifiers
    "chebi_id": "metabolite",
    "pubchem_id": "metabolite",
    "kegg_id": "metabolite",
    "hmdb_id": "metabolite",
    "inchi": "metabolite",
    "inchikey": "metabolite",
    "smiles": "metabolite",
    "refmet_id": "metabolite",
    "refmet_name": "metabolite",
    "molecular_formula": "metabolite",
    "molecular_weight": "metabolite",
    "monoisotopic_mass": "metabolite",
    "iupac_name": "metabolite",
    # Protein identifiers (for future use)
    "uniprot_id": "protein",
    "pdb_id": "protein",
    "amino_acid_sequence": "protein",
    "protein_name": "protein",
    # Gene identifiers (for future use)
    "gene_symbol": "gene",
    "ensembl_id": "gene",
    "ncbi_gene_id": "gene",
    # Common properties that could apply to multiple entity types
    "name": "all",
    "synonyms": "all",
    "description": "all",
    "external_ids": "all",
}

# Get database path
db_path = Path("data/metamapper.db")
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Return rows as dictionaries
cursor = conn.cursor()

try:
    # Check if property_configs table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='property_configs'"
    )
    if not cursor.fetchone():
        print("property_configs table does not exist in the database!")
        sys.exit(1)

    # Add entity_type column if it doesn't exist
    cursor.execute("PRAGMA table_info(property_configs)")
    columns = [col["name"] for col in cursor.fetchall()]

    if "entity_type" not in columns:
        print("Adding entity_type column to property_configs table...")
        cursor.execute(
            "ALTER TABLE property_configs ADD COLUMN entity_type TEXT DEFAULT 'metabolite'"
        )
        print("Column added successfully")
    else:
        print("entity_type column already exists in property_configs table")

    # Get all existing property configs
    cursor.execute(
        """
        SELECT pc.id, pc.resource_id, pc.property_name, r.name as resource_name, r.entity_type as resource_entity_type
        FROM property_configs pc
        JOIN resources r ON pc.resource_id = r.id
    """
    )
    property_configs = cursor.fetchall()

    update_count = 0
    for config in property_configs:
        property_name = config["property_name"]
        resource_entity_type = config["resource_entity_type"]

        # Determine appropriate entity_type for this property
        if property_name in DEFAULT_PROPERTY_ENTITY_TYPES:
            property_entity_type = DEFAULT_PROPERTY_ENTITY_TYPES[property_name]
        elif resource_entity_type:
            # If no specific mapping, inherit from resource
            property_entity_type = resource_entity_type
        else:
            # Default fallback
            property_entity_type = "metabolite"

        # Special case for SPOKE - use property-specific entity type
        # For other resources, we could consider using resource_entity_type
        if (
            resource_entity_type == "all"
            and property_name in DEFAULT_PROPERTY_ENTITY_TYPES
        ):
            property_entity_type = DEFAULT_PROPERTY_ENTITY_TYPES[property_name]

        # Update the property_config with the determined entity_type
        cursor.execute(
            "UPDATE property_configs SET entity_type = ? WHERE id = ?",
            (property_entity_type, config["id"]),
        )

        update_count += cursor.rowcount

    # Verify the updates
    cursor.execute(
        """
        SELECT pc.id, pc.property_name, pc.entity_type as property_entity_type, 
               r.name as resource_name, r.entity_type as resource_entity_type
        FROM property_configs pc
        JOIN resources r ON pc.resource_id = r.id
        ORDER BY r.name, pc.property_name
    """
    )
    updated_configs = cursor.fetchall()

    print("\nProperty configurations with entity types:")
    print("=========================================")

    current_resource = None
    for config in updated_configs:
        if config["resource_name"] != current_resource:
            current_resource = config["resource_name"]
            print(
                f"\n{current_resource} (Resource Entity Type: {config['resource_entity_type']}):"
            )

        print(
            f"  - {config['property_name']} (Entity Type: {config['property_entity_type']})"
        )

    # Check for any properties with NULL entity_type
    cursor.execute(
        """
        SELECT id, property_name, resource_id 
        FROM property_configs 
        WHERE entity_type IS NULL
    """
    )
    null_configs = cursor.fetchall()

    if null_configs:
        print("\nWARNING: The following property configs have NULL entity_type:")
        for config in null_configs:
            print(
                f"  - ID: {config['id']}, Property: {config['property_name']}, Resource ID: {config['resource_id']}"
            )

        # Set default entity_type for any NULL values
        cursor.execute(
            "UPDATE property_configs SET entity_type = 'metabolite' WHERE entity_type IS NULL"
        )
        print(
            f"Updated {cursor.rowcount} property configs with default entity_type = 'metabolite'"
        )

    # Commit changes
    conn.commit()
    print(
        f"\nProperty configuration entity types updated successfully ({update_count} configs updated)"
    )

except Exception as e:
    print(f"Error updating property configuration entity types: {e}")
    conn.rollback()
    sys.exit(1)

finally:
    # Close connection
    conn.close()

print("\nNext steps:")
print("1. Review entity-type specific property extraction patterns")
print("2. Consider adding protein-specific resources and property configurations")
print("3. Update verification scripts to test properties by entity type")

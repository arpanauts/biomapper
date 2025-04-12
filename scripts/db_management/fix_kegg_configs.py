#!/usr/bin/env python3
"""
Fix KEGG property extraction configurations to better match actual API responses.
"""

import sqlite3
import sys
import logging
from pathlib import Path
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database path
db_path = Path('data/metamapper.db')

def connect_to_db(db_path):
    """Connect to the database."""
    if not db_path.exists():
        logger.error(f"Database file {db_path} not found!")
        return None
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Use row factory for named columns
    return conn

def get_resource_id(cursor, name):
    """Get resource ID by name."""
    cursor.execute("SELECT id FROM resources WHERE name = ?", (name,))
    result = cursor.fetchone()
    if not result:
        logger.error(f"Resource '{name}' not found!")
        return None
    return result['id']

def get_property_configs(cursor, resource_id):
    """Get property extraction configurations for a resource."""
    cursor.execute(
        """SELECT id, ontology_type, property_name, extraction_method, 
           extraction_pattern, result_type, transform_function, 
           priority, is_active
           FROM property_extraction_configs 
           WHERE resource_id = ?
           ORDER BY property_name""", 
        (resource_id,)
    )
    return [dict(row) for row in cursor.fetchall()]

def update_property_config(cursor, config_id, **kwargs):
    """Update a property extraction configuration."""
    # Build the SET part of the SQL query
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    set_clause += ", updated_at = datetime('now')"
    
    # Build the parameter values
    params = list(kwargs.values())
    params.append(config_id)
    
    cursor.execute(
        f"""UPDATE property_extraction_configs 
           SET {set_clause}
           WHERE id = ?""",
        params
    )
    
    return cursor.rowcount

def get_improved_patterns():
    """Return improved patterns for KEGG property extractions."""
    return {
        "compound_name": {
            "method": "regex",
            "pattern": r"NAME\s+(.*?)(?=;|\n)",
            "description": "Extract first name from NAME field"
        },
        "formula": {
            "method": "regex",
            "pattern": r"FORMULA\s+(.*?)(?=\n[A-Z]+:|$)",
            "description": "Extract chemical formula from FORMULA field"
        },
        "exact_mass": {
            "method": "regex",
            "pattern": r"EXACT_MASS\s+([\d\.]+)",
            "description": "Extract exact mass from EXACT_MASS field"
        },
        "mol_weight": {
            "method": "regex",
            "pattern": r"MOL_WEIGHT\s+([\d\.]+)",
            "description": "Extract molecular weight from MOL_WEIGHT field"
        },
        "kegg_id": {
            "method": "regex",
            "pattern": r"ENTRY\s+(\w+)",
            "description": "Extract KEGG ID from ENTRY field"
        },
        "pubchem_id": {
            "method": "regex",
            "pattern": r"PubChem:\s+(\d+)",
            "description": "Extract PubChem ID from DBLINKS section"
        },
        "chebi_id": {
            "method": "regex",
            "pattern": r"ChEBI:\s+(\d+)",
            "description": "Extract ChEBI ID from DBLINKS section"
        },
        "hmdb_id": {
            "method": "regex",
            "pattern": r"HMDB:\s+(HMDB\d+)",
            "description": "Extract HMDB ID from DBLINKS section (optional, not all compounds have this)"
        },
        "pathway_ids": {
            "method": "regex_all",
            "pattern": r"map\d+",
            "description": "Extract all pathway IDs from PATHWAY section"
        },
        "inchi": {
            "method": "regex",
            "pattern": r"InChI=(.+?)(?=\n|$)",
            "description": "Extract InChI from DB_LINKS section (optional, not all compounds have this)"
        },
        "smiles": {
            "method": "regex",
            "pattern": r"SMILES:\s+(.+?)(?=\n|$)",
            "description": "Extract SMILES from DB_LINKS section (optional, not all compounds have this)"
        }
    }

def fix_kegg_configs(conn, dry_run=True):
    """Fix KEGG property extraction configurations."""
    cursor = conn.cursor()
    
    # Get KEGG resource ID
    kegg_id = get_resource_id(cursor, "KEGG")
    if not kegg_id:
        return
    
    # Get current configurations
    configs = get_property_configs(cursor, kegg_id)
    if not configs:
        logger.error("No KEGG property extraction configurations found!")
        return
    
    # Get improved patterns
    improved_patterns = get_improved_patterns()
    
    # Track the number of updated configurations
    updated_count = 0
    
    # Print current and proposed configurations
    print(f"\nFound {len(configs)} KEGG property extraction configurations:\n")
    print(f"{'ID':<5} {'Property Name':<20} {'Current Pattern':<50} {'Proposed Pattern':<50} {'Update?':<8}")
    print("-" * 135)
    
    for config in configs:
        property_name = config['property_name']
        current_pattern = config['extraction_pattern']
        
        # Check if there's an improved pattern
        if property_name in improved_patterns:
            improved = improved_patterns[property_name]
            proposed_method = improved['method']
            proposed_pattern = improved['pattern']
            description = improved['description']
            
            # Check if the pattern needs to be updated
            needs_update = (current_pattern != proposed_pattern or 
                           config['extraction_method'] != proposed_method)
            
            # Truncate patterns if they're too long
            current_display = current_pattern
            if len(current_display) > 50:
                current_display = current_display[:47] + "..."
                
            proposed_display = proposed_pattern
            if len(proposed_display) > 50:
                proposed_display = proposed_display[:47] + "..."
            
            print(f"{config['id']:<5} {property_name:<20} {current_display:<50} {proposed_display:<50} "
                  f"{'Yes' if needs_update else 'No':<8}")
            
            # Update the configuration if needed and not in dry run mode
            if needs_update and not dry_run:
                rows_updated = update_property_config(
                    cursor, config['id'],
                    extraction_method=proposed_method,
                    extraction_pattern=proposed_pattern
                )
                
                if rows_updated:
                    updated_count += 1
                    logger.info(f"Updated {property_name} pattern: {description}")
        else:
            logger.warning(f"No improved pattern available for {property_name}")
    
    # Commit changes if not in dry run mode
    if not dry_run:
        conn.commit()
        logger.info(f"Updated {updated_count} KEGG property extraction configurations")
    else:
        logger.info("Dry run mode - no changes were made to the database")
    
    logger.info("KEGG extraction configurations updated successfully")

def main():
    parser = argparse.ArgumentParser(description="Fix KEGG property extraction configurations.")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any changes to the database")
    parser.add_argument("--db-path", type=str, default="data/metamapper.db", help="Path to the database")
    args = parser.parse_args()
    
    # Get database path
    db_path = Path(args.db_path)
    
    # Connect to the database
    conn = connect_to_db(db_path)
    if not conn:
        return
    
    try:
        # Fix KEGG configurations
        fix_kegg_configs(conn, args.dry_run)
    except Exception as e:
        logger.error(f"Error fixing KEGG configurations: {str(e)}")
    finally:
        # Close the connection
        conn.close()

if __name__ == "__main__":
    main()

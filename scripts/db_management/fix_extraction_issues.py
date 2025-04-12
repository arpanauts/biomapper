#!/usr/bin/env python3
"""
Fix specific issues with property extraction configurations
and correct JSON path patterns that weren't working.
"""

import sqlite3
import json
import sys
import datetime
from pathlib import Path

# Get database path
db_path = Path('data/metamapper.db')
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Use row factory for named columns
cursor = conn.cursor()

def get_resource_id(name):
    """Get resource ID by name."""
    cursor.execute("SELECT id FROM resources WHERE name = ?", (name,))
    result = cursor.fetchone()
    if not result:
        print(f"Resource '{name}' not found!")
        return None
    return result['id']

def get_property_configs(resource_id):
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

def update_property_config(config_id, extraction_pattern, is_active=True):
    """Update a property extraction configuration."""
    now = datetime.datetime.utcnow().isoformat()
    
    cursor.execute(
        """UPDATE property_extraction_configs 
           SET extraction_pattern = ?, is_active = ?, updated_at = ?
           WHERE id = ?""",
        (extraction_pattern, is_active, now, config_id)
    )
    
    print(f"Updated property extraction config ID {config_id}")
    return cursor.rowcount

# Fix UniChem patterns regression
def fix_unichem_patterns():
    """Fix UniChem property extraction patterns."""
    resource_id = get_resource_id("UniChem")
    if not resource_id:
        return
    
    print(f"\nFixing UniChem property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # The issue with UniChem is that the response structure depends on whether we're 
    # using get_compound_info_by_src_id (returns a dict with chembl_ids, pubchem_ids, etc.),
    # or we're dealing with the individual entries returned (which have src_id and src_compound_id).
    # Let's fix the patterns to match the actual response structure:
    
    patterns = {
        "chembl_ids": "$.chembl_ids",  # array of IDs
        "chebi_ids": "$.chebi_ids",    # array of IDs
        "pubchem_ids": "$.pubchem_ids", # array of IDs
        "kegg_ids": "$.kegg_ids",      # array of IDs
        "hmdb_ids": "$.hmdb_ids",      # array of IDs
        "drugbank_ids": "$.drugbank_ids", # array of IDs
        "unichem_id": "$[0].uci",      # first item's UCI
        "src_compound_id": "$[0].src_compound_id", # first item's src_compound_id
        "src_id": "$[0].src_id"        # first item's src_id
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            if new_pattern != config['extraction_pattern']:
                updated += update_property_config(config['id'], new_pattern)
    
    conn.commit()
    print(f"Updated {updated} UniChem property extraction patterns")

# Fix KEGG patterns that weren't working
def fix_kegg_patterns():
    """Fix KEGG property extraction patterns."""
    resource_id = get_resource_id("KEGG")
    if not resource_id:
        return
    
    print(f"\nFixing KEGG property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Adjust patterns to better match KEGG text response format
    patterns = {
        "compound_name": r"^NAME\s+(.+?)$",
        "formula": r"^FORMULA\s+(.+?)$",
        "exact_mass": r"^EXACT_MASS\s+(.+?)$",
        "mol_weight": r"^MOL_WEIGHT\s+(.+?)$",
        "kegg_id": r"^ENTRY\s+(\w+)",
        "pubchem_id": r"^DBLINKS.+?PubChem:\s+(\d+)",
        "chebi_id": r"^DBLINKS.+?ChEBI:\s+(\d+)",
        "hmdb_id": r"^DBLINKS.+?HMDB:\s+(HMDB\d+)",
        "pathway_ids": r"^PATHWAY\s+(.+?)$",
        "smiles": r"SMILES:\s+(.+?)$",
        "inchi": r"InChI=(.+?)$"
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            # For KEGG, we need to change the extraction method to 'multiline_regex'
            cursor.execute(
                """UPDATE property_extraction_configs 
                   SET extraction_pattern = ?, extraction_method = ?, updated_at = ?
                   WHERE id = ?""",
                (new_pattern, "multiline_regex", datetime.datetime.utcnow().isoformat(), config['id'])
            )
            print(f"Updated KEGG property extraction config ID {config['id']}")
            updated += 1
    
    conn.commit()
    print(f"Updated {updated} KEGG property extraction patterns")

# Now let's fine-tune the PubChem patterns for the remaining issues
def fix_pubchem_patterns():
    """Fix remaining PubChem property extraction patterns."""
    resource_id = get_resource_id("PubChem")
    if not resource_id:
        return
    
    print(f"\nFixing PubChem property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Adjust patterns for PubChem results
    patterns = {
        # These fields need special handling because they might be nested differently
        "hmdb_id": "$..xrefs.hmdb",
        "chebi_id": "$..xrefs.chebi",
        "kegg_id": "$..xrefs.kegg",
        "synonyms": "$..synonyms[*]"
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            if new_pattern != config['extraction_pattern']:
                updated += update_property_config(config['id'], new_pattern)
    
    conn.commit()
    print(f"Updated {updated} PubChem property extraction patterns")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix specific issues with property extraction configurations")
    parser.add_argument("--all", action="store_true", help="Fix all issues")
    parser.add_argument("--unichem", action="store_true", help="Fix UniChem patterns")
    parser.add_argument("--kegg", action="store_true", help="Fix KEGG patterns")
    parser.add_argument("--pubchem", action="store_true", help="Fix PubChem patterns")
    args = parser.parse_args()
    
    if args.all or not any([args.unichem, args.kegg, args.pubchem]):
        fix_unichem_patterns()
        fix_kegg_patterns()
        fix_pubchem_patterns()
    else:
        if args.unichem:
            fix_unichem_patterns()
        if args.kegg:
            fix_kegg_patterns()
        if args.pubchem:
            fix_pubchem_patterns()
    
    # Close the connection
    conn.close()
    print("\nAll fixes applied successfully")

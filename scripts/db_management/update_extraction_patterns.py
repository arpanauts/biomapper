#!/usr/bin/env python3
"""
Update property extraction configurations based on actual API responses.
"""

import sqlite3
import json
import sys
import datetime
from pathlib import Path
import time

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

# PubChem patterns need to be updated to match the actual API response
def update_pubchem_patterns():
    """Update PubChem property extraction patterns."""
    resource_id = get_resource_id("PubChem")
    if not resource_id:
        return
    
    print(f"\nUpdating PubChem property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Define accurate JSON path patterns for PubChem results
    patterns = {
        "compound_name": "$.name",
        "description": "$.name",  # PubChem doesn't have a direct description field in our client response
        "formula": "$.formula",
        "molecular_weight": "$.mass",
        "inchi": "$.inchi",
        "inchikey": "$.inchikey",
        "smiles": "$.smiles",
        "pubchem_id": "$.pubchem_cid",
        "hmdb_id": "$.xrefs.hmdb",
        "chebi_id": "$.xrefs.chebi",
        "kegg_id": "$.xrefs.kegg",
        # PubChem client doesn't return synonyms in a standard way in our implementation
        "synonyms": "$.synonyms"
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

# KEGG patterns need to be updated to match the actual API response
def update_kegg_patterns():
    """Update KEGG property extraction patterns."""
    resource_id = get_resource_id("KEGG")
    if not resource_id:
        return
    
    print(f"\nUpdating KEGG property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Define accurate regex patterns for KEGG results
    patterns = {
        "compound_name": r"NAME\s+(.*?)(?=\n[A-Z]+:|\n$)",
        "formula": r"FORMULA\s+(.*?)(?=\n[A-Z]+:|\n$)",
        "exact_mass": r"EXACT_MASS\s+([\d\.]+)",
        "mol_weight": r"MOL_WEIGHT\s+([\d\.]+)",
        "kegg_id": r"^ENTRY\s+(\w+)",
        "pubchem_id": r"DBLINKS\s+PubChem:\s+(\d+)",
        "chebi_id": r"DBLINKS\s+ChEBI:\s+(\d+)",
        "hmdb_id": r"DBLINKS\s+HMDB:\s+(HMDB\d+)",
        "pathway_ids": r"PATHWAY\s+(.*?)(?=\n[A-Z]+:|\n$)",
        "smiles": r"DBLINKS\s+PubChem:\s+\d+\s+STRUCTURE\s.*\s*.*SMILES:\s+(.*?)$",
        "inchi": r"DBLINKS\s+PubChem:\s+\d+\s+STRUCTURE\s.*\s*.*InChI:\s+(.*?)$"
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            if new_pattern != config['extraction_pattern']:
                updated += update_property_config(config['id'], new_pattern)
    
    conn.commit()
    print(f"Updated {updated} KEGG property extraction patterns")

# UniChem patterns need to be updated to match the actual API response
def update_unichem_patterns():
    """Update UniChem property extraction patterns."""
    resource_id = get_resource_id("UniChem")
    if not resource_id:
        return
    
    print(f"\nUpdating UniChem property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Define accurate JSON path patterns for UniChem results
    patterns = {
        "chembl_ids": "$[?(@.src_id==1)].src_compound_id",
        "chebi_ids": "$[?(@.src_id==7)].src_compound_id",
        "pubchem_ids": "$[?(@.src_id==22)].src_compound_id",
        "kegg_ids": "$[?(@.src_id==6)].src_compound_id",
        "hmdb_ids": "$[?(@.src_id==2)].src_compound_id",
        "drugbank_ids": "$[?(@.src_id==3)].src_compound_id",
        "unichem_id": "$.uci",
        "src_compound_id": "$.src_compound_id",
        "src_id": "$.src_id"
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

# RefMet patterns need to be updated to match the actual API response
def update_refmet_patterns():
    """Update RefMet property extraction patterns."""
    resource_id = get_resource_id("RefMet")
    if not resource_id:
        return
    
    print(f"\nUpdating RefMet property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Define accurate JSON path patterns for RefMet results
    patterns = {
        "refmet_id": "$.refmet_id",
        "name": "$.name",
        "formula": "$.formula",
        "exact_mass": "$.exact_mass",
        "inchikey": "$.inchikey",
        "pubchem_id": "$.pubchem_id",
        "chebi_id": "$.chebi_id",
        "hmdb_id": "$.hmdb_id",
        "kegg_id": "$.kegg_id"
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            if new_pattern != config['extraction_pattern']:
                updated += update_property_config(config['id'], new_pattern)
    
    conn.commit()
    print(f"Updated {updated} RefMet property extraction patterns")

# RaMP-DB patterns need to be updated to match the actual API response
def update_rampdb_patterns():
    """Update RaMP-DB property extraction patterns."""
    resource_id = get_resource_id("RaMP-DB")
    if not resource_id:
        return
    
    print(f"\nUpdating RaMP-DB property extraction patterns (Resource ID: {resource_id})")
    configs = get_property_configs(resource_id)
    
    # Define accurate JSON path patterns for RaMP-DB results
    # These need to match the actual structure from the RaMP-DB API
    patterns = {
        "metabolite_id": "$.metaboliteID",
        "metabolite_name": "$.metaboliteName",
        "hmdb_ids": "$.hmdbIDs",
        "kegg_ids": "$.keggIDs",
        "pubchem_ids": "$.pubchemIDs",
        "chebi_ids": "$.chebiIDs",
        "pathway_id": "$.pathwayID",
        "pathway_name": "$.pathwayName",
        "pathway_source": "$.pathwaySource",
        "total_pathways": "$.stats.totalPathways",
        "pathways_by_source": "$.stats.pathwaysBySource",
        "unique_pathway_names": "$.stats.uniquePathwayNames",
        "pathway_sources": "$.stats.pathwaySources"
    }
    
    updated = 0
    for config in configs:
        property_name = config['property_name']
        if property_name in patterns:
            new_pattern = patterns[property_name]
            if new_pattern != config['extraction_pattern']:
                updated += update_property_config(config['id'], new_pattern)
    
    conn.commit()
    print(f"Updated {updated} RaMP-DB property extraction patterns")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update property extraction patterns for resources")
    parser.add_argument("--all", action="store_true", help="Update patterns for all resources")
    parser.add_argument("--pubchem", action="store_true", help="Update PubChem patterns")
    parser.add_argument("--kegg", action="store_true", help="Update KEGG patterns")
    parser.add_argument("--unichem", action="store_true", help="Update UniChem patterns")
    parser.add_argument("--refmet", action="store_true", help="Update RefMet patterns")
    parser.add_argument("--rampdb", action="store_true", help="Update RaMP-DB patterns")
    args = parser.parse_args()
    
    if args.all or not any([args.pubchem, args.kegg, args.unichem, args.refmet, args.rampdb]):
        update_pubchem_patterns()
        update_kegg_patterns()
        update_unichem_patterns()
        update_refmet_patterns()
        update_rampdb_patterns()
    else:
        if args.pubchem:
            update_pubchem_patterns()
        if args.kegg:
            update_kegg_patterns()
        if args.unichem:
            update_unichem_patterns()
        if args.refmet:
            update_refmet_patterns()
        if args.rampdb:
            update_rampdb_patterns()
    
    # Close the connection
    conn.close()
    print("\nAll property extraction patterns updated successfully")

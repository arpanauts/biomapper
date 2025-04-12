#!/usr/bin/env python3
"""
Set up property extraction configurations for various resources in the metamapper database.
"""

import sqlite3
import json
import sys
from pathlib import Path
import datetime

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

def check_existing_configs(resource_id):
    """Check if configurations already exist for a resource."""
    cursor.execute(
        "SELECT COUNT(*) as count FROM property_extraction_configs WHERE resource_id = ?", 
        (resource_id,)
    )
    result = cursor.fetchone()
    return result['count'] > 0

def add_property_config(
    resource_id, 
    ontology_type, 
    property_name, 
    extraction_method, 
    extraction_pattern, 
    result_type, 
    transform_function=None, 
    priority=10, 
    is_active=True, 
    ns_prefix=None, 
    ns_uri=None
):
    """Add a property extraction configuration."""
    now = datetime.datetime.utcnow().isoformat()
    
    cursor.execute(
        """INSERT INTO property_extraction_configs 
           (resource_id, ontology_type, property_name, extraction_method, 
            extraction_pattern, result_type, transform_function, 
            priority, is_active, created_at, updated_at, ns_prefix, ns_uri)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (resource_id, ontology_type, property_name, extraction_method, 
         extraction_pattern, result_type, transform_function, 
         priority, is_active, now, now, ns_prefix, ns_uri)
    )
    
    print(f"Added property config for {ontology_type}.{property_name}")
    return cursor.lastrowid

def setup_pubchem_configs(overwrite=False):
    """Set up property extraction configurations for PubChem."""
    resource_id = get_resource_id("PubChem")
    if not resource_id:
        return
    
    if check_existing_configs(resource_id) and not overwrite:
        print(f"PubChem already has property extraction configurations. Use --overwrite to replace them.")
        return
    
    if overwrite:
        cursor.execute("DELETE FROM property_extraction_configs WHERE resource_id = ?", (resource_id,))
        print("Deleted existing PubChem property configurations")
    
    # Add PubChem property configurations
    configs = [
        # Basic information
        ("PUBCHEM", "compound_name", "json_path", "$.Record.RecordTitle", "string"),
        ("PUBCHEM", "description", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Computed Descriptors')].Information[?(@.Name=='IUPAC Name')].StringValue", "string"),
        ("PUBCHEM", "synonyms", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Synonyms')].Section[?(@.TOCHeading=='Depositor-Supplied Synonyms')].Information[?(@.Name=='Depositor-Supplied Synonyms')].StringValueList", "list"),
        
        # Chemical properties
        ("PUBCHEM", "formula", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Molecular Formula')].Information[?(@.Name=='Molecular Formula')].StringValue", "string"),
        ("PUBCHEM", "molecular_weight", "json_path", "$.Record.Section[?(@.TOCHeading=='Chemical and Physical Properties')].Section[?(@.TOCHeading=='Computed Properties')].Information[?(@.Name=='Molecular Weight')].NumValue", "number"),
        ("PUBCHEM", "inchi", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Computed Descriptors')].Information[?(@.Name=='InChI')].StringValue", "string"),
        ("PUBCHEM", "inchikey", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Computed Descriptors')].Information[?(@.Name=='InChIKey')].StringValue", "string"),
        ("PUBCHEM", "smiles", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Computed Descriptors')].Information[?(@.Name=='Canonical SMILES')].StringValue", "string"),
        
        # Database identifiers
        ("PUBCHEM", "pubchem_id", "json_path", "$.Record.RecordNumber", "string", "str"),
        ("PUBCHEM", "hmdb_id", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Other Identifiers')].Information[?(@.Name=='HMDB')].StringValue", "string"),
        ("PUBCHEM", "kegg_id", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Other Identifiers')].Information[?(@.Name=='KEGG')].StringValue", "string"),
        ("PUBCHEM", "chebi_id", "json_path", "$.Record.Section[?(@.TOCHeading=='Names and Identifiers')].Section[?(@.TOCHeading=='Other Identifiers')].Information[?(@.Name=='ChEBI')].StringValue", "string"),
    ]
    
    for config in configs:
        if len(config) == 5:
            ontology_type, property_name, extraction_method, extraction_pattern, result_type = config
            transform_function = None
        else:
            ontology_type, property_name, extraction_method, extraction_pattern, result_type, transform_function = config
            
        add_property_config(
            resource_id=resource_id,
            ontology_type=ontology_type,
            property_name=property_name,
            extraction_method=extraction_method,
            extraction_pattern=extraction_pattern,
            result_type=result_type,
            transform_function=transform_function
        )
    
    conn.commit()
    print(f"Added {len(configs)} property extraction configurations for PubChem")

def setup_kegg_configs(overwrite=False):
    """Set up property extraction configurations for KEGG."""
    resource_id = get_resource_id("KEGG")
    if not resource_id:
        return
    
    if check_existing_configs(resource_id) and not overwrite:
        print(f"KEGG already has property extraction configurations. Use --overwrite to replace them.")
        return
    
    if overwrite:
        cursor.execute("DELETE FROM property_extraction_configs WHERE resource_id = ?", (resource_id,))
        print("Deleted existing KEGG property configurations")
    
    # Add KEGG property configurations
    configs = [
        # Basic information
        ("KEGG", "compound_name", "regex", r"NAME\s+(.*?)(?=\n\w+:|\n$)", "string"),
        ("KEGG", "formula", "regex", r"FORMULA\s+(.*?)(?=\n\w+:|\n$)", "string"),
        ("KEGG", "exact_mass", "regex", r"EXACT_MASS\s+(.*?)(?=\n\w+:|\n$)", "number"),
        ("KEGG", "mol_weight", "regex", r"MOL_WEIGHT\s+(.*?)(?=\n\w+:|\n$)", "number"),
        
        # Database identifiers
        ("KEGG", "kegg_id", "regex", r"ENTRY\s+(\w+)\s+", "string"),
        ("KEGG", "pubchem_id", "regex", r"DBLINKS\s+PubChem:\s+(\d+)(?=\n|$)", "string"),
        ("KEGG", "chebi_id", "regex", r"DBLINKS\s+ChEBI:\s+(\d+)(?=\n|$)", "string", "lambda x: f'CHEBI:{x}'"),
        ("KEGG", "hmdb_id", "regex", r"DBLINKS\s+HMDB:\s+(HMDB\d+)(?=\n|$)", "string"),
        
        # Pathways
        ("KEGG", "pathway_ids", "regex", r"PATHWAY\s+(.*?)(?=\n\w+:|\n$)", "string", "lambda x: x.split('\\n')"),
        
        # Structure representations
        ("KEGG", "smiles", "regex", r"db:pubchem-substance\s+exact_mass\s+\d+\.\d+\s+smiles\s+(.*?)(?=\n)", "string"),
        ("KEGG", "inchi", "regex", r"db:pubchem-substance\s+inchi\s+(.*?)(?=\n)", "string"),
    ]
    
    for config in configs:
        if len(config) == 5:
            ontology_type, property_name, extraction_method, extraction_pattern, result_type = config
            transform_function = None
        else:
            ontology_type, property_name, extraction_method, extraction_pattern, result_type, transform_function = config
            
        add_property_config(
            resource_id=resource_id,
            ontology_type=ontology_type,
            property_name=property_name,
            extraction_method=extraction_method,
            extraction_pattern=extraction_pattern,
            result_type=result_type,
            transform_function=transform_function
        )
    
    conn.commit()
    print(f"Added {len(configs)} property extraction configurations for KEGG")

def setup_unichem_configs(overwrite=False):
    """Set up property extraction configurations for UniChem."""
    resource_id = get_resource_id("UniChem")
    if not resource_id:
        return
    
    if check_existing_configs(resource_id) and not overwrite:
        print(f"UniChem already has property extraction configurations. Use --overwrite to replace them.")
        return
    
    if overwrite:
        cursor.execute("DELETE FROM property_extraction_configs WHERE resource_id = ?", (resource_id,))
        print("Deleted existing UniChem property configurations")
    
    # Add UniChem property configurations
    configs = [
        # Identifier mappings
        ("UNICHEM", "chembl_ids", "json_path", "$.chembl_ids", "list"),
        ("UNICHEM", "chebi_ids", "json_path", "$.chebi_ids", "list"),
        ("UNICHEM", "pubchem_ids", "json_path", "$.pubchem_ids", "list"),
        ("UNICHEM", "kegg_ids", "json_path", "$.kegg_ids", "list"),
        ("UNICHEM", "hmdb_ids", "json_path", "$.hmdb_ids", "list"),
        ("UNICHEM", "drugbank_ids", "json_path", "$.drugbank_ids", "list"),
        
        # Search results
        ("UNICHEM", "unichem_id", "json_path", "$.uci", "string"),
        ("UNICHEM", "src_compound_id", "json_path", "$.src_compound_id", "string"),
        ("UNICHEM", "src_id", "json_path", "$.src_id", "string"),
    ]
    
    for config in configs:
        ontology_type, property_name, extraction_method, extraction_pattern, result_type = config
            
        add_property_config(
            resource_id=resource_id,
            ontology_type=ontology_type,
            property_name=property_name,
            extraction_method=extraction_method,
            extraction_pattern=extraction_pattern,
            result_type=result_type
        )
    
    conn.commit()
    print(f"Added {len(configs)} property extraction configurations for UniChem")

def setup_refmet_configs(overwrite=False):
    """Set up property extraction configurations for RefMet."""
    resource_id = get_resource_id("RefMet")
    if not resource_id:
        return
    
    if check_existing_configs(resource_id) and not overwrite:
        print(f"RefMet already has property extraction configurations. Use --overwrite to replace them.")
        return
    
    if overwrite:
        cursor.execute("DELETE FROM property_extraction_configs WHERE resource_id = ?", (resource_id,))
        print("Deleted existing RefMet property configurations")
    
    # Add RefMet property configurations
    configs = [
        # Basic information
        ("REFMET", "refmet_id", "json_path", "$.refmet_id", "string"),
        ("REFMET", "name", "json_path", "$.name", "string"),
        ("REFMET", "formula", "json_path", "$.formula", "string"),
        ("REFMET", "exact_mass", "json_path", "$.exact_mass", "string"),
        
        # Identifiers
        ("REFMET", "inchikey", "json_path", "$.inchikey", "string"),
        ("REFMET", "pubchem_id", "json_path", "$.pubchem_id", "string"),
        ("REFMET", "chebi_id", "json_path", "$.chebi_id", "string"),
        ("REFMET", "hmdb_id", "json_path", "$.hmdb_id", "string"),
        ("REFMET", "kegg_id", "json_path", "$.kegg_id", "string"),
    ]
    
    for config in configs:
        ontology_type, property_name, extraction_method, extraction_pattern, result_type = config
            
        add_property_config(
            resource_id=resource_id,
            ontology_type=ontology_type,
            property_name=property_name,
            extraction_method=extraction_method,
            extraction_pattern=extraction_pattern,
            result_type=result_type
        )
    
    conn.commit()
    print(f"Added {len(configs)} property extraction configurations for RefMet")

def setup_rampdb_configs(overwrite=False):
    """Set up property extraction configurations for RaMP-DB."""
    resource_id = get_resource_id("RaMP-DB")
    if not resource_id:
        return
    
    if check_existing_configs(resource_id) and not overwrite:
        print(f"RaMP-DB already has property extraction configurations. Use --overwrite to replace them.")
        return
    
    if overwrite:
        cursor.execute("DELETE FROM property_extraction_configs WHERE resource_id = ?", (resource_id,))
        print("Deleted existing RaMP-DB property configurations")
    
    # Add RaMP-DB property configurations
    configs = [
        # Metabolite information
        ("RAMPDB", "metabolite_id", "json_path", "$.id", "string"),
        ("RAMPDB", "metabolite_name", "json_path", "$.metabolite_name", "string"),
        ("RAMPDB", "hmdb_ids", "json_path", "$.hmdb_ids", "list"),
        ("RAMPDB", "kegg_ids", "json_path", "$.kegg_ids", "list"),
        ("RAMPDB", "pubchem_ids", "json_path", "$.pubchem_ids", "list"),
        ("RAMPDB", "chebi_ids", "json_path", "$.chebi_ids", "list"),
        
        # Pathway information
        ("RAMPDB", "pathway_id", "json_path", "$.pathway_id", "string"),
        ("RAMPDB", "pathway_name", "json_path", "$.pathway_name", "string"),
        ("RAMPDB", "pathway_source", "json_path", "$.pathway_source", "string"),
        
        # Pathway statistics
        ("RAMPDB", "total_pathways", "json_path", "$.total_pathways", "number"),
        ("RAMPDB", "pathways_by_source", "json_path", "$.pathways_by_source", "dict"),
        ("RAMPDB", "unique_pathway_names", "json_path", "$.unique_pathway_names", "list"),
        ("RAMPDB", "pathway_sources", "json_path", "$.pathway_sources", "list"),
    ]
    
    for config in configs:
        ontology_type, property_name, extraction_method, extraction_pattern, result_type = config
            
        add_property_config(
            resource_id=resource_id,
            ontology_type=ontology_type,
            property_name=property_name,
            extraction_method=extraction_method,
            extraction_pattern=extraction_pattern,
            result_type=result_type
        )
    
    conn.commit()
    print(f"Added {len(configs)} property extraction configurations for RaMP-DB")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up property extraction configurations for resources")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing property configurations")
    parser.add_argument("--resource", type=str, help="Only configure a specific resource (by name)")
    args = parser.parse_args()
    
    # Set up property extraction configurations
    if args.resource:
        if args.resource.upper() == "PUBCHEM":
            setup_pubchem_configs(args.overwrite)
        elif args.resource.upper() == "KEGG":
            setup_kegg_configs(args.overwrite)
        elif args.resource.upper() == "UNICHEM":
            setup_unichem_configs(args.overwrite)
        elif args.resource.upper() == "REFMET":
            setup_refmet_configs(args.overwrite)
        elif args.resource.upper() == "RAMPDB" or args.resource.upper() == "RAMP-DB":
            setup_rampdb_configs(args.overwrite)
        else:
            print(f"Unknown resource: {args.resource}")
    else:
        # Set up configurations for all resources
        setup_pubchem_configs(args.overwrite)
        setup_kegg_configs(args.overwrite)
        setup_unichem_configs(args.overwrite)
        setup_refmet_configs(args.overwrite)
        setup_rampdb_configs(args.overwrite)
    
    print("\nProperty extraction configuration setup complete!")

#!/usr/bin/env python3
"""
Update resource configurations in the metamapper database based on client implementations.
"""

import sqlite3
import sys
import json
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

# Define resource configurations based on client implementations
resource_configs = {
    "ChEBI": {
        "base_url": "https://www.ebi.ac.uk/ols/api",
        "timeout": 30,
        "description": "Chemical Entities of Biological Interest database (EBI)",
        "client_type": "ChEBIClient"
    },
    "PubChem": {
        "base_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        "timeout": 30,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "rate_limit_wait": 0.2,
        "description": "NCBI PubChem database",
        "client_type": "PubChemClient"
    },
    "KEGG": {
        "base_url": "https://rest.kegg.jp",
        "timeout": 30,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "description": "KEGG API for metabolic pathway and compound information",
        "client_type": "KEGGClient"
    },
    "UniChem": {
        "base_url": "https://www.ebi.ac.uk/unichem/rest",
        "timeout": 30,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "description": "EBI's compound identifier mapping service",
        "client_type": "UniChemClient"
    },
    "RefMet": {
        "base_url": "https://www.metabolomicsworkbench.org/databases/refmet",
        "timeout": 30,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "description": "Reference list of Metabolite nomenclature from Metabolomics Workbench",
        "client_type": "RefMetClient"
    },
    "SPOKE": {
        "host": "localhost",
        "port": 8529,
        "database": "spoke",
        "username": "spoke_user",
        "password": "",
        "timeout": 30,
        "description": "SPOKE Knowledge Graph",
        "client_type": "ArangoDBClient"
    },
    "RaMP-DB": {
        "db_path": "/path/to/rampdb.sqlite",  # Placeholder - update with actual path
        "timeout": 30,
        "max_retries": 3,
        "description": "Rapid Mapping Database for metabolites and pathways",
        "client_type": "RaMPClient"
    },
    "MetabolitesCSV": {
        "file_path": "data/metabolites.csv",  # Placeholder - update with actual path
        "description": "CSV file with metabolite data",
        "client_type": "CSVClient"
    }
}

try:
    # Update resource configurations
    for name, config in resource_configs.items():
        description = config.pop("description")
        client_type = config.pop("client_type")
        
        # Check if resource exists
        cursor.execute("SELECT id, config FROM resources WHERE name = ?", (name,))
        resource = cursor.fetchone()
        
        if resource:
            resource_id, current_config_json = resource
            
            # Parse current config if it exists
            try:
                current_config = json.loads(current_config_json) if current_config_json else {}
            except json.JSONDecodeError:
                current_config = {}
            
            # Update with new config while preserving any existing values not in our template
            merged_config = {**current_config, **config}
            
            # Update resource
            cursor.execute(
                "UPDATE resources SET description = ?, client_type = ?, config = ? WHERE id = ?",
                (description, client_type, json.dumps(merged_config), resource_id)
            )
            print(f"Updated configuration for '{name}' (ID: {resource_id})")
        else:
            print(f"Resource '{name}' not found in database - skipping")
    
    # Commit changes
    conn.commit()
    print("Resource configurations updated successfully")
    
    # Verify the changes
    cursor.execute("SELECT id, name, description, client_type, config FROM resources")
    resources = cursor.fetchall()
    
    print("\nUpdated resources in the database:")
    print("=================================")
    for resource in resources:
        print(f"ID: {resource[0]}, Name: {resource[1]}, Type: {resource[3]}")
        print(f"Description: {resource[2]}")
        try:
            config = json.loads(resource[4]) if resource[4] else {}
            print(f"Configuration: {json.dumps(config, indent=2)}")
        except json.JSONDecodeError:
            print(f"Configuration: {resource[4]} (invalid JSON)")
        print("-" * 50)
    
except Exception as e:
    print(f"Error updating resource configurations: {e}")
    conn.rollback()

finally:
    # Close connection
    conn.close()

#!/usr/bin/env python3
"""
Update SPOKE endpoint property configurations from Cypher to AQL.

This script updates the extraction patterns in the endpoint_property_configs table
for the SPOKE endpoint (ID 8) to use AQL instead of Cypher.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Default path to the SQLite database
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/metamapper.db')

def connect_to_database(db_path=None):
    """Connect to the SQLite database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_spoke_property_configs(conn):
    """Get the current SPOKE property configurations."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT config_id, endpoint_id, ontology_type, property_name, 
               extraction_method, extraction_pattern, transform_method
        FROM endpoint_property_configs
        WHERE endpoint_id = 8
    """)
    
    return cursor.fetchall()

def convert_cypher_to_aql(cypher_pattern):
    """Convert a Cypher query pattern to AQL."""
    # Parse the Cypher pattern from the JSON string
    try:
        pattern_obj = json.loads(cypher_pattern)
        cypher_query = pattern_obj.get('cypher', '')
    except json.JSONDecodeError:
        print(f"Error parsing Cypher pattern: {cypher_pattern}")
        return None
    
    # Map different Cypher queries to AQL
    if "MATCH (c:Compound) WHERE c.identifier = $id AND c.source =" in cypher_query:
        # Extract the source name
        import re
        source_match = re.search(r'c\.source = \"([^\"]+)\"', cypher_query)
        source = source_match.group(1) if source_match else ""
        
        aql_query = (
            f"FOR c IN Compound "
            f"FILTER c.identifier == @id AND c.source == '{source}' "
            f"RETURN c"
        )
        return json.dumps({"aql": aql_query})
    
    elif "MATCH (c:Compound) WHERE c.inchikey = $id" in cypher_query:
        aql_query = (
            "FOR c IN Compound "
            "FILTER c.inchikey == @id "
            "RETURN c"
        )
        return json.dumps({"aql": aql_query})
    
    else:
        print(f"Unknown Cypher pattern: {cypher_query}")
        return None

def update_spoke_property_configs(conn):
    """Update SPOKE property configurations from Cypher to AQL."""
    cursor = conn.cursor()
    
    # Get the current configurations
    configs = get_spoke_property_configs(conn)
    
    updates = []
    for config in configs:
        config_id = config['config_id']
        cypher_pattern = config['extraction_pattern']
        
        # Convert to AQL
        aql_pattern = convert_cypher_to_aql(cypher_pattern)
        
        if aql_pattern:
            updates.append((aql_pattern, config_id))
    
    # Update the configurations
    cursor.executemany("""
        UPDATE endpoint_property_configs
        SET extraction_pattern = ?
        WHERE config_id = ?
    """, updates)
    
    conn.commit()
    print(f"Updated {len(updates)} SPOKE property configurations from Cypher to AQL.")

def main():
    """Main function to update SPOKE property configurations."""
    print("Updating SPOKE property configurations from Cypher to AQL...")
    
    conn = connect_to_database()
    
    try:
        # Show current SPOKE property configurations
        print("Current SPOKE property configurations:")
        configs = get_spoke_property_configs(conn)
        for config in configs:
            print(f"  {config['ontology_type']} ({config['property_name']}): {config['extraction_pattern']}")
        
        # Update SPOKE property configurations
        update_spoke_property_configs(conn)
        
        # Show updated SPOKE property configurations
        print("\nUpdated SPOKE property configurations:")
        configs = get_spoke_property_configs(conn)
        for config in configs:
            print(f"  {config['ontology_type']} ({config['property_name']}): {config['extraction_pattern']}")
        
        print("\nSPOKE property configurations updated successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()

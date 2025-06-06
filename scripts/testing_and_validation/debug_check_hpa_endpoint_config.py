#!/usr/bin/env python3
"""Check HPA endpoint configuration in the database"""

import sqlite3
import pandas as pd

db_path = "/home/ubuntu/biomapper/data/metamapper.db"

try:
    conn = sqlite3.connect(db_path)
    
    # Check HPA_Protein endpoint configuration
    print("=== HPA_Protein Endpoint Configuration ===")
    endpoint_query = """
    SELECT id, name, description, primary_ontology_type, entity_type, connection_details
    FROM endpoints
    WHERE name = 'HPA_Protein'
    """
    endpoint_df = pd.read_sql_query(endpoint_query, conn)
    print(endpoint_df.to_string())
    
    if not endpoint_df.empty:
        hpa_endpoint_id = endpoint_df.iloc[0]['id']
        
        # Check PropertyExtractionConfig for HPA
        print("\n=== HPA Property Extraction Configurations ===")
        prop_query = """
        SELECT pec.*, o.name as ontology_name
        FROM property_extraction_configs pec
        LEFT JOIN ontologies o ON pec.ontology_id = o.id
        WHERE pec.endpoint_id = ?
        """
        prop_df = pd.read_sql_query(prop_query, conn, params=(hpa_endpoint_id,))
        print(prop_df.to_string())
        
        # Check related MappingResource
        print("\n=== HPA Related Mapping Resources ===")
        resource_query = """
        SELECT * FROM resources
        WHERE name LIKE '%hpa%'
        """
        resource_df = pd.read_sql_query(resource_query, conn)
        print(resource_df.to_string())
        
        # Check mapping paths involving HPA
        print("\n=== Mapping Paths involving HPA_Protein ===")
        path_query = """
        SELECT mp.*, 
               e1.name as source_endpoint_name, 
               e2.name as target_endpoint_name
        FROM mapping_paths mp
        JOIN endpoints e1 ON mp.source_endpoint_id = e1.id
        JOIN endpoints e2 ON mp.target_endpoint_id = e2.id
        WHERE e1.name = 'HPA_Protein' OR e2.name = 'HPA_Protein'
        """
        path_df = pd.read_sql_query(path_query, conn)
        print(path_df.to_string())
    
    # Also check UKBB_Protein for comparison
    print("\n\n=== UKBB_Protein Endpoint Configuration (for comparison) ===")
    ukbb_query = """
    SELECT id, name, description, primary_ontology_type, entity_type, connection_details
    FROM endpoints
    WHERE name = 'UKBB_Protein'
    """
    ukbb_df = pd.read_sql_query(ukbb_query, conn)
    print(ukbb_df.to_string())
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
#!/usr/bin/env python3
"""
Setup script for endpoint mapping configuration.

This script populates the database with sample endpoint and mapping resource configurations
for the MetabolitesCSV-to-SPOKE relationship example.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Default path to the SQLite database
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/metamapper.db")
print(f"Using database path: {os.path.abspath(DEFAULT_DB_PATH)}")


def connect_to_database(db_path=None):
    """Connect to the SQLite database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def setup_endpoints(conn):
    """Set up sample endpoints (MetabolitesCSV and SPOKE)."""
    cursor = conn.cursor()

    # Check if endpoints already exist
    cursor.execute(
        "SELECT COUNT(*) FROM endpoints WHERE name IN ('MetabolitesCSV', 'SPOKE')"
    )
    if cursor.fetchone()[0] > 0:
        print("Endpoints already exist, skipping...")
        return

    # Insert MetabolitesCSV endpoint
    metabolites_connection = {
        "file_path": "/home/ubuntu/biomapper/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv",
        "delimiter": "\t",
    }

    cursor.execute(
        """
        INSERT INTO endpoints 
        (endpoint_id, name, description, endpoint_type, connection_info, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            7,  # Use ID 7 for consistency with existing documentation
            "MetabolitesCSV",
            "Arivale metabolomics data in CSV format",
            "file",
            json.dumps(metabolites_connection),
            datetime.now(),
        ),
    )

    # Insert SPOKE endpoint
    spoke_connection = {
        "url": "https://spoke-api.example.org",
        "auth_token": "${SPOKE_TOKEN}",
    }

    cursor.execute(
        """
        INSERT INTO endpoints 
        (endpoint_id, name, description, endpoint_type, connection_info, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            8,  # Use ID 8 for consistency with existing documentation
            "SPOKE",
            "Scalable Precision Medicine Open Knowledge Engine",
            "graph",
            json.dumps(spoke_connection),
            datetime.now(),
        ),
    )

    conn.commit()
    print("Endpoints created successfully.")


def setup_mapping_resources(conn):
    """Set up sample mapping resources (UniChem, KEGG, etc.)."""
    cursor = conn.cursor()

    # Check if mapping resources already exist
    cursor.execute(
        "SELECT COUNT(*) FROM mapping_resources WHERE name IN ('UniChem', 'KEGG')"
    )
    if cursor.fetchone()[0] > 0:
        print("Mapping resources already exist, skipping...")
        return

    # Insert UniChem as a mapping resource
    unichem_connection = {
        "base_url": "https://www.ebi.ac.uk/unichem/",
        "timeout_ms": 5000,
    }

    cursor.execute(
        """
        INSERT INTO mapping_resources 
        (resource_id, name, resource_type, connection_info, priority, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            10,  # Use ID 10 for consistency with existing documentation
            "UniChem",
            "api",
            json.dumps(unichem_connection),
            1,  # High priority
            datetime.now(),
        ),
    )

    # Insert KEGG as a mapping resource
    kegg_connection = {"base_url": "https://rest.kegg.jp/", "timeout_ms": 5000}

    cursor.execute(
        """
        INSERT INTO mapping_resources 
        (resource_id, name, resource_type, connection_info, priority, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            9,  # Use ID 9 for consistency with existing documentation
            "KEGG",
            "api",
            json.dumps(kegg_connection),
            2,  # Medium priority
            datetime.now(),
        ),
    )

    conn.commit()
    print("Mapping resources created successfully.")


def setup_ontology_coverage(conn):
    """Set up ontology coverage for mapping resources."""
    cursor = conn.cursor()

    # Check if ontology coverage already exists
    cursor.execute("SELECT COUNT(*) FROM ontology_coverage")
    if cursor.fetchone()[0] > 0:
        print("Ontology coverage already exists, skipping...")
        return

    # UniChem ontology coverage
    unichem_coverage = [
        (10, "hmdb", "chebi", "full"),
        (10, "hmdb", "pubchem", "full"),
        (10, "chebi", "pubchem", "full"),
        (10, "pubchem", "hmdb", "full"),
        (10, "pubchem", "chebi", "full"),
        (10, "chebi", "hmdb", "full"),
    ]

    cursor.executemany(
        """
        INSERT INTO ontology_coverage 
        (resource_id, source_type, target_type, support_level)
        VALUES (?, ?, ?, ?)
        """,
        unichem_coverage,
    )

    # KEGG ontology coverage
    kegg_coverage = [
        (9, "kegg", "pubchem", "full"),
        (9, "kegg", "chebi", "partial"),
        (9, "kegg", "cas", "partial"),
        (9, "kegg", "name", "full"),
    ]

    cursor.executemany(
        """
        INSERT INTO ontology_coverage 
        (resource_id, source_type, target_type, support_level)
        VALUES (?, ?, ?, ?)
        """,
        kegg_coverage,
    )

    conn.commit()
    print("Ontology coverage created successfully.")


def setup_endpoint_ontology_preferences(conn):
    """Set up ontology preferences for endpoints."""
    cursor = conn.cursor()

    # Check if ontology preferences already exist
    cursor.execute("SELECT COUNT(*) FROM endpoint_ontology_preferences")
    if cursor.fetchone()[0] > 0:
        print("Endpoint ontology preferences already exist, skipping...")
        return

    # MetabolitesCSV ontology preferences
    metabolitescsv_preferences = [
        (7, "hmdb", 1),  # HMDB IDs are first choice (most reliable/available)
        (7, "kegg", 2),  # KEGG IDs are second choice
        (7, "pubchem", 3),  # PubChem IDs are third choice
        (7, "cas", 4),  # CAS numbers are fourth choice
        (7, "name", 5),  # Names are least preferred (too ambiguous)
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_ontology_preferences 
        (endpoint_id, ontology_type, preference_level)
        VALUES (?, ?, ?)
        """,
        metabolitescsv_preferences,
    )

    # SPOKE ontology preferences
    spoke_preferences = [
        (8, "chebi", 1),  # ChEBI IDs are first choice in SPOKE
        (8, "hmdb", 1),  # HMDB IDs are equally preferred (tie for first)
        (8, "pubchem", 2),  # PubChem IDs are second choice
        (8, "drugbank", 3),  # DrugBank IDs are third choice
        (8, "chembl", 4),  # ChEMBL IDs are fourth choice
        (8, "inchikey", 5),  # InChIKeys are least preferred
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_ontology_preferences 
        (endpoint_id, ontology_type, preference_level)
        VALUES (?, ?, ?)
        """,
        spoke_preferences,
    )

    conn.commit()
    print("Endpoint ontology preferences created successfully.")


def setup_endpoint_property_configs(conn):
    """Set up property configurations for endpoints."""
    cursor = conn.cursor()

    # Check if property configs already exist
    cursor.execute("SELECT COUNT(*) FROM endpoint_property_configs")
    if cursor.fetchone()[0] > 0:
        print("Endpoint property configs already exist, skipping...")
        return

    # MetabolitesCSV property configurations
    metabolitescsv_configs = [
        (7, "hmdb", "HMDB ID", "column", json.dumps({"column_name": "HMDB"}), None),
        (7, "kegg", "KEGG ID", "column", json.dumps({"column_name": "KEGG"}), None),
        (
            7,
            "pubchem",
            "PubChem ID",
            "column",
            json.dumps({"column_name": "PUBCHEM"}),
            None,
        ),
        (7, "cas", "CAS Number", "column", json.dumps({"column_name": "CAS"}), None),
        (
            7,
            "name",
            "Compound Name",
            "column",
            json.dumps({"column_name": "BIOCHEMICAL_NAME"}),
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_property_configs 
        (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern, transform_method)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        metabolitescsv_configs,
    )

    # SPOKE property configurations
    spoke_configs = [
        (
            8,
            "chebi",
            "ChEBI ID",
            "query",
            json.dumps(
                {
                    "cypher": 'MATCH (c:Compound) WHERE c.identifier = $id AND c.source = "ChEBI" RETURN c'
                }
            ),
            None,
        ),
        (
            8,
            "hmdb",
            "HMDB ID",
            "query",
            json.dumps(
                {
                    "cypher": 'MATCH (c:Compound) WHERE c.identifier = $id AND c.source = "HMDB" RETURN c'
                }
            ),
            None,
        ),
        (
            8,
            "pubchem",
            "PubChem ID",
            "query",
            json.dumps(
                {
                    "cypher": 'MATCH (c:Compound) WHERE c.identifier = $id AND c.source = "PubChem" RETURN c'
                }
            ),
            None,
        ),
        (
            8,
            "drugbank",
            "DrugBank ID",
            "query",
            json.dumps(
                {
                    "cypher": 'MATCH (c:Compound) WHERE c.identifier = $id AND c.source = "DrugBank" RETURN c'
                }
            ),
            None,
        ),
        (
            8,
            "chembl",
            "ChEMBL ID",
            "query",
            json.dumps(
                {
                    "cypher": 'MATCH (c:Compound) WHERE c.identifier = $id AND c.source = "ChEMBL" RETURN c'
                }
            ),
            None,
        ),
        (
            8,
            "inchikey",
            "InChIKey",
            "query",
            json.dumps(
                {"cypher": "MATCH (c:Compound) WHERE c.inchikey = $id RETURN c"}
            ),
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_property_configs 
        (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern, transform_method)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        spoke_configs,
    )

    conn.commit()
    print("Endpoint property configs created successfully.")


def setup_endpoint_relationship(conn):
    """Set up relationship between MetabolitesCSV and SPOKE."""
    cursor = conn.cursor()

    # Check if relationship already exists
    cursor.execute("SELECT COUNT(*) FROM endpoint_relationships")
    if cursor.fetchone()[0] > 0:
        print("Endpoint relationship already exists, skipping...")
        return

    # Create relationship
    cursor.execute(
        """
        INSERT INTO endpoint_relationships 
        (relationship_id, name, description, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            1,
            "MetabolitesCSV-to-SPOKE",
            "Maps metabolites from Arivale CSV to SPOKE entities",
            datetime.now(),
        ),
    )

    # Add MetabolitesCSV as source member
    cursor.execute(
        """
        INSERT INTO endpoint_relationship_members 
        (relationship_id, endpoint_id, role, priority)
        VALUES (?, ?, ?, ?)
        """,
        (1, 7, "source", 1),
    )

    # Add SPOKE as target member
    cursor.execute(
        """
        INSERT INTO endpoint_relationship_members 
        (relationship_id, endpoint_id, role, priority)
        VALUES (?, ?, ?, ?)
        """,
        (1, 8, "target", 1),
    )

    conn.commit()
    print("Endpoint relationship created successfully.")


def main():
    """Main function to set up the endpoint mapping configuration."""
    print("Setting up endpoint mapping configuration...")

    conn = connect_to_database()

    try:
        # Set up the various components
        setup_endpoints(conn)
        setup_mapping_resources(conn)
        setup_ontology_coverage(conn)
        setup_endpoint_ontology_preferences(conn)
        setup_endpoint_property_configs(conn)
        setup_endpoint_relationship(conn)

        print("Endpoint mapping configuration completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

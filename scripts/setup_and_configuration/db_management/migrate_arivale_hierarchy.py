#!/usr/bin/env python3
"""
Migration script to implement hierarchical endpoint organization for Arivale.

This script:
1. Adds parent_endpoint_id and endpoint_subtype columns to the endpoints table
2. Creates a top-level Arivale endpoint 
3. Updates the existing MetabolitesCSV endpoint to reference Arivale
4. Creates new endpoints for ClinicalLabs and Proteomics within Arivale
5. Sets up property configs for the new endpoints
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

ARIVALE_DATA_DIR = "/procedure/data/local_data/ARIVALE_SNAPSHOTS"


def connect_to_database(db_path=None):
    """Connect to the SQLite database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def add_hierarchy_columns(conn):
    """Add parent_endpoint_id and endpoint_subtype columns to endpoints table."""
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(endpoints)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "parent_endpoint_id" not in columns:
        print("Adding parent_endpoint_id column to endpoints table...")
        cursor.execute(
            """
            ALTER TABLE endpoints 
            ADD COLUMN parent_endpoint_id INTEGER 
            REFERENCES endpoints(endpoint_id)
        """
        )

    if "endpoint_subtype" not in columns:
        print("Adding endpoint_subtype column to endpoints table...")
        cursor.execute(
            """
            ALTER TABLE endpoints 
            ADD COLUMN endpoint_subtype TEXT
        """
        )

    conn.commit()
    print("Hierarchy columns added successfully.")


def create_arivale_parent_endpoint(conn):
    """Create the top-level Arivale endpoint."""
    cursor = conn.cursor()

    # Check if Arivale endpoint already exists
    cursor.execute("SELECT endpoint_id FROM endpoints WHERE name = 'Arivale'")
    result = cursor.fetchone()

    if result:
        print("Arivale parent endpoint already exists with ID:", result["endpoint_id"])
        return result["endpoint_id"]

    # Insert new Arivale endpoint
    cursor.execute(
        """
        INSERT INTO endpoints 
        (name, description, endpoint_type, connection_info, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            "Arivale",
            "Arivale multiomic dataset collection",
            "multiomic",
            json.dumps(
                {
                    "provider": "Arivale Inc.",
                    "description": "Comprehensive wellness dataset",
                    "data_directory": ARIVALE_DATA_DIR,
                }
            ),
            datetime.now(),
        ),
    )

    arivale_id = cursor.lastrowid
    conn.commit()
    print(f"Created Arivale parent endpoint with ID: {arivale_id}")
    return arivale_id


def update_metabolitescsv_endpoint(conn, arivale_id):
    """Update the existing MetabolitesCSV endpoint to reference Arivale as parent."""
    cursor = conn.cursor()

    # Get MetabolitesCSV endpoint ID
    cursor.execute("SELECT endpoint_id FROM endpoints WHERE name = 'MetabolitesCSV'")
    result = cursor.fetchone()

    if not result:
        print("MetabolitesCSV endpoint not found, skipping update.")
        return None

    metabolites_id = result["endpoint_id"]

    # Update it to reference Arivale as parent
    cursor.execute(
        """
        UPDATE endpoints 
        SET parent_endpoint_id = ?, endpoint_subtype = ?
        WHERE endpoint_id = ?
    """,
        (arivale_id, "metabolomics", metabolites_id),
    )

    conn.commit()
    print(
        f"Updated MetabolitesCSV (ID: {metabolites_id}) to reference Arivale as parent."
    )
    return metabolites_id


def create_clinical_labs_endpoint(conn, arivale_id):
    """Create ClinicalLabs endpoint as a child of Arivale."""
    cursor = conn.cursor()

    # Check if ClinicalLabs endpoint already exists
    cursor.execute("SELECT endpoint_id FROM endpoints WHERE name = 'ClinicalLabsCSV'")
    result = cursor.fetchone()

    if result:
        print("ClinicalLabs endpoint already exists with ID:", result["endpoint_id"])
        return result["endpoint_id"]

    # Insert new ClinicalLabs endpoint
    cursor.execute(
        """
        INSERT INTO endpoints 
        (name, description, endpoint_type, connection_info, parent_endpoint_id, endpoint_subtype, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "ClinicalLabsCSV",
            "Arivale clinical laboratory data in TSV format",
            "file",
            json.dumps(
                {
                    "file_path": os.path.join(
                        ARIVALE_DATA_DIR, "chemistries_metadata.tsv"
                    ),
                    "delimiter": "\t",
                }
            ),
            arivale_id,
            "clinical_labs",
            datetime.now(),
        ),
    )

    labs_id = cursor.lastrowid
    conn.commit()
    print(f"Created ClinicalLabsCSV endpoint with ID: {labs_id}")
    return labs_id


def create_proteomics_endpoint(conn, arivale_id):
    """Create Proteomics endpoint as a child of Arivale."""
    cursor = conn.cursor()

    # Check if Proteomics endpoint already exists
    cursor.execute("SELECT endpoint_id FROM endpoints WHERE name = 'ProteomicsCSV'")
    result = cursor.fetchone()

    if result:
        print("Proteomics endpoint already exists with ID:", result["endpoint_id"])
        return result["endpoint_id"]

    # Insert new Proteomics endpoint
    cursor.execute(
        """
        INSERT INTO endpoints 
        (name, description, endpoint_type, connection_info, parent_endpoint_id, endpoint_subtype, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "ProteomicsCSV",
            "Arivale proteomics data in TSV format",
            "file",
            json.dumps(
                {
                    "file_path": os.path.join(
                        ARIVALE_DATA_DIR, "proteomics_corrected.tsv"
                    ),
                    "metadata_file": os.path.join(
                        ARIVALE_DATA_DIR, "proteomics_metadata.tsv"
                    ),
                    "delimiter": "\t",
                }
            ),
            arivale_id,
            "proteomics",
            datetime.now(),
        ),
    )

    proteomics_id = cursor.lastrowid
    conn.commit()
    print(f"Created ProteomicsCSV endpoint with ID: {proteomics_id}")
    return proteomics_id


def setup_clinical_labs_property_configs(conn, labs_id):
    """Set up property configurations for ClinicalLabs endpoint."""
    cursor = conn.cursor()

    # First, let's check if we already have configs for this endpoint
    cursor.execute(
        """
        SELECT COUNT(*) FROM endpoint_property_configs 
        WHERE endpoint_id = ?
    """,
        (labs_id,),
    )

    if cursor.fetchone()[0] > 0:
        print("Property configs for ClinicalLabsCSV already exist, skipping...")
        return

    # Define property configs for clinical labs based on actual column names
    labs_configs = [
        (
            labs_id,
            "loinc",
            "Labcorp LOINC ID",
            "column",
            json.dumps({"column_name": "Labcorp LOINC ID"}),
            None,
        ),
        (
            labs_id,
            "loinc",
            "Quest LOINC ID",
            "column",
            json.dumps({"column_name": "Quest LOINC ID"}),
            None,
        ),
        (
            labs_id,
            "labcorp_id",
            "Labcorp ID",
            "column",
            json.dumps({"column_name": "Labcorp ID"}),
            None,
        ),
        (
            labs_id,
            "quest_id",
            "Quest ID",
            "column",
            json.dumps({"column_name": "Quest ID"}),
            None,
        ),
        (labs_id, "name", "Name", "column", json.dumps({"column_name": "Name"}), None),
        (
            labs_id,
            "display_name",
            "Display Name",
            "column",
            json.dumps({"column_name": "Display Name"}),
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_property_configs 
        (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern, transform_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        labs_configs,
    )

    conn.commit()
    print("Clinical labs property configs created successfully.")


def setup_proteomics_property_configs(conn, proteomics_id):
    """Set up property configurations for Proteomics endpoint.

    The proteomics file has a unique structure where protein IDs are in column names,
    following a pattern like 'CAM_P00441' or 'ONC2_P08069' where the part after the underscore
    is a UniProt ID. We need a special extraction method for this.
    """
    cursor = conn.cursor()

    # First, let's check if we already have configs for this endpoint
    cursor.execute(
        """
        SELECT COUNT(*) FROM endpoint_property_configs 
        WHERE endpoint_id = ?
    """,
        (proteomics_id,),
    )

    if cursor.fetchone()[0] > 0:
        print("Property configs for ProteomicsCSV already exist, skipping...")
        return

    # Define property configs for proteomics
    # This requires a special pattern to extract UniProt IDs from column names
    proteomics_configs = [
        (
            proteomics_id,
            "uniprot",
            "UniProt ID",
            "pattern",
            json.dumps(
                {
                    "pattern": "^(CAM|CRE|CVD2|CVD3|DEV|INF|IRE|MET|NEU1|NEX|ODA|ONC2|ONC3)_([A-Z0-9]+)$",
                    "group": 2,
                }
            ),
            "extract_uniprot_from_column_name",
        ),
        (
            proteomics_id,
            "chip_id",
            "Chip ID",
            "pattern",
            json.dumps(
                {
                    "pattern": "^(CAM|CRE|CVD2|CVD3|DEV|INF|IRE|MET|NEU1|NEX|ODA|ONC2|ONC3)_([A-Z0-9]+)$",
                    "group": 1,
                }
            ),
            None,
        ),
        (
            proteomics_id,
            "public_client_id",
            "Client ID",
            "column",
            json.dumps({"column_name": "public_client_id"}),
            None,
        ),
        (
            proteomics_id,
            "sample_id",
            "Sample ID",
            "column",
            json.dumps({"column_name": "sample_id"}),
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO endpoint_property_configs 
        (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern, transform_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        proteomics_configs,
    )

    conn.commit()
    print("Proteomics property configs created successfully.")


def inspect_file_columns(file_path, delimiter="\t", max_rows=5):
    """Helper function to inspect column names in a TSV/CSV file.
    Handles files with metadata headers starting with #.
    """
    import csv

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Read the file line by line to skip metadata headers
            lines = []
            header_line = None
            data_lines = []

            for line in f:
                if line.startswith("#"):
                    # This is a metadata line, store it
                    lines.append(line.strip())
                else:
                    # This might be the header line or data
                    if header_line is None:
                        header_line = line.strip()
                    else:
                        # Only store up to max_rows data lines
                        if len(data_lines) < max_rows:
                            data_lines.append(line.strip())

            # Print metadata lines
            print(f"\nMetadata in {os.path.basename(file_path)}:")
            for i, line in enumerate(lines[:5]):
                print(f"  {line}")
            if len(lines) > 5:
                print(f"  ... ({len(lines) - 5} more metadata lines)")

            # Parse and print header
            if header_line:
                headers = list(csv.reader([header_line], delimiter=delimiter))[0]
                print(f"\nColumns in {os.path.basename(file_path)}:")
                for i, header in enumerate(headers):
                    print(f"  {i+1}. {header}")

                # Parse and print data rows
                print("\nSample data rows:")
                for i, line in enumerate(data_lines):
                    row = list(csv.reader([line], delimiter=delimiter))[0]
                    print(
                        f"  Row {i+1}: {row[:min(5, len(row))]}..."
                        + (" [truncated]" if len(row) > 5 else "")
                    )
            else:
                print(f"\nNo column headers found in {os.path.basename(file_path)}")

    except Exception as e:
        print(f"Error inspecting file {file_path}: {e}")


def setup_ontology_preferences(conn, endpoint_ids):
    """Set up ontology preferences for the endpoints."""
    cursor = conn.cursor()

    # Define common preferences for all endpoints
    ontology_preferences = []

    # For metabolites endpoint (existing)
    metabolites_preferences = [
        (endpoint_ids.get("metabolites"), "hmdb", 1),  # Highest preference
        (endpoint_ids.get("metabolites"), "pubchem", 2),
        (endpoint_ids.get("metabolites"), "chebi", 3),
        (endpoint_ids.get("metabolites"), "inchikey", 4),
        (endpoint_ids.get("metabolites"), "name", 5),  # Lowest preference
    ]

    # For clinical labs endpoint
    labs_preferences = [
        (endpoint_ids.get("labs"), "loinc", 1),  # Highest preference
        (endpoint_ids.get("labs"), "snomed", 2),
        (endpoint_ids.get("labs"), "name", 3),  # Lowest preference
    ]

    # For proteomics endpoint
    proteomics_preferences = [
        (endpoint_ids.get("proteomics"), "uniprot", 1),  # Highest preference
        (endpoint_ids.get("proteomics"), "entrez", 2),
        (endpoint_ids.get("proteomics"), "gene_symbol", 3),
        (endpoint_ids.get("proteomics"), "name", 4),  # Lowest preference
    ]

    all_preferences = []
    for prefs in [metabolites_preferences, labs_preferences, proteomics_preferences]:
        if prefs[0][0] is not None:  # If endpoint_id is not None
            all_preferences.extend(prefs)

    # Insert preferences
    for endpoint_id, ontology_type, preference_level in all_preferences:
        if endpoint_id is None:
            continue

        # Check if preference already exists
        cursor.execute(
            """
            SELECT COUNT(*) FROM endpoint_ontology_preferences 
            WHERE endpoint_id = ? AND ontology_type = ?
        """,
            (endpoint_id, ontology_type),
        )

        if cursor.fetchone()[0] > 0:
            print(
                f"Ontology preference for {ontology_type} already exists for endpoint {endpoint_id}"
            )
            continue

        # Insert preference
        cursor.execute(
            """
            INSERT INTO endpoint_ontology_preferences
            (endpoint_id, ontology_type, preference_level)
            VALUES (?, ?, ?)
        """,
            (endpoint_id, ontology_type, preference_level),
        )

    conn.commit()
    print("Ontology preferences set up successfully.")


def update_endpoint_relationships(conn):
    """Update existing relationships to account for the new hierarchical structure."""
    cursor = conn.cursor()

    # Check if we need to update any relationships
    cursor.execute(
        """
        SELECT er.relationship_id, er.name, erm.endpoint_id, e.name as endpoint_name
        FROM endpoint_relationships er
        JOIN endpoint_relationship_members erm ON er.relationship_id = erm.relationship_id
        JOIN endpoints e ON erm.endpoint_id = e.endpoint_id
        WHERE e.parent_endpoint_id IS NOT NULL
    """
    )

    relationships = cursor.fetchall()
    print(
        f"Found {len(relationships)} relationship members with hierarchical endpoints."
    )

    # No changes needed for now, this function could be expanded later
    # to add relationships between the new endpoints


def main():
    """Main function to migrate to hierarchical endpoint structure."""
    print("Migrating to hierarchical endpoint structure...")

    conn = connect_to_database()

    try:
        # 1. Add hierarchy columns to endpoints table
        add_hierarchy_columns(conn)

        # 2. Create parent Arivale endpoint
        arivale_id = create_arivale_parent_endpoint(conn)

        # 3. Update existing MetabolitesCSV endpoint
        metabolites_id = update_metabolitescsv_endpoint(conn, arivale_id)

        # 4. Create new endpoints for Arivale data types
        labs_id = create_clinical_labs_endpoint(conn, arivale_id)
        proteomics_id = create_proteomics_endpoint(conn, arivale_id)

        # Store endpoint IDs for later use
        endpoint_ids = {
            "arivale": arivale_id,
            "metabolites": metabolites_id,
            "labs": labs_id,
            "proteomics": proteomics_id,
        }

        # 5. Inspect the TSV files to understand their structure
        print("\n=== Inspecting TSV Files ===")
        inspect_file_columns(
            os.path.join(ARIVALE_DATA_DIR, "metabolomics_metadata.tsv")
        )
        inspect_file_columns(os.path.join(ARIVALE_DATA_DIR, "chemistries_metadata.tsv"))
        inspect_file_columns(os.path.join(ARIVALE_DATA_DIR, "proteomics_corrected.tsv"))

        # 6. Set up property configs for the new endpoints
        setup_clinical_labs_property_configs(conn, labs_id)
        setup_proteomics_property_configs(conn, proteomics_id)

        # 7. Set up ontology preferences for the endpoints
        setup_ontology_preferences(conn, endpoint_ids)

        # 8. Update any existing relationships
        update_endpoint_relationships(conn)

        print("\nHierarchical endpoint migration completed successfully.")
        print("\nAll steps completed. The database now has:")
        print("1. A parent 'Arivale' endpoint representing the full dataset")
        print(
            "2. Three child endpoints for different data types: metabolomics, clinical labs, and proteomics"
        )
        print("3. Property configs for extracting ontology IDs from each data type")
        print("4. Ontology preferences for each endpoint type")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

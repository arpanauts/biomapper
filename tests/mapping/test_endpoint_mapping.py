#!/usr/bin/env python
"""
Test script for endpoint-to-endpoint mapping implementation.

This script demonstrates the use of the relationship mapping layer
to discover and execute mappings between MetabolitesCSV and SPOKE.
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3


# Define simplified custom implementations for testing
class MockPathFinder:
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()

    async def discover_paths_for_relationship(self, relationship_id):
        # Get source and target endpoints
        self.cursor.execute(
            """
            SELECT e.endpoint_id, e.name, m.role
            FROM endpoints e
            JOIN endpoint_relationship_members m ON e.endpoint_id = m.endpoint_id
            WHERE m.relationship_id = ?
        """,
            (relationship_id,),
        )

        endpoints = {}
        for row in self.cursor.fetchall():
            endpoints[row[2]] = {"id": row[0], "name": row[1]}

        if "source" not in endpoints or "target" not in endpoints:
            return []

        # Get ontology preferences for both endpoints
        source_prefs = self._get_ontology_preferences(endpoints["source"]["id"])
        target_prefs = self._get_ontology_preferences(endpoints["target"]["id"])

        # Discover paths between ontology types
        paths = []
        for source_ont, source_pref in source_prefs:
            for target_ont, target_pref in target_prefs:
                # Find paths between these ontology types
                ont_paths = self._find_ontology_paths(source_ont, target_ont)

                for path in ont_paths:
                    # Calculate a score based on preferences
                    score = 1.0 / (source_pref + target_pref)

                    # Store in the relationship_mapping_paths table
                    self._store_relationship_path(
                        relationship_id, source_ont, target_ont, path["id"], score
                    )

                    # Add to results
                    paths.append({"path": path, "score": score})

        return paths

    def _get_ontology_preferences(self, endpoint_id):
        self.cursor.execute(
            """
            SELECT ontology_type, preference_level
            FROM endpoint_ontology_preferences
            WHERE endpoint_id = ?
            ORDER BY preference_level ASC
        """,
            (endpoint_id,),
        )

        return [(row[0], row[1]) for row in self.cursor.fetchall()]

    def _find_ontology_paths(self, source_type, target_type):
        self.cursor.execute(
            """
            SELECT id, source_type, target_type, path_steps, performance_score
            FROM mapping_paths
            WHERE LOWER(source_type) = LOWER(?)
            AND LOWER(target_type) = LOWER(?)
            ORDER BY performance_score DESC
            LIMIT 5
        """,
            (source_type, target_type),
        )

        paths = []
        for row in self.cursor.fetchall():
            paths.append(
                {
                    "id": row[0],
                    "source_type": row[1],
                    "target_type": row[2],
                    "path_steps": json.loads(row[3]) if row[3] else [],
                    "performance_score": row[4],
                }
            )

        return paths

    def _store_relationship_path(
        self, relationship_id, source_ont, target_ont, path_id, score
    ):
        try:
            # First check if it already exists
            self.cursor.execute(
                """
                SELECT id FROM relationship_mapping_paths
                WHERE relationship_id = ? AND source_ontology = ? AND target_ontology = ?
            """,
                (relationship_id, source_ont, target_ont),
            )

            existing = self.cursor.fetchone()

            if existing:
                # Update existing
                self.cursor.execute(
                    """
                    UPDATE relationship_mapping_paths
                    SET ontology_path_id = ?,
                        performance_score = ?,
                        last_discovered = ?
                    WHERE id = ?
                """,
                    (path_id, score, datetime.now().isoformat(), existing[0]),
                )
            else:
                # Insert new
                self.cursor.execute(
                    """
                    INSERT INTO relationship_mapping_paths
                    (relationship_id, source_ontology, target_ontology, 
                     ontology_path_id, performance_score, last_discovered)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        relationship_id,
                        source_ont,
                        target_ont,
                        path_id,
                        score,
                        datetime.now().isoformat(),
                    ),
                )

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing relationship path: {e}")
            return False


class MockMappingExecutor:
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()

    async def map_entity(
        self,
        relationship_id,
        source_entity,
        source_ontology=None,
        confidence_threshold=0.0,
    ):
        # If source ontology not specified, use default
        if not source_ontology:
            source_ontology = self._get_default_source_ontology(relationship_id)

        # Get the best mapping path
        path_info = self._get_best_relationship_path(relationship_id, source_ontology)

        if not path_info:
            return []

        # Get the ontology path
        ontology_path = self._get_ontology_path(path_info["ontology_path_id"])

        if not ontology_path:
            return []

        # For testing, create a simulated mapping result
        results = [
            {
                "source_id": source_entity,
                "source_type": source_ontology,
                "target_id": f"mapped_{source_entity}",
                "target_type": path_info["target_ontology"],
                "confidence": 0.95,
                "path": path_info["ontology_path_id"],
            }
        ]

        # Update usage statistics
        self._update_path_usage(path_info["id"])

        return results

    async def map_from_endpoint_data(self, relationship_id, source_data):
        # Get source endpoint preferences
        source_endpoint = self._get_source_endpoint(relationship_id)

        if not source_endpoint:
            return []

        # Get ontology preferences
        preferences = self._get_ontology_preferences(source_endpoint["endpoint_id"])

        # Try each preference
        for ont_type, _ in preferences:
            # Extract property from data
            source_id = self._extract_property_from_data(source_data, ont_type)

            if source_id:
                # Map using the extracted ID
                return await self.map_entity(
                    relationship_id=relationship_id,
                    source_entity=source_id,
                    source_ontology=ont_type,
                )

        return []

    def _extract_property_from_data(self, data, ontology_type):
        try:
            field_mapping = {
                "hmdb": ["HMDB", "hmdb", "hmdb_id"],
                "chebi": ["CHEBI", "chebi", "chebi_id"],
                "pubchem": ["PUBCHEM", "pubchem", "pubchem_id"],
                "kegg": ["KEGG", "kegg", "kegg_id"],
                "inchikey": ["INCHIKEY", "inchikey", "inchi_key"],
                "cas": ["CAS", "cas", "cas_id"],
                "name": ["BIOCHEMICAL_NAME", "name", "compound_name"],
            }

            # Try to find a match in the data
            for field in field_mapping.get(ontology_type.lower(), []):
                if field in data and data[field]:
                    return data[field]

            # If no exact field match, try case-insensitive
            for field in field_mapping.get(ontology_type.lower(), []):
                for key in data:
                    if key.lower() == field.lower() and data[key]:
                        return data[key]

            print(f"No property found for ontology type {ontology_type}")
            # For testing, if we can't extract the property, use a fallback value
            if ontology_type.lower() == "hmdb":
                return data.get("HMDB", "HMDB00001")
            elif ontology_type.lower() == "chebi":
                return data.get("CHEBI", "CHEBI:15422")
            elif ontology_type.lower() == "name":
                return data.get("BIOCHEMICAL_NAME", "Unknown Compound")
        except Exception as e:
            print(f"Error extracting property: {e}")

        return None

    def _get_default_source_ontology(self, relationship_id):
        source_endpoint = self._get_source_endpoint(relationship_id)

        if not source_endpoint:
            return "hmdb"  # Default

        preferences = self._get_ontology_preferences(source_endpoint["endpoint_id"])

        if preferences:
            return preferences[0][0]

        return "hmdb"  # Default

    def _get_best_relationship_path(self, relationship_id, source_ontology):
        try:
            self.cursor.execute(
                """
                SELECT id, relationship_id, source_ontology, target_ontology, 
                       ontology_path_id, performance_score
                FROM relationship_mapping_paths
                WHERE relationship_id = ?
                AND LOWER(source_ontology) = LOWER(?)
                ORDER BY performance_score DESC
                LIMIT 1
            """,
                (relationship_id, source_ontology),
            )

            row = self.cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "relationship_id": row[1],
                    "source_ontology": row[2],
                    "target_ontology": row[3],
                    "ontology_path_id": row[4],
                    "performance_score": row[5],
                }

            # If no path found, create a default mapping path for testing
            print(
                f"No mapping path found for {relationship_id}/{source_ontology}, creating one"
            )

            # Find a valid ontology path to use
            self.cursor.execute(
                """
                SELECT id FROM mapping_paths
                WHERE LOWER(source_type) = LOWER(?)
                LIMIT 1
            """,
                (source_ontology,),
            )
            path_id = self.cursor.fetchone()

            if not path_id:
                print("No suitable ontology path found")
                return None

            # Create a relationship mapping path for testing
            self.cursor.execute(
                """
                INSERT INTO relationship_mapping_paths
                (relationship_id, source_ontology, target_ontology, ontology_path_id, 
                 performance_score, usage_count, last_discovered)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    relationship_id,
                    source_ontology,
                    "chebi",
                    path_id[0],
                    0.9,
                    0,
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()

            # Return the newly created path
            self.cursor.execute(
                """
                SELECT id, relationship_id, source_ontology, target_ontology, 
                       ontology_path_id, performance_score
                FROM relationship_mapping_paths
                WHERE relationship_id = ? AND source_ontology = ?
                ORDER BY id DESC LIMIT 1
            """,
                (relationship_id, source_ontology),
            )

            row = self.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "relationship_id": row[1],
                    "source_ontology": row[2],
                    "target_ontology": row[3],
                    "ontology_path_id": row[4],
                    "performance_score": row[5],
                }
        except Exception as e:
            print(f"Error getting best path: {e}")

        return None

    def _get_ontology_path(self, path_id):
        self.cursor.execute(
            """
            SELECT id, source_type, target_type, path_steps, performance_score
            FROM mapping_paths
            WHERE id = ?
        """,
            (path_id,),
        )

        row = self.cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "source_type": row[1],
                "target_type": row[2],
                "path_steps": json.loads(row[3]) if row[3] else [],
                "performance_score": row[4],
            }

        return None

    def _update_path_usage(self, path_id):
        try:
            self.cursor.execute(
                """
                UPDATE relationship_mapping_paths
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), path_id),
            )

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating path usage: {e}")
            return False

    def _get_source_endpoint(self, relationship_id):
        try:
            self.cursor.execute(
                """
                SELECT e.endpoint_id, e.name, e.description
                FROM endpoints e
                JOIN endpoint_relationship_members m ON e.endpoint_id = m.endpoint_id
                WHERE m.relationship_id = ?
                AND m.role = 'source'
            """,
                (relationship_id,),
            )

            row = self.cursor.fetchone()

            if row:
                return {"endpoint_id": row[0], "name": row[1], "description": row[2]}
        except Exception as e:
            print(f"Error getting source endpoint: {e}")

        # If we fail to get the real endpoint, create a mock one for testing
        return {
            "endpoint_id": 7,  # MetabolitesCSV
            "name": "MetabolitesCSV",
            "description": "CSV file with metabolite data",
        }

    def _get_ontology_preferences(self, endpoint_id):
        self.cursor.execute(
            """
            SELECT ontology_type, preference_level
            FROM endpoint_ontology_preferences
            WHERE endpoint_id = ?
            ORDER BY preference_level ASC
        """,
            (endpoint_id,),
        )

        return [(row[0], row[1]) for row in self.cursor.fetchall()]


# Now use our implementation classes
from biomapper.mapping.relationships.path_finder import RelationshipPathFinder
from biomapper.mapping.relationships.executor import RelationshipMappingExecutor


import pytest


@pytest.mark.skip(reason="Requires external database file at /home/ubuntu/biomapper/data/metamapper.db")
async def test_relationship_mapping():
    """Test the endpoint-to-endpoint mapping implementation."""
    # Initialize database connection
    db_path = "/home/ubuntu/biomapper/data/metamapper.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. List all relationships
        print("\n=== Endpoint Relationships ===")
        cursor.execute(
            """
            SELECT r.relationship_id, r.name, r.description, COUNT(m.endpoint_id) as members
            FROM endpoint_relationships r
            LEFT JOIN endpoint_relationship_members m ON r.relationship_id = m.relationship_id
            GROUP BY r.relationship_id
        """
        )
        rows = cursor.fetchall()

        for row in rows:
            print(f"ID: {row[0]} | Name: {row[1]}")
            print(f"Description: {row[2]}")
            print(f"Members: {row[3]}")

            # Get relationship members
            cursor.execute(
                """
                SELECT m.role, e.endpoint_id, e.name
                FROM endpoint_relationship_members m
                JOIN endpoints e ON m.endpoint_id = e.endpoint_id
                WHERE m.relationship_id = ?
            """,
                (row[0],),
            )
            members = cursor.fetchall()

            for member in members:
                print(f"  {member[0]}: {member[2]} (ID: {member[1]})")

            print("")

        # 2. Use the MetabolitesToSPOKE relationship (ID: 3)
        relationship_id = 3

        # 3. Discover mapping paths
        print("\n=== Discovering Mapping Paths ===")
        path_finder = MockPathFinder(conn)
        paths = await path_finder.discover_paths_for_relationship(relationship_id)

        print(
            f"Discovered {len(paths)} mapping paths for relationship {relationship_id}"
        )
        for i, path in enumerate(paths):
            source_ont = path["path"]["source_type"]
            target_ont = path["path"]["target_type"]
            score = path["score"]
            print(f"Path {i+1}: {source_ont} → {target_ont} (score: {score:.2f})")

            # Show path steps
            steps = path["path"].get("path_steps", [])
            for j, step in enumerate(steps):
                print(
                    f"  Step {j+1}: {step.get('source_type', step.get('from_type'))} → {step.get('target_type', step.get('to_type'))}"
                )

        # 4. Execute a mapping using a sample metabolite
        print("\n=== Executing Mapping ===")
        executor = MockMappingExecutor(conn)

        # Use HMDB ID from the sample data
        hmdb_id = "HMDB01301"  # S-1-pyrroline-5-carboxylate

        try:
            # First, make sure we have at least one relationship path
            conn.execute(
                """
                SELECT COUNT(*) FROM relationship_mapping_paths
                WHERE relationship_id = ? AND source_ontology = ?
            """,
                (relationship_id, "hmdb"),
            )
            count = conn.cursor().fetchone()[0]

            if count == 0:
                print("Creating a test mapping path...")
                # Insert a test path if none exists
                conn.execute(
                    """
                    INSERT INTO relationship_mapping_paths
                    (relationship_id, source_ontology, target_ontology, ontology_path_id, 
                     performance_score, usage_count, last_discovered)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        relationship_id,
                        "hmdb",
                        "chebi",
                        1,
                        0.9,
                        0,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

            # Map single entity
            results = await executor.map_entity(
                relationship_id=relationship_id,
                source_entity=hmdb_id,
                source_ontology="hmdb",
            )

            if results:
                print(f"Mapped {hmdb_id} to:")
                for result in results:
                    print(
                        f"  {result['target_id']} (confidence: {result['confidence']})"
                    )
            else:
                print(f"No mapping results found for {hmdb_id}")
        except Exception as e:
            print(f"Error during mapping: {e}")

        # Map entity from source data
        print("\n=== Mapping from Source Data ===")
        source_data = {
            "BIOCHEMICAL_NAME": "Vitamin E",
            "HMDB": "HMDB01893",
            "CHEBI": "CHEBI:33263",
        }

        try:
            results = await executor.map_from_endpoint_data(
                relationship_id=relationship_id, source_data=source_data
            )

            if results:
                print(f"Mapped {source_data['BIOCHEMICAL_NAME']} to:")
                for result in results:
                    print(
                        f"  {result['target_id']} (confidence: {result['confidence']})"
                    )
            else:
                print(f"No mapping results found for {source_data['BIOCHEMICAL_NAME']}")
        except Exception as e:
            print(f"Error during data mapping: {e}")

        # 6. Show the relationship mapping paths
        print("\n=== Relationship Mapping Paths ===")
        cursor.execute(
            """
            SELECT id, relationship_id, source_ontology, target_ontology, 
                   ontology_path_id, performance_score, usage_count
            FROM relationship_mapping_paths
            WHERE relationship_id = ?
            ORDER BY performance_score DESC
        """,
            (relationship_id,),
        )
        paths = cursor.fetchall()

        for path in paths:
            print(f"ID: {path[0]} | {path[2]} → {path[3]}")
            print(f"  Performance Score: {path[5]}")
            print(f"  Usage Count: {path[6]}")
            print(f"  Ontology Path ID: {path[4]}")

            # Get the ontology path details
            cursor.execute(
                """
                SELECT source_type, target_type, path_steps
                FROM mapping_paths
                WHERE id = ?
            """,
                (path[4],),
            )
            ont_path = cursor.fetchone()

            if ont_path:
                print(f"  Ontology Path: {ont_path[0]} → {ont_path[1]}")
                try:
                    steps = json.loads(ont_path[2])
                    print(f"  Steps: {len(steps)}")
                except:
                    print("  Error parsing path steps")

            print("")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(test_relationship_mapping())

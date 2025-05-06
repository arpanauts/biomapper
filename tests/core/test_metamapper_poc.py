#!/usr/bin/env python3
"""
Proof of Concept: MetamappingEngine with Endpoint Relationships

This script demonstrates the integration of MetamappingEngine with
the endpoint-to-endpoint mapping functionality.
"""

import os
import sys
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Add requests for API calls
import requests

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Create minimal versions of required components
class UniChemAdapter:
    """A real adapter for connecting to UniChem API."""

    def __init__(self, name, db_connection):
        self.name = name
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.base_url = "https://www.ebi.ac.uk/unichem/rest"

        # UniChem source IDs mapping
        self.source_ids = {
            "hmdb": 22,  # HMDB
            "chebi": 7,  # ChEBI
            "pubchem": 22,  # PubChem Compound
            "kegg": 6,  # KEGG Compound
            "drugbank": 2,  # DrugBank
            "chembl": 1,  # ChEMBL
        }

    async def connect(self):
        """Connect to the resource."""
        try:
            # Test the API connection
            logger.info(f"Connecting to UniChem API at {self.base_url}")
            response = requests.get(f"{self.base_url}/src_ids")
            if response.status_code == 200:
                logger.info(f"Successfully connected to UniChem API")
                # Print some data from the response to verify connectivity
                data = response.json()
                if data:
                    logger.info(f"UniChem sources available: {len(data)} sources")
                    for source in data[:3]:  # Show first 3 sources
                        logger.info(
                            f"Source: {source.get('name', 'Unknown')} (ID: {source.get('src_id', 'Unknown')})"
                        )
                return True
            else:
                logger.error(
                    f"Failed to connect to UniChem API: {response.status_code}"
                )
                return False
        except Exception as e:
            logger.error(f"Error connecting to UniChem API: {e}")
            return False

    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """Map an entity from source to target type using UniChem."""
        logger.info(
            f"Mapping {source_id} from {source_type} to {target_type} using {self.name}"
        )

        # Clean the source ID (UniChem expects identifiers without prefixes)
        clean_source_id = self._clean_id(source_id, source_type)

        # Get UniChem source IDs
        source_ucm_id = self.source_ids.get(source_type.lower())
        target_ucm_id = self.source_ids.get(target_type.lower())

        if not source_ucm_id or not target_ucm_id:
            logger.warning(
                f"UniChem doesn't support {source_type} to {target_type} mapping"
            )
            return []

        try:
            # Call UniChem API to get the mapping
            url = f"{self.base_url}/src_compound_id/{clean_source_id}/src_id/{source_ucm_id}"
            response = requests.get(url)

            if response.status_code != 200:
                logger.warning(f"UniChem API error: {response.status_code}")
                return []

            results = []
            data = response.json()

            # UniChem returns a list of mappings to all available sources
            all_mappings = data if isinstance(data, list) else []

            for mapping in all_mappings:
                # Find mappings to the target source
                if mapping.get("src_id") == target_ucm_id:
                    target_id = mapping.get("src_compound_id")
                    if target_id:
                        # Add prefix if needed
                        target_id_formatted = self._format_id(target_id, target_type)
                        results.append(
                            {
                                "target_id": target_id_formatted,
                                "source": self.name,
                                "confidence": 0.95,  # UniChem mappings are high confidence
                                "metadata": {"api_response": mapping},
                            }
                        )

            # If no direct mappings, try the "connectivity" endpoint for compound info
            if not results:
                logger.info(f"No direct mapping found, trying connectivity endpoint")
                conn_url = (
                    f"{self.base_url}/connectivity/{clean_source_id}/{source_ucm_id}"
                )
                conn_response = requests.get(conn_url)

                if conn_response.status_code == 200:
                    conn_data = conn_response.json()
                    if conn_data and isinstance(conn_data, dict):
                        target_ids = conn_data.get(str(target_ucm_id), [])
                        for target_id in target_ids:
                            target_id_formatted = self._format_id(
                                target_id, target_type
                            )
                            results.append(
                                {
                                    "target_id": target_id_formatted,
                                    "source": self.name,
                                    "confidence": 0.9,  # Slightly lower confidence for connectivity mappings
                                    "metadata": {},
                                }
                            )

            logger.info(
                f"Found {len(results)} mappings from {source_id} to {target_type}"
            )
            return results

        except Exception as e:
            logger.error(f"Error calling UniChem API: {e}")
            return []

    def _clean_id(self, source_id, source_type):
        """Remove prefixes from IDs for UniChem."""
        if source_type.lower() == "chebi" and source_id.startswith("CHEBI:"):
            return source_id[6:]  # Remove 'CHEBI:' prefix
        elif source_type.lower() == "hmdb" and source_id.startswith("HMDB"):
            return source_id[4:]  # Remove 'HMDB' prefix
        return source_id

    def _format_id(self, target_id, target_type):
        """Format the target ID with appropriate prefix."""
        if target_type.lower() == "chebi" and not target_id.startswith("CHEBI:"):
            return f"CHEBI:{target_id}"
        elif target_type.lower() == "hmdb" and not target_id.startswith("HMDB"):
            return f"HMDB{target_id}"
        return target_id

    async def store_mapping(
        self, source_id, source_type, target_id, target_type, confidence, metadata=None
    ):
        """Store a mapping in the cache."""
        logger.info(
            f"Storing mapping: {source_id} ({source_type}) -> {target_id} ({target_type})"
        )
        return True


class MockResourceAdapter:
    """A mock adapter for testing when API is unavailable."""

    def __init__(self, name, db_connection):
        self.name = name
        self.conn = db_connection
        self.cursor = db_connection.cursor()

    async def connect(self):
        """Connect to the resource."""
        return True

    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """Map an entity from source to target type."""
        logger.info(
            f"Mapping {source_id} from {source_type} to {target_type} using {self.name}"
        )

        # Create a realistic mock mapping result
        if source_type.lower() == "hmdb" and target_type.lower() == "chebi":
            results = [
                {
                    "target_id": "CHEBI:16240",  # Actual ChEBI ID for some metabolite
                    "source": self.name,
                    "confidence": 0.95,
                    "metadata": {},
                }
            ]
        elif source_type.lower() == "chebi" and target_type.lower() == "hmdb":
            results = [
                {
                    "target_id": "HMDB0000001",  # Actual HMDB ID
                    "source": self.name,
                    "confidence": 0.95,
                    "metadata": {},
                }
            ]
        else:
            # Generic mapping for other types
            results = [
                {
                    "target_id": f"{target_type}_mapped_{source_id}",
                    "source": self.name,
                    "confidence": 0.8,
                    "metadata": {},
                }
            ]

        return results

    async def store_mapping(
        self, source_id, source_type, target_id, target_type, confidence, metadata=None
    ):
        """Store a mapping in the cache."""
        logger.info(
            f"Storing mapping: {source_id} ({source_type}) -> {target_id} ({target_type})"
        )
        return True


class SimpleMetadataManager:
    """A simplified metadata manager for testing."""

    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()

    def get_all_ontology_types(self):
        """Get all ontology types from the database."""
        self.cursor.execute(
            """
            SELECT DISTINCT source_type FROM mapping_paths
            UNION
            SELECT DISTINCT target_type FROM mapping_paths
        """
        )
        return [row[0].lower() for row in self.cursor.fetchall()]

    def find_resources_by_capability(self, source_type, target_type):
        """Find resources that can map between source and target types."""
        # For POC, return our test resources
        return [{"name": "sqlite_cache"}, {"name": "test_resource"}]

    def update_performance_metrics(
        self, resource_name, operation, source_type, target_type, elapsed_ms, success
    ):
        """Update performance metrics for a resource."""
        logger.info(
            f"Updated performance metrics for {resource_name}: {elapsed_ms}ms, success={success}"
        )
        return True


class SimpleDispatcher:
    """A simplified mapping dispatcher for testing."""

    def __init__(self, metadata_manager, db_connection):
        self.metadata_manager = metadata_manager
        # Use both real and mock adapters
        self.resource_adapters = {
            "sqlite_cache": MockResourceAdapter("sqlite_cache", db_connection),
            "unichem": UniChemAdapter("unichem", db_connection),
            "test_resource": MockResourceAdapter("test_resource", db_connection),
        }

        # Test connect to UniChem
        logger.info("Initializing connection to UniChem API")


from collections import deque
import time


class SimpleMetamappingEngine:
    """A simplified metamapping engine for testing."""

    def __init__(self, dispatcher, max_path_length=3):
        self.dispatcher = dispatcher
        self.metadata_manager = dispatcher.metadata_manager
        self.max_path_length = max_path_length

    async def find_mapping_path(self, source_type, target_type):
        """Find a mapping path from source to target type."""
        logger.info(f"Finding mapping path from {source_type} to {target_type}")

        # For POC, retrieve a path from the database
        self.metadata_manager.cursor.execute(
            """
            SELECT id, path_steps FROM mapping_paths
            WHERE LOWER(source_type) = LOWER(?) AND LOWER(target_type) = LOWER(?)
            ORDER BY performance_score DESC LIMIT 1
        """,
            (source_type, target_type),
        )

        row = self.metadata_manager.cursor.fetchone()

        if not row:
            logger.warning(f"No path found from {source_type} to {target_type}")
            return None

        # Parse path steps from JSON
        steps = json.loads(row[1]) if row[1] else []

        # If no steps, create a direct path
        if not steps:
            steps = [source_type, target_type]

        logger.info(f"Path steps: {steps}")

        # Format the path for the metamapping engine
        path = []
        for i in range(len(steps) - 1):
            path.append(
                {
                    "source_type": steps[i],
                    "target_type": steps[i + 1],
                    "resources": self.metadata_manager.find_resources_by_capability(
                        steps[i], steps[i + 1]
                    ),
                }
            )

        formatted_steps = [f"{p['source_type']} → {p['target_type']}" for p in path]
        logger.info(f"Formatted path: {formatted_steps}")
        return path

    async def execute_mapping_path(
        self, source_id, mapping_path, relationship_id=None, **kwargs
    ):
        """Execute a mapping path."""
        logger.info(f"Executing mapping path for {source_id}")
        path_desc = [
            f"{step['source_type']} → {step['target_type']}" for step in mapping_path
        ]
        logger.info(f"Path steps: {path_desc}")

        if not mapping_path:
            logger.warning("No mapping path provided")
            return []

        current_ids = [{"id": source_id, "confidence": 1.0}]
        results = []

        # Record the full path for mapping cache
        path_json = json.dumps(
            [
                {"source": step["source_type"], "target": step["target_type"]}
                for step in mapping_path
            ]
        )

        # Execution for POC - prioritize using the real UniChem adapter
        for step_index, step in enumerate(mapping_path):
            source_type = step["source_type"]
            target_type = step["target_type"]

            # Override resources to prefer UniChem
            resources = [{"name": "unichem"}]

            logger.info(
                f"Step {step_index+1}: Mapping from {source_type} to {target_type}"
            )
            logger.info(
                f"Current IDs to map: {[id_info['id'] for id_info in current_ids]}"
            )

            next_ids = []
            for id_info in current_ids:
                current_id = id_info["id"]
                base_confidence = id_info["confidence"]

                # Try UniChem first, then fallback to others
                success = False
                resource_used = None

                # Explicitly try UniChem
                try:
                    logger.info(f"Trying to map {current_id} with UniChem")
                    unichem_adapter = self.dispatcher.resource_adapters["unichem"]
                    step_results = await unichem_adapter.map_entity(
                        current_id, source_type, target_type
                    )

                    if step_results:
                        logger.info(f"UniChem returned {len(step_results)} results")
                        success = True
                        resource_used = "unichem"
                        for result in step_results:
                            next_ids.append(
                                {
                                    "id": result["target_id"],
                                    "confidence": base_confidence
                                    * result.get("confidence", 1.0),
                                    "source": "unichem",
                                    "metadata": result.get("metadata", {}),
                                }
                            )
                except Exception as e:
                    logger.error(f"Error in UniChem mapping: {e}")

                # If UniChem failed, try the test resource
                if not success:
                    try:
                        logger.info(f"Falling back to test_resource for {current_id}")
                        test_adapter = self.dispatcher.resource_adapters[
                            "test_resource"
                        ]
                        step_results = await test_adapter.map_entity(
                            current_id, source_type, target_type
                        )

                        if step_results:
                            logger.info(
                                f"Test resource returned {len(step_results)} results"
                            )
                            resource_used = "test_resource"
                            for result in step_results:
                                next_ids.append(
                                    {
                                        "id": result["target_id"],
                                        "confidence": base_confidence
                                        * result.get("confidence", 1.0),
                                        "source": "test_resource",
                                        "metadata": result.get("metadata", {}),
                                    }
                                )
                    except Exception as e:
                        logger.error(f"Error in test_resource mapping: {e}")

            if not next_ids:
                logger.warning(
                    f"Mapping path failed at step {source_type} -> {target_type}"
                )
                return []

            current_ids = next_ids
            logger.info(
                f"After step {step_index+1}, we have {len(current_ids)} mapped entities"
            )

        # Format results
        for id_info in current_ids:
            results.append(
                {
                    "target_id": id_info["id"],
                    "confidence": id_info["confidence"],
                    "source": "metamapping",
                    "metadata": {
                        "mapping_path": id_info.get("path", []),
                        **id_info.get("metadata", {}),
                    },
                }
            )

        # Store the results in the mapping_cache if we have a relationship_id
        if relationship_id and results:
            logger.info(f"Storing {len(results)} mapping results in cache")
            try:
                # Get the first source and target types from the path
                source_type = mapping_path[0]["source_type"]
                target_type = mapping_path[-1]["target_type"]

                # Get resource ID (use 10 for UniChem as default)
                resource_id = 10  # UniChem

                for result in results:
                    # Insert into mapping_cache - use the metadata manager connection
                    self.metadata_manager.cursor.execute(
                        """
                        INSERT INTO mapping_cache
                        (source_id, source_type, target_id, target_type, confidence, mapping_path, resource_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            source_id,
                            source_type,
                            result["target_id"],
                            target_type,
                            result["confidence"],
                            path_json,
                            resource_id,
                        ),
                    )

                    # Get the mapping_id for the relationship_mappings table
                    mapping_id = self.metadata_manager.cursor.lastrowid

                    # Link to the relationship
                    self.metadata_manager.cursor.execute(
                        """
                        INSERT INTO relationship_mappings
                        (relationship_id, mapping_id)
                        VALUES (?, ?)
                    """,
                        (relationship_id, mapping_id),
                    )

                self.metadata_manager.conn.commit()
                logger.info("Successfully stored mapping results in database")
            except Exception as e:
                logger.error(f"Error storing mapping results: {e}")
                self.metadata_manager.conn.rollback()

        return results


class RelationshipMappingExecutor:
    """Executes endpoint-to-endpoint mappings using metamapping."""

    def __init__(self, db_connection):
        """Initialize with database connection and metamapping engine."""
        self.conn = db_connection
        self.cursor = db_connection.cursor()

        # Set up the metamapping components
        metadata_manager = SimpleMetadataManager(db_connection)
        dispatcher = SimpleDispatcher(metadata_manager, db_connection)
        self.metamapping_engine = SimpleMetamappingEngine(dispatcher)

        # Initialize path finder for relationship operations
        self.path_finder = RelationshipPathFinder(db_connection)

    async def map_entity(self, relationship_id, source_entity, source_ontology=None):
        """Map an entity using the relationship and metamapping engine."""
        # Check if we already have a cached mapping result
        cached_result = self.path_finder._get_cached_mapping(
            relationship_id, source_entity, source_ontology
        )
        if cached_result:
            logger.info(f"Found cached mapping for {source_entity}")
            return [cached_result]

        # Get the best mapping path for this relationship and ontology
        path_info = self._get_best_relationship_path(relationship_id, source_ontology)

        if not path_info:
            logger.warning(
                f"No relationship mapping path found for {relationship_id}/{source_ontology}"
            )
            return []

        logger.info(
            f"Found relationship path: {path_info['source_ontology']} → {path_info['target_ontology']}"
        )

        # Get the ontology mapping path
        ontology_path_id = path_info["ontology_path_id"]
        ontology_path = self._get_ontology_path(ontology_path_id)

        if not ontology_path:
            logger.warning(f"Could not find ontology path with ID {ontology_path_id}")
            return []

        logger.info(
            f"Ontology path: {ontology_path['source_type']} → {ontology_path['target_type']}"
        )
        logger.info(f"Path steps: {ontology_path['path_steps']}")

        # Convert ontology path to metamapping format
        mapping_path = []
        path_steps = ontology_path["path_steps"]

        # Ensure we have at least source and target in the path
        if not path_steps:
            path_steps = [path_info["source_ontology"], path_info["target_ontology"]]

        # If we only have a single step, make sure we have source and target
        if len(path_steps) < 2:
            path_steps = [path_info["source_ontology"], path_info["target_ontology"]]

        logger.info(f"Using path steps: {path_steps}")

        for i in range(len(path_steps) - 1):
            mapping_path.append(
                {
                    "source_type": path_steps[i],
                    "target_type": path_steps[i + 1],
                    "resources": [{"name": "unichem"}, {"name": "test_resource"}],
                }
            )

        # Make sure we have at least one step
        if not mapping_path:
            logger.warning("No mapping steps created!")
            # Create a direct mapping step
            mapping_path = [
                {
                    "source_type": path_info["source_ontology"],
                    "target_type": path_info["target_ontology"],
                    "resources": [{"name": "unichem"}, {"name": "test_resource"}],
                }
            ]

        # Execute the mapping path
        results = await self.metamapping_engine.execute_mapping_path(
            source_entity, mapping_path, relationship_id=relationship_id
        )

        if results:
            # Update usage statistics
            self._update_path_usage(path_info["id"])

        return results

    def _get_best_relationship_path(self, relationship_id, source_ontology):
        """Get the best mapping path for a relationship and source ontology."""
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

        return None

    def _get_ontology_path(self, path_id):
        """Get ontology mapping path by ID."""
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
            # Parse path steps from JSON, ensuring we have a list
            raw_steps = row[3]
            try:
                if raw_steps and raw_steps.strip():
                    steps = json.loads(raw_steps)
                else:
                    steps = [row[1], row[2]]

                # Make sure steps is a list
                if not isinstance(steps, list):
                    steps = [row[1], row[2]]
            except Exception as e:
                logger.error(f"Error parsing path steps: {e}")
                steps = [row[1], row[2]]

            return {
                "id": row[0],
                "source_type": row[1],
                "target_type": row[2],
                "path_steps": steps,
                "performance_score": row[4],
            }

        return None

    def _update_path_usage(self, path_id):
        """Update usage statistics for a path."""
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
            logger.error(f"Error updating path usage: {e}")
            self.conn.rollback()
            return False


class RelationshipPathFinder:
    """Discovers mapping paths for endpoint relationships."""

    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()

    def _get_cached_mapping(self, relationship_id, source_id, source_ontology):
        """Get a cached mapping result for a source entity."""
        try:
            self.cursor.execute(
                """
                SELECT c.target_id, c.target_type, c.confidence
                FROM mapping_cache c
                JOIN relationship_mappings r ON c.mapping_id = r.mapping_id
                WHERE r.relationship_id = ?
                AND c.source_id = ?
                AND c.source_type = ?
                ORDER BY c.confidence DESC LIMIT 1
            """,
                (relationship_id, source_id, source_ontology),
            )

            row = self.cursor.fetchone()
            if row:
                logger.info(f"Found cached mapping: {source_id} → {row[0]} ({row[2]})")
                return {
                    "target_id": row[0],
                    "target_type": row[1],
                    "confidence": row[2],
                    "source": "cache",
                    "metadata": {"from_cache": True},
                }
        except Exception as e:
            logger.error(f"Error getting cached mapping: {e}")

        return None

    async def discover_paths_for_relationship(self, relationship_id):
        """Find and store optimal mapping paths for a relationship."""
        logger.info(f"Discovering paths for relationship {relationship_id}")

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
            logger.warning(
                f"Relationship {relationship_id} is missing source or target endpoint"
            )
            return []

        logger.info(f"Found endpoints for relationship: {endpoints}")

        # Get ontology preferences for both endpoints
        source_prefs = self._get_ontology_preferences(endpoints["source"]["id"])
        target_prefs = self._get_ontology_preferences(endpoints["target"]["id"])

        if not source_prefs:
            logger.warning(
                f"No ontology preferences for source endpoint {endpoints['source']['id']}"
            )
            # Add default preferences for testing
            source_prefs = [("hmdb", 1), ("chebi", 2), ("pubchem", 3)]

        if not target_prefs:
            logger.warning(
                f"No ontology preferences for target endpoint {endpoints['target']['id']}"
            )
            # Add default preferences for testing
            target_prefs = [("chebi", 1), ("pubchem", 2), ("hmdb", 3)]

        logger.info(f"Source preferences: {source_prefs}")
        logger.info(f"Target preferences: {target_prefs}")

        # Find paths between ontology types
        paths = []
        for source_ont, source_pref in source_prefs:
            for target_ont, target_pref in target_prefs:
                # Find a mapping path
                ont_paths = self._find_ontology_paths(source_ont, target_ont)

                if not ont_paths:
                    logger.warning(
                        f"No ontology paths found from {source_ont} to {target_ont}"
                    )
                    continue

                for path in ont_paths:
                    # Calculate a score based on preferences
                    score = 1.0 / (source_pref + target_pref)

                    # Store in the relationship_mapping_paths table
                    success = self._store_relationship_path(
                        relationship_id, source_ont, target_ont, path["id"], score
                    )

                    if success:
                        paths.append({"path": path, "score": score})

        logger.info(
            f"Discovered {len(paths)} mapping paths for relationship {relationship_id}"
        )
        return paths

    def _get_ontology_preferences(self, endpoint_id):
        """Get ordered ontology preferences for an endpoint."""
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
        """Find all mapping paths between two ontology types."""
        # Try direct path first
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
            # Parse path steps from JSON, ensuring we have a list
            raw_steps = row[3]
            try:
                if raw_steps and raw_steps.strip():
                    steps = json.loads(raw_steps)
                else:
                    steps = [row[1], row[2]]

                # Make sure steps is a list
                if not isinstance(steps, list):
                    steps = [row[1], row[2]]
            except Exception as e:
                logger.error(f"Error parsing path steps: {e}")
                steps = [row[1], row[2]]

            paths.append(
                {
                    "id": row[0],
                    "source_type": row[1],
                    "target_type": row[2],
                    "path_steps": steps,
                    "performance_score": row[4],
                }
            )

        return paths

    def _store_relationship_path(
        self, relationship_id, source_ont, target_ont, path_id, score
    ):
        """Store a relationship mapping path in the database."""
        try:
            # Check if it already exists
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
                     ontology_path_id, performance_score, last_discovered, usage_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        relationship_id,
                        source_ont,
                        target_ont,
                        path_id,
                        score,
                        datetime.now().isoformat(),
                        0,
                    ),
                )

            self.conn.commit()
            logger.info(
                f"Stored relationship path: {source_ont} → {target_ont} (score: {score})"
            )
            return True
        except Exception as e:
            logger.error(f"Error storing relationship path: {e}")
            self.conn.rollback()
            return False


async def main():
    """Main entry point for the POC."""
    logger.info("Starting MetamappingEngine POC")

    # Connect to the database
    db_path = "/home/ubuntu/biomapper/data/metamapper.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Select a relationship ID (MetabolitesCSV to SPOKE)
    relationship_id = 1  # ID from the database

    # First, discover and store mapping paths
    path_finder = RelationshipPathFinder(conn)
    discovered_paths = await path_finder.discover_paths_for_relationship(
        relationship_id
    )

    if not discovered_paths:
        logger.warning("No paths discovered. Cannot proceed with mapping.")
        conn.close()
        return

    # Create the relationship mapping executor
    executor = RelationshipMappingExecutor(conn)

    # Get all relationship mapping paths for this relationship (should have some after discovery)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, source_ontology, target_ontology, ontology_path_id, performance_score, usage_count
        FROM relationship_mapping_paths
        WHERE relationship_id = ?
        ORDER BY performance_score DESC
    """,
        (relationship_id,),
    )

    paths = cursor.fetchall()

    logger.info(
        f"Found {len(paths)} relationship mapping paths for relationship {relationship_id}"
    )

    if paths:
        # Take the first path and use its source ontology
        first_path = paths[0]
        source_ontology = first_path["source_ontology"]

        logger.info(f"Using source ontology: {source_ontology}")

        # Sample metabolite ID (you can replace with an actual ID from your data)
        metabolite_id = "HMDB0000001"  # For HMDB ontology

        logger.info(f"Mapping {metabolite_id} from {source_ontology} to SPOKE")

        # Try with a known HMDB ID for a real test
        real_metabolite_ids = [
            "HMDB0000123",  # Glycine - well known and widely mapped compound
            "HMDB0000517",  # L-Arginine - widely used and mapped amino acid
            "HMDB0000929",  # Tryptophan - another well-known amino acid
        ]

        # Try each ID
        for test_id in real_metabolite_ids:
            logger.info(f"\n=== Testing with {test_id} ===\n")

            # Execute the mapping
            results = await executor.map_entity(
                relationship_id=relationship_id,
                source_entity=test_id,
                source_ontology=source_ontology,
            )

            if results:
                logger.info(f"Mapped {test_id} to SPOKE:")
                for result in results:
                    logger.info(
                        f"  {result['target_id']} (confidence: {result['confidence']})"
                    )
                # If we got results, no need to try other IDs
                break
            else:
                logger.warning(f"No mapping results found for {test_id}")
        # Results are already logged in the loop above
    else:
        logger.warning(
            f"No relationship mapping paths found for relationship {relationship_id}"
        )

    conn.close()
    logger.info("POC completed")


if __name__ == "__main__":
    asyncio.run(main())

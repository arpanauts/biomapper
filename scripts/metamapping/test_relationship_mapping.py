#!/usr/bin/env python
"""
Test script for metamapping between endpoints.

This script tests the metamapping functionality between MetabolitesCSV and SPOKE
endpoints, creating a relationship, discovering mapping paths, and executing
mappings with sample data.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional

# Add project root to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from biomapper.db.session import get_session
from biomapper.mapping.metadata.manager import ResourceMetadataManager
from biomapper.mapping.metadata.dispatcher import MappingDispatcher
from biomapper.mapping.health import PropertyHealthTracker, EndpointHealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_endpoint_relationship(db_session, name: str, description: str) -> int:
    """
    Create a relationship between endpoints.

    Args:
        db_session: Database session
        name: Relationship name
        description: Relationship description

    Returns:
        int: New relationship ID
    """
    try:
        # Check if relationship already exists
        existing = db_session.execute(
            "SELECT relationship_id FROM endpoint_relationships WHERE name = :name",
            {"name": name},
        ).fetchone()

        if existing:
            logger.info(
                f"Relationship '{name}' already exists with ID {existing.relationship_id}"
            )
            return existing.relationship_id

        # Insert new relationship
        result = db_session.execute(
            """INSERT INTO endpoint_relationships (name, description, created_at)
               VALUES (:name, :description, CURRENT_TIMESTAMP)
               RETURNING relationship_id""",
            {"name": name, "description": description},
        )
        relationship_id = result.fetchone()[0]
        db_session.commit()

        logger.info(f"Created relationship '{name}' with ID {relationship_id}")
        return relationship_id

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating relationship: {e}")
        raise


async def add_relationship_member(
    db_session,
    relationship_id: int,
    endpoint_id: int,
    role: str = "member",
    priority: int = 0,
) -> bool:
    """
    Add an endpoint as a member of a relationship.

    Args:
        db_session: Database session
        relationship_id: Relationship ID
        endpoint_id: Endpoint ID
        role: Role in the relationship (source, target, etc.)
        priority: Priority in the relationship

    Returns:
        bool: Success flag
    """
    try:
        # Check if member already exists
        existing = db_session.execute(
            """SELECT * FROM endpoint_relationship_members 
               WHERE relationship_id = :relationship_id AND endpoint_id = :endpoint_id""",
            {"relationship_id": relationship_id, "endpoint_id": endpoint_id},
        ).fetchone()

        if existing:
            logger.info(
                f"Endpoint {endpoint_id} is already a member of relationship {relationship_id}"
            )

            # Update role and priority if different
            if existing.role != role or existing.priority != priority:
                db_session.execute(
                    """UPDATE endpoint_relationship_members 
                       SET role = :role, priority = :priority
                       WHERE relationship_id = :relationship_id AND endpoint_id = :endpoint_id""",
                    {
                        "relationship_id": relationship_id,
                        "endpoint_id": endpoint_id,
                        "role": role,
                        "priority": priority,
                    },
                )
                db_session.commit()
                logger.info(f"Updated role to '{role}' and priority to {priority}")

            return True

        # Add member
        db_session.execute(
            """INSERT INTO endpoint_relationship_members 
               (relationship_id, endpoint_id, role, priority)
               VALUES (:relationship_id, :endpoint_id, :role, :priority)""",
            {
                "relationship_id": relationship_id,
                "endpoint_id": endpoint_id,
                "role": role,
                "priority": priority,
            },
        )
        db_session.commit()

        logger.info(
            f"Added endpoint {endpoint_id} to relationship {relationship_id} with role '{role}'"
        )
        return True

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error adding relationship member: {e}")
        return False


async def get_endpoint_id_by_name(db_session, name: str) -> Optional[int]:
    """
    Get endpoint ID by name.

    Args:
        db_session: Database session
        name: Endpoint name

    Returns:
        int: Endpoint ID or None if not found
    """
    result = db_session.execute(
        "SELECT endpoint_id FROM endpoints WHERE name = :name", {"name": name}
    ).fetchone()

    return result.endpoint_id if result else None


async def find_mapping_paths(
    db_session,
    source_endpoint_id: int,
    target_endpoint_id: int,
    metadata_manager: Optional[ResourceMetadataManager] = None,
) -> List[Dict[str, Any]]:
    """
    Find mapping paths between endpoints.

    Args:
        db_session: Database session
        source_endpoint_id: Source endpoint ID
        target_endpoint_id: Target endpoint ID
        metadata_manager: Optional ResourceMetadataManager

    Returns:
        List of mapping paths
    """
    try:
        # Get source endpoint info
        source_endpoint = db_session.execute(
            "SELECT * FROM endpoints WHERE endpoint_id = :id",
            {"id": source_endpoint_id},
        ).fetchone()

        if not source_endpoint:
            logger.error(f"Source endpoint {source_endpoint_id} not found")
            return []

        # Get target endpoint info
        target_endpoint = db_session.execute(
            "SELECT * FROM endpoints WHERE endpoint_id = :id",
            {"id": target_endpoint_id},
        ).fetchone()

        if not target_endpoint:
            logger.error(f"Target endpoint {target_endpoint_id} not found")
            return []

        logger.info(
            f"Finding mapping paths from {source_endpoint.name} to {target_endpoint.name}"
        )

        # Get source ontology preferences
        source_prefs = db_session.execute(
            """SELECT ontology_type, preference_level FROM endpoint_ontology_preferences
               WHERE endpoint_id = :id
               ORDER BY preference_level DESC""",
            {"id": source_endpoint_id},
        ).fetchall()

        if not source_prefs:
            logger.warning(
                f"No ontology preferences defined for source endpoint {source_endpoint_id}"
            )
            return []

        # Get target ontology preferences
        target_prefs = db_session.execute(
            """SELECT ontology_type, preference_level FROM endpoint_ontology_preferences
               WHERE endpoint_id = :id
               ORDER BY preference_level DESC""",
            {"id": target_endpoint_id},
        ).fetchall()

        if not target_prefs:
            logger.warning(
                f"No ontology preferences defined for target endpoint {target_endpoint_id}"
            )
            return []

        # See if we already have property configs for the preferences
        source_configs = {}
        for pref in source_prefs:
            config = db_session.execute(
                """SELECT * FROM endpoint_property_configs
                   WHERE endpoint_id = :endpoint_id AND ontology_type = :ontology_type""",
                {
                    "endpoint_id": source_endpoint_id,
                    "ontology_type": pref.ontology_type,
                },
            ).fetchone()

            if config:
                source_configs[pref.ontology_type] = config

        target_configs = {}
        for pref in target_prefs:
            config = db_session.execute(
                """SELECT * FROM endpoint_property_configs
                   WHERE endpoint_id = :endpoint_id AND ontology_type = :ontology_type""",
                {
                    "endpoint_id": target_endpoint_id,
                    "ontology_type": pref.ontology_type,
                },
            ).fetchone()

            if config:
                target_configs[pref.ontology_type] = config

        # Log preferences and configs
        logger.info(f"Source preferences: {[p.ontology_type for p in source_prefs]}")
        logger.info(f"Source configs: {list(source_configs.keys())}")
        logger.info(f"Target preferences: {[p.ontology_type for p in target_prefs]}")
        logger.info(f"Target configs: {list(target_configs.keys())}")

        # Find direct mapping paths (source ontology -> target ontology)
        direct_paths = []

        # If we have ResourceMetadataManager, use it to find mappable paths
        if metadata_manager:
            for source_pref in source_prefs:
                for target_pref in target_prefs:
                    source_type = source_pref.ontology_type
                    target_type = target_pref.ontology_type

                    # Skip if we don't have configs for either type
                    if (
                        source_type not in source_configs
                        or target_type not in target_configs
                    ):
                        continue

                    # Check if mapping is possible
                    resources = metadata_manager.find_resources_by_capability(
                        source_type=source_type, target_type=target_type
                    )

                    if resources:
                        logger.info(
                            f"Found direct mapping path: {source_type} -> {target_type}"
                        )
                        direct_paths.append(
                            {
                                "source_endpoint_id": source_endpoint_id,
                                "target_endpoint_id": target_endpoint_id,
                                "source_type": source_type,
                                "target_type": target_type,
                                "resources": resources,
                                "steps": 1,
                                "confidence": 0.9,  # Direct mapping has high confidence
                            }
                        )

        # For demo purposes, if we don't have ResourceMetadataManager or no direct paths found,
        # create sample paths
        if not direct_paths:
            # Find common types that could be used as intermediates
            intermediate_types = [
                "hmdb",
                "pubchem",
                "chebi",
                "kegg",
                "inchikey",
                "smiles",
            ]

            # Create some sample paths
            sample_paths = []

            # Try to match source and target types
            for source_pref in source_prefs:
                source_type = source_pref.ontology_type
                if source_type not in source_configs:
                    continue

                for target_pref in target_prefs:
                    target_type = target_pref.ontology_type
                    if target_type not in target_configs:
                        continue

                    # Direct path
                    sample_paths.append(
                        {
                            "source_endpoint_id": source_endpoint_id,
                            "target_endpoint_id": target_endpoint_id,
                            "source_type": source_type,
                            "target_type": target_type,
                            "steps": 1,
                            "path": [
                                {"from_type": source_type, "to_type": target_type}
                            ],
                            "confidence": 0.9,
                        }
                    )

                    # For some combinations, add multi-step paths
                    if source_type == "hmdb" and target_type == "chebi":
                        sample_paths.append(
                            {
                                "source_endpoint_id": source_endpoint_id,
                                "target_endpoint_id": target_endpoint_id,
                                "source_type": source_type,
                                "target_type": target_type,
                                "steps": 2,
                                "path": [
                                    {"from_type": "hmdb", "to_type": "pubchem"},
                                    {"from_type": "pubchem", "to_type": "chebi"},
                                ],
                                "confidence": 0.8,
                            }
                        )
                    elif source_type == "pubchem" and target_type == "hmdb":
                        sample_paths.append(
                            {
                                "source_endpoint_id": source_endpoint_id,
                                "target_endpoint_id": target_endpoint_id,
                                "source_type": source_type,
                                "target_type": target_type,
                                "steps": 2,
                                "path": [
                                    {"from_type": "pubchem", "to_type": "chebi"},
                                    {"from_type": "chebi", "to_type": "hmdb"},
                                ],
                                "confidence": 0.8,
                            }
                        )

            return sample_paths

        return direct_paths

    except Exception as e:
        logger.error(f"Error finding mapping paths: {e}")
        return []


async def save_mapping_path(db_session, path: Dict[str, Any]) -> Optional[int]:
    """
    Save a mapping path to the database.

    Args:
        db_session: Database session
        path: Mapping path details

    Returns:
        int: Path ID or None if failed
    """
    try:
        # Check if we already have this path
        existing = db_session.execute(
            """SELECT id FROM mapping_paths
               WHERE source_type = :source_type
               AND target_type = :target_type""",
            {"source_type": path["source_type"], "target_type": path["target_type"]},
        ).fetchone()

        if existing:
            logger.info(f"Mapping path already exists with ID {existing.id}")
            return existing.id

        # Convert path details to JSON
        path_json = json.dumps(path.get("path", []))

        # Insert new path - adapt to existing schema
        result = db_session.execute(
            """INSERT INTO mapping_paths
               (source_type, target_type, path_steps, performance_score, success_rate)
               VALUES (:source_type, :target_type, :path_steps, :performance_score, :success_rate)
               RETURNING id""",
            {
                "source_type": path["source_type"],
                "target_type": path["target_type"],
                "path_steps": path_json,
                "performance_score": path.get("confidence", 0.5),
                "success_rate": 0.8,  # Default success rate
            },
        )
        path_id = result.fetchone()[0]
        db_session.commit()

        logger.info(f"Saved mapping path with ID {path_id}")
        return path_id

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving mapping path: {e}")
        return None


async def get_sample_data(
    db_session, endpoint_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get sample data for an endpoint.

    Args:
        db_session: Database session
        endpoint_id: Endpoint ID
        limit: Maximum number of samples

    Returns:
        List of sample data items
    """
    # Get endpoint info
    endpoint = db_session.execute(
        "SELECT * FROM endpoints WHERE endpoint_id = :id", {"id": endpoint_id}
    ).fetchone()

    if not endpoint:
        logger.error(f"Endpoint {endpoint_id} not found")
        return []

    # For demo purposes, create some sample data based on endpoint type
    if endpoint.name == "MetabolitesCSV":
        return [
            {
                "HMDB": "HMDB0000001",
                "BIOCHEMICAL_NAME": "1-Methylhistidine",
                "KEGG": "C01152",
                "PUBCHEM": "92865",
            },
            {
                "HMDB": "HMDB0000002",
                "BIOCHEMICAL_NAME": "1,3-Diaminopropane",
                "KEGG": "C00986",
                "PUBCHEM": "428",
            },
            {
                "HMDB": "HMDB0000005",
                "BIOCHEMICAL_NAME": "2-Ketobutyric acid",
                "KEGG": "C00109",
                "PUBCHEM": "58",
            },
            {
                "HMDB": "HMDB0000008",
                "BIOCHEMICAL_NAME": "2-Hydroxybutyric acid",
                "KEGG": "C05984",
                "PUBCHEM": "11266",
            },
            {
                "HMDB": "HMDB0000010",
                "BIOCHEMICAL_NAME": "2-Methoxyestrone",
                "KEGG": "",
                "PUBCHEM": "5284485",
            },
        ]
    elif endpoint.name == "SPOKE":
        return [
            {"identifier": "CHEBI:15377", "name": "water", "source": "ChEBI"},
            {"identifier": "CHEBI:27732", "name": "glucose", "source": "ChEBI"},
            {
                "identifier": "HMDB0000001",
                "name": "1-Methylhistidine",
                "source": "HMDB",
            },
            {
                "identifier": "HMDB0000002",
                "name": "1,3-Diaminopropane",
                "source": "HMDB",
            },
            {"identifier": "CID123456", "name": "Caffeine", "source": "PubChem"},
        ]
    else:
        logger.warning(f"No sample data available for endpoint type {endpoint.name}")
        return []


async def extract_property(
    db_session,
    endpoint_id: int,
    ontology_type: str,
    property_name: str,
    data: Dict[str, Any],
) -> Any:
    """
    Extract a property from data using the endpoint's property config.

    Args:
        db_session: Database session
        endpoint_id: Endpoint ID
        ontology_type: Ontology type
        property_name: Property name
        data: Data to extract from

    Returns:
        Extracted property value
    """
    try:
        # Get property config
        config = db_session.execute(
            """SELECT * FROM endpoint_property_configs
               WHERE endpoint_id = :endpoint_id
               AND ontology_type = :ontology_type
               AND property_name = :property_name""",
            {
                "endpoint_id": endpoint_id,
                "ontology_type": ontology_type,
                "property_name": property_name,
            },
        ).fetchone()

        if not config:
            logger.error(
                f"No property config found for {endpoint_id}/{ontology_type}/{property_name}"
            )
            return None

        # Parse extraction pattern
        pattern = json.loads(config.extraction_pattern)

        # Extract based on method
        if config.extraction_method == "column":
            column_name = pattern.get("column_name")
            if not column_name or column_name not in data:
                logger.warning(f"Column {column_name} not found in data")
                return None

            return data[column_name]

        elif config.extraction_method == "pattern":
            import re

            regex = re.compile(pattern.get("pattern", ""))
            group = pattern.get("group", 0)

            # Apply pattern to relevant field
            field = pattern.get("field", "identifier")
            if field not in data:
                logger.warning(f"Field {field} not found in data")
                return None

            match = regex.match(data[field])
            if not match:
                return None

            try:
                return match.group(group)
            except IndexError:
                logger.warning(f"Group {group} not found in match")
                return None

        elif config.extraction_method == "query":
            # Not implemented for demo
            logger.warning("Query extraction not implemented in demo")
            return None

        else:
            logger.warning(f"Unsupported extraction method: {config.extraction_method}")
            return None

    except Exception as e:
        logger.error(f"Error extracting property: {e}")
        return None


async def execute_mapping_path(
    source_id: str,
    source_type: str,
    target_type: str,
    path: Dict[str, Any],
    metadata_manager: Optional[ResourceMetadataManager] = None,
    dispatcher: Optional[MappingDispatcher] = None,
) -> List[Dict[str, Any]]:
    """
    Execute a mapping path to convert from source to target type.

    Args:
        source_id: Source identifier
        source_type: Source ontology type
        target_type: Target ontology type
        path: Mapping path details
        metadata_manager: Optional ResourceMetadataManager
        dispatcher: Optional MappingDispatcher

    Returns:
        List of mapping results
    """
    if not dispatcher or not metadata_manager:
        # For demo purposes, create some dummy mappings
        if source_type == "hmdb" and target_type == "chebi":
            if source_id == "HMDB0000001":
                return [{"target_id": "CHEBI:16737", "confidence": 0.9}]
            elif source_id == "HMDB0000002":
                return [{"target_id": "CHEBI:16526", "confidence": 0.95}]
            else:
                # Generate a dummy mapping
                return [
                    {
                        "target_id": f"CHEBI:{hash(source_id) % 100000}",
                        "confidence": 0.7,
                    }
                ]

        elif source_type == "pubchem" and target_type == "chebi":
            if source_id == "92865":
                return [{"target_id": "CHEBI:16737", "confidence": 0.85}]
            elif source_id == "428":
                return [{"target_id": "CHEBI:16526", "confidence": 0.9}]
            else:
                return [
                    {
                        "target_id": f"CHEBI:{hash(source_id) % 100000}",
                        "confidence": 0.75,
                    }
                ]

        # Default dummy mapping
        return [
            {
                "target_id": f"{target_type}_{hash(source_id) % 100000}",
                "confidence": 0.6,
            }
        ]

    # Use the actual dispatcher for mapping
    logger.info(f"Mapping {source_id} ({source_type}) to {target_type}")

    # If path has multiple steps, execute each step
    if path.get("steps", 1) > 1 and "path" in path:
        current_ids = [{"id": source_id, "confidence": 1.0}]

        for step in path["path"]:
            from_type = step["from_type"]
            to_type = step["to_type"]

            # Execute each step
            next_ids = []
            for id_info in current_ids:
                step_results = await dispatcher.map_entity(
                    source_id=id_info["id"], source_type=from_type, target_type=to_type
                )

                # Accumulate results with compounded confidence
                for result in step_results:
                    next_ids.append(
                        {
                            "id": result["target_id"],
                            "confidence": id_info["confidence"]
                            * result.get("confidence", 1.0),
                        }
                    )

            # If we couldn't map anything, the path failed
            if not next_ids:
                return []

            # Update current IDs for the next step
            current_ids = next_ids

        # Format final results
        return [
            {"target_id": id_info["id"], "confidence": id_info["confidence"]}
            for id_info in current_ids
        ]

    # For direct mapping
    return await dispatcher.map_entity(
        source_id=source_id, source_type=source_type, target_type=target_type
    )


async def main():
    """Main execution function."""
    # Use the existing metamapper.db database
    db_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
        "data/metamapper.db",
    )
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return

    logger.info(f"Using database at {db_path}")

    # Create a database manager with the specific path
    from biomapper.db.session import DatabaseManager

    db_manager = DatabaseManager(db_url=f"sqlite:///{db_path}")

    # Create a session using this manager
    db_session = db_manager.create_session()

    try:
        # Get endpoint IDs
        metabolites_id = await get_endpoint_id_by_name(db_session, "MetabolitesCSV")
        spoke_id = await get_endpoint_id_by_name(db_session, "SPOKE")

        # Create endpoints if they don't exist
        if not metabolites_id:
            logger.info("Creating MetabolitesCSV endpoint")
            result = db_session.execute(
                """INSERT INTO endpoints (name, description, endpoint_type, connection_info, created_at)
                   VALUES (:name, :description, :endpoint_type, :connection_info, CURRENT_TIMESTAMP)
                   RETURNING endpoint_id""",
                {
                    "name": "MetabolitesCSV",
                    "description": "Arivale metabolites data in CSV format",
                    "endpoint_type": "csv",
                    "connection_info": json.dumps(
                        {"file_path": "/data/metabolites.csv"}
                    ),
                },
            )
            metabolites_id = result.fetchone()[0]
            db_session.commit()

            # Add property configs
            db_session.execute(
                """INSERT INTO endpoint_property_configs 
                   (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern)
                   VALUES (:endpoint_id, :ontology_type, :property_name, :extraction_method, :extraction_pattern)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "hmdb",
                    "property_name": "HMDB ID",
                    "extraction_method": "column",
                    "extraction_pattern": json.dumps({"column_name": "HMDB"}),
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_property_configs 
                   (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern)
                   VALUES (:endpoint_id, :ontology_type, :property_name, :extraction_method, :extraction_pattern)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "pubchem",
                    "property_name": "PubChem ID",
                    "extraction_method": "column",
                    "extraction_pattern": json.dumps({"column_name": "PUBCHEM"}),
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_property_configs 
                   (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern)
                   VALUES (:endpoint_id, :ontology_type, :property_name, :extraction_method, :extraction_pattern)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "kegg",
                    "property_name": "KEGG ID",
                    "extraction_method": "column",
                    "extraction_pattern": json.dumps({"column_name": "KEGG"}),
                },
            )

            # Add ontology preferences
            db_session.execute(
                """INSERT INTO endpoint_ontology_preferences
                   (endpoint_id, ontology_type, preference_level)
                   VALUES (:endpoint_id, :ontology_type, :preference_level)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "hmdb",
                    "preference_level": 3,
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_ontology_preferences
                   (endpoint_id, ontology_type, preference_level)
                   VALUES (:endpoint_id, :ontology_type, :preference_level)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "pubchem",
                    "preference_level": 2,
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_ontology_preferences
                   (endpoint_id, ontology_type, preference_level)
                   VALUES (:endpoint_id, :ontology_type, :preference_level)""",
                {
                    "endpoint_id": metabolites_id,
                    "ontology_type": "kegg",
                    "preference_level": 1,
                },
            )

            db_session.commit()

        if not spoke_id:
            logger.info("Creating SPOKE endpoint")
            result = db_session.execute(
                """INSERT INTO endpoints (name, description, endpoint_type, connection_info, created_at)
                   VALUES (:name, :description, :endpoint_type, :connection_info, CURRENT_TIMESTAMP)
                   RETURNING endpoint_id""",
                {
                    "name": "SPOKE",
                    "description": "SPOKE Knowledge Graph",
                    "endpoint_type": "graph",
                    "connection_info": json.dumps({"url": "http://spoke.server/api"}),
                },
            )
            spoke_id = result.fetchone()[0]
            db_session.commit()

            # Add property configs
            db_session.execute(
                """INSERT INTO endpoint_property_configs 
                   (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern)
                   VALUES (:endpoint_id, :ontology_type, :property_name, :extraction_method, :extraction_pattern)""",
                {
                    "endpoint_id": spoke_id,
                    "ontology_type": "chebi",
                    "property_name": "ChEBI ID",
                    "extraction_method": "query",
                    "extraction_pattern": json.dumps(
                        {
                            "aql": "FOR c IN Compound FILTER c.identifier == @id AND c.source == 'ChEBI' RETURN c"
                        }
                    ),
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_property_configs 
                   (endpoint_id, ontology_type, property_name, extraction_method, extraction_pattern)
                   VALUES (:endpoint_id, :ontology_type, :property_name, :extraction_method, :extraction_pattern)""",
                {
                    "endpoint_id": spoke_id,
                    "ontology_type": "hmdb",
                    "property_name": "HMDB ID",
                    "extraction_method": "query",
                    "extraction_pattern": json.dumps(
                        {
                            "aql": "FOR c IN Compound FILTER c.identifier == @id AND c.source == 'HMDB' RETURN c"
                        }
                    ),
                },
            )

            # Add ontology preferences
            db_session.execute(
                """INSERT INTO endpoint_ontology_preferences
                   (endpoint_id, ontology_type, preference_level)
                   VALUES (:endpoint_id, :ontology_type, :preference_level)""",
                {
                    "endpoint_id": spoke_id,
                    "ontology_type": "chebi",
                    "preference_level": 3,
                },
            )

            db_session.execute(
                """INSERT INTO endpoint_ontology_preferences
                   (endpoint_id, ontology_type, preference_level)
                   VALUES (:endpoint_id, :ontology_type, :preference_level)""",
                {
                    "endpoint_id": spoke_id,
                    "ontology_type": "hmdb",
                    "preference_level": 2,
                },
            )

            db_session.commit()

        logger.info(
            f"Found endpoints: MetabolitesCSV (ID: {metabolites_id}), SPOKE (ID: {spoke_id})"
        )

        # Create relationship between endpoints
        relationship_id = await create_endpoint_relationship(
            db_session,
            name="MetabolitesToSPOKE",
            description="Maps metabolites from Arivale data to SPOKE compounds",
        )

        # Add endpoints as members
        await add_relationship_member(
            db_session,
            relationship_id=relationship_id,
            endpoint_id=metabolites_id,
            role="source",
            priority=1,
        )

        await add_relationship_member(
            db_session,
            relationship_id=relationship_id,
            endpoint_id=spoke_id,
            role="target",
            priority=1,
        )

        # Initialize health tracker
        health_tracker = PropertyHealthTracker(db_session)

        # Find mapping paths
        paths = await find_mapping_paths(
            db_session, source_endpoint_id=metabolites_id, target_endpoint_id=spoke_id
        )

        logger.info(f"Found {len(paths)} mapping paths")

        # Save paths
        saved_path_ids = []
        for path in paths:
            path_id = await save_mapping_path(db_session, path)
            if path_id:
                saved_path_ids.append(path_id)

        logger.info(f"Saved {len(saved_path_ids)} mapping paths")

        # Get sample data
        samples = await get_sample_data(db_session, metabolites_id, limit=5)
        logger.info(f"Got {len(samples)} sample data items")

        # Test property extraction
        for sample in samples:
            # Try different ontology types
            for ontology_type in ["hmdb", "pubchem", "kegg"]:
                # Extract property value
                start_time = time.time()
                property_name = f"{ontology_type.upper()} ID"

                try:
                    value = await extract_property(
                        db_session,
                        endpoint_id=metabolites_id,
                        ontology_type=ontology_type,
                        property_name=property_name,
                        data=sample,
                    )

                    success = bool(value)
                    error_message = None

                except Exception as e:
                    success = False
                    error_message = str(e)
                    value = None

                # Skip health tracking since the tables don't exist
                execution_time_ms = int((time.time() - start_time) * 1000)
                # Would normally track health metrics here:
                # health_tracker.record_extraction_attempt(
                #     endpoint_id=metabolites_id,
                #     ontology_type=ontology_type,
                #     property_name=property_name,
                #     success=success,
                #     execution_time_ms=execution_time_ms,
                #     error_message=error_message
                # )

                if success:
                    logger.info(
                        f"Extracted {ontology_type}: {value} from sample {sample.get('BIOCHEMICAL_NAME', 'Unknown')}"
                    )

                    # Execute mapping for each path
                    for path in paths:
                        # Only use paths with matching source type
                        if path["source_type"] != ontology_type:
                            continue

                        # Execute mapping
                        mapping_results = await execute_mapping_path(
                            source_id=value,
                            source_type=ontology_type,
                            target_type=path["target_type"],
                            path=path,
                        )

                        if mapping_results:
                            logger.info(
                                f"Mapped {value} ({ontology_type}) to {mapping_results}"
                            )
                        else:
                            logger.warning(
                                f"No mapping found for {value} ({ontology_type})"
                            )

        # Skip flushing health metrics
        # health_tracker.flush_metrics()

        # Skip health check for now since the tables don't exist
        logger.info(
            "Skipping health check as health monitoring tables do not exist yet"
        )

        # To enable health checks, first create the required tables:
        # 1. endpoint_property_health
        # 2. health_check_logs

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
    finally:
        db_session.close()


if __name__ == "__main__":
    import time

    asyncio.run(main())

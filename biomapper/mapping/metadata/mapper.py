"""Relationship mapping executor for executing endpoint-to-endpoint mappings."""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.session import get_async_session
from biomapper.mapping.metadata.pathfinder import RelationshipPathFinder
from biomapper.mapping.metadata.interfaces import StepExecutor

logger = logging.getLogger(__name__)


class RelationshipMappingExecutor:
    """Executes endpoint-to-endpoint mappings using discovered paths."""

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        pathfinder: Optional[RelationshipPathFinder] = None,
        step_executor: Optional[StepExecutor] = None,
    ):
        """Initialize the mapping executor.

        Args:
            db_session: Optional database session to use for queries.
            pathfinder: Optional relationship path finder to use.
            step_executor: Optional step executor to use for mapping steps.
        """
        self._session = db_session
        self._pathfinder = pathfinder
        self._step_executor = step_executor

    async def get_session(self) -> AsyncSession:
        """Get an active database session.

        Returns:
            An active SQLAlchemy AsyncSession.
        """
        if self._session is None:
            self._session = await get_async_session()
        return self._session

    async def get_pathfinder(self) -> RelationshipPathFinder:
        """Get a relationship path finder instance.

        Returns:
            A RelationshipPathFinder instance.
        """
        if self._pathfinder is None:
            self._pathfinder = RelationshipPathFinder(self._session)
        return self._pathfinder

    async def get_step_executor(self) -> StepExecutor:
        """Get a step executor instance.

        Returns:
            A StepExecutor instance.
        """
        if self._step_executor is None:
            # Import here to avoid circular imports
            from biomapper.mapping.metadata.step_executor import StepExecutorFactory

            self._step_executor = await StepExecutorFactory.create_step_executor(
                self._session
            )
        return self._step_executor

    async def get_mapping_resources(self) -> Dict[int, Dict]:
        """Get available mapping resources.

        Returns:
            Dictionary of resource ID to resource details.
        """
        session = await self.get_session()
        query = """
            SELECT resource_id, name, resource_type, connection_info, priority
            FROM mapping_resources
        """
        result = await session.execute(text(query))
        resources = result.fetchall()

        return {
            resource.resource_id: {
                "resource_id": resource.resource_id,
                "name": resource.name,
                "resource_type": resource.resource_type,
                "connection_info": json.loads(resource.connection_info)
                if resource.connection_info
                else {},
                "priority": resource.priority,
            }
            for resource in resources
        }

    async def check_cache(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        relationship_id: Optional[int] = None,
    ) -> List[Dict]:
        """Check for cached mappings.

        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            relationship_id: Optional relationship ID to check.

        Returns:
            List of cached mapping dictionaries.
        """
        session = await self.get_session()

        if relationship_id is not None:
            # Query with relationship filter
            query = """
                SELECT mc.* 
                FROM mapping_cache mc
                JOIN relationship_mappings rm ON mc.mapping_id = rm.mapping_id
                WHERE mc.source_id = :source_id
                AND mc.source_type = :source_type
                AND mc.target_type = :target_type
                AND rm.relationship_id = :relationship_id
                ORDER BY mc.confidence DESC
            """
            result = await session.execute(
                text(query),
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_type": target_type,
                    "relationship_id": relationship_id,
                },
            )
        else:
            # Query without relationship filter
            query = """
                SELECT * 
                FROM mapping_cache
                WHERE source_id = :source_id
                AND source_type = :source_type
                AND target_type = :target_type
                ORDER BY confidence DESC
            """
            result = await session.execute(
                text(query),
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_type": target_type,
                },
            )

        cached_mappings = []
        for row in result.fetchall():
            mapping_path = None
            if row.mapping_path:
                try:
                    mapping_path = json.loads(row.mapping_path)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to decode mapping_path for cached mapping {row.mapping_id}"
                    )

            cached_mappings.append(
                {
                    "mapping_id": row.mapping_id,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "target_id": row.target_id,
                    "target_type": row.target_type,
                    "confidence": row.confidence,
                    "mapping_path": mapping_path,
                    "resource_id": row.resource_id,
                    "created_at": row.created_at,
                }
            )

        return cached_mappings

    async def store_mapping(
        self,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        confidence: float,
        mapping_path: Optional[List[Dict]] = None,
        resource_id: Optional[int] = None,
        relationship_id: Optional[int] = None,
    ) -> Optional[int]:
        """Store a mapping result in the cache.

        Args:
            source_id: The source ID.
            source_type: The source ontology type.
            target_id: The target ID.
            target_type: The target ontology type.
            confidence: The mapping confidence score.
            mapping_path: Optional list of steps used for the mapping.
            resource_id: Optional resource ID used for the mapping.
            relationship_id: Optional relationship ID to associate.

        Returns:
            The mapping ID if successful, None otherwise.
        """
        session = await self.get_session()

        try:
            # Check if mapping already exists
            query = """
                SELECT mapping_id, confidence
                FROM mapping_cache
                WHERE source_id = :source_id
                AND source_type = :source_type
                AND target_id = :target_id
                AND target_type = :target_type
            """
            result = await session.execute(
                text(query),
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_id": target_id,
                    "target_type": target_type,
                },
            )
            existing = result.fetchone()

            mapping_id = None

            if existing:
                # Update existing mapping if confidence is higher
                if existing.confidence < confidence:
                    query = """
                        UPDATE mapping_cache
                        SET confidence = :confidence,
                            mapping_path = :mapping_path,
                            resource_id = :resource_id,
                            created_at = CURRENT_TIMESTAMP
                        WHERE mapping_id = :mapping_id
                    """
                    await session.execute(
                        text(query),
                        {
                            "mapping_id": existing.mapping_id,
                            "confidence": confidence,
                            "mapping_path": json.dumps(mapping_path)
                            if mapping_path
                            else None,
                            "resource_id": resource_id,
                        },
                    )

                mapping_id = existing.mapping_id
            else:
                # Create new mapping
                query = """
                    INSERT INTO mapping_cache
                    (source_id, source_type, target_id, target_type, confidence, mapping_path, resource_id, created_at)
                    VALUES
                    (:source_id, :source_type, :target_id, :target_type, :confidence, :mapping_path, :resource_id, CURRENT_TIMESTAMP)
                    RETURNING mapping_id
                """
                result = await session.execute(
                    text(query),
                    {
                        "source_id": source_id,
                        "source_type": source_type,
                        "target_id": target_id,
                        "target_type": target_type,
                        "confidence": confidence,
                        "mapping_path": json.dumps(mapping_path)
                        if mapping_path
                        else None,
                        "resource_id": resource_id,
                    },
                )
                mapping_id = result.fetchone()[0]

            # Associate with relationship if provided
            if relationship_id is not None and mapping_id is not None:
                # Check if relationship mapping already exists
                query = """
                    SELECT COUNT(*)
                    FROM relationship_mappings
                    WHERE relationship_id = :relationship_id
                    AND mapping_id = :mapping_id
                """
                result = await session.execute(
                    text(query),
                    {"relationship_id": relationship_id, "mapping_id": mapping_id},
                )
                count = result.scalar()

                if count == 0:
                    # Create new relationship mapping
                    query = """
                        INSERT INTO relationship_mappings
                        (relationship_id, mapping_id)
                        VALUES
                        (:relationship_id, :mapping_id)
                    """
                    await session.execute(
                        text(query),
                        {"relationship_id": relationship_id, "mapping_id": mapping_id},
                    )

            await session.commit()
            return mapping_id

        except SQLAlchemyError as e:
            logger.error(f"Database error while storing mapping: {e}")
            await session.rollback()
            return None

    async def execute_mapping_step(
        self, source_id: str, source_type: str, target_type: str, step_config: Dict
    ) -> List[Dict]:
        """Execute a single mapping step.

        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            step_config: Step configuration.

        Returns:
            List of mapping results.
        """
        step_executor = await self.get_step_executor()

        # Normalize IDs if needed (some resources expect specific formats)
        normalized_source_id = source_id

        # Special handling for HMDB IDs with UniChem
        if (
            source_type.lower() == "hmdb"
            and step_config.get("resource") == "unichem"
            and normalized_source_id.startswith("HMDB")
        ):
            # UniChem expects HMDB IDs without the "HMDB" prefix
            normalized_source_id = normalized_source_id.replace("HMDB", "")

        try:
            results = await step_executor.execute_step(
                normalized_source_id, source_type, target_type, step_config
            )

            return results
        except Exception as e:
            logger.error(
                f"Error executing mapping step {source_type} -> {target_type}: {e}"
            )
            return []

    async def execute_mapping_path(
        self, source_id: str, source_type: str, target_type: str, path_steps: List[Dict]
    ) -> List[Dict]:
        """Execute a mapping path with multiple steps.

        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            path_steps: List of mapping step configurations.

        Returns:
            List of mapping results.
        """
        if not path_steps:
            logger.warning(
                f"No path steps to execute for {source_type} -> {target_type}"
            )
            return []

        if len(path_steps) == 1:
            # Single step path
            return await self.execute_mapping_step(
                source_id, source_type, target_type, path_steps[0]
            )

        # Multi-step path
        current_results = [{"id": source_id, "type": source_type, "confidence": 1.0}]

        for i, step in enumerate(path_steps):
            step_source_type = step.get("source_type", current_results[0]["type"])
            step_target_type = step.get("target_type")

            if not step_target_type:
                if i == len(path_steps) - 1:
                    step_target_type = target_type
                else:
                    step_target_type = path_steps[i + 1].get("source_type")

            new_results = []

            # Execute step for each intermediate result
            for result in current_results:
                step_results = await self.execute_mapping_step(
                    result["id"], result["type"], step_target_type, step
                )

                # Propagate confidence
                for step_result in step_results:
                    step_result["confidence"] = (
                        step_result.get("confidence", 1.0) * result["confidence"]
                    )

                new_results.extend(step_results)

            # Update current results for next step
            current_results = new_results

            # Early stopping if no results
            if not current_results:
                logger.warning(
                    f"No results after step {i+1} of {len(path_steps)} for {source_type} -> {target_type}"
                )
                return []

        # Format final results
        return [
            {
                "target_id": result["id"],
                "target_type": result["type"],
                "confidence": result["confidence"],
                "source_id": source_id,
                "source_type": source_type,
            }
            for result in current_results
            if result["type"] == target_type
        ]

    async def map_with_relationship(
        self,
        relationship_id: int,
        source_id: str,
        source_type: str,
        target_type: str,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """Map a source ID to target type using a specific relationship.

        Args:
            relationship_id: The relationship ID.
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            force_refresh: Whether to bypass cache and force re-mapping.

        Returns:
            List of mapping results.
        """
        # Check cache first if not forcing refresh
        if not force_refresh:
            cached = await self.check_cache(
                source_id, source_type, target_type, relationship_id
            )

            if cached:
                logger.info(
                    f"Found {len(cached)} cached mappings for {source_id} ({source_type} -> {target_type})"
                )
                return cached

        # Get best mapping path for this relationship
        pathfinder = await self.get_pathfinder()
        start_time = time.time()

        mapping_path = await pathfinder.get_best_mapping_path(
            relationship_id, source_type, target_type
        )

        if not mapping_path or not mapping_path.get("path_steps"):
            logger.warning(
                f"No suitable mapping path found for {source_type} -> {target_type}"
            )
            return []

        # Execute the mapping path
        results = await self.execute_mapping_path(
            source_id, source_type, target_type, mapping_path["path_steps"]
        )

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Update metrics
        await pathfinder.update_path_metrics(
            relationship_id,
            source_type,
            target_type,
            bool(results),  # Success if we got any results
            execution_time_ms,
        )

        # Store results in cache
        stored_ids = []
        for result in results:
            mapping_id = await self.store_mapping(
                source_id=source_id,
                source_type=source_type,
                target_id=result["target_id"],
                target_type=target_type,
                confidence=result["confidence"],
                mapping_path=mapping_path["path_steps"],
                resource_id=None,  # We don't have a single resource for multi-step paths
                relationship_id=relationship_id,
            )
            if mapping_id:
                stored_ids.append(mapping_id)

        logger.info(f"Stored {len(stored_ids)} mappings in cache")

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "mapping_id": None,
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_id": result["target_id"],
                    "target_type": target_type,
                    "confidence": result["confidence"],
                    "mapping_path": mapping_path["path_steps"],
                    "resource_id": None,
                    "created_at": None,
                }
            )

        return formatted_results

    async def map_endpoint_value(
        self,
        relationship_id: int,
        value: str,
        source_endpoint_id: int,
        target_endpoint_id: int,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """Map a value from source endpoint to target endpoint.

        Args:
            relationship_id: The relationship ID.
            value: The value to map.
            source_endpoint_id: The source endpoint ID.
            target_endpoint_id: The target endpoint ID.
            force_refresh: Whether to bypass cache and force re-mapping.

        Returns:
            List of mapping results.
        """
        pathfinder = await self.get_pathfinder()

        # Get endpoint details
        source_endpoint = await pathfinder.get_endpoint_details(source_endpoint_id)
        target_endpoint = await pathfinder.get_endpoint_details(target_endpoint_id)

        if not source_endpoint or not target_endpoint:
            logger.error(
                f"Source or target endpoint not found for relationship {relationship_id}"
            )
            return []

        # Determine source ontology types to try
        # First, try with NAME as fallback if nothing else is available
        source_ontologies = await pathfinder.get_supported_ontology_types(
            source_endpoint_id
        )
        if not source_ontologies:
            source_ontologies = ["NAME"]

        # Get target ontology types
        target_ontologies = await pathfinder.get_supported_ontology_types(
            target_endpoint_id
        )
        if not target_ontologies:
            logger.error(
                f"No ontology types available for target endpoint {target_endpoint_id}"
            )
            return []

        logger.info(
            f"Mapping between source ontologies {source_ontologies} and target ontologies {target_ontologies}"
        )

        all_results = []

        # Try mapping with each source ontology
        for source_ontology in source_ontologies:
            for target_ontology in target_ontologies:
                results = await self.map_with_relationship(
                    relationship_id,
                    value,
                    source_ontology,
                    target_ontology,
                    force_refresh,
                )

                if results:
                    all_results.extend(results)

        # Sort by confidence
        all_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return all_results

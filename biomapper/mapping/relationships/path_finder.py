"""
Relationship Path Finder Module.

This module implements the RelationshipPathFinder class for discovering and
managing mapping paths between endpoints within relationships.
"""

import asyncio

# Import metamapping engine
# Import needed modules
from typing import List, Dict, Any, Tuple, Optional
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RelationshipPathFinder:
    """Discovers and manages mapping paths for endpoint relationships."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the relationship path finder.

        Args:
            db_session: SQLAlchemy AsyncSession to use.
        """
        if not isinstance(db_session, AsyncSession):
            raise TypeError("db_session must be an AsyncSession instance")
        self.db_session = db_session
        # For testing, we'll implement a simple finder function directly
        # rather than using the actual MetamappingEngine which requires a dispatcher

    async def find_ontology_mapping_paths(
        self, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """Find mapping paths between ontology types."""
        return await self._find_ontology_paths(source_type, target_type)

    async def discover_paths_for_relationship(
        self, relationship_id: int
    ) -> List[Dict[str, Any]]:
        """
        Find and store optimal mapping paths for a relationship.

        Args:
            relationship_id: ID of the relationship to discover paths for

        Returns:
            List of discovered paths with scores
        """
        # Get relationship details
        relationship = await self._get_relationship(relationship_id)
        if not relationship:
            raise ValueError(f"Relationship {relationship_id} not found")

        # Get source and target endpoints
        source_endpoint = await self._get_endpoint_by_role(relationship_id, "source")
        target_endpoint = await self._get_endpoint_by_role(relationship_id, "target")

        if not source_endpoint or not target_endpoint:
            raise ValueError(
                f"Relationship {relationship_id} must have both source and target endpoints"
            )

        # Get ontology preferences for both endpoints
        source_preferences = await self._get_ontology_preferences(
            source_endpoint["endpoint_id"]
        )
        target_preferences = await self._get_ontology_preferences(
            target_endpoint["endpoint_id"]
        )

        # Find optimal paths between each preferred ontology pair
        discovered_paths = []
        for source_ont, source_pref in source_preferences:
            for target_ont, target_pref in target_preferences:
                logger.debug(f"Finding paths from {source_ont} to {target_ont}")

                # Find ontology-level paths
                ont_paths = await self._find_ontology_paths(source_ont, target_ont)

                # Score paths based on preferences and path metrics
                scored_paths = self._score_paths(
                    ont_paths, source_pref=source_pref, target_pref=target_pref
                )

                # Store the best path for this ontology pair
                if scored_paths:
                    best_path = scored_paths[0]
                    await self._store_relationship_path(
                        relationship_id=relationship_id,
                        source_ontology=source_ont,
                        target_ontology=target_ont,
                        ontology_path_id=best_path["path_id"],
                        score=best_path["score"],
                    )
                    discovered_paths.append(best_path)
                    logger.debug(
                        f"Stored best path for {source_ont} to {target_ont} with score {best_path['score']}"
                    )

        return discovered_paths

    async def _find_ontology_paths(
        self, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """Find ontology-level paths between source and target types."""
        query = text(
            """
            SELECT id, source_type, target_type, path_steps, performance_score, success_rate
            FROM mapping_paths
            WHERE LOWER(source_type) = LOWER(:source_type)
            AND LOWER(target_type) = LOWER(:target_type)
            ORDER BY performance_score DESC
        """
        )
        try:
            result = await self.db_session.execute(
                query, {"source_type": source_type, "target_type": target_type}
            )
            rows = result.fetchall()

            paths = []
            for row in rows:
                paths.append(
                    {
                        "id": row.id,
                        "source_type": row.source_type,
                        "target_type": row.target_type,
                        "path_steps": json.loads(row.path_steps),
                        "performance_score": row.performance_score,
                        "success_rate": row.success_rate,
                    }
                )
            return paths
        except Exception as e:
            logger.error(f"Error finding ontology paths: {e}")
            return []

    def _score_paths(
        self, paths: List[Dict[str, Any]], source_pref: int, target_pref: int
    ) -> List[Dict[str, Any]]:
        """
        Score paths based on preferences and metrics.

        Args:
            paths: List of ontology paths
            source_pref: Preference level of source ontology
            target_pref: Preference level of target ontology

        Returns:
            List of scored paths sorted by score (highest first)
        """
        scored_paths = []
        for path in paths:
            # Base score on path's performance metrics
            base_score = path.get("performance_score", 0.5)

            # Adjust for preference levels (lower preference level = higher priority)
            pref_factor = 1.0 / max(0.1, (source_pref + target_pref) / 2)

            # Length penalty (shorter paths are better)
            path_steps = path.get("path_steps", [])
            length_factor = 1.0 / max(1, len(path_steps))

            # Calculate final score
            final_score = base_score * pref_factor * length_factor

            scored_paths.append(
                {"path_id": path["id"], "path": path, "score": final_score}
            )

        # Sort by score (highest first)
        return sorted(scored_paths, key=lambda p: p["score"], reverse=True)

    async def _get_relationship(self, relationship_id: int) -> Optional[Dict[str, Any]]:
        """Get relationship details from database."""
        query = text(
            """
            SELECT relationship_id, name, description, created_at
            FROM endpoint_relationships
            WHERE relationship_id = :relationship_id
        """
        )
        try:
            result = await self.db_session.execute(
                query, {"relationship_id": relationship_id}
            )
            row = result.fetchone()

            if row:
                return {
                    "relationship_id": row.relationship_id,
                    "name": row.name,
                    "description": row.description,
                    "created_at": row.created_at,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting relationship: {e}")
            return None

    async def _get_endpoint_by_role(
        self, relationship_id: int, role: str
    ) -> Optional[Dict[str, Any]]:
        """Get endpoint with specified role in relationship."""
        query = text(
            """
            SELECT e.endpoint_id, e.name, e.description, e.type, e.connection_info
            FROM endpoints e
            JOIN endpoint_relationship_members m ON e.endpoint_id = m.endpoint_id
            WHERE m.relationship_id = :relationship_id
            AND m.role = :role
        """
        )
        try:
            result = await self.db_session.execute(
                query, {"relationship_id": relationship_id, "role": role}
            )
            row = result.fetchone()

            if row:
                return {
                    "endpoint_id": row.endpoint_id,
                    "name": row.name,
                    "description": row.description,
                    "type": row.type,
                    "connection_info": row.connection_info,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting endpoint by role: {e}")
            return None

    async def _get_ontology_preferences(
        self, endpoint_id: int
    ) -> List[Tuple[str, int]]:
        """
        Get ordered ontology preferences for an endpoint.

        Returns a list of (ontology_type, preference_level) tuples sorted by preference.
        """
        query = text(
            """
            SELECT ontology_type, preference_level
            FROM endpoint_ontology_preferences
            WHERE endpoint_id = :endpoint_id
            ORDER BY preference_level ASC
        """
        )
        try:
            result = await self.db_session.execute(query, {"endpoint_id": endpoint_id})
            rows = result.fetchall()

            return [(row.ontology_type, row.preference_level) for row in rows]
        except Exception as e:
            logger.error(f"Error getting ontology preferences: {e}")
            return []

    async def _store_relationship_path(
        self,
        relationship_id: int,
        source_ontology: str,
        target_ontology: str,
        ontology_path_id: int,
        score: float,
    ) -> bool:
        """Store a relationship-specific mapping path."""
        query = text(
            """
            INSERT INTO relationship_mapping_paths
            (relationship_id, source_ontology, target_ontology, ontology_path_id,
             performance_score, last_discovered)
            VALUES (:relationship_id, :source_ontology, :target_ontology, :ontology_path_id,
                    :score, :last_discovered)
            ON CONFLICT(relationship_id, source_ontology, target_ontology)
            DO UPDATE SET
                ontology_path_id = excluded.ontology_path_id,
                performance_score = excluded.performance_score,
                last_discovered = excluded.last_discovered
        """
        )
        params = {
            "relationship_id": relationship_id,
            "source_ontology": source_ontology,
            "target_ontology": target_ontology,
            "ontology_path_id": ontology_path_id,
            "score": score,
            "last_discovered": datetime.now().isoformat(),
        }
        try:
            await self.db_session.execute(query, params)
            await self.db_session.commit()
            logger.debug(
                f"Stored/Updated path for rel {relationship_id}: {source_ontology} -> {target_ontology}"
            )
            return True
        except Exception as e:
            logger.error(f"Error storing relationship path: {e}")
            await self.db_session.rollback()
            return False

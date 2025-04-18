"""Relationship mapping path finder for discovering and storing optimal mapping paths."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, func, Table, Column, Integer, String, Float, DateTime, ForeignKey, MetaData, text
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.session import get_async_session

logger = logging.getLogger(__name__)

class RelationshipPathFinder:
    """Discovers and manages mapping paths between endpoints for relationships."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize the path finder with an optional database session.
        
        Args:
            db_session: Optional database session to use for queries.
        """
        self._session = db_session
    
    async def get_session(self) -> AsyncSession:
        """Get an active database session.
        
        Returns:
            An active SQLAlchemy AsyncSession.
        """
        if self._session is None:
            self._session = await get_async_session()
        return self._session
    
    async def get_relationship_by_id(self, relationship_id: int) -> Optional[Dict]:
        """Get relationship details by ID.
        
        Args:
            relationship_id: The ID of the relationship to retrieve.
            
        Returns:
            Dictionary containing relationship details or None if not found.
        """
        session = await self.get_session()
        
        # First get the basic relationship info
        query = """
            SELECT relationship_id, name, description
            FROM endpoint_relationships
            WHERE relationship_id = :relationship_id
        """
        result = await session.execute(text(query), {"relationship_id": relationship_id})
        relationship = result.fetchone()
        
        if relationship is None:
            logger.warning(f"Relationship with ID {relationship_id} not found")
            return None
        
        # Get source endpoint ID
        query = """
            SELECT endpoint_id
            FROM endpoint_relationship_members
            WHERE relationship_id = :relationship_id AND role = 'source'
            LIMIT 1
        """
        result = await session.execute(text(query), {"relationship_id": relationship_id})
        source_member = result.fetchone()
        
        # Get target endpoint ID
        query = """
            SELECT endpoint_id
            FROM endpoint_relationship_members
            WHERE relationship_id = :relationship_id AND role = 'target'
            LIMIT 1
        """
        result = await session.execute(text(query), {"relationship_id": relationship_id})
        target_member = result.fetchone()
        
        source_endpoint_id = source_member[0] if source_member else None
        target_endpoint_id = target_member[0] if target_member else None
        
        if source_endpoint_id is None or target_endpoint_id is None:
            logger.warning(f"Relationship {relationship_id} is missing source or target endpoint")
            return None
        
        return {
            "relationship_id": relationship.relationship_id,
            "name": relationship.name,
            "description": relationship.description,
            "source_endpoint_id": source_endpoint_id,
            "target_endpoint_id": target_endpoint_id,
        }
    
    async def get_endpoint_details(self, endpoint_id: int) -> Optional[Dict]:
        """Get endpoint details by ID.
        
        Args:
            endpoint_id: The ID of the endpoint to retrieve.
            
        Returns:
            Dictionary containing endpoint details or None if not found.
        """
        session = await self.get_session()
        query = """
            SELECT endpoint_id, name, endpoint_type, connection_info
            FROM endpoints
            WHERE endpoint_id = :endpoint_id
        """
        result = await session.execute(text(query), {"endpoint_id": endpoint_id})
        endpoint = result.fetchone()
        
        if endpoint is None:
            logger.warning(f"Endpoint with ID {endpoint_id} not found")
            return None
        
        connection_info = {}
        if hasattr(endpoint, 'connection_info') and endpoint.connection_info:
            try:
                connection_info = json.loads(endpoint.connection_info)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode connection_info for endpoint {endpoint.name}")
        
        return {
            "endpoint_id": endpoint.endpoint_id,
            "name": endpoint.name,
            "endpoint_type": endpoint.endpoint_type,
            "endpoint_subtype": getattr(endpoint, 'endpoint_subtype', None),
            "connection_info": connection_info,
        }
    
    async def get_supported_ontology_types(self, endpoint_id: int) -> List[str]:
        """Get supported ontology types for an endpoint.
        
        Args:
            endpoint_id: The ID of the endpoint.
            
        Returns:
            List of supported ontology type strings.
        """
        session = await self.get_session()
        # Query endpoint property configurations to get supported ontologies
        query = """
            SELECT DISTINCT ontology_type 
            FROM endpoint_property_configs
            WHERE endpoint_id = :endpoint_id
        """
        result = await session.execute(text(query), {"endpoint_id": endpoint_id})
        ontology_types = [row[0] for row in result.fetchall() if row[0]]
        
        # If no configurations found, fallback to common types
        if not ontology_types:
            # For demo purposes, provide some fallback ontology types
            if await self._is_endpoint_type(endpoint_id, "file"):
                ontology_types = ["hmdb", "name", "pubchem"]
            elif await self._is_endpoint_type(endpoint_id, "graph"):
                ontology_types = ["chebi", "pubchem"]
        
        return ontology_types
    
    async def _is_endpoint_type(self, endpoint_id: int, endpoint_type: str) -> bool:
        """Check if an endpoint is of a specific type.
        
        Args:
            endpoint_id: The endpoint ID.
            endpoint_type: The endpoint type to check.
            
        Returns:
            True if the endpoint is of the specified type, False otherwise.
        """
        session = await self.get_session()
        query = """
            SELECT COUNT(*) 
            FROM endpoints
            WHERE endpoint_id = :endpoint_id
            AND endpoint_type = :endpoint_type
        """
        result = await session.execute(
            text(query), 
            {"endpoint_id": endpoint_id, "endpoint_type": endpoint_type}
        )
        count = result.scalar()
        return count > 0
    
    async def get_existing_mapping_paths(
        self, 
        source_type: str, 
        target_type: str
    ) -> List[Dict]:
        """Get existing mapping paths between ontology types.
        
        Args:
            source_type: The source ontology type.
            target_type: The target ontology type.
            
        Returns:
            List of mapping path dictionaries.
        """
        session = await self.get_session()
        query = """
            SELECT id, source_type, target_type, path_steps,
                   performance_score, success_rate, usage_count
            FROM mapping_paths
            WHERE source_type = :source_type AND target_type = :target_type
            ORDER BY performance_score DESC NULLS LAST,
                     success_rate DESC NULLS LAST,
                     usage_count DESC
        """
        result = await session.execute(
            text(query), 
            {"source_type": source_type, "target_type": target_type}
        )
        
        paths = []
        for row in result.fetchall():
            path_steps = []
            try:
                if row.path_steps:
                    path_steps = json.loads(row.path_steps)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode path_steps for mapping path ID {row.id}")
            
            paths.append({
                "id": row.id,
                "source_type": row.source_type,
                "target_type": row.target_type,
                "path_steps": path_steps,
                "performance_score": row.performance_score,
                "success_rate": row.success_rate,
                "usage_count": row.usage_count,
            })
        
        return paths
    
    async def discover_relationship_paths(
        self,
        relationship_id: int,
        force_rediscover: bool = False
    ) -> List[Dict]:
        """Discover and store mapping paths for a relationship.
        
        Args:
            relationship_id: The relationship ID to discover paths for.
            force_rediscover: Whether to force rediscovery of paths.
            
        Returns:
            List of discovered relationship mapping paths.
        """
        session = await self.get_session()
        
        # Get relationship details
        relationship = await self.get_relationship_by_id(relationship_id)
        
        if not relationship:
            logger.error(f"Relationship {relationship_id} not found")
            return []
        
        # Get source and target endpoints
        source_endpoint_id = relationship["source_endpoint_id"]
        target_endpoint_id = relationship["target_endpoint_id"]
        
        source_endpoint = await self.get_endpoint_details(source_endpoint_id)
        target_endpoint = await self.get_endpoint_details(target_endpoint_id)
        
        if not source_endpoint or not target_endpoint:
            logger.error(f"Source or target endpoint not found for relationship {relationship_id}")
            return []
        
        # Get ontology types supported by each endpoint
        source_ontologies = await self.get_supported_ontology_types(source_endpoint_id)
        target_ontologies = await self.get_supported_ontology_types(target_endpoint_id)
        
        logger.info(f"Source ontologies for {source_endpoint['name']}: {source_ontologies}")
        logger.info(f"Target ontologies for {target_endpoint['name']}: {target_ontologies}")
        
        # Check existing relationship mapping paths if not forcing rediscovery
        if not force_rediscover:
            query = """
                SELECT id, relationship_id, source_ontology, target_ontology,
                       ontology_path_id, performance_score, success_rate, usage_count
                FROM relationship_mapping_paths
                WHERE relationship_id = :relationship_id
            """
            result = await session.execute(text(query), {"relationship_id": relationship_id})
            existing_paths = result.fetchall()
            
            if existing_paths:
                logger.info(f"Found {len(existing_paths)} existing mapping paths for relationship {relationship_id}")
                return [
                    {
                        "id": path.id,
                        "relationship_id": path.relationship_id,
                        "source_ontology": path.source_ontology,
                        "target_ontology": path.target_ontology,
                        "ontology_path_id": path.ontology_path_id,
                        "performance_score": path.performance_score,
                        "success_rate": path.success_rate,
                        "usage_count": path.usage_count,
                    }
                    for path in existing_paths
                ]
        
        # Discover paths between all combinations of ontology types
        discovered_paths = []
        
        for source_ontology in source_ontologies:
            for target_ontology in target_ontologies:
                # Find existing mapping paths
                mapping_paths = await self.get_existing_mapping_paths(source_ontology, target_ontology)
                
                if not mapping_paths:
                    # If no existing path, create a basic one (for demonstration purposes)
                    if source_ontology.lower() in ["hmdb", "pubchem"] and target_ontology.lower() in ["chebi", "pubchem"]:
                        path_id = await self._create_sample_mapping_path(source_ontology, target_ontology)
                        if path_id:
                            # Get the newly created path
                            mapping_paths = await self.get_existing_mapping_paths(source_ontology, target_ontology)
                    
                    if not mapping_paths:
                        logger.info(f"No mapping path found for {source_ontology} -> {target_ontology}")
                        continue
                
                # Use the best mapping path based on scores and usage
                best_path = mapping_paths[0]
                
                try:
                    # Check if relationship mapping path already exists
                    query = """
                        SELECT id, relationship_id, source_ontology, target_ontology,
                               ontology_path_id, performance_score, success_rate, usage_count
                        FROM relationship_mapping_paths
                        WHERE relationship_id = :relationship_id
                        AND source_ontology = :source_ontology
                        AND target_ontology = :target_ontology
                    """
                    result = await session.execute(
                        text(query), 
                        {
                            "relationship_id": relationship_id,
                            "source_ontology": source_ontology,
                            "target_ontology": target_ontology
                        }
                    )
                    existing = result.fetchone()
                    
                    if existing:
                        # Update existing path if necessary
                        if existing.ontology_path_id != best_path["id"] or force_rediscover:
                            query = """
                                UPDATE relationship_mapping_paths
                                SET ontology_path_id = :ontology_path_id,
                                    performance_score = :performance_score,
                                    success_rate = :success_rate,
                                    last_discovered = CURRENT_TIMESTAMP
                                WHERE id = :id
                            """
                            await session.execute(
                                text(query),
                                {
                                    "id": existing.id,
                                    "ontology_path_id": best_path["id"],
                                    "performance_score": best_path["performance_score"],
                                    "success_rate": best_path["success_rate"]
                                }
                            )
                            logger.info(f"Updated relationship mapping path for {source_ontology} -> {target_ontology}")
                        
                        discovered_paths.append({
                            "id": existing.id,
                            "relationship_id": existing.relationship_id,
                            "source_ontology": existing.source_ontology,
                            "target_ontology": existing.target_ontology,
                            "ontology_path_id": best_path["id"],
                            "performance_score": best_path["performance_score"],
                            "success_rate": best_path["success_rate"],
                            "usage_count": existing.usage_count,
                        })
                    else:
                        # Create new relationship mapping path
                        query = """
                            INSERT INTO relationship_mapping_paths
                            (relationship_id, source_ontology, target_ontology, ontology_path_id,
                             performance_score, success_rate, last_discovered)
                            VALUES
                            (:relationship_id, :source_ontology, :target_ontology, :ontology_path_id,
                             :performance_score, :success_rate, CURRENT_TIMESTAMP)
                            RETURNING id
                        """
                        result = await session.execute(
                            text(query),
                            {
                                "relationship_id": relationship_id,
                                "source_ontology": source_ontology,
                                "target_ontology": target_ontology,
                                "ontology_path_id": best_path["id"],
                                "performance_score": best_path["performance_score"],
                                "success_rate": best_path["success_rate"]
                            }
                        )
                        
                        # Get the ID of the newly inserted row
                        new_id = result.fetchone()[0]
                        
                        discovered_paths.append({
                            "id": new_id,
                            "relationship_id": relationship_id,
                            "source_ontology": source_ontology,
                            "target_ontology": target_ontology,
                            "ontology_path_id": best_path["id"],
                            "performance_score": best_path["performance_score"],
                            "success_rate": best_path["success_rate"],
                            "usage_count": 0,
                        })
                        
                        logger.info(f"Created new relationship mapping path for {source_ontology} -> {target_ontology}")
                
                except SQLAlchemyError as e:
                    logger.error(f"Database error while processing path {source_ontology} -> {target_ontology}: {e}")
                    await session.rollback()
        
        await session.commit()
        return discovered_paths
    
    async def _create_sample_mapping_path(self, source_type: str, target_type: str) -> Optional[int]:
        """Create a sample mapping path for demonstration purposes.
        
        Args:
            source_type: The source ontology type.
            target_type: The target ontology type.
            
        Returns:
            The ID of the created mapping path, or None if creation failed.
        """
        session = await self.get_session()
        
        # Create path steps based on types
        path_steps = []
        
        if source_type.lower() == "hmdb" and target_type.lower() == "pubchem":
            # Direct mapping with UniChem
            path_steps = [{"resource": "unichem", "source_type": "hmdb", "target_type": "pubchem"}]
        elif source_type.lower() == "hmdb" and target_type.lower() == "chebi":
            # Two-step mapping via PubChem
            path_steps = [
                {"resource": "unichem", "source_type": "hmdb", "target_type": "pubchem"},
                {"resource": "unichem", "source_type": "pubchem", "target_type": "chebi"}
            ]
        elif source_type.lower() == "pubchem" and target_type.lower() == "chebi":
            # Direct mapping with UniChem
            path_steps = [{"resource": "unichem", "source_type": "pubchem", "target_type": "chebi"}]
        elif source_type.lower() == "pubchem" and target_type.lower() == "hmdb":
            # Direct mapping with UniChem
            path_steps = [{"resource": "unichem", "source_type": "pubchem", "target_type": "hmdb"}]
        elif source_type.lower() == "name" and target_type.lower() in ["pubchem", "chebi", "hmdb"]:
            # Name requires some additional parsing
            path_steps = [{"resource": "extraction", "source_type": "name", "target_type": target_type.lower()}]
        
        if not path_steps:
            return None
        
        try:
            # Insert the new mapping path
            query = """
                INSERT INTO mapping_paths
                (source_type, target_type, path_steps, performance_score, success_rate, usage_count)
                VALUES
                (:source_type, :target_type, :path_steps, :performance_score, :success_rate, 0)
                RETURNING id
            """
            result = await session.execute(
                text(query),
                {
                    "source_type": source_type,
                    "target_type": target_type,
                    "path_steps": json.dumps(path_steps),
                    "performance_score": 0.8,  # Default good score
                    "success_rate": 0.9        # Default good success rate
                }
            )
            
            path_id = result.fetchone()[0]
            await session.commit()
            
            logger.info(f"Created sample mapping path for {source_type} -> {target_type} with ID {path_id}")
            return path_id
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating sample mapping path: {e}")
            await session.rollback()
            return None
    
    async def get_best_mapping_path(
        self,
        relationship_id: int,
        source_ontology: str,
        target_ontology: str,
        force_discover: bool = False
    ) -> Optional[Dict]:
        """Get the best mapping path for a specific relationship and ontology types.
        
        Args:
            relationship_id: The relationship ID.
            source_ontology: The source ontology type.
            target_ontology: The target ontology type.
            force_discover: Whether to force path discovery.
            
        Returns:
            Dictionary with mapping path details or None if not found.
        """
        session = await self.get_session()
        
        # Check if we have a stored relationship mapping path
        query = """
            SELECT rmp.id, rmp.relationship_id, rmp.source_ontology, rmp.target_ontology,
                   rmp.ontology_path_id, rmp.performance_score, rmp.success_rate, rmp.usage_count,
                   mp.path_steps
            FROM relationship_mapping_paths rmp
            JOIN mapping_paths mp ON rmp.ontology_path_id = mp.id
            WHERE rmp.relationship_id = :relationship_id
            AND rmp.source_ontology = :source_ontology
            AND rmp.target_ontology = :target_ontology
            ORDER BY rmp.performance_score DESC NULLS LAST,
                     rmp.success_rate DESC NULLS LAST,
                     rmp.usage_count DESC
        """
        result = await session.execute(
            text(query), 
            {
                "relationship_id": relationship_id,
                "source_ontology": source_ontology,
                "target_ontology": target_ontology
            }
        )
        path = result.fetchone()
        
        if not path or force_discover:
            # If path doesn't exist or we're forcing discovery, trigger discovery
            paths = await self.discover_relationship_paths(relationship_id, force_rediscover=force_discover)
            
            # Find the path for our specific ontology types
            for discovered_path in paths:
                if (discovered_path["source_ontology"] == source_ontology and 
                    discovered_path["target_ontology"] == target_ontology):
                    
                    # Get full mapping path details
                    query = """
                        SELECT id, source_type, target_type, path_steps,
                               performance_score, success_rate
                        FROM mapping_paths
                        WHERE id = :path_id
                    """
                    result = await session.execute(text(query), {"path_id": discovered_path["ontology_path_id"]})
                    mapping_path = result.fetchone()
                    
                    if mapping_path:
                        path_steps = []
                        try:
                            if mapping_path.path_steps:
                                path_steps = json.loads(mapping_path.path_steps)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode path_steps for mapping path ID {mapping_path.id}")
                        
                        return {
                            "relationship_mapping_id": discovered_path["id"],
                            "relationship_id": relationship_id,
                            "source_ontology": source_ontology,
                            "target_ontology": target_ontology,
                            "ontology_path_id": mapping_path.id,
                            "path_steps": path_steps,
                            "performance_score": mapping_path.performance_score,
                            "success_rate": mapping_path.success_rate,
                        }
            
            logger.warning(f"No mapping path found for {source_ontology} -> {target_ontology} in relationship {relationship_id}")
            return None
        
        # Parse the path steps from the result
        path_steps = []
        try:
            if path.path_steps:
                path_steps = json.loads(path.path_steps)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode path_steps for mapping path ID {path.ontology_path_id}")
        
        return {
            "relationship_mapping_id": path.id,
            "relationship_id": relationship_id,
            "source_ontology": source_ontology,
            "target_ontology": target_ontology,
            "ontology_path_id": path.ontology_path_id,
            "path_steps": path_steps,
            "performance_score": path.performance_score,
            "success_rate": path.success_rate,
        }
    
    async def update_path_metrics(
        self,
        relationship_id: int,
        source_ontology: str,
        target_ontology: str,
        success: bool,
        execution_time_ms: int = None
    ) -> None:
        """Update metrics for a mapping path after using it.
        
        Args:
            relationship_id: The relationship ID.
            source_ontology: The source ontology type.
            target_ontology: The target ontology type.
            success: Whether the mapping was successful.
            execution_time_ms: Execution time in milliseconds.
        """
        session = await self.get_session()
        
        try:
            # Get relationship mapping path
            query = """
                SELECT id, success_rate, performance_score, usage_count
                FROM relationship_mapping_paths
                WHERE relationship_id = :relationship_id
                AND source_ontology = :source_ontology
                AND target_ontology = :target_ontology
            """
            result = await session.execute(
                text(query), 
                {
                    "relationship_id": relationship_id,
                    "source_ontology": source_ontology,
                    "target_ontology": target_ontology
                }
            )
            path = result.fetchone()
            
            if not path:
                logger.warning(f"No mapping path found to update metrics for {source_ontology} -> {target_ontology}")
                return
            
            # Update usage count and last used timestamp
            updates = {
                "usage_count": path.usage_count + 1 if path.usage_count else 1,
                "last_used": datetime.now()
            }
            
            # Update success rate
            if path.success_rate is not None:
                # Weighted average: give more weight to recent results
                alpha = 0.1  # Weight of new value
                new_success_rate = path.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
                updates["success_rate"] = new_success_rate
            else:
                updates["success_rate"] = 1.0 if success else 0.0
            
            # Update performance score if execution time provided
            if execution_time_ms is not None and execution_time_ms > 0:
                # Lower is better for performance score (inverse of execution time)
                # Normalize to a 0-1 scale where 1 is best
                max_expected_time = 10000  # 10 seconds as max expected time
                normalized_score = max(0, 1 - (execution_time_ms / max_expected_time))
                
                if path.performance_score is not None:
                    # Weighted average for performance score
                    new_performance_score = path.performance_score * (1 - alpha) + normalized_score * alpha
                    updates["performance_score"] = new_performance_score
                else:
                    updates["performance_score"] = normalized_score
            
            # Build the update query
            set_clauses = []
            for key, value in updates.items():
                if key == "last_used":
                    set_clauses.append(f"{key} = CURRENT_TIMESTAMP")
                else:
                    set_clauses.append(f"{key} = :{key}")
            
            update_query = f"""
                UPDATE relationship_mapping_paths
                SET {', '.join(set_clauses)}
                WHERE id = :id
            """
            
            # Remove last_used from parameters since we're using CURRENT_TIMESTAMP
            if "last_used" in updates:
                del updates["last_used"]
            
            # Add ID to parameters
            updates["id"] = path.id
            
            # Execute the update
            await session.execute(text(update_query), updates)
            await session.commit()
            
            logger.info(f"Updated metrics for mapping path {source_ontology} -> {target_ontology}")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while updating path metrics: {e}")
            await session.rollback()
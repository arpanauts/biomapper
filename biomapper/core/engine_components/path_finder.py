"""
Path finder module for discovering and managing mapping paths.

This module handles the discovery, caching, and selection of mapping paths
between different ontology types or endpoints in the biomapper system.
"""

import asyncio
import logging
import time
from typing import List, Optional, Union, Dict, Tuple, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.core.exceptions import BiomapperError, ErrorCode
from biomapper.db.models import (
    MappingPath,
    MappingPathStep,
    MappingResource,
    EndpointRelationship,
    RelationshipMappingPath,
    Endpoint
)

logger = logging.getLogger(__name__)


class PathFinder:
    """Service for discovering and managing mapping paths between ontologies."""
    
    def __init__(
        self,
        cache_size: int = 100,
        cache_expiry_seconds: int = 300
    ):
        """
        Initialize the PathFinder service.
        
        Args:
            cache_size: Maximum number of paths to cache
            cache_expiry_seconds: Cache expiry time in seconds
        """
        self.logger = logger
        self._path_cache: Dict[str, List[Union[MappingPath, ReversiblePath]]] = {}
        self._path_cache_timestamps: Dict[str, float] = {}
        self._path_cache_lock = asyncio.Lock()
        self._path_cache_max_size = cache_size
        self._path_cache_expiry_seconds = cache_expiry_seconds
    
    async def find_mapping_paths(
        self,
        session: AsyncSession,
        source_ontology: str,
        target_ontology: str,
        bidirectional: bool = False,
        preferred_direction: str = "forward",
        source_endpoint: Optional[Endpoint] = None,
        target_endpoint: Optional[Endpoint] = None,
    ) -> List[Union[MappingPath, ReversiblePath]]:
        """
        Find mapping paths between ontologies, optionally searching in both directions.

        Args:
            session: The database session
            source_ontology: Source ontology term
            target_ontology: Target ontology term
            bidirectional: If True, search for both forward and reverse paths
            preferred_direction: Preferred direction for path ordering ("forward" or "reverse")
            source_endpoint: Optional source endpoint for relationship-specific path selection
            target_endpoint: Optional target endpoint for relationship-specific path selection

        Returns:
            List of paths (may be wrapped in ReversiblePath if reverse paths were found)
            Paths are sorted by direction preference and then by priority
        """
        # Use caching to avoid redundant database calls
        cache_key = f"{source_ontology}_{target_ontology}_{bidirectional}_{preferred_direction}"
        
        # Check cache
        cached_paths = await self._get_cached_paths(cache_key)
        if cached_paths is not None:
            return cached_paths
        
        self.logger.debug(
            f"Searching for mapping paths from '{source_ontology}' to '{target_ontology}' "
            f"(bidirectional={bidirectional}, preferred={preferred_direction})"
        )

        # First, try to find relationship-specific paths if endpoints are provided
        relationship_paths = []
        if source_endpoint and target_endpoint:
            self.logger.debug(
                f"Checking for relationship-specific paths between endpoints "
                f"{source_endpoint.id} and {target_endpoint.id}"
            )
            relationship_paths = await self._find_paths_for_relationship(
                session,
                source_endpoint.id,
                target_endpoint.id,
                source_ontology,
                target_ontology
            )
            
            if relationship_paths:
                self.logger.info(f"Using {len(relationship_paths)} relationship-specific path(s)")
                # If we found relationship-specific paths, use only those
                paths = [ReversiblePath(path, is_reverse=False) for path in relationship_paths]
                
                # If bidirectional, also check for reverse relationship paths
                if bidirectional:
                    reverse_relationship_paths = await self._find_paths_for_relationship(
                        session,
                        target_endpoint.id,
                        source_endpoint.id,
                        target_ontology,
                        source_ontology
                    )
                    if reverse_relationship_paths:
                        reverse_path_objects = [
                            ReversiblePath(path, is_reverse=True) 
                            for path in reverse_relationship_paths
                        ]
                        if preferred_direction == "reverse":
                            paths = reverse_path_objects + paths
                        else:
                            paths = paths + reverse_path_objects
            else:
                self.logger.debug(
                    "No relationship-specific paths found, falling back to general path search"
                )

        # If no relationship-specific paths found (or no endpoints provided), use general path finding
        if not relationship_paths:
            if bidirectional:
                # Search for both forward and reverse paths concurrently
                forward_task = asyncio.create_task(
                    self._find_direct_paths(session, source_ontology, target_ontology)
                )
                reverse_task = asyncio.create_task(
                    self._find_direct_paths(session, target_ontology, source_ontology)
                )
                
                # Wait for both tasks to complete
                forward_paths, reverse_paths = await asyncio.gather(forward_task, reverse_task)
                
                # Wrap forward paths
                paths = [ReversiblePath(path, is_reverse=False) for path in forward_paths]
                
                # Wrap reverse paths and add them
                reverse_path_objects = [
                    ReversiblePath(path, is_reverse=True) for path in reverse_paths
                ]
                
                # Order based on preferred direction
                if preferred_direction == "reverse":
                    paths = reverse_path_objects + paths
                else:
                    paths = paths + reverse_path_objects
                    
                self.logger.info(
                    f"Found {len(forward_paths)} forward and {len(reverse_paths)} reverse "
                    f"mapping path(s) for {source_ontology} <-> {target_ontology}"
                )
            else:
                # Just search for forward paths
                forward_paths = await self._find_direct_paths(session, source_ontology, target_ontology)
                paths = [ReversiblePath(path, is_reverse=False) for path in forward_paths]
                
                self.logger.info(
                    f"Found {len(forward_paths)} mapping path(s) for "
                    f"{source_ontology} -> {target_ontology}"
                )
        
        # Sort paths by priority (considering ReversiblePath priority adjustments)
        paths.sort(key=lambda p: p.priority or 999)
        
        # Cache the results
        await self._cache_paths(cache_key, paths)
        
        return paths
    
    async def find_best_path(
        self,
        session: AsyncSession,
        source_ontology: str,
        target_ontology: str,
        bidirectional: bool = False,
        source_endpoint: Optional[Endpoint] = None,
        target_endpoint: Optional[Endpoint] = None,
    ) -> Optional[Union[MappingPath, ReversiblePath]]:
        """
        Find the single best mapping path between ontologies.
        
        This is a convenience method that returns the highest priority path.
        
        Args:
            session: The database session
            source_ontology: Source ontology term
            target_ontology: Target ontology term
            bidirectional: If True, consider reverse paths as well
            source_endpoint: Optional source endpoint
            target_endpoint: Optional target endpoint
            
        Returns:
            The best path or None if no paths found
        """
        paths = await self.find_mapping_paths(
            session,
            source_ontology,
            target_ontology,
            bidirectional=bidirectional,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )
        
        return paths[0] if paths else None
    
    async def _find_paths_for_relationship(
        self, 
        session: AsyncSession, 
        source_endpoint_id: int,
        target_endpoint_id: int,
        source_ontology: str, 
        target_ontology: str
    ) -> List[MappingPath]:
        """
        Find mapping paths for a specific endpoint relationship.
        
        This method looks for paths that are explicitly associated with the relationship
        between two endpoints through the RelationshipMappingPath table.
        
        Args:
            session: Database session
            source_endpoint_id: ID of the source endpoint
            target_endpoint_id: ID of the target endpoint
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            
        Returns:
            List of MappingPath objects associated with the relationship, ordered by priority
        """
        self.logger.debug(
            f"Searching for relationship-specific paths from endpoint {source_endpoint_id} "
            f"to {target_endpoint_id} with ontologies '{source_ontology}' -> '{target_ontology}'"
        )
        
        # First, find the EndpointRelationship between these endpoints
        relationship_stmt = (
            select(EndpointRelationship)
            .where(EndpointRelationship.source_endpoint_id == source_endpoint_id)
            .where(EndpointRelationship.target_endpoint_id == target_endpoint_id)
        )
        
        try:
            relationship_result = await session.execute(relationship_stmt)
            relationship = relationship_result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error while finding endpoint relationship: {e}")
            raise BiomapperError(
                f"Database error in path finder: {e}",
                error_code=ErrorCode.DATABASE_QUERY_ERROR
            )
        
        if not relationship:
            self.logger.debug(
                f"No EndpointRelationship found between endpoints "
                f"{source_endpoint_id} and {target_endpoint_id}"
            )
            return []
        
        self.logger.debug(f"Found EndpointRelationship ID: {relationship.id}")
        
        # Now find RelationshipMappingPaths for this relationship with matching ontologies
        mapping_paths_stmt = (
            select(MappingPath)
            .join(
                RelationshipMappingPath,
                RelationshipMappingPath.ontology_path_id == MappingPath.id
            )
            .where(RelationshipMappingPath.relationship_id == relationship.id)
            .where(RelationshipMappingPath.source_ontology == source_ontology)
            .where(RelationshipMappingPath.target_ontology == target_ontology)
            .where(MappingPath.is_active == True)
            .options(
                selectinload(MappingPath.steps).joinedload(
                    MappingPathStep.mapping_resource
                )
            )
            .order_by(MappingPath.priority.asc())
        )
        
        try:
            result = await session.execute(mapping_paths_stmt)
            paths = result.scalars().unique().all()
            
            if paths:
                self.logger.info(
                    f"Found {len(paths)} relationship-specific mapping path(s) for "
                    f"relationship {relationship.id} ({source_ontology} -> {target_ontology})"
                )
                for path in paths:
                    self.logger.debug(
                        f" - Path ID: {path.id}, Name: '{path.name}', Priority: {path.priority}"
                    )
            else:
                self.logger.debug(
                    f"No relationship-specific mapping paths found for relationship "
                    f"{relationship.id} with ontologies {source_ontology} -> {target_ontology}"
                )
                
            return paths
            
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database query error finding relationship paths: {e}", exc_info=True
            )
            raise BiomapperError(
                f"Database error finding relationship paths between endpoints "
                f"{source_endpoint_id} and {target_endpoint_id}",
                error_code=ErrorCode.DATABASE_QUERY_ERROR,
                details={
                    "source_endpoint_id": source_endpoint_id,
                    "target_endpoint_id": target_endpoint_id,
                    "source_ontology": source_ontology,
                    "target_ontology": target_ontology,
                    "error": str(e)
                }
            )
    
    async def _find_direct_paths(
        self,
        session: AsyncSession,
        source_ontology: str,
        target_ontology: str
    ) -> List[MappingPath]:
        """
        Find direct mapping paths from source to target ontology.
        
        This method performs a complex query that checks the input ontology of the
        first step and the output ontology of the last step to ensure the path
        actually transforms from source to target.
        
        Args:
            session: Database session
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            
        Returns:
            List of MappingPath objects ordered by priority
        """
        self.logger.debug(
            f"Searching for direct mapping paths from '{source_ontology}' to '{target_ontology}'"
        )

        # First check if there are simple paths defined by source_type and target_type
        simple_stmt = (
            select(MappingPath)
            .where(MappingPath.source_type == source_ontology)
            .where(MappingPath.target_type == target_ontology)
            .where(MappingPath.is_active == True)
            .options(
                selectinload(MappingPath.steps).joinedload(
                    MappingPathStep.mapping_resource
                )
            )
            .order_by(MappingPath.priority.asc())
        )
        
        try:
            simple_result = await session.execute(simple_stmt)
            simple_paths = simple_result.scalars().unique().all()
            
            if simple_paths:
                self.logger.debug(
                    f"Found {len(simple_paths)} simple mapping path(s) using source_type/target_type"
                )
                for path in simple_paths:
                    self.logger.debug(
                        f" - Path: '{path.name}' (ID: {path.id}, Priority: {path.priority})"
                    )
                return simple_paths
        except SQLAlchemyError as e:
            self.logger.warning(f"Error in simple path query: {e}")

        # If no simple paths found, use complex query checking step ontologies
        # Subquery to find the first step's input ontology for each path
        first_step_sq = (
            select(MappingPathStep.mapping_path_id, MappingResource.input_ontology_term)
            .join(
                MappingResource,
                MappingPathStep.mapping_resource_id == MappingResource.id,
            )
            .where(MappingPathStep.step_order == 1)
            .distinct()
            .subquery("first_step_sq")
        )

        # Subquery to find the maximum step order for each path
        max_step_sq = (
            select(
                MappingPathStep.mapping_path_id,
                func.max(MappingPathStep.step_order).label("max_order"),
            )
            .group_by(MappingPathStep.mapping_path_id)
            .subquery("max_step_sq")
        )

        # Subquery to find the last step's output ontology for each path
        last_step_sq = (
            select(
                MappingPathStep.mapping_path_id, MappingResource.output_ontology_term
            )
            .join(
                MappingResource,
                MappingPathStep.mapping_resource_id == MappingResource.id,
            )
            .join(
                max_step_sq,
                (MappingPathStep.mapping_path_id == max_step_sq.c.mapping_path_id)
                & (MappingPathStep.step_order == max_step_sq.c.max_order),
            )
            .distinct()
            .subquery("last_step_sq")
        )

        # Main query to select MappingPaths matching source and target
        stmt = (
            select(MappingPath)
            .options(
                selectinload(MappingPath.steps).joinedload(
                    MappingPathStep.mapping_resource
                )
            )
            .join(first_step_sq, MappingPath.id == first_step_sq.c.mapping_path_id)
            .join(last_step_sq, MappingPath.id == last_step_sq.c.mapping_path_id)
            .where(first_step_sq.c.input_ontology_term == source_ontology)
            .where(last_step_sq.c.output_ontology_term == target_ontology)
            .where(MappingPath.is_active == True)
            .order_by(MappingPath.priority.asc())
        )
        
        try:
            result = await session.execute(stmt)
            paths = result.scalars().unique().all()
            
            if paths:
                self.logger.debug(
                    f"Found {len(paths)} direct mapping path(s) from '{source_ontology}' to '{target_ontology}'"
                )
                for path in paths:
                    self.logger.debug(
                        f" - Path ID: {path.id}, Name: '{path.name}', Priority: {path.priority}"
                    )
            else:
                self.logger.debug(
                    f"No direct mapping paths found from '{source_ontology}' to '{target_ontology}'"
                )
                
            return paths
            
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database query error finding direct paths: {e}", exc_info=True
            )
            raise BiomapperError(
                f"Database error finding paths from {source_ontology} to {target_ontology}",
                error_code=ErrorCode.DATABASE_QUERY_ERROR,
                details={"source": source_ontology, "target": target_ontology, "error": str(e)}
            ) from e
    
    async def _get_cached_paths(
        self, 
        cache_key: str
    ) -> Optional[List[Union[MappingPath, ReversiblePath]]]:
        """
        Get paths from cache if available and not expired.
        
        Args:
            cache_key: The cache key
            
        Returns:
            Cached paths or None if not found/expired
        """
        current_time = time.time()
        
        async with self._path_cache_lock:
            if cache_key in self._path_cache:
                # Check if cache entry is expired
                timestamp = self._path_cache_timestamps.get(cache_key, 0)
                if current_time - timestamp < self._path_cache_expiry_seconds:
                    self.logger.debug(f"Using cached paths for {cache_key}")
                    return self._path_cache[cache_key]
                else:
                    # Remove expired cache entry
                    self.logger.debug(f"Cache entry for {cache_key} expired, removing")
                    del self._path_cache[cache_key]
                    if cache_key in self._path_cache_timestamps:
                        del self._path_cache_timestamps[cache_key]
        
        return None
    
    async def _cache_paths(
        self, 
        cache_key: str, 
        paths: List[Union[MappingPath, ReversiblePath]]
    ) -> None:
        """
        Cache paths with timestamp.
        
        Args:
            cache_key: The cache key
            paths: The paths to cache
        """
        async with self._path_cache_lock:
            # Implement simple LRU by removing oldest entries if cache is full
            if len(self._path_cache) >= self._path_cache_max_size:
                # Find and remove the oldest entry
                oldest_key = min(
                    self._path_cache_timestamps.keys(), 
                    key=lambda k: self._path_cache_timestamps[k]
                )
                del self._path_cache[oldest_key]
                del self._path_cache_timestamps[oldest_key]
                self.logger.debug(f"Evicted oldest cache entry: {oldest_key}")
            
            # Add new entry
            self._path_cache[cache_key] = paths
            self._path_cache_timestamps[cache_key] = time.time()
            self.logger.debug(f"Cached {len(paths)} paths for {cache_key}")
    
    def clear_cache(self) -> None:
        """Clear all cached paths."""
        self._path_cache.clear()
        self._path_cache_timestamps.clear()
        self.logger.info("Path cache cleared")
    
    async def get_path_details(self, session: AsyncSession, path_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a mapping path including all steps.
        
        Args:
            session: Database session
            path_id: The ID of the mapping path
            
        Returns:
            A dictionary with detailed information about the path
        """
        try:
            # Query the path with its steps
            stmt = (select(MappingPath)
                    .where(MappingPath.id == path_id)
                    .options(selectinload(MappingPath.steps)
                            .selectinload(MappingPathStep.mapping_resource)))

            result = await session.execute(stmt)
            path = result.scalar_one_or_none()

            if not path:
                self.logger.warning(f"Path with ID {path_id} not found in metamapper DB.")
                return {}

            path_details = {}
            # Add details for each step in the path
            # Sort steps to ensure consistent ordering in details
            sorted_steps = sorted(path.steps, key=lambda s: s.step_order)
            for step in sorted_steps:
                step_order = step.step_order
                resource = step.mapping_resource

                # Create a step entry with relevant details
                step_key = f"step_{step_order}"
                path_details[step_key] = {
                    "resource_id": resource.id if resource else None,
                    "resource_name": resource.name if resource else "Unknown",
                    "resource_client": resource.client_class_path if resource else "Unknown",
                    # Use the actual ontology terms stored in the resource
                    "input_ontology": resource.input_ontology_term if resource else "Unknown",
                    "output_ontology": resource.output_ontology_term if resource else "Unknown",
                }
            
            self.logger.debug(f"Retrieved details for path {path_id}: {path_details}")
            return path_details

        except SQLAlchemyError as e:
            self.logger.warning(f"SQLAlchemyError getting path details for {path_id}: {str(e)}")
            return {} # Return empty dict on DB error, don't block the main operation
        except Exception as e:
            # Catch other potential errors during detail retrieval
            self.logger.warning(f"Unexpected error getting path details for {path_id}: {str(e)}", exc_info=True)
            return {} # Return empty dict on error, don't block the main operation
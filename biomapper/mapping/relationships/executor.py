"""
Relationship Mapping Executor Module.

This module implements the RelationshipMappingExecutor class for executing
mapping operations between endpoints using discovered relationship paths.
"""

# No external imports needed

# Import needed modules
import datetime
import json
import os
import aiohttp
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import sessionmaker
from biomapper.db.models import (
    Endpoint, MappingResource, EndpointRelationship, OntologyPreference, MappingPath, EntityMapping, Base
)
from biomapper.mapping.resources.clients.unichem_client import map_with_unichem

logger = logging.getLogger(__name__)

class RelationshipMappingExecutor:
    """Executes mappings based on defined relationship paths."""

    def __init__(self, db_session: AsyncSession, http_session: aiohttp.ClientSession):
        self.db_session = db_session
        self.http_session = http_session

    # Restoring execute_mapping method for direct path execution
    async def execute_mapping(self, input_entity: str, mapping_path: MappingPath) -> Tuple[Optional[str], float]:
        """Executes a series of mapping steps defined in a specific MappingPath object."""
        if not mapping_path.path_steps:
            logger.warning(f"Mapping path {mapping_path.id} has no steps defined.")
            return None, 0.0
        
        try:
            # Handle both string JSON and already parsed list/dict
            if isinstance(mapping_path.path_steps, str):
                path_steps = json.loads(mapping_path.path_steps)
            elif isinstance(mapping_path.path_steps, (list, dict)):
                 path_steps = mapping_path.path_steps
            else:
                 logger.error(f"Path steps for path {mapping_path.id} has unexpected type: {type(mapping_path.path_steps)}")
                 return None, 0.0
        except json.JSONDecodeError:
            logger.error(f"Could not decode path_steps JSON for path {mapping_path.id}: {mapping_path.path_steps}")
            return None, 0.0
        
        if not isinstance(path_steps, list) or not path_steps:
             logger.error(f"Path steps for path {mapping_path.id} are not a valid list or are empty: {path_steps}")
             return None, 0.0

        current_value = input_entity
        total_score = 1.0  # Start with a perfect score
        step_num = 0

        for step in path_steps:
            step_num += 1
            source_type = step.get('source_type')
            target_type = step.get('target_type')
            resource_id = step.get('resource_id')

            if not all([source_type, target_type, resource_id]):
                logger.error(f"Path {mapping_path.id}, Step {step_num}: Invalid step format - missing source_type, target_type, or resource_id: {step}")
                return None, 0.0

            logger.info(f"Path {mapping_path.id}, Step {step_num}: Mapping {current_value} ({source_type}) -> ({target_type}) using Resource ID {resource_id}")
            
            try:
                current_value, step_score = await self._execute_mapping_step(
                    current_value, source_type, target_type, resource_id
                )
                # Ensure step_score is float, default to 0.0 if None
                step_score = float(step_score) if step_score is not None else 0.0 
                total_score *= step_score  # Combine scores multiplicatively
                
                if current_value is None:
                    logger.warning(f"Path {mapping_path.id}, Step {step_num}: Mapping returned None. Stopping execution.")
                    return None, 0.0 # If any step fails, the whole path fails
            except Exception as e:
                logger.exception(f"Path {mapping_path.id}, Step {step_num}: Error executing mapping step: {e}")
                return None, 0.0

        logger.info(f"Path {mapping_path.id}: Final result = {current_value}, Total Score = {total_score:.4f}")
        # TODO: Persist the mapping result (input_entity -> current_value) and score in EntityMapping table?
        return current_value, total_score

    # Restoring _execute_mapping_step method
    async def _execute_mapping_step(
        self,
        input_value: str,
        source_type: str,
        target_type: str,
        resource_id: int
    ) -> Tuple[Optional[str], float]:
        """Executes a single step of the mapping using the appropriate resource client/adapter."""
        
        if resource_id == 10: # UniChem
            logger.debug(f"Using UniChem client for {source_type} -> {target_type}")
            output_value, score = await map_with_unichem(
                input_entity=input_value,
                input_ontology=source_type.upper(), # Ensure uppercase for UniChem client
                target_ontology=target_type.upper(), # Ensure uppercase for UniChem client
                session=self.http_session
            )
            return output_value, score
        else:
            logger.warning(f"No mapping implementation found for resource ID {resource_id} ({source_type} -> {target_type}). Returning None.")
            # For now, return None if no specific handler exists
            return None, 0.0

    async def map_entity(self, relationship_id: int, source_entity: str, 
                        source_ontology: Optional[str] = None, 
                        confidence_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Map an entity using the best available relationship path.
        
        Args:
            relationship_id: ID of the relationship to use
            source_entity: Source entity identifier
            source_ontology: Source ontology type (if None, uses endpoint's highest preference)
            confidence_threshold: Minimum confidence for results
            
        Returns:
            List of mapping results
        """
        async with self.db_session as session:
            try:
                # 1. Determine Source Ontology if not provided
                if not source_ontology:
                    # Use the refactored helper here
                    source_ontology = await self._get_default_source_ontology(session, relationship_id)
                    if not source_ontology:
                        logger.warning(f"Could not determine default source ontology for relationship {relationship_id}.")
                        return []
                    logger.debug(f"Using default source ontology: {source_ontology}")

                # 2. Find the best mapping path (still uses raw SQL temporarily)
                best_path = await self._get_best_relationship_path(session, relationship_id, source_ontology)
                if not best_path:
                    logger.warning(f"No suitable mapping path found for relationship {relationship_id} and source ontology {source_ontology}.")
                    return []
                
                ontology_path_id = best_path.id
                target_ontology = best_path.target_ontology_type # Get target from the path itself
                logger.debug(f"Selected mapping path ID: {ontology_path_id} ({source_ontology} -> {target_ontology})")

                # 3. Check full path cache first (still uses raw SQL temporarily)
                cached_result = await self._check_cache(session, source_entity, source_ontology, target_ontology)
                if cached_result:
                    logger.info(f"Full path cache hit for {source_ontology}:{source_entity} -> {target_ontology}")
                    # Convert raw SQL result dict to expected format
                    if cached_result.confidence >= confidence_threshold:
                        # Use refactored helper
                        await self._update_path_usage(session, ontology_path_id)
                        await session.commit() # Commit path usage update
                        return [{
                            "source_id": cached_result.source_id,
                            "source_type": cached_result.source_type,
                            "target_id": cached_result.target_id,
                            "target_type": cached_result.target_type,
                            "confidence": cached_result.confidence,
                            "path": ontology_path_id, 
                            "mapping_source": "cache",
                            "metadata": json.loads(cached_result.metadata or '{}')
                        }]
                    else:
                         logger.debug(f"Full path cache hit for {source_ontology}:{source_entity} -> {target_ontology}, but confidence {cached_result.confidence} < {confidence_threshold}")

                # 4. Get the ontology path steps (Use refactored helper)
                ontology_path = best_path
                if not ontology_path or not ontology_path.steps: # Use the .steps property
                    logger.error(f"Ontology path {ontology_path_id} not found or has no steps.")
                    return []
                
                path_steps = json.loads(ontology_path.steps) # Parse the JSON steps
                logger.debug(f"Executing path steps: {path_steps}")

                # 5. Execute mapping steps (cache check/store still raw SQL temporarily)
                current_entity = source_entity
                current_ontology = source_ontology
                aggregated_confidence = 1.0
                step_results = []

                for i, step in enumerate(path_steps):
                    step_target_ontology = step['target_ontology']
                    step_resource_id = step['resource_id']
                    
                    logger.debug(f"Step {i+1}: Map {current_ontology}:{current_entity} -> {step_target_ontology} using resource {step_resource_id}")

                    # Check step cache (still raw SQL temporarily)
                    step_cache = await self._check_cache(session, current_entity, current_ontology, step_target_ontology)
                    if step_cache:
                         logger.info(f"Step cache hit: {current_ontology}:{current_entity} -> {step_target_ontology}")
                         next_entity = step_cache.target_id
                         step_confidence = step_cache.confidence or 1.0
                    else:
                        step_result = await self._execute_mapping_step(
                            session, current_entity, current_ontology, step_target_ontology, step_resource_id
                        )

                        if step_result and step_result[0] is not None:
                            next_entity, step_confidence = step_result
                            # Store step result in cache (still raw SQL temporarily)
                            await self._store_cache(
                                session,
                                source_entity=current_entity,
                                source_type=current_ontology,
                                target_entity=next_entity,
                                target_type=step_target_ontology,
                                confidence=step_confidence,
                                mapping_source=f"resource_{step_resource_id}",
                                is_derived=False,
                                derivation_path=None
                            )
                        else:
                            logger.warning(f"Mapping step {i+1} failed for {current_ontology}:{current_entity} -> {step_target_ontology}")
                            aggregated_confidence = 0.0
                            break

                    step_results.append({
                        "input_entity": current_entity,
                        "input_ontology": current_ontology,
                        "output_entity": next_entity,
                        "output_ontology": step_target_ontology,
                        "resource_id": step_resource_id,
                        "confidence": step_confidence
                    })

                    current_entity = next_entity
                    current_ontology = step_target_ontology
                    aggregated_confidence *= step_confidence

                    if aggregated_confidence < confidence_threshold:
                        logger.warning(f"Aggregated confidence {aggregated_confidence:.4f} dropped below threshold {confidence_threshold} at step {i+1}.")
                        aggregated_confidence = 0.0
                        break

                # 6. Process final result (Store still raw SQL temporarily)
                final_results = []
                if aggregated_confidence >= confidence_threshold and current_ontology == target_ontology:
                    final_target_id = current_entity
                    logger.info(f"Mapping successful: {source_ontology}:{source_entity} -> {target_ontology}:{final_target_id} (Confidence: {aggregated_confidence}) - Storing full path result.")
                    
                    await self._store_cache(
                        session,
                        source_entity=source_entity,
                        source_type=source_ontology,
                        target_entity=final_target_id,
                        target_type=target_ontology,
                        confidence=aggregated_confidence,
                        mapping_source="derived",
                        is_derived=True,
                        derivation_path=[ontology_path_id]
                    )
                    
                    # Use refactored helper
                    await self._update_path_usage(session, ontology_path_id)

                    final_results.append({
                        "source_id": source_entity,
                        "source_type": source_ontology,
                        "target_id": final_target_id,
                        "target_type": target_ontology,
                        "confidence": aggregated_confidence,
                        "path": ontology_path_id,
                        "mapping_source": "executor",
                        "metadata": {"steps": step_results}
                    })
                else:
                     logger.warning(f"Mapping failed or confidence too low for {source_ontology}:{source_entity}. Final confidence: {aggregated_confidence}, Target reached: {current_ontology == target_ontology}")


                await session.commit()
                return final_results

            except Exception as e:
                logger.error(f"Error during mapping for relationship {relationship_id}, entity {source_entity}: {e}")
                await session.rollback()
                return []

    # --- Refactored Helper Methods --- 

    async def _get_default_source_ontology(self, session: AsyncSession, relationship_id: int) -> Optional[str]:
        """Gets the highest priority default source ontology for a relationship using ORM."""
        try:
            # Get relationship to find source endpoint ID
            stmt_rel = select(EndpointRelationship).where(EndpointRelationship.id == relationship_id)
            result_rel = await session.execute(stmt_rel)
            relationship = result_rel.scalar_one_or_none()
            if not relationship:
                logger.warning(f"Relationship ID {relationship_id} not found.")
                return None

            source_endpoint_id = relationship.source_endpoint_id

            # Find highest priority ontology preference for the source endpoint
            stmt_pref = (
                select(OntologyPreference.ontology_name)
                .where(OntologyPreference.endpoint_id == source_endpoint_id)
                .order_by(OntologyPreference.priority.asc()) # Lower priority number is higher preference
                .limit(1)
            )
            result_pref = await session.execute(stmt_pref)
            ontology_name = result_pref.scalar_one_or_none()
            if ontology_name:
                 logger.debug(f"Found default source ontology '{ontology_name}' for relationship {relationship_id} (endpoint {source_endpoint_id})")
            else:
                 logger.debug(f"No default source ontology preference found for endpoint {source_endpoint_id}")
            return ontology_name
        except Exception as e:
            logger.error(f"Error fetching default source ontology for relationship {relationship_id}: {e}")
            return None

    async def _get_ontology_path(self, session: AsyncSession, ontology_path_id: int) -> Optional[MappingPath]:
        """Retrieves a specific ontology mapping path by its ID using ORM."""
        try:
            # Use session.get for primary key lookup - much simpler!
            ontology_path = await session.get(MappingPath, ontology_path_id)
            if not ontology_path:
                logger.warning(f"Ontology path with ID {ontology_path_id} not found.")
            # Log the retrieved path steps for debugging
            # elif ontology_path.path_steps:
            #     logger.debug(f"Retrieved path {ontology_path_id} steps: {ontology_path.steps}")
            return ontology_path
        except Exception as e:
            logger.error(f"Error fetching ontology path {ontology_path_id}: {e}")
            return None


    async def _update_path_usage(self, session: AsyncSession, ontology_path_id: int) -> None:
        """Increments usage count and updates last used timestamp for a mapping path using ORM."""
        try:
            # Use ORM update approach
            stmt = (
                update(MappingPath)
                .where(MappingPath.id == ontology_path_id)
                .values(
                    usage_count=MappingPath.usage_count + 1,
                    # Use timezone aware UTC now
                    last_used=datetime.datetime.now(datetime.timezone.utc)
                 )
                # Don't synchronize session state, direct update is fine
                .execution_options(synchronize_session=False)
            )
            result = await session.execute(stmt)
            if result.rowcount == 0:
                 logger.warning(f"Attempted to update usage for non-existent path ID {ontology_path_id}")
            else:
                 logger.debug(f"Updated usage stats for path {ontology_path_id}")
            # No explicit commit here, handled in map_entity caller
        except Exception as e:
            logger.error(f"Error updating usage for path {ontology_path_id}: {e}")
            # Rollback likely handled by caller

    # --- Refactored Caching Methods ---

    async def _check_cache(self, session: AsyncSession, source_entity: str, source_type: str, target_type: str) -> Optional[EntityMapping]:
        """Checks the cache for an existing mapping using ORM."""
        try:
            stmt = (
                select(EntityMapping)
                .where(
                    EntityMapping.source_id == source_entity,
                    EntityMapping.source_type == source_type,
                    EntityMapping.target_type == target_type
                 )
                # Get the best available mapping (highest confidence, most recent)
                .order_by(EntityMapping.confidence.desc().nullslast(), EntityMapping.last_updated.desc())
                .limit(1)
             )

            result = await session.execute(stmt)
            cached_mapping = result.scalar_one_or_none()

            if cached_mapping:
                # Check expiration
                now = datetime.datetime.now(datetime.timezone.utc)
                if cached_mapping.expires_at and cached_mapping.expires_at < now:
                    logger.debug(f"Cache hit for {source_type}:{source_entity} -> {target_type} but expired at {cached_mapping.expires_at}. Treating as miss.")
                    # Optionally delete expired entry here or have a separate cleanup process
                    # await session.delete(cached_mapping)
                    # await session.flush() # Flush deletion if needed before returning
                    return None

                # Optional: Update usage count on cache hit? Debatable.
                # cached_mapping.usage_count += 1
                # cached_mapping.last_updated = now
                # logger.debug(f"Cache hit: Updated usage count for mapping ID {cached_mapping.id}")

                logger.debug(f"Cache hit for {source_type}:{source_entity} -> {target_type} (ID: {cached_mapping.id}, Target: {cached_mapping.target_id})")
                return cached_mapping
            else:
                logger.debug(f"Cache miss for {source_type}:{source_entity} -> {target_type}")
                return None
        except Exception as e:
            logger.error(f"Error checking cache for {source_type}:{source_entity} -> {target_type}: {e}")
            return None


    async def _store_cache(
        self,
        session: AsyncSession,
        source_entity: str,
        source_type: str,
        target_entity: str,
        target_type: str,
        confidence: float,
        mapping_source: str,
        is_derived: bool,
        derivation_path: Optional[List[int]] = None,
        ttl_days: int = 365 # Default TTL
        ) -> None:
        """Stores or updates a mapping in the cache using ORM."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            expires_at = now + datetime.timedelta(days=ttl_days) if ttl_days > 0 else None

            # Check if this exact mapping already exists to decide between update and insert
            stmt = select(EntityMapping).where(
                EntityMapping.source_id == source_entity,
                EntityMapping.source_type == source_type,
                EntityMapping.target_id == target_entity, # Match exact target ID
                EntityMapping.target_type == target_type
            ).limit(1)
            result = await session.execute(stmt)
            existing_mapping = result.scalar_one_or_none()

            if existing_mapping:
                # Update existing mapping
                existing_mapping.confidence = confidence
                existing_mapping.mapping_source = mapping_source
                existing_mapping.is_derived = is_derived
                # Use the property setter for derivation path list
                existing_mapping.derivation_path_list = derivation_path or []
                existing_mapping.last_updated = now
                existing_mapping.usage_count = existing_mapping.usage_count + 1 # Increment usage on store/update
                existing_mapping.expires_at = expires_at
                logger.debug(f"Updating existing cache entry ID {existing_mapping.id} for {source_type}:{source_entity} -> {target_type}:{target_entity}")
                # session.add(existing_mapping) # Not strictly necessary if object is already managed
            else:
                 # Create new mapping
                new_mapping = EntityMapping(
                    source_id=source_entity,
                    source_type=source_type,
                    target_id=target_entity,
                    target_type=target_type,
                    confidence=confidence,
                    mapping_source=mapping_source,
                    is_derived=is_derived,
                    # derivation_path handled by property below
                    last_updated=now,
                    usage_count=1, # Initial usage
                    expires_at=expires_at
                )
                # Set derivation path list using the setter property
                new_mapping.derivation_path_list = derivation_path or []
                session.add(new_mapping)
                logger.debug(f"Storing new cache entry for {source_type}:{source_entity} -> {target_type}:{target_entity}")

            # Flush to ensure the operation happens before potential commit/rollback by caller
            await session.flush()

        except Exception as e:
            # Log the detailed error context
            log_context = f"source={source_type}:{source_entity}, target={target_type}:{target_entity}, conf={confidence}, src={mapping_source}, derived={is_derived}, path={derivation_path}"
            logger.error(f"Error storing cache entry ({log_context}): {e}")
            # Rollback should be handled by the main map_entity caller

    async def _get_best_relationship_path(
        self,
        session: AsyncSession,
        relationship_id: int,
        source_ontology_type: str
    ) -> Optional[MappingPath]: # Return the whole MappingPath object
        """
        Determines the best MappingPath object based on relationship, source ontology,
        preferences, and usage using ORM.

        Prioritizes paths based on:
        1. Target Endpoint's preference for the path's source ontology type.
        2. Path usage count (higher is better).
        """
        try:
            # Subquery to get the target endpoint ID for the relationship
            target_endpoint_subq = (
                select(EndpointRelationship.target_endpoint_id)
                .where(EndpointRelationship.id == relationship_id)
                .scalar_subquery()
                .correlate(None) # Ensure it doesn't correlate unintentionally
            )

            # Main query to find the best path object
            stmt = (
                select(MappingPath) # Select the whole object
                .join(EndpointRelationship, MappingPath.relationship_id == EndpointRelationship.id)
                # Join OntologyPreference LEFT OUTER JOIN to get preference priority
                # We join on the *target* endpoint's preference for the *path's source* ontology type
                .outerjoin(
                    OntologyPreference,
                    and_(
                        OntologyPreference.endpoint_id == target_endpoint_subq,
                        OntologyPreference.relationship_id == MappingPath.relationship_id,
                        OntologyPreference.ontology_name == MappingPath.source_ontology_type # Preference for the type we are *receiving* from the path
                    )
                )
                .where(
                    MappingPath.relationship_id == relationship_id,
                    MappingPath.source_ontology_type == source_ontology_type,
                    # Removed target_ontology_type constraint - find best path *from* source
                    MappingPath.is_enabled == True # Only consider enabled paths
                )
                .order_by(
                    OntologyPreference.priority.desc().nullslast(), # Highest priority first (nulls last)
                    MappingPath.usage_count.desc().nullslast()      # Most used path as tie-breaker (nulls last)
                )
                .limit(1)
            )

            result = await session.execute(stmt)
            best_path = result.scalar_one_or_none() # Get the MappingPath object or None

            if best_path:
                logger.debug(f"Found best path ID: {best_path.id} ({best_path.source_ontology_type} -> {best_path.target_ontology_type}) for relationship {relationship_id} starting from {source_ontology_type}")
            else:
                logger.warning(f"No suitable path found for relationship {relationship_id} starting from {source_ontology_type}")

            return best_path # Return the object or None

        except Exception as e:
            logger.error(f"Error finding best path for relationship {relationship_id} from {source_ontology_type}: {e}")
            return None

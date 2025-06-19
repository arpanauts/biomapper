"""
Relationship Mapping Executor Module.

This module implements the RelationshipMappingExecutor class for executing
mapping operations between endpoints using discovered relationship paths.
"""

# No external imports needed

# Import needed modules
import datetime
import json
import aiohttp
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, or_
from biomapper.db.cache_models import (
    EntityMapping,
)
from biomapper.db.models import (
    Endpoint,
    MappingResource,
    EndpointRelationship,
    OntologyPreference,
    MappingPath,
)
from biomapper.mapping.resources.clients.unichem_client import map_with_unichem
from biomapper.mapping.clients.uniprot_name_client import UniProtNameClient
from biomapper.mapping.clients.umls_client import UMLSClient
from biomapper.mapping.adapters.spoke_adapter import SpokeClient

logger = logging.getLogger(__name__)


class RelationshipMappingExecutor:
    """Executes mappings based on defined relationship paths."""

    def __init__(self, db_session: AsyncSession, http_session: aiohttp.ClientSession):
        self.db_session = db_session
        self.http_session = http_session

    # Restoring execute_mapping method for direct path execution
    async def execute_mapping(
        self, input_entity: str, mapping_path: MappingPath
    ) -> Tuple[Optional[str], float]:
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
                logger.error(
                    f"Path steps for path {mapping_path.id} has unexpected type: {type(mapping_path.path_steps)}"
                )
                return None, 0.0
        except json.JSONDecodeError:
            logger.error(
                f"Could not decode path_steps JSON for path {mapping_path.id}: {mapping_path.path_steps}"
            )
            return None, 0.0

        if not isinstance(path_steps, list) or not path_steps:
            logger.error(
                f"Path steps for path {mapping_path.id} are not a valid list or are empty: {path_steps}"
            )
            return None, 0.0

        current_value = input_entity
        total_score = 1.0  # Start with a perfect score
        step_num = 0

        for step in path_steps:
            async with self.db_session.begin_nested() if self.db_session.in_transaction() else self.db_session.begin() as nested_step_transaction:
                step_session = nested_step_transaction.session

                step_num += 1
                step_source_type = step.get("source")
                step_target_type = step.get("target")
                resource_name = step.get("resource_name")

                if not all([step_source_type, step_target_type, resource_name]):
                    logger.error(
                        f"Path {mapping_path.id}, Step {step_num}: Invalid step format - missing source, target, or resource_name: {step}"
                    )
                    await nested_step_transaction.rollback()
                    return None, 0.0

                # Look up resource_id from resource_name
                resource_id_stmt = (
                    select(MappingResource.id)
                    .where(MappingResource.name == resource_name)
                    .limit(1)
                )
                resource_id_res = await step_session.execute(resource_id_stmt)
                resource_id = resource_id_res.scalar_one_or_none()

                if resource_id is None:
                    logger.error(
                        f"Path {mapping_path.id}, Step {step_num}: Could not find resource ID for resource_name '{resource_name}'"
                    )
                    await nested_step_transaction.rollback()
                    return None, 0.0

                logger.info(
                    f"Path {mapping_path.id}, Step {step_num}: Mapping {current_value} ({step_source_type}) -> ({step_target_type}) using Resource '{resource_name}' (ID: {resource_id})"
                )

                try:
                    current_value, step_score = await self._execute_mapping_step(
                        step_session,
                        current_value,
                        step_source_type,
                        step_target_type,
                        resource_id,
                    )
                    # Ensure step_score is float, default to 0.0 if None
                    step_score = float(step_score) if step_score is not None else 0.0
                    total_score *= step_score  # Combine scores multiplicatively

                    if current_value is None:
                        logger.warning(
                            f"Path {mapping_path.id}, Step {step_num}: Mapping returned None. Stopping execution."
                        )
                        return None, 0.0  # If any step fails, the whole path fails
                except Exception:
                    logger.error(
                        f"Path {mapping_path.id}, Step {step_num}: Error executing mapping step",
                        exc_info=True,
                    )
                    await nested_step_transaction.rollback()
                    return None, 0.0

                # Commit the nested transaction for this step if successful
                # Although _execute_mapping_step might handle its own transactions depending on implementation
                # await nested_step_transaction.commit() # Might not be needed if _execute_mapping_step commits

        logger.info(
            f"Path {mapping_path.id}: Final result = {current_value}, Total Score = {total_score:.4f}"
        )
        # TODO: Persist the mapping result (input_entity -> current_value) and score in EntityMapping table?
        return current_value, total_score

    # Restoring _execute_mapping_step method
    async def _execute_mapping_step(
        self,
        session: AsyncSession,
        current_value: str,
        source_type: str,
        target_type: str,
        resource_id: int,
    ) -> Tuple[Optional[str], float]:
        """Executes a single mapping step using the appropriate resource client."""

        resource_info_stmt = (
            select(MappingResource.name)
            .where(MappingResource.id == resource_id)
            .limit(1)
        )
        result = await session.execute(resource_info_stmt)
        resource_name = result.scalar_one_or_none()

        if not resource_name:
            logger.error(f"Could not find mapping resource with ID {resource_id}")
            return None, 0.0

        mapped_value = None
        confidence = 0.0

        # --- Client Dispatch Logic ---
        if resource_name == "UniChem":
            logger.debug(
                f"Using UniChem client for step: {source_type} -> {target_type}"
            )
            try:
                # Ensure map_with_unichem uses an HTTP client session managed appropriately
                mapped_value, confidence = await map_with_unichem(
                    input_entity=current_value,
                    input_ontology=source_type.upper(),  # Ensure uppercase for UniChem client
                    target_ontology=target_type.upper(),  # Ensure uppercase for UniChem client
                    session=self.http_session,
                )
            except Exception as e:
                logger.error(f"Error mapping with UniChem: {e}", exc_info=True)
                return None, 0.0
        elif resource_name == "UniProt_NameSearch":
            logger.debug(
                f"Using UniProt Name Search client for step: {source_type} -> {target_type}"
            )
            try:
                client = UniProtNameClient(session=self.http_session)
                # Assuming find_uniprot_id takes the name (current_value) and returns (value, confidence)
                mapped_value, confidence = await client.find_uniprot_id(current_value)
                logger.debug(
                    f"UniProt client returned: {mapped_value} (Confidence: {confidence})"
                )
            except Exception as e:
                logger.error(
                    f"Error mapping with UniProt Name Search: {e}", exc_info=True
                )
                return None, 0.0
        elif resource_name == "UMLS_Metathesaurus":
            logger.debug(
                f"Using UMLS Metathesaurus client for step: {source_type} -> {target_type}"
            )
            try:
                client = UMLSClient(session=self.http_session)
                # Assuming find_cui takes the term (current_value) and returns (value, confidence)
                # NOTE: find_cui method needs implementation in UMLSClient
                mapped_value, confidence = await client.find_cui(current_value)
                logger.debug(
                    f"UMLS client returned: {mapped_value} (Confidence: {confidence})"
                )
            except AttributeError:
                logger.error(
                    "UMLSClient does not have the 'find_cui' method implemented yet.",
                    exc_info=True,
                )
                return None, 0.0
            except Exception as e:
                logger.error(
                    f"Error mapping with UMLS Metathesaurus: {e}", exc_info=True
                )
                return None, 0.0
        else:
            logger.warning(
                f"No mapping implementation found for resource '{resource_name}' (ID: {resource_id}). Step: {source_type} -> {target_type}. Returning None."
            )
            return None, 0.0

        return mapped_value, confidence

    async def map_entity(
        self,
        relationship_id: int,
        source_entity: str,
        source_ontology: Optional[str] = None,
        confidence_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Map an entity using the best available relationship path.

        Args:
            relationship_id: ID of the relationship to use
            source_entity: Source entity identifier
            source_ontology: Optional source entity ontology type (e.g., 'PUBCHEM')
            confidence_threshold: Minimum confidence score for results

        Returns:
            List of mapping results
        """
        async with self.db_session.begin_nested() if self.db_session.in_transaction() else self.db_session.begin() as nested_transaction:
            try:
                session = nested_transaction.session

                # 1. Determine Source Ontology if not provided
                if not source_ontology:
                    source_ontology = await self._get_default_source_ontology(
                        session, relationship_id
                    )
                    if not source_ontology:
                        logger.error(
                            f"Could not determine default source ontology for relationship {relationship_id}"
                        )
                        return []
                    logger.info(f"Using default source ontology: {source_ontology}")

                # 2. Find the Best Path for this relationship and source ontology
                best_path_result = await self._get_best_relationship_path(
                    session, relationship_id, source_ontology
                )
                if not best_path_result:
                    logger.warning(
                        f"No suitable mapping path found for relationship {relationship_id} and source ontology {source_ontology}."
                    )
                    return []

                best_path, target_type = best_path_result

                # 3. Check Cache (using the determined path's target type)
                cache_result = await self._check_cache(
                    session, source_entity, source_ontology, target_type
                )
                if cache_result and cache_result.confidence >= confidence_threshold:
                    logger.info(
                        f"Cache hit: {source_ontology}:{source_entity} -> {target_type}:{cache_result.target_id} (Confidence: {cache_result.confidence})"
                    )
                    # Update path usage even on cache hit
                    if best_path:
                        await self._update_path_usage(session, best_path.id)
                    await nested_transaction.commit()
                    return [
                        {
                            "target_id": cache_result.target_id,
                            "target_type": cache_result.target_type,
                            "confidence": cache_result.confidence,
                            "mapping_source": cache_result.mapping_source,
                            "mapping_path_id": best_path.id
                            if best_path
                            else None,  # Include path ID
                        }
                    ]
                else:
                    logger.info(
                        f"Cache miss or low confidence for {source_ontology}:{source_entity} -> {target_type}."
                    )

                # 4. Execute Mapping using the best path
                if best_path:
                    logger.info(
                        f"Executing mapping path {best_path.id} ({best_path.source_type} -> {best_path.target_type})..."
                    )
                    mapped_entity, confidence_score = await self.execute_mapping(
                        source_entity, best_path
                    )
                    await self._update_path_usage(session, best_path.id)
                else:
                    mapped_entity = source_entity
                    confidence_score = 1.0

                # 5. SPOKE Validation (If target is SPOKE and mapping succeeded)
                validated_entity = mapped_entity
                original_confidence = confidence_score
                mapping_source_str = f"path_{best_path.id}" if best_path else "no_path"

                # Get target endpoint info to check if it's SPOKE
                target_info = await self._get_target_endpoint_info(
                    session, relationship_id
                )

                if (
                    target_info
                    and target_info.get("type") == "spoke"
                    and mapped_entity is not None
                ):
                    logger.info(
                        f"Target endpoint '{target_info.get('name')}' is SPOKE. Attempting validation..."
                    )
                    spoke_client = await self._get_spoke_client(
                        session, relationship_id
                    )
                    if spoke_client:
                        spoke_entity_type = self._get_spoke_entity_type_for_ontology(
                            target_type
                        )
                        logger.info(
                            f"Checking SPOKE for {spoke_entity_type} with ID {mapped_entity}"
                        )

                        # The get_entity method needs to be async or run in an executor
                        # Assuming SpokeClient methods are async as they involve I/O
                        try:
                            validation_result = await spoke_client.get_entity(
                                spoke_entity_type, mapped_entity
                            )
                            if validation_result:
                                logger.info(
                                    f"SPOKE Validation Successful for {mapped_entity}. Setting confidence to 1.0."
                                )
                                confidence_score = (
                                    1.0  # Override confidence if found in SPOKE
                                )
                                mapping_source_str += ",spoke_validated"
                            else:
                                logger.warning(
                                    f"SPOKE Validation Failed: {mapped_entity} not found in SPOKE as {spoke_entity_type}. Discarding result."
                                )
                                # Set mapped_entity to None to prevent caching/returning failed validation
                                mapped_entity = None
                                confidence_score = 0.0
                        except Exception as spoke_exc:
                            logger.error(
                                f"Error during SPOKE validation for {mapped_entity}: {spoke_exc}",
                                exc_info=True,
                            )
                            # Decide if we should proceed with the unvalidated result or discard
                            # For now, let's discard if validation fails due to error
                            mapped_entity = None
                            confidence_score = 0.0
                    else:
                        logger.error("Could not initialize SpokeClient for validation.")
                        # Decide policy: proceed without validation or fail?
                        # Let's proceed but log warning, keep original confidence.
                        logger.warning(
                            "Proceeding without SPOKE validation due to client initialization failure."
                        )
                        validated_entity = mapped_entity  # Keep original mapping
                        confidence_score = original_confidence  # Keep original score
                else:
                    validated_entity = mapped_entity  # No validation needed or mapping failed initially
                    confidence_score = confidence_score

                # 6. Store Result in Cache (if mapping succeeded and passed validation if applicable)
                results = []
                if (
                    validated_entity is not None
                    and confidence_score >= confidence_threshold
                ):
                    logger.info(
                        f"Mapping successful: {source_ontology}:{source_entity} -> {target_type}:{validated_entity} (Confidence: {confidence_score}, Source: {mapping_source_str})"
                    )
                    await self._store_cache(
                        session,
                        source_entity,
                        source_ontology,
                        validated_entity,
                        target_type,
                        confidence_score,
                        mapping_source=mapping_source_str,
                        is_derived=False,  # Direct mapping execution
                        derivation_path=None,
                    )
                    results.append(
                        {
                            "target_id": validated_entity,
                            "target_type": target_type,
                            "confidence": confidence_score,
                            "mapping_source": mapping_source_str,
                            "mapping_path_id": best_path.id
                            if best_path
                            else None,  # Include path ID
                        }
                    )
                elif (
                    validated_entity is None
                    and target_info
                    and target_info.get("type") == "spoke"
                ):
                    # Explicitly log failure due to SPOKE validation
                    logger.warning(
                        f"Mapping discarded for {source_ontology}:{source_entity} due to failed SPOKE validation."
                    )
                elif confidence_score < confidence_threshold:
                    logger.warning(
                        f"Mapping result confidence {confidence_score} below threshold {confidence_threshold} for {source_ontology}:{source_entity}."
                    )
                else:
                    # General mapping failure (e.g., execute_mapping returned None)
                    logger.warning(
                        f"Mapping failed for {source_ontology}:{source_entity}."
                    )

                # Commit transaction for this entity
                await nested_transaction.commit()
                return results

            except Exception as e:
                logger.exception(
                    f"Error mapping entity {source_entity} for relationship {relationship_id}: {e}"
                )
                # Rollback if using nested transaction, otherwise the main context manager handles it
                # await nested_transaction.rollback()
                return []  # Return empty list on error

    async def _get_default_source_ontology(
        self, session: AsyncSession, relationship_id: int
    ) -> Optional[str]:
        """Gets the highest priority default source ontology for a relationship using ORM."""
        stmt = (
            select(OntologyPreference.ontology_name)
            .join(
                EndpointRelationship,
                OntologyPreference.relationship_id == EndpointRelationship.id,
            )
            .join(Endpoint, EndpointRelationship.source_endpoint_id == Endpoint.id)
            .where(
                OntologyPreference.relationship_id == relationship_id,
                # Assuming role is implicitly 'source' by joining on source_endpoint_id
                # or that preferences are primarily defined per-relationship
            )
            .order_by(
                OntologyPreference.priority.asc()
            )  # Lower number = higher priority
            .limit(1)
        )
        result = await session.execute(stmt)
        ontology_name = result.scalar_one_or_none()
        if not ontology_name:
            # Fallback: Check default preference for the source endpoint itself? Might be needed.
            logger.warning(
                f"No specific source ontology preference found for relationship {relationship_id}."
            )
            # Add fallback logic here if necessary
        return ontology_name

    async def _get_ontology_path(
        self, session: AsyncSession, ontology_path_id: int
    ) -> Optional[MappingPath]:
        """Retrieves a specific ontology mapping path by its ID using ORM."""
        stmt = select(MappingPath).where(MappingPath.id == ontology_path_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_path_usage(
        self, session: AsyncSession, ontology_path_id: int
    ) -> None:
        """Increments usage count and updates last used timestamp for a mapping path using ORM."""
        try:
            stmt = (
                update(MappingPath)
                .where(MappingPath.id == ontology_path_id)
                .values(
                    usage_count=MappingPath.usage_count + 1,
                    last_used=datetime.datetime.utcnow(),
                )
                .execution_options(
                    synchronize_session=False
                )  # Important for async updates
            )
            await session.execute(stmt)
            # Removed commit here, should be handled by the caller's transaction
            logger.debug(f"Updated usage count for path {ontology_path_id}")
        except Exception as e:
            logger.error(f"Error updating usage count for path {ontology_path_id}: {e}")
            # Consider rollback or re-raising depending on transaction strategy

    async def _check_cache(
        self,
        session: AsyncSession,
        source_entity: str,
        source_type: str,
        target_type: str,
    ) -> Optional[EntityMapping]:  # Return the EntityMapping object or None
        """Checks the cache for an existing mapping using ORM."""
        now = datetime.datetime.utcnow()
        try:
            stmt = (
                select(EntityMapping)
                .where(
                    EntityMapping.source_id == source_entity,
                    EntityMapping.source_type == source_type,
                    EntityMapping.target_type == target_type,
                    or_(
                        EntityMapping.expires_at == None, EntityMapping.expires_at > now
                    ),
                )
                .order_by(
                    EntityMapping.confidence.desc().nullslast(),
                    EntityMapping.last_updated.desc(),
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            mapping = result.scalar_one_or_none()

            if mapping:
                # Update usage count on cache hit
                mapping.usage_count += 1
                mapping.last_updated = now  # Update last updated on hit
                await session.flush([mapping])  # Flush changes within the transaction
                # Commit should be handled by the caller
                logger.debug(
                    f"Cache hit: Found mapping ID {mapping.id} for {source_type}:{source_entity} -> {target_type}:{mapping.target_id}"
                )
                return mapping
            else:
                logger.debug(
                    f"Cache miss for {source_type}:{source_entity} -> {target_type}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Error checking cache for {source_type}:{source_entity} -> {target_type}: {e}"
            )
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
        ttl_days: int = 365,  # Default TTL
    ) -> None:
        """Stores or updates a mapping in the cache using ORM."""
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(days=ttl_days) if ttl_days else None
        derivation_path_json = json.dumps(derivation_path) if derivation_path else None

        try:
            # Check if mapping exists (ignoring expiration for update check)
            existing_stmt = (
                select(EntityMapping)
                .where(
                    EntityMapping.source_id == source_entity,
                    EntityMapping.source_type == source_type,
                    EntityMapping.target_id
                    == target_entity,  # Also check target_id for specific update
                    EntityMapping.target_type == target_type,
                )
                .limit(1)
            )

            result = await session.execute(existing_stmt)
            existing_mapping = result.scalar_one_or_none()

            if existing_mapping:
                # Update existing mapping
                existing_mapping.confidence = confidence
                existing_mapping.mapping_source = mapping_source
                existing_mapping.is_derived = is_derived
                existing_mapping.derivation_path = derivation_path_json
                existing_mapping.last_updated = now
                existing_mapping.expires_at = expires
                # Reset usage count on update? Or increment? Let's increment.
                existing_mapping.usage_count += 1
                await session.flush([existing_mapping])  # Flush changes
                logger.debug(f"Updated existing cache entry ID {existing_mapping.id}")
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
                    derivation_path=derivation_path_json,
                    last_updated=now,
                    expires_at=expires,
                    usage_count=1,  # Start usage count at 1
                )
                session.add(new_mapping)
                await session.flush(
                    [new_mapping]
                )  # Flush to get ID if needed, within transaction
                logger.debug(
                    f"Stored new cache entry for {source_type}:{source_entity} -> {target_type}:{target_entity}"
                )

            # Commit should be handled by the caller (map_entity)
        except Exception as e:
            logger.error(
                f"Error storing cache for {source_type}:{source_entity} -> {target_type}:{target_entity}: {e}"
            )
            # Consider rollback or re-raising

    async def _get_best_relationship_path(
        self, session: AsyncSession, relationship_id: int, source_ontology_type: str
    ) -> Optional[
        Tuple[Optional[MappingPath], str]
    ]:  # Return Optional path object and target type
        """
        Determines the best MappingPath object based on relationship and source ontology.

        1. Gets the preferred target ontology type for the relationship.
        2. If source type matches target type, returns (None, target_type).
        3. Otherwise, finds the most used, enabled path matching source and target types.
        """
        try:
            # 1. Get the correct preferred target ontology type for this relationship
            target_ontology_type = await self._get_preferred_target_ontology(
                session, relationship_id
            )

            if not target_ontology_type:
                # _get_preferred_target_ontology already logs the warning
                return None

            # logger.info message is now inside _get_preferred_target_ontology

            # 2. If source already matches the preferred target, no path is needed.
            if source_ontology_type == target_ontology_type:
                logger.info(
                    f"Source ontology '{source_ontology_type}' matches preferred target ontology. No mapping path needed."
                )
                # Return None for the path, but return the target type so the caller knows what it is.
                return (None, target_ontology_type)

            # 3. Find an enabled MappingPath from source_ontology_type to preferred_target_ontology_type
            # TODO: Add filtering based on is_enabled once the model supports it.
            path_stmt = (
                select(MappingPath)
                .where(
                    MappingPath.source_type == source_ontology_type,
                    MappingPath.target_type == target_ontology_type,
                    # MappingPath.is_enabled == True # Assuming this field exists based on previous code
                )
                .order_by(
                    MappingPath.usage_count.desc().nullslast()  # Prioritize by usage
                )
                .limit(1)
            )

            result = await session.execute(path_stmt)
            best_path = (
                result.scalar_one_or_none()
            )  # Get the MappingPath object or None

            if best_path:
                logger.debug(
                    f"Found best path ID: {best_path.id} ({best_path.source_type} -> {best_path.target_type}) matching source {source_ontology_type} and target {target_ontology_type}"
                )
            else:
                logger.warning(
                    f"No suitable enabled path found from {source_ontology_type} to {target_ontology_type}"
                )

            return best_path, target_ontology_type  # Return path and target type

        except Exception as e:
            # Add exc_info=True for full traceback in logs
            logger.error(
                f"Error finding best path for relationship {relationship_id} from {source_ontology_type}: {e}",
                exc_info=True,
            )
            return None

    async def _get_target_endpoint_info(
        self, session: AsyncSession, relationship_id: int
    ) -> Optional[Dict[str, Any]]:
        """Gets the target endpoint details, including connection info, for a relationship."""
        stmt = (
            select(
                Endpoint.id, Endpoint.name, Endpoint.type, Endpoint.connection_details
            )
            .join(
                EndpointRelationship,
                EndpointRelationship.target_endpoint_id == Endpoint.id,
            )
            .where(EndpointRelationship.id == relationship_id)
        )
        result = await session.execute(stmt)
        endpoint = result.fetchone()
        if endpoint:
            return {
                "endpoint_id": endpoint.id,
                "name": endpoint.name,
                "type": endpoint.type,
                "connection_details": endpoint.connection_details,
            }
        logger.warning(
            f"Could not find target endpoint for relationship {relationship_id}"
        )
        return None

    async def _get_preferred_target_ontology(
        self, session: AsyncSession, relationship_id: int
    ) -> Optional[str]:
        """Determines the preferred target ontology type based on OntologyPreference."""

        logger.debug(
            f"_get_preferred_target_ontology called for relationship_id: {relationship_id}"
        )

        # 1. Get the target endpoint ID for the given relationship_id
        target_endpoint_id_stmt = (
            select(EndpointRelationship.target_endpoint_id)
            .where(EndpointRelationship.id == relationship_id)
            .limit(1)
        )
        target_endpoint_id_res = await session.execute(target_endpoint_id_stmt)
        target_endpoint_id = target_endpoint_id_res.scalar_one_or_none()

        logger.debug(f"Found target_endpoint_id: {target_endpoint_id}")

        if not target_endpoint_id:
            logger.warning(
                f"_get_preferred_target_ontology: Could not find target endpoint for relationship {relationship_id}"
            )
            return None

        # 2. Find the highest priority preference for that relationship_id and target_endpoint_id
        pref_stmt = (
            select(OntologyPreference.ontology_name)
            .where(
                # OntologyPreference allows preferences set at either the relationship level OR the endpoint level.
                # For relationships, we need the one specific to this relationship AND target endpoint.
                OntologyPreference.relationship_id == relationship_id,
                OntologyPreference.endpoint_id == target_endpoint_id,
            )
            .order_by(OntologyPreference.priority.asc())
            .limit(1)
        )
        pref_res = await session.execute(pref_stmt)
        raw_pref_results = (
            pref_res.fetchall()
        )  # Use fetchall to see all results if limit(1) wasn't effective
        logger.debug(
            f"Preference query raw results (ontology_name): {raw_pref_results}"
        )

        preferred_ontology = raw_pref_results[0][0] if raw_pref_results else None

        if preferred_ontology:
            logger.info(
                f"Relationship {relationship_id}: Determined preferred target ontology type: {preferred_ontology}"
            )
        else:
            logger.warning(
                f"_get_preferred_target_ontology: No preference found for relationship {relationship_id} and target endpoint {target_endpoint_id}"
            )

        logger.debug(f"Returning preferred_ontology: {preferred_ontology}")
        return preferred_ontology

    async def _get_spoke_client(
        self, session: AsyncSession, relationship_id: int
    ) -> Optional[SpokeClient]:
        """Gets or initializes the SpokeClient using config from the target endpoint's connection_info."""
        target_info = await self._get_target_endpoint_info(session, relationship_id)
        if not target_info or target_info.get("type") != "spoke":
            logger.error(
                f"Target endpoint for relationship {relationship_id} not found or is not SPOKE."
            )
            return None

        endpoint_id = target_info.get("endpoint_id")
        connection_info_str = target_info.get("connection_details")

        if not endpoint_id:
            logger.error(
                f"Could not retrieve endpoint ID for SPOKE target in relationship {relationship_id}."
            )
            return None
        if not connection_info_str:
            logger.error(f"Missing connection_info for SPOKE endpoint {endpoint_id}.")
            return None

        try:
            # Parse the connection_info JSON string
            config = json.loads(connection_info_str)
            if not isinstance(config, dict):
                raise TypeError("Parsed connection_info is not a dictionary.")

            # Pass the parsed config dictionary directly to SpokeClient constructor
            spoke_client = SpokeClient(config)
            logger.info(
                f"Successfully initialized SpokeClient for endpoint {endpoint_id}"
            )
            return spoke_client
        except json.JSONDecodeError:
            logger.exception(
                f"Failed to parse connection_info JSON for endpoint {endpoint_id}: {connection_info_str}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Failed to initialize SpokeClient for endpoint {endpoint_id} from connection_info: {e}"
            )
            return None

    def _get_spoke_entity_type_for_ontology(self, ontology_type: str) -> str:
        """Maps ontology types to SPOKE entity types."""
        # Ensure comparison is case-insensitive
        ontology_type_upper = ontology_type.upper()
        mapping = {
            "CHEBI": "Compound",
            "HMDB": "Compound",
            "PUBCHEM": "Compound",  # Assuming PubChem CID maps to Compound
            "KEGG": "Compound",  # Assuming KEGG Compound maps to Compound
            "INCHIKEY": "Compound",  # SPOKE might index by InChIKey directly
            "UNIPROT": "Protein",
            "ENTREZ": "Gene",
            # Add more mappings based on SPOKE's schema and supported IDs
        }
        # Default to 'Compound' if no specific mapping is found,
        # or potentially raise an error if strict mapping is required.
        default_type = "Compound"
        entity_type = mapping.get(ontology_type_upper, default_type)
        if entity_type == default_type and ontology_type_upper not in mapping:
            logger.warning(
                f"No specific SPOKE entity type mapping found for ontology '{ontology_type}'. Defaulting to '{default_type}'."
            )
        return entity_type

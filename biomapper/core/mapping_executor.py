import asyncio
import importlib
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from biomapper.core.exceptions import BiomapperError, NoPathFoundError, ClientError

# Import models for metamapper DB
from ..db.models import (
    Endpoint, EndpointPropertyConfig, PropertyExtractionConfig, MappingPath, MappingPathStep, MappingResource, OntologyPreference
)
# Import models for cache DB
from ..db.cache_models import (
    Base as CacheBase, # Import the Base for cache tables
    EntityMapping, 
    EntityMappingProvenance, 
    PathExecutionLog as MappingPathExecutionLog,
    PathExecutionStatus
)

# Define PathLogMappingAssociation which is missing from cache_models.py
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.ext.declarative import declarative_base

# This class should be moved to cache_models.py later
class PathLogMappingAssociation(CacheBase):
    """Association between a mapping log and input/output identifiers."""
    
    __tablename__ = "path_log_mapping_associations"
    
    id = Column(Integer, primary_key=True)
    log_id = Column(Integer, ForeignKey("path_execution_logs.id"), nullable=False)
    input_identifier = Column(String(255), nullable=False)
    output_identifier = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<PathLogMappingAssociation log_id={self.log_id} input={self.input_identifier} output={self.output_identifier}>"

# Assume config holds the DB URLs
from ..utils.config import CONFIG_DB_URL, CACHE_DB_URL 

logger = logging.getLogger(__name__)

class MappingExecutor:
    """Executes mapping tasks based on configurations in metamapper.db."""

    def __init__(self, metamapper_db_url: str = CONFIG_DB_URL, mapping_cache_db_url: str = CACHE_DB_URL):
        """
        Initializes the MappingExecutor.

        :param metamapper_db_url: URL for the metamapper database.
        :param mapping_cache_db_url: URL for the mapping cache database.
        """
        self.engine = create_async_engine(metamapper_db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.cache_engine = create_async_engine(mapping_cache_db_url, echo=False)
        self.async_cache_session = sessionmaker(
            self.cache_engine, expire_on_commit=False, class_=AsyncSession
        )

        # Ensure cache tables are created (run this synchronously for simplicity during init)
        # It's generally better to run create_all in a separate setup script or use migrations,
        # but for simplicity in this context, we do it here.
        async def init_cache_db():
            async with self.cache_engine.begin() as conn:
                await conn.run_sync(CacheBase.metadata.create_all)

        # Run the async function to initialize the cache DB
        try:
            # Use asyncio.run() if not already in an event loop, or await if called from async context
            # Checking for a running loop to avoid RuntimeError
            try:
                loop = asyncio.get_running_loop()
                # If called from within an async function/loop, schedule it
                asyncio.ensure_future(init_cache_db())
                # Note: This might not guarantee completion before the executor is used.
                # A more robust approach would involve an async factory or explicit init method.
            except RuntimeError: # No running event loop
                asyncio.run(init_cache_db())
        except Exception as e:
            logger.error(f"Failed to initialize cache database schema: {e}")
            raise

        logger.info(f"MappingExecutor initialized with DB: {metamapper_db_url}, CacheDB: {mapping_cache_db_url}")
        
    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()

    async def _get_ontology_type(
        self, meta_session: AsyncSession, endpoint_name: str, property_name: str = "PrimaryIdentifier"
    ) -> Optional[str]:
        """Get the ontology type for a specific property of a given endpoint name."""
        try:
            # Join Endpoint -> EndpointPropertyConfig -> PropertyExtractionConfig
            stmt = (
                select(PropertyExtractionConfig.ontology_type)
                .join(EndpointPropertyConfig, EndpointPropertyConfig.property_extraction_config_id == PropertyExtractionConfig.id)
                .join(Endpoint, Endpoint.id == EndpointPropertyConfig.endpoint_id)
                .where(Endpoint.name == endpoint_name)
                .where(EndpointPropertyConfig.property_name == property_name)
                .limit(1) # Should only be one config per endpoint/property pair
            )
            result = await meta_session.execute(stmt)
            ontology_type = result.scalar_one_or_none()

            if ontology_type:
                logger.debug(f"Found ontology type '{ontology_type}' for endpoint '{endpoint_name}', property '{property_name}'")
                return ontology_type
            else:
                logger.warning(f"No EndpointPropertyConfig found linking endpoint '{endpoint_name}' and property '{property_name}' to a PropertyExtractionConfig.")
                return None

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching ontology type for {endpoint_name}.{property_name}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ontology type for {endpoint_name}.{property_name}: {e}", exc_info=True)
            return None

    async def _find_mapping_paths(
        self, session: AsyncSession, source_ontology: str, target_ontology: str
    ) -> List[MappingPath]:
        """Find all potential mapping paths from source to target ontology, ordered by priority."""
        logger.debug(f"Searching for mapping paths from '{source_ontology}' to '{target_ontology}'")

        # We need to join MappingPath -> MappingPathStep -> MappingResource 
        # for both the first step (to check source_ontology) 
        # and the last step (to check target_ontology).
        
        # Subquery to find the first step's input ontology for each path
        first_step_sq = (
            select(
                MappingPathStep.mapping_path_id,
                MappingResource.input_ontology_term
            )
            .join(MappingResource, MappingPathStep.mapping_resource_id == MappingResource.id)
            .where(MappingPathStep.step_order == 1)
            .distinct()
            .subquery('first_step_sq')
        )

        # Subquery to find the maximum step order for each path
        max_step_sq = (
            select(
                MappingPathStep.mapping_path_id,
                func.max(MappingPathStep.step_order).label('max_order')
            )
            .group_by(MappingPathStep.mapping_path_id)
            .subquery('max_step_sq')
        )

        # Subquery to find the last step's output ontology for each path
        last_step_sq = (
            select(
                MappingPathStep.mapping_path_id,
                MappingResource.output_ontology_term
            )
            .join(MappingResource, MappingPathStep.mapping_resource_id == MappingResource.id)
            .join(max_step_sq, 
                  (MappingPathStep.mapping_path_id == max_step_sq.c.mapping_path_id) & 
                  (MappingPathStep.step_order == max_step_sq.c.max_order))
            .distinct()
            .subquery('last_step_sq')
        )

        # Main query to select MappingPaths matching source and target
        stmt = (
            select(MappingPath)
            # Use selectinload for eager loading related steps and resources
            .options(selectinload(MappingPath.steps).joinedload(MappingPathStep.mapping_resource))
            .join(first_step_sq, MappingPath.id == first_step_sq.c.mapping_path_id)
            .join(last_step_sq, MappingPath.id == last_step_sq.c.mapping_path_id)
            .where(first_step_sq.c.input_ontology_term == source_ontology)
            .where(last_step_sq.c.output_ontology_term == target_ontology)
            .order_by(MappingPath.priority.asc()) # Lower number means higher priority
        )

        result = await session.execute(stmt)
        # Use unique() to handle potential duplicates if joins create multiple rows for the same path
        paths = result.scalars().unique().all()

        if paths:
            logger.debug(f"Found {len(paths)} potential mapping path(s) from '{source_ontology}' to '{target_ontology}'")
            # Log the found paths for clarity
            for path in paths:
                logger.debug(f" - Path ID: {path.id}, Name: '{path.name}', Priority: {path.priority}")
        else:
            logger.warning(f"No direct mapping paths found from '{source_ontology}' to '{target_ontology}'")

        return paths

    async def _find_best_path(self, session: AsyncSession, source_type: str, target_type: str) -> Optional[MappingPath]:
        """Find the highest priority mapping path."""
        paths = await self._find_mapping_paths(session, source_type, target_type)
        return paths[0] if paths else None

    def _load_client_class(self, client_class_path: str) -> type:
        """Dynamically load the client class."""
        try:
            module_path, class_name = client_class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            ClientClass = getattr(module, class_name)
            return ClientClass
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            logger.error(f"Error loading client class '{client_class_path}': {e}", exc_info=True)
            raise ImportError(f"Could not load client class {client_class_path}: {e}")

    async def _load_client(self, resource: MappingResource) -> Any:
        """Loads and initializes a client instance."""
        client_class = self._load_client_class(resource.client_class_path)
        # Pass the parsed config to client init if needed
        config_for_init = json.loads(resource.config_template or '{}')
        client_instance = client_class(config=config_for_init)
        return client_instance

    async def _cache_results(
        self,
        cache_session: AsyncSession,
        path_log_id: int,
        source_ontology: str,
        target_ontology: str,
        results: Dict[str, Optional[List[str]]],
    ):
        """
        Caches the mapping results in the database, handling updates and provenance.

        Args:
            session: The database session.
            path_log_id: The ID of the PathExecutionLog entry for provenance.
            source_ontology: The source ontology type (e.g., 'GENE_NAME').
            target_ontology: The target ontology type (e.g., 'UNIPROTKB_AC').
            results: Dictionary of {original_source_id: mapped_value_list}.
        """
        now = datetime.now(timezone.utc)
        log_mapping_associations = []
        mappings_added_count = 0
        mappings_to_add_or_update = [] # Collect mappings to add/update

        # Retrieve the PathExecutionLog entry first
        path_log = await cache_session.get(MappingPathExecutionLog, path_log_id)
        if not path_log:
            logger.error(f"PathExecutionLog with ID {path_log_id} not found. Cannot cache results.")
            return

        unique_results_to_process = {} # Ensure we only process each source_id once
        for source_id, target_ids in results.items():
            if source_id not in unique_results_to_process:
                 unique_results_to_process[source_id] = target_ids

        for source_id, target_ids in unique_results_to_process.items():
            # Ensure target_ids is a list even if None for consistent processing
            processed_target_ids = target_ids if isinstance(target_ids, list) else ([target_ids] if target_ids else [])

            # Handle cases where mapping produced multiple results or no result
            if not processed_target_ids:
                target_id_str = None # Explicitly None if no mapping found
                logger.debug(f"Skipping cache for {source_id} -> None ({source_ontology} -> {target_ontology})")
                continue # Skip caching for this source_id
            elif len(processed_target_ids) == 1:
                target_id_str = str(processed_target_ids[0]) # Convert single result to string
            else:
                # Store multiple results as a JSON string list
                target_id_str = json.dumps(sorted([str(tid) for tid in processed_target_ids]))

            # Check if mapping already exists for this source_id, source_type, target_type
            stmt = select(EntityMapping).where(
                EntityMapping.source_id == source_id,
                EntityMapping.source_type == source_ontology,
                EntityMapping.target_type == target_ontology,
            )
            existing_mapping_result = await cache_session.execute(stmt)
            existing_mapping = existing_mapping_result.scalars().first()

            if existing_mapping:
                # Update existing mapping ONLY if target changed
                if existing_mapping.target_id != target_id_str:
                    existing_mapping.target_id = target_id_str
                    existing_mapping.last_updated = now
                    mappings_to_add_or_update.append(existing_mapping) # Mark for update
                    # Add association for this execution log
                    assoc = PathLogMappingAssociation(
                        log_id=path_log_id,
                        input_identifier=source_id,
                        output_identifier=target_id_str
                    )
                    log_mapping_associations.append(assoc)
                else:
                    # Mapping hasn't changed, but associate with this run if not already done
                    assoc_stmt = select(PathLogMappingAssociation).where(
                        PathLogMappingAssociation.log_id == path_log_id,
                        PathLogMappingAssociation.input_identifier == source_id,
                        PathLogMappingAssociation.output_identifier == target_id_str
                    )
                    existing_assoc_result = await cache_session.execute(assoc_stmt)
                    if not existing_assoc_result.scalars().first():
                         assoc = PathLogMappingAssociation(
                             log_id=path_log_id,
                             input_identifier=source_id,
                             output_identifier=target_id_str
                         )
                         log_mapping_associations.append(assoc) # Add association for existing mapping

            else:
                # Create new mapping
                mapping = EntityMapping(
                    source_id=source_id,
                    source_type=source_ontology,
                    target_id=target_id_str,
                    target_type=target_ontology,
                    last_updated=now,
                )
                mappings_to_add_or_update.append(mapping) # Mark for addition
                mappings_added_count += 1
                 # Association will be created after flush gives the new mapping ID

        # If nothing was added, updated, or needs associating, return early.
        if not mappings_to_add_or_update and not log_mapping_associations:
            logger.debug("All mapping results were either skipped (e.g., null targets), already up-to-date, or previously associated. Nothing new to commit.")
            return

        # Add/Update new mappings and associations to the session
        try:
            async with cache_session.begin_nested(): # Use nested transaction
                if mappings_to_add_or_update: # Only add/update if there are new/updated mappings
                    cache_session.add_all(mappings_to_add_or_update)
                    await cache_session.flush() # Flush to get IDs for new mappings and apply updates

                    # Create associations for NEW mappings (updated ones handled above)
                    # Need to re-query to reliably get IDs after flush if they were new
                    newly_added_mapping_ids = {m.id for m in mappings_to_add_or_update if m.id}
                    
                    for mapping in mappings_to_add_or_update:
                        if not mapping.id: # Should have ID after flush if it was added/updated
                             logger.warning(f"Mapping for source {mapping.source_id} did not receive an ID after flush.")
                             continue
                        # Check if it's a new mapping based on original count
                        # A better check might be needed if updates are frequent
                        is_new = any(mapping.source_id == orig_id for orig_id, _ in unique_results_to_process.items() if mappings_added_count > 0)
                        
                        if is_new: # Simplified check: assume if added_count > 0, this could be new
                           # Ensure association for new mapping if not already added above
                           is_already_associated = any(
                               assoc.input_identifier == mapping.source_id and 
                               assoc.output_identifier == mapping.target_id and 
                               assoc.log_id == path_log_id 
                               for assoc in log_mapping_associations
                           )
                           if not is_already_associated:
                              assoc = PathLogMappingAssociation(
                                  log_id=path_log_id,
                                  input_identifier=mapping.source_id,
                                  output_identifier=mapping.target_id
                              )
                              log_mapping_associations.append(assoc)


                if log_mapping_associations:
                     # Deduplicate associations before adding
                    unique_assocs = { (a.log_id, a.input_identifier, a.output_identifier): a for a in log_mapping_associations }.values()
                    if unique_assocs:
                        cache_session.add_all(list(unique_assocs))
                        await cache_session.flush() # Flush associations

            # --- Commit and log details (only if there were changes) --- #
            await cache_session.commit() # Commit the nested transaction

            # Calculate counts based on actual changes committed
            entity_mappings_processed = mappings_to_add_or_update # Represents mappings added or updated
            updated_count = len(entity_mappings_processed) - mappings_added_count
            associations_committed = len(unique_assocs) if 'unique_assocs' in locals() and unique_assocs else 0

            log_message = f"Cache update: Processed {len(entity_mappings_processed)} mappings "
            if mappings_added_count > 0:
                log_message += f"(added {mappings_added_count} new) "
            if updated_count > 0:
                log_message += f"(updated {updated_count} existing) "
            log_message += f"and committed {associations_committed} associations with log ID {path_log_id}."
            logger.info(log_message)
            # --- End of commit and log block --- #

        except IntegrityError as e:
            await cache_session.rollback()
            logger.error(f"IntegrityError during cache commit for log ID {path_log_id}: {e}", exc_info=True)
        except Exception as e:
            await cache_session.rollback()
            logger.error(f"Unexpected error during cache commit for log ID {path_log_id}: {e}", exc_info=True)

    async def _check_cache(
        self, cache_session: AsyncSession, source_ids: List[str], source_type: str, target_type: str,
        max_age_days: Optional[int] = None
    ) -> Dict[str, Optional[str]]:
        """
        Check the cache for existing mappings.

        :param cache_session: The cache database session
        :param source_ids: List of source IDs to check
        :param source_type: The source ontology type
        :param target_type: The target ontology type
        :param max_age_days: Optional maximum age in days for cached results
        :return: Dictionary mapping source IDs to target IDs (or None if not found/stale)
        """
        logger.debug(f"Checking cache for {len(source_ids)} source IDs: {source_type} -> {target_type}")
        result = {source_id: None for source_id in source_ids}
        if not source_ids: return result

        stmt = select(EntityMapping).where(
            EntityMapping.source_id.in_(source_ids),
            EntityMapping.source_type == source_type,
            EntityMapping.target_type == target_type
        )
        if max_age_days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            stmt = stmt.where(EntityMapping.last_updated >= cutoff_date)
            logger.debug(f"Applying cache max age filter: >= {cutoff_date}")

        query_result = await cache_session.execute(stmt)
        mappings = query_result.scalars().all()

        processed_mappings: Dict[str, Tuple[datetime, str]] = {}
        for mapping in mappings:
            if mapping.source_id not in processed_mappings or mapping.last_updated > processed_mappings[mapping.source_id][0]:
                 processed_mappings[mapping.source_id] = (mapping.last_updated, mapping.target_id)

        cache_hits = 0
        for source_id, (_, target_id) in processed_mappings.items():
            result[source_id] = target_id
            cache_hits += 1

        if cache_hits > 0:
            logger.info(f"Cache hit: Found {cache_hits}/{len(source_ids)} mappings in cache for {source_type} -> {target_type}")
        else:
            logger.debug(f"Cache miss: No valid mappings found in cache for {source_type} -> {target_type}")
        return result

    async def execute_mapping(
        self, source_endpoint_name: str, target_endpoint_name: str, input_identifiers: List[str] = None, 
        input_data: List[str] = None,
        source_property_name: str = "PrimaryIdentifier", target_property_name: str = "PrimaryIdentifier",
        use_cache: bool = True, max_cache_age_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a mapping process based on endpoint configurations. Works with input_identifiers or input_data parameter.

        :param source_endpoint_name: Source endpoint name
        :param target_endpoint_name: Target endpoint name
        :param input_identifiers: List of identifiers to map (deprecated, use input_data instead)  
        :param input_data: List of identifiers to map (preferred parameter)
        :param source_property_name: Property name for the source endpoint
        :param target_property_name: Property name for the target endpoint
        :param use_cache: Whether to check the cache before executing the mapping
        :param max_cache_age_days: Maximum age of cached results to use (None = no limit)
        :return: Dictionary with mapping results
        """
        # Handle the case where input_data is provided instead of input_identifiers
        if input_data is not None and input_identifiers is None:
            input_identifiers = input_data
        elif input_identifiers is None and input_data is None:
            input_identifiers = []

        try:
            # Session for metamapper DB (config)
            async with self.async_session() as meta_session:
                logger.info(f"Executing mapping: {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}")

                # Corrected calls to _get_ontology_type, passing property names
                source_ontology = await self._get_ontology_type(meta_session, source_endpoint_name, source_property_name)
                target_ontology = await self._get_ontology_type(meta_session, target_endpoint_name, target_property_name)

                if not source_ontology or not target_ontology:
                     error_message = "Configuration Error: Could not determine source/target ontology types for the specified properties."
                     logger.error(error_message)
                     # Return structured error immediately
                     return {
                         "error": PathExecutionStatus.FAILURE,
                         "details": {
                             "source_endpoint": source_endpoint_name,
                             "source_property": source_property_name,
                             "target_endpoint": target_endpoint_name,
                             "target_property": target_property_name
                         }
                     }

                logger.info(f"Mapping from {source_ontology} to {target_ontology}")

                # --- Get Endpoints and Validate Ontologies ---
                async with self.async_session() as config_session:
                    source_endpoint_res = await config_session.execute(
                        select(Endpoint).where(Endpoint.name == source_endpoint_name)
                    )
                    source_endpoint = source_endpoint_res.scalar_one_or_none()

                    target_endpoint_res = await config_session.execute(
                        select(Endpoint).where(Endpoint.name == target_endpoint_name)
                    )
                    target_endpoint = target_endpoint_res.scalar_one_or_none()

                    if not source_endpoint or not target_endpoint:
                        error_message = "Source or target endpoint not found."
                        logger.error(error_message)
                        # Need to return here as we cannot proceed
                        normalized_results = {id: None for id in input_identifiers}
                        return { 
                            "request_params": { 
                                "source_endpoint_name": source_endpoint_name, 
                                "target_endpoint_name": target_endpoint_name, 
                                "source_identifiers": input_identifiers, 
                                "source_ontology_type": source_ontology, 
                                "target_ontology_type": target_ontology, 
                            }, 
                            "status": PathExecutionStatus.FAILURE.value, 
                            "error": error_message, 
                            "selected_path_id": None, 
                            "selected_path_name": None, 
                            "results": normalized_results
                        }
                    
                # --- Find the best path --- 
                path = await self._find_best_path(meta_session, source_ontology, target_ontology)
                if not path:
                    error_message = f"No mapping path found from {source_ontology} to {target_ontology}"
                    logger.error(error_message)
                    return {
                        "status": PathExecutionStatus.NO_PATH_FOUND.value,
                        "error": error_message,
                        "results": {id: None for id in input_identifiers}
                    }

                source_node = None
                target_node = None
                for step in path.steps:
                    if step.step_order == 1:
                        source_node = step.mapping_resource
                    if step.step_order == max(s.step_order for s in path.steps):
                        target_node = step.mapping_resource

                if not source_node or not target_node:
                    error_message = f"Path {path.id} has invalid configuration - missing source or target node"
                    logger.error(error_message)
                    return {
                        "status": PathExecutionStatus.FAILURE.value,
                        "error": error_message,
                        "results": {id: None for id in input_identifiers}
                    }

                # Initialize final result dictionary and path_log
                final_results: Dict[str, Optional[str]] = {}
                path_log = None

                try:
                    async with self.get_cache_session() as cache_session:
                        try:
                            # 1. Check cache
                            cached_results = await self._check_cache(
                                cache_session,
                                input_identifiers,
                                source_ontology,
                                target_ontology,
                                max_age_days=path.cache_duration_days if hasattr(path, 'cache_duration_days') else max_cache_age_days
                            )

                            # 2. Initialize final_results with valid cached hits
                            # Use .get() for safety, default to None if key not found (shouldn't happen with init)
                            final_results = {k: v for k, v in cached_results.items() if v is not None}
                            uncached_identifiers = [id for id in input_identifiers if cached_results.get(id) is None]

                            # 3. Execute path for uncached identifiers
                            if not uncached_identifiers:
                                logger.info("All identifiers found in cache.")
                                # Create log entry even if only cache was used
                                path_log = await self._create_mapping_log(
                                    cache_session, 
                                    path.id, 
                                    PathExecutionStatus.COMPLETED_FROM_CACHE,
                                    representative_source_id=input_identifiers[0] if input_identifiers else "unknown", # Add example source ID
                                    source_entity_type=source_ontology # Pass the source ontology type
                                )
                                await cache_session.commit()
                            else:
                                path_log = await self._create_mapping_log(
                                    cache_session, 
                                    path.id, 
                                    PathExecutionStatus.PENDING,
                                    representative_source_id=uncached_identifiers[0] if uncached_identifiers else "unknown", # Add example source ID
                                    source_entity_type=source_ontology # Pass the source ontology type
                                )
                                logger.info(f"Executing path ID {path.id} for {len(uncached_identifiers)} uncached identifiers. Log ID: {path_log.id}")

                                # Initialize current results with input identifiers and execute path
                                current_results: Dict[str, Optional[List[str]]] = {orig_id: [orig_id] for orig_id in uncached_identifiers}
                                path_status = PathExecutionStatus.PENDING
                                
                                for step in sorted(path.steps, key=lambda s: s.step_order):
                                    step_input_set: Set[str] = set()
                                    for original_id, id_list in current_results.items():
                                        if id_list:
                                            step_input_set.update(id_list)
                                    
                                    step_input_values = sorted(list(step_input_set))
                                    if not step_input_values:
                                        logger.warning(f"Skipping step {step.step_order} due to no input values.")
                                        continue
                                    
                                    logger.info(f"Executing Step {step.step_order}: Resource '{step.mapping_resource.name}'")
                                    try:
                                        client_instance = await self._load_client(step.mapping_resource)
                                        step_results = await client_instance.map_identifiers(step_input_values)
                                        
                                        # Process step results and update current_results for next step
                                        next_current_results = {}
                                        for original_id, current_id_list in current_results.items():
                                            if current_id_list is None:
                                                next_current_results[original_id] = None
                                                continue
                                            
                                            aggregated_outputs_for_orig_id = set()
                                            found_mapping = False
                                            for current_id in current_id_list:
                                                output_for_current_id = step_results.get(current_id)
                                                if output_for_current_id:
                                                    aggregated_outputs_for_orig_id.update(output_for_current_id)
                                                    found_mapping = True
                                                elif output_for_current_id is None:
                                                    found_mapping = True
                                            
                                            if found_mapping:
                                                next_current_results[original_id] = sorted(list(aggregated_outputs_for_orig_id)) if aggregated_outputs_for_orig_id else None
                                            else:
                                                next_current_results[original_id] = None
                                        
                                        current_results = next_current_results
                                    except Exception as e:
                                        logger.error(f"Error during step {step.step_order}: {e}", exc_info=True)
                                        path_status = PathExecutionStatus.FAILURE
                                        # Update path log with error
                                        path_log.status = path_status
                                        path_log.end_time = datetime.now(timezone.utc)
                                        path_log.error_message = str(e)
                                        break
                                
                                # 4. Update final_results with newly mapped results
                                mapped_results = {}
                                for orig_id, id_list in current_results.items():
                                    if id_list and len(id_list) > 0:
                                        # Just take the first result for simplicity
                                        mapped_results[orig_id] = id_list[0]
                                    else:
                                        mapped_results[orig_id] = None
                                
                                # Update final_results with newly mapped results
                                final_results.update(mapped_results)
                                logger.info(f"Mapping step finished. Total results: {len(final_results)}. Status: {path_status}")

                                # Update path log
                                if path_status != PathExecutionStatus.FAILURE:
                                    # Check if all source IDs were successfully mapped
                                    if all(mapped_results.get(id) is not None for id in uncached_identifiers):
                                        path_status = PathExecutionStatus.SUCCESS
                                    elif any(mapped_results.get(id) is not None for id in uncached_identifiers):
                                        path_status = PathExecutionStatus.PARTIAL_SUCCESS
                                    else:
                                        path_status = PathExecutionStatus.NO_MAPPING_FOUND
                                
                                path_log.status = path_status
                                path_log.end_time = datetime.now(timezone.utc)

                                # 5. Cache the newly mapped results
                                if mapped_results:  # Only cache if there are new results
                                    await self._cache_results(
                                        cache_session,
                                        path_log.id,
                                        source_ontology,
                                        target_ontology,
                                        results=mapped_results  # Cache only the *newly* mapped results
                                    )
                                await cache_session.commit()  # Commit log update and new cache entries

                        except Exception as e:
                            logger.error(f"Error during mapping execution for path {path.id}: {e}", exc_info=True)
                            if path_log:
                                path_log.status = PathExecutionStatus.FAILED
                                path_log.end_time = datetime.now(timezone.utc)
                            await cache_session.rollback()
                            # Keep potentially partial final_results from cache

                except Exception as e:
                    logger.error(f"Outer execution error in execute_mapping (e.g., DB connection): {e}", exc_info=True)
                    # Ensure final_results is initialized if outer error occurs early
                    if not final_results:
                         final_results = {}

        except Exception as e:
            logger.error(f"Global error in execute_mapping: {e}", exc_info=True)
            return {
                "status": PathExecutionStatus.FAILURE.value,
                "error": str(e),
                "results": {id: None for id in input_identifiers}
            }

        # Return the aggregated results
        return final_results if final_results else {}
                
    async def _create_mapping_log(
        self,
        session: AsyncSession,
        path_id: int,
        execution_status: PathExecutionStatus,
        error_message: Optional[str] = None,
        representative_source_id: str = "unknown",
        source_entity_type: str = None,
    ) -> MappingPathExecutionLog:
        """Create a mapping execution log entry.
        
        Args:
            session: Database session
            path_id: ID of the mapping path
            execution_status: Status of the execution
            error_message: Error message if any
            representative_source_id: Example source ID for this mapping
            source_entity_type: Type of the source entity
            
        Returns:
            Created mapping log entry
        """
        now = datetime.now(timezone.utc)
        mapping_log = MappingPathExecutionLog(
            relationship_mapping_path_id=path_id,
            status=execution_status,
            error_message=error_message,
            start_time=now,
            source_entity_id=representative_source_id,
            source_entity_type=source_entity_type,
        )
        session.add(mapping_log)
        await session.flush()
        return mapping_log
        
    async def _update_execution_metadata(
        self,
        session: AsyncSession,
        mapping_log: MappingPathExecutionLog,
        input_identifiers: List[str],
        results: Optional[Dict[str, Optional[str]]] = None,
    ) -> None:
        """Update execution metadata with input/output mapping associations.
        
        Args:
            session: Database session
            mapping_log: Mapping execution log entry
            input_identifiers: List of input identifiers
            results: Mapping results dictionary
        """
        if not results:
            return
            
        # Create mapping associations
        associations = []
        for input_id, output_id in results.items():
            association = PathLogMappingAssociation(
                log_id=mapping_log.id,
                input_identifier=input_id,
                output_identifier=output_id,
            )
            associations.append(association)
            
        if associations:
            session.add_all(associations)
            await session.flush()

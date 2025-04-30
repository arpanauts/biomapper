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
    Base as CacheBase, 
    EntityMapping, 
    EntityMappingProvenance, 
    PathExecutionLog, 
    PathExecutionStatus
)

# Define PathLogMappingAssociation which is missing from cache_models.py
from sqlalchemy import Column, Integer, ForeignKey
class PathLogMappingAssociation(CacheBase):
    """Association table to track which entity mappings were created or updated by which execution log."""
    __tablename__ = "path_log_mapping_associations"
    
    id = Column(Integer, primary_key=True)
    path_execution_log_id = Column(Integer, ForeignKey("path_execution_logs.id", ondelete="CASCADE"), nullable=False)
    entity_mapping_id = Column(Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), nullable=False)
    
    def __repr__(self):
        return f"<PathLogMappingAssociation log_id={self.path_execution_log_id} mapping_id={self.entity_mapping_id}>"

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

    async def _get_ontology_type(
        self, meta_session: AsyncSession, endpoint_name: str
    ) -> Optional[str]:
        """Get the primary ontology type for a given endpoint name using OntologyPreference."""
        try:
            # 1. Find the endpoint ID
            endpoint_stmt = select(Endpoint.id).where(Endpoint.name == endpoint_name)
            endpoint_result = await meta_session.execute(endpoint_stmt)
            endpoint_id = endpoint_result.scalar_one_or_none()

            if not endpoint_id:
                logger.warning(f"Endpoint '{endpoint_name}' not found.")
                return None

            # 2. Find the highest priority OntologyPreference for this endpoint
            pref_stmt = (
                select(OntologyPreference.ontology_name)
                .where(OntologyPreference.endpoint_id == endpoint_id)
                .order_by(OntologyPreference.priority.asc()) # Lower number = higher priority
                .limit(1)
            )
            pref_result = await meta_session.execute(pref_stmt)
            ontology_type = pref_result.scalar_one_or_none()

            if ontology_type:
                logger.debug(f"Found ontology type '{ontology_type}' via preference for endpoint '{endpoint_name}' (ID: {endpoint_id})")
                return ontology_type
            else:
                logger.warning(f"No OntologyPreference found for endpoint '{endpoint_name}' (ID: {endpoint_id}).")
                # Fallback: Could potentially check PropertyExtractionConfig, but let's keep it simple for now.
                return None

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching ontology preference for {endpoint_name}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ontology preference for {endpoint_name}: {e}", exc_info=True)
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
        # Pass the parsed config to client init if needed, or handle in map_identifiers
        # config_for_init = json.loads(resource.config_template or '{}')
        client_instance = client_class() # Assuming config primarily for map_identifiers
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
        path_log = await cache_session.get(PathExecutionLog, path_log_id)
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
                    assoc = PathLogMappingAssociation(path_execution_log_id=path_log_id, entity_mapping_id=existing_mapping.id)
                    log_mapping_associations.append(assoc)
                else:
                    # Mapping hasn't changed, but associate with this run if not already done
                    assoc_stmt = select(PathLogMappingAssociation).where(
                        PathLogMappingAssociation.path_execution_log_id == path_log_id,
                        PathLogMappingAssociation.entity_mapping_id == existing_mapping.id
                    )
                    existing_assoc_result = await cache_session.execute(assoc_stmt)
                    if not existing_assoc_result.scalars().first():
                         assoc = PathLogMappingAssociation(path_execution_log_id=path_log_id, entity_mapping_id=existing_mapping.id)
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
                           is_already_associated = any(assoc.entity_mapping_id == mapping.id and assoc.path_execution_log_id == path_log_id for assoc in log_mapping_associations)
                           if not is_already_associated:
                              assoc = PathLogMappingAssociation(path_execution_log_id=path_log_id, entity_mapping_id=mapping.id)
                              log_mapping_associations.append(assoc)


                if log_mapping_associations:
                     # Deduplicate associations before adding
                    unique_assocs = { (a.path_execution_log_id, a.entity_mapping_id): a for a in log_mapping_associations }.values()
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

        # Initialize result with all IDs set to None (not found)
        result = {source_id: None for source_id in source_ids}

        # If no source IDs to check, return immediately
        if not source_ids:
            return result

        # Construct query based on criteria
        stmt = select(EntityMapping).where(
            EntityMapping.source_id.in_(source_ids),
            EntityMapping.source_type == source_type,
            EntityMapping.target_type == target_type
        )

        # Add time filter if max_age_days specified
        if max_age_days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            stmt = stmt.where(EntityMapping.last_updated >= cutoff_date)
            logger.debug(f"Applying cache max age filter: >= {cutoff_date}")

        # Execute query
        query_result = await cache_session.execute(stmt)
        mappings = query_result.scalars().all()

        # Process results - use the most recent mapping if duplicates exist for a source_id
        # (although ideally duplicates shouldn't happen for the same source/target type combo)
        processed_mappings: Dict[str, Tuple[datetime, str]] = {}
        for mapping in mappings:
            if mapping.source_id not in processed_mappings or mapping.last_updated > processed_mappings[mapping.source_id][0]:
                 processed_mappings[mapping.source_id] = (mapping.last_updated, mapping.target_id)

        cache_hits = 0
        for source_id, (created_at, target_id) in processed_mappings.items():
            result[source_id] = target_id
            cache_hits += 1
            logger.debug(f"Cache hit: Found mapping for {source_id} ({source_type} -> {target_type}) -> {target_id}")

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
        results: Optional[Dict[str, Any]] = None
        log_entry: Optional[PathExecutionLog] = None # To store the log entry
        cached_results: Dict[str, Optional[str]] = {}
        identifiers_to_map: List[str] = input_identifiers # Default if cache not used
        final_results: Dict[str, Optional[List[str]]] = {} # To combine cache and new results (Values should be lists)
        start_time = datetime.now(timezone.utc) # Define start time here

        final_status = PathExecutionStatus.FAILURE
        path_log = None
        error_message = None # Initialize error message
        selected_path = None # Initialize selected_path

        try:
            # Session for metamapper DB (config)
            async with self.async_session() as meta_session:
                logger.info(f"Executing mapping: {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}")

                # Corrected calls to _get_ontology_type
                source_ontology = await self._get_ontology_type(meta_session, source_endpoint_name)
                target_ontology = await self._get_ontology_type(meta_session, target_endpoint_name)

                if not source_ontology or not target_ontology:
                     final_status = "Configuration Error: Could not determine source/target ontology types"
                     # Return structured error immediately
                     return {
                         "error": final_status,
                         "details": {
                             "source_endpoint": source_endpoint_name,
                             "source_property": source_property_name,
                             "target_endpoint": target_endpoint_name,
                             "target_property": target_property_name
                         }
                     }

                logger.info(f"Mapping from {source_ontology} to {target_ontology}")

                # Session for mapping_cache DB (results/provenance)
                async with self.async_cache_session() as cache_session:

                    # --- Get Endpoints and Validate Ontologies --- (Moved ID fetching here)
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
                            final_status = PathExecutionStatus.FAILURE
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
                                "status": final_status.value, 
                                "error": error_message, 
                                "selected_path_id": None, 
                                "selected_path_name": None, 
                                "results": normalized_results
                            }
                        
                        # Store IDs for later use
                        source_endpoint_id = source_endpoint.id
                        target_endpoint_id = target_endpoint.id

                        # Validate input/output types against endpoints (Optional but good practice)
                        # ... (validation logic can be added here)

                    # --- Cache Check --- 
                    if use_cache and self.async_cache_session: # Ensure factory exists
                        try:
                            # Create session if needed (might be created earlier if cache check happened)
                            if not cache_session:
                                cache_session = self.async_cache_session()

                            # Perform cache check (read-only, no transaction needed here)
                            cached_results = await self._check_cache(
                                cache_session=cache_session, # Correct keyword argument
                                source_ids=list(input_identifiers),
                                source_type=source_ontology,
                                target_type=target_ontology,
                                max_age_days=max_cache_age_days
                            )
                            logger.debug(f"Cache check returned: {cached_results}") # DEBUG
                            logger.debug(f"Cache check for {len(input_identifiers)} identifiers returned {len(cached_results)} results.")
                            # Determine which identifiers still need mapping
                            identifiers_to_map = [
                                id for id in input_identifiers if cached_results.get(id) is None
                            ]
                            logger.debug(f"Identifiers needing mapping after cache check: {identifiers_to_map}") # DEBUG
                            logger.debug(f"Cached identifiers ({len(cached_results)}): {list(cached_results.keys())}")
                            logger.debug(f"Uncached identifiers ({len(identifiers_to_map)}): {list(identifiers_to_map)}")

                            if not identifiers_to_map:
                                logger.info("All identifiers found in cache.")
                        except Exception as e:
                            logger.error(f"Error during cache check: {e}", exc_info=True)
                            # No rollback needed for read-only check failure
                            identifiers_to_map = list(input_identifiers)
                            logger.warning("Proceeding without cache results due to error during check.")
                    else:
                        # Not using cache or no factory configured
                        identifiers_to_map = list(input_identifiers)
                        logger.debug(f"Cache not used. Processing all {len(identifiers_to_map)} identifiers.")

                    # --- Step 2: Find Path --- 
                    # Session for metamapper DB (config)
                    async with self.async_session() as meta_session:
                        logger.debug(f"Finding path for {len(identifiers_to_map)} uncached identifiers from {source_ontology} to {target_ontology}")
                        selected_path = await self._find_best_path(meta_session, source_ontology, target_ontology)

                        # --- Step 3: Execute Path (if necessary and path exists) ---
                        final_status = PathExecutionStatus.PENDING # Default status
                        error_message = None # Default error message
                        final_results: Dict[str, Optional[List[str]]] = {} # Initialize empty
                        if 'cached_results' in locals() and cached_results: # Pre-populate if cache was used
                            for source_id, cached_target_id in cached_results.items():
                                if cached_target_id is not None:
                                    final_results[source_id] = [cached_target_id] # Wrap cached string in a list
                                else:
                                    final_results[source_id] = None # Keep None as None
                        loop_error_details = None # Initialize error details
 
                        async with self.async_cache_session() as cache_session: # Re-enter cache session for logging/updates
                            try:
                                path_log = None # Initialize path_log here for the scope
                                # loop_error_details already initialized outside this try

                                # --- Create Initial PathExecutionLog ---
                                if selected_path and identifiers_to_map:
                                    start_time = datetime.now(timezone.utc)
                                    representative_source_id = identifiers_to_map[0]
                                    path_log = PathExecutionLog(
                                        relationship_mapping_path_id=selected_path.id,
                                        source_entity_id=representative_source_id,
                                        source_entity_type=source_ontology,
                                        start_time=start_time,
                                        status=PathExecutionStatus.PENDING,
                                    )
                                    cache_session.add(path_log)
                                    await cache_session.flush() # Get ID
                                    logger.info(f"Executing path ID {selected_path.id} for {len(identifiers_to_map)} uncached identifiers. Log ID: {path_log.id}")
                                else:
                                     start_time = datetime.now(timezone.utc) # Still need a start time for duration if no path execution

                                # --- Execute Steps --- 
                                if selected_path and identifiers_to_map:
                                    current_results: Dict[str, Optional[List[str]]] = { orig_id: [orig_id] for orig_id in identifiers_to_map }
                                    final_step_results: Dict[str, Optional[List[str]]] = {}

                                    for step in sorted(selected_path.steps, key=lambda s: s.step_order):
                                        step_input_set: Set[str] = set()
                                        for id_list in current_results.values():
                                            if id_list: step_input_set.update(id_list)
                                        step_input_values: List[str] = sorted(list(step_input_set))
                                        
                                        if not step_input_values:
                                            logger.warning(f"Skipping step {step.step_order} due to no input values.")
                                            continue

                                        logger.info(f"Executing Step {step.step_order}: Resource '{step.mapping_resource.name}'")
                                        step_error_message = None
                                        try:
                                            client_instance = await self._load_client(step.mapping_resource)
                                            step_results = await client_instance.map_identifiers(identifiers=step_input_values)
                                            logger.debug(f"Step {step.step_order} raw results: {step_results}")
                                        except Exception as client_exec_err:
                                            step_error_message = f"Client Error ({step.mapping_resource.name}, Step {step.step_order}): {type(client_exec_err).__name__}: {client_exec_err}"
                                            logger.error(f"Error during step {step.step_order}: {step_error_message}", exc_info=True)
                                            step_results = {input_val: None for input_val in step_input_values}

                                        if step_error_message:
                                            loop_error_details = {"step": step.step_order, "error": step_error_message}
                                            final_status = PathExecutionStatus.FAILURE
                                            # Attempt to update log immediately
                                            if path_log:
                                                try:
                                                    async with self.async_cache_session() as error_log_session:
                                                        path_log.end_time = datetime.now(timezone.utc)
                                                        path_log.duration_ms = int((path_log.end_time - start_time).total_seconds() * 1000)
                                                        path_log.status = final_status
                                                        path_log.error_message = json.dumps(loop_error_details)
                                                        await error_log_session.merge(path_log)
                                                        await error_log_session.commit() # Commit error log state
                                                except Exception as log_upd_err:
                                                    logger.error(f"Failed to update PathExecutionLog on step error: {log_upd_err}", exc_info=True)
                                            break # Stop path execution

                                        # Process step results and update current_results for next step
                                        next_current_results: Dict[str, Optional[List[str]]] = {}
                                        for original_id, current_id_list in current_results.items():
                                            if current_id_list is None: next_current_results[original_id] = None; continue
                                            aggregated_outputs_for_orig_id: Set[str] = set()
                                            found_mapping = False
                                            for current_id in current_id_list:
                                                output_for_current_id = step_results.get(current_id)
                                                if output_for_current_id: aggregated_outputs_for_orig_id.update(output_for_current_id); found_mapping = True
                                                elif output_for_current_id is None: found_mapping = True
                                            if found_mapping: next_current_results[original_id] = sorted(list(aggregated_outputs_for_orig_id)) if aggregated_outputs_for_orig_id else None
                                            else: next_current_results[original_id] = None
                                        current_results = next_current_results
                                        logger.debug(f"State after Step {step.step_order}: {current_results}")

                                        # Store final step results
                                        if step.step_order == max(s.step_order for s in selected_path.steps):
                                            final_step_results = current_results
                                            logger.info(f"Final step ({step.step_order}) completed.")

                                # --- Combine results (cached + executed path results) ---
                                if 'final_step_results' in locals() and final_step_results:
                                    final_results.update(final_step_results)

                                # --- Determine Final Status (if no loop error occurred) ---
                                if not loop_error_details:
                                    original_input_ids_set = set(input_identifiers)
                                    successfully_mapped_ids = {k for k, v in final_results.items() if v is not None and k in original_input_ids_set}

                                    if successfully_mapped_ids == original_input_ids_set:
                                        final_status = PathExecutionStatus.SUCCESS
                                    elif successfully_mapped_ids:
                                        final_status = PathExecutionStatus.PARTIAL_SUCCESS
                                    elif not identifiers_to_map and cached_results: # All cached, successful implicitly
                                         final_status = PathExecutionStatus.SUCCESS
                                    elif selected_path and not successfully_mapped_ids: # Path executed but no results
                                         final_status = PathExecutionStatus.NO_MAPPING_FOUND
                                    elif not selected_path and identifiers_to_map: # No path found for items needing mapping
                                        final_status = PathExecutionStatus.NO_PATH_FOUND
                                        error_message = f"No valid mapping path found from {source_ontology} to {target_ontology}."
                                    elif not selected_path and not identifiers_to_map: # All cached, no path needed
                                         final_status = PathExecutionStatus.SUCCESS
                                    else: # Fallback/unexpected case
                                        final_status = PathExecutionStatus.FAILURE 
                                        error_message = error_message or "Unknown state determining final status."
                                    logger.info(f"Final status determined as: {final_status.name}")

                                # --- Finalize PathExecutionLog (if execution was attempted) ---
                                if path_log:
                                    path_log.end_time = datetime.now(timezone.utc)
                                    path_log.duration_ms = int((path_log.end_time - start_time).total_seconds() * 1000)
                                    path_log.status = final_status
                                    if loop_error_details and not path_log.error_message: # Log loop error if not already set
                                        path_log.error_message = json.dumps(loop_error_details)
                                    await cache_session.merge(path_log)
                                    # Commit log changes only if no outer exception occurs
                                    # Commit happens outside the loop error handling block for success/partial/no_mapping cases
                                    if final_status != PathExecutionStatus.FAILURE: 
                                        await cache_session.commit() 

                                # --- Cache Results --- 
                                if final_results and final_status != PathExecutionStatus.FAILURE:
                                    await self._cache_results(
                                        cache_session=cache_session,
                                        path_log_id=path_log.id if path_log else None,
                                        source_ontology=source_ontology,
                                        target_ontology=target_ontology,
                                        results=final_results
                                    )

                            except ClientError as ce:
                                logger.error(f"ClientError within cache session: {ce}", exc_info=True)
                                await cache_session.rollback()
                                final_status = PathExecutionStatus.FAILURE
                                error_message = f"Client Error ({getattr(ce, 'client_name', 'UnknownClient')}): {ce}"
                                if not final_results: final_results = {id: None for id in input_identifiers}
                            except Exception as e:
                                logger.error(f"Unexpected error within cache session: {type(e).__name__}: {e}", exc_info=True)
                                await cache_session.rollback()
                                final_status = PathExecutionStatus.FAILURE
                                error_message = f"Executor Error: {type(e).__name__}: {e}"
                                if not final_results: final_results = {id: None for id in input_identifiers}
                                
                         # End of 'async with cache_session'
 
                    # --- Final Return Statement (inside meta_session, after cache_session block) --- #
                    path_id = selected_path.id if selected_path else None
                    
                    # MERGE RESULTS: Combine cached and new results correctly into the final format
                    final_results_structured: Dict[str, Optional[List[str]]] = {}
                    
                    # 1. Add cached results (wrapping strings in lists)
                    if 'cached_results' in locals() and cached_results:
                        for src_id, cached_tgt_id in cached_results.items():
                            if cached_tgt_id is not None:
                                final_results_structured[src_id] = [cached_tgt_id] # Wrap string in list
                            else:
                                final_results_structured[src_id] = None # Keep None

                    # 2. Add/Update with results from the path execution
                    if 'final_results' in locals() and final_results: 
                        final_results_structured.update(final_results)

                    return {
                        "request_params": {
                            "source_endpoint_name": source_endpoint_name,
                            "target_endpoint_name": target_endpoint_name,
                            "source_identifiers": input_identifiers,
                            "source_ontology_type": source_ontology,
                            "target_ontology_type": target_ontology,
                        },
                        "status": final_status.value, # Use the final status determined within the blocks
                        "error": error_message,
                        "selected_path_id": path_id,
                        "selected_path_name": selected_path.name if selected_path else None,
                        "results": final_results_structured # Return the correctly merged and formatted results
                    }
                # End of 'async with meta_session'
        except NoPathFoundError as npfe:
            logger.warning(f"NoPathFoundError encountered: {npfe}")
            final_status = PathExecutionStatus.NO_PATH_FOUND
            error_message = str(npfe)
            # Ensure final_results is initialized for return structure
            if 'final_results' not in locals() or final_results is None:
                final_results = {id: None for id in input_identifiers} if 'input_identifiers' in locals() else {}
            
            # Normalize results for consistent return format
            normalized_results = {}
            for source_id, target_value in final_results.items():
                if target_value is None:
                    normalized_results[source_id] = None
                elif isinstance(target_value, list) and len(target_value) > 0:
                    normalized_results[source_id] = target_value[0]  # Take the first result
                else:
                    normalized_results[source_id] = target_value
                    
            return { # Return error structure
                "request_params": {
                    "source_endpoint_name": source_endpoint_name if 'source_endpoint_name' in locals() else 'Unknown',
                    "target_endpoint_name": target_endpoint_name if 'target_endpoint_name' in locals() else 'Unknown',
                    "source_identifiers": input_identifiers if 'input_identifiers' in locals() else [],
                    "source_ontology_type": source_ontology if 'source_ontology' in locals() else 'Unknown',
                    "target_ontology_type": target_ontology if 'target_ontology' in locals() else 'Unknown',
                },
                "status": final_status.value,
                "error": error_message,
                "selected_path_id": None,
                "selected_path_name": None,
                "results": normalized_results
            }
        except Exception as outer_exc:
            logger.error(f"Outer exception during mapping execution: {type(outer_exc).__name__}: {outer_exc}", exc_info=True)
            final_status = PathExecutionStatus.FAILURE
            error_message = f"System Error: {type(outer_exc).__name__}: {outer_exc}"
            # Ensure final_results is initialized for return structure
            if 'final_results' not in locals() or final_results is None:
                final_results = {id: None for id in input_identifiers} if 'input_identifiers' in locals() else {}
                
            # Normalize results for consistent return format
            normalized_results = {}
            for source_id, target_value in final_results.items():
                if target_value is None:
                    normalized_results[source_id] = None
                elif isinstance(target_value, list) and len(target_value) > 0:
                    normalized_results[source_id] = target_value[0]  # Take the first result
                else:
                    normalized_results[source_id] = target_value
                    
            return { # Return error structure
                "request_params": {
                    "source_endpoint_name": source_endpoint_name if 'source_endpoint_name' in locals() else 'Unknown',
                    "target_endpoint_name": target_endpoint_name if 'target_endpoint_name' in locals() else 'Unknown',
                    "source_identifiers": input_identifiers if 'input_identifiers' in locals() else [],
                    "source_ontology_type": source_ontology if 'source_ontology' in locals() else 'Unknown',
                    "target_ontology_type": target_ontology if 'target_ontology' in locals() else 'Unknown',
                },
                "status": final_status.value,
                "error": error_message,
                "selected_path_id": selected_path.id if 'selected_path' in locals() and selected_path else None, # Path might be known even on outer error
                "selected_path_name": selected_path.name if 'selected_path' in locals() and selected_path else None,
                "results": normalized_results
            }

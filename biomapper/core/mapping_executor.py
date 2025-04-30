import asyncio
import importlib
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Type
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DBAPIError
from biomapper.core.exceptions import (
    BiomapperError,
    NoPathFoundError,
    ClientError,
    ConfigurationError,
    CacheError,
    MappingExecutionError,
    ClientExecutionError,
    ClientInitializationError,
    CacheTransactionError,
    CacheRetrievalError,
)

# Import models for metamapper DB
from ..db.models import (
    Endpoint,
    EndpointPropertyConfig,
    PropertyExtractionConfig,
    MappingPath,
    MappingPathStep,
    MappingResource,
    OntologyPreference,
)

# Import models for cache DB
from ..db.cache_models import (
    Base as CacheBase,  # Import the Base for cache tables
    EntityMapping,
    EntityMappingProvenance,
    PathExecutionLog as MappingPathExecutionLog,
    PathExecutionStatus,
    PathLogMappingAssociation,
)

# Assume config holds the DB URLs
from ..utils.config import CONFIG_DB_URL, CACHE_DB_URL

logger = logging.getLogger(__name__)


class ReversiblePath:
    """Wrapper to allow executing a path in reverse direction."""
    
    def __init__(self, original_path, is_reverse=False):
        self.original_path = original_path
        self.is_reverse = is_reverse
        
    @property
    def id(self):
        return self.original_path.id
        
    @property
    def name(self):
        return f"{self.original_path.name} (Reverse)" if self.is_reverse else self.original_path.name
    
    @property
    def priority(self):
        # Reverse paths have slightly lower priority
        return self.original_path.priority + (5 if self.is_reverse else 0)
    
    @property
    def steps(self):
        if not self.is_reverse:
            return self.original_path.steps
        else:
            # Return steps in reverse order
            return sorted(self.original_path.steps, key=lambda s: -s.step_order)
    
    def __getattr__(self, name):
        # Delegate other attributes to the original path
        return getattr(self.original_path, name)


class MappingExecutor:
    """Executes mapping tasks based on configurations in metamapper.db."""

    def __init__(
        self,
        metamapper_db_url: str = CONFIG_DB_URL,
        mapping_cache_db_url: str = CACHE_DB_URL,
    ):
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
            except RuntimeError:  # No running event loop
                asyncio.run(init_cache_db())
        except Exception as e:
            logger.error(f"Failed to initialize cache database schema: {e}")
            raise

        logger.info(
            f"MappingExecutor initialized with DB: {metamapper_db_url}, CacheDB: {mapping_cache_db_url}"
        )

    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()

    async def _get_path_details(
        self, meta_session: AsyncSession, path_id: int
    ) -> Dict[str, Any]:
        """
        Retrieve details about a mapping path for use in confidence scoring and metadata.

        Args:
            meta_session: SQLAlchemy session for the metamapper database
            path_id: ID of the MappingPath to analyze

        Returns:
            Dict containing path details including:
                - hop_count: Number of steps in the path
                - resource_types: List of resource types used
                - client_identifiers: List of client identifiers used
        """
        # Query to get the path with its steps and resources
        stmt = (
            select(MappingPath)
            .options(
                selectinload(MappingPath.steps).joinedload(
                    MappingPathStep.mapping_resource
                )
            )
            .where(MappingPath.id == path_id)
        )

        result = await meta_session.execute(stmt)
        path = result.scalar_one_or_none()

        if not path:
            logger.warning(f"Path ID {path_id} not found in database")
            return {"hop_count": 1, "resource_types": [], "client_identifiers": []}

        # Count the steps as hop count
        steps = sorted(path.steps, key=lambda s: s.step_order)
        hop_count = len(steps)

        # Extract info about resources used
        resource_types = []
        client_identifiers = []

        for step in steps:
            if step.mapping_resource:
                resource_type = getattr(step.mapping_resource, "resource_type", None)
                if resource_type:
                    resource_types.append(resource_type)

                client_id = getattr(step.mapping_resource, "name", None)
                if client_id:
                    client_identifiers.append(client_id)

        return {
            "hop_count": hop_count,
            "resource_types": resource_types,
            "client_identifiers": client_identifiers,
            "path_name": path.name if path else None,
            "path_description": path.description if path else None,
        }

    def _calculate_confidence_score(
        self,
        path_log: MappingPathExecutionLog,
        processed_target_ids: List[str],
        path_details: Dict[str, Any] = None,
        is_reverse: bool = False,
    ) -> float:
        """
        Calculate a confidence score for a mapping based on various factors.

        Args:
            path_log: The path execution log containing metadata about the mapping path
            processed_target_ids: List of target IDs from the mapping result
            path_details: Dictionary of path details from _get_path_details
            is_reverse: Whether this mapping used a reverse path

        Returns:
            float: A confidence score between 0.0 and 1.0
        """
        # Base score starts at 0.7
        base_score = 0.7

        # Factor 1: Number of results - prefer single, definitive mappings
        if len(processed_target_ids) == 1:
            result_score = 0.2  # Bonus for single mapping
        elif len(processed_target_ids) == 0:
            result_score = (
                -0.5
            )  # Large penalty for no results (though this should rarely happen)
        else:
            # Multiple results reduce confidence inversely with count (bounded)
            result_score = max(-0.2, -0.05 * len(processed_target_ids))

        # Factor 2: Path length (hop count) - shorter paths are preferred
        hop_count = path_details.get("hop_count", 1) if path_details else 1

        # Simple logic: penalty for longer paths
        if hop_count <= 1:
            path_score = 0.1  # Direct mapping bonus
        elif hop_count == 2:
            path_score = 0.05  # Small bonus for 2-hop
        else:
            # Increasing penalty for longer paths
            path_score = -0.05 * (hop_count - 2)

        # Factor 3: Resource type - some resources are more trustworthy
        resource_score = 0

        if (
            path_details
            and "resource_types" in path_details
            and path_details["resource_types"]
        ):
            # Look at the primary resource (first in the chain)
            primary_resource = (
                path_details["resource_types"][0].lower()
                if path_details["resource_types"]
                else None
            )

            if primary_resource:
                if primary_resource in ["api", "official_api"]:
                    resource_score = 0.1  # Official APIs are more trustworthy
                elif primary_resource in ["database", "curated_database"]:
                    resource_score = 0.08  # Curated databases are trusted
                elif primary_resource in ["file", "local_file"]:
                    resource_score = (
                        0.05  # Local files are usually trusted but may be outdated
                    )
                elif primary_resource in ["llm", "ai"]:
                    resource_score = -0.1  # LLM-based mappings are less trusted

        # Factor 4: Direction - reverse mappings are slightly less preferred
        direction_score = -0.05 if is_reverse else 0.0
                
        # Combine scores with bounds
        final_score = min(
            1.0, max(0.1, base_score + result_score + path_score + resource_score + direction_score)
        )

        return final_score

    async def _get_ontology_type(
        self,
        meta_session: AsyncSession,
        endpoint_name: str,
        property_name: str = "PrimaryIdentifier",
    ) -> Optional[str]:
        """Get the ontology type for a specific property of a given endpoint name."""
        try:
            # Join Endpoint -> EndpointPropertyConfig -> PropertyExtractionConfig
            stmt = (
                select(PropertyExtractionConfig.ontology_type)
                .join(
                    EndpointPropertyConfig,
                    EndpointPropertyConfig.property_extraction_config_id
                    == PropertyExtractionConfig.id,
                )
                .join(Endpoint, Endpoint.id == EndpointPropertyConfig.endpoint_id)
                .where(Endpoint.name == endpoint_name)
                .where(EndpointPropertyConfig.property_name == property_name)
                .limit(1)  # Should only be one config per endpoint/property pair
            )
            result = await meta_session.execute(stmt)
            ontology_type = result.scalar_one_or_none()

            if ontology_type:
                logger.debug(
                    f"Found ontology type '{ontology_type}' for endpoint '{endpoint_name}', property '{property_name}'"
                )
                return ontology_type
            else:
                logger.warning(
                    f"No EndpointPropertyConfig found linking endpoint '{endpoint_name}' and property '{property_name}' to a PropertyExtractionConfig."
                )
                return None

        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True,
            )
            return None

    async def _find_direct_paths(
        self, session: AsyncSession, source_ontology: str, target_ontology: str
    ) -> List[MappingPath]:
        """Find direct mapping paths from source to target ontology without direction reversal."""
        logger.debug(
            f"Searching for direct mapping paths from '{source_ontology}' to '{target_ontology}'"
        )

        # We need to join MappingPath -> MappingPathStep -> MappingResource
        # for both the first step (to check source_ontology)
        # and the last step (to check target_ontology).

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
            # Use selectinload for eager loading related steps and resources
            .options(
                selectinload(MappingPath.steps).joinedload(
                    MappingPathStep.mapping_resource
                )
            )
            .join(first_step_sq, MappingPath.id == first_step_sq.c.mapping_path_id)
            .join(last_step_sq, MappingPath.id == last_step_sq.c.mapping_path_id)
            .where(first_step_sq.c.input_ontology_term == source_ontology)
            .where(last_step_sq.c.output_ontology_term == target_ontology)
            .order_by(MappingPath.priority.asc())  # Lower number means higher priority
        )

        result = await session.execute(stmt)
        # Use unique() to handle potential duplicates if joins create multiple rows for the same path
        paths = result.scalars().unique().all()

        if paths:
            logger.debug(
                f"Found {len(paths)} direct mapping path(s) from '{source_ontology}' to '{target_ontology}'"
            )
            # Log the found paths for clarity
            for path in paths:
                logger.debug(
                    f" - Path ID: {path.id}, Name: '{path.name}', Priority: {path.priority}"
                )
        else:
            logger.debug(
                f"No direct mapping paths found from '{source_ontology}' to '{target_ontology}'"
            )

        return paths
        
    async def _find_mapping_paths(
        self, session: AsyncSession, source_ontology: str, target_ontology: str, 
        bidirectional: bool = False
    ) -> List[Union[MappingPath, ReversiblePath]]:
        """
        Find mapping paths between ontologies, optionally searching in both directions.
        
        Args:
            session: The database session
            source_ontology: Source ontology term
            target_ontology: Target ontology term
            bidirectional: If True, also search for reverse paths (target→source) when no forward paths exist
            
        Returns:
            List of paths (may be wrapped in ReversiblePath if reverse paths were found)
        """
        logger.debug(
            f"Searching for mapping paths from '{source_ontology}' to '{target_ontology}' (bidirectional={bidirectional})"
        )
        
        # First try to find forward paths
        forward_paths = await self._find_direct_paths(session, source_ontology, target_ontology)
        paths = [ReversiblePath(path, is_reverse=False) for path in forward_paths]
        
        # If bidirectional flag is set and no forward paths were found, try reverse
        if bidirectional and not paths:
            logger.info(f"No forward paths found, searching for reverse paths from '{target_ontology}' to '{source_ontology}'")
            reverse_paths = await self._find_direct_paths(session, target_ontology, source_ontology)
            paths.extend([ReversiblePath(path, is_reverse=True) for path in reverse_paths])
        
        if paths:
            direction = "bidirectional" if bidirectional else "forward"
            logger.info(f"Found {len(paths)} potential mapping path(s) using {direction} search")
            for path in paths:
                reverse_text = "(REVERSE)" if path.is_reverse else ""
                logger.info(f" - Path ID: {path.id}, Name: '{path.name}' {reverse_text}, Priority: {path.priority}")
        else:
            logger.warning(f"No mapping paths found from '{source_ontology}' to '{target_ontology}' (bidirectional={bidirectional})")
        
        return paths

    async def _find_best_path(
        self, session: AsyncSession, source_type: str, target_type: str, 
        bidirectional: bool = False
    ) -> Optional[Union[MappingPath, ReversiblePath]]:
        """
        Find the highest priority mapping path, optionally considering reverse paths.
        
        Args:
            session: Database session
            source_type: Source ontology type
            target_type: Target ontology type
            bidirectional: If True, also search for reverse paths if no forward paths found
            
        Returns:
            The highest priority path, which might be a reverse path if bidirectional=True
        """
        paths = await self._find_mapping_paths(session, source_type, target_type, bidirectional=bidirectional)
        return paths[0] if paths else None

    def _load_client_class(self, client_class_path: str) -> type:
        """Dynamically load the client class."""
        try:
            module_path, class_name = client_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            ClientClass = getattr(module, class_name)
            return ClientClass
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            logger.error(
                f"Error loading client class '{client_class_path}': {e}", exc_info=True
            )
            raise ClientInitializationError(
                f"Could not load client class {client_class_path}",
                client_name=class_name,
                details=str(e),
            )

    async def _load_client(self, resource: MappingResource) -> Any:
        """Loads and initializes a client instance."""
        try:
            client_class = self._load_client_class(resource.client_class_path)
            # Parse the config template
            config_for_init = {}
            if resource.config_template:
                try:
                    config_for_init = json.loads(resource.config_template)
                except json.JSONDecodeError as json_err:
                    raise ClientInitializationError(
                        f"Invalid configuration template JSON for {resource.name}",
                        client_name=resource.name,
                        details=str(json_err),
                    )

            # Initialize the client with the config
            client_instance = client_class(config=config_for_init)
            return client_instance
        except ClientInitializationError:
            # Re-raise without wrapping to preserve the original error
            raise
        except Exception as e:
            # Catch any other initialization errors
            logger.error(
                f"Unexpected error initializing client for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Unexpected error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            )
            
    async def _execute_mapping_step(
        self,
        step: MappingPathStep,
        input_values: List[str],
        is_reverse: bool = False
    ) -> Dict[str, Optional[List[str]]]:
        """
        Execute a single mapping step, handling reverse execution if needed.
        
        Args:
            step: The mapping step to execute
            input_values: List of input identifiers
            is_reverse: If True, execute in reverse direction (output→input)
            
        Returns:
            Dictionary mapping input IDs to lists of output IDs
        """
        client_instance = await self._load_client(step.mapping_resource)
        
        if not is_reverse:
            # Normal forward execution
            return await client_instance.map_identifiers(input_values)
        else:
            # Reverse execution - try specialized reverse method first
            if hasattr(client_instance, "reverse_map_identifiers"):
                logger.debug(f"Using specialized reverse_map_identifiers method for {step.mapping_resource.name}")
                return await client_instance.reverse_map_identifiers(input_values)
                
            # Fall back to inverting the results of forward mapping
            logger.info(f"Executing reverse mapping for {step.mapping_resource.name} by inverting forward results")
            # Get all possible output identifiers by executing a forward mapping
            # Then filter for matches with our input values
            
            # This approach is less efficient but more reliable than trying to 
            # simulate reverse mapping for clients that don't support it
            try:
                # We first need to get all mappings related to our inputs
                all_forward_results = await client_instance.map_identifiers(input_values)
                
                # Now invert the mapping (source_id → [target_ids] becomes target_id → [source_id])
                inverted_results = {}
                for source_id, target_ids in all_forward_results.items():
                    if not target_ids:
                        continue
                        
                    for target_id in target_ids:
                        if target_id in input_values:  # Only include our requested inputs
                            if target_id not in inverted_results:
                                inverted_results[target_id] = []
                            inverted_results[target_id].append(source_id)
                
                # Add empty results for inputs with no matches
                for input_id in input_values:
                    if input_id not in inverted_results:
                        inverted_results[input_id] = []
                        
                return inverted_results
            except Exception as e:
                logger.error(f"Failed to execute reverse mapping for {step.mapping_resource.name}: {e}")
                # Return empty results rather than failing
                return {input_id: [] for input_id in input_values}

    async def _get_path_details_from_log(
        self, cache_session: AsyncSession, path_log_id: int
    ) -> Dict[str, Any]:
        """
        Get path details for a given path execution log.

        Args:
            cache_session: Database session for the cache database
            path_log_id: ID of the PathExecutionLog

        Returns:
            Dict with path details (hop_count, resource types, etc.)
        """
        # Retrieve the PathExecutionLog entry
        path_log = await cache_session.get(MappingPathExecutionLog, path_log_id)
        if not path_log:
            logger.warning(f"PathExecutionLog with ID {path_log_id} not found")
            return {
                "hop_count": 1,
                "resource_types": ["unknown"],
                "client_identifiers": ["unknown"],
            }

        # Get the mapping path ID
        path_id = path_log.relationship_mapping_path_id

        # Create a session for metamapper DB to get full path details
        async with self.async_session() as meta_session:
            # Use the helper method to get path details
            return await self._get_path_details(meta_session, path_id)

    async def _cache_results(
        self,
        cache_session: AsyncSession,
        path_log_id: int,
        source_ontology: str,
        target_ontology: str,
        results: Dict[str, Optional[List[str]]],
        mapping_direction: str,
    ):
        """
        Caches the mapping results in the database, handling updates and provenance.

        Args:
            session: The database session.
            path_log_id: The ID of the PathExecutionLog entry for provenance.
            source_ontology: The source ontology type (e.g., 'GENE_NAME').
            target_ontology: The target ontology type (e.g., 'UNIPROTKB_AC').
            results: Dictionary mapping source IDs to lists of target IDs or None.
            mapping_direction: The direction of the mapping ('forward' or 'reverse').
        """
        now = datetime.now(timezone.utc)
        log_mapping_associations = []
        mappings_added_count = 0
        mappings_to_add_or_update = []  # Collect mappings to add/update

        # OUTER TRY BLOCK for the entire method
        try:
            # Retrieve the PathExecutionLog entry first
            path_log = await cache_session.get(MappingPathExecutionLog, path_log_id)
            if not path_log:
                logger.error(
                    f"ConfigurationError: PathExecutionLog with ID {path_log_id} not found. Cannot cache results."
                )
                return

            # Get detailed path information to use for confidence scoring and metadata
            path_details = await self._get_path_details_from_log(
                cache_session, path_log_id
            )

            unique_results_to_process = {}  # Ensure we only process each source_id once
            for source_id, target_ids in results.items():
                if source_id not in unique_results_to_process:
                    unique_results_to_process[source_id] = target_ids

            for source_id, target_ids in unique_results_to_process.items():
                # Ensure target_ids is a list even if None for consistent processing
                processed_target_ids = (
                    target_ids
                    if isinstance(target_ids, list)
                    else ([target_ids] if target_ids else [])
                )

                # Determine the target_id representation for EntityMapping storage
                if not processed_target_ids:
                    target_id_str = None  # Explicitly None if no mapping found
                elif len(processed_target_ids) == 1:
                    target_id_str = str(processed_target_ids[0])
                else:
                    target_id_str = json.dumps(
                        sorted([str(tid) for tid in processed_target_ids])
                    )

                # --- Create/Update EntityMapping --- #
                # Check if mapping already exists
                stmt = select(EntityMapping).where(
                    EntityMapping.source_id == source_id,
                    EntityMapping.source_type == source_ontology,
                    EntityMapping.target_type == target_ontology,
                )
                existing_mapping_result = await cache_session.execute(stmt)
                existing_mapping = existing_mapping_result.scalars().first()

                # Prepare common mapping details
                path_hop_count = path_details.get("hop_count", 1)
                confidence_score = self._calculate_confidence_score(
                    path_log=path_log,
                    processed_target_ids=processed_target_ids,
                    path_details=path_details,
                )
                mapping_details = {
                    # Store path details as JSON (consider making this cleaner)
                    "path_details": path_details,
                }

                if existing_mapping:
                    # Update existing mapping
                    existing_mapping.target_id = target_id_str # Update target even if None
                    existing_mapping.last_updated = now
                    existing_mapping.confidence_score = confidence_score
                    existing_mapping.hop_count = path_hop_count
                    existing_mapping.mapping_path_details = mapping_details # Store raw dict
                    existing_mapping.mapping_direction = mapping_direction
                    existing_mapping.usage_count = (existing_mapping.usage_count or 0) + 1
                    # No need to add to session if only updating
                    mappings_to_add_or_update.append(existing_mapping) # Track for logging
                elif target_id_str is not None: # Only create NEW entries if a mapping was found
                    new_mapping = EntityMapping(
                        source_id=source_id,
                        source_type=source_ontology,
                        target_id=target_id_str,
                        target_type=target_ontology,
                        confidence=1.0,  # Default confidence, overwrite below
                        mapping_source=path_log.relationship_mapping_path_id, # Link to path ID
                        is_derived=path_hop_count > 1,
                        last_updated=now,
                        confidence_score=confidence_score,
                        hop_count=path_hop_count,
                        mapping_path_details=mapping_details, # Store raw dict
                        mapping_direction=mapping_direction,
                        usage_count=1,
                    )
                    mappings_to_add_or_update.append(new_mapping)
                    mappings_added_count += 1

                # --- Create PathLogMappingAssociation entries --- #
                # ALWAYS create association(s) for the input_identifier and this log_id
                if not processed_target_ids:
                    # If no target, create one association with output=None
                    log_mapping_associations.append(
                        PathLogMappingAssociation(
                            log_id=path_log_id,
                            input_identifier=source_id,
                            output_identifier=None, # Explicitly None
                        )
                    )
                else:
                    # If targets exist, create association for each input->output pair
                    for target_id in processed_target_ids:
                        log_mapping_associations.append(
                            PathLogMappingAssociation(
                                log_id=path_log_id,
                                input_identifier=source_id,
                                output_identifier=str(target_id),
                            )
                        )

            # --- Commit Changes --- #
            try:
                # Add all new mappings and associations
                if mappings_to_add_or_update:
                    # Use merge for updates, add_all for new ones?
                    # For simplicity now, let SQLAlchemy handle based on primary key if objects
                    # were fetched from the session.
                    # If we created new objects, add_all is needed.
                    # Let's explicitly add new ones.
                    new_mappings = [m for m in mappings_to_add_or_update if not cache_session.is_modified(m) and m not in cache_session]
                    if new_mappings:
                        cache_session.add_all(new_mappings)

                if log_mapping_associations:
                    cache_session.add_all(log_mapping_associations)
                    await cache_session.flush() # Flush to ensure associations are persisted before logging count
                    logger.info(
                        f"Cache update: Processed {len(unique_results_to_process)} unique inputs, "
                        f"added/updated {len(mappings_to_add_or_update)} EntityMappings, "
                        f"committed {len(log_mapping_associations)} associations with log ID {path_log_id}."
                    )

                await cache_session.commit()
            except (
                SQLAlchemyError,
                DBAPIError,
            ) as db_error:
                await cache_session.rollback()
                logger.error(
                    f"CacheTransactionError: Database error during inner transaction for log ID {path_log_id}: {db_error}",
                    exc_info=True,
                )
                raise CacheTransactionError(
                    f"Database error during transaction for log ID {path_log_id}"
                ) from db_error
            except Exception as e:
                await cache_session.rollback()
                logger.error(
                    f"CacheError: Unexpected error during transaction for log ID {path_log_id}: {e}",
                    exc_info=True,
                )
                raise CacheError(
                    f"Unexpected error during cache transaction for log ID {path_log_id}"
                ) from e

        # OUTER EXCEPT BLOCKS for the entire method
        except (SQLAlchemyError, DBAPIError) as db_error:
            try:
                await cache_session.rollback()
            except Exception:
                pass  # Ignore errors during rollback
            logger.error(
                f"CacheTransactionError: Database error during cache commit for log ID {path_log_id}: {db_error}",
                exc_info=True,
            )
            raise CacheTransactionError(
                f"Database error during cache operation for log ID {path_log_id}"
            ) from db_error
        except CacheTransactionError:
            # Re-raise specific cache errors without wrapping
            raise
        except Exception as e:
            try:
                await cache_session.rollback()
            except Exception:
                pass  # Ignore errors during rollback
            logger.error(
                f"Unexpected error during cache operation for log ID {path_log_id}: {e}",
                exc_info=True,
            )
            raise CacheError(
                f"Unexpected error during cache operation for log ID {path_log_id}"
            ) from e

    async def _check_cache(
        self,
        cache_session: AsyncSession,
        source_ids: List[str],
        source_type: str,
        target_type: str,
        max_age_days: Optional[int] = None,
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
        logger.debug(
            f"Checking cache for {len(source_ids)} source IDs: {source_type} -> {target_type}"
        )
        result = {source_id: None for source_id in source_ids}
        if not source_ids:
            return result

        try:
            stmt = select(EntityMapping).where(
                EntityMapping.source_id.in_(source_ids),
                EntityMapping.source_type == source_type,
                EntityMapping.target_type == target_type,
            )
            if max_age_days is not None:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
                stmt = stmt.where(EntityMapping.last_updated >= cutoff_date)
                logger.debug(f"Applying cache max age filter: >= {cutoff_date}")

            query_result = await cache_session.execute(stmt)
            mappings = query_result.scalars().all()

            processed_mappings: Dict[str, Tuple[datetime, str]] = {}
            for mapping in mappings:
                if (
                    mapping.source_id not in processed_mappings
                    or mapping.last_updated > processed_mappings[mapping.source_id][0]
                ):
                    processed_mappings[mapping.source_id] = (
                        mapping.last_updated,
                        mapping.target_id,
                    )

            cache_hits = 0
            for source_id, (_, target_id) in processed_mappings.items():
                result[source_id] = target_id
                cache_hits += 1

            if cache_hits > 0:
                logger.info(
                    f"Cache hit: Found {cache_hits}/{len(source_ids)} mappings in cache for {source_type} -> {target_type}"
                )
            else:
                logger.debug(
                    f"Cache miss: No valid mappings found in cache for {source_type} -> {target_type}"
                )
            return result

        except (SQLAlchemyError, DBAPIError) as db_error:
            logger.error(
                f"CacheRetrievalError: Database error during cache check for {source_type} -> {target_type}: {db_error}",
                exc_info=True,
            )
            raise CacheRetrievalError(
                f"Database error during cache check for {source_type} -> {target_type}"
            ) from db_error

    async def execute_mapping(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str] = None,
        input_data: List[str] = None,
        source_property_name: str = "PrimaryIdentifier",
        target_property_name: str = "PrimaryIdentifier",
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
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
        :param mapping_direction: The direction of mapping ('forward' or 'reverse')
        :param try_reverse_mapping: When True, attempts to find reverse paths if no forward paths exist
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
                logger.info(
                    f"Executing mapping: {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}"
                )

                # Corrected calls to _get_ontology_type, passing property names
                source_ontology = await self._get_ontology_type(
                    meta_session, source_endpoint_name, source_property_name
                )
                target_ontology = await self._get_ontology_type(
                    meta_session, target_endpoint_name, target_property_name
                )

                if not source_ontology or not target_ontology:
                    error_message = f"Configuration Error: Could not determine source ontology ('{source_ontology}') or target ontology ('{target_ontology}') for {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}."
                    logger.error(error_message)
                    raise ConfigurationError(error_message)

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
                        logger.error(
                            f"ConfigurationError: {error_message} (Source: '{source_endpoint_name}', Target: '{target_endpoint_name}')"
                        )
                        raise ConfigurationError(error_message)

                # --- Find the best path, optionally considering reverse paths ---
                path = await self._find_best_path(
                    meta_session, source_ontology, target_ontology, bidirectional=try_reverse_mapping
                )
                
                if not path:
                    error_message = f"No mapping path found from {source_ontology} to {target_ontology}"
                    logger.error(error_message)
                    return {
                        "status": PathExecutionStatus.NO_PATH_FOUND.value,
                        "error": error_message,
                        "results": {id: None for id in input_identifiers},
                    }
                
                # Determine if this is a reversed path
                is_reverse_path = getattr(path, "is_reverse", False)
                
                # Set effective direction based on path direction
                effective_direction = "reverse" if is_reverse_path else mapping_direction
                
                if is_reverse_path:
                    logger.info(f"Using reverse path '{path.name}' for {target_ontology} -> {source_ontology}")
                else:
                    logger.info(f"Using forward path '{path.name}' for {source_ontology} -> {target_ontology}")

                source_node = None
                target_node = None
                for step in path.steps:
                    if step.step_order == 1:
                        source_node = step.mapping_resource
                    if step.step_order == max(s.step_order for s in path.steps):
                        target_node = step.mapping_resource

                if not source_node or not target_node:
                    error_message = f"Configuration Error: Path ID {path.id} ('{path.name}') has no steps defined."
                    logger.error(error_message)
                    raise ConfigurationError(error_message)

                # Initialize final result dictionary and path_log
                final_results: Dict[str, Optional[str]] = {}
                path_log = None

                try:
                    async with self.get_cache_session() as cache_session:
                        try:
                            # 1. Check cache
                            cached_results = await self._check_cache(
                                cache_session,
                                list(input_identifiers),
                                source_ontology,
                                target_ontology,
                                max_age_days=path.cache_duration_days
                                if hasattr(path, "cache_duration_days")
                                else max_cache_age_days,
                            )

                            # 2. Initialize final_results with valid cached hits
                            # Use .get() for safety, default to None if key not found (shouldn't happen with init)
                            final_results = {
                                k: v for k, v in cached_results.items() if v is not None
                            }
                            uncached_identifiers = [
                                id
                                for id in input_identifiers
                                if cached_results.get(id) is None
                            ]

                            # 3. Execute path for uncached identifiers
                            if not uncached_identifiers:
                                logger.info("All identifiers found in cache.")
                                # Create log entry even if only cache was used
                                path_log = await self._create_mapping_log(
                                    cache_session,
                                    path.id,
                                    PathExecutionStatus.SUCCESS,
                                    representative_source_id=input_identifiers[0]
                                    if input_identifiers
                                    else "unknown",  # Add example source ID
                                    source_entity_type=source_ontology,  # Pass the source ontology type
                                )
                                await cache_session.commit()
                            else:
                                path_log = await self._create_mapping_log(
                                    cache_session,
                                    path.id,
                                    PathExecutionStatus.PENDING,
                                    representative_source_id=uncached_identifiers[0]
                                    if uncached_identifiers
                                    else "unknown",  # Add example source ID
                                    source_entity_type=source_ontology,  # Pass the source ontology type
                                )
                                logger.info(
                                    f"Executing path ID {path.id} for {len(uncached_identifiers)} uncached identifiers. Log ID: {path_log.id}"
                                )

                                # Initialize current results with input identifiers and execute path
                                current_results: Dict[str, Optional[List[str]]] = {
                                    orig_id: [orig_id]
                                    for orig_id in uncached_identifiers
                                }
                                path_status = PathExecutionStatus.PENDING

                                for step in sorted(
                                    path.steps, key=lambda s: s.step_order
                                ):
                                    step_input_set: Set[str] = set()
                                    for original_id, id_list in current_results.items():
                                        if id_list:
                                            step_input_set.update(id_list)

                                    step_input_values = sorted(list(step_input_set))
                                    if not step_input_values:
                                        logger.warning(
                                            f"Skipping step {step.step_order} due to no input values."
                                        )
                                        continue

                                    logger.info(
                                        f"Executing Step {step.step_order}: Resource '{step.mapping_resource.name}'"
                                    )
                                    try:
                                        client_instance = await self._load_client(
                                            step.mapping_resource
                                        )
                                        step_results = (
                                            await client_instance.map_identifiers(
                                                step_input_values
                                            )
                                        )

                                        # Process step results and update current_results for next step
                                        next_current_results = {}
                                        for (
                                            original_id,
                                            current_id_list,
                                        ) in current_results.items():
                                            if current_id_list is None:
                                                next_current_results[original_id] = None
                                                continue

                                            aggregated_outputs_for_orig_id = set()
                                            found_mapping = False
                                            for current_id in current_id_list:
                                                output_for_current_id = (
                                                    step_results.get(current_id)
                                                )
                                                if output_for_current_id:
                                                    aggregated_outputs_for_orig_id.update(
                                                        output_for_current_id
                                                    )
                                                    found_mapping = True
                                                elif output_for_current_id is None:
                                                    found_mapping = True

                                            if found_mapping:
                                                next_current_results[original_id] = (
                                                    sorted(
                                                        list(
                                                            aggregated_outputs_for_orig_id
                                                        )
                                                    )
                                                    if aggregated_outputs_for_orig_id
                                                    else None
                                                )
                                            else:
                                                next_current_results[original_id] = None

                                        current_results = next_current_results
                                    except ClientInitializationError:
                                        # Re-raise initialization errors without wrapping
                                        path_status = PathExecutionStatus.FAILURE
                                        if path_log:
                                            path_log.status = (
                                                PathExecutionStatus.FAILURE
                                            )
                                        raise
                                    except Exception as e:
                                        client_name = (
                                            step.mapping_resource.name
                                            if step.mapping_resource
                                            else "Unknown Client"
                                        )
                                        logger.error(
                                            f"Error during execution of mapping step {step.step_order} using client {client_name}: {e}",
                                            exc_info=True,
                                        )
                                        path_status = PathExecutionStatus.FAILURE
                                        if path_log:
                                            path_log.status = (
                                                PathExecutionStatus.FAILURE
                                            )
                                        raise ClientExecutionError(
                                            f"Error in client execution: {e}",
                                            client_name=client_name,
                                            details=str(e),
                                        ) from e

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
                                logger.info(
                                    f"Mapping step finished. Total results: {len(final_results)}. Status: {path_status}"
                                )

                                # Update path log
                                if path_status != PathExecutionStatus.FAILURE:
                                    # Check if all source IDs were successfully mapped
                                    if all(
                                        mapped_results.get(id) is not None
                                        for id in uncached_identifiers
                                    ):
                                        path_status = PathExecutionStatus.SUCCESS
                                    elif any(
                                        mapped_results.get(id) is not None
                                        for id in uncached_identifiers
                                    ):
                                        path_status = PathExecutionStatus.PARTIAL_SUCCESS
                                    else:
                                        path_status = PathExecutionStatus.NO_MAPPING_FOUND

                                path_log.status = path_status
                                path_log.end_time = datetime.now(timezone.utc)

                                # 5. Cache the newly mapped results
                                if (
                                    mapped_results
                                ):  # Only cache if there are new results
                                    await self._cache_results(
                                        cache_session,
                                        path_log.id,
                                        source_ontology,
                                        target_ontology,
                                        results=mapped_results,  # Cache only the *newly* mapped results
                                        mapping_direction=mapping_direction,  # Pass direction
                                    )
                                await (
                                    cache_session.commit()
                                )  # Commit log update and new cache entries

                        except (
                            Exception
                        ) as cache_lookup_error:  # Catch any error during cache check
                            logger.error(
                                f"CacheError during cache lookup, proceeding without cache: {cache_lookup_error}",
                                exc_info=True,
                            )
                            cached_results = {}

                        # Filter uncached_identifiers based on cache results
                        uncached_identifiers = [
                            id
                            for id in input_identifiers
                            if cached_results.get(id) is None
                        ]

                        if uncached_identifiers:
                            path_log = await self._create_mapping_log(
                                cache_session,
                                path.id,
                                PathExecutionStatus.PENDING,
                                representative_source_id=uncached_identifiers[0]
                                if uncached_identifiers
                                else "unknown",  # Add example source ID
                                source_entity_type=source_ontology,  # Pass the source ontology type
                            )
                            logger.info(
                                f"Executing path ID {path.id} for {len(uncached_identifiers)} uncached identifiers. Log ID: {path_log.id}"
                            )

                            # Initialize current results with input identifiers and execute path
                            current_results: Dict[str, Optional[List[str]]] = {
                                orig_id: [orig_id] for orig_id in uncached_identifiers
                            }
                            path_status = PathExecutionStatus.PENDING

                            for step in sorted(path.steps, key=lambda s: s.step_order):
                                step_input_set: Set[str] = set()
                                for original_id, id_list in current_results.items():
                                    if id_list:
                                        step_input_set.update(id_list)

                                step_input_values = sorted(list(step_input_set))
                                if not step_input_values:
                                    logger.warning(
                                        f"Skipping step {step.step_order} due to no input values."
                                    )
                                    continue

                                logger.info(
                                    f"Executing Step {step.step_order}: Resource '{step.mapping_resource.name}'"
                                )
                                try:
                                    client_instance = await self._load_client(
                                        step.mapping_resource
                                    )
                                    step_results = (
                                        await client_instance.map_identifiers(
                                            step_input_values
                                        )
                                    )

                                    # Process step results and update current_results for next step
                                    next_current_results = {}
                                    for (
                                        original_id,
                                        current_id_list,
                                    ) in current_results.items():
                                        if current_id_list is None:
                                            next_current_results[original_id] = None
                                            continue

                                        aggregated_outputs_for_orig_id = set()
                                        found_mapping = False
                                        for current_id in current_id_list:
                                            output_for_current_id = step_results.get(
                                                current_id
                                            )
                                            if output_for_current_id:
                                                aggregated_outputs_for_orig_id.update(
                                                    output_for_current_id
                                                )
                                                found_mapping = True
                                            elif output_for_current_id is None:
                                                found_mapping = True

                                        if found_mapping:
                                            next_current_results[original_id] = (
                                                sorted(
                                                    list(
                                                        aggregated_outputs_for_orig_id
                                                    )
                                                )
                                                if aggregated_outputs_for_orig_id
                                                else None
                                            )
                                        else:
                                            next_current_results[original_id] = None

                                    current_results = next_current_results
                                except ClientInitializationError:
                                    # Re-raise initialization errors without wrapping
                                    path_status = PathExecutionStatus.FAILURE
                                    if path_log:
                                        path_log.status = PathExecutionStatus.FAILURE
                                    raise
                                except Exception as e:
                                    client_name = (
                                        step.mapping_resource.name
                                        if step.mapping_resource
                                        else "Unknown Client"
                                    )
                                    logger.error(
                                        f"Error during execution of mapping step {step.step_order} using client {client_name}: {e}",
                                        exc_info=True,
                                    )
                                    path_status = PathExecutionStatus.FAILURE
                                    if path_log:
                                        path_log.status = PathExecutionStatus.FAILURE
                                    raise ClientExecutionError(
                                        f"Error in client execution: {e}",
                                        client_name=client_name,
                                        details=str(e),
                                    ) from e

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
                            logger.info(
                                f"Mapping step finished. Total results: {len(final_results)}. Status: {path_status}"
                            )

                            # Update path log
                            if path_status != PathExecutionStatus.FAILURE:
                                # Check if all source IDs were successfully mapped
                                if all(
                                    mapped_results.get(id) is not None
                                    for id in uncached_identifiers
                                ):
                                    path_status = PathExecutionStatus.SUCCESS
                                elif any(
                                    mapped_results.get(id) is not None
                                    for id in uncached_identifiers
                                ):
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
                                    results=mapped_results,  # Cache only the *newly* mapped results
                                    mapping_direction=mapping_direction,  # Pass direction
                                )
                            await (
                                cache_session.commit()
                            )  # Commit log update and new cache entries

                except Exception as e:
                    logger.error(
                        f"Error during mapping execution for path {path.id}: {e}",
                        exc_info=True,
                    )
                    if path_log:
                        path_log.status = PathExecutionStatus.FAILED
                        path_log.end_time = datetime.now(timezone.utc)
                    await cache_session.rollback()
                    # Keep potentially partial final_results from cache

        except (
            ClientExecutionError,
            ClientInitializationError,
            CacheError,
            ConfigurationError,
            NoPathFoundError,
        ):
            # Re-raise specific exceptions without wrapping to preserve the error type
            if not final_results:
                final_results = {}
            raise
        except Exception as e:
            logger.error(
                f"Unhandled error in execute_mapping (e.g., DB connection): {e}",
                exc_info=True,
            )
            # Ensure final_results is initialized if outer error occurs early
            if not final_results:
                final_results = {}
            raise MappingExecutionError(
                f"Unhandled error during mapping execution: {e}"
            ) from e

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

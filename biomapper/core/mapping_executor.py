import asyncio
import enum
import importlib
import json
import time # Add import time
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Type
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DBAPIError

# Import composite identifier handling
from biomapper.core.composite_handler import CompositeIdentifierHandler, CompositeMiddleware
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin
from biomapper.core.exceptions import (
    BiomapperError,
    NoPathFoundError,
    ClientError,
    ConfigurationError, # Import ConfigurationError
    CacheError,
    MappingExecutionError,
    ClientExecutionError,
    ClientInitializationError,
    CacheTransactionError,
    CacheRetrievalError,
    CacheStorageError,
    ErrorCode, # Import ErrorCode
    DatabaseQueryError, # Import DatabaseQueryError
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
    MappingSession,  # Add this for session logging
    ExecutionMetric # Added ExecutionMetric
)

# Import our centralized configuration settings
from biomapper.config import settings

from pathlib import Path # Added import

import logging # Re-added import
import os # Add import os

from biomapper.utils.formatters import PydanticEncoder

# Added get_current_utc_time definition
def get_current_utc_time() -> datetime:
    """Return the current time in UTC timezone."""
    return datetime.now(timezone.utc)

class ReversiblePath:
    """Wrapper to allow executing a path in reverse direction."""

    def __init__(self, original_path: MappingPath, is_reverse: bool = False):
        self.original_path = original_path
        self.is_reverse = is_reverse

    @property
    def id(self) -> Optional[int]:
        return self.original_path.id

    @property
    def name(self) -> Optional[str]:
        return (
            f"{self.original_path.name} (Reverse)"
            if self.is_reverse
            else self.original_path.name
        )

    @property
    def priority(self) -> Optional[int]:
        # Reverse paths have slightly lower priority
        original_priority = self.original_path.priority if self.original_path.priority is not None else 100 # Default priority if None
        return original_priority + (5 if self.is_reverse else 0)

    @property
    def steps(self) -> List[MappingPathStep]:
        if not self.is_reverse:
            return self.original_path.steps
        else:
            # Return steps in reverse order
            return sorted(self.original_path.steps, key=lambda s: -(s.step_order or 0))

    def __getattr__(self, name: str) -> Any:
        # Delegate other attributes to the original path
        return getattr(self.original_path, name)


class MappingExecutor(CompositeIdentifierMixin):
    """Executes mapping tasks based on configurations in metamapper.db."""

    def __init__(
        self,
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False, # Added parameter to control SQL echoing
        path_cache_size: int = 100, # Maximum number of paths to cache
        path_cache_expiry_seconds: int = 300, # Cache expiry time in seconds (5 minutes)
        max_concurrent_batches: int = 5, # Maximum number of batches to process concurrently
        enable_metrics: bool = True, # Whether to enable metrics tracking
    ):
        """
        Initializes the MappingExecutor.

        Args:
            metamapper_db_url: URL for the metamapper database. If None, uses settings.metamapper_db_url.
            mapping_cache_db_url: URL for the mapping cache database. If None, uses settings.cache_db_url.
            echo_sql: Boolean flag to enable SQL echoing for debugging purposes.
            path_cache_size: Maximum number of paths to cache in memory
            path_cache_expiry_seconds: Cache expiry time in seconds
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            
        Returns:
            An initialized MappingExecutor instance with database tables created
        """
        # Initialize the CompositeIdentifierMixin
        super().__init__()

        self.logger = logging.getLogger(__name__) # Moved logger initialization before Langfuse setup

        self.metamapper_db_url = (
            metamapper_db_url
            if metamapper_db_url is not None
            else settings.metamapper_db_url
        )
        self.mapping_cache_db_url = (
            mapping_cache_db_url
            if mapping_cache_db_url is not None
            else settings.cache_db_url
        )
        self.echo_sql = echo_sql
        
        # Path caching and concurrency settings
        self._path_cache = {}
        self._path_cache_timestamps = {}
        self._path_cache_lock = asyncio.Lock()  # Thread safety for cache access
        self._path_cache_max_size = path_cache_size
        self._path_cache_expiry_seconds = path_cache_expiry_seconds
        self.max_concurrent_batches = max_concurrent_batches
        
        # Performance monitoring
        self.enable_metrics = enable_metrics
        self._metrics_tracker = None
        self._langfuse_tracker = None
        
        # Initialize metrics tracking if enabled and langfuse is available
        if self.enable_metrics:
            try:
                import langfuse
                self._langfuse_tracker = langfuse.Langfuse(
                    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                )
                self.logger.info("Langfuse metrics tracking initialized")
            except (ImportError, Exception) as e:
                self.logger.warning(f"Langfuse metrics tracking not available: {e}")

        # Log database URLs being used
        self.logger.info(f"Using Metamapper DB URL: {self.metamapper_db_url}")
        self.logger.info(f"Using Mapping Cache DB URL: {self.mapping_cache_db_url}")
        self.logger.info(f"Initialized with path_cache_size={path_cache_size}, concurrent_batches={max_concurrent_batches}")

        # Ensure directories for file-based DBs exist
        for db_url in [self.metamapper_db_url, self.mapping_cache_db_url]:
            if db_url.startswith("sqlite"):
                try:
                    # Extract path after '///'
                    db_path_str = db_url.split(":///", 1)[1]
                    db_path = Path(db_path_str)
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Ensured directory exists: {db_path.parent}")
                except IndexError:
                    self.logger.error(f"Could not parse file path from SQLite URL: {db_url}")
                except Exception as e:
                    self.logger.error(f"Error ensuring directory for {db_url}: {e}")

        # Setup SQLAlchemy engines and sessions for Metamapper
        meta_async_url = self.metamapper_db_url
        if self.metamapper_db_url.startswith("sqlite:///"):
            meta_async_url = self.metamapper_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        self.async_metamapper_engine = create_async_engine(meta_async_url, echo=self.echo_sql)
        self.MetamapperSessionFactory = sessionmaker(
            self.async_metamapper_engine, class_=AsyncSession, expire_on_commit=False
        )
        # Define an async session property for easier access
        self.async_metamapper_session = self.MetamapperSessionFactory

        # Setup SQLAlchemy engines and sessions for Mapping Cache
        cache_async_url = self.mapping_cache_db_url
        if self.mapping_cache_db_url.startswith("sqlite:///"):
            cache_async_url = self.mapping_cache_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        self.async_cache_engine = create_async_engine(cache_async_url, echo=self.echo_sql)
        self.CacheSessionFactory = sessionmaker(
            self.async_cache_engine, class_=AsyncSession, expire_on_commit=False
        )
        # Define an async session property for easier access
        self.async_cache_session = self.CacheSessionFactory

    async def _init_db_tables(self, engine, base_metadata):
        """Initialize database tables if they don't exist.
        
        Args:
            engine: SQLAlchemy async engine to use
            base_metadata: The metadata object containing table definitions
        """
        try:
            # Check if the tables already exist
            async with engine.connect() as conn:
                # Check if mapping_sessions table exists
                has_tables = await conn.run_sync(
                    lambda sync_conn: sync_conn.dialect.has_table(
                        sync_conn, "mapping_sessions"
                    )
                )
                
                if has_tables:
                    self.logger.info(f"Tables already exist in database {engine.url}, skipping initialization.")
                    return
                
                # Tables don't exist, create them
                self.logger.info(f"Tables don't exist in database {engine.url}, creating them...")
            
            # Create tables
            async with engine.begin() as conn:
                await conn.run_sync(base_metadata.create_all)
            self.logger.info(f"Database tables for {engine.url} initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error initializing database tables for {engine.url}: {str(e)}", exc_info=True)
            raise BiomapperError(
                f"Failed to initialize database tables: {str(e)}",
                error_code=ErrorCode.DATABASE_INITIALIZATION_ERROR,
                details={"engine_url": str(engine.url)}
            ) from e
    
    @classmethod
    async def create(
        cls,
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False,
        path_cache_size: int = 100,
        path_cache_expiry_seconds: int = 300,
        max_concurrent_batches: int = 5,
        enable_metrics: bool = True,
    ):
        """Asynchronously create and initialize a MappingExecutor instance.
        
        This factory method creates a MappingExecutor instance and initializes
        the database tables for both metamapper and cache databases.
        
        Args:
            metamapper_db_url: URL for the metamapper database. If None, uses settings.metamapper_db_url.
            mapping_cache_db_url: URL for the mapping cache database. If None, uses settings.cache_db_url.
            echo_sql: Boolean flag to enable SQL echoing for debugging purposes.
            path_cache_size: Maximum number of paths to cache in memory
            path_cache_expiry_seconds: Cache expiry time in seconds
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            
        Returns:
            An initialized MappingExecutor instance with database tables created
        """
        # Create instance with standard constructor
        executor = cls(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=mapping_cache_db_url,
            echo_sql=echo_sql,
            path_cache_size=path_cache_size,
            path_cache_expiry_seconds=path_cache_expiry_seconds,
            max_concurrent_batches=max_concurrent_batches,
            enable_metrics=enable_metrics,
        )
        
        # Initialize cache database tables
        await executor._init_db_tables(executor.async_cache_engine, CacheBase.metadata)
        
        # Note: We don't initialize metamapper tables here because they're assumed to be
        # already set up and populated. The issue is specifically with cache tables.
        
        executor.logger.info("MappingExecutor instance created and database tables initialized.")
        return executor
    
    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()


    async def _get_path_details(self, path_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a mapping path including all steps.
        
        Args:
            path_id: The ID of the mapping path
            
        Returns:
            A dictionary with detailed information about the path
        """
        try:
            async with self.get_metamapper_session() as session:
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

    async def _cache_results(
        self,
        results_to_cache: Dict[str, Dict[str, Any]],
        path: Union[MappingPath, "ReversiblePath"],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None
    ):
        """
        Store successful mapping results in the cache.
        
        Calculates and populates metadata fields:
        - confidence_score: Based on path length and direction.
        - hop_count: Number of steps in the executed path.
        - mapping_direction: Whether the path was executed in "forward" or "reverse" direction.
        - mapping_path_details: Structured JSON information about the path execution.
        
        Args:
            results_to_cache: Dictionary of source identifiers to mapping results.
            path: MappingPath or ReversiblePath that was executed.
            source_ontology: Source ontology type.
            target_ontology: Target ontology type.
            mapping_session_id: Optional ID of the mapping session.
        
        Returns:
            The ID of the created path execution log entry, or None if no results cached.
        
        Raises:
            CacheStorageError: If there is an error storing the results in the cache.
            CacheTransactionError: If there is an error during the database transaction.
            CacheError: For other unexpected caching errors.
        """
        # Skip if no results to cache
        if not results_to_cache:
            self.logger.debug("No results to cache")
            return None # Return None explicitly

        path_id = path.id
        path_name = path.name
        self.logger.debug(f"Caching results for path ID: {path_id}, Name: {path_name}")

        # Retrieve detailed path information using the helper method
        try:
            path_step_details = await self._get_path_details(path_id)
        except Exception as e:
            # Log error but proceed with caching if possible, using empty details
            self.logger.error(f"Failed to retrieve path details for {path_id} during caching: {e}", exc_info=True)
            path_step_details = {}

        # Determine if this is a reverse path
        is_reversed = getattr(path, "is_reverse", False)
        mapping_direction = "reverse" if is_reversed else "forward"

        # Calculate hop count from path steps if available
        hop_count = len(path.steps) if hasattr(path, "steps") and path.steps else None
        self.logger.debug(f"Path {path_id} - Reversed: {is_reversed}, Hop Count: {hop_count}")

        # Prepare the rich path details JSON structure
        mapping_path_info = {
            "path_id": path_id,
            "path_name": path_name,
            "is_reversed": is_reversed,
            "hop_count": hop_count,
            "steps": path_step_details # Use the retrieved step details
        }
        try:
            # Serialize to JSON
            path_details_json = json.dumps(mapping_path_info, cls=PydanticEncoder)
        except Exception as e:
            self.logger.error(f"Failed to serialize path details for {path_id} to JSON: {e}", exc_info=True)
            path_details_json = json.dumps({"error": "Failed to serialize path details"}, cls=PydanticEncoder) # Fallback JSON

        # Calculate match count accurately
        input_count = len(results_to_cache)
        match_count = sum(
            1 for res in results_to_cache.values()
            if res.get("target_identifiers") and any(res["target_identifiers"])
        )
        self.logger.debug(f"Input Count: {input_count}, Match Count: {match_count}")

        # Create a mapping execution log entry (initially without ID)
        log_entry = MappingPathExecutionLog(
            path_id=path_id,
            source_ontology_type=source_ontology,
            target_ontology_type=target_ontology,
            session_id=mapping_session_id,
            execution_time=get_current_utc_time(), # Use helper method
            status=PathExecutionStatus.SUCCESS,
            input_count=input_count,
            match_count=match_count,
            path_details_json=path_details_json # Store the full JSON here now
        )

        entity_mappings = []
        current_time = get_current_utc_time() # Get time once for consistency

        for source_id, result in results_to_cache.items():
            target_identifiers = result.get("target_identifiers", [])
            # Ensure target_identifiers is always a list
            if not isinstance(target_identifiers, list):
                target_identifiers = [target_identifiers] if target_identifiers is not None else []
            
            # Filter out None values from target identifiers
            valid_target_ids = [tid for tid in target_identifiers if tid is not None]

            if not valid_target_ids:
                self.logger.debug(f"No valid target identifiers found for source {source_id}")
                continue

            # Calculate confidence score based on mapping path characteristics
            confidence_score = self._calculate_confidence_score(result, hop_count, is_reversed, path_step_details)
            
            self.logger.debug(f"Source: {source_id}, Hops: {hop_count}, Reversed: {is_reversed}, Confidence: {confidence_score}")

            # Create mapping_path_details JSON with complete path information
            mapping_path_details_dict = self._create_mapping_path_details(
                path_id=path_id,
                path_name=path_name,
                hop_count=hop_count,
                mapping_direction=mapping_direction,
                path_step_details=path_step_details,
                log_id=log_entry.id if log_entry and log_entry.id else None,
                additional_metadata=result.get("additional_metadata")
            )
            try:
                mapping_path_details = json.dumps(mapping_path_details_dict, cls=PydanticEncoder)
            except Exception as e:
                self.logger.error(f"Failed to serialize mapping_path_details for {source_id} to JSON: {e}", exc_info=True)
                mapping_path_details = json.dumps({"error": "Failed to serialize details"}, cls=PydanticEncoder)

            # Create entity mapping for each valid target identifier
            for target_id in valid_target_ids:
                # Determine mapping source based on path details
                source_type = self._determine_mapping_source(path_step_details)
                
                entity_mapping = EntityMapping(
                    source_id=str(source_id),  # Updated to match field names in cache_models.py
                    source_type=source_ontology,
                    target_id=str(target_id),
                    target_type=target_ontology,
                    mapping_source=source_type,  # Set mapping_source from our helper function
                    last_updated=current_time,
                    
                    # Enhanced metadata fields:
                    confidence_score=confidence_score,
                    hop_count=hop_count,
                    mapping_direction=mapping_direction,
                    mapping_path_details=mapping_path_details
                )
                entity_mappings.append(entity_mapping)

        if not entity_mappings:
            self.logger.warning(f"No valid entity mappings generated for path {path_id}, despite having results to cache. Check input data.")
            # Optionally, still log the execution attempt even if no mappings are created
            try:
                async with self.get_cache_session() as session:
                    log_entry.status = PathExecutionStatus.SUCCESS_NO_MATCH # Indicate success but no mappings
                    log_entry.match_count = 0 # Correct match count
                    session.add(log_entry)
                    await session.commit()
                    self.logger.info(f"Logged execution for path {path_id} with no resulting mappings.")
                    return log_entry.id
            except Exception as e:
                 self.logger.error(f"Failed to log no-match execution for path {path_id}: {e}", exc_info=True)
                 # Decide how to handle this - maybe raise CacheError? For now, just log.
                 return None # Indicate failure to log
            # return None # Indicate nothing was cached

        # Store the log entry and mappings in the cache database
        log_entry_id = None
        try:
            async with self.get_cache_session() as session:
                # Add the log entry first to get its ID
                session.add(log_entry)
                await session.flush() # Generate the ID for log_entry
                log_entry_id = log_entry.id
                self.logger.debug(f"Created MappingPathExecutionLog entry with ID: {log_entry_id}")

                # Update entity mappings with the log entry ID
                for mapping in entity_mappings:
                    mapping.path_execution_log_id = log_entry_id
                
                # Add all entity mappings
                session.add_all(entity_mappings)
                await session.commit() # Commit the transaction

                self.logger.info(f"Successfully cached {len(entity_mappings)} mappings and execution log (ID: {log_entry_id}) for path {path_id}.")
                return log_entry_id # Return the ID of the log entry

        except IntegrityError as e:
            await session.rollback() # Rollback on integrity error (e.g., duplicate)
            self.logger.error(f"IntegrityError during cache storage for path {path_id}: {str(e)}")
            raise CacheStorageError(f"Error storing mapping results in cache: {str(e)}", original_exception=e)
        except SQLAlchemyError as e:
            await session.rollback() # Rollback on other DB errors
            self.logger.error(f"SQLAlchemyError during cache transaction for path {path_id}: {str(e)}", exc_info=True)
            raise CacheTransactionError(f"Error during cache transaction: {str(e)}", original_exception=e)
        except Exception as e:
            # Ensure rollback happens even for unexpected errors within the 'try' block
            # Check if session is active before rolling back
            if 'session' in locals() and session.is_active:
                await session.rollback()
            self.logger.error(f"Unexpected error during caching for path {path_id}: {str(e)}", exc_info=True)
            raise CacheError(f"Unexpected error during caching: {str(e)}", original_exception=e)


    async def _find_direct_paths(
        self, session: AsyncSession, source_ontology: str, target_ontology: str
    ) -> List[MappingPath]:
        """Find direct mapping paths from source to target ontology without direction reversal."""
        self.logger.debug(
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

        try:
            result = await session.execute(stmt)
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database query error finding direct paths: {e}", exc_info=True
            )
            raise BiomapperError(
                f"Database error finding paths from {source_ontology} to {target_ontology}",
                error_code=ErrorCode.DATABASE_QUERY_ERROR,
                details={"source": source_ontology, "target": target_ontology},
            ) from e

        # Use unique() to handle potential duplicates if joins create multiple rows for the same path
        paths = result.scalars().unique().all()

        if paths:
            self.logger.debug(
                f"Found {len(paths)} direct mapping path(s) from '{source_ontology}' to '{target_ontology}'"
            )
            # Log the found paths for clarity
            for path in paths:
                self.logger.debug(
                    f" - Path ID: {path.id}, Name: '{path.name}', Priority: {path.priority}"
                )
        else:
            self.logger.debug(
                f"No direct mapping paths found from '{source_ontology}' to '{target_ontology}'"
            )

        return paths

    async def _find_mapping_paths(
        self,
        session: AsyncSession,
        source_ontology: str,
        target_ontology: str,
        bidirectional: bool = False,
        preferred_direction: str = "forward",
    ) -> List[Union[MappingPath, "ReversiblePath"]]:
        """
        Find mapping paths between ontologies, optionally searching in both directions concurrently.

        Args:
            session: The database session
            source_ontology: Source ontology term
            target_ontology: Target ontology term
            bidirectional: If True, search for both forward and reverse paths in parallel
            preferred_direction: Preferred direction for path ordering ("forward" or "reverse")

        Returns:
            List of paths (may be wrapped in ReversiblePath if reverse paths were found)
            Paths are sorted by direction preference and then by priority
        """
        # Use caching to avoid redundant database calls
        cache_key = f"{source_ontology}_{target_ontology}_{bidirectional}_{preferred_direction}"
        
        # Initialize path cache if needed with time-based expiration
        if not hasattr(self, "_path_cache"):
            self._path_cache = {}
            self._path_cache_timestamps = {}
            self._path_cache_lock = asyncio.Lock()  # Thread safety for cache access
            self._path_cache_max_size = 100  # Maximum number of paths to cache
            self._path_cache_expiry_seconds = 300  # Cache expiry time in seconds (5 minutes)
            
        # Check if cache entry exists and is not expired
        current_time = time.time()
        cache_hit = False
        
        async with self._path_cache_lock:
            if cache_key in self._path_cache:
                # Check if cache entry is expired
                timestamp = self._path_cache_timestamps.get(cache_key, 0)
                if current_time - timestamp < self._path_cache_expiry_seconds:
                    cache_hit = True
                    self.logger.debug(f"Using cached paths for {cache_key}")
                    return self._path_cache[cache_key]
                else:
                    # Remove expired cache entry
                    self.logger.debug(f"Cache entry for {cache_key} expired, removing")
                    del self._path_cache[cache_key]
                    if cache_key in self._path_cache_timestamps:
                        del self._path_cache_timestamps[cache_key]
            
        self.logger.debug(
            f"Searching for mapping paths from '{source_ontology}' to '{target_ontology}' (bidirectional={bidirectional}, preferred={preferred_direction})"
        )

        # Create tasks for both forward and reverse path finding
        forward_task = self._find_direct_paths(session, source_ontology, target_ontology)
        
        if bidirectional:
            # Only create the reverse task if bidirectional=True
            reverse_task = self._find_direct_paths(session, target_ontology, source_ontology)
            # Run both tasks concurrently
            forward_paths, reverse_paths = await asyncio.gather(forward_task, reverse_task)
            
            # Process forward paths
            paths = [ReversiblePath(path, is_reverse=False) for path in forward_paths]
            # Process reverse paths
            reverse_path_objects = [ReversiblePath(path, is_reverse=True) for path in reverse_paths]
            
            # Combine paths based on preferred direction
            if preferred_direction == "reverse":
                # If reverse is preferred, put reverse paths first
                paths = reverse_path_objects + paths
            else:
                # Otherwise, forward paths first (default)
                paths = paths + reverse_path_objects
        else:
            # If not bidirectional, just get the forward paths
            forward_paths = await forward_task
            paths = [ReversiblePath(path, is_reverse=False) for path in forward_paths]

        # Sort paths by priority after respecting direction preference
        paths = sorted(paths, key=lambda p: (-1 if p.is_reverse != (preferred_direction == "reverse") else 1, p.priority))

        # Log found paths
        if paths:
            direction = "bidirectional" if bidirectional else "forward"
            self.logger.info(
                f"Found {len(paths)} potential mapping path(s) using {direction} search"
            )
            for path in paths:
                reverse_text = "(REVERSE)" if path.is_reverse else ""
                self.logger.info(
                    f" - Path ID: {path.id}, Name: '{path.name}' {reverse_text}, Priority: {path.priority}"
                )
        
        # Cache the results to avoid redundant database calls with thread safety and size limits
        async with self._path_cache_lock:
            # Implement LRU-like behavior by removing oldest entries if cache is too large
            if len(self._path_cache) >= self._path_cache_max_size:
                # Find oldest entry
                oldest_key = None
                oldest_time = float('inf')
                for key, timestamp in self._path_cache_timestamps.items():
                    if timestamp < oldest_time:
                        oldest_time = timestamp
                        oldest_key = key
                        
                if oldest_key:
                    self.logger.debug(f"Cache full, removing oldest entry: {oldest_key}")
                    del self._path_cache[oldest_key]
                    del self._path_cache_timestamps[oldest_key]
            
            # Store new cache entry with timestamp
            self._path_cache[cache_key] = paths
            self._path_cache_timestamps[cache_key] = time.time()
            
            # Add telemetry
            cache_size = len(self._path_cache)
            if cache_size % 10 == 0:  # Log every 10 entries
                self.logger.info(f"Path cache contains {cache_size} entries")
        
        # Log warning if no paths were found
        if not paths:
            self.logger.warning(
                f"No mapping paths found from '{source_ontology}' to '{target_ontology}' (bidirectional={bidirectional})"
            )
            
        return paths

    async def _find_best_path(
        self,
        session: AsyncSession,
        source_type: str,
        target_type: str,
        bidirectional: bool = False,
        preferred_direction: str = "forward",
        allow_reverse: bool = False,
    ) -> Optional[Union[MappingPath, ReversiblePath]]:
        """
        Find the highest priority mapping path, optionally considering reverse paths concurrently.

        Args:
            session: Database session
            source_type: Source ontology type
            target_type: Target ontology type
            bidirectional: If True, also search for reverse paths concurrently with forward paths
            preferred_direction: Preferred direction ("forward" or "reverse") for path selection
            allow_reverse: Legacy parameter to maintain compatibility, same as bidirectional=True

        Returns:
            The highest priority path, sorted by direction preference and then by priority
        """
        # For compatibility: if allow_reverse is True, make sure bidirectional is too
        if allow_reverse and not bidirectional:
            bidirectional = True
            
        # Find all paths with the given parameters
        paths = await self._find_mapping_paths(
            session, 
            source_type, 
            target_type, 
            bidirectional=bidirectional,
            preferred_direction=preferred_direction
        )
        
        return paths[0] if paths else None

    async def _get_endpoint_properties(self, session: AsyncSession, endpoint_name: str) -> List[EndpointPropertyConfig]:
        """Get all property configurations for an endpoint."""
        stmt = select(EndpointPropertyConfig).join(Endpoint, EndpointPropertyConfig.endpoint_id == Endpoint.id).where(Endpoint.name == endpoint_name)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _get_ontology_preferences(self, session: AsyncSession, endpoint_name: str) -> List[OntologyPreference]:
        """Get ontology preferences for an endpoint."""
        # Join Endpoint to OntologyPreference via endpoint_id
        stmt = select(OntologyPreference).join(
            Endpoint, 
            OntologyPreference.endpoint_id == Endpoint.id
        ).where(Endpoint.name == endpoint_name)
        
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _get_endpoint(self, session: AsyncSession, endpoint_name: str) -> Optional[Endpoint]:
        """Retrieves an endpoint by name.
        
        Args:
            session: SQLAlchemy session
            endpoint_name: Name of the endpoint to retrieve
            
        Returns:
            The Endpoint if found, None otherwise
        """
        try:
            stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
            result = await session.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if endpoint:
                self.logger.debug(f"Found endpoint: {endpoint.name} (ID: {endpoint.id})")
            else:
                self.logger.warning(f"Endpoint not found: {endpoint_name}")
                
            return endpoint
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving endpoint {endpoint_name}: {e}", exc_info=True)
            raise DatabaseQueryError(
                f"Database error fetching endpoint",
                details={"endpoint": endpoint_name, "error": str(e)}
            ) from e
    
    async def _get_ontology_type(self, session: AsyncSession, endpoint_name: str, property_name: str) -> Optional[str]:
        """Retrieves the primary ontology type for a given endpoint and property name."""
        self.logger.debug(f"Getting ontology type for {endpoint_name}.{property_name}")
        try:
            # Join EndpointPropertyConfig with Endpoint
            stmt = (
                select(EndpointPropertyConfig.ontology_type)
                .join(Endpoint, Endpoint.id == EndpointPropertyConfig.endpoint_id)
                .where(Endpoint.name == endpoint_name)
                .where(EndpointPropertyConfig.property_name == property_name)
                .limit(1)
            )
            result = await session.execute(stmt)
            ontology_type = result.scalar_one_or_none()
            
            if ontology_type:
                self.logger.debug(f"Found ontology type: {ontology_type}")
            else:
                self.logger.warning(f"Ontology type not found for {endpoint_name}.{property_name}")
            
            return ontology_type
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error retrieving ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True
            )
            raise DatabaseQueryError(
                f"Database error fetching ontology type",
                details={"endpoint": endpoint_name, "property": property_name, "error": str(e)}
            ) from e
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True
            )
            raise BiomapperError(
                f"An unexpected error occurred while retrieving ontology type",
                error_code=ErrorCode.DATABASE_QUERY_ERROR,  # Changed to DATABASE_QUERY_ERROR to match test
                details={"endpoint": endpoint_name, "property": property_name, "error": str(e)}
            ) from e

    async def _load_client_class(self, client_class_path: str) -> type:
        """Dynamically load the client class."""
        try:
            module_path, class_name = client_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            ClientClass = getattr(module, class_name)
            return ClientClass
        except (ImportError, AttributeError) as e:
            self.logger.error(
                f"Error loading client class '{client_class_path}': {e}", exc_info=True
            )
            raise ClientInitializationError(
                f"Could not load client class {client_class_path}",
                client_name=client_class_path.split(".")[-1] if "." in client_class_path else client_class_path,
                details={"error": str(e)}
            ) from e

    async def _load_client(self, resource: MappingResource) -> Any:
        """Loads and initializes a client instance."""
        try:
            client_class = await self._load_client_class(resource.client_class_path)
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

            # Initialize the client with the config, passing it as 'config'
            client_instance = client_class(config=config_for_init)
            return client_instance
        except ImportError as e:
            self.logger.error(
                f"ImportError during client initialization for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Import error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            ) from e
        except AttributeError as e:
            self.logger.error(
                f"AttributeError during client initialization for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Attribute error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            ) from e
        except Exception as e:
            # Catch any other initialization errors
            self.logger.error(
                f"Unexpected error initializing client for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Unexpected error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            )

    async def _execute_mapping_step(
        self, step: MappingPathStep, input_values: List[str], is_reverse: bool = False
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Execute a single mapping step, handling reverse execution if needed.

        Args:
            step: The mapping step to execute
            input_values: List of input identifiers
            is_reverse: If True, execute in reverse direction (output→input)

        Returns:
            Dictionary mapping input IDs to tuples: (list of output IDs, successful source component ID or None)
        """
        try:
            client_instance = await self._load_client(step.mapping_resource)
        except ClientInitializationError:
            # Propagate initialization errors directly
            raise

        try:
            if not is_reverse:
                # Normal forward execution
                self.logger.debug(
                    f"_execute_mapping_step calling {client_instance.__class__.__name__}.map_identifiers with {len(input_values)} identifiers."
                )
                if len(input_values) < 10:
                    self.logger.debug(f"  Input sample: {input_values}")
                else:
                    self.logger.debug(f"  Input sample: {input_values[:10]}...")
                # map_identifiers is expected to return the rich dictionary:
                # {'primary_ids': [...], 'input_to_primary': {in:out}, 'errors': [...]}
                # This needs to be converted to Dict[str, Tuple[Optional[List[str]], Optional[str]]]
                client_results_dict = await client_instance.map_identifiers(input_values)
                
                processed_step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
                successful_mappings = client_results_dict.get('input_to_primary', {})
                for input_id, mapped_primary_id in successful_mappings.items():
                    processed_step_results[input_id] = ([mapped_primary_id], None) 
                
                errors_list = client_results_dict.get('errors', [])
                for error_detail in errors_list:
                    error_input_id = error_detail.get('input_id')
                    if error_input_id:
                        processed_step_results[error_input_id] = (None, None)
                        
                for val in input_values: # Ensure all original inputs are covered
                    if val not in processed_step_results:
                        processed_step_results[val] = (None, None)
                return processed_step_results
            else:
                # Reverse execution - try specialized reverse method first
                if hasattr(client_instance, "reverse_map_identifiers"):
                    self.logger.debug(
                        f"Using specialized reverse_map_identifiers method for {step.mapping_resource.name}"
                    )
                    client_results_dict = await client_instance.reverse_map_identifiers(
                        input_values
                    )
                    # client_results_dict is in the rich format:
                    # {'primary_ids': [...], 'input_to_primary': {in_id: out_id}, 'errors': [{'input_id': ...}]}
                    
                    # Expected output format for _execute_mapping_step is:
                    # Dict[str, Tuple[Optional[List[str]], Optional[str]]]
                    # i.e., Dict[original_input_id, ([mapped_ids_for_this_input], successful_component_if_any)]
                    
                    processed_step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
                    
                    successful_mappings = client_results_dict.get('input_to_primary', {})
                    for input_id, mapped_primary_id in successful_mappings.items():
                        # The format is ([mapped_id], None) where None is for component_id (not applicable here)
                        processed_step_results[input_id] = ([mapped_primary_id], None) 
                    
                    errors_list = client_results_dict.get('errors', [])
                    for error_detail in errors_list:
                        error_input_id = error_detail.get('input_id')
                        if error_input_id:
                            processed_step_results[error_input_id] = (None, None)
                            
                    # Ensure all original input_values passed to the step have an entry in the output
                    for val in input_values:
                        if val not in processed_step_results:
                            # Default to no mapping if not covered by success or error from client
                            processed_step_results[val] = (None, None) 
                    return processed_step_results

                # Fall back to inverting the results of forward mapping
                # NOTE: Conceptual issue here if map_identifiers expects source-type IDs
                # and input_values are target-type IDs.
                self.logger.info(
                    f"Executing reverse mapping for {step.mapping_resource.name} by inverting forward results"
                )
                # client_instance.map_identifiers is expected to return the rich structure.
                forward_results_dict = await client_instance.map_identifiers(input_values)

                # Now invert the mapping (target_id → [source_id])
                # The output of _execute_mapping_step should be Dict[str, Tuple[Optional[List[str]], Optional[str]]]
                # where the key is the *original input_id to this step* (which are target_ids in this context)
                inverted_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
                
                # Iterate through successful forward mappings from the client's perspective:
                # {source_id_of_client_map: target_id_of_client_map}
                for client_source_id, client_target_id in forward_results_dict.get('input_to_primary', {}).items():
                    # We are interested if this client_target_id is one of the IDs we are trying to map from (i.e., in input_values)
                    if client_target_id in input_values:
                        if client_target_id not in inverted_results:
                            inverted_results[client_target_id] = ([], None)
                        # Ensure the list is not None before appending
                        if inverted_results[client_target_id][0] is not None:
                             inverted_results[client_target_id][0].append(client_source_id)
                        else: # Should not happen if initialized with ([], None)
                             inverted_results[client_target_id] = ([client_source_id], None)
            
                # Add empty results (None, None) for step's input_values that didn't appear as a target in the forward map
                for original_step_input_id in input_values:
                    if original_step_input_id not in inverted_results:
                        inverted_results[original_step_input_id] = (None, None)
                
                return inverted_results

        except ClientError as ce:  # Catch specific client errors if raised by client
            self.logger.error(
                f"ClientError during execution step for {step.mapping_resource.name}: {ce}",
                exc_info=False, # Only log the exception message unless debug is high
            )

            # Ensure details is always a dictionary
            details_dict = (
                ce.details
                if isinstance(ce.details, dict)
                else {"error_message": str(ce.details)}
            )

            raise ClientExecutionError(
                f"Client error during step execution: {ce.message}",
                client_name=step.mapping_resource.name,
                details=details_dict,
                error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            ) from ce
        except (
            Exception
        ) as e:  # Fallback for other unexpected errors during client execution
            error_details = {"original_exception": str(e)}
            self.logger.error(
                f"Unexpected error during execution step for {step.mapping_resource.name}: {e}",
                exc_info=True,
            )
            raise ClientExecutionError(
                f"Unexpected error during step execution",
                client_name=step.mapping_resource.name,
                details=error_details,
            ) from e

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
        try:
            path_log = await cache_session.get(MappingPathExecutionLog, path_log_id)
        except SQLAlchemyError as e:
            self.logger.error(
                f"Cache retrieval error getting path log ID {path_log_id}: {e}",
                exc_info=True,
            )
            raise CacheRetrievalError(
                f"[{ErrorCode.CACHE_RETRIEVAL_ERROR}] Error during cache lookup query. (original_exception={type(e).__name__}: {e})",
                details={"log_id": path_log_id},
            ) from e

        if not path_log:
            self.logger.warning(f"PathExecutionLog with ID {path_log_id} not found")
            return {
                "hop_count": 1,
                "resource_types": ["unknown"],
                "client_identifiers": ["unknown"],
            }

        # Get the mapping path ID
        path_id = path_log.relationship_mapping_path_id

        # Create a session for metamapper DB to get full path details
        async with self.async_metamapper_session() as meta_session:
            # Use the helper method to get path details
            return await self._get_path_details(meta_session, path_id)

    async def _create_mapping_log(
        self,
        cache_session: AsyncSession,
        path_id: int,
        status: PathExecutionStatus,
        representative_source_id: str,
        source_entity_type: str,
    ) -> MappingPathExecutionLog:
        """
        Create a new path execution log entry.

        Args:
            cache_session: The cache database session
            path_id: The ID of the mapping path being executed
            status: Initial status of the path execution
            representative_source_id: A source ID to represent this execution batch
            source_entity_type: The ontology type of the source entities

        Returns:
            The created PathExecutionLog instance
        """
        try:
            now = datetime.now(timezone.utc)
            log_entry = MappingPathExecutionLog(
                relationship_mapping_path_id=path_id,
                status=status,
                start_time=now,
                source_entity_id=representative_source_id,  # Updated field name
                source_entity_type=source_entity_type,
            )
            cache_session.add(log_entry)
            await cache_session.flush()  # Ensure ID is generated
            await cache_session.commit() # Commit to make it visible to other sessions
            return log_entry
        except SQLAlchemyError as e:
            self.logger.error(f"Cache storage error creating path log: {e}", exc_info=True)
            raise CacheStorageError(
                f"[{ErrorCode.CACHE_STORAGE_ERROR}] Failed to create path execution log entry. (original_exception={type(e).__name__}: {e})",
                details={"path_id": path_id, "source_id": representative_source_id},
            ) from e

    async def _check_cache(
        self,
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_path_id: Optional[int] = None,
        expiry_time: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Check cache for existing mapping results.

        Args:
            input_identifiers: List of identifiers to check for cached mappings
            source_ontology: The ontology type of the source entities
            target_ontology: The ontology type of the target entities
            mapping_path_id: Optional ID of the mapping path to filter results by
            expiry_time: Optional cutoff time for result freshness

        Returns:
            Dictionary mapping input identifiers to result dictionaries containing target IDs and metadata
        """
        if not input_identifiers:
            return {}

        results = {}

        try:
            async with self.async_cache_session() as cache_session:
                # Construct base query
                stmt = select(EntityMapping).where(
                    EntityMapping.source_type == source_ontology,
                    EntityMapping.target_type == target_ontology
                )

                # Add filter for source_id based on the number of identifiers
                if len(input_identifiers) == 1:
                    stmt = stmt.where(EntityMapping.source_id == input_identifiers[0])
                elif len(input_identifiers) > 1:
                    stmt = stmt.where(EntityMapping.source_id.in_(input_identifiers))
                else: # len == 0
                    return {} # No identifiers, return empty cache results

                # Add timestamp filtering if expiry_time is provided
                if expiry_time:
                    stmt = stmt.where(EntityMapping.last_updated >= expiry_time)

                try:
                    # Execute query
                    result = await cache_session.execute(stmt)
                    mappings = result.scalars().all()
                except SQLAlchemyError as e:
                    self.logger.error(f"Cache query execution failed: {e}", exc_info=True)
                    raise CacheRetrievalError(
                        f"Error during cache lookup query",
                        details={"source_type": source_ontology, "target_type": target_ontology, "count": len(input_identifiers), "error": str(e)}
                    ) from e
                except Exception as e:
                    self.logger.error(f"Unexpected error during cache retrieval: {e}", exc_info=True)
                    raise CacheError(
                        f"Unexpected error during cache retrieval",
                        error_code=ErrorCode.UNKNOWN_ERROR,
                        details={"error": str(e)}
                    ) from e

                # Process the mappings
                for mapping in mappings:
                    # If mapping_path_id is specified, check if it matches
                    should_include = True
                    if mapping_path_id is not None and mapping.mapping_path_details:
                        # Extract path_id from the JSON string
                        try:
                            if isinstance(mapping.mapping_path_details, str):
                                path_details = json.loads(mapping.mapping_path_details)
                            else:
                                path_details = mapping.mapping_path_details
                                
                            stored_path_id = path_details.get('path_id')
                            if stored_path_id != mapping_path_id:
                                should_include = False
                        except (json.JSONDecodeError, AttributeError, TypeError):
                            # If we can't determine the path ID, don't include this result
                            should_include = False
                    
                    if should_include:
                        # Format the result with consistent structure
                        target_identifiers = None
                        if mapping.target_id:
                            # Check if it's a JSON array
                            try:
                                if mapping.target_id.startswith('[') and mapping.target_id.endswith(']'):
                                    # It's a JSON array of target IDs
                                    target_identifiers = json.loads(mapping.target_id)
                                else:
                                    # Single target ID
                                    target_identifiers = [mapping.target_id]
                            except (json.JSONDecodeError, AttributeError):
                                # Fallback to treating as a single ID
                                target_identifiers = [mapping.target_id]
                        
                        # Get mapping path details
                        path_details = None
                        if mapping.mapping_path_details:
                            try:
                                if isinstance(mapping.mapping_path_details, str):
                                    path_details = json.loads(mapping.mapping_path_details)
                                else:
                                    path_details = mapping.mapping_path_details
                            except (json.JSONDecodeError, TypeError):
                                # If invalid, leave as None
                                pass
                                
                        # Create a result structure that matches what _execute_path returns
                        results[mapping.source_id] = {
                            "source_identifier": mapping.source_id,
                            "target_identifiers": target_identifiers,
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": "Found in cache.",
                            "confidence_score": mapping.confidence_score or 0.8,  # Default if not set
                            "mapping_path_details": path_details,
                            "hop_count": mapping.hop_count,
                            "mapping_direction": mapping.mapping_direction,
                            "cached": True,  # Flag indicating this was from cache
                        }

                return results

        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking cache: {e}", exc_info=True)
            raise CacheRetrievalError(
                f"Error during cache lookup query",
                details={
                    "source_type": source_ontology,
                    "target_type": target_ontology,
                    "count": len(input_identifiers),
                    "error": str(e)
                }
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error checking cache: {e}", exc_info=True)
            raise CacheError(
                f"Unexpected error during cache retrieval",
                error_code=ErrorCode.UNKNOWN_ERROR,
                details={"error": str(e)}
            ) from e

    async def execute_mapping(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str] = None,
        input_data: List[str] = None, # Preferred input parameter
        source_property_name: str = "PrimaryIdentifier",
        target_property_name: str = "PrimaryIdentifier",
        source_ontology_type: str = None,  # Optional: provide source ontology directly
        target_ontology_type: str = None,  # Optional: provide target ontology directly
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = "forward", # Primarily for initial path finding bias
        try_reverse_mapping: bool = False, # Allows using reversed path if no forward found
        validate_bidirectional: bool = False, # Validates forward mappings by testing reverse mapping
        progress_callback: Optional[callable] = None, # Callback function for reporting progress
        batch_size: int = 250,  # Number of identifiers to process in each batch
        max_concurrent_batches: Optional[int] = None,  # Maximum number of batches to process concurrently
        max_hop_count: Optional[int] = None,  # Maximum number of hops to allow in paths
        min_confidence: float = 0.0,  # Minimum confidence score to accept
        enable_metrics: Optional[bool] = None,  # Whether to enable metrics tracking
    ) -> Dict[str, Any]:
        """
        Execute a mapping process based on endpoint configurations, using an iterative strategy.

        Steps:
        1. Attempt direct mapping using the primary shared ontology.
        2. Identify unmapped entities.
        3. For unmapped entities, attempt to convert secondary identifiers to the primary shared ontology based on priority. (To be implemented next)
        4. Re-attempt direct mapping using derived primary identifiers. (To be implemented next)
        5. Aggregate results.

        :param source_endpoint_name: Source endpoint name
        :param target_endpoint_name: Target endpoint name
        :param input_identifiers: List of identifiers to map (deprecated, use input_data instead)
        :param input_data: List of identifiers to map (preferred parameter)
        :param source_property_name: Property name defining the primary ontology type for the source endpoint
        :param target_property_name: Property name defining the primary ontology type for the target endpoint
        :param use_cache: Whether to check the cache before executing mapping steps
        :param max_cache_age_days: Maximum age of cached results to use (None = no limit)
        :param mapping_direction: The preferred direction ('forward' or 'reverse') - influences path selection but strategy remains the same.
        :param try_reverse_mapping: Allows using a reversed path if no forward path found in direct/indirect steps.
        :param validate_bidirectional: If True, validates forward mappings by running a reverse mapping and checking if target IDs map back to their source.
        :param progress_callback: Optional callback function for reporting progress (signature: callback(current: int, total: int, status: str))
        :return: Dictionary with mapping results, including provenance and validation status when bidirectional validation is enabled.
        """
        # --- Input Handling ---
        if input_data is not None and input_identifiers is None:
            input_identifiers = input_data
        elif input_identifiers is None and input_data is None:
            self.logger.warning("No input identifiers provided for mapping.")
            return {} # Return empty if no input
        # Ensure it's a list even if None was passed initially
        input_identifiers = input_identifiers if input_identifiers is not None else []

        # Use a set for efficient lookup and to handle potential duplicates in input
        original_input_ids_set = set(input_identifiers)
        successful_mappings = {}  # Store successfully mapped {input_id: result_details}
        processed_ids = set() # Track IDs processed in any successful step (cache hit or execution)
        final_results = {} # Initialize final results
        
        # Initialize progress tracking variables
        total_ids = len(original_input_ids_set)
        current_progress = 0
        
        # Report initial progress if callback provided
        if progress_callback:
            progress_callback(current_progress, total_ids, "Starting mapping process")

        # Set default parameter values from class attributes if not provided
        if max_concurrent_batches is None:
            max_concurrent_batches = getattr(self, "max_concurrent_batches", 5)
        
        if enable_metrics is None:
            enable_metrics = getattr(self, "enable_metrics", True)
            
        # Start overall execution performance tracking
        overall_start_time = time.time()
        
        # --- 0. Initial Setup --- Create a mapping session for logging ---
        mapping_session_id = await self._create_mapping_session_log(
            source_endpoint_name, target_endpoint_name, source_property_name,
            target_property_name, use_cache, try_reverse_mapping, len(original_input_ids_set),
            max_cache_age_days=max_cache_age_days
        )

        try:
            # --- 1. Get Endpoint Config and Primary Ontologies ---
            async with self.async_metamapper_session() as meta_session:
                self.logger.info(
                    f"Executing mapping: {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}"
                )
                
                # --- Check for composite identifiers and handle if needed ---
                # Skip composite handling for this optimization test
                self._composite_initialized = True
                # if not self._composite_initialized:
                #     await self._initialize_composite_handler(meta_session)
                
                # Get the primary source ontology type (needed to check for composite patterns)
                primary_source_ontology = await self._get_ontology_type(
                    meta_session, source_endpoint_name, source_property_name
                )
                
                # Check if composite identifier handling is needed for this ontology type
                if self._composite_handler.has_patterns_for_ontology(primary_source_ontology):
                    self.logger.info(f"Detected potential composite identifiers for ontology type '{primary_source_ontology}'")
                    
                    # Check if we should use composite handling
                    use_composite_handling = True
                    for input_id in input_identifiers:
                        if self._composite_handler.is_composite(input_id, primary_source_ontology):
                            self.logger.info(f"Found composite identifier pattern in '{input_id}'. Using composite identifier handling.")
                            break
                    else:
                        # No composite identifiers found in input
                        use_composite_handling = False
                    
                    if use_composite_handling:
                        # Use the specialized method that handles composite identifiers
                        return await self.execute_mapping_with_composite_handling(
                            meta_session,
                            input_identifiers,
                            source_endpoint_name,
                            target_endpoint_name,
                            primary_source_ontology,
                            # We don't have target_ontology yet, so get it now
                            await self._get_ontology_type(meta_session, target_endpoint_name, target_property_name),
                            mapping_session_id=mapping_session_id,
                            source_property_name=source_property_name,
                            target_property_name=target_property_name,
                            use_cache=use_cache,
                            max_cache_age_days=max_cache_age_days,
                            mapping_direction=mapping_direction,
                            try_reverse_mapping=try_reverse_mapping
                        )

                # Fetch endpoints and primary ontology types
                source_endpoint = await self._get_endpoint(meta_session, source_endpoint_name)
                target_endpoint = await self._get_endpoint(meta_session, target_endpoint_name)
                # We already have primary_source_ontology from the composite identifier check
                primary_target_ontology = await self._get_ontology_type(
                    meta_session, target_endpoint_name, target_property_name
                )

                # --- Debug Logging ---
                src_prop_name = getattr(source_endpoint, 'primary_property_name', 'NOT_FOUND') if source_endpoint else 'ENDPOINT_NONE'
                tgt_prop_name = getattr(target_endpoint, 'primary_property_name', 'NOT_FOUND') if target_endpoint else 'ENDPOINT_NONE'
                self.logger.info(f"DEBUG: SrcEP PrimaryProp: {src_prop_name}")
                self.logger.info(f"DEBUG: TgtEP PrimaryProp: {tgt_prop_name}")
                # --- End Debug Logging ---

                # Validate configuration
                if not all([source_endpoint, target_endpoint, primary_source_ontology, primary_target_ontology]):
                    error_message = "Configuration Error: Could not determine endpoints or primary ontologies."
                    # Log specific missing items if needed
                    self.logger.error(f"{error_message} SourceEndpoint: {source_endpoint}, TargetEndpoint: {target_endpoint}, SourceOntology: {primary_source_ontology}, TargetOntology: {primary_target_ontology}")
                    raise ConfigurationError(error_message) # Use ConfigurationError directly

                self.logger.info(f"Primary mapping ontologies: {primary_source_ontology} -> {primary_target_ontology}")

                # --- 2. Attempt Direct Primary Mapping (Source Ontology -> Target Ontology) ---
                self.logger.info("--- Step 2: Attempting Direct Primary Mapping ---")
                primary_path = await self._find_best_path(
                    meta_session,
                    primary_source_ontology,
                    primary_target_ontology,
                    preferred_direction=mapping_direction,
                    allow_reverse=try_reverse_mapping,
                )

                if not primary_path:
                    self.logger.warning(
                        f"No direct primary mapping path found from {primary_source_ontology} to {primary_target_ontology}."
                    )
                else:
                    self.logger.info(f"Found direct primary path: {primary_path.name} (ID: {primary_path.id})")
                    # Determine which IDs need processing (not found in cache)
                    ids_to_process_step2 = list(original_input_ids_set - processed_ids)
                    if not ids_to_process_step2:
                         self.logger.info("All relevant identifiers already processed via cache. Skipping Step 2 execution.")
                    else:
                        self.logger.info(f"Executing direct primary path for {len(ids_to_process_step2)} identifiers.")
                        primary_results_details = await self._execute_path(
                            meta_session,
                            primary_path,
                            ids_to_process_step2, # Process only those not found in cache yet
                            primary_source_ontology,
                            primary_target_ontology,
                            mapping_session_id=mapping_session_id,
                            batch_size=batch_size,
                            max_hop_count=max_hop_count,
                            filter_confidence=min_confidence,
                            max_concurrent_batches=max_concurrent_batches
                        )

                        # Process results from direct path
                        if primary_results_details:
                            num_newly_mapped = 0
                            for source_id, result_data in primary_results_details.items():
                                # Ensure result_data is not None and contains target_identifiers
                                if result_data and result_data.get("target_identifiers") is not None:
                                    if source_id not in successful_mappings:
                                        successful_mappings[source_id] = result_data
                                        processed_ids.add(source_id)
                                        num_newly_mapped += 1
                                    else:
                                        # Handle potential updates or conflicts if needed, though cache should prevent this
                                        self.logger.debug(f"Identifier {source_id} already mapped, skipping update from direct path.")
                            self.logger.info(f"Direct primary path execution mapped {num_newly_mapped} additional identifiers.")
                        else:
                            self.logger.info("Direct primary path execution yielded no new mappings.")

                # --- 3 & 4. Identify Unmapped Entities & Attempt Secondary -> Primary Conversion ---
                self.logger.info("--- Steps 3 & 4: Identifying Unmapped Entities & Attempting Secondary -> Primary Conversion ---")
                unmapped_ids_step3 = list(original_input_ids_set - processed_ids) # IDs not mapped by cache or Step 2
                
                # Initialize tracking for derived primary IDs - needed regardless of whether step 3 & 4 are executed
                derived_primary_ids = {}  # Will store {source_id: {'primary_id': derived_id, 'provenance': details}}

                if not unmapped_ids_step3:
                    self.logger.info("All input identifiers successfully mapped or handled in previous steps. Skipping Steps 3 & 4.")
                else:
                    self.logger.info(f"Found {len(unmapped_ids_step3)} identifiers remaining for Steps 3 & 4: {unmapped_ids_step3[:10]}...")

                    # --- 3a. Find and prioritize available secondary ontology types ---
                    # Get all available secondary properties for the source endpoint
                    all_properties = await self._get_endpoint_properties(meta_session, source_endpoint_name)
                    
                    # Filter to only secondary properties (those with different ontology than primary)
                    secondary_properties = [prop for prop in all_properties 
                                           if prop.property_name != source_property_name 
                                           and prop.ontology_type 
                                           and prop.ontology_type != primary_source_ontology]
                    
                    if not secondary_properties:
                        self.logger.warning(f"No suitable secondary properties/ontologies found for source endpoint '{source_endpoint_name}' (excluding primary '{source_property_name}' / '{primary_source_ontology}'). Skipping Steps 3 & 4.")
                    else:
                        # Get ontology preferences for the source endpoint to prioritize secondary types
                        preferences = await self._get_ontology_preferences(meta_session, source_endpoint_name)
                        
                        # Sort secondary properties by preference priority (or use order by ID if no preference found)
                        if preferences:
                            # Create a mapping of ontology_type to priority from preferences
                            priority_map = {pref.ontology_name: pref.priority for pref in preferences}
                            # Sort secondary properties by priority (lower number = higher priority)
                            secondary_properties.sort(key=lambda prop: priority_map.get(prop.ontology_type, 999))
                            self.logger.info(f"Sorted {len(secondary_properties)} secondary properties by endpoint preference priority.")
                        else:
                            self.logger.info(f"No ontology preferences found for '{source_endpoint_name}'. Using default property order.")
                            
                        # Initialize tracking for derived primary IDs
                        derived_primary_ids = {}  # Will store {source_id: {'primary_id': derived_id, 'provenance': details}}
                        
                        # --- 4. Iterate through secondary types for each unmapped entity ---
                        for secondary_prop in secondary_properties:
                            # Skip processing if all IDs now have derived primaries
                            unmapped_ids_without_derived = [uid for uid in unmapped_ids_step3 if uid not in derived_primary_ids]
                            if not unmapped_ids_without_derived:
                                self.logger.info("All unmapped identifiers now have derived primary IDs. Skipping remaining secondary properties.")
                                break
                                
                            secondary_source_ontology = secondary_prop.ontology_type
                            secondary_source_property_name = secondary_prop.property_name
                            
                            self.logger.info(f"Processing secondary property '{secondary_source_property_name}' with ontology type '{secondary_source_ontology}'")
                            self.logger.info(f"Remaining unmapped entities without derived primaries: {len(unmapped_ids_without_derived)}")
                            
                            # Find a path that converts this secondary ontology to primary source ontology
                            # This is different from before - we're looking for Secondary -> PRIMARY SOURCE (not target)
                            secondary_to_primary_path = await self._find_best_path(
                                meta_session,
                                secondary_source_ontology,  # From secondary source ontology
                                primary_source_ontology,    # To primary SOURCE ontology (not target)
                                preferred_direction=mapping_direction,
                                allow_reverse=try_reverse_mapping,
                            )
                            
                            if not secondary_to_primary_path:
                                self.logger.warning(f"No mapping path found from secondary ontology {secondary_source_ontology} to primary source ontology {primary_source_ontology}. Trying next secondary property.")
                                continue  # Try next secondary property
                                
                            self.logger.info(f"Found secondary-to-primary path: {secondary_to_primary_path.name} (ID: {secondary_to_primary_path.id})")
                            self.logger.info(f"Executing secondary-to-primary conversion for {len(unmapped_ids_without_derived)} identifiers.")
                            
                            # Execute this path to convert secondary -> primary source
                            conversion_results = await self._execute_path(
                                meta_session,
                                secondary_to_primary_path,
                                unmapped_ids_without_derived,
                                secondary_source_ontology,  # Start with secondary
                                primary_source_ontology,    # Convert to primary source
                                mapping_session_id=mapping_session_id,
                                batch_size=batch_size,
                                max_hop_count=max_hop_count,
                                filter_confidence=min_confidence,
                                max_concurrent_batches=max_concurrent_batches
                            )
                            
                            # Process results - for each successfully converted ID, store the derived primary
                            if conversion_results:
                                num_newly_derived = 0
                                for source_id, result_data in conversion_results.items():
                                    if result_data and result_data.get("target_identifiers"):
                                        # Store the derived primary ID(s) for this source ID
                                        derived_primary_ids[source_id] = {
                                            "primary_ids": result_data["target_identifiers"],
                                            "provenance": {
                                                "derived_from": secondary_source_ontology,
                                                "via_path": secondary_to_primary_path.name,
                                                "path_id": secondary_to_primary_path.id,
                                                "confidence": result_data.get("confidence_score", 0.0),
                                            }
                                        }
                                        num_newly_derived += 1
                                        
                                self.logger.info(f"Derived primary IDs for {num_newly_derived} entities using {secondary_source_ontology} -> {primary_source_ontology} conversion.")
                            else:
                                self.logger.info(f"No primary IDs derived from {secondary_source_ontology} -> {primary_source_ontology} conversion.")
                                
                        self.logger.info(f"Secondary-to-primary conversion complete. Derived primary IDs for {len(derived_primary_ids)}/{len(unmapped_ids_step3)} unmapped entities.")

                # --- 5. Re-attempt Direct Primary Mapping using derived primary IDs ---
                self.logger.info("--- Step 5: Re-attempting Direct Primary Mapping using derived primary IDs ---")
                
                # Check if we have any derived primary IDs to process
                if not derived_primary_ids:
                    self.logger.info("No derived primary IDs available. Skipping Step 5.")
                else:
                    self.logger.info(f"Re-attempting primary mapping using derived IDs for {len(derived_primary_ids)} entities.")
                    
                    # Check if we have a primary path to execute
                    if not primary_path:
                        self.logger.warning(f"No direct mapping path from {primary_source_ontology} to {primary_target_ontology} available for Step 5.")
                    else:
                        # Process each derived ID separately as they may have different primary IDs
                        for source_id, derived_data in derived_primary_ids.items():
                            if source_id in processed_ids:
                                # Skip if this ID was already successfully mapped somewhere
                                continue
                                
                            derived_primary_id_list = derived_data["primary_ids"]
                            provenance_info = derived_data["provenance"]
                            
                            # For each derived primary ID, attempt the mapping to target
                            for derived_primary_id in derived_primary_id_list:
                                self.logger.debug(f"Attempting mapping for {source_id} using derived primary ID {derived_primary_id}")
                                
                                # Check cache for any existing valid mappings first
                                if use_cache:
                                    self.logger.info("Checking cache for existing mappings...")
                                    pending_ids = list(original_input_ids_set - processed_ids)
                                    
                                    # Update progress
                                    if progress_callback:
                                        progress_callback(current_progress, total_ids, "Checking cache for existing mappings")
                                    
                                    # Try to get as many mappings from cache as possible
                                    cache_results = await self._get_cached_mappings(
                                        primary_source_ontology,
                                        primary_target_ontology,
                                        pending_ids,
                                        max_age_days=max_cache_age_days
                                    )
                                    
                                # Execute the primary path for this specific derived ID
                                derived_mapping_results = await self._execute_path(
                                    meta_session,
                                    primary_path,
                                    [derived_primary_id],  # Just the single derived ID
                                    primary_source_ontology,
                                    primary_target_ontology,
                                    mapping_session_id=mapping_session_id,
                                    batch_size=batch_size,
                                    max_hop_count=max_hop_count,
                                    filter_confidence=min_confidence,
                                    max_concurrent_batches=max_concurrent_batches
                                )
                                
                                # Process results - connect back to original source ID
                                if derived_mapping_results and derived_primary_id in derived_mapping_results:
                                    result_data = derived_mapping_results[derived_primary_id]
                                    if result_data and result_data.get("target_identifiers"):
                                        # Create a merged result that maintains connection to original source ID
                                        source_result = {
                                            "source_identifier": source_id,
                                            "target_identifiers": result_data["target_identifiers"],
                                            "status": PathExecutionStatus.SUCCESS.value,
                                            "message": f"Mapped via derived primary ID {derived_primary_id}",
                                            "confidence_score": result_data.get("confidence_score", 0.5) * 0.9,  # Slightly lower confidence for indirect mapping
                                            "hop_count": (result_data.get("hop_count", 1) + 1),  # Add a hop for the derivation step
                                            "mapping_direction": result_data.get("mapping_direction", "forward"),
                                            "derived_path": True,  # Flag to indicate this was through a derived ID
                                            "intermediate_id": derived_primary_id,  # Store the intermediate ID
                                        }
                                        
                                        # Merge path details
                                        if result_data.get("mapping_path_details"):
                                            # Get path details (might be string or dict)
                                            path_details = result_data["mapping_path_details"]
                                            if isinstance(path_details, str):
                                                try:
                                                    path_details = json.loads(path_details)
                                                except json.JSONDecodeError:
                                                    path_details = {}
                                            
                                            # Add the derivation step info to path details
                                            if isinstance(path_details, dict):
                                                path_details["derived_step"] = provenance_info
                                                source_result["mapping_path_details"] = json.dumps(path_details)
                                        
                                        # Add to successful mappings
                                        successful_mappings[source_id] = source_result
                                        processed_ids.add(source_id)
                                        self.logger.debug(f"Successfully mapped {source_id} to {source_result['target_identifiers']} via derived ID {derived_primary_id}")
                                        break  # Stop processing additional derived IDs for this source once we have a success
                            
                        # Log summary of indirect mapping results
                        newly_mapped = len([sid for sid in derived_primary_ids.keys() if sid in processed_ids])
                        self.logger.info(f"Indirect mapping using derived primary IDs successfully mapped {newly_mapped}/{len(derived_primary_ids)} additional entities.")

                # --- 6. Bidirectional Validation (if requested) ---
                if validate_bidirectional:
                    self.logger.info("--- Step 6: Performing Bidirectional Validation ---")
                    
                    # Skip if no successful mappings to validate
                    if not successful_mappings:
                        self.logger.info("No successful mappings to validate. Skipping bidirectional validation.")
                    else:
                        # Extract all target IDs that need validation
                        target_ids_to_validate = set()
                        for result in successful_mappings.values():
                            if result and result.get("target_identifiers"):
                                target_ids_to_validate.update(result["target_identifiers"])
                        
                        self.logger.info(f"Found {len(target_ids_to_validate)} unique target IDs to validate")
                        
                        # Find a reverse mapping path from target back to source
                        primary_source_ontology = await self._get_ontology_type(
                            meta_session, source_endpoint_name, source_property_name
                        )
                        primary_target_ontology = await self._get_ontology_type(
                            meta_session, target_endpoint_name, target_property_name
                        )
                        
                        self.logger.info(f"Step 1: Finding reverse mapping path from {primary_target_ontology} back to {primary_source_ontology}...")
                        reverse_path = await self._find_best_path(
                            meta_session,
                            primary_target_ontology,  # Using target as source
                            primary_source_ontology,  # Using source as target
                            preferred_direction="forward",  # We want a direct T->S path
                            allow_reverse=True  # Allow using S->T paths in reverse if needed
                        )
                        
                        if not reverse_path:
                            self.logger.warning(f"No reverse mapping path found from {primary_target_ontology} to {primary_source_ontology}. Validation incomplete.")
                        else:
                            self.logger.info(f"Step 2: Found reverse path: {reverse_path.name} (id={reverse_path.id})")
                            
                            # Execute reverse mapping
                            self.logger.info(f"Step 3: Reverse mapping from target to source...")
                            reverse_results = await self._execute_path(
                                meta_session,
                                reverse_path,
                                list(target_ids_to_validate),
                                primary_target_ontology,
                                primary_source_ontology,
                                mapping_session_id=mapping_session_id,
                                batch_size=batch_size,
                                max_concurrent_batches=max_concurrent_batches,
                                filter_confidence=min_confidence
                            )
                            
                            # Now enrich successful_mappings with validation status
                            self.logger.info(f"Step 4: Reconciling bidirectional mappings...")
                            successful_mappings = await self._reconcile_bidirectional_mappings(
                                successful_mappings,
                                reverse_results
                            )

                # --- 7. Aggregate Results & Finalize ---
                self.logger.info("--- Step 7: Aggregating final results ---")
                final_results = successful_mappings
                
                # Add nulls for any original inputs that were never successfully processed
                unmapped_count = 0
                for input_id in original_input_ids_set:
                    if input_id not in processed_ids:
                        # Use a consistent structure for not found/mapped
                        final_results[input_id] = {
                            "source_identifier": input_id,
                            "target_identifiers": None,
                            "status": PathExecutionStatus.NO_MAPPING_FOUND.value,
                            "message": "No successful mapping found via direct or secondary paths.",
                            "confidence_score": 0.0,
                            "mapping_path_details": None,
                            "hop_count": None,
                            "mapping_direction": None,
                        }
                        unmapped_count += 1
                
                self.logger.info(f"Mapping finished. Successfully processed {len(processed_ids)}/{len(original_input_ids_set)} inputs. ({unmapped_count} unmapped)")
                return final_results
                
        except BiomapperError as e:
            # Logged within specific steps or helpers typically
            self.logger.error(f"Biomapper Error during mapping execution: {e}", exc_info=True)
            # Return partial results + indicate error
            final_results = {**successful_mappings}
            error_count = 0
            for input_id in original_input_ids_set:
                if input_id not in processed_ids:
                    final_results[input_id] = {
                        "source_identifier": input_id,
                        "target_identifiers": None,
                        "status": PathExecutionStatus.ERROR.value,
                        "message": f"Mapping failed due to error: {e}",
                        # Add error details if possible/safe
                        "confidence_score": 0.0,
                        "mapping_direction": None,
                    }
                    error_count += 1
            self.logger.warning(f"Returning partial results due to error. {error_count} inputs potentially affected.")
            return final_results
            
        except Exception as e:
            self.logger.exception("Unhandled exception during mapping execution.")
            # Re-raise as a generic mapping error? Or return error structure?
            # For now, return error structure for all non-processed IDs
            final_results = {**successful_mappings}
            error_count = 0
            for input_id in original_input_ids_set:
                if input_id not in processed_ids:
                    final_results[input_id] = {
                        "source_identifier": input_id,
                        "target_identifiers": None,
                        "status": PathExecutionStatus.ERROR.value,
                        "message": f"Unexpected error during mapping: {e}",
                        "confidence_score": 0.0,
                        "mapping_direction": None,
                    }
                    error_count += 1
            self.logger.error(f"Unhandled exception affected {error_count} inputs.")
            return final_results
            
        finally:
            # Update session log upon completion (success, partial, or handled failure)
            if 'mapping_session_id' in locals() and mapping_session_id:
                status = PathExecutionStatus.SUCCESS
                if 'final_results' in locals():
                    # Check for error status - use string literals since we need to compare with string values
                    # PathExecutionStatus.FAILURE.value is the proper way to check error status
                    if any(r.get("status") == "failure" for r in final_results.values()):
                        status = PathExecutionStatus.PARTIAL_SUCCESS
                elif 'e' in locals():
                    status = PathExecutionStatus.FAILURE
                    
                # Calculate overall execution metrics
                overall_end_time = time.time()
                total_execution_time = overall_end_time - overall_start_time
                
                # Count results
                results_count = len([r for r in final_results.values() if r.get("target_identifiers")])
                
                # Calculate unmapped count here to ensure it's always defined
                unmapped_count = 0
                if 'original_input_ids_set' in locals() and 'processed_ids' in locals():
                    # If both variables are defined, calculate unmapped count properly
                    unmapped_count = len(original_input_ids_set) - len(processed_ids)
                elif 'original_input_ids_set' in locals() and 'final_results' in locals():
                    # Alternative calculation if processed_ids is not available but final_results is
                    unmapped_count = len(original_input_ids_set) - results_count
                
                execution_metrics = {
                    "source_endpoint": source_endpoint_name,
                    "target_endpoint": target_endpoint_name,
                    "input_count": len(original_input_ids_set) if 'original_input_ids_set' in locals() else 0,
                    "result_count": results_count,
                    "unmapped_count": unmapped_count,
                    "success_rate": (results_count / len(original_input_ids_set) * 100) if 'original_input_ids_set' in locals() and original_input_ids_set else 0,
                    "total_execution_time": total_execution_time,
                    "batch_size": batch_size,
                    "max_concurrent_batches": max_concurrent_batches,
                    "try_reverse_mapping": try_reverse_mapping,
                    "mapping_direction": mapping_direction,
                    "start_time": overall_start_time,
                    "end_time": overall_end_time
                }
                
                # Log overall execution metrics
                self.logger.info(
                    f"Mapping execution completed in {total_execution_time:.3f}s: "
                    f"{results_count}/{execution_metrics['input_count']} successful "
                    f"({execution_metrics['success_rate']:.1f}%), "
                    f"{execution_metrics['unmapped_count']} unmapped"
                )
                
                # Track performance metrics if enabled
                if enable_metrics:
                    try:
                        await self.track_mapping_metrics("mapping_execution", execution_metrics)
                        
                        # Also save performance metrics to database
                        if mapping_session_id:
                            await self._save_metrics_to_database(mapping_session_id, "mapping_execution", execution_metrics)
                    except Exception as e:
                        self.logger.warning(f"Error tracking metrics: {str(e)}")
                
                await self._update_mapping_session_log(
                    mapping_session_id, 
                    status=status,
                    end_time=get_current_utc_time(),
                    results_count=results_count,
                    error_message=str(e) if 'e' in locals() else None
                )
            else:
                self.logger.error("mapping_session_id not defined, cannot update session log.")

    async def _execute_path(
        self,
        session: AsyncSession, # Pass meta session
        path: Union[MappingPath, "ReversiblePath"],
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None,
        batch_size: int = 250,
        max_hop_count: Optional[int] = None,
        filter_confidence: float = 0.0,
        max_concurrent_batches: int = 5
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Execute a mapping path or its reverse, with optimized batched processing.
        
        Args:
            session: Database session
            path: The path to execute
            input_identifiers: List of identifiers to map
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            mapping_session_id: Optional ID for the mapping session
            batch_size: Size of batches for processing large input sets
            max_hop_count: Maximum number of hops to allow (skip longer paths)
            filter_confidence: Minimum confidence threshold for results
            max_concurrent_batches: Maximum number of batches to process concurrently
            
        Returns:
            Dictionary mapping input identifiers to their results
        """
        # Skip execution if max_hop_count is specified and this path exceeds it
        path_hop_count = len(path.steps) if hasattr(path, "steps") and path.steps else 1
        if max_hop_count is not None and path_hop_count > max_hop_count:
            self.logger.info(f"Skipping path {path.id} with {path_hop_count} hops (exceeds max_hop_count of {max_hop_count})")
            return {input_id: {
                "source_identifier": input_id,
                "target_identifiers": None,
                "status": PathExecutionStatus.SKIPPED.value,
                "message": f"Path skipped (hop count {path_hop_count} exceeds max_hop_count {max_hop_count})",
                "path_id": path.id,
                "path_name": path.name,
                "is_reverse": getattr(path, "is_reverse", False),
                "hop_count": path_hop_count,
                "mapping_direction": "reverse" if getattr(path, "is_reverse", False) else "forward",
                "confidence_score": 0.0
            } for input_id in input_identifiers}
            
        # Add performance tracking
        execution_start_time = time.time()
        metrics = {
            "path_id": path.id,
            "input_count": len(input_identifiers),
            "batch_size": batch_size,
            "max_concurrent_batches": max_concurrent_batches,
            "is_reverse": getattr(path, "is_reverse", False),
            "start_time": execution_start_time,
            "processing_times": {},
            "success_count": 0,
            "error_count": 0,
            "filtered_count": 0
        }
        
        self.logger.debug(f"Executing path {path.id} for {len(input_identifiers)} IDs with batch_size={batch_size}")
        
        # Convert input to a list (needed for batching)
        input_ids_list = list(set(input_identifiers))  # Deduplicate while preserving order
        
        # Create batches for processing
        batches = [input_ids_list[i:i+batch_size] for i in range(0, len(input_ids_list), batch_size)]
        self.logger.debug(f"Split {len(input_ids_list)} identifiers into {len(batches)} batches")
        
        # Initialize results dictionary to store combined results
        combined_results = {}
        
        # Create a semaphore to limit concurrent batch processing
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        # Define batch processing function with performance tracking
        async def process_batch(batch_index: int, batch_ids: List[str]):
            async with semaphore:
                batch_start_time = time.time()
                batch_metrics = {
                    "start_time": batch_start_time,
                    "batch_size": len(batch_ids),
                    "success_count": 0,
                    "error_count": 0,
                    "filtered_count": 0
                }
                
                self.logger.debug(f"Processing batch {batch_index+1}/{len(batches)} with {len(batch_ids)} identifiers")
                batch_set = set(batch_ids)
                
                try:
                    # Start timing the path execution
                    path_execution_start = get_current_utc_time()
                    
                    # Execute path steps directly for this batch
                    is_reverse_execution = getattr(path, 'is_reverse', False)
                    self.logger.debug(f"Executing {'reverse' if is_reverse_execution else 'forward'} path {path.id}")
                    
                    # Start with the initial input identifiers
                    current_input_ids = batch_set
                    # Dict to track execution progress: input_id -> {final_ids: List[str], provenance: List[Dict]}
                    execution_progress = {input_id: {
                        'final_ids': [],
                        'provenance': [{
                            'path_id': path.id,
                            'path_name': getattr(path, 'name', f"Path-{path.id}"),
                            'steps_details': []
                        }]
                    } for input_id in batch_ids}
                    
                    # Get the steps to execute (in correct order based on direction)
                    steps_to_execute = path.steps
                    if is_reverse_execution and hasattr(path, 'steps') and path.steps:
                        # For reverse paths, execute steps in reverse order
                        steps_to_execute = list(reversed(path.steps))
                    
                    # Track unique identifiers at each step to avoid duplicates
                    step_input_ids = set(current_input_ids)
                    
                    # Execute each step in the path
                    for step_index, step in enumerate(steps_to_execute):
                        step_start_time = time.time()
                        step_id = step.id if hasattr(step, 'id') else f"step_{step_index}"
                        step_name = step.name if hasattr(step, 'name') else f"Step {step_index}"
                        self.logger.debug(f"Executing step {step_id} ({step_name}) with {len(step_input_ids)} input IDs")
                        
                        if not step_input_ids:
                            self.logger.debug(f"No input IDs for step {step_id} - skipping")
                            break
                        
                        try:
                            # Execute the mapping step with the current set of input IDs
                            step_results = await self._execute_mapping_step(
                                step=step,
                                input_values=list(step_input_ids),
                                is_reverse=is_reverse_execution
                            )
                            
                            # Track which original inputs connect to which outputs through this step
                            # and update provenance information
                            next_step_input_ids = set()
                            
                            # Go through all original input IDs still in the execution path
                            for original_input_id, progress_data in execution_progress.items():
                                current_progress = progress_data.copy()
                                
                                # For the first step, the input ID will be one of our original batch IDs
                                # For subsequent steps, we need to trace through previous mappings
                                if step_index == 0:
                                    if original_input_id in step_results:
                                        # Direct result for this original input ID
                                        mapped_ids, source_component = step_results[original_input_id]
                                        
                                        if mapped_ids:  # If mapping was successful
                                            # Add the mapped IDs to the next step's inputs
                                            next_step_input_ids.update(mapped_ids)
                                            
                                            # If this is the last step, these are our final results for this input
                                            if len(steps_to_execute) == 1:
                                                current_progress['final_ids'] = mapped_ids
                                            
                                            # Add step details to provenance
                                            step_detail = {
                                                'step_id': step_id,
                                                'step_name': step_name,
                                                'resource_id': step.mapping_resource.id, # Changed to .id
                                                'client_name': getattr(step, 'client_name', 'Unknown'),
                                                'input_ids': [original_input_id],
                                                'output_ids': mapped_ids,
                                                'resolved_historical': False,  # This would need to be set based on actual resolution
                                                'execution_time': time.time() - step_start_time
                                            }
                                            current_progress['provenance'][0]['steps_details'].append(step_detail)
                                            execution_progress[original_input_id] = current_progress
                                else:
                                    # For subsequent steps, we need to check if any of our previous output IDs
                                    # are inputs to the current step
                                    if 'provenance' in current_progress and current_progress['provenance']:
                                        previous_step_detail = current_progress['provenance'][0]['steps_details'][-1] if current_progress['provenance'][0]['steps_details'] else None
                                        
                                        if previous_step_detail and 'output_ids' in previous_step_detail:
                                            previous_output_ids = previous_step_detail['output_ids']
                                            
                                            # Check if any of our previous outputs were mapped in this step
                                            all_mapped_ids = []
                                            input_ids_for_step = []
                                            
                                            for prev_output_id in previous_output_ids:
                                                if prev_output_id in step_results:
                                                    # This previous output was mapped in this step
                                                    mapped_ids, source_component = step_results[prev_output_id]
                                                    
                                                    if mapped_ids:  # If mapping was successful
                                                        # Add to our running list for this original input
                                                        all_mapped_ids.extend(mapped_ids)
                                                        next_step_input_ids.update(mapped_ids)
                                                        input_ids_for_step.append(prev_output_id)
                                            
                                            # If we got any mappings for this original input in this step
                                            if all_mapped_ids:
                                                # If this is the last step, these are our final results
                                                if step_index == len(steps_to_execute) - 1:
                                                    current_progress['final_ids'] = all_mapped_ids
                                                
                                                # Add step details to provenance
                                                step_detail = {
                                                    'step_id': step_id,
                                                    'step_name': step_name,
                                                    'resource_id': step.mapping_resource.id, # Changed to .id
                                                    'client_name': getattr(step, 'client_name', 'Unknown'),
                                                    'input_ids': input_ids_for_step,
                                                    'output_ids': all_mapped_ids, 
                                                    'resolved_historical': False,  # Would need to be set based on actual resolution
                                                    'execution_time': time.time() - step_start_time
                                                }
                                                current_progress['provenance'][0]['steps_details'].append(step_detail)
                                                execution_progress[original_input_id] = current_progress
                            
                            # Update the input IDs for the next step
                            step_input_ids = next_step_input_ids
                            
                            self.logger.debug(f"Step {step_id} completed with {len(next_step_input_ids)} output IDs")
                            
                        except Exception as e:
                            self.logger.error(f"Error executing step {step_id}: {str(e)}", exc_info=True)
                            # We continue with the next step to see if partial results can be obtained
                    
                    # Now execution_progress contains our raw results
                    raw_results = execution_progress
                    
                    # Transform the results
                    batch_results = {}
                    for original_id, result_data in raw_results.items():
                        if not result_data or not result_data.get('final_ids'):
                            # No mapping found for this ID
                            continue
                        
                        # Extract the final mapped IDs
                        final_ids = result_data.get('final_ids', [])
                        
                        # Get provenance data (first entry if multiple exist)
                        provenance = result_data.get('provenance', [{}])[0]
                        
                        # Extract path details from provenance
                        path_id = provenance.get('path_id')
                        path_name = provenance.get('path_name')
                        steps_details = provenance.get('steps_details', [])
                        
                        # Check if any step involved historical ID resolution
                        resolved_historical = any(
                            step.get('resolved_historical', False) 
                            for step in steps_details
                        )
                        
                        # Calculate hop count (number of steps)
                        hop_count = len(steps_details)
                        
                        # Determine mapping direction
                        mapping_direction = "reverse" if getattr(path, 'is_reverse', False) else "forward"
                        
                        # Get detailed path step information for confidence calculation
                        path_step_details = {}
                        for i, step in enumerate(steps_details):
                            path_step_details[str(i)] = {
                                "resource_id": step.get("resource_id"),
                                "resource_name": step.get("client_name", ""),
                                "resolved_historical": step.get("resolved_historical", False)
                            }
                        
                        # Calculate confidence score
                        confidence_score = self._calculate_confidence_score(
                            {}, 
                            hop_count, 
                            getattr(path, 'is_reverse', False),
                            path_step_details
                        )
                        
                        self.logger.debug(f"Source: {original_id}, Hops: {hop_count}, Reversed: {getattr(path, 'is_reverse', False)}, Confidence: {confidence_score}")
                        
                        # Create mapping path details
                        mapping_path_details = self._create_mapping_path_details(
                            path_id=path_id,
                            path_name=path_name,
                            hop_count=hop_count,
                            mapping_direction=mapping_direction,
                            path_step_details=path_step_details,
                            additional_metadata={
                                "resolved_historical": resolved_historical,
                                "confidence_score": confidence_score,
                                "source_ontology": source_ontology,
                                "target_ontology": target_ontology
                            }
                        )
                        
                        # Build the result structure
                        batch_results[original_id] = {
                            "source_identifier": original_id,
                            "target_identifiers": final_ids,
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": f"Successfully mapped via path: {path_name}",
                            "confidence_score": confidence_score,
                            "mapping_path_details": mapping_path_details,
                            "hop_count": hop_count,
                            "mapping_direction": mapping_direction,
                            "mapping_source": self._determine_mapping_source(path_step_details)
                        }
                    
                    return batch_results
                    
                except Exception as e:
                    # Record batch error in metrics
                    batch_metrics["error_count"] = len(batch_ids)
                    metrics["error_count"] += len(batch_ids)
                    batch_metrics["error"] = str(e)
                    batch_metrics["error_type"] = type(e).__name__
                    
                    error_time = time.time()
                    batch_metrics["total_time"] = error_time - batch_start_time
                    metrics["processing_times"][f"batch_{batch_index}"] = batch_metrics
                    
                    self.logger.error(f"Error executing batch {batch_index+1} of path {path.id}: {str(e)}", exc_info=True)
                    # Return failed results for each ID in this batch
                    return {input_id: {
                        "source_identifier": input_id,
                        "target_identifiers": None,
                        "status": PathExecutionStatus.EXECUTION_ERROR.value,
                        "message": f"Error during path execution: {str(e)}",
                        "confidence_score": 0.0,
                        "mapping_direction": "reverse" if getattr(path, "is_reverse", False) else "forward",
                        "error_details": {
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    } for input_id in batch_ids}
                
                finally:
                    # Record batch completion metrics regardless of success/failure
                    batch_end_time = time.time()
                    batch_metrics["total_time"] = batch_end_time - batch_start_time
                    metrics["processing_times"][f"batch_{batch_index}"] = batch_metrics
        
        # Process batches concurrently
        batch_tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        batch_results_list = await asyncio.gather(*batch_tasks)
        
        # Combine all batch results
        for batch_result in batch_results_list:
            if batch_result:
                combined_results.update(batch_result)
        
        # Add error entries for any IDs not found in results
        missing_ids = 0
        for input_id in input_identifiers:
            if input_id not in combined_results:
                missing_ids += 1
                combined_results[input_id] = {
                    "source_identifier": input_id,
                    "target_identifiers": None,
                    "status": PathExecutionStatus.NO_MAPPING_FOUND.value,
                    "message": f"No mapping found via path: {path.name}",
                    "confidence_score": 0.0,
                    "mapping_direction": "reverse" if getattr(path, 'is_reverse', False) else "forward",
                    "path_id": path.id,
                    "path_name": path.name
                }
        
        # Record final execution metrics
        execution_end_time = time.time()
        total_execution_time = execution_end_time - execution_start_time
        
        metrics["end_time"] = execution_end_time
        metrics["total_execution_time"] = total_execution_time
        metrics["missing_ids"] = missing_ids
        metrics["result_count"] = len(combined_results)
        
        # Log performance metrics
        success_rate = (metrics["success_count"] / len(input_identifiers) * 100) if input_identifiers else 0
        self.logger.info(
            f"Path {path.id} execution completed in {total_execution_time:.3f}s: "
            f"{metrics['success_count']}/{len(input_identifiers)} successful ({success_rate:.1f}%), "
            f"{metrics['error_count']} errors, {metrics['filtered_count']} filtered"
        )
        
        # If configured, send metrics to monitoring system
        if hasattr(self, "metrics_tracker") and callable(getattr(self, "track_mapping_metrics", None)):
            try:
                await self.track_mapping_metrics("path_execution", metrics)
            except Exception as e:
                self.logger.warning(f"Failed to track metrics: {str(e)}")
        
        return combined_results

    async def _reconcile_bidirectional_mappings(
        self,
        forward_mappings: Dict[str, Dict[str, Any]],
        reverse_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich forward mappings with bidirectional validation status.
        
        Instead of filtering, this adds validation status information to each mapping
        that succeeded in the primary S->T direction.
        
        Args:
            forward_mappings: Dictionary of source_id -> mapping_result from forward mapping
            reverse_results: Dictionary of target_id -> reverse_mapping_result from reverse mapping
            
        Returns:
            Dictionary of enriched source_id -> mapping_result with validation status added
        """
        validated_count = 0
        unidirectional_count = 0
        
        target_to_sources = {} # Stores target_id -> set of all source_ids it can reverse map to
        for target_id, rev_res_item in reverse_results.items():
            if rev_res_item and rev_res_item.get("target_identifiers"):
                all_reverse_mapped_to_source_ids = set(rev_res_item["target_identifiers"])
                
                # Handle Arivale ID components in reverse mapped IDs
                # If client returns "INF_P12345", ensure "P12345" is also considered.
                current_set_copy = set(all_reverse_mapped_to_source_ids) # Iterate over a copy
                for rs_id in current_set_copy:
                    if any(rs_id.startswith(p) for p in ('INF_', 'CAM_', 'CVD_', 'CVD2_', 'DEV_')):
                        parts = rs_id.split('_', 1)
                        if len(parts) > 1:
                            all_reverse_mapped_to_source_ids.add(parts[1]) # Add the UniProt part
            
                target_to_sources[target_id] = all_reverse_mapped_to_source_ids
    
        enriched_mappings = {}
        for source_id, fwd_res_item in forward_mappings.items():
            enriched_result = fwd_res_item.copy()
            
            if not fwd_res_item or not fwd_res_item.get("target_identifiers"):
                enriched_result["validation_status"] = "Successful (NoFwdTarget)"
                unidirectional_count += 1
            else:
                forward_mapped_target_ids = fwd_res_item["target_identifiers"]
                current_status_for_source = None

                for target_id_from_fwd_map in forward_mapped_target_ids:
                    if target_id_from_fwd_map in target_to_sources: # This forward target has reverse mapping data
                        all_possible_reverse_sources_for_target = target_to_sources[target_id_from_fwd_map]
                        
                        if source_id in all_possible_reverse_sources_for_target: # Original source_id is among them
                            primary_reverse_mapped_id = reverse_results.get(target_id_from_fwd_map, {}).get("mapped_value")
                            
                            # Normalize primary_reverse_mapped_id if it's an Arivale ID
                            normalized_primary_reverse_id = primary_reverse_mapped_id
                            if primary_reverse_mapped_id and any(primary_reverse_mapped_id.startswith(p) for p in ('INF_', 'CAM_', 'CVD_', 'CVD2_', 'DEV_')):
                                parts = primary_reverse_mapped_id.split('_', 1)
                                if len(parts) > 1:
                                    normalized_primary_reverse_id = parts[1]

                            if normalized_primary_reverse_id == source_id:
                                current_status_for_source = "Validated"
                            else:
                                current_status_for_source = "Validated (Ambiguous)"
                            break # Found validation status for this source_id
            
                if current_status_for_source:
                    enriched_result["validation_status"] = current_status_for_source
                    validated_count += 1
                else: # No validation path found to the original source_id
                    any_fwd_target_had_reverse_data = any(tid in target_to_sources for tid in forward_mapped_target_ids)
                    if any_fwd_target_had_reverse_data:
                        enriched_result["validation_status"] = "Successful"
                    else:
                        enriched_result["validation_status"] = "Successful (NoReversePath)"
                    unidirectional_count += 1
            
            # Add this entry to the enriched_mappings dictionary
            enriched_mappings[source_id] = enriched_result
    
        self.logger.info(
            f"Validation status: {validated_count} validated (bidirectional), "
            f"{unidirectional_count} successful (one-directional only)"
        )
        return enriched_mappings

    async def track_mapping_metrics(self, event_type: str, metrics: Dict[str, Any]) -> None:
        """
        Track mapping metrics for performance monitoring.
        
        This method integrates with external monitoring systems like Langfuse, Prometheus, etc.
        It can be overridden in subclasses to provide different implementations.
        
        Args:
            event_type: The type of event being tracked (e.g., path_execution, batch_processing)
            metrics: A dictionary containing metrics to track
        """
        # If Langfuse tracking is enabled, send metrics there
        if hasattr(self, "_langfuse_tracker") and self._langfuse_tracker:
            try:
                # If this is a path execution event, create a trace
                if event_type == "path_execution":
                    trace_id = f"path_{metrics['path_id']}_{int(metrics['start_time'])}"
                    
                    # Create a trace for the entire path execution
                    trace = self._langfuse_tracker.trace(
                        name="path_execution",
                        id=trace_id,
                        metadata={
                            "path_id": metrics.get("path_id"),
                            "is_reverse": metrics.get("is_reverse", False),
                            "input_count": metrics.get("input_count", 0),
                            "batch_size": metrics.get("batch_size", 0),
                            "max_concurrent_batches": metrics.get("max_concurrent_batches", 1)
                        }
                    )
                    
                    # Add spans for each batch
                    for batch_key, batch_metrics in metrics.get("processing_times", {}).items():
                        batch_span = trace.span(
                            name=f"batch_{batch_key}",
                            start_time=datetime.fromtimestamp(batch_metrics.get("start_time", 0)),
                            end_time=datetime.fromtimestamp(batch_metrics.get("start_time", 0) + batch_metrics.get("total_time", 0)),
                            metadata={
                                "batch_size": batch_metrics.get("batch_size", 0),
                                "success_count": batch_metrics.get("success_count", 0),
                                "error_count": batch_metrics.get("error_count", 0),
                                "filtered_count": batch_metrics.get("filtered_count", 0)
                            }
                        )
                        
                        if "error" in batch_metrics:
                            batch_span.add_observation(
                                name="error",
                                value=batch_metrics["error"],
                                metadata={"error_type": batch_metrics.get("error_type", "unknown")}
                            )
                            
                    # Add summary metrics
                    trace.update(
                        metadata={
                            "total_execution_time": metrics.get("total_execution_time", 0),
                            "success_count": metrics.get("success_count", 0),
                            "error_count": metrics.get("error_count", 0),
                            "filtered_count": metrics.get("filtered_count", 0),
                            "missing_ids": metrics.get("missing_ids", 0),
                            "result_count": metrics.get("result_count", 0)
                        }
                    )
                    
                self.logger.debug(f"Sent '{event_type}' metrics to monitoring system")
            except Exception as e:
                self.logger.warning(f"Failed to send metrics to monitoring system: {str(e)}")
                
        # Additional monitoring systems could be integrated here
        
    async def _save_metrics_to_database(self, session_id: int, metric_type: str, metrics: Dict[str, Any]) -> None:
        """
        Save performance metrics to the database for analysis and reporting.
        
        Args:
            session_id: ID of the MappingSession
            metric_type: Type of metrics being saved
            metrics: Dictionary of metrics to save
        """
        try:
            async with self.async_cache_session() as session:
                # Update session-level metrics if appropriate
                if metric_type == "mapping_execution":
                    mapping_session = await session.get(MappingSession, session_id)
                    if mapping_session:
                        mapping_session.batch_size = metrics.get("batch_size")
                        mapping_session.max_concurrent_batches = metrics.get("max_concurrent_batches")
                        mapping_session.total_execution_time = metrics.get("total_execution_time")
                        mapping_session.success_rate = metrics.get("success_rate")
                
                # Save detailed metrics
                for metric_name, metric_value in metrics.items():
                    # Skip non-numeric metrics or complex objects
                    if isinstance(metric_value, (dict, list)):
                        continue
                        
                    metric_entry = ExecutionMetric(
                        mapping_session_id=session_id,
                        metric_type=metric_type,
                        metric_name=metric_name,
                        timestamp=datetime.utcnow()
                    )
                    
                    # Set the appropriate value field based on type
                    if isinstance(metric_value, (int, float)):
                        metric_entry.metric_value = float(metric_value)
                    elif metric_value is not None:
                        metric_entry.string_value = str(metric_value)
                        
                    session.add(metric_entry)
                    
                await session.commit()
                self.logger.debug(f"Saved {len(metrics)} metrics to database for session {session_id}")
                
        except Exception as e:
            self.logger.warning(f"Failed to save metrics to database: {str(e)}")
            # Don't raise the exception - we don't want to fail the mapping process due to metrics errors

    async def _create_mapping_session_log(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        source_property_name: str,
        target_property_name: str,
        use_cache: bool,
        try_reverse_mapping: bool,
        input_count: int,
        max_cache_age_days: Optional[int] = None,
    ) -> int:
        """Create a new mapping session log entry."""
        try:
            async with self.async_cache_session() as cache_session:
                now = get_current_utc_time()
                
                # Create parameters JSON
                parameters = json.dumps({
                    "source_property_name": source_property_name,
                    "target_property_name": target_property_name,
                    "use_cache": use_cache,
                    "try_reverse_mapping": try_reverse_mapping,
                    "input_count": input_count,
                    "max_cache_age_days": max_cache_age_days,
                })
                
                log_entry = MappingSession(
                    source_endpoint=source_endpoint_name,
                    target_endpoint=target_endpoint_name,
                    parameters=parameters,
                    start_time=now,
                    status="running"
                )
                cache_session.add(log_entry)
                await cache_session.flush()  # Ensure ID is generated
                await cache_session.commit() # Commit to make it visible to other sessions
                return log_entry.id
        except SQLAlchemyError as e:
            self.logger.error(f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Cache storage error creating mapping session log. (original_exception={type(e).__name__}: {e})", exc_info=True)
            raise CacheStorageError(
                f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Failed to create mapping session log entry. (original_exception={type(e).__name__}: {e})",
                details={
                    "source_endpoint": source_endpoint_name,
                    "target_endpoint": target_endpoint_name,
                    "input_count": input_count,
                },
            ) from e

    async def _update_mapping_session_log(
        self,
        session_id: int,
        status: PathExecutionStatus,
        end_time: datetime,
        results_count: int = 0,
        error_message: Optional[str] = None,
    ):
        """Update the status and end time of a mapping session log."""
        try:
            async with self.async_cache_session() as cache_session:
                log_entry = await cache_session.get(MappingSession, session_id)
                if log_entry:
                    log_entry.status = status.value if isinstance(status, PathExecutionStatus) else status
                    log_entry.end_time = end_time
                    log_entry.results_count = results_count
                    if error_message:
                        log_entry.error_message = error_message
                    await cache_session.commit()
                    self.logger.info(f"Updated mapping session log ID {session_id} with status {status}")
                else:
                    self.logger.warning(f"Mapping session log ID {session_id} not found for update.")
        except SQLAlchemyError as e:
            self.logger.error(f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Cache storage error updating mapping session log. (original_exception={type(e).__name__}: {e})", exc_info=True)
            raise CacheStorageError(
                f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Failed to update mapping session log entry. (original_exception={type(e).__name__}: {e})",
                details={"session_id": session_id},
            ) from e
            
    def _calculate_confidence_score(
        self, 
        result: Dict[str, Any], 
        hop_count: Optional[int], 
        is_reversed: bool, 
        path_step_details: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score based on mapping characteristics.
        
        The confidence score is determined by:
        1. Existing score in the result (if provided)
        2. Number of hops in the mapping path
        3. Whether the path was executed in reverse
        4. Type of mapping resources used (e.g., direct API vs RAG)
        
        Args:
            result: The mapping result dictionary
            hop_count: Number of steps in the mapping path
            is_reversed: Whether the path was executed in reverse
            path_step_details: Detailed information about the path steps
            
        Returns:
            A confidence score between 0.0 and 1.0
        """
        # Check if result already has a confidence score
        if result.get("confidence_score") is not None:
            return result["confidence_score"]
        
        # Base confidence calculation from hop count
        if hop_count is not None:
            if hop_count <= 1:
                base_confidence = 0.95  # Direct mapping (highest confidence)
            elif hop_count == 2:
                base_confidence = 0.85  # 2-hop mapping (high confidence)
            else:
                # Decrease confidence for longer paths: 0.95 → 0.85 → 0.75 → 0.65 → ...
                base_confidence = max(0.15, 0.95 - ((hop_count - 1) * 0.1))
        else:
            base_confidence = 0.7  # Default if hop_count is unknown
        
        # Apply penalty for reverse paths
        if is_reversed:
            base_confidence = max(0.1, base_confidence - 0.1)
        
        # Apply additional adjustments based on resource types
        resource_types = []
        for step_key, step_info in path_step_details.items():
            if not isinstance(step_info, dict):
                continue
                
            # Check resource name for clues
            resource_name = step_info.get("resource_name", "").lower()
            client_path = step_info.get("resource_client", "").lower()
            
            # Determine source based on resource name or client path
            if "spoke" in resource_name or "spoke" in client_path:
                resource_types.append("spoke")
            elif "rag" in resource_name or "rag" in client_path:
                resource_types.append("rag")
            elif "llm" in resource_name or "llm" in client_path:
                resource_types.append("llm")
            elif "ramp" in resource_name or "ramp" in client_path:
                resource_types.append("ramp")
                
        # Apply adjustments for specific resources
        if "rag" in resource_types:
            base_confidence = max(0.1, base_confidence - 0.05)  # Small penalty for RAG-based mappings
        if "llm" in resource_types:
            base_confidence = max(0.1, base_confidence - 0.1)   # Larger penalty for LLM-based mappings
        
        return round(base_confidence, 2)  # Round to 2 decimal places for consistency
    
    def _create_mapping_path_details(
        self,
        path_id: int,
        path_name: str,
        hop_count: Optional[int],
        mapping_direction: str,
        path_step_details: Dict[str, Any],
        log_id: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a structured mapping_path_details JSON with complete path information.
        
        Args:
            path_id: The ID of the mapping path
            path_name: The name of the mapping path
            hop_count: Number of steps in the path
            mapping_direction: Direction of the mapping (forward, reverse, bidirectional)
            path_step_details: Detailed information about the path steps
            log_id: Optional ID of the execution log entry
            additional_metadata: Optional additional metadata to include
            
        Returns:
            A dictionary with structured path details ready to be serialized to JSON
        """
        # Initialize details with core information
        details = {
            "path_id": path_id,
            "path_name": path_name,
            "hop_count": hop_count,
            "direction": mapping_direction,
            "log_id": log_id,
            "execution_timestamp": datetime.utcnow().isoformat(),
            "steps": {}
        }
        
        # Add step details if available
        if path_step_details:
            details["steps"] = path_step_details
        
        # Add any additional metadata
        if additional_metadata:
            details["additional_metadata"] = additional_metadata
            
        return details
    
    def _determine_mapping_source(self, path_step_details: Dict[str, Any]) -> str:
        """
        Determine the mapping source based on the path steps.
        
        Args:
            path_step_details: Detailed information about the path steps
            
        Returns:
            A string indicating the mapping source (api, spoke, rag, etc.)
        """
        # Default source if we can't determine
        default_source = "api"
        
        # Check for empty details
        if not path_step_details:
            return default_source
            
        # Check each step for resource type clues
        for step_key, step_info in path_step_details.items():
            if not isinstance(step_info, dict):
                continue
                
            # Check resource name for clues
            resource_name = step_info.get("resource_name", "").lower()
            client_path = step_info.get("resource_client", "").lower()
            
            # Determine source based on resource name or client path
            if "spoke" in resource_name or "spoke" in client_path:
                return "spoke"
            elif "rag" in resource_name or "rag" in client_path:
                return "rag"
            elif "llm" in resource_name or "llm" in client_path:
                return "llm"
            elif "ramp" in resource_name or "ramp" in client_path:
                return "ramp"
                
        return default_source

    async def _reconcile_bidirectional_mappings(
        self,
        forward_mappings: Dict[str, Dict[str, Any]],
        reverse_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich forward mappings with bidirectional validation status.
        
        Instead of filtering, this adds validation status information to each mapping
        that succeeded in the primary S->T direction.
        
        Args:
            forward_mappings: Dictionary of source_id -> mapping_result from forward mapping
            reverse_results: Dictionary of target_id -> reverse_mapping_result from reverse mapping
            
        Returns:
            Dictionary of enriched source_id -> mapping_result with validation status added
        """
        validated_count = 0
        unidirectional_count = 0
        
        target_to_sources = {} # Stores target_id -> set of all source_ids it can reverse map to
        for target_id, rev_res_item in reverse_results.items():
            if rev_res_item and rev_res_item.get("target_identifiers"):
                all_reverse_mapped_to_source_ids = set(rev_res_item["target_identifiers"])
                
                # Handle Arivale ID components in reverse mapped IDs
                # If client returns "INF_P12345", ensure "P12345" is also considered.
                current_set_copy = set(all_reverse_mapped_to_source_ids) # Iterate over a copy
                for rs_id in current_set_copy:
                    if any(rs_id.startswith(p) for p in ('INF_', 'CAM_', 'CVD_', 'CVD2_', 'DEV_')):
                        parts = rs_id.split('_', 1)
                        if len(parts) > 1:
                            all_reverse_mapped_to_source_ids.add(parts[1]) # Add the UniProt part
            
                target_to_sources[target_id] = all_reverse_mapped_to_source_ids
    
        enriched_mappings = {}
        for source_id, fwd_res_item in forward_mappings.items():
            enriched_result = fwd_res_item.copy()
            
            if not fwd_res_item or not fwd_res_item.get("target_identifiers"):
                enriched_result["validation_status"] = "Successful (NoFwdTarget)"
                unidirectional_count += 1
            else:
                forward_mapped_target_ids = fwd_res_item["target_identifiers"]
                current_status_for_source = None

                for target_id_from_fwd_map in forward_mapped_target_ids:
                    if target_id_from_fwd_map in target_to_sources: # This forward target has reverse mapping data
                        all_possible_reverse_sources_for_target = target_to_sources[target_id_from_fwd_map]
                        
                        if source_id in all_possible_reverse_sources_for_target: # Original source_id is among them
                            primary_reverse_mapped_id = reverse_results.get(target_id_from_fwd_map, {}).get("mapped_value")
                            
                            # Normalize primary_reverse_mapped_id if it's an Arivale ID
                            normalized_primary_reverse_id = primary_reverse_mapped_id
                            if primary_reverse_mapped_id and any(primary_reverse_mapped_id.startswith(p) for p in ('INF_', 'CAM_', 'CVD_', 'CVD2_', 'DEV_')):
                                parts = primary_reverse_mapped_id.split('_', 1)
                                if len(parts) > 1:
                                    normalized_primary_reverse_id = parts[1]

                            if normalized_primary_reverse_id == source_id:
                                current_status_for_source = "Validated"
                            else:
                                current_status_for_source = "Validated (Ambiguous)"
                            break # Found validation status for this source_id
            
                if current_status_for_source:
                    enriched_result["validation_status"] = current_status_for_source
                    validated_count += 1
                else: # No validation path found to the original source_id
                    any_fwd_target_had_reverse_data = any(tid in target_to_sources for tid in forward_mapped_target_ids)
                    if any_fwd_target_had_reverse_data:
                        enriched_result["validation_status"] = "Successful"
                    else:
                        enriched_result["validation_status"] = "Successful (NoReversePath)"
                    unidirectional_count += 1
            
            # Add this entry to the enriched_mappings dictionary
            enriched_mappings[source_id] = enriched_result
    
        self.logger.info(
            f"Validation status: {validated_count} validated (bidirectional), "
            f"{unidirectional_count} successful (one-directional only)"
        )
        return enriched_mappings

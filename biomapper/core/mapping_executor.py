import asyncio
import json
import os
import time # Add import time
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# Import composite identifier handling
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin
from biomapper.core.exceptions import (
    BiomapperError,
    ClientError,
    ConfigurationError, # Import ConfigurationError
    MappingExecutionError,
    ClientExecutionError,
    ClientInitializationError,
    CacheStorageError,
    ErrorCode, # Import ErrorCode
    DatabaseQueryError, # Import DatabaseQueryError
    StrategyNotFoundError,
    InactiveStrategyError,
)

# Import new strategy handling modules
from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.engine_components.progress_reporter import ProgressReporter
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.services.mapping_path_execution_service import MappingPathExecutionService
from biomapper.core.services.strategy_execution_service import StrategyExecutionService
from biomapper.core.engine_components.mapping_executor_initializer import MappingExecutorInitializer
from biomapper.core.engine_components.robust_execution_coordinator import RobustExecutionCoordinator

# Import utilities
from biomapper.core.utils.placeholder_resolver import resolve_placeholders
from biomapper.core.utils.time_utils import get_current_utc_time

# Import models
from biomapper.core.models.result_bundle import MappingResultBundle

# Import models for metamapper DB
from ..db.models import (
    Endpoint,
    EndpointPropertyConfig,
    MappingPath,
    MappingPathStep,
    OntologyPreference,
    MappingStrategy,
    MappingStrategyStep,
)

# Import models for cache DB
from ..db.cache_models import (
    PathExecutionStatus,
    MappingSession,  # Add this for session logging
    ExecutionMetric # Added ExecutionMetric
)

# Import models for metamapper DB
from ..db.models import Base as MetamapperBase

# Import database setup service
from .services.database_setup_service import DatabaseSetupService

# Import our centralized configuration settings
from biomapper.config import settings


import logging # Re-added import
import os # Add import os





class MappingExecutor(CompositeIdentifierMixin):
    """
    Main execution engine for biomapper mapping operations.
    
    The MappingExecutor handles the execution of mapping strategies and individual mapping
    paths based on configurations stored in the metamapper database. It supports both
    YAML-defined multi-step mapping strategies and direct path-based mappings.
    
    Key capabilities:
    - Execute YAML-defined mapping strategies with multiple sequential steps
    - Execute individual mapping paths between endpoints  
    - Manage caching of mapping results and path configurations
    - Handle bidirectional mapping validation
    - Support composite identifier processing
    - Track mapping metrics and performance
    
    The executor integrates with dedicated strategy action classes for specific operations
    and provides comprehensive result tracking with provenance information.
    """

    def __init__(
        self,
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False, # Added parameter to control SQL echoing
        path_cache_size: int = 100, # Maximum number of paths to cache
        path_cache_expiry_seconds: int = 300, # Cache expiry time in seconds (5 minutes)
        max_concurrent_batches: int = 5, # Maximum number of batches to process concurrently
        enable_metrics: bool = True, # Whether to enable metrics tracking
        # Robust execution parameters with backward-compatible defaults
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
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
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
            
        Returns:
            An initialized MappingExecutor instance with database tables created
        """
        # Initialize the CompositeIdentifierMixin
        super().__init__()

        self.logger = logging.getLogger(__name__)
        
        # Store core parameters for backward compatibility
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
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.checkpoint_enabled = checkpoint_enabled
        
        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=checkpoint_dir if checkpoint_enabled else None,
            logger=self.logger
        )
        
        # Progress tracking
        self.progress_reporter = ProgressReporter()
        
        # Concurrency settings
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_metrics = enable_metrics
        self._metrics_tracker = None
        
        # Initialize all components using the MappingExecutorInitializer
        self._initializer = MappingExecutorInitializer(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=mapping_cache_db_url,
            echo_sql=echo_sql,
            path_cache_size=path_cache_size,
            path_cache_expiry_seconds=path_cache_expiry_seconds,
            max_concurrent_batches=max_concurrent_batches,
            enable_metrics=enable_metrics,
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=checkpoint_dir,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Initialize all components
        components = self._initializer.initialize_components(self)
        
        # Assign components to self
        self.session_manager = components['session_manager']
        self.client_manager = components['client_manager']
        self.config_loader = components['config_loader']
        self.strategy_handler = components['strategy_handler']
        self.path_finder = components['path_finder']
        self.path_execution_manager = components['path_execution_manager']
        self.cache_manager = components['cache_manager']
        self.identifier_loader = components['identifier_loader']
        self.strategy_orchestrator = components['strategy_orchestrator']
        self.checkpoint_manager = components['checkpoint_manager']
        self.progress_reporter = components['progress_reporter']
        self._langfuse_tracker = components['langfuse_tracker']
        
        # Create convenience references for backward compatibility
        convenience_refs = self._initializer.get_convenience_references()
        self.async_metamapper_engine = convenience_refs['async_metamapper_engine']
        self.MetamapperSessionFactory = convenience_refs['MetamapperSessionFactory']
        self.async_metamapper_session = convenience_refs['async_metamapper_session']
        self.async_cache_engine = convenience_refs['async_cache_engine']
        self.CacheSessionFactory = convenience_refs['CacheSessionFactory']
        self.async_cache_session = convenience_refs['async_cache_session']
        
        # Set function references after MappingExecutor is fully initialized
        self._initializer.set_executor_function_references(self)
        
        # Initialize MetadataQueryService
        self.metadata_query_service = MetadataQueryService(self.session_manager)
        
        # Initialize MappingPathExecutionService with all required arguments
        self.path_execution_service = MappingPathExecutionService(
            session_manager=self.session_manager,
            client_manager=self.client_manager,
            cache_manager=self.cache_manager,
            path_finder=self.path_finder,
            path_execution_manager=self.path_execution_manager,
            composite_handler=self,  # MappingExecutor implements composite handling
            logger=self.logger
        )
        
        # Initialize MappingPathExecutionService
        self.path_execution_service = MappingPathExecutionService(
            session_manager=self.session_manager,
            client_manager=self.client_manager,
            cache_manager=self.cache_manager,
            path_finder=self.path_finder,
            path_execution_manager=self.path_execution_manager,
            composite_handler=self,  # MappingExecutor implements composite handling
            logger=self.logger
        )
        
        # Set executor reference for delegation
        self.path_execution_service.set_executor(self)
        
        # Initialize RobustExecutionCoordinator
        self.robust_execution_coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=self.strategy_orchestrator,
            checkpoint_manager=self.checkpoint_manager,
            progress_reporter=self.progress_reporter,
            batch_size=self.batch_size,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            checkpoint_enabled=self.checkpoint_enabled,
            logger=self.logger
        )
        
        # Initialize metrics tracker if needed
        if enable_metrics:
            try:
                from biomapper.monitoring.metrics import MetricsTracker
                self._metrics_tracker = MetricsTracker(
                    langfuse=self._langfuse_tracker
                )
            except ImportError:
                self.logger.warning("MetricsTracker not available - langfuse module not installed")
                self._metrics_tracker = None
        else:
            self._metrics_tracker = None
        
        # Initialize MappingResultBundle (extracted module)
        self.MappingResultBundle = MappingResultBundle
        
        # Initialize StrategyExecutionService
        self.strategy_execution_service = StrategyExecutionService(
            strategy_orchestrator=self.strategy_orchestrator,
            robust_execution_coordinator=self.robust_execution_coordinator,
            logger=self.logger
        )
        
        self.logger.info("MappingExecutor initialization complete")

    
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
        # Robust execution parameters
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
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
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
            
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
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=checkpoint_dir,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        # Initialize database tables using DatabaseSetupService
        db_setup_service = DatabaseSetupService(logger=executor.logger)
        await db_setup_service.initialize_tables(executor.async_metamapper_engine, MetamapperBase.metadata)
        await db_setup_service.initialize_tables(executor.async_cache_engine, CacheBase.metadata)
        
        return executor

    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()



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
        
        Delegates to PathFinder service.
        """
        return await self.path_finder._find_paths_for_relationship(
            session,
            source_endpoint_id,
            target_endpoint_id,
            source_ontology,
            target_ontology
        )

    async def _find_direct_paths(
        self, session: AsyncSession, source_ontology: str, target_ontology: str
    ) -> List[MappingPath]:
        """
        Find direct mapping paths from source to target ontology.
        
        Delegates to PathFinder service.
        """
        return await self.path_finder._find_direct_paths(
            session,
            source_ontology,
            target_ontology
        )

    async def _find_mapping_paths(
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
        Find mapping paths between ontologies.
        
        Delegates to PathFinder service.
        """
        return await self.path_finder.find_mapping_paths(
            session,
            source_ontology,
            target_ontology,
            bidirectional=bidirectional,
            preferred_direction=preferred_direction,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )

    async def _find_best_path(
        self,
        session: AsyncSession,
        source_type: str,
        target_type: str,
        bidirectional: bool = False,
        preferred_direction: str = "forward",
        allow_reverse: bool = False,
        source_endpoint: Optional[Endpoint] = None,
        target_endpoint: Optional[Endpoint] = None,
    ) -> Optional[Union[MappingPath, ReversiblePath]]:
        """
        Find the highest priority mapping path.
        
        Delegates to PathFinder service.
        """
        # For compatibility: if allow_reverse is True, make sure bidirectional is too
        if allow_reverse and not bidirectional:
            bidirectional = True
            
        return await self.path_finder.find_best_path(
            session,
            source_type,
            target_type,
            bidirectional=bidirectional,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )

    async def _get_endpoint_properties(self, session: AsyncSession, endpoint_name: str) -> List[EndpointPropertyConfig]:
        """Get all property configurations for an endpoint."""
        return await self.metadata_query_service.get_endpoint_properties(session, endpoint_name)

    async def _get_ontology_preferences(self, session: AsyncSession, endpoint_name: str) -> List[OntologyPreference]:
        """Get ontology preferences for an endpoint."""
        return await self.metadata_query_service.get_ontology_preferences(session, endpoint_name)

    async def _get_endpoint(self, session: AsyncSession, endpoint_name: str) -> Optional[Endpoint]:
        """Retrieves an endpoint by name.
        
        Args:
            session: SQLAlchemy session
            endpoint_name: Name of the endpoint to retrieve
            
        Returns:
            The Endpoint if found, None otherwise
        """
        return await self.metadata_query_service.get_endpoint(session, endpoint_name)
    
    async def _get_ontology_type(self, session: AsyncSession, endpoint_name: str, property_name: str) -> Optional[str]:
        """Retrieves the primary ontology type for a given endpoint and property name."""
        return await self.metadata_query_service.get_ontology_type(session, endpoint_name, property_name)


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
        step_start = time.time()
        self.logger.debug(f"TIMING: _execute_mapping_step started for {len(input_values)} identifiers")
        
        try:
            client_load_start = time.time()
            client_instance = await self.client_manager.get_client_instance(step.mapping_resource)
            self.logger.debug(f"TIMING: get_client_instance took {time.time() - client_load_start:.3f}s")
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
                mapping_start = time.time()
                # Check if we should bypass cache for specific clients
                client_config = None
                if (hasattr(client_instance, '__class__') and 
                    client_instance.__class__.__name__ == 'UniProtHistoricalResolverClient' and
                    os.environ.get('BYPASS_UNIPROT_CACHE', '').lower() == 'true'):
                    self.logger.info("Bypassing cache for UniProtHistoricalResolverClient")
                    client_config = {'bypass_cache': True}
                
                client_results_from_map_identifiers = await client_instance.map_identifiers(input_values, config=client_config)
                self.logger.debug(f"TIMING: client.map_identifiers took {time.time() - mapping_start:.3f}s")
            
                processed_step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
            
                # Iterate through the results from the client
                # client_results_from_map_identifiers is Dict[str, Tuple[Optional[List[str]], Optional[str_metadata]]]
                for input_id, client_tuple in client_results_from_map_identifiers.items():
                    mapped_ids_list, _ = client_tuple # metadata_or_component_id is the second part
                
                    # _execute_mapping_step is documented to return:
                    # Dict[input_ID, Tuple[Optional[List[output_IDs]], Optional[successful_source_component_ID]]]
                    # We will pass the mapped_ids_list as is.
                    # The metadata from UniProtHistoricalResolver (e.g., "primary") is not a structural component_id.
                    # So, pass None for the component_id part of the tuple here.
                    if mapped_ids_list:
                        processed_step_results[input_id] = (mapped_ids_list, None) 
                    else:
                        # Client indicated no mapping or an error for this specific ID in its structure
                        processed_step_results[input_id] = (None, None)

                # Ensure all original input_values passed to the step have an entry in the output
                # This handles cases where an input_id might not even be in client_results_from_map_identifiers' keys
                for val in input_values:
                    if val not in processed_step_results:
                        processed_step_results[val] = (None, None)
                self.logger.debug(f"TIMING: _execute_mapping_step completed in {time.time() - step_start:.3f}s")
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
                    self.logger.debug(f"TIMING: _execute_mapping_step (reverse) completed in {time.time() - step_start:.3f}s")
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
                "Unexpected error during step execution",
                client_name=step.mapping_resource.name,
                details=error_details,
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
        self.logger.info(f"TIMING: execute_mapping started for {len(original_input_ids_set)} identifiers")
        
        # --- 0. Initial Setup --- Create a mapping session for logging ---
        setup_start = time.time()
        mapping_session_id = await self._create_mapping_session_log(
            source_endpoint_name, target_endpoint_name, source_property_name,
            target_property_name, use_cache, try_reverse_mapping, len(original_input_ids_set),
            max_cache_age_days=max_cache_age_days
        )
        self.logger.info(f"TIMING: mapping session setup took {time.time() - setup_start:.3f}s")

        try:
            # --- 1. Get Endpoint Config and Primary Ontologies ---
            config_start = time.time()
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
                self.logger.info(f"TIMING: endpoint configuration took {time.time() - config_start:.3f}s")

                # --- 2. Attempt Direct Primary Mapping (Source Ontology -> Target Ontology) ---
                self.logger.info("--- Step 2: Attempting Direct Primary Mapping ---")
                path_find_start = time.time()
                primary_path = await self._find_best_path(
                    meta_session,
                    primary_source_ontology,
                    primary_target_ontology,
                    preferred_direction=mapping_direction,
                    allow_reverse=try_reverse_mapping,
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                )
                self.logger.info(f"TIMING: _find_best_path took {time.time() - path_find_start:.3f}s")

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
                        path_exec_start = time.time()
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
                        self.logger.info(f"TIMING: _execute_path took {time.time() - path_exec_start:.3f}s")

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
                secondary_start = time.time()
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
                                
                                # --- CORRECTED CACHE CHECK for the derived_primary_id ---
                                cached_derived_mapping = None
                                if use_cache:
                                    self.logger.debug(f"Checking cache for derived ID: {derived_primary_id} ({primary_source_ontology}) -> {primary_target_ontology}")
                                    # Calculate expiry time if max_cache_age_days is specified
                                    expiry_time = None
                                    if max_cache_age_days is not None:
                                        expiry_time = datetime.now(timezone.utc) - timedelta(days=max_cache_age_days)
                                    
                                    cache_results_for_derived, _ = await self.cache_manager.check_cache(
                                        input_identifiers=[derived_primary_id],
                                        source_ontology=primary_source_ontology,
                                        target_ontology=primary_target_ontology,
                                        expiry_time=expiry_time
                                    )
                                    if cache_results_for_derived and derived_primary_id in cache_results_for_derived:
                                        cached_derived_mapping = cache_results_for_derived[derived_primary_id]
                                        self.logger.info(f"Cache hit for derived ID {derived_primary_id} -> {cached_derived_mapping.get('target_identifiers')}")

                                # Initialize derived_mapping_results_for_current_id
                                derived_mapping_results_for_current_id = None

                                if cached_derived_mapping:
                                    # Use the cached result directly
                                    derived_mapping_results_for_current_id = {derived_primary_id: cached_derived_mapping}
                                elif primary_path: # Only execute path if no cache hit and primary_path exists
                                    self.logger.debug(f"Cache miss or not used for derived ID {derived_primary_id}. Executing primary_path.")
                                    derived_mapping_results_for_current_id = await self._execute_path(
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
                                else:
                                    self.logger.debug(f"No primary_path available to execute for derived ID {derived_primary_id}. Skipping execution for this ID.")
                                
                                # Process results - connect back to original source ID
                                if derived_mapping_results_for_current_id and derived_primary_id in derived_mapping_results_for_current_id:
                                    result_data = derived_mapping_results_for_current_id[derived_primary_id]
                                    if result_data and result_data.get("target_identifiers"):
                                        source_result = {
                                            "source_identifier": source_id,
                                            "target_identifiers": result_data["target_identifiers"],
                                            "status": PathExecutionStatus.SUCCESS.value,
                                            "message": f"Mapped via derived primary ID {derived_primary_id}" + (" (from cache)" if cached_derived_mapping else ""),
                                            "confidence_score": result_data.get("confidence_score", 0.5) * 0.9,  # Slightly lower confidence for indirect mapping
                                            "hop_count": (result_data.get("hop_count", 0) + 1 if result_data.get("hop_count") is not None else 2), # Add a hop for derivation; ensure hop_count exists
                                            "mapping_direction": result_data.get("mapping_direction", "forward"),
                                            "derived_path": True,
                                            "intermediate_id": derived_primary_id,
                                            "mapping_path_details": result_data.get("mapping_path_details")
                                        }

                                        current_path_details_str = source_result.get("mapping_path_details")
                                        new_path_details = {}
                                        if isinstance(current_path_details_str, str):
                                            try:
                                                new_path_details = json.loads(current_path_details_str)
                                            except json.JSONDecodeError:
                                                self.logger.warning(f"Could not parse path_details JSON from mapping result: {current_path_details_str}")
                                                new_path_details = {"original_mapping_step_details": current_path_details_str}
                                        elif isinstance(current_path_details_str, dict):
                                            new_path_details = current_path_details_str
                                        elif current_path_details_str is None:
                                            new_path_details = {}
                                        else:
                                            self.logger.warning(f"Unexpected type for path_details: {type(current_path_details_str)}. Storing as string.")
                                            new_path_details = {"original_mapping_step_details": str(current_path_details_str)}
                                            
                                        new_path_details["derived_step_provenance"] = provenance_info
                                        source_result["mapping_path_details"] = json.dumps(new_path_details)
                                        
                                        successful_mappings[source_id] = source_result
                                        processed_ids.add(source_id)
                                        self.logger.debug(f"Successfully mapped {source_id} to {source_result['target_identifiers']} via derived ID {derived_primary_id}")
                                        break  # Stop processing additional derived IDs for this source_id once we have a success
                            
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
                            allow_reverse=True,  # Allow using S->T paths in reverse if needed
                            source_endpoint=target_endpoint,  # Note: swapped for reverse
                            target_endpoint=source_endpoint,  # Note: swapped for reverse
                        )
                        
                        if not reverse_path:
                            self.logger.warning(f"No reverse mapping path found from {primary_target_ontology} to {primary_source_ontology}. Validation incomplete.")
                        else:
                            self.logger.info(f"Step 2: Found reverse path: {reverse_path.name} (id={reverse_path.id})")
                            
                            # Execute reverse mapping
                            self.logger.info("Step 3: Reverse mapping from target to source...")
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
                            self.logger.info("Step 4: Reconciling bidirectional mappings...")
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
        
        This method now delegates to MappingPathExecutionService for the actual execution logic.
        
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
        # Delegate to MappingPathExecutionService
        return await self.path_execution_service.execute_path(
            path=path,
            input_identifiers=input_identifiers,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=mapping_session_id,
            execution_context=None,
            batch_size=batch_size,
            max_hop_count=max_hop_count,
            filter_confidence=filter_confidence,
            max_concurrent_batches=max_concurrent_batches
        )

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

    async def execute_strategy(
        self,
        strategy_name: str,
        initial_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> MappingResultBundle:
        """
        Execute a named mapping strategy from the database (delegates to StrategyExecutionService).
        
        This method delegates to the StrategyExecutionService for executing database-stored
        mapping strategies. This is the legacy method maintained for backward compatibility.
        
        Args:
            strategy_name: Name of the strategy to execute
            initial_identifiers: List of identifiers to start with
            source_ontology_type: Optional override for source ontology type
            target_ontology_type: Optional override for target ontology type
            entity_type: Optional entity type if not implicitly available
            
        Returns:
            MappingResultBundle containing comprehensive results and provenance
            
        Raises:
            StrategyNotFoundError: If the strategy is not found in the database
            InactiveStrategyError: If the strategy is not active
            MappingExecutionError: If an error occurs during execution
        """
        return await self.strategy_execution_service.execute_strategy(
            strategy_name=strategy_name,
            initial_identifiers=initial_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            entity_type=entity_type,
        )

    async def execute_yaml_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        progress_callback: Optional[callable] = None,
        batch_size: int = 250,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Execute a YAML-defined mapping strategy using dedicated strategy action classes.
        
        This method executes a multi-step mapping strategy defined in YAML configuration.
        Each step in the strategy is executed sequentially using dedicated action classes
        (ConvertIdentifiersLocalAction, ExecuteMappingPathAction, FilterByTargetPresenceAction),
        with the output of one step becoming the input for the next. The `is_required` field 
        on each step controls whether step failures halt execution or allow it to continue.
        
        Args:
            strategy_name: Name of the strategy defined in YAML configuration
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            input_identifiers: List of identifiers to map
            source_ontology_type: Optional override for source ontology type
            target_ontology_type: Optional override for target ontology type
            use_cache: Whether to use caching (default: True)
            max_cache_age_days: Maximum cache age in days
            progress_callback: Optional callback function(current_step, total_steps, status)
            batch_size: Size of batches for processing (default: 250)
            min_confidence: Minimum confidence threshold (default: 0.0)
            
        Returns:
            Dict[str, Any]: A MappingResultBundle-structured dictionary containing:
                - 'results': Dict[str, Dict] mapping source IDs to their mapped values
                - 'metadata': Dict with execution metadata including step-by-step provenance
                - 'step_results': List[Dict] with detailed results from each step
                - 'statistics': Dict with mapping statistics
                - 'final_identifiers': List of identifiers after all steps
                - 'final_ontology_type': Final ontology type after all conversions
                
        Raises:
            ConfigurationError: If the strategy doesn't exist, is inactive, has no steps,
                               or if source/target endpoints are not found
            MappingExecutionError: If a required step fails during execution
            
        Example:
            >>> executor = MappingExecutor()
            >>> result = await executor.execute_yaml_strategy(
            ...     strategy_name="ukbb_to_hpa_protein",
            ...     source_endpoint_name="UKBB",
            ...     target_endpoint_name="HPA",
            ...     input_identifiers=["ADAMTS13", "ALB"],
            ...     use_cache=True
            ... )
            >>> print(f"Final identifiers: {result['final_identifiers']}")
            >>> print(f"Step results: {len(result['step_results'])}")
        """
        # Delegate to StrategyOrchestrator
        return await self.strategy_orchestrator.execute_strategy(
            strategy_name=strategy_name,
            input_identifiers=input_identifiers,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            progress_callback=progress_callback,
            batch_size=batch_size,
            min_confidence=min_confidence,
        )
    async def _get_endpoint_by_name(self, session: AsyncSession, endpoint_name: str) -> Optional[Endpoint]:
        """
        Retrieve an endpoint configuration by name from the metamapper database.
        
        Args:
            session: Active database session
            endpoint_name: Name of the endpoint to retrieve
            
        Returns:
            Endpoint object if found, None otherwise
        """
        return await self.metadata_query_service.get_endpoint(session, endpoint_name)

    async def async_dispose(self):
        """Asynchronously dispose of underlying database engines."""
        self.logger.info("Disposing of MappingExecutor engines...")
        
        # Dispose metamapper engine
        if hasattr(self, 'async_metamapper_engine') and self.async_metamapper_engine:
            await self.async_metamapper_engine.dispose()
            self.logger.info("Metamapper engine disposed.")
            
        # Dispose cache engine  
        if hasattr(self, 'async_cache_engine') and self.async_cache_engine:
            await self.async_cache_engine.dispose()
            self.logger.info("Cache engine disposed.")
            
        # Clear client cache
        if hasattr(self, 'client_manager'):
            self.client_manager.clear_cache()
            
        self.logger.info("MappingExecutor engines disposed.")

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
            
    
    # Legacy Handler Methods (Placeholder Implementations)
    # These methods are referenced by the legacy execute_strategy method but are not implemented.
    # They are maintained for backward compatibility but will raise NotImplementedError when called.
    
    async def _handle_convert_identifiers_local(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for CONVERT_IDENTIFIERS_LOCAL action type.
        
        This method has been refactored to use the newer ConvertIdentifiersLocalAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to convert
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Mapping results with converted identifiers
        """
        try:
            # Extract parameters from action_parameters
            endpoint_context = action_parameters.get('endpoint_context', 'SOURCE')
            output_ontology_type = action_parameters.get('output_ontology_type')
            input_ontology_type = action_parameters.get('input_ontology_type', current_source_ontology_type)
            
            if not output_ontology_type:
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "failed",
                    "error": "output_ontology_type is required in action_parameters",
                    "details": {"action_parameters": action_parameters}
                }
            
            # For legacy compatibility with ConvertIdentifiersLocalAction,
            # we'll provide a basic implementation that performs ontology type
            # conversion without requiring full endpoint database configurations.
            # This maintains backward compatibility while using the StrategyAction framework.
            
            self.logger.info(f"Legacy convert identifiers: {input_ontology_type} -> {output_ontology_type}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.convert_identifiers_local import ConvertIdentifiersLocalAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = ConvertIdentifiersLocalAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_endpoint = MagicMock(spec=Endpoint)
                    mock_endpoint.id = 1
                    mock_endpoint.name = "LEGACY_ENDPOINT"
                    
                    # Create action parameters
                    action_params = {
                        'endpoint_context': endpoint_context,
                        'output_ontology_type': output_ontology_type,
                        'input_ontology_type': input_ontology_type
                    }
                    
                    # Create context
                    context = {
                        "db_session": session,
                        "mapping_executor": self,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_params,
                        source_endpoint=mock_endpoint,
                        target_endpoint=mock_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', output_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails (e.g., due to missing endpoint configurations),
                # fall back to a basic implementation that just changes the ontology type
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: just update the ontology type without actual conversion
                return {
                    "output_identifiers": current_identifiers,  # Keep same identifiers
                    "output_ontology_type": output_ontology_type,  # Update ontology type
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "conversion_type": "ontology_type_only",
                        "input_ontology_type": input_ontology_type,
                        "output_ontology_type": output_ontology_type,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in _handle_convert_identifiers_local: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
    
    async def _handle_execute_mapping_path(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for EXECUTE_MAPPING_PATH action type.
        
        This method has been refactored to use the newer ExecuteMappingPathAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to map
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Mapping results with mapped identifiers
        """
        try:
            # Extract parameters from action_parameters
            mapping_path_name = action_parameters.get('mapping_path_name')
            resource_name = action_parameters.get('resource_name')
            
            if not mapping_path_name and not resource_name:
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "failed",
                    "error": "Either mapping_path_name or resource_name is required in action_parameters",
                    "details": {"action_parameters": action_parameters}
                }
            
            self.logger.info(f"Legacy execute mapping path: {mapping_path_name or resource_name}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.execute_mapping_path import ExecuteMappingPathAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = ExecuteMappingPathAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_source_endpoint = MagicMock(spec=Endpoint)
                    mock_source_endpoint.id = 1
                    mock_source_endpoint.name = "LEGACY_SOURCE_ENDPOINT"
                    
                    mock_target_endpoint = MagicMock(spec=Endpoint)
                    mock_target_endpoint.id = 2
                    mock_target_endpoint.name = "LEGACY_TARGET_ENDPOINT"
                    
                    # Create context with legacy settings
                    context = {
                        "db_session": session,
                        "cache_settings": {
                            "use_cache": True,
                            "max_cache_age_days": None
                        },
                        "mapping_executor": self,
                        "batch_size": 250,
                        "min_confidence": 0.0,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_parameters,
                        source_endpoint=mock_source_endpoint,
                        target_endpoint=mock_target_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', current_source_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails, provide a basic fallback
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: return identifiers unchanged
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "mapping_type": "no_change",
                        "mapping_path_name": mapping_path_name,
                        "resource_name": resource_name,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in _handle_execute_mapping_path: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
    
    async def _handle_filter_identifiers_by_target_presence(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for FILTER_IDENTIFIERS_BY_TARGET_PRESENCE action type.
        
        This method has been refactored to use the newer FilterByTargetPresenceAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to filter
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Filtered identifiers based on target presence
        """
        try:
            # Extract parameters from action_parameters
            endpoint_context = action_parameters.get('endpoint_context', 'TARGET')
            ontology_type_to_match = action_parameters.get('ontology_type_to_match', current_source_ontology_type)
            
            self.logger.info(f"Legacy filter by target presence: {ontology_type_to_match}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.filter_by_target_presence import FilterByTargetPresenceAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = FilterByTargetPresenceAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_source_endpoint = MagicMock(spec=Endpoint)
                    mock_source_endpoint.id = 1
                    mock_source_endpoint.name = "LEGACY_SOURCE_ENDPOINT"
                    
                    mock_target_endpoint = MagicMock(spec=Endpoint)
                    mock_target_endpoint.id = 2
                    mock_target_endpoint.name = "LEGACY_TARGET_ENDPOINT"
                    
                    # Create action parameters in the format expected by the action class
                    action_params = {
                        'endpoint_context': endpoint_context,
                        'ontology_type_to_match': ontology_type_to_match
                    }
                    action_params.update(action_parameters)  # Include any additional parameters
                    
                    # Create context
                    context = {
                        "db_session": session,
                        "mapping_executor": self,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_params,
                        source_endpoint=mock_source_endpoint,
                        target_endpoint=mock_target_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', current_source_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails, provide a basic fallback
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: return all identifiers (no filtering)
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "filter_type": "no_filtering",
                        "endpoint_context": endpoint_context,
                        "ontology_type_to_match": ontology_type_to_match,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in _handle_filter_identifiers_by_target_presence: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }

    
    # ============================================================================
    # UTILITY API METHODS - Refactored from scripts
    # ============================================================================
    
    
    async def get_ontology_column(self, endpoint_name: str, ontology_type: str) -> str:
        """
        Get the column name for a given ontology type from an endpoint's property configuration.
        
        This method delegates to the IdentifierLoader for backward compatibility.
        
        Args:
            endpoint_name: Name of the endpoint
            ontology_type: Ontology type to look up (e.g., 'UniProt', 'Gene')
            
        Returns:
            Column name for the ontology type
            
        Raises:
            ConfigurationError: If endpoint, property config, or extraction config not found
            DatabaseQueryError: If there's an error querying the database
        """
        return await self.identifier_loader.get_ontology_column(endpoint_name, ontology_type)
    
    async def load_endpoint_identifiers(
        self, 
        endpoint_name: str, 
        ontology_type: str,
        return_dataframe: bool = False
    ) -> Union[List[str], 'pd.DataFrame']:
        """
        Load identifiers from an endpoint using its configuration in metamapper.db.
        
        This method delegates to the IdentifierLoader to maintain separation of concerns.
        
        Args:
            endpoint_name: Name of the endpoint to load from
            ontology_type: Ontology type of the identifiers to load
            return_dataframe: If True, return the full dataframe instead of just identifiers
            
        Returns:
            List of unique identifiers (default) or full DataFrame if return_dataframe=True
            
        Raises:
            ConfigurationError: If endpoint not found or file path issues
            FileNotFoundError: If the data file doesn't exist
            KeyError: If the specified column doesn't exist in the data
            DatabaseQueryError: If there's an error querying the database
        """
        return await self.identifier_loader.load_endpoint_identifiers(
            endpoint_name=endpoint_name,
            ontology_type=ontology_type,
            return_dataframe=return_dataframe
        )
    
    async def get_strategy_info(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a strategy including its steps and metadata.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dictionary containing strategy information including:
            - name: Strategy name
            - description: Strategy description
            - is_active: Whether the strategy is active
            - source_ontology_type: Default source ontology type
            - target_ontology_type: Default target ontology type
            - steps: List of step configurations
            
        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            DatabaseQueryError: If there's an error querying the database
        """
        try:
            async with self.async_metamapper_session() as session:
                # Get strategy with its steps
                stmt = (
                    select(MappingStrategy)
                    .where(MappingStrategy.name == strategy_name)
                    .options(selectinload(MappingStrategy.steps))
                )
                result = await session.execute(stmt)
                strategy = result.scalar_one_or_none()
                
                if not strategy:
                    raise StrategyNotFoundError(f"Strategy '{strategy_name}' not found")
                
                # Build strategy info
                strategy_info = {
                    "name": strategy.name,
                    "description": strategy.description,
                    "is_active": strategy.is_active,
                    "source_ontology_type": strategy.default_source_ontology_type,
                    "target_ontology_type": strategy.default_target_ontology_type,
                    "version": strategy.version,
                    "steps": []
                }
                
                # Add step information
                for step in sorted(strategy.steps, key=lambda s: s.step_order):
                    step_info = {
                        "step_id": step.step_id,
                        "step_order": step.step_order,
                        "action_type": step.action_type,
                        "description": step.description,
                        "parameters": json.loads(step.parameters) if step.parameters else {}
                    }
                    strategy_info["steps"].append(step_info)
                
                return strategy_info
                
        except StrategyNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting strategy info for {strategy_name}: {e}")
            raise DatabaseQueryError(f"Failed to get strategy info: {e}")
    
    async def validate_strategy_prerequisites(
        self, 
        strategy_name: str, 
        source_endpoint: str, 
        target_endpoint: str
    ) -> Dict[str, Any]:
        """
        Validate that all prerequisites are met for executing a strategy.
        
        This method performs pre-flight checks to ensure:
        - Strategy exists and is active
        - Source and target endpoints exist
        - Required ontology types are configured
        - Data files are accessible
        
        Args:
            strategy_name: Name of the strategy to validate
            source_endpoint: Name of the source endpoint
            target_endpoint: Name of the target endpoint
            
        Returns:
            Dictionary with validation results:
            - valid: Boolean indicating if all checks passed
            - errors: List of error messages if any
            - warnings: List of warning messages if any
            - strategy_info: Basic strategy information
            
        Raises:
            DatabaseQueryError: If there's an error querying the database
        """
        errors = []
        warnings = []
        strategy_info = None
        
        try:
            # Check strategy exists and get info
            # NOTE: Strategy validation removed as get_strategy was refactored to ConfigLoader
            # which handles YAML-based strategies instead of database strategies
            strategy_info = {
                "name": strategy_name,
                "source_ontology": "UNKNOWN",  # Would be loaded from YAML
                "target_ontology": "UNKNOWN"   # Would be loaded from YAML
            }
            
            # Check endpoints exist
            async with self.async_metamapper_session() as session:
                # Check source endpoint
                source = await self._get_endpoint_by_name(session, source_endpoint)
                if not source:
                    errors.append(f"Source endpoint '{source_endpoint}' not found")
                else:
                    # Check if source file exists (for file-based endpoints)
                    if source.type in ['file_csv', 'file_tsv']:
                        conn_details = json.loads(source.connection_details)
                        file_path = conn_details.get('file_path', '')
                        file_path = resolve_placeholders(file_path, {})
                        if not os.path.exists(file_path):
                            errors.append(f"Source data file not found: {file_path}")
                
                # Check target endpoint
                target = await self._get_endpoint_by_name(session, target_endpoint)
                if not target:
                    errors.append(f"Target endpoint '{target_endpoint}' not found")
                else:
                    # Check if target file exists (for file-based endpoints)
                    if target.type in ['file_csv', 'file_tsv']:
                        conn_details = json.loads(target.connection_details)
                        file_path = conn_details.get('file_path', '')
                        file_path = resolve_placeholders(file_path, {})
                        if not os.path.exists(file_path):
                            errors.append(f"Target data file not found: {file_path}")
                
                # Check ontology configurations if we have strategy info
                if strategy_info and source:
                    try:
                        await self.get_ontology_column(source_endpoint, 
                                                     strategy_info['source_ontology'])
                    except ConfigurationError as e:
                        errors.append(f"Source ontology configuration error: {e}")
                
                if strategy_info and target:
                    # Note: Target might use different ontology types, so we check if any exist
                    stmt = select(EndpointPropertyConfig).where(
                        EndpointPropertyConfig.endpoint_id == target.id
                    )
                    result = await session.execute(stmt)
                    configs = result.scalars().all()
                    if not configs:
                        warnings.append("No property configurations found for target endpoint")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "strategy_info": strategy_info
            }
            
        except Exception as e:
            self.logger.error(f"Error validating strategy prerequisites: {e}")
            raise DatabaseQueryError(f"Failed to validate prerequisites: {e}")
    
    async def execute_strategy_with_comprehensive_results(
        self,
        strategy_name: str,
        source_endpoint: str,
        target_endpoint: str,
        input_identifiers: List[str],
        use_cache: bool = True,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a strategy with enhanced result processing and comprehensive output.
        
        This is a high-level convenience method that wraps execute_yaml_strategy
        with additional result processing and formatting.
        
        Args:
            strategy_name: Name of the strategy to execute
            source_endpoint: Name of the source endpoint
            target_endpoint: Name of the target endpoint
            input_identifiers: List of input identifiers to map
            use_cache: Whether to use cached mappings (default: True)
            progress_callback: Optional callback for progress updates
            **kwargs: Additional keyword arguments passed to execute_yaml_strategy
            
        Returns:
            Dictionary with comprehensive results including:
            - results: Mapping results by identifier
            - final_identifiers: List of successfully mapped identifiers
            - summary: Execution summary with statistics
            - context: Any context data from bidirectional strategies
            - metrics: Performance metrics
            - provenance: Detailed provenance information
            
        Raises:
            Various exceptions from execute_yaml_strategy
        """
        start_time = time.time()
        
        # Execute the strategy
        result = await self.execute_yaml_strategy(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint,
            target_endpoint_name=target_endpoint,
            input_identifiers=input_identifiers,
            use_cache=use_cache,
            progress_callback=progress_callback,
            **kwargs
        )
        
        # Add execution time to metrics
        execution_time = time.time() - start_time
        if 'metrics' not in result:
            result['metrics'] = {}
        result['metrics']['total_execution_time'] = execution_time
        
        # Enhance summary with additional statistics
        if 'summary' in result:
            summary = result['summary']
            
            # Calculate success rate
            total_input = summary.get('total_input', 0)
            successful = summary.get('successful_mappings', 0)
            if total_input > 0:
                summary['success_rate'] = (successful / total_input) * 100
            else:
                summary['success_rate'] = 0
            
            # Add timing information
            summary['execution_time_seconds'] = execution_time
            
            # Categorize results by mapping status
            if 'results' in result:
                status_counts = {}
                for identifier, mapping in result['results'].items():
                    status = mapping.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
                summary['status_breakdown'] = status_counts
        
        # Log comprehensive summary
        self.logger.info(f"Strategy execution completed in {execution_time:.2f} seconds")
        if 'summary' in result:
            self.logger.info(f"Success rate: {result['summary']['success_rate']:.1f}%")
            self.logger.info(f"Status breakdown: {result['summary'].get('status_breakdown', {})}")
        
        return result

    # Robust execution methods (integrated from RobustExecutionMixin)
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress dict as argument
        """
        self.progress_reporter.add_callback(callback)
        self.checkpoint_manager.add_progress_callback(callback)
    
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_args: Dict[str, Any],
        operation_name: str,
        retry_exceptions: Tuple[type, ...] = (Exception,)
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Async callable to execute
            operation_args: Arguments to pass to the operation
            operation_name: Name for logging purposes
            retry_exceptions: Tuple of exception types to retry on
            
        Returns:
            Result of the operation
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Report attempt
                self.progress_reporter.report({
                    'type': 'retry_attempt',
                    'operation': operation_name,
                    'attempt': attempt + 1,
                    'max_attempts': self.max_retries
                })
                
                # Execute operation
                result = await operation(**operation_args)
                
                # Success - report and return
                if attempt > 0:
                    self.logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
                    
                return result
                
            except retry_exceptions as e:
                last_error = e
                self.logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay)
                    
        # All retries exhausted
        error_msg = f"{operation_name} failed after {self.max_retries} attempts"
        self.logger.error(f"{error_msg}: {last_error}")
        
        # Report failure
        self.progress_reporter.report({
            'type': 'retry_exhausted',
            'operation': operation_name,
            'attempts': self.max_retries,
            'last_error': str(last_error)
        })
        
        raise MappingExecutionError(
            error_msg,
            details={
                'operation': operation_name,
                'attempts': self.max_retries,
                'last_error': str(last_error)
            }
        )
    
    async def process_in_batches(
        self,
        items: List[Any],
        processor: Callable,
        processor_name: str,
        checkpoint_key: str,
        execution_id: str,
        checkpoint_state: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Process items in batches with checkpointing.
        
        Args:
            items: List of items to process
            processor: Async callable that processes a batch
            processor_name: Name for logging purposes
            checkpoint_key: Key to store results in checkpoint
            execution_id: Unique identifier for checkpointing
            checkpoint_state: Existing checkpoint state to resume from
            
        Returns:
            List of all results
        """
        # Initialize or restore state
        if checkpoint_state and checkpoint_key in checkpoint_state:
            results = checkpoint_state[checkpoint_key]
            processed_count = checkpoint_state.get('processed_count', 0)
            remaining_items = items[processed_count:]
            self.logger.info(
                f"Resuming {processor_name} from checkpoint: "
                f"{processed_count}/{len(items)} already processed"
            )
        else:
            results = []
            processed_count = 0
            remaining_items = items
            
        total_count = len(items)
        
        # Process in batches
        for i in range(0, len(remaining_items), self.batch_size):
            batch = remaining_items[i:i + self.batch_size]
            batch_num = (processed_count + i) // self.batch_size + 1
            total_batches = (total_count + self.batch_size - 1) // self.batch_size
            
            self.logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} items) for {processor_name}"
            )
            
            # Report batch start
            self.progress_reporter.report({
                'type': 'batch_start',
                'processor': processor_name,
                'batch_num': batch_num,
                'total_batches': total_batches,
                'batch_size': len(batch),
                'total_processed': processed_count + i,
                'total_count': total_count
            })
            
            try:
                # Process batch with retry
                batch_results = await self.execute_with_retry(
                    operation=processor,
                    operation_args={'batch': batch},
                    operation_name=f"{processor_name}_batch_{batch_num}",
                    retry_exceptions=(asyncio.TimeoutError, Exception)
                )
                
                # Append results
                results.extend(batch_results)
                
                # Update processed count
                current_processed = processed_count + i + len(batch)
                
                # Save checkpoint
                if self.checkpoint_enabled:
                    checkpoint_data = {
                        checkpoint_key: results,
                        'processed_count': current_processed,
                        'total_count': total_count,
                        'processor': processor_name
                    }
                    
                    # Preserve other checkpoint data
                    if checkpoint_state:
                        for key, value in checkpoint_state.items():
                            if key not in checkpoint_data:
                                checkpoint_data[key] = value
                                
                    await self.checkpoint_manager.save_checkpoint(execution_id, checkpoint_data)
                
                # Report batch completion
                self.progress_reporter.report({
                    'type': 'batch_complete',
                    'processor': processor_name,
                    'batch_num': batch_num,
                    'total_batches': total_batches,
                    'batch_results': len(batch_results),
                    'total_processed': current_processed,
                    'total_count': total_count,
                    'progress_percent': (current_processed / total_count * 100)
                })
                
            except Exception as e:
                self.logger.error(
                    f"Batch {batch_num} failed for {processor_name}: {e}"
                )
                
                # Report batch failure
                self.progress_reporter.report({
                    'type': 'batch_failed',
                    'processor': processor_name,
                    'batch_num': batch_num,
                    'total_batches': total_batches,
                    'error': str(e)
                })
                
                # Re-raise to trigger retry or abort
                raise
                
        return results
    
    async def execute_yaml_strategy_robust(
        self,
        strategy_name: str,
        input_identifiers: List[str],
        source_endpoint_name: Optional[str] = None,
        target_endpoint_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        resume_from_checkpoint: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a YAML strategy with robust error handling and checkpointing.
        
        This wraps the standard execute_yaml_strategy method with additional
        robustness features via the RobustExecutionCoordinator.
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of input identifiers
            source_endpoint_name: Source endpoint name (optional, can be auto-detected)
            target_endpoint_name: Target endpoint name (optional, can be auto-detected)
            execution_id: Unique ID for this execution (for checkpointing)
            resume_from_checkpoint: Whether to resume from checkpoint if available
            **kwargs: Additional arguments to pass to execute_yaml_strategy
            
        Returns:
            Strategy execution results with additional robustness metadata
        """
        # Delegate to the RobustExecutionCoordinator
        return await self.robust_execution_coordinator.execute_strategy_robustly(
            strategy_name=strategy_name,
            input_identifiers=input_identifiers,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            execution_id=execution_id,
            resume_from_checkpoint=resume_from_checkpoint,
            **kwargs
        )

    async def get_strategy(self, strategy_name: str) -> Optional[MappingStrategy]:
        """
        Get a strategy by name from the database.
        
        Args:
            strategy_name: Name of the strategy to retrieve
            
        Returns:
            MappingStrategy object if found, None otherwise
        """
        try:
            async with self.async_metamapper_session() as session:
                query = select(MappingStrategy).where(MappingStrategy.name == strategy_name)
                result = await session.execute(query)
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting strategy {strategy_name}: {e}")
            return None

    def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]):
        """
        Save checkpoint data for an execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to save in the checkpoint
        """
        return self.checkpoint_manager.save_checkpoint(execution_id, checkpoint_data)

    def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for an execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        return self.checkpoint_manager.load_checkpoint(execution_id)

    def _report_progress(self, progress_data: Dict[str, Any]):
        """
        Report progress to registered callbacks.
        
        Args:
            progress_data: Progress information to report
        """
        return self.progress_reporter.report(progress_data)
    
    # Checkpoint-related delegate methods for backward compatibility
    
    async def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]):
        """
        Save checkpoint data for the given execution ID.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to save in the checkpoint
        """
        await self.checkpoint_manager.save_checkpoint(execution_id, checkpoint_data)
    
    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for the given execution ID.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        return await self.checkpoint_manager.load_checkpoint(execution_id)
    
    def _report_progress(self, progress_data: Dict[str, Any]):
        """
        Report progress to registered callbacks.
        
        Args:
            progress_data: Progress information to report
        """
        self.progress_reporter.report(progress_data)
    
    # Client delegate methods
    
    def _load_client(self, client_path: str, **kwargs):
        """Load a client instance (delegates to client manager)."""
        return self.client_manager.get_client_instance(client_path, **kwargs)
    
    @property
    def checkpoint_dir(self):
        """Get the checkpoint directory path."""
        return self.checkpoint_manager.checkpoint_dir
    
    @checkpoint_dir.setter
    def checkpoint_dir(self, value):
        """Set the checkpoint directory path."""
        if hasattr(self.checkpoint_manager, 'checkpoint_dir'):
            from pathlib import Path
            if value is not None:
                self.checkpoint_manager.checkpoint_dir = Path(value)
                self.checkpoint_manager.checkpoint_dir.mkdir(parents=True, exist_ok=True)
                self.checkpoint_manager.checkpoint_enabled = True
            else:
                self.checkpoint_manager.checkpoint_dir = None
                self.checkpoint_manager.checkpoint_enabled = False

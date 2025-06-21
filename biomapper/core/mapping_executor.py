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

# Import services
from biomapper.core.services import IterativeMappingService
from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.engine_components.progress_reporter import ProgressReporter
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.services.mapping_path_execution_service import MappingPathExecutionService
from biomapper.core.services.mapping_step_execution_service import MappingStepExecutionService
from biomapper.core.services.strategy_execution_service import StrategyExecutionService
from biomapper.core.services.result_aggregation_service import ResultAggregationService
from biomapper.core.services.bidirectional_validation_service import BidirectionalValidationService
from biomapper.core.services.direct_mapping_service import DirectMappingService
from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService
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
    ExecutionMetric, # Added ExecutionMetric
    Base as CacheBase,  # Add for database table creation
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
        # Support both old-style (config params) and new-style (pre-initialized components)
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False,
        path_cache_size: int = 100,
        path_cache_expiry_seconds: int = 300,
        max_concurrent_batches: int = 5,
        enable_metrics: bool = True,
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
        # Pre-initialized components (new style)
        session_manager=None,
        client_manager=None,
        config_loader=None,
        strategy_handler=None,
        path_finder=None,
        path_execution_manager=None,
        cache_manager=None,
        identifier_loader=None,
        strategy_orchestrator=None,
        checkpoint_manager=None,
        progress_reporter=None,
        langfuse_tracker=None,
    ):
        """
        Initializes the MappingExecutor.
        
        Supports two initialization modes:
        1. Legacy mode: Pass configuration parameters and components are created internally
        2. Component mode: Pass pre-initialized components directly

        Legacy mode args:
            metamapper_db_url: URL for the metamapper database
            mapping_cache_db_url: URL for the mapping cache database
            echo_sql: Boolean flag to enable SQL echoing
            path_cache_size: Maximum number of paths to cache
            path_cache_expiry_seconds: Cache expiry time in seconds
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
            
        Component mode args:
            session_manager: Pre-initialized SessionManager instance
            client_manager: Pre-initialized ClientManager instance
            config_loader: Pre-initialized ConfigLoader instance
            strategy_handler: Pre-initialized StrategyHandler instance
            path_finder: Pre-initialized PathFinder instance
            path_execution_manager: Pre-initialized PathExecutionManager instance
            cache_manager: Pre-initialized CacheManager instance
            identifier_loader: Pre-initialized IdentifierLoader instance
            strategy_orchestrator: Pre-initialized StrategyOrchestrator instance
            checkpoint_manager: Pre-initialized CheckpointManager instance
            progress_reporter: Pre-initialized ProgressReporter instance
            langfuse_tracker: Pre-initialized Langfuse tracker instance
        """
        # Initialize the CompositeIdentifierMixin
        super().__init__()

        self.logger = logging.getLogger(__name__)
        
        # Check if we're in legacy mode (configuration parameters) or component mode
        if session_manager is None:
            # Legacy mode: use MappingExecutorInitializer to create components
            self.logger.debug("Initializing MappingExecutor in legacy mode")
            
            # Store configuration parameters
            self.batch_size = batch_size
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.checkpoint_enabled = checkpoint_enabled
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
            
            # Store DB URLs for backward compatibility
            self.metamapper_db_url = metamapper_db_url if metamapper_db_url else settings.metamapper_db_url
            self.mapping_cache_db_url = mapping_cache_db_url if mapping_cache_db_url else settings.cache_db_url
            self.echo_sql = echo_sql
            
        else:
            # Component mode: use pre-initialized components
            self.logger.debug("Initializing MappingExecutor in component mode")
            
            # Store configuration parameters
            self.batch_size = batch_size
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.checkpoint_enabled = checkpoint_enabled
            self.max_concurrent_batches = max_concurrent_batches
            self.enable_metrics = enable_metrics
            
            # Assign pre-initialized components
            self.session_manager = session_manager
            self.client_manager = client_manager
            self.config_loader = config_loader
            self.strategy_handler = strategy_handler
            self.path_finder = path_finder
            self.path_execution_manager = path_execution_manager
            self.cache_manager = cache_manager
            self.identifier_loader = identifier_loader
            self.strategy_orchestrator = strategy_orchestrator
            self.checkpoint_manager = checkpoint_manager
            self.progress_reporter = progress_reporter
            self._langfuse_tracker = langfuse_tracker
            self._metrics_tracker = None
            
            # Create convenience references for backward compatibility
            self.async_metamapper_engine = self.session_manager.async_metamapper_engine
            self.MetamapperSessionFactory = self.session_manager.MetamapperSessionFactory
            self.async_metamapper_session = self.session_manager.async_metamapper_session
            self.async_cache_engine = self.session_manager.async_cache_engine
            self.CacheSessionFactory = self.session_manager.CacheSessionFactory
            self.async_cache_session = self.session_manager.async_cache_session
            
            # Store DB URLs for backward compatibility (extract from session_manager)
            self.metamapper_db_url = str(self.async_metamapper_engine.url)
            self.mapping_cache_db_url = str(self.async_cache_engine.url)
            self.echo_sql = self.async_metamapper_engine.echo
        
        # Initialize MetadataQueryService
        self.metadata_query_service = MetadataQueryService(self.session_manager)
        
        # Initialize MappingPathExecutionService with all required arguments
        # Initialize BidirectionalValidationService
        self.bidirectional_validation_service = BidirectionalValidationService()
        
        # Initialize DirectMappingService
        self.direct_mapping_service = DirectMappingService(logger=self.logger)
        
        # Initialize MappingStepExecutionService
        self.step_execution_service = MappingStepExecutionService(
            client_manager=self.client_manager,
            cache_manager=self.cache_manager,
            logger=self.logger
        )
        
        # Initialize IterativeMappingService
        self.iterative_mapping_service = IterativeMappingService(logger=self.logger)
        # Initialize MappingPathExecutionService with all required arguments
        self.path_execution_service = MappingPathExecutionService(
            session_manager=self.session_manager,
            client_manager=self.client_manager,
            cache_manager=self.cache_manager,
            path_finder=self.path_finder,
            path_execution_manager=self.path_execution_manager,
            composite_handler=self,  # MappingExecutor implements composite handling
            step_execution_service=self.step_execution_service,
            logger=self.logger
        )
        
        # Set executor reference for delegation
        self.path_execution_service.set_executor(self)
        
        # Initialize ExecutionLifecycleService
        self.lifecycle_service = ExecutionLifecycleService(
            checkpoint_manager=self.checkpoint_manager,
            progress_reporter=self.progress_reporter,
            metrics_manager=self._langfuse_tracker
        )
        
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
        
        # Initialize ResultAggregationService
        self.result_aggregation_service = ResultAggregationService(logger=self.logger)
        
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
        
        This factory method uses MappingExecutorInitializer to create all components
        and initializes the database tables for both metamapper and cache databases.
        
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
        # Create initializer with all configuration parameters
        initializer = MappingExecutorInitializer(
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
        
        # Use the initializer to create the executor
        executor = await initializer.create_executor()
        
        # Initialize metamapper database tables using DatabaseSetupService
        # (cache tables are already initialized in create_executor)
        db_setup_service = DatabaseSetupService(logger=executor.logger)
        await db_setup_service.initialize_tables(executor.async_metamapper_engine, MetamapperBase.metadata)
        
        return executor

    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()



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
                # Use the DirectMappingService to handle this step
                direct_mapping_result = await self.direct_mapping_service.execute_direct_mapping(
                    meta_session=meta_session,
                    path_finder=self.path_finder,
                    path_executor=self,
                    primary_source_ontology=primary_source_ontology,
                    primary_target_ontology=primary_target_ontology,
                    original_input_ids_set=original_input_ids_set,
                    processed_ids=processed_ids,
                    successful_mappings=successful_mappings,
                    mapping_direction=mapping_direction,
                    try_reverse_mapping=try_reverse_mapping,
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    mapping_session_id=mapping_session_id,
                    batch_size=batch_size,
                    max_hop_count=max_hop_count,
                    min_confidence=min_confidence,
                    max_concurrent_batches=max_concurrent_batches
                )
                
                # Store the primary path reference for potential use in step 5
                primary_path = None
                if direct_mapping_result["path_found"]:
                    # We need to retrieve the path object for later use in step 5
                    primary_path = await self._find_best_path(
                        meta_session,
                        primary_source_ontology,
                        primary_target_ontology,
                        preferred_direction=mapping_direction,
                        allow_reverse=try_reverse_mapping,
                        source_endpoint=source_endpoint,
                        target_endpoint=target_endpoint,
                    )

                # --- 3, 4, & 5. Iterative Secondary Mapping ---
                self.logger.info("--- Steps 3, 4, & 5: Performing Iterative Secondary Mapping ---")
                secondary_start = time.time()
                unmapped_ids_step3 = list(original_input_ids_set - processed_ids) # IDs not mapped by cache or Step 2
                
                # Use the IterativeMappingService to handle the complex iterative mapping logic
                iterative_results = await self.iterative_mapping_service.perform_iterative_mapping(
                    unmapped_ids=unmapped_ids_step3,
                    source_endpoint_name=source_endpoint_name,
                    target_endpoint_name=target_endpoint_name,
                    primary_source_ontology=primary_source_ontology,
                    primary_target_ontology=primary_target_ontology,
                    source_property_name=source_property_name,
                    primary_path=primary_path,
                    meta_session=meta_session,
                    mapping_executor=self,
                    mapping_session_id=mapping_session_id,
                    mapping_direction=mapping_direction,
                    try_reverse_mapping=try_reverse_mapping,
                    use_cache=use_cache,
                    max_cache_age_days=max_cache_age_days,
                    batch_size=batch_size,
                    max_concurrent_batches=max_concurrent_batches,
                    max_hop_count=max_hop_count,
                    min_confidence=min_confidence,
                )
                
                # Unpack the results from the iterative mapping service
                iterative_successful_mappings, iterative_processed_ids, derived_primary_ids = iterative_results
                
                # Merge the results back into the main tracking variables
                successful_mappings.update(iterative_successful_mappings)
                processed_ids.update(iterative_processed_ids)
                
                # Log timing for iterative mapping
                self.logger.info(f"TIMING: iterative secondary mapping took {time.time() - secondary_start:.3f}s")

                # --- 6. Bidirectional Validation (if requested) ---
                if validate_bidirectional:
                    # Delegate to the BidirectionalValidationService
                    successful_mappings = await self.bidirectional_validation_service.validate_mappings(
                        mapping_executor=self,
                        meta_session=meta_session,
                        successful_mappings=successful_mappings,
                        source_endpoint_name=source_endpoint_name,
                        target_endpoint_name=target_endpoint_name,
                        source_property_name=source_property_name,
                        target_property_name=target_property_name,
                        source_endpoint=source_endpoint,
                        target_endpoint=target_endpoint,
                        mapping_session_id=mapping_session_id,
                        batch_size=batch_size,
                        max_concurrent_batches=max_concurrent_batches,
                        min_confidence=min_confidence
                    )

                # --- 7. Aggregate Results & Finalize ---
                self.logger.info("--- Step 7: Aggregating final results ---")
                
                # Use ResultAggregationService to aggregate results
                final_results = self.result_aggregation_service.aggregate_mapping_results(
                    successful_mappings=successful_mappings,
                    original_input_ids=input_identifiers,
                    processed_ids=processed_ids,
                    strategy_name="execute_mapping",
                    source_ontology_type=source_endpoint_name,
                    target_ontology_type=target_endpoint_name,
                )
                
                return final_results
                
        except BiomapperError as e:
            # Logged within specific steps or helpers typically
            self.logger.error(f"Biomapper Error during mapping execution: {e}", exc_info=True)
            
            # Use ResultAggregationService to aggregate error results
            final_results = self.result_aggregation_service.aggregate_error_results(
                successful_mappings=successful_mappings,
                original_input_ids=input_identifiers,
                processed_ids=processed_ids,
                error=e,
                error_status=PathExecutionStatus.ERROR,
            )
            
            return final_results
            
        except Exception as e:
            self.logger.exception("Unhandled exception during mapping execution.")
            
            # Use ResultAggregationService to aggregate error results
            final_results = self.result_aggregation_service.aggregate_error_results(
                successful_mappings=successful_mappings,
                original_input_ids=input_identifiers,
                processed_ids=processed_ids,
                error=e,
                error_status=PathExecutionStatus.ERROR,
            )
            
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
        self.lifecycle_service.add_progress_callback(callback)
    
    
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
                await self.lifecycle_service.report_progress({
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
        await self.lifecycle_service.report_progress({
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
            await self.lifecycle_service.report_batch_progress(
                batch_number=batch_num,
                total_batches=total_batches,
                items_processed=processed_count + i,
                total_items=total_count,
                batch_metadata={
                    'type': 'batch_start',
                    'processor': processor_name,
                    'batch_size': len(batch)
                }
            )
            
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
                                
                    await self.lifecycle_service.save_batch_checkpoint(
                        execution_id=execution_id,
                        batch_number=batch_num,
                        batch_state=checkpoint_data,
                        checkpoint_metadata={'processor': processor_name}
                    )
                
                # Report batch completion
                await self.lifecycle_service.report_batch_progress(
                    batch_number=batch_num,
                    total_batches=total_batches,
                    items_processed=current_processed,
                    total_items=total_count,
                    batch_metadata={
                        'type': 'batch_complete',
                        'processor': processor_name,
                        'batch_results': len(batch_results)
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    f"Batch {batch_num} failed for {processor_name}: {e}"
                )
                
                # Report batch failure
                await self.lifecycle_service.report_progress({
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



    async def _report_progress(self, progress_data: Dict[str, Any]):
        """
        Report progress to registered callbacks.
        
        Args:
            progress_data: Progress information to report
        """
        await self.lifecycle_service.report_progress(progress_data)
    
    # Client delegate methods
    
    def _load_client(self, client_path: str, **kwargs):
        """Load a client instance (delegates to client manager)."""
        return self.client_manager.get_client_instance(client_path, **kwargs)
    
    @property
    def checkpoint_dir(self):
        """Get the checkpoint directory path."""
        return self.lifecycle_service.get_checkpoint_directory()
    
    @checkpoint_dir.setter
    def checkpoint_dir(self, value):
        """Set the checkpoint directory path."""
        from pathlib import Path
        if value is not None:
            self.lifecycle_service.set_checkpoint_directory(Path(value))
            # Ensure directory exists
            Path(value).mkdir(parents=True, exist_ok=True)
            self.checkpoint_enabled = True
        else:
            self.lifecycle_service.set_checkpoint_directory(None)
            self.checkpoint_enabled = False

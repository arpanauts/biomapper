import logging
import time
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

# Import composite identifier handling
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin

# Import exceptions
from biomapper.core.exceptions import (
    MappingExecutionError,
    ConfigurationError,
    DatabaseQueryError,
    CacheStorageError,
    ErrorCode,
    StrategyNotFoundError,
    InactiveStrategyError,
)

# Import services and components
from biomapper.core.engine_components.initialization_service import InitializationService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_manager import LifecycleManager
from biomapper.core.services.database_setup_service import DatabaseSetupService

# Import models
from biomapper.core.models.result_bundle import MappingResultBundle
from ..db.models import Base as MetamapperBase, MappingStrategy
from ..db.cache_models import PathExecutionStatus, MappingSession, ExecutionMetric

# Import utilities
from biomapper.core.utils.placeholder_resolver import resolve_placeholders
from biomapper.core.utils.time_utils import get_current_utc_time

# Import configuration
from biomapper.config import settings





class MappingExecutor(CompositeIdentifierMixin):
    """
    High-level facade for biomapper's service-oriented mapping architecture.
    
    The MappingExecutor serves as the primary entry point for all mapping operations,
    providing a clean and simple API while delegating complex operations to specialized
    services. It follows the Facade design pattern to hide the complexity of the underlying
    service ecosystem from clients.
    
    Architecture Overview:
    - Acts as a facade that delegates to specialized execution services
    - Manages initialization and coordination of the service ecosystem
    - Provides backward compatibility while leveraging the new service architecture
    
    Key Responsibilities:
    - Provides high-level methods for common mapping operations
    - Delegates YAML strategy execution to YamlStrategyExecutionService
    - Delegates iterative mapping to IterativeExecutionService
    - Delegates database strategies to DbStrategyExecutionService
    - Manages service initialization through MappingExecutorInitializer
    
    The executor abstracts away the complexity of service interactions, allowing clients
    to perform sophisticated mapping operations with simple method calls.
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
        Initializes the MappingExecutor as a lean facade.
        
        All component initialization is delegated to InitializationService.
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
        
        # Initialize MappingHandlerService
        self.mapping_handler_service = MappingHandlerService(
            logger=self.logger,
            client_manager=self.client_manager,
            path_finder=self.path_finder,
            async_metamapper_session=self.async_metamapper_session,
            metadata_query_service=self.metadata_query_service,
        )
        
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
        
        # Initialize the new execution services
        self.iterative_execution_service = IterativeExecutionService(
            direct_mapping_service=self.direct_mapping_service,
            iterative_mapping_service=self.iterative_mapping_service,
            bidirectional_validation_service=self.bidirectional_validation_service,
            result_aggregation_service=self.result_aggregation_service,
            path_finder=self.path_finder,
            composite_handler=self._composite_handler,
            async_metamapper_session=self.async_metamapper_session,
            metadata_query_service=self.metadata_query_service,
            logger=self.logger,
        )
        # Set the executor reference
        self.iterative_execution_service.set_executor(self)
        
        self.db_strategy_execution_service = DbStrategyExecutionService(
            strategy_execution_service=self.strategy_execution_service,
            logger=self.logger,
        )
        
        self.yaml_strategy_execution_service = YamlStrategyExecutionService(
            strategy_orchestrator=self.strategy_orchestrator,
            logger=self.logger,
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
        input_data: List[str] = None,
        source_property_name: str = "PrimaryIdentifier",
        target_property_name: str = "PrimaryIdentifier",
        source_ontology_type: str = None,
        target_ontology_type: str = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
        validate_bidirectional: bool = False,
        progress_callback: Optional[callable] = None,
        batch_size: int = 250,
        max_concurrent_batches: Optional[int] = None,
        max_hop_count: Optional[int] = None,
        min_confidence: float = 0.0,
        enable_metrics: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Execute a mapping process based on endpoint configurations, using an iterative strategy.

        This method delegates to the IterativeExecutionService for the actual execution logic.
        The service handles:
        1. Attempt direct mapping using the primary shared ontology.
        2. Identify unmapped entities.
        3. For unmapped entities, attempt to convert secondary identifiers to the primary shared ontology.
        4. Re-attempt direct mapping using derived primary identifiers.
        5. Aggregate results.

        Args:
            source_endpoint_name: Source endpoint name
            target_endpoint_name: Target endpoint name
            input_identifiers: List of identifiers to map (deprecated, use input_data instead)
            input_data: List of identifiers to map (preferred parameter)
            source_property_name: Property name defining the primary ontology type for the source endpoint
            target_property_name: Property name defining the primary ontology type for the target endpoint
            source_ontology_type: Optional source ontology type override
            target_ontology_type: Optional target ontology type override
            use_cache: Whether to check the cache before executing mapping steps
            max_cache_age_days: Maximum age of cached results to use (None = no limit)
            mapping_direction: The preferred direction ('forward' or 'reverse')
            try_reverse_mapping: Allows using a reversed path if no forward path found
            validate_bidirectional: If True, validates forward mappings by testing reverse mapping
            progress_callback: Optional callback function for reporting progress
            batch_size: Number of identifiers to process in each batch
            max_concurrent_batches: Maximum number of batches to process concurrently
            max_hop_count: Maximum number of hops to allow in paths
            min_confidence: Minimum confidence score to accept
            enable_metrics: Whether to enable metrics tracking

        Returns:
            Dictionary with mapping results, including provenance and validation status
        """
        return await self.iterative_execution_service.execute(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            input_data=input_data,
            source_property_name=source_property_name,
            target_property_name=target_property_name,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            mapping_direction=mapping_direction,
            try_reverse_mapping=try_reverse_mapping,
            validate_bidirectional=validate_bidirectional,
            progress_callback=progress_callback,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            max_hop_count=max_hop_count,
            min_confidence=min_confidence,
            enable_metrics=enable_metrics,
            mapping_executor=self,  # Pass self as the mapping_executor for callbacks
        )

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
        Execute a named mapping strategy from the database.
        
        This method delegates to the DbStrategyExecutionService for executing database-stored
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
        return await self.db_strategy_execution_service.execute(
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
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a YAML-defined mapping strategy using dedicated strategy action classes.
        
        This method delegates to the YamlStrategyExecutionService for executing multi-step
        mapping strategies defined in YAML configuration. Each step in the strategy is
        executed sequentially using dedicated action classes, with the output of one step
        becoming the input for the next.
        
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
            initial_context: Optional initial context dictionary to merge into execution context
            
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
        return await self.yaml_strategy_execution_service.execute(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            progress_callback=progress_callback,
            batch_size=batch_size,
            min_confidence=min_confidence,
            initial_context=initial_context,
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
        
        Delegates to MappingHandlerService.handle_convert_identifiers_local.
        """
        return await self.mapping_handler_service.handle_convert_identifiers_local(
            current_identifiers=current_identifiers,
            action_parameters=action_parameters,
            current_source_ontology_type=current_source_ontology_type,
            target_ontology_type=target_ontology_type,
            step_id=step_id,
            step_description=step_description,
            mapping_executor=self,  # Pass self reference for context
            **kwargs
        )
    
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
        
        Delegates to MappingHandlerService.handle_execute_mapping_path.
        """
        return await self.mapping_handler_service.handle_execute_mapping_path(
            current_identifiers=current_identifiers,
            action_parameters=action_parameters,
            current_source_ontology_type=current_source_ontology_type,
            target_ontology_type=target_ontology_type,
            step_id=step_id,
            step_description=step_description,
            mapping_executor=self,  # Pass self reference for context
            **kwargs
        )
    
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
        
        Delegates to MappingHandlerService.handle_filter_identifiers_by_target_presence.
        """
        return await self.mapping_handler_service.handle_filter_identifiers_by_target_presence(
            current_identifiers=current_identifiers,
            action_parameters=action_parameters,
            current_source_ontology_type=current_source_ontology_type,
            target_ontology_type=target_ontology_type,
            step_id=step_id,
            step_description=step_description,
            mapping_executor=self,  # Pass self reference for context
            **kwargs
        )

    
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
    
    async def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]):
        """
        Save checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to checkpoint
        """
        await self.lifecycle_service.save_checkpoint(execution_id, checkpoint_data)
    
    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        return await self.lifecycle_service.load_checkpoint(execution_id)

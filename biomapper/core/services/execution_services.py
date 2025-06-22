"""
Execution services for different mapping strategies.

This module contains service classes that handle the execution logic for different
types of mapping operations, extracted from the MappingExecutor class to improve
modularity and maintainability.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, AsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.core.exceptions import (
    BiomapperError,
    ConfigurationError,
)
from biomapper.db.cache_models import PathExecutionStatus
from biomapper.core.services.direct_mapping_service import DirectMappingService
from biomapper.core.services.iterative_mapping_service import IterativeMappingService
from biomapper.core.services.bidirectional_validation_service import BidirectionalValidationService
from biomapper.core.services.result_aggregation_service import ResultAggregationService
from biomapper.core.services.strategy_execution_service import StrategyExecutionService as LegacyStrategyExecutionService
from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.composite_handler import CompositeIdentifierHandler
from biomapper.core.engine_components.strategy_orchestrator import StrategyOrchestrator
from biomapper.core.utils.time_utils import get_current_utc_time
from biomapper.core.services.session_metrics_service import SessionMetricsService


class IterativeExecutionService:
    """
    Service for executing iterative mapping strategies in biomapper's service-oriented architecture.
    
    The IterativeExecutionService is a specialized service that handles iterative mapping
    approaches where mappings are attempted through multiple providers or strategies
    sequentially. It is part of the service layer that the MappingExecutor facade delegates to.
    
    Key Responsibilities:
    1. Execute multi-step mapping processes with fallback strategies
    2. Handle direct primary mapping attempts
    3. Perform iterative secondary mapping for unmapped identifiers
    4. Optionally validate mappings bidirectionally
    5. Aggregate results from multiple mapping attempts
    
    This service exemplifies the separation of concerns in the new architecture, focusing
    solely on iterative execution logic while delegating specific operations to other services.
    """
    
    def __init__(
        self,
        direct_mapping_service: DirectMappingService,
        iterative_mapping_service: IterativeMappingService,
        bidirectional_validation_service: BidirectionalValidationService,
        result_aggregation_service: ResultAggregationService,
        path_finder: PathFinder,
        composite_handler: CompositeIdentifierHandler,
        async_metamapper_session: AsyncContextManager,
        async_cache_session: AsyncContextManager,
        metadata_query_service,
        session_metrics_service: SessionMetricsService,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the IterativeExecutionService.
        
        Args:
            direct_mapping_service: Service for direct mapping execution
            iterative_mapping_service: Service for iterative secondary mapping
            bidirectional_validation_service: Service for bidirectional validation
            result_aggregation_service: Service for aggregating results
            path_finder: Component for finding mapping paths
            composite_handler: Handler for composite identifiers
            async_metamapper_session: Async context manager for database sessions
            metadata_query_service: Service for metadata queries
            logger: Optional logger instance
        """
        self.direct_mapping_service = direct_mapping_service
        self.iterative_mapping_service = iterative_mapping_service
        self.bidirectional_validation_service = bidirectional_validation_service
        self.result_aggregation_service = result_aggregation_service
        self.path_finder = path_finder
        self._composite_handler = composite_handler
        self.async_metamapper_session = async_metamapper_session
        self.async_cache_session = async_cache_session
        self.metadata_query_service = metadata_query_service
        self.session_metrics_service = session_metrics_service
        self.logger = logger or logging.getLogger(__name__)
        
        # References that will be set by MappingExecutor after initialization
        self._executor = None
        
        # Initialize composite handler flag
        self._composite_initialized = True
    
    def set_executor(self, executor):
        """Set the MappingExecutor reference for method delegation."""
        self._executor = executor

    async def execute(
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
        mapping_executor = None,  # Add mapping_executor parameter for callbacks
    ) -> Dict[str, Any]:
        """
        Execute a mapping process based on endpoint configurations, using an iterative strategy.

        Steps:
        1. Attempt direct mapping using the primary shared ontology.
        2. Identify unmapped entities.
        3. For unmapped entities, attempt to convert secondary identifiers to the primary shared ontology based on priority.
        4. Re-attempt direct mapping using derived primary identifiers.
        5. Aggregate results.

        Args:
            source_endpoint_name: Source endpoint name
            target_endpoint_name: Target endpoint name
            input_identifiers: List of identifiers to map (deprecated, use input_data instead)
            input_data: List of identifiers to map (preferred parameter)
            source_property_name: Property name defining the primary ontology type for the source endpoint
            target_property_name: Property name defining the primary ontology type for the target endpoint
            use_cache: Whether to check the cache before executing mapping steps
            max_cache_age_days: Maximum age of cached results to use (None = no limit)
            mapping_direction: The preferred direction ('forward' or 'reverse')
            try_reverse_mapping: Allows using a reversed path if no forward path found
            validate_bidirectional: If True, validates forward mappings by running a reverse mapping
            progress_callback: Optional callback function for reporting progress
            batch_size: Number of identifiers to process in each batch
            max_concurrent_batches: Maximum number of batches to process concurrently
            max_hop_count: Maximum number of hops to allow in paths
            min_confidence: Minimum confidence score to accept
            enable_metrics: Whether to enable metrics tracking
            mapping_executor: Reference to MappingExecutor for path execution

        Returns:
            Dictionary with mapping results, including provenance and validation status
        """
        # --- Input Handling ---
        if input_data is not None and input_identifiers is None:
            input_identifiers = input_data
        elif input_identifiers is None and input_data is None:
            self.logger.warning("No input identifiers provided for mapping.")
            return {}
        input_identifiers = input_identifiers if input_identifiers is not None else []

        # Use a set for efficient lookup and to handle potential duplicates in input
        original_input_ids_set = set(input_identifiers)
        successful_mappings = {}
        processed_ids = set()
        final_results = {}
        
        # Initialize progress tracking variables
        total_ids = len(original_input_ids_set)
        current_progress = 0
        
        # Report initial progress if callback provided
        if progress_callback:
            progress_callback(current_progress, total_ids, "Starting mapping process")

        # Set default parameter values if not provided
        if max_concurrent_batches is None:
            max_concurrent_batches = 5
        
        if enable_metrics is None:
            enable_metrics = True
            
        # Start overall execution performance tracking
        overall_start_time = time.time()
        self.logger.info(f"TIMING: execute_mapping started for {len(original_input_ids_set)} identifiers")
        
        # --- 0. Initial Setup --- Create a mapping session for logging ---
        setup_start = time.time()
        async with self.async_cache_session() as cache_session:
            mapping_session = await self.session_metrics_service.create_mapping_session_log(
                cache_session,
                source_endpoint_name, target_endpoint_name, source_property_name,
                target_property_name, use_cache, try_reverse_mapping, len(original_input_ids_set),
                max_cache_age_days=max_cache_age_days
            )
            mapping_session_id = mapping_session.id
        self.logger.info(f"TIMING: mapping session setup took {time.time() - setup_start:.3f}s")

        try:
            # --- 1. Get Endpoint Config and Primary Ontologies ---
            config_start = time.time()
            async with self.async_metamapper_session() as meta_session:
                self.logger.info(
                    f"Executing mapping: {source_endpoint_name}.{source_property_name} -> {target_endpoint_name}.{target_property_name}"
                )
                
                # --- Check for composite identifiers and handle if needed ---
                self._composite_initialized = True
                
                # Get the primary source ontology type
                primary_source_ontology = await self.metadata_query_service.get_ontology_type(
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
                        use_composite_handling = False
                    
                    if use_composite_handling:
                        # Use the specialized method that handles composite identifiers
                        return await self._executor.execute_mapping_with_composite_handling(
                            meta_session,
                            input_identifiers,
                            source_endpoint_name,
                            target_endpoint_name,
                            primary_source_ontology,
                            await self.metadata_query_service.get_ontology_type(meta_session, target_endpoint_name, target_property_name),
                            mapping_session_id=mapping_session_id,
                            source_property_name=source_property_name,
                            target_property_name=target_property_name,
                            use_cache=use_cache,
                            max_cache_age_days=max_cache_age_days,
                            mapping_direction=mapping_direction,
                            try_reverse_mapping=try_reverse_mapping
                        )

                # Fetch endpoints and primary ontology types
                source_endpoint = await self._executor._get_endpoint_by_name(meta_session, source_endpoint_name)
                target_endpoint = await self._executor._get_endpoint_by_name(meta_session, target_endpoint_name)
                primary_target_ontology = await self.metadata_query_service.get_ontology_type(
                    meta_session, target_endpoint_name, target_property_name
                )

                # --- Debug Logging ---
                src_prop_name = getattr(source_endpoint, 'primary_property_name', 'NOT_FOUND') if source_endpoint else 'ENDPOINT_NONE'
                tgt_prop_name = getattr(target_endpoint, 'primary_property_name', 'NOT_FOUND') if target_endpoint else 'ENDPOINT_NONE'
                self.logger.info(f"DEBUG: SrcEP PrimaryProp: {src_prop_name}")
                self.logger.info(f"DEBUG: TgtEP PrimaryProp: {tgt_prop_name}")

                # Validate configuration
                if not all([source_endpoint, target_endpoint, primary_source_ontology, primary_target_ontology]):
                    error_message = "Configuration Error: Could not determine endpoints or primary ontologies."
                    self.logger.error(f"{error_message} SourceEndpoint: {source_endpoint}, TargetEndpoint: {target_endpoint}, SourceOntology: {primary_source_ontology}, TargetOntology: {primary_target_ontology}")
                    raise ConfigurationError(error_message)

                self.logger.info(f"Primary mapping ontologies: {primary_source_ontology} -> {primary_target_ontology}")
                self.logger.info(f"TIMING: endpoint configuration took {time.time() - config_start:.3f}s")

                # --- 2. Attempt Direct Primary Mapping ---
                direct_mapping_result = await self.direct_mapping_service.execute_direct_mapping(
                    meta_session=meta_session,
                    path_finder=self.path_finder,
                    path_executor=mapping_executor,  # Use passed mapping_executor
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
                
                # Store the primary path reference
                primary_path = None
                if direct_mapping_result["path_found"]:
                    primary_path = await self.path_finder.find_best_path(
                        meta_session,
                        primary_source_ontology,
                        primary_target_ontology,
                        bidirectional=try_reverse_mapping,
                        source_endpoint=source_endpoint,
                        target_endpoint=target_endpoint,
                    )

                # --- 3, 4, & 5. Iterative Secondary Mapping ---
                self.logger.info("--- Steps 3, 4, & 5: Performing Iterative Secondary Mapping ---")
                secondary_start = time.time()
                unmapped_ids_step3 = list(original_input_ids_set - processed_ids)
                
                iterative_results = await self.iterative_mapping_service.perform_iterative_mapping(
                    unmapped_ids=unmapped_ids_step3,
                    source_endpoint_name=source_endpoint_name,
                    target_endpoint_name=target_endpoint_name,
                    primary_source_ontology=primary_source_ontology,
                    primary_target_ontology=primary_target_ontology,
                    source_property_name=source_property_name,
                    primary_path=primary_path,
                    meta_session=meta_session,
                    mapping_executor=mapping_executor,  # Use passed mapping_executor
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
                
                # Unpack the results
                iterative_successful_mappings, iterative_processed_ids, derived_primary_ids = iterative_results
                
                # Merge the results
                successful_mappings.update(iterative_successful_mappings)
                processed_ids.update(iterative_processed_ids)
                
                self.logger.info(f"TIMING: iterative secondary mapping took {time.time() - secondary_start:.3f}s")

                # --- 6. Bidirectional Validation (if requested) ---
                if validate_bidirectional:
                    successful_mappings = await self.bidirectional_validation_service.validate_mappings(
                        mapping_executor=mapping_executor,  # Use passed mapping_executor
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
            self.logger.error(f"Biomapper Error during mapping execution: {e}", exc_info=True)
            
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
            
            final_results = self.result_aggregation_service.aggregate_error_results(
                successful_mappings=successful_mappings,
                original_input_ids=input_identifiers,
                processed_ids=processed_ids,
                error=e,
                error_status=PathExecutionStatus.ERROR,
            )
            
            return final_results
            
        finally:
            # Update session log upon completion
            if 'mapping_session_id' in locals() and mapping_session_id:
                status = PathExecutionStatus.SUCCESS
                if 'final_results' in locals():
                    if any(r.get("status") == "failure" for r in final_results.values()):
                        status = PathExecutionStatus.PARTIAL_SUCCESS
                elif 'e' in locals():
                    status = PathExecutionStatus.FAILURE
                    
                # Calculate overall execution metrics
                overall_end_time = time.time()
                total_execution_time = overall_end_time - overall_start_time
                
                # Count results
                results_count = len([r for r in final_results.values() if r.get("target_identifiers")])
                
                # Calculate unmapped count
                unmapped_count = 0
                if 'original_input_ids_set' in locals() and 'processed_ids' in locals():
                    unmapped_count = len(original_input_ids_set) - len(processed_ids)
                elif 'original_input_ids_set' in locals() and 'final_results' in locals():
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
                        # Also save performance metrics to database
                        if mapping_session_id:
                            async with self.async_cache_session() as cache_session:
                                await self.session_metrics_service.save_metrics_to_database(cache_session, mapping_session_id, "mapping_execution", execution_metrics)
                    except Exception as e:
                        self.logger.warning(f"Error tracking metrics: {str(e)}")
                
                async with self.async_cache_session() as cache_session:
                    await self.session_metrics_service.update_mapping_session_log(
                        cache_session,
                        mapping_session_id, 
                        status=status,
                        end_time=get_current_utc_time(),
                        results_count=results_count,
                        error_message=str(e) if 'e' in locals() else None
                    )
            else:
                self.logger.error("mapping_session_id not defined, cannot update session log.")


class DbStrategyExecutionService:
    """
    Service for executing database-stored mapping strategies in biomapper's service architecture.
    
    The DbStrategyExecutionService is a specialized service that executes mapping strategies
    stored in the database, allowing for dynamic strategy management without code changes.
    It is part of the execution services layer that the MappingExecutor facade delegates to.
    
    Key Responsibilities:
    - Retrieve mapping strategies from the database by name
    - Execute database-defined strategies with runtime parameters
    - Support dynamic strategy updates without application restart
    - Maintain compatibility with legacy database strategy format
    
    This service enables data-driven configuration of mapping workflows, allowing
    administrators to modify strategies through database updates rather than code changes.
    """
    
    def __init__(
        self,
        strategy_execution_service: LegacyStrategyExecutionService,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the DbStrategyExecutionService.
        
        Args:
            strategy_execution_service: Service for executing strategies
            logger: Optional logger instance
        """
        self.strategy_execution_service = strategy_execution_service
        self.logger = logger or logging.getLogger(__name__)

    async def execute(
        self,
        strategy_name: str,
        initial_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> MappingResultBundle:
        """
        Execute a named mapping strategy from the database.
        
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


class YamlStrategyExecutionService:
    """
    Service for executing YAML-defined mapping strategies in biomapper's service architecture.
    
    The YamlStrategyExecutionService is a specialized service that executes mapping workflows
    defined in YAML configuration files. It is the primary method for defining complex,
    multi-step mapping pipelines and is part of the execution services layer that the
    MappingExecutor facade delegates to.
    
    Key Responsibilities:
    - Load and parse YAML strategy definitions from configuration files
    - Execute multi-step workflows with StrategyAction classes
    - Pass initial context and parameters to strategy steps
    - Orchestrate complex mapping pipelines declaratively
    - Support configuration-driven workflow modifications
    
    This service embodies the configuration-driven philosophy of the new architecture,
    allowing complex mapping logic to be defined and modified without changing code.
    """
    
    def __init__(
        self,
        strategy_orchestrator: StrategyOrchestrator,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the YamlStrategyExecutionService.
        
        Args:
            strategy_orchestrator: Orchestrator for YAML strategies
            logger: Optional logger instance
        """
        self.strategy_orchestrator = strategy_orchestrator
        self.logger = logger or logging.getLogger(__name__)

    async def execute(
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
        
        This method executes a multi-step mapping strategy defined in YAML configuration.
        Each step in the strategy is executed sequentially using dedicated action classes,
        with the output of one step becoming the input for the next.
        
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
        """
        # Delegate to StrategyOrchestrator
        return await self.strategy_orchestrator.execute_strategy(
            strategy_name=strategy_name,
            input_identifiers=input_identifiers,
            initial_context=initial_context,
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
"""
InitializationService to encapsulate component setup for MappingExecutor.

This module contains the InitializationService class which is responsible for:
- Initializing all services and components required by MappingExecutor
- Handling both legacy (config-based) and component-based initialization modes
- Managing the complex setup of services in the correct dependency order
- Returning a dictionary of initialized components for use by MappingExecutor
"""

import logging
import os
from typing import Dict, Any, Optional

# Import composite identifier handling
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin

# Import exceptions
from biomapper.core.exceptions import (
    BiomapperError,
    ConfigurationError,
    ErrorCode,
)

# Import services
from biomapper.core.services import IterativeMappingService
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.services.mapping_path_execution_service import MappingPathExecutionService
from biomapper.core.services.mapping_step_execution_service import MappingStepExecutionService
from biomapper.core.services.strategy_execution_service import StrategyExecutionService
from biomapper.core.services.result_aggregation_service import ResultAggregationService
from biomapper.core.services.bidirectional_validation_service import BidirectionalValidationService
from biomapper.core.services.direct_mapping_service import DirectMappingService
from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService
from biomapper.core.services.execution_services import (
    IterativeExecutionService,
    DbStrategyExecutionService,
    YamlStrategyExecutionService,
)
from biomapper.core.services.mapping_handler_service import MappingHandlerService
from biomapper.core.services.session_metrics_service import SessionMetricsService

# Import engine components
from biomapper.core.engine_components.mapping_executor_initializer import MappingExecutorInitializer
from biomapper.core.engine_components.robust_execution_coordinator import RobustExecutionCoordinator

# Import models
from biomapper.core.models.result_bundle import MappingResultBundle

# Import centralized configuration settings
from biomapper.config import settings


class InitializationService:
    """Service responsible for initializing all components required by MappingExecutor.
    
    This service encapsulates the complex initialization logic that was previously
    in MappingExecutor.__init__, providing a clean separation of initialization
    concerns from the core execution logic.
    """
    
    def __init__(self):
        """Initialize the InitializationService."""
        self.logger = logging.getLogger(__name__)
    
    def initialize_components(
        self,
        mapping_executor,
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
    ) -> Dict[str, Any]:
        """Initialize all components required by MappingExecutor.
        
        This method handles both legacy (configuration-based) and component-based
        initialization modes. It returns a dictionary containing all initialized
        services and components.
        
        Args:
            mapping_executor: The MappingExecutor instance being initialized
            metamapper_db_url: URL for the metamapper database (legacy mode)
            mapping_cache_db_url: URL for the mapping cache database (legacy mode)
            echo_sql: Boolean flag to enable SQL echoing (legacy mode)
            path_cache_size: Maximum number of paths to cache (legacy mode)
            path_cache_expiry_seconds: Cache expiry time in seconds (legacy mode)
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
            session_manager: Pre-initialized SessionManager instance (component mode)
            client_manager: Pre-initialized ClientManager instance (component mode)
            config_loader: Pre-initialized ConfigLoader instance (component mode)
            strategy_handler: Pre-initialized StrategyHandler instance (component mode)
            path_finder: Pre-initialized PathFinder instance (component mode)
            path_execution_manager: Pre-initialized PathExecutionManager instance (component mode)
            cache_manager: Pre-initialized CacheManager instance (component mode)
            identifier_loader: Pre-initialized IdentifierLoader instance (component mode)
            strategy_orchestrator: Pre-initialized StrategyOrchestrator instance (component mode)
            checkpoint_manager: Pre-initialized CheckpointManager instance (component mode)
            progress_reporter: Pre-initialized ProgressReporter instance (component mode)
            langfuse_tracker: Pre-initialized Langfuse tracker instance (component mode)
            
        Returns:
            Dictionary containing all initialized components
        """
        components = {}
        
        # Check if we're in legacy mode (configuration parameters) or component mode
        if session_manager is None:
            # Legacy mode: use MappingExecutorInitializer to create components
            self.logger.debug("Initializing components in legacy mode")
            
            # Store configuration parameters in mapping_executor
            mapping_executor.batch_size = batch_size
            mapping_executor.max_retries = max_retries
            mapping_executor.retry_delay = retry_delay
            mapping_executor.checkpoint_enabled = checkpoint_enabled
            mapping_executor.max_concurrent_batches = max_concurrent_batches
            mapping_executor.enable_metrics = enable_metrics
            mapping_executor._metrics_tracker = None
            
            # Initialize all components using the MappingExecutorInitializer
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
                retry_delay=retry_delay
            )
            
            # Initialize all components
            initialized_components = initializer.initialize_components(mapping_executor)
            
            # Extract components from initializer
            components['session_manager'] = initialized_components['session_manager']
            components['client_manager'] = initialized_components['client_manager']
            components['config_loader'] = initialized_components['config_loader']
            components['strategy_handler'] = initialized_components['strategy_handler']
            components['path_finder'] = initialized_components['path_finder']
            components['path_execution_manager'] = initialized_components['path_execution_manager']
            components['cache_manager'] = initialized_components['cache_manager']
            components['identifier_loader'] = initialized_components['identifier_loader']
            components['strategy_orchestrator'] = initialized_components['strategy_orchestrator']
            components['checkpoint_manager'] = initialized_components['checkpoint_manager']
            components['progress_reporter'] = initialized_components['progress_reporter']
            components['langfuse_tracker'] = initialized_components['langfuse_tracker']
            
            # Get convenience references for backward compatibility
            convenience_refs = initializer.get_convenience_references()
            components['async_metamapper_engine'] = convenience_refs['async_metamapper_engine']
            components['MetamapperSessionFactory'] = convenience_refs['MetamapperSessionFactory']
            components['async_metamapper_session'] = convenience_refs['async_metamapper_session']
            components['async_cache_engine'] = convenience_refs['async_cache_engine']
            components['CacheSessionFactory'] = convenience_refs['CacheSessionFactory']
            components['async_cache_session'] = convenience_refs['async_cache_session']
            
            # Set function references after MappingExecutor is fully initialized
            initializer.set_executor_function_references(mapping_executor)
            
            # Store DB URLs for backward compatibility
            components['metamapper_db_url'] = metamapper_db_url if metamapper_db_url else settings.metamapper_db_url
            components['mapping_cache_db_url'] = mapping_cache_db_url if mapping_cache_db_url else settings.cache_db_url
            components['echo_sql'] = echo_sql
            
        else:
            # Component mode: use pre-initialized components
            self.logger.debug("Initializing components in component mode")
            
            # Store configuration parameters in mapping_executor
            mapping_executor.batch_size = batch_size
            mapping_executor.max_retries = max_retries
            mapping_executor.retry_delay = retry_delay
            mapping_executor.checkpoint_enabled = checkpoint_enabled
            mapping_executor.max_concurrent_batches = max_concurrent_batches
            mapping_executor.enable_metrics = enable_metrics
            
            # Store pre-initialized components
            components['session_manager'] = session_manager
            components['client_manager'] = client_manager
            components['config_loader'] = config_loader
            components['strategy_handler'] = strategy_handler
            components['path_finder'] = path_finder
            components['path_execution_manager'] = path_execution_manager
            components['cache_manager'] = cache_manager
            components['identifier_loader'] = identifier_loader
            components['strategy_orchestrator'] = strategy_orchestrator
            components['checkpoint_manager'] = checkpoint_manager
            components['progress_reporter'] = progress_reporter
            components['langfuse_tracker'] = langfuse_tracker
            components['_metrics_tracker'] = None
            
            # Create convenience references for backward compatibility
            components['async_metamapper_engine'] = session_manager.async_metamapper_engine
            components['MetamapperSessionFactory'] = session_manager.MetamapperSessionFactory
            components['async_metamapper_session'] = session_manager.async_metamapper_session
            components['async_cache_engine'] = session_manager.async_cache_engine
            components['CacheSessionFactory'] = session_manager.CacheSessionFactory
            components['async_cache_session'] = session_manager.async_cache_session
            
            # Store DB URLs for backward compatibility (extract from session_manager)
            components['metamapper_db_url'] = str(session_manager.async_metamapper_engine.url)
            components['mapping_cache_db_url'] = str(session_manager.async_cache_engine.url)
            components['echo_sql'] = session_manager.async_metamapper_engine.echo
        
        # Initialize services that depend on the core components
        components['metadata_query_service'] = MetadataQueryService(components['session_manager'])
        
        # Initialize SessionMetricsService
        components['session_metrics_service'] = SessionMetricsService()
        
        # Initialize MappingHandlerService
        components['mapping_handler_service'] = MappingHandlerService(
            logger=self.logger,
            client_manager=components['client_manager'],
            path_finder=components['path_finder'],
            async_metamapper_session=components['async_metamapper_session'],
            metadata_query_service=components['metadata_query_service'],
        )
        
        # Initialize BidirectionalValidationService
        components['bidirectional_validation_service'] = BidirectionalValidationService()
        
        # Initialize DirectMappingService
        components['direct_mapping_service'] = DirectMappingService(logger=self.logger)
        
        # Initialize MappingStepExecutionService
        components['step_execution_service'] = MappingStepExecutionService(
            client_manager=components['client_manager'],
            cache_manager=components['cache_manager'],
            logger=self.logger
        )
        
        # Initialize IterativeMappingService
        components['iterative_mapping_service'] = IterativeMappingService(logger=self.logger)
        
        # Initialize MappingPathExecutionService with all required arguments
        components['path_execution_service'] = MappingPathExecutionService(
            session_manager=components['session_manager'],
            client_manager=components['client_manager'],
            cache_manager=components['cache_manager'],
            path_finder=components['path_finder'],
            path_execution_manager=components['path_execution_manager'],
            composite_handler=mapping_executor,  # MappingExecutor implements composite handling
            step_execution_service=components['step_execution_service'],
            logger=self.logger
        )
        
        # Set executor reference for delegation
        components['path_execution_service'].set_executor(mapping_executor)
        
        # Initialize ExecutionLifecycleService
        components['lifecycle_service'] = ExecutionLifecycleService(
            checkpoint_manager=components['checkpoint_manager'],
            progress_reporter=components['progress_reporter'],
            metrics_manager=components['langfuse_tracker']
        )
        
        # Initialize RobustExecutionCoordinator
        components['robust_execution_coordinator'] = RobustExecutionCoordinator(
            strategy_orchestrator=components['strategy_orchestrator'],
            checkpoint_manager=components['checkpoint_manager'],
            progress_reporter=components['progress_reporter'],
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            checkpoint_enabled=checkpoint_enabled,
            logger=self.logger
        )
        
        # Initialize metrics tracker if needed
        if enable_metrics:
            try:
                from biomapper.monitoring.metrics import MetricsTracker
                components['_metrics_tracker'] = MetricsTracker(
                    langfuse=components['langfuse_tracker']
                )
            except ImportError:
                self.logger.warning("MetricsTracker not available - langfuse module not installed")
                components['_metrics_tracker'] = None
        else:
            components['_metrics_tracker'] = None
        
        # Initialize MappingResultBundle (extracted module)
        components['MappingResultBundle'] = MappingResultBundle
        
        # Initialize StrategyExecutionService
        components['strategy_execution_service'] = StrategyExecutionService(
            strategy_orchestrator=components['strategy_orchestrator'],
            robust_execution_coordinator=components['robust_execution_coordinator'],
            logger=self.logger
        )
        
        # Initialize ResultAggregationService
        components['result_aggregation_service'] = ResultAggregationService(logger=self.logger)
        
        # Initialize the new execution services
        components['iterative_execution_service'] = IterativeExecutionService(
            direct_mapping_service=components['direct_mapping_service'],
            iterative_mapping_service=components['iterative_mapping_service'],
            bidirectional_validation_service=components['bidirectional_validation_service'],
            result_aggregation_service=components['result_aggregation_service'],
            path_finder=components['path_finder'],
            composite_handler=mapping_executor,
            async_metamapper_session=components['async_metamapper_session'],
            metadata_query_service=components['metadata_query_service'],
            logger=self.logger,
        )
        # Set the executor reference
        components['iterative_execution_service'].set_executor(mapping_executor)
        
        components['db_strategy_execution_service'] = DbStrategyExecutionService(
            strategy_execution_service=components['strategy_execution_service'],
            logger=self.logger,
        )
        
        components['yaml_strategy_execution_service'] = YamlStrategyExecutionService(
            strategy_orchestrator=components['strategy_orchestrator'],
            logger=self.logger,
        )
        
        self.logger.info("All components initialized successfully")
        
        return components
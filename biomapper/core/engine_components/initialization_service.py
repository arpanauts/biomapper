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
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.engine_components.client_manager import ClientManager
from biomapper.core.engine_components.config_loader import ConfigLoader
from biomapper.core.engine_components.strategy_handler import StrategyHandler
from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.engine_components.path_execution_manager import PathExecutionManager
from biomapper.core.engine_components.cache_manager import CacheManager
from biomapper.core.engine_components.identifier_loader import IdentifierLoader
from biomapper.core.engine_components.strategy_orchestrator import StrategyOrchestrator
from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.engine_components.progress_reporter import ProgressReporter
from biomapper.core.engine_components.robust_execution_coordinator import RobustExecutionCoordinator

# Import models
from biomapper.core.models.result_bundle import MappingResultBundle

# Import centralized configuration settings
from biomapper.config import settings

# Import cache models for database initialization
from biomapper.db.cache_models import Base as CacheBase


class InitializationService:
    """Service responsible for initializing all components required by MappingExecutor.
    
    This service encapsulates the complex initialization logic that was previously
    in MappingExecutor.__init__, providing a clean separation of initialization
    concerns from the core execution logic.
    
    This is now the single source of truth for creating ALL individual, low-level
    service components from a configuration dictionary.
    """
    
    def __init__(self):
        """Initialize the InitializationService."""
        self.logger = logging.getLogger(__name__)
    
    def create_components(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for create_components_from_config for backward compatibility."""
        return self.create_components_from_config(config)
    
    def create_components_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create all components from a configuration dictionary.
        
        This is the primary method that takes a config dict and creates all
        initialized low-level services by calling individual creation methods.
        
        Args:
            config: Configuration dictionary containing all initialization parameters
                Required keys:
                - metamapper_db_url: URL for the metamapper database
                - mapping_cache_db_url: URL for the mapping cache database
                Optional keys:
                - echo_sql: Boolean flag to enable SQL echoing (default: False)
                - path_cache_size: Maximum number of paths to cache (default: 100)
                - path_cache_expiry_seconds: Cache expiry time in seconds (default: 300)
                - max_concurrent_batches: Maximum number of batches to process concurrently (default: 5)
                - enable_metrics: Whether to enable metrics tracking (default: True)
                - checkpoint_enabled: Enable checkpointing for resumable execution (default: False)
                - checkpoint_dir: Directory for checkpoint files (default: None)
                - batch_size: Number of items to process per batch (default: 100)
                - max_retries: Maximum retry attempts for failed operations (default: 3)
                - retry_delay: Delay in seconds between retry attempts (default: 5)
                
        Returns:
            Dictionary containing all initialized components
        """
        self.logger.info("Creating all components from configuration dictionary")
        
        # Extract configuration with defaults
        metamapper_db_url = config.get('metamapper_db_url', settings.metamapper_db_url)
        mapping_cache_db_url = config.get('mapping_cache_db_url', settings.cache_db_url)
        echo_sql = config.get('echo_sql', False)
        path_cache_size = config.get('path_cache_size', 100)
        path_cache_expiry_seconds = config.get('path_cache_expiry_seconds', 300)
        max_concurrent_batches = config.get('max_concurrent_batches', 5)
        enable_metrics = config.get('enable_metrics', True)
        checkpoint_enabled = config.get('checkpoint_enabled', False)
        checkpoint_dir = config.get('checkpoint_dir', None)
        batch_size = config.get('batch_size', 100)
        max_retries = config.get('max_retries', 3)
        retry_delay = config.get('retry_delay', 5)
        
        # Initialize components dictionary
        components = {}
        
        # Step 1: Create core components that don't depend on others
        components['checkpoint_manager'] = self._create_checkpoint_manager(checkpoint_enabled, checkpoint_dir)
        components['progress_reporter'] = self._create_progress_reporter()
        components['client_manager'] = self._create_client_manager()
        components['config_loader'] = self._create_config_loader()
        components['path_finder'] = self._create_path_finder(path_cache_size, path_cache_expiry_seconds)
        
        # Step 2: Create session manager and related components
        components['session_manager'] = self._create_session_manager(
            metamapper_db_url, mapping_cache_db_url, echo_sql
        )
        
        # Add convenience references
        components.update(self._get_session_convenience_references(components['session_manager']))
        
        # Step 3: Create components that depend on session manager
        components['cache_manager'] = self._create_cache_manager(components['session_manager'])
        components['identifier_loader'] = self._create_identifier_loader(components['session_manager'])
        
        # Step 4: Create Langfuse tracker if metrics are enabled
        components['langfuse_tracker'] = self._create_langfuse_tracker(enable_metrics)
        
        # Step 5: Create components that need a mapping_executor reference (will be set later)
        components['strategy_handler'] = self._create_strategy_handler(None)  # Will set executor later
        components['path_execution_manager'] = self._create_path_execution_manager(
            components['session_manager'],
            components['cache_manager'],
            max_retries,
            retry_delay,
            batch_size,
            max_concurrent_batches,
            enable_metrics
        )
        components['strategy_orchestrator'] = self._create_strategy_orchestrator(
            components['session_manager'],
            components['cache_manager'],
            components['strategy_handler'],
            None  # Will set executor later
        )
        
        # Step 6: Create basic services
        components['metadata_query_service'] = self._create_metadata_query_service(components['session_manager'])
        components['session_metrics_service'] = self._create_session_metrics_service()
        components['bidirectional_validation_service'] = self._create_bidirectional_validation_service()
        components['direct_mapping_service'] = self._create_direct_mapping_service()
        components['result_aggregation_service'] = self._create_result_aggregation_service()
        components['iterative_mapping_service'] = self._create_iterative_mapping_service()
        
        # Step 7: Create MappingHandlerService
        components['mapping_handler_service'] = self._create_mapping_handler_service(
            components['client_manager'],
            components['path_finder'],
            components['async_metamapper_session'],
            components['metadata_query_service']
        )
        
        # Step 8: Create MappingStepExecutionService
        components['step_execution_service'] = self._create_mapping_step_execution_service(
            components['client_manager'],
            components['cache_manager']
        )
        
        # Step 9: Create MappingPathExecutionService (needs composite_handler which will be mapping_executor)
        # This will be created later when mapping_executor is available
        
        # Step 10: Create lifecycle and execution coordinator services
        components['lifecycle_service'] = self._create_execution_lifecycle_service(
            components['checkpoint_manager'],
            components['progress_reporter'],
            components['langfuse_tracker']
        )
        
        components['robust_execution_coordinator'] = self._create_robust_execution_coordinator(
            components['strategy_orchestrator'],
            components['checkpoint_manager'],
            components['progress_reporter'],
            batch_size,
            max_retries,
            retry_delay,
            checkpoint_enabled
        )
        
        # Step 11: Create strategy execution service
        components['strategy_execution_service'] = self._create_strategy_execution_service(
            components['strategy_orchestrator'],
            components['robust_execution_coordinator']
        )
        
        # Step 12: Create db and yaml strategy execution services
        components['db_strategy_execution_service'] = self._create_db_strategy_execution_service(
            components['strategy_execution_service']
        )
        
        components['yaml_strategy_execution_service'] = self._create_yaml_strategy_execution_service(
            components['strategy_orchestrator']
        )
        
        # Step 13: Store additional items
        components['MappingResultBundle'] = MappingResultBundle
        components['_metrics_tracker'] = None  # Will be set later if needed
        
        # Store configuration parameters for later use
        components['config'] = {
            'metamapper_db_url': metamapper_db_url,
            'mapping_cache_db_url': mapping_cache_db_url,
            'echo_sql': echo_sql,
            'batch_size': batch_size,
            'max_retries': max_retries,
            'retry_delay': retry_delay,
            'checkpoint_enabled': checkpoint_enabled,
            'max_concurrent_batches': max_concurrent_batches,
            'enable_metrics': enable_metrics,
        }
        
        self.logger.info("All components created successfully from configuration")
        return components
    
    def complete_initialization(self, mapping_executor, components: Dict[str, Any]) -> Dict[str, Any]:
        """Complete initialization of components that require mapping_executor reference.
        
        This method should be called after the MappingExecutor instance is created to
        finalize components that need a reference to it.
        
        Args:
            mapping_executor: The MappingExecutor instance
            components: Dictionary of initialized components from create_components_from_config
            
        Returns:
            Updated components dictionary with all services fully initialized
        """
        self.logger.info("Completing component initialization with mapping_executor reference")
        
        # Update components that need mapping_executor reference
        components['strategy_handler'].mapping_executor = mapping_executor
        components['strategy_orchestrator'].mapping_executor = mapping_executor
        
        # Create services that depend on mapping_executor
        components['path_execution_service'] = self._create_mapping_path_execution_service(
            components['session_manager'],
            components['client_manager'],
            components['cache_manager'],
            components['path_finder'],
            components['path_execution_manager'],
            mapping_executor,  # composite_handler
            components['step_execution_service']
        )
        
        # Create iterative execution service (needs composite_handler)
        components['iterative_execution_service'] = self._create_iterative_execution_service(
            components['direct_mapping_service'],
            components['iterative_mapping_service'],
            components['bidirectional_validation_service'],
            components['result_aggregation_service'],
            components['path_finder'],
            mapping_executor,  # composite_handler
            components['async_metamapper_session'],
            components['async_cache_session'],
            components['metadata_query_service'],
            components['session_metrics_service']
        )
        
        # Set function references on PathExecutionManager
        self.set_executor_function_references(mapping_executor, components['path_execution_manager'])
        
        # Initialize metrics tracker if needed
        if components['config']['enable_metrics']:
            try:
                from biomapper.monitoring.metrics import MetricsTracker
                components['_metrics_tracker'] = MetricsTracker(
                    langfuse=components['langfuse_tracker']
                )
            except ImportError:
                self.logger.warning("MetricsTracker not available - langfuse module not installed")
                components['_metrics_tracker'] = None
        
        self.logger.info("Component initialization completed")
        return components
    
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
            # Legacy mode: use our new create_components_from_config method
            self.logger.debug("Initializing components in legacy mode")
            
            # Store configuration parameters in mapping_executor
            mapping_executor.batch_size = batch_size
            mapping_executor.max_retries = max_retries
            mapping_executor.retry_delay = retry_delay
            mapping_executor.checkpoint_enabled = checkpoint_enabled
            mapping_executor.max_concurrent_batches = max_concurrent_batches
            mapping_executor.enable_metrics = enable_metrics
            mapping_executor._metrics_tracker = None
            
            # Create configuration dictionary
            config = {
                'metamapper_db_url': metamapper_db_url,
                'mapping_cache_db_url': mapping_cache_db_url,
                'echo_sql': echo_sql,
                'path_cache_size': path_cache_size,
                'path_cache_expiry_seconds': path_cache_expiry_seconds,
                'max_concurrent_batches': max_concurrent_batches,
                'enable_metrics': enable_metrics,
                'checkpoint_enabled': checkpoint_enabled,
                'checkpoint_dir': checkpoint_dir,
                'batch_size': batch_size,
                'max_retries': max_retries,
                'retry_delay': retry_delay,
            }
            
            # Use create_components_from_config to initialize all components
            components = self.create_components_from_config(config)
            
            # Complete initialization with mapping_executor reference
            components = self.complete_initialization(mapping_executor, components)
            
            # Store DB URLs for backward compatibility
            components['metamapper_db_url'] = components['config']['metamapper_db_url']
            components['mapping_cache_db_url'] = components['config']['mapping_cache_db_url']
            components['echo_sql'] = components['config']['echo_sql']
            
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
            components.update(self._get_session_convenience_references(session_manager))
            
            # Store DB URLs for backward compatibility (extract from session_manager)
            components['metamapper_db_url'] = str(session_manager.async_metamapper_engine.url)
            components['mapping_cache_db_url'] = str(session_manager.async_cache_engine.url)
            components['echo_sql'] = session_manager.async_metamapper_engine.echo
            
            # Store configuration for consistency
            components['config'] = {
                'metamapper_db_url': components['metamapper_db_url'],
                'mapping_cache_db_url': components['mapping_cache_db_url'],
                'echo_sql': components['echo_sql'],
                'batch_size': batch_size,
                'max_retries': max_retries,
                'retry_delay': retry_delay,
                'checkpoint_enabled': checkpoint_enabled,
                'max_concurrent_batches': max_concurrent_batches,
                'enable_metrics': enable_metrics,
            }
            
            # Initialize remaining services using our creation methods
            components['metadata_query_service'] = self._create_metadata_query_service(components['session_manager'])
            components['session_metrics_service'] = self._create_session_metrics_service()
            components['bidirectional_validation_service'] = self._create_bidirectional_validation_service()
            components['direct_mapping_service'] = self._create_direct_mapping_service()
            components['result_aggregation_service'] = self._create_result_aggregation_service()
            components['iterative_mapping_service'] = self._create_iterative_mapping_service()
            
            components['mapping_handler_service'] = self._create_mapping_handler_service(
                components['client_manager'],
                components['path_finder'],
                components['async_metamapper_session'],
                components['metadata_query_service']
            )
            
            components['step_execution_service'] = self._create_mapping_step_execution_service(
                components['client_manager'],
                components['cache_manager']
            )
            
            components['lifecycle_service'] = self._create_execution_lifecycle_service(
                components['checkpoint_manager'],
                components['progress_reporter'],
                components['langfuse_tracker']
            )
            
            components['robust_execution_coordinator'] = self._create_robust_execution_coordinator(
                components['strategy_orchestrator'],
                components['checkpoint_manager'],
                components['progress_reporter'],
                batch_size,
                max_retries,
                retry_delay,
                checkpoint_enabled
            )
            
            components['strategy_execution_service'] = self._create_strategy_execution_service(
                components['strategy_orchestrator'],
                components['robust_execution_coordinator']
            )
            
            components['db_strategy_execution_service'] = self._create_db_strategy_execution_service(
                components['strategy_execution_service']
            )
            
            components['yaml_strategy_execution_service'] = self._create_yaml_strategy_execution_service(
                components['strategy_orchestrator']
            )
            
            # Create services that depend on mapping_executor
            components['path_execution_service'] = self._create_mapping_path_execution_service(
                components['session_manager'],
                components['client_manager'],
                components['cache_manager'],
                components['path_finder'],
                components['path_execution_manager'],
                mapping_executor,
                components['step_execution_service']
            )
            
            components['iterative_execution_service'] = self._create_iterative_execution_service(
                components['direct_mapping_service'],
                components['iterative_mapping_service'],
                components['bidirectional_validation_service'],
                components['result_aggregation_service'],
                components['path_finder'],
                mapping_executor,
                components['async_metamapper_session'],
                components['async_cache_session'],
                components['metadata_query_service'],
                components['session_metrics_service']
            )
            
            # Set executor references
            components['path_execution_service'].set_executor(mapping_executor)
            components['iterative_execution_service'].set_executor(mapping_executor)
            
            # Store additional items
            components['MappingResultBundle'] = MappingResultBundle
            
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
        
        self.logger.info("All components initialized successfully")
        
        return components
    
    # ============================================================================
    # Individual component creation methods
    # ============================================================================
    
    def _create_checkpoint_manager(self, checkpoint_enabled: bool, checkpoint_dir: Optional[str]) -> CheckpointManager:
        """Create and return a CheckpointManager instance."""
        self.logger.debug("Creating CheckpointManager")
        return CheckpointManager(
            checkpoint_dir=checkpoint_dir if checkpoint_enabled else None,
            logger=self.logger
        )
    
    def _create_progress_reporter(self) -> ProgressReporter:
        """Create and return a ProgressReporter instance."""
        self.logger.debug("Creating ProgressReporter")
        return ProgressReporter()
    
    def _create_client_manager(self) -> ClientManager:
        """Create and return a ClientManager instance."""
        self.logger.debug("Creating ClientManager")
        return ClientManager(logger=self.logger)
    
    def _create_config_loader(self) -> ConfigLoader:
        """Create and return a ConfigLoader instance."""
        self.logger.debug("Creating ConfigLoader")
        return ConfigLoader(logger=self.logger)
    
    def _create_path_finder(self, cache_size: int, cache_expiry_seconds: int) -> PathFinder:
        """Create and return a PathFinder instance."""
        self.logger.debug("Creating PathFinder")
        return PathFinder(
            cache_size=cache_size,
            cache_expiry_seconds=cache_expiry_seconds
        )
    
    def _create_session_manager(
        self, 
        metamapper_db_url: str, 
        mapping_cache_db_url: str, 
        echo_sql: bool
    ) -> SessionManager:
        """Create and return a SessionManager instance."""
        self.logger.debug("Creating SessionManager")
        return SessionManager(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=mapping_cache_db_url,
            echo_sql=echo_sql
        )
    
    def _get_session_convenience_references(self, session_manager: SessionManager) -> Dict[str, Any]:
        """Get convenience references from SessionManager for backward compatibility."""
        return {
            'async_metamapper_engine': session_manager.async_metamapper_engine,
            'MetamapperSessionFactory': session_manager.MetamapperSessionFactory,
            'async_metamapper_session': session_manager.async_metamapper_session,
            'async_cache_engine': session_manager.async_cache_engine,
            'CacheSessionFactory': session_manager.CacheSessionFactory,
            'async_cache_session': session_manager.async_cache_session,
        }
    
    def _create_cache_manager(self, session_manager: SessionManager) -> CacheManager:
        """Create and return a CacheManager instance."""
        self.logger.debug("Creating CacheManager")
        return CacheManager(
            cache_sessionmaker=session_manager.CacheSessionFactory,
            logger=self.logger
        )
    
    def _create_identifier_loader(self, session_manager: SessionManager) -> IdentifierLoader:
        """Create and return an IdentifierLoader instance."""
        self.logger.debug("Creating IdentifierLoader")
        return IdentifierLoader(
            metamapper_session_factory=session_manager.MetamapperSessionFactory
        )
    
    def _create_langfuse_tracker(self, enable_metrics: bool) -> Optional[Any]:
        """Create and return a Langfuse tracker instance if metrics are enabled."""
        if not enable_metrics:
            self.logger.debug("Metrics tracking disabled")
            return None
        
        try:
            import langfuse
            tracker = langfuse.Langfuse(
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
            )
            self.logger.info("Langfuse metrics tracking initialized")
            return tracker
        except (ImportError, Exception) as e:
            self.logger.warning(f"Langfuse metrics tracking not available: {e}")
            return None
    
    def _create_strategy_handler(self, mapping_executor) -> StrategyHandler:
        """Create and return a StrategyHandler instance."""
        self.logger.debug("Creating StrategyHandler")
        return StrategyHandler(mapping_executor=mapping_executor)
    
    def _create_path_execution_manager(
        self,
        session_manager: SessionManager,
        cache_manager: CacheManager,
        max_retries: int,
        retry_delay: int,
        batch_size: int,
        max_concurrent_batches: int,
        enable_metrics: bool
    ) -> PathExecutionManager:
        """Create and return a PathExecutionManager instance."""
        self.logger.debug("Creating PathExecutionManager")
        return PathExecutionManager(
            metamapper_session_factory=session_manager.MetamapperSessionFactory,
            cache_manager=None,  # MappingExecutor handles caching directly
            logger=self.logger,
            semaphore=None,  # Will create semaphore as needed
            max_retries=max_retries,
            retry_delay=retry_delay,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            enable_metrics=enable_metrics,
            load_client_func=None,  # Will be set after MappingExecutor is fully initialized
            execute_mapping_step_func=None,  # Will be set after MappingExecutor is fully initialized
            calculate_confidence_score_func=None,  # Will be set after MappingExecutor is fully initialized
            create_mapping_path_details_func=None,  # Will be set after MappingExecutor is fully initialized
            determine_mapping_source_func=None,  # Will be set after MappingExecutor is fully initialized
            track_mapping_metrics_func=None  # Will be set after MappingExecutor is fully initialized
        )
    
    def _create_strategy_orchestrator(
        self,
        session_manager: SessionManager,
        cache_manager: CacheManager,
        strategy_handler: StrategyHandler,
        mapping_executor
    ) -> StrategyOrchestrator:
        """Create and return a StrategyOrchestrator instance."""
        self.logger.debug("Creating StrategyOrchestrator")
        return StrategyOrchestrator(
            metamapper_session_factory=session_manager.MetamapperSessionFactory,
            cache_manager=cache_manager,
            strategy_handler=strategy_handler,
            mapping_executor=mapping_executor,  # Pass self for backwards compatibility
            logger=self.logger
        )
    
    def _create_metadata_query_service(self, session_manager: SessionManager) -> MetadataQueryService:
        """Create and return a MetadataQueryService instance."""
        self.logger.debug("Creating MetadataQueryService")
        return MetadataQueryService(session_manager)
    
    def _create_session_metrics_service(self) -> SessionMetricsService:
        """Create and return a SessionMetricsService instance."""
        self.logger.debug("Creating SessionMetricsService")
        return SessionMetricsService()
    
    def _create_bidirectional_validation_service(self) -> BidirectionalValidationService:
        """Create and return a BidirectionalValidationService instance."""
        self.logger.debug("Creating BidirectionalValidationService")
        return BidirectionalValidationService()
    
    def _create_direct_mapping_service(self) -> DirectMappingService:
        """Create and return a DirectMappingService instance."""
        self.logger.debug("Creating DirectMappingService")
        return DirectMappingService(logger=self.logger)
    
    def _create_result_aggregation_service(self) -> ResultAggregationService:
        """Create and return a ResultAggregationService instance."""
        self.logger.debug("Creating ResultAggregationService")
        return ResultAggregationService(logger=self.logger)
    
    def _create_mapping_handler_service(
        self,
        client_manager: ClientManager,
        path_finder: PathFinder,
        async_metamapper_session,
        metadata_query_service: MetadataQueryService
    ) -> MappingHandlerService:
        """Create and return a MappingHandlerService instance."""
        self.logger.debug("Creating MappingHandlerService")
        return MappingHandlerService(
            logger=self.logger,
            client_manager=client_manager,
            path_finder=path_finder,
            async_metamapper_session=async_metamapper_session,
            metadata_query_service=metadata_query_service,
        )
    
    def _create_mapping_step_execution_service(
        self,
        client_manager: ClientManager,
        cache_manager: CacheManager
    ) -> MappingStepExecutionService:
        """Create and return a MappingStepExecutionService instance."""
        self.logger.debug("Creating MappingStepExecutionService")
        return MappingStepExecutionService(
            client_manager=client_manager,
            cache_manager=cache_manager,
            logger=self.logger
        )
    
    def _create_iterative_mapping_service(self) -> IterativeMappingService:
        """Create and return an IterativeMappingService instance."""
        self.logger.debug("Creating IterativeMappingService")
        return IterativeMappingService(logger=self.logger)
    
    def _create_mapping_path_execution_service(
        self,
        session_manager: SessionManager,
        client_manager: ClientManager,
        cache_manager: CacheManager,
        path_finder: PathFinder,
        path_execution_manager: PathExecutionManager,
        composite_handler,
        step_execution_service: MappingStepExecutionService
    ) -> MappingPathExecutionService:
        """Create and return a MappingPathExecutionService instance."""
        self.logger.debug("Creating MappingPathExecutionService")
        return MappingPathExecutionService(
            session_manager=session_manager,
            client_manager=client_manager,
            cache_manager=cache_manager,
            path_finder=path_finder,
            path_execution_manager=path_execution_manager,
            composite_handler=composite_handler,
            step_execution_service=step_execution_service,
            logger=self.logger
        )
    
    def _create_execution_lifecycle_service(
        self,
        checkpoint_manager: CheckpointManager,
        progress_reporter: ProgressReporter,
        metrics_manager
    ) -> ExecutionLifecycleService:
        """Create and return an ExecutionLifecycleService instance."""
        self.logger.debug("Creating ExecutionLifecycleService")
        return ExecutionLifecycleService(
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            metrics_manager=metrics_manager
        )
    
    def _create_robust_execution_coordinator(
        self,
        strategy_orchestrator: StrategyOrchestrator,
        checkpoint_manager: CheckpointManager,
        progress_reporter: ProgressReporter,
        batch_size: int,
        max_retries: int,
        retry_delay: int,
        checkpoint_enabled: bool
    ) -> RobustExecutionCoordinator:
        """Create and return a RobustExecutionCoordinator instance."""
        self.logger.debug("Creating RobustExecutionCoordinator")
        return RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
            checkpoint_enabled=checkpoint_enabled,
            logger=self.logger
        )
    
    def _create_strategy_execution_service(
        self,
        strategy_orchestrator: StrategyOrchestrator,
        robust_execution_coordinator: RobustExecutionCoordinator
    ) -> StrategyExecutionService:
        """Create and return a StrategyExecutionService instance."""
        self.logger.debug("Creating StrategyExecutionService")
        return StrategyExecutionService(
            strategy_orchestrator=strategy_orchestrator,
            robust_execution_coordinator=robust_execution_coordinator,
            logger=self.logger
        )
    
    def _create_iterative_execution_service(
        self,
        direct_mapping_service: DirectMappingService,
        iterative_mapping_service: IterativeMappingService,
        bidirectional_validation_service: BidirectionalValidationService,
        result_aggregation_service: ResultAggregationService,
        path_finder: PathFinder,
        composite_handler,
        async_metamapper_session,
        async_cache_session,
        metadata_query_service: MetadataQueryService,
        session_metrics_service: SessionMetricsService
    ) -> IterativeExecutionService:
        """Create and return an IterativeExecutionService instance."""
        self.logger.debug("Creating IterativeExecutionService")
        return IterativeExecutionService(
            direct_mapping_service=direct_mapping_service,
            iterative_mapping_service=iterative_mapping_service,
            bidirectional_validation_service=bidirectional_validation_service,
            result_aggregation_service=result_aggregation_service,
            path_finder=path_finder,
            composite_handler=composite_handler,
            async_metamapper_session=async_metamapper_session,
            async_cache_session=async_cache_session,
            metadata_query_service=metadata_query_service,
            session_metrics_service=session_metrics_service,
            logger=self.logger
        )
        

        # Initialize SessionMetricsService
        components['session_metrics_service'] = SessionMetricsService()
        
        # Initialize the new execution services
        components['iterative_execution_service'] = IterativeExecutionService(
            direct_mapping_service=components['direct_mapping_service'],
            iterative_mapping_service=components['iterative_mapping_service'],
            bidirectional_validation_service=components['bidirectional_validation_service'],
            result_aggregation_service=components['result_aggregation_service'],
            path_finder=components['path_finder'],
            composite_handler=mapping_executor,
            async_metamapper_session=components['async_metamapper_session'],
            async_cache_session=components['async_cache_session'],
            metadata_query_service=components['metadata_query_service'],
            session_metrics_service=components['session_metrics_service'],
            logger=self.logger,
        )
    
    def _create_db_strategy_execution_service(
        self,
        strategy_execution_service: StrategyExecutionService
    ) -> DbStrategyExecutionService:
        """Create and return a DbStrategyExecutionService instance."""
        self.logger.debug("Creating DbStrategyExecutionService")
        return DbStrategyExecutionService(
            strategy_execution_service=strategy_execution_service,
            logger=self.logger,
        )
    
    def _create_yaml_strategy_execution_service(
        self,
        strategy_orchestrator: StrategyOrchestrator
    ) -> YamlStrategyExecutionService:
        """Create and return a YamlStrategyExecutionService instance."""
        self.logger.debug("Creating YamlStrategyExecutionService")
        return YamlStrategyExecutionService(
            strategy_orchestrator=strategy_orchestrator,
            logger=self.logger,
        )
    
    def set_executor_function_references(self, mapping_executor, path_execution_manager: PathExecutionManager):
        """Set function references on PathExecutionManager after MappingExecutor is fully initialized.
        
        Args:
            mapping_executor: The fully initialized MappingExecutor instance
            path_execution_manager: The PathExecutionManager instance to configure
        """
        if path_execution_manager:
            # Set function references
            path_execution_manager._load_client = getattr(mapping_executor, '_load_client', None)
            path_execution_manager._execute_mapping_step = getattr(mapping_executor, '_execute_mapping_step', None)
            path_execution_manager._calculate_confidence_score = getattr(
                mapping_executor, '_calculate_confidence_score', path_execution_manager._calculate_confidence_score
            )
            path_execution_manager._create_mapping_path_details = getattr(
                mapping_executor, '_create_mapping_path_details', path_execution_manager._create_mapping_path_details
            )
            path_execution_manager._determine_mapping_source = getattr(
                mapping_executor, '_determine_mapping_source', path_execution_manager._determine_mapping_source
            )
            if mapping_executor.enable_metrics:
                path_execution_manager.track_mapping_metrics = getattr(mapping_executor, 'track_mapping_metrics', None)
"""
MappingExecutorBuilder - Builder pattern implementation for MappingExecutor construction.

This builder is responsible for constructing a fully-configured MappingExecutor instance.
It uses the InitializationService to create low-level components and then instantiates
and wires together the high-level coordinator and manager services.

The builder pattern provides a clean separation between the construction logic and the
operational logic of the MappingExecutor, making the system more maintainable and testable.
"""

import logging
from typing import Dict, Any, Optional

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.initialization_service import InitializationService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_manager import LifecycleManager
from biomapper.core.services.result_aggregation_service import ResultAggregationService
from biomapper.core.services.execution_services import (
    IterativeExecutionService,
    DbStrategyExecutionService,
    YamlStrategyExecutionService,
)


class MappingExecutorBuilder:
    """
    Builder class for constructing MappingExecutor instances.
    
    This builder follows the Builder pattern to separate the complex construction logic
    of MappingExecutor from its operational logic. It handles:
    1. Initialization of low-level components via InitializationService
    2. Creation and wiring of high-level coordinator services
    3. Assembly of the complete MappingExecutor instance
    
    The builder ensures all dependencies are properly resolved and injected,
    creating a fully functional MappingExecutor ready for use.
    """
    
    def __init__(
        self,
        # Configuration parameters
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
        # Pre-initialized components (optional)
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
        Initialize the MappingExecutorBuilder with configuration parameters.
        
        The builder supports both legacy mode (using database URLs) and component mode
        (using pre-initialized components). All parameters are stored for use during
        the build process.
        
        Args:
            metamapper_db_url: URL for the metamapper database (legacy mode)
            mapping_cache_db_url: URL for the mapping cache database (legacy mode)
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
            session_manager: Pre-initialized SessionManager (component mode)
            client_manager: Pre-initialized ClientManager (component mode)
            config_loader: Pre-initialized ConfigLoader (component mode)
            strategy_handler: Pre-initialized StrategyHandler (component mode)
            path_finder: Pre-initialized PathFinder (component mode)
            path_execution_manager: Pre-initialized PathExecutionManager (component mode)
            cache_manager: Pre-initialized CacheManager (component mode)
            identifier_loader: Pre-initialized IdentifierLoader (component mode)
            strategy_orchestrator: Pre-initialized StrategyOrchestrator (component mode)
            checkpoint_manager: Pre-initialized CheckpointManager (component mode)
            progress_reporter: Pre-initialized ProgressReporter (component mode)
            langfuse_tracker: Pre-initialized Langfuse tracker (component mode)
        """
        self.logger = logging.getLogger(__name__)
        
        # Store all configuration parameters
        self.metamapper_db_url = metamapper_db_url
        self.mapping_cache_db_url = mapping_cache_db_url
        self.echo_sql = echo_sql
        self.path_cache_size = path_cache_size
        self.path_cache_expiry_seconds = path_cache_expiry_seconds
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_metrics = enable_metrics
        self.checkpoint_enabled = checkpoint_enabled
        self.checkpoint_dir = checkpoint_dir
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Store pre-initialized components
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
        self.langfuse_tracker = langfuse_tracker
        
        self.logger.debug("MappingExecutorBuilder initialized with configuration")
    
    def build(self) -> MappingExecutor:
        """
        Build a fully configured MappingExecutor instance.
        
        This method orchestrates the entire construction process:
        1. Creates a bare MappingExecutor instance
        2. Uses InitializationService to initialize low-level components
        3. Creates and wires high-level coordinator services
        4. Injects all dependencies into the MappingExecutor
        5. Returns the fully assembled instance
        
        Returns:
            A fully configured and ready-to-use MappingExecutor instance
            
        Raises:
            ConfigurationError: If required dependencies cannot be resolved
            RuntimeError: If construction fails for any reason
        """
        self.logger.info("Building MappingExecutor instance")
        
        try:
            # Step 1: Create a bare MappingExecutor instance
            # We'll need to modify MappingExecutor to support a no-args constructor
            # For now, we'll pass all the parameters to maintain compatibility
            mapping_executor = MappingExecutor(
                metamapper_db_url=self.metamapper_db_url,
                mapping_cache_db_url=self.mapping_cache_db_url,
                echo_sql=self.echo_sql,
                path_cache_size=self.path_cache_size,
                path_cache_expiry_seconds=self.path_cache_expiry_seconds,
                max_concurrent_batches=self.max_concurrent_batches,
                enable_metrics=self.enable_metrics,
                checkpoint_enabled=self.checkpoint_enabled,
                checkpoint_dir=self.checkpoint_dir,
                batch_size=self.batch_size,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                session_manager=self.session_manager,
                client_manager=self.client_manager,
                config_loader=self.config_loader,
                strategy_handler=self.strategy_handler,
                path_finder=self.path_finder,
                path_execution_manager=self.path_execution_manager,
                cache_manager=self.cache_manager,
                identifier_loader=self.identifier_loader,
                strategy_orchestrator=self.strategy_orchestrator,
                checkpoint_manager=self.checkpoint_manager,
                progress_reporter=self.progress_reporter,
                langfuse_tracker=self.langfuse_tracker,
            )
            
            self.logger.info("MappingExecutor instance built successfully")
            return mapping_executor
            
        except Exception as e:
            self.logger.error(f"Failed to build MappingExecutor: {str(e)}")
            raise RuntimeError(f"MappingExecutor construction failed: {str(e)}") from e
    
    def _create_bare_executor(self) -> MappingExecutor:
        """
        Create a bare MappingExecutor instance without initialization.
        
        This is a placeholder for future refactoring where MappingExecutor
        will support a no-args constructor. The actual initialization will
        be handled separately through dependency injection.
        
        Returns:
            A bare, uninitialized MappingExecutor instance
        """
        # This method will be implemented when MappingExecutor is refactored
        # to support construction without initialization
        raise NotImplementedError(
            "Bare executor creation not yet supported. "
            "MappingExecutor refactoring required."
        )
    
    def _initialize_components(self, mapping_executor: MappingExecutor) -> Dict[str, Any]:
        """
        Initialize low-level components using InitializationService.
        
        This method delegates to InitializationService to create all the low-level
        components required by the system (database sessions, clients, caches, etc.).
        
        Args:
            mapping_executor: The MappingExecutor instance being built
            
        Returns:
            Dictionary containing all initialized components
        """
        initialization_service = InitializationService()
        return initialization_service.initialize_components(
            mapping_executor,
            metamapper_db_url=self.metamapper_db_url,
            mapping_cache_db_url=self.mapping_cache_db_url,
            echo_sql=self.echo_sql,
            path_cache_size=self.path_cache_size,
            path_cache_expiry_seconds=self.path_cache_expiry_seconds,
            max_concurrent_batches=self.max_concurrent_batches,
            enable_metrics=self.enable_metrics,
            checkpoint_enabled=self.checkpoint_enabled,
            checkpoint_dir=self.checkpoint_dir,
            batch_size=self.batch_size,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            session_manager=self.session_manager,
            client_manager=self.client_manager,
            config_loader=self.config_loader,
            strategy_handler=self.strategy_handler,
            path_finder=self.path_finder,
            path_execution_manager=self.path_execution_manager,
            cache_manager=self.cache_manager,
            identifier_loader=self.identifier_loader,
            strategy_orchestrator=self.strategy_orchestrator,
            checkpoint_manager=self.checkpoint_manager,
            progress_reporter=self.progress_reporter,
            langfuse_tracker=self.langfuse_tracker,
        )
    
    def _create_coordinators(
        self,
        components: Dict[str, Any],
        mapping_executor: MappingExecutor
    ) -> Dict[str, Any]:
        """
        Create and wire high-level coordinator services.
        
        This method creates the StrategyCoordinatorService, MappingCoordinatorService,
        and LifecycleManager, wiring them with their required dependencies from the
        component dictionary.
        
        Args:
            components: Dictionary of initialized low-level components
            mapping_executor: The MappingExecutor instance being built
            
        Returns:
            Dictionary containing the created coordinator services
        """
        coordinators = {}
        
        # Create execution services that coordinators depend on
        result_aggregation_service = ResultAggregationService(logger=self.logger)
        
        iterative_execution_service = IterativeExecutionService(
            direct_mapping_service=components['direct_mapping_service'],
            iterative_mapping_service=components['iterative_mapping_service'],
            bidirectional_validation_service=components['bidirectional_validation_service'],
            result_aggregation_service=result_aggregation_service,
            path_finder=components['path_finder'],
            composite_handler=mapping_executor,
            async_metamapper_session=components['async_metamapper_session'],
            async_cache_session=components['async_cache_session'],
            metadata_query_service=components['metadata_query_service'],
            session_metrics_service=components['session_metrics_service'],
            logger=self.logger,
        )
        iterative_execution_service.set_executor(mapping_executor)
        
        db_strategy_execution_service = DbStrategyExecutionService(
            strategy_execution_service=components['strategy_execution_service'],
            logger=self.logger,
        )
        
        yaml_strategy_execution_service = YamlStrategyExecutionService(
            strategy_orchestrator=components['strategy_orchestrator'],
            logger=self.logger,
        )
        
        # Create StrategyCoordinatorService
        coordinators['strategy_coordinator'] = StrategyCoordinatorService(
            db_strategy_execution_service=db_strategy_execution_service,
            yaml_strategy_execution_service=yaml_strategy_execution_service,
            robust_execution_coordinator=components['robust_execution_coordinator'],
            logger=self.logger
        )
        
        # Create MappingCoordinatorService
        coordinators['mapping_coordinator'] = MappingCoordinatorService(
            iterative_execution_service=iterative_execution_service,
            path_execution_service=components['path_execution_service'],
            logger=self.logger
        )
        
        # Create LifecycleManager
        coordinators['lifecycle_manager'] = LifecycleManager(
            session_manager=components['session_manager'],
            execution_lifecycle_service=components['lifecycle_service'],
            client_manager=components.get('client_manager'),
        )
        
        # Store execution services for later injection
        coordinators['result_aggregation_service'] = result_aggregation_service
        coordinators['iterative_execution_service'] = iterative_execution_service
        coordinators['db_strategy_execution_service'] = db_strategy_execution_service
        coordinators['yaml_strategy_execution_service'] = yaml_strategy_execution_service
        
        return coordinators
    
    def _wire_dependencies(
        self,
        mapping_executor: MappingExecutor,
        components: Dict[str, Any],
        coordinators: Dict[str, Any]
    ) -> None:
        """
        Wire all dependencies into the MappingExecutor instance.
        
        This method injects all components and coordinators into the MappingExecutor,
        ensuring all dependencies are properly connected.
        
        Args:
            mapping_executor: The MappingExecutor instance to configure
            components: Dictionary of low-level components
            coordinators: Dictionary of high-level coordinator services
        """
        # Inject all components
        for key, value in components.items():
            setattr(mapping_executor, key, value)
        
        # Inject all coordinators
        for key, value in coordinators.items():
            setattr(mapping_executor, key, value)
        
        self.logger.debug("All dependencies wired successfully")
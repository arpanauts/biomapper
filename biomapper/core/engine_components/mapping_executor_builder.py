"""
MappingExecutorBuilder - Responsible for constructing fully-configured MappingExecutor instances.

This builder encapsulates the complex logic of assembling a MappingExecutor with all its
dependencies properly wired together. It uses the InitializationService to create low-level
components and then instantiates and wires together the high-level coordinator and manager services.
"""

import logging
from typing import Optional

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.initialization_service import InitializationService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_manager import LifecycleManager
from biomapper.core.services.database_setup_service import DatabaseSetupService
from biomapper.db.models import Base as MetamapperBase
from biomapper.config import settings


class MappingExecutorBuilder:
    """
    Builder class responsible for constructing fully-configured MappingExecutor instances.
    
    This builder:
    1. Takes configuration parameters in its __init__
    2. Uses InitializationService to get base components
    3. Instantiates high-level coordinators and managers
    4. Returns a fully assembled MappingExecutor instance
    """
    
    def __init__(
        self,
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
    ):
        """
        Initialize the builder with configuration parameters.
        
        Args:
            metamapper_db_url: URL for the metamapper database
            mapping_cache_db_url: URL for the mapping cache database
            echo_sql: Boolean flag to enable SQL echoing
            path_cache_size: Maximum number of paths to cache in memory
            path_cache_expiry_seconds: Cache expiry time in seconds
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        self.logger = logging.getLogger(__name__)
        
        # Store configuration parameters
        self.metamapper_db_url = metamapper_db_url or settings.metamapper_db_url
        self.mapping_cache_db_url = mapping_cache_db_url or settings.cache_db_url
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
        
    def build(self) -> MappingExecutor:
        """
        Build and return a fully configured MappingExecutor instance.
        
        This method:
        1. Creates a temporary MappingExecutor instance (needed for composite handling)
        2. Uses InitializationService to create all base components
        3. Instantiates high-level coordinators and managers
        4. Constructs the final MappingExecutor with all dependencies wired
        
        Returns:
            A fully configured MappingExecutor instance
        """
        self.logger.info("Building MappingExecutor instance")
        
        # Create a temporary MappingExecutor instance for composite handling
        # This is needed because some services require a composite handler reference
        temp_executor = object()  # Placeholder
        
        # Initialize all base components using InitializationService
        initialization_service = InitializationService()
        components = initialization_service.initialize_components(
            mapping_executor=temp_executor,
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
        )
        
        # Extract the execution services that were created by InitializationService
        iterative_execution_service = components['iterative_execution_service']
        db_strategy_execution_service = components['db_strategy_execution_service']
        yaml_strategy_execution_service = components['yaml_strategy_execution_service']
        
        # Create high-level coordinators
        strategy_coordinator = StrategyCoordinatorService(
            db_strategy_execution_service=db_strategy_execution_service,
            yaml_strategy_execution_service=yaml_strategy_execution_service,
            robust_execution_coordinator=components['robust_execution_coordinator'],
            logger=self.logger
        )
        
        mapping_coordinator = MappingCoordinatorService(
            iterative_execution_service=iterative_execution_service,
            path_execution_service=components['path_execution_service'],
            logger=self.logger
        )
        
        lifecycle_manager = LifecycleManager(
            session_manager=components['session_manager'],
            execution_lifecycle_service=components['lifecycle_service'],
            client_manager=components['client_manager'],
            cache_manager=components['cache_manager'],
            path_finder=components['path_finder'],
            path_execution_manager=components['path_execution_manager'],
            composite_handler=temp_executor,  # Will be updated after executor creation
            step_execution_service=components['step_execution_service'],
            logger=self.logger
        )
        
        # Create the final MappingExecutor with high-level components
        executor = MappingExecutor(
            strategy_coordinator=strategy_coordinator,
            mapping_coordinator=mapping_coordinator,
            lifecycle_manager=lifecycle_manager,
            # Pass through other required services/components
            metadata_query_service=components['metadata_query_service'],
            identifier_loader=components['identifier_loader'],
            session_manager=components['session_manager'],
            client_manager=components['client_manager'],
            config_loader=components['config_loader'],
            # Session factories for backward compatibility
            async_metamapper_session=components['async_metamapper_session'],
            async_cache_session=components['async_cache_session'],
            # Configuration parameters
            batch_size=self.batch_size,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            checkpoint_enabled=self.checkpoint_enabled,
            max_concurrent_batches=self.max_concurrent_batches,
            enable_metrics=self.enable_metrics,
        )
        
        # Update composite handler references
        lifecycle_manager._composite_handler = executor
        components['path_execution_service']._composite_handler = executor
        iterative_execution_service._composite_handler = executor
        
        # Set executor references for services that need it
        components['path_execution_service'].set_executor(executor)
        iterative_execution_service.set_executor(executor)
        
        self.logger.info("MappingExecutor built successfully")
        return executor
    
    async def build_async(self) -> MappingExecutor:
        """
        Asynchronously build a MappingExecutor instance.
        
        This method is similar to build() but can be used in async contexts
        and also initializes database tables.
        
        Returns:
            A fully configured MappingExecutor instance with initialized databases
        """
        # Build the executor
        executor = self.build()
        
        # Initialize database tables
        db_setup_service = DatabaseSetupService(logger=self.logger)
        await db_setup_service.initialize_tables(
            executor.session_manager.async_metamapper_engine, 
            MetamapperBase.metadata
        )
        
        return executor
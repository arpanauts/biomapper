# biomapper/core/mapping_executor.py

import logging
from typing import List, Dict, Any, Optional, Union, Callable
from sqlalchemy.ext.asyncio import AsyncSession

# Core components
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService

# Models
from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.db.models import MappingStrategy, MappingPath

class MappingExecutor(CompositeIdentifierMixin):
    """
    High-level facade for BioMapper's service-oriented mapping architecture.

    This class serves as the primary, clean entry point for all mapping operations.
    It follows the Facade design pattern, delegating all complex logic to specialized
    coordinator services. It is constructed by the MappingExecutorBuilder.
    """

    def __init__(
        self,
        lifecycle_coordinator: LifecycleCoordinator,
        mapping_coordinator: MappingCoordinatorService,
        strategy_coordinator: StrategyCoordinatorService,
        session_manager: SessionManager,
        metadata_query_service: MetadataQueryService,
    ):
        self.logger = logging.getLogger(__name__)

        # Use InitializationService to initialize all components
        initialization_service = InitializationService()
        components = initialization_service.initialize_components(
            self,
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
            session_manager=session_manager,
            client_manager=client_manager,
            config_loader=config_loader,
            strategy_handler=strategy_handler,
            path_finder=path_finder,
            path_execution_manager=path_execution_manager,
            cache_manager=cache_manager,
            identifier_loader=identifier_loader,
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            langfuse_tracker=langfuse_tracker,
        )

        # Assign all components from the initialization service to self
        for key, value in components.items():
            setattr(self, key, value)

        # Initialize the execution services first, as coordinators depend on them.
        self.result_aggregation_service = ResultAggregationService(logger=self.logger)
        
        self.iterative_execution_service = IterativeExecutionService(
            direct_mapping_service=self.direct_mapping_service,
            iterative_mapping_service=self.iterative_mapping_service,
            bidirectional_validation_service=self.bidirectional_validation_service,
            result_aggregation_service=self.result_aggregation_service,
            path_finder=self.path_finder,
            composite_handler=self._composite_handler,
            async_metamapper_session=self.async_metamapper_session,
            async_cache_session=self.async_cache_session,
            metadata_query_service=self.metadata_query_service,
            session_metrics_service=self.session_metrics_service,
            logger=self.logger,
        )
        
        self.db_strategy_execution_service = DbStrategyExecutionService(
            strategy_execution_service=self.strategy_execution_service,
            logger=self.logger,
        )
        
        self.yaml_strategy_execution_service = YamlStrategyExecutionService(
            strategy_orchestrator=self.strategy_orchestrator,
            logger=self.logger,
        )

        # Now, initialize Coordinator and Manager services that compose other services
        self.strategy_coordinator = StrategyCoordinatorService(
            db_strategy_execution_service=self.db_strategy_execution_service,
            yaml_strategy_execution_service=self.yaml_strategy_execution_service,
            robust_execution_coordinator=self.robust_execution_coordinator,
            logger=self.logger
        )

        self.mapping_coordinator = MappingCoordinatorService(
            iterative_execution_service=self.iterative_execution_service,
            path_execution_service=self.path_execution_service,
            logger=self.logger
        )

        # Create the specialized lifecycle services
        self.execution_session_service = ExecutionSessionService(
            execution_lifecycle_service=self.lifecycle_service,
            logger=self.logger
        )
        
        self.checkpoint_service = CheckpointService(
            execution_lifecycle_service=self.lifecycle_service,
            checkpoint_dir=checkpoint_dir,
            logger=self.logger
        )
        
        self.resource_disposal_service = ResourceDisposalService(
            session_manager=self.session_manager,
            client_manager=self.client_manager,
            logger=self.logger
        )
        
        # Create the lifecycle coordinator that delegates to these services
        self.lifecycle_manager = LifecycleCoordinator(
            execution_session_service=self.execution_session_service,
            checkpoint_service=self.checkpoint_service,
            resource_disposal_service=self.resource_disposal_service,
            logger=self.logger
        )

        # Set executor reference for services that need it for callbacks/delegation
        self.path_execution_service.set_executor(self)
        self.iterative_execution_service.set_executor(self)

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
        # The initializer now handles both metamapper and cache database table initialization
        executor = await initializer.create_executor()
        
        return executor

    def get_cache_session(self):
        """Get a cache database session."""
        return self.async_cache_session()


        self.lifecycle_coordinator = lifecycle_coordinator
        self.mapping_coordinator = mapping_coordinator
        self.strategy_coordinator = strategy_coordinator
        self.session_manager = session_manager
        self.metadata_query_service = metadata_query_service

    async def execute_mapping(
        self, *args, **kwargs
    ) -> Dict[str, Any]:
        """Delegates mapping execution to the MappingCoordinatorService."""
        return await self.mapping_coordinator.execute_mapping(*args, **kwargs)

    async def _execute_path(
        self, *args, **kwargs
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Delegates path execution to the MappingCoordinatorService."""
        return await self.mapping_coordinator.execute_path(*args, **kwargs)

    async def execute_strategy(
        self, *args, **kwargs
    ) -> MappingResultBundle:
        """Delegates DB strategy execution to the StrategyCoordinatorService."""
        return await self.strategy_coordinator.execute_strategy(*args, **kwargs)

    async def execute_yaml_strategy(
        self, *args, **kwargs
    ) -> MappingResultBundle:
        """Delegates YAML strategy execution to the StrategyCoordinatorService."""
        return await self.strategy_coordinator.execute_yaml_strategy(*args, **kwargs)

    async def execute_robust_yaml_strategy(
        self, *args, **kwargs
    ) -> Dict[str, Any]:
        """Delegates robust YAML strategy execution to the StrategyCoordinatorService."""
        return await self.strategy_coordinator.execute_robust_yaml_strategy(*args, **kwargs)

    async def get_strategy(self, strategy_name: str) -> Optional[MappingStrategy]:
        """Delegates strategy retrieval to the MetadataQueryService."""
        async with self.session_manager.get_async_metamapper_session() as session:
            return await self.metadata_query_service.get_strategy(session, strategy_name)

    def get_cache_session(self) -> AsyncSession:
        """Provides a session to the cache database."""
        return self.session_manager.get_async_cache_session()

    async def async_dispose(self):
        """Delegates resource disposal to the LifecycleCoordinator."""
        await self.lifecycle_coordinator.dispose_resources()

    async def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]):
        """Delegates checkpoint saving to the LifecycleCoordinator."""
        await self.lifecycle_coordinator.save_checkpoint(execution_id, checkpoint_data)

    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Delegates checkpoint loading to the LifecycleCoordinator."""
        return await self.lifecycle_coordinator.load_checkpoint(execution_id)

    async def start_session(self, *args, **kwargs) -> int:
        """Delegates session start to the LifecycleCoordinator."""
        return await self.lifecycle_coordinator.start_session(*args, **kwargs)

    async def end_session(self, *args, **kwargs):
        """Delegates session end to the LifecycleCoordinator."""
        await self.lifecycle_coordinator.end_session(*args, **kwargs)

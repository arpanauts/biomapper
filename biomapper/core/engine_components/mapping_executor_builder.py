# biomapper/core/engine_components/mapping_executor_builder.py

import logging
from typing import Optional, Dict, Any

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.initialization_service import InitializationService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.services.database_setup_service import DatabaseSetupService
from biomapper.db.models import Base as MetamapperBase
from biomapper.db.cache_models import Base as CacheBase

class MappingExecutorBuilder:
    """
    Builder class responsible for constructing fully-configured MappingExecutor instances.

    This builder orchestrates the entire setup process:
    1. Takes a configuration dictionary.
    2. Uses InitializationService to create all low-level components.
    3. Instantiates and wires the high-level coordinators.
    4. Constructs the final MappingExecutor facade.
    5. Resolves any circular dependencies by setting references post-construction.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config if config is not None else {}
        self.initialization_service = InitializationService()

    def build(self) -> MappingExecutor:
        """
        Builds and returns a fully configured MappingExecutor instance.
        """
        self.logger.info("Building MappingExecutor instance.")

        # 1. Create all low-level components
        components = self.initialization_service.create_components(self.config)

        # 2. Create high-level coordinators
        lifecycle_coordinator = self._create_lifecycle_coordinator(components)
        mapping_coordinator = self._create_mapping_coordinator(components)
        strategy_coordinator = self._create_strategy_coordinator(components)

        # 3. Create the lean MappingExecutor facade
        executor = MappingExecutor(
            lifecycle_coordinator=lifecycle_coordinator,
            mapping_coordinator=mapping_coordinator,
            strategy_coordinator=strategy_coordinator,
            session_manager=components['session_manager'],
            metadata_query_service=components['metadata_query_service']
        )

        # 4. Resolve circular dependencies by setting executor reference
        self._set_composite_handler_references(executor, components)

        self.logger.info("MappingExecutor built successfully.")
        return executor

    async def build_async(self) -> MappingExecutor:
        """
        Asynchronously builds a MappingExecutor and initializes database tables.
        """
        executor = self.build()

        # Initialize database tables
        db_setup_service = DatabaseSetupService()
        await db_setup_service.initialize_tables(
            executor.session_manager.async_metamapper_engine,
            MetamapperBase.metadata
        )
        await db_setup_service.initialize_tables(
            executor.session_manager.async_cache_engine,
            CacheBase.metadata
        )
        self.logger.info("Database tables initialized.")

        return executor

    def _create_lifecycle_coordinator(self, components: Dict[str, Any]) -> LifecycleCoordinator:
        return LifecycleCoordinator(
            execution_session_service=components['execution_session_service'],
            checkpoint_service=components['checkpoint_service'],
            resource_disposal_service=components['resource_disposal_service']
        )

    def _create_mapping_coordinator(self, components: Dict[str, Any]) -> MappingCoordinatorService:
        return MappingCoordinatorService(
            iterative_execution_service=components['iterative_execution_service'],
            path_execution_service=components['path_execution_service']
        )

    def _create_strategy_coordinator(self, components: Dict[str, Any]) -> StrategyCoordinatorService:
        return StrategyCoordinatorService(
            db_strategy_execution_service=components['db_strategy_execution_service'],
            yaml_strategy_execution_service=components['yaml_strategy_execution_service'],
            robust_execution_coordinator=components['robust_execution_coordinator']
        )

    def _set_composite_handler_references(self, executor: MappingExecutor, components: Dict[str, Any]):
        """
        Sets the 'composite_handler' or 'executor' reference on services that need it.
        This is done post-construction to break circular dependencies.
        """
        self.logger.debug("Setting composite handler references on dependent services.")
        components['strategy_orchestrator'].set_composite_handler(executor)
        components['iterative_execution_service'].set_composite_handler(executor)
        components['path_execution_service'].set_composite_handler(executor)

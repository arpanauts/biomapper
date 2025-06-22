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

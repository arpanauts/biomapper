"""MappingExecutor - Pure facade for biomapper execution orchestration.

This module provides the main entry point for biomapper operations, delegating
all functionality to specialized coordinator services.
"""

from typing import Any, Dict, List, Optional, Union

from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.mapping_executor_composite import CompositeIdentifierMixin
from biomapper.core.services.metadata_query_service import MetadataQueryService


class MappingExecutor(CompositeIdentifierMixin):
    """Pure facade for biomapper execution operations.
    
    This class serves as the main entry point for biomapper functionality,
    delegating all operations to specialized coordinator services.
    """
    
    def __init__(
        self,
        lifecycle_coordinator: LifecycleCoordinator,
        mapping_coordinator: MappingCoordinatorService,
        strategy_coordinator: StrategyCoordinatorService,
        session_manager: SessionManager,
        metadata_query_service: MetadataQueryService
    ) -> None:
        """Initialize the MappingExecutor with pre-built coordinators.
        
        Args:
            lifecycle_coordinator: Handles resource lifecycle operations
            mapping_coordinator: Handles mapping execution operations
            strategy_coordinator: Handles strategy execution operations
            session_manager: Manages database sessions
            metadata_query_service: Handles metadata queries
        """
        super().__init__()
        self.lifecycle_coordinator = lifecycle_coordinator
        self.mapping_coordinator = mapping_coordinator
        self.strategy_coordinator = strategy_coordinator
        self.session_manager = session_manager
        self.metadata_query_service = metadata_query_service
    
    # Lifecycle Methods
    
    async def async_dispose(self) -> None:
        """Dispose of all resources."""
        await self.lifecycle_coordinator.dispose_resources()
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state_data: Dict[str, Any]
    ) -> None:
        """Save a checkpoint of the current state.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            state_data: State data to save
        """
        await self.lifecycle_coordinator.save_checkpoint(checkpoint_id, state_data)
    
    async def load_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Load a previously saved checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            The loaded state data
        """
        return await self.lifecycle_coordinator.load_checkpoint(checkpoint_id)
    
    async def start_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start a new execution session.
        
        Args:
            session_id: Unique identifier for the session
            metadata: Optional metadata for the session
        """
        await self.lifecycle_coordinator.start_session(session_id, metadata)
    
    async def end_session(self, session_id: str) -> None:
        """End an execution session.
        
        Args:
            session_id: Unique identifier for the session
        """
        await self.lifecycle_coordinator.end_session(session_id)
    
    # Mapping Execution Methods
    
    async def execute_mapping(
        self,
        identifiers: Union[str, List[str]],
        source_ontology: str,
        target_ontology: str,
        mapping_type: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a mapping between ontologies.
        
        Args:
            identifiers: Identifier(s) to map
            source_ontology: Source ontology name
            target_ontology: Target ontology name
            mapping_type: Optional mapping type
            options: Optional execution options
            
        Returns:
            Mapping results
        """
        return await self.mapping_coordinator.execute_mapping(
            identifiers, source_ontology, target_ontology, mapping_type, options
        )
    
    async def _execute_path(
        self,
        identifiers: List[str],
        path: List[str],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a mapping along a specific path.
        
        Args:
            identifiers: Identifiers to map
            path: Sequence of ontologies defining the mapping path
            options: Optional execution options
            
        Returns:
            Path execution results
        """
        return await self.mapping_coordinator.execute_path(identifiers, path, options)
    
    # Strategy Execution Methods
    
    async def execute_strategy(
        self,
        strategy_name: str,
        identifiers: Union[str, List[str]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a named mapping strategy.
        
        Args:
            strategy_name: Name of the strategy to execute
            identifiers: Identifier(s) to process
            parameters: Optional strategy parameters
            
        Returns:
            Strategy execution results
        """
        return await self.strategy_coordinator.execute_strategy(
            strategy_name, identifiers, parameters
        )
    
    async def execute_yaml_strategy(
        self,
        yaml_content: str,
        identifiers: Union[str, List[str]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a strategy defined in YAML format.
        
        Args:
            yaml_content: YAML strategy definition
            identifiers: Identifier(s) to process
            parameters: Optional strategy parameters
            
        Returns:
            Strategy execution results
        """
        return await self.strategy_coordinator.execute_yaml_strategy(
            yaml_content, identifiers, parameters
        )
    
    async def execute_robust_yaml_strategy(
        self,
        yaml_content: str,
        identifiers: Union[str, List[str]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a YAML strategy with robust error handling.
        
        Args:
            yaml_content: YAML strategy definition
            identifiers: Identifier(s) to process
            parameters: Optional strategy parameters
            
        Returns:
            Strategy execution results with error details
        """
        return await self.strategy_coordinator.execute_robust_yaml_strategy(
            yaml_content, identifiers, parameters
        )
    
    # Utility Methods
    
    async def get_strategy(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a strategy definition by name.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Strategy definition or None if not found
        """
        return await self.metadata_query_service.get_strategy(strategy_name)
    
    def get_cache_session(self):
        """Get an async cache session.
        
        Returns:
            Async cache session instance
        """
        return self.session_manager.get_async_cache_session()
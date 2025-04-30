"""
Base mapper module providing the foundation for all entity mappers in Biomapper.

This module defines the AbstractEntityMapper base class which provides common
functionality for resource management, mapping operations, and performance tracking.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

from biomapper.mapping.metadata.manager import ResourceMetadataManager
from biomapper.mapping.adapters.cache_adapter import CacheResourceAdapter


class AbstractEntityMapper(ABC):
    """
    Abstract base class for all entity mappers.
    
    This class provides common functionality for resource management,
    mapping operations, and performance tracking.
    """
    
    def __init__(
        self, 
        entity_type: str, 
        db_path: Optional[str] = None, 
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the entity mapper.
        
        Args:
            entity_type: Type of entity this mapper handles (e.g., "metabolite", "protein")
            db_path: Path to metadata database (optional)
            config: Configuration options for resources (optional)
        """
        self.entity_type = entity_type
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize resource metadata components
        self.metadata_manager = ResourceMetadataManager(db_path)
        self._resources_initialized = False
    
    async def initialize_resources(self):
        """Initialize all resources needed by this mapper."""
        if self._resources_initialized:
            return
            
        # Setup common resources
        await self._setup_common_resources()
        
        # Setup entity-specific resources
        await self._setup_entity_resources()
        
        self._resources_initialized = True
        
    async def _setup_common_resources(self):
        """Setup resources common to all entity types."""
        # Setup SQLite cache adapter
        cache_config = self.config.get("sqlite_cache", {"db_path": self._get_default_cache_path()})
        cache_adapter = CacheResourceAdapter(cache_config, "sqlite_cache")
        
        # Setup SPOKE adapter if configuration is available
        spoke_config = self.config.get("spoke_graph")
        if spoke_config:
            from biomapper.mapping.adapters.spoke_adapter import SpokeResourceAdapter
            spoke_adapter = SpokeResourceAdapter(spoke_config, "spoke_graph")
            try:
                pass
            except Exception as e:
                self.logger.warning(f"Failed to initialize SPOKE adapter: {e}")
    
    @abstractmethod
    async def _setup_entity_resources(self):
        """
        Setup resources specific to this entity type.
        
        This method must be implemented by subclasses to initialize
        the resources needed for their specific entity type.
        """
        pass
    
    def _get_default_cache_path(self) -> str:
        """Get the default path to the mapping cache."""
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".biomapper", "mappings.db")
    
    async def map_entity(
        self, 
        source_id: str, 
        source_type: str, 
        target_type: str,
        confidence_threshold: float = 0.0,
        preferred_resource: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Map an entity from one identifier system to another.
        
        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            confidence_threshold: Minimum confidence for results
            preferred_resource: Name of preferred resource (optional)
            **kwargs: Additional parameters for the mapping operation
            
        Returns:
            List of mappings with target_id and confidence
        """
        # Ensure resources are initialized
        await self.initialize_resources()
        
        # Perform the mapping operation
        # results = await self.dispatcher.map_entity(
        #     source_id=source_id,
        #     source_type=source_type,
        #     target_type=target_type,
        #     preferred_resource=preferred_resource,
        #     **kwargs
        # )
        
        # Filter by confidence threshold
        # if confidence_threshold > 0:
        #     results = [r for r in results if r.get("confidence", 0) >= confidence_threshold]
            
        # return results
    
    async def batch_map_entities(
        self,
        source_ids: List[str],
        source_type: str,
        target_type: str,
        confidence_threshold: float = 0.0,
        **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map multiple entities in batch.
        
        Args:
            source_ids: List of source identifiers
            source_type: Source ontology type
            target_type: Target ontology type
            confidence_threshold: Minimum confidence for results
            **kwargs: Additional parameters for the mapping operation
            
        Returns:
            Dictionary mapping source IDs to lists of mapping results
        """
        # Ensure resources are initialized
        await self.initialize_resources()
        
        # Perform the batch mapping operation
        # results = await self.dispatcher.batch_map_entities(
        #     source_ids=source_ids,
        #     source_type=source_type,
        #     target_type=target_type,
        #     **kwargs
        # )
        
        # Filter by confidence threshold
        # if confidence_threshold > 0:
        #     filtered_results = {}
        #     for source_id, mappings in results.items():
        #         filtered_results[source_id] = [
        #             m for m in mappings if m.get("confidence", 0) >= confidence_threshold
        #         ]
        #     return filtered_results
            
        # return results
    
    async def get_resource_performance(
        self, 
        source_type: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics for resources used by this mapper.
        
        Args:
            source_type: Filter by source ontology type (optional)
            target_type: Filter by target ontology type (optional)
            
        Returns:
            List of performance metrics for matching resources
        """
        with self.metadata_manager:
            return self.metadata_manager.get_performance_summary(
                source_type=source_type,
                target_type=target_type
            )
    
    def run_sync(self, async_func, *args, **kwargs):
        """
        Run an async method synchronously.
        
        This method provides backward compatibility with synchronous code.
        
        Args:
            async_func: Async method to run
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Result of the async method
        """
        return asyncio.run(async_func(*args, **kwargs))

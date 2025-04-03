"""
Mapping Dispatcher for Biomapper Resource Metadata System.

This module provides the MappingDispatcher class, which orchestrates
mapping operations across multiple resources based on capabilities
and performance metrics.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, TypeVar, Type

from biomapper.mapping.metadata.manager import ResourceMetadataManager
from biomapper.mapping.metadata.interfaces import ResourceAdapter
from biomapper.mapping.metadata.metamapping import MetamappingEngine

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ResourceAdapter)


class MappingDispatcher:
    """
    Orchestrates mapping operations across resources.
    
    This class uses the resource metadata to intelligently route
    mapping operations to the most appropriate resources, based on
    capabilities, performance, and availability.
    """
    
    def __init__(self, metadata_manager: ResourceMetadataManager):
        """
        Initialize the mapping dispatcher.
        
        The MappingDispatcher orchestrates mapping operations across resources,
        including direct mappings and multi-step metamappings when no direct path
        is available.
        
        Args:
            metadata_manager: The resource metadata manager
        """
        self.metadata_manager = metadata_manager
        self.resource_adapters: Dict[str, ResourceAdapter] = {}
        self.metamapping_engine = MetamappingEngine(self)
        self.enable_metamapping = True  # Can be disabled for testing or performance
        
    async def add_resource_adapter(self, name: str, adapter: ResourceAdapter) -> bool:
        """
        Add a resource adapter to the dispatcher.
        
        Args:
            name: Name of the resource
            adapter: Resource adapter instance
            
        Returns:
            bool: True if adapter was successfully added, False otherwise
        """
        try:
            # Ensure the adapter implements the ResourceAdapter protocol
            if not hasattr(adapter, 'connect') or not hasattr(adapter, 'map_entity'):
                logger.error(f"Adapter for {name} does not implement the ResourceAdapter protocol")
                return False
                
            # Try to connect to the resource
            if not await adapter.connect():
                logger.error(f"Could not connect to resource {name}")
                return False
                
            self.resource_adapters[name] = adapter
            logger.info(f"Added resource adapter for {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding resource adapter for {name}: {e}")
            return False
            
    async def map_entity(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        preferred_resource: Optional[str] = None,
        timeout_ms: int = 10000,
        update_cache: bool = True,
        allow_metamapping: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Map an entity using the most appropriate resource.
        
        This method attempts to map an entity using available resources. If no direct
        mapping is available and metamapping is enabled, it will attempt to find and
        execute a multi-step mapping path.
        
        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            preferred_resource: Name of preferred resource, if any
            timeout_ms: Maximum time to wait for a response (milliseconds)
            update_cache: Whether to update the cache with results
            allow_metamapping: Override global metamapping setting (optional)
            
        Returns:
            List of mappings, each containing at least 'target_id' and 'confidence'
        """
        # If preferred resource is specified and available, use it
        if preferred_resource and preferred_resource in self.resource_adapters:
            start_time = time.time()
            try:
                results = await asyncio.wait_for(
                    self.resource_adapters[preferred_resource].map_entity(
                        source_id, source_type, target_type
                    ),
                    timeout=timeout_ms / 1000
                )
                
                # Log performance metrics
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.metadata_manager.update_performance_metrics(
                    preferred_resource, "map", source_type, target_type, 
                    elapsed_ms, bool(results)
                )
                
                # Update cache if necessary
                if update_cache and results and preferred_resource != "sqlite_cache":
                    await self._update_cache(source_id, source_type, target_type, results)
                    
                return results
                
            except asyncio.TimeoutError:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"Operation timed out for {preferred_resource} after {elapsed_ms}ms")
                self.metadata_manager.update_performance_metrics(
                    preferred_resource, "map", source_type, target_type, 
                    elapsed_ms, False
                )
                
                # If preferred resource timed out, fall back to other resources
                if not preferred_resource.startswith("fallback_"):
                    return await self.map_entity(
                        source_id, source_type, target_type, 
                        preferred_resource=f"fallback_{preferred_resource}",
                        timeout_ms=timeout_ms
                    )
                return []
                
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Error mapping with {preferred_resource}: {e}")
                self.metadata_manager.update_performance_metrics(
                    preferred_resource, "map", source_type, target_type, 
                    elapsed_ms, False
                )
                return []
        
        # Get resources ordered by priority for this operation
        resources = self.metadata_manager.get_resources_by_priority(
            source_type, target_type, "map"
        )
        
        # Try resources in order
        for resource in resources:
            resource_name = resource['name']
            
            # Skip resources without adapters
            if resource_name not in self.resource_adapters:
                continue
                
            # For low success rate resources, reduce timeout
            success_rate = resource.get('success_rate', 1.0)
            resource_timeout = max(1000, int(timeout_ms * success_rate))
            
            start_time = time.time()
            try:
                results = await asyncio.wait_for(
                    self.resource_adapters[resource_name].map_entity(
                        source_id, source_type, target_type
                    ),
                    timeout=resource_timeout / 1000
                )
                
                # Log performance metrics
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.metadata_manager.update_performance_metrics(
                    resource_name, "map", source_type, target_type, 
                    elapsed_ms, bool(results)
                )
                
                if results:
                    # Update cache if necessary
                    if update_cache and resource_name != "sqlite_cache":
                        await self._update_cache(source_id, source_type, target_type, results)
                    return results
                    
            except asyncio.TimeoutError:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"Operation timed out for {resource_name} after {elapsed_ms}ms")
                self.metadata_manager.update_performance_metrics(
                    resource_name, "map", source_type, target_type, 
                    elapsed_ms, False
                )
                
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Error mapping with {resource_name}: {e}")
                self.metadata_manager.update_performance_metrics(
                    resource_name, "map", source_type, target_type, 
                    elapsed_ms, False
                )
        
        # No successful results from direct mapping
        # Try metamapping if enabled
        should_try_metamapping = allow_metamapping if allow_metamapping is not None else self.enable_metamapping
        if should_try_metamapping:
            logger.info(f"No direct mapping found for {source_type} to {target_type}, trying metamapping")
            try:
                # Find a mapping path
                mapping_path = await self.metamapping_engine.find_mapping_path(source_type, target_type)
                
                if mapping_path:
                    logger.info(f"Found mapping path with {len(mapping_path)} steps")
                    metamapping_results = await self.metamapping_engine.execute_mapping_path(
                        source_id=source_id,
                        mapping_path=mapping_path,
                        **kwargs if 'kwargs' in locals() else {}
                    )
                    
                    # Cache the results of the complete mapping for future use
                    if metamapping_results and update_cache:
                        await self._update_cache(
                            source_id=source_id,
                            source_type=source_type,
                            target_type=target_type,
                            results=metamapping_results
                        )
                    
                    return metamapping_results
                else:
                    logger.info(f"No metamapping path found for {source_type} to {target_type}")
            except Exception as e:
                logger.error(f"Error during metamapping: {e}")
        
        # No results from direct mapping or metamapping
        return []
    
    async def batch_map_entities(
        self,
        source_ids: List[str],
        source_type: str,
        target_type: str,
        preferred_resource: Optional[str] = None,
        timeout_ms: int = 30000,
        update_cache: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map multiple entities in batch.
        
        Args:
            source_ids: List of source identifiers
            source_type: Source ontology type
            target_type: Target ontology type
            preferred_resource: Name of preferred resource, if any
            timeout_ms: Maximum time to wait for all responses (milliseconds)
            update_cache: Whether to update the cache with results
            
        Returns:
            Dictionary mapping source IDs to lists of mappings
        """
        # Check if we have any batch-capable resources
        batch_resources = []
        for name, adapter in self.resource_adapters.items():
            capabilities = adapter.get_capabilities()
            if capabilities.get("supports_batch", False):
                batch_resources.append((name, adapter, capabilities.get("max_batch_size", 100)))
                
        # If no batch resources or preferred resource is specified, map individually
        if not batch_resources or preferred_resource:
            results = {}
            # Use asyncio.gather to parallelize individual mapping operations
            tasks = [
                self.map_entity(
                    source_id, source_type, target_type, 
                    preferred_resource, timeout_ms // len(source_ids), update_cache
                )
                for source_id in source_ids
            ]
            
            # Process in batches to avoid overwhelming the system
            batch_size = 10
            for i in range(0, len(tasks), batch_size):
                batch_results = await asyncio.gather(*tasks[i:i+batch_size])
                for j, source_id in enumerate(source_ids[i:i+batch_size]):
                    results[source_id] = batch_results[j]
                    
            return results
            
        # Use batch-capable resources
        # Sort by priority
        resources = self.metadata_manager.get_resources_by_priority(
            source_type, target_type, "batch_map"
        )
        
        # Prioritize batch-capable resources that match our filter
        batch_resources = [
            (name, adapter, max_batch)
            for name, adapter, max_batch in batch_resources
            if any(r['name'] == name for r in resources)
        ]
        
        if not batch_resources:
            # Fall back to individual mapping
            return await self.batch_map_entities(
                source_ids, source_type, target_type, 
                preferred_resource, timeout_ms, update_cache
            )
            
        # Use the first batch-capable resource
        name, adapter, max_batch = batch_resources[0]
        
        # Split into batches according to max_batch_size
        results = {}
        for i in range(0, len(source_ids), max_batch):
            batch = source_ids[i:i+max_batch]
            
            # This is a simplified implementation that assumes the adapter
            # has a batch_map_entities method - in a real implementation,
            # you would check if the method exists and fall back if not
            start_time = time.time()
            try:
                batch_results = await asyncio.wait_for(
                    adapter.batch_map_entities(batch, source_type, target_type),
                    timeout=timeout_ms / 1000
                )
                
                # Log performance metrics
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.metadata_manager.update_performance_metrics(
                    name, "batch_map", source_type, target_type, 
                    elapsed_ms, bool(batch_results)
                )
                
                # Update cache if necessary
                if update_cache and name != "sqlite_cache":
                    for source_id, mappings in batch_results.items():
                        if mappings:
                            await self._update_cache(source_id, source_type, target_type, mappings)
                            
                results.update(batch_results)
                
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Error batch mapping with {name}: {e}")
                self.metadata_manager.update_performance_metrics(
                    name, "batch_map", source_type, target_type, 
                    elapsed_ms, False
                )
                
                # Fall back to individual mapping for this batch
                for source_id in batch:
                    results[source_id] = await self.map_entity(
                        source_id, source_type, target_type,
                        None, timeout_ms // len(batch), update_cache
                    )
                    
        return results
    
    def get_adapter_by_type(self, adapter_type: Union[str, Type[T]]) -> List[Tuple[str, T]]:
        """
        Get all adapters of a specific type.
        
        Args:
            adapter_type: Type of adapter or type name
            
        Returns:
            List of (name, adapter) tuples for adapters of the specified type
        """
        if isinstance(adapter_type, str):
            return [
                (name, adapter) 
                for name, adapter in self.resource_adapters.items()
                if adapter.get_capabilities().get("type") == adapter_type
            ]
        else:
            return [
                (name, adapter) 
                for name, adapter in self.resource_adapters.items()
                if isinstance(adapter, adapter_type)
            ]
    
    async def _update_cache(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """
        Update the SQLite cache with results from other resources.
        
        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            results: Mapping results to cache
            
        Returns:
            bool: True if cache was updated successfully, False otherwise
        """
        if "sqlite_cache" not in self.resource_adapters:
            return False
            
        cache_adapter = self.resource_adapters["sqlite_cache"]
        
        # The cache adapter should have an update_mappings method
        if not hasattr(cache_adapter, 'update_mappings'):
            logger.warning("Cache adapter does not have update_mappings method")
            return False
            
        try:
            # Call the update_mappings method if it exists
            return await cache_adapter.update_mappings(
                source_id, source_type, target_type, results
            )
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            return False

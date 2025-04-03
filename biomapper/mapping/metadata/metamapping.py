"""
Metamapping module for the Biomapper Resource Metadata System.

This module provides functionality for multi-step (metamapping) operations
when direct mapping between two ontologies is not available.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from collections import deque

logger = logging.getLogger(__name__)

class MetamappingEngine:
    """
    Manages multi-step mappings across ontologies.
    
    The MetamappingEngine enables mapping between ontologies that have no
    direct connection by finding and executing paths through intermediate
    ontologies.
    """
    
    def __init__(self, dispatcher, max_path_length=3):
        """
        Initialize the metamapping engine.
        
        Args:
            dispatcher: The MappingDispatcher instance
            max_path_length: Maximum number of steps in a mapping path
        """
        self.dispatcher = dispatcher
        self.metadata_manager = dispatcher.metadata_manager
        self.max_path_length = max_path_length
        
    async def find_mapping_path(self, source_type: str, target_type: str) -> Optional[List[Dict[str, Any]]]:
        """
        Find a path to map from source_type to target_type.
        
        Uses breadth-first search to find the shortest path from source_type
        to target_type using available resources.
        
        Args:
            source_type: Source identifier type
            target_type: Target identifier type
            
        Returns:
            List of mapping steps, each containing source_type, target_type, and resources,
            or None if no path is found
        """
        # Get all possible ontology types
        possible_intermediates = self.metadata_manager.get_all_ontology_types()
        
        # Queue for BFS, each entry contains (current_type, path_so_far)
        queue = deque([(source_type, [])])
        visited = {source_type}  # Track visited types to avoid cycles
        
        while queue:
            current_type, path = queue.popleft()
            
            # Check if we've reached the target
            if current_type == target_type and path:  # Ensure path is not empty
                return path
            
            # If path is already at max length, don't extend further
            if len(path) >= self.max_path_length:
                continue
            
            # Find all possible next steps
            for next_type in possible_intermediates:
                if next_type in visited:
                    continue
                    
                resources = self.metadata_manager.find_resources_by_capability(
                    source_type=current_type,
                    target_type=next_type
                )
                
                if resources:
                    # Add this step to the path
                    new_path = path + [{
                        "source_type": current_type,
                        "target_type": next_type,
                        "resources": resources
                    }]
                    
                    # If we've reached the target, return the path
                    if next_type == target_type:
                        return new_path
                    
                    # Otherwise, add to queue for further exploration
                    queue.append((next_type, new_path))
                    visited.add(next_type)
        
        # If we get here, no path was found
        return None
    
    async def execute_mapping_path(
        self,
        source_id: str,
        mapping_path: List[Dict[str, Any]],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute a multi-step mapping path.
        
        Args:
            source_id: Source entity identifier
            mapping_path: List of mapping steps from find_mapping_path
            **kwargs: Additional parameters for mapping
            
        Returns:
            List of final mapping results
        """
        current_ids = [{"id": source_id, "confidence": 1.0}]
        results = []
        
        # For each step in the path
        for step in mapping_path:
            source_type = step["source_type"]
            target_type = step["target_type"]
            resources = step["resources"]
            
            # Map all current IDs to the next step
            next_ids = []
            for id_info in current_ids:
                current_id = id_info["id"]
                base_confidence = id_info["confidence"]
                
                # Try each resource until one succeeds
                step_results = []
                for resource_info in resources:
                    resource_name = resource_info["name"]
                    
                    # Skip if dispatcher doesn't have this resource
                    if resource_name not in self.dispatcher.resource_adapters:
                        continue
                        
                    adapter = self.dispatcher.resource_adapters[resource_name]
                    
                    try:
                        start_time = time.time()
                        resource_results = await adapter.map_entity(
                            current_id, source_type, target_type, **kwargs
                        )
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        
                        # Record performance metrics
                        success = bool(resource_results)
                        self.metadata_manager.update_performance_metrics(
                            resource_name, "map", source_type, target_type,
                            elapsed_ms, success
                        )
                        
                        if resource_results:
                            step_results = resource_results
                            
                            # Cache intermediate mapping results
                            await self._cache_intermediate_results(
                                current_id, source_type,
                                target_type, resource_results
                            )
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error in metamapping step with {resource_name}: {e}")
                
                # Accumulate results with compounded confidence
                for result in step_results:
                    # Determine path information for tracking
                    path_entry = {
                        "source_id": current_id,
                        "source_type": source_type,
                        "target_id": result["target_id"],
                        "target_type": target_type,
                        "resource": result["source"],
                        "confidence": result["confidence"]
                    }
                    
                    # Get existing path or initialize new one
                    path = id_info.get("path", [])
                    
                    next_ids.append({
                        "id": result["target_id"],
                        # Multiply confidences to reflect compounded uncertainty
                        "confidence": base_confidence * result["confidence"],
                        # Track the path for debugging and confidence calculation
                        "path": path + [path_entry],
                        "metadata": result.get("metadata", {})
                    })
            
            # If we couldn't map anything at this step, the path failed
            if not next_ids:
                logger.warning(f"Mapping path failed at step {source_type} to {target_type}")
                return []
                
            # Update current IDs for the next step
            current_ids = next_ids
        
        # Format final results
        for id_info in current_ids:
            results.append({
                "target_id": id_info["id"],
                "confidence": id_info["confidence"],
                "source": "metamapping",
                "metadata": {
                    "mapping_path": id_info.get("path", []),
                    **id_info.get("metadata", {})
                }
            })
            
        return results
    
    async def _cache_intermediate_results(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """
        Cache intermediate mapping results.
        
        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            results: Mapping results
            
        Returns:
            True if cached successfully, False otherwise
        """
        # Find the cache adapter
        cache_adapters = [
            adapter for name, adapter in self.dispatcher.resource_adapters.items()
            if name == "sqlite_cache" or getattr(adapter, "is_cache", False)
        ]
        
        if not cache_adapters:
            return False
            
        # Use the first cache adapter
        cache_adapter = cache_adapters[0]
        
        try:
            for result in results:
                if hasattr(cache_adapter, "store_mapping"):
                    await cache_adapter.store_mapping(
                        source_id=source_id,
                        source_type=source_type,
                        target_id=result["target_id"],
                        target_type=target_type,
                        confidence=result["confidence"],
                        metadata=result.get("metadata", {})
                    )
            return True
        except Exception as e:
            logger.warning(f"Error caching intermediate results: {e}")
            return False

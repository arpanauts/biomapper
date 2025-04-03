# Enhanced MetaboliteNameMapper Implementation

## Overview

The `MetaboliteNameMapper` is one of Biomapper's core components that maps metabolite names to standard identifiers. This document outlines how to enhance it with the Resource Metadata System to make it more powerful, resilient, and extensible.

## Current Limitations

The current `MetaboliteNameMapper` has several limitations:

1. **Fixed Resources**: Hard-coded dependencies on specific resources
2. **Limited Fallbacks**: Minimal handling of resource unavailability
3. **No Performance Tracking**: No data on which resources perform best
4. **Synchronous Only**: Lacks async support for concurrent operations
5. **Limited Batch Processing**: Inefficient for mapping multiple entities

## Enhanced Implementation

The enhanced `MetaboliteNameMapper` will leverage the Resource Metadata System to address these limitations:

```python
from typing import List, Dict, Any, Optional
import asyncio

from biomapper.mapping.metadata.manager import ResourceMetadataManager
from biomapper.mapping.metadata.dispatcher import MappingDispatcher
from biomapper.mapping.adapters.cache_adapter import CacheResourceAdapter
from biomapper.mapping.adapters.spoke_adapter import SpokeResourceAdapter
from biomapper.core.base_mapper import BaseMapper
from biomapper.mapping.clients.chebi_client import ChEBIClient
from biomapper.mapping.clients.refmet_client import RefMetClient
from biomapper.mapping.clients.unichem_client import UniChemClient

class EnhancedMetaboliteNameMapper:
    """Enhanced mapper for metabolite names using the Resource Metadata System."""
    
    def __init__(self, db_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the metabolite name mapper.
        
        Args:
            db_path: Path to the metadata database. If None, uses the default path.
            config: Additional configuration options for resources
        """
        self.config = config or {}
        
        # Initialize resource metadata components
        self.metadata_manager = ResourceMetadataManager(db_path)
        self.dispatcher = MappingDispatcher(self.metadata_manager)
        self._resources_initialized = False
    
    async def initialize_resources(self) -> None:
        """Initialize and register all available resources."""
        if self._resources_initialized:
            return
            
        # Setup SQLite cache adapter
        cache_config = self.config.get("sqlite_cache", {"db_path": self._get_default_cache_path()})
        cache_adapter = CacheResourceAdapter(cache_config, "sqlite_cache")
        await self.dispatcher.add_resource_adapter("sqlite_cache", cache_adapter)
        
        # Setup SPOKE adapter if configuration is available
        spoke_config = self.config.get("spoke_graph")
        if spoke_config:
            spoke_adapter = SpokeResourceAdapter(spoke_config, "spoke_graph")
            try:
                await self.dispatcher.add_resource_adapter("spoke_graph", spoke_adapter)
            except Exception as e:
                self.logger.warning(f"Failed to initialize SPOKE adapter: {e}")
        
        # Setup ChEBI API adapter
        try:
            chebi_config = self.config.get("chebi_api", {})
            chebi_client = ChEBIClient(**chebi_config)
            chebi_adapter = self._create_api_adapter(chebi_client, "chebi_api")
            await self.dispatcher.add_resource_adapter("chebi_api", chebi_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize ChEBI adapter: {e}")
            
        # Setup RefMet API adapter
        try:
            refmet_config = self.config.get("refmet_api", {})
            refmet_client = RefMetClient(**refmet_config)
            refmet_adapter = self._create_api_adapter(refmet_client, "refmet_api")
            await self.dispatcher.add_resource_adapter("refmet_api", refmet_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize RefMet adapter: {e}")
            
        # Setup UniChem API adapter
        try:
            unichem_config = self.config.get("unichem_api", {})
            unichem_client = UniChemClient(**unichem_config)
            unichem_adapter = self._create_api_adapter(unichem_client, "unichem_api")
            await self.dispatcher.add_resource_adapter("unichem_api", unichem_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize UniChem adapter: {e}")
            
        self._resources_initialized = True
    
    def _create_api_adapter(self, client: Any, name: str) -> "APIResourceAdapter":
        """Create an API resource adapter for a client."""
        # In a real implementation, you would have an APIResourceAdapter class
        from biomapper.mapping.adapters.api_adapter import APIResourceAdapter
        return APIResourceAdapter(client, name)
    
    def _get_default_cache_path(self) -> str:
        """Get the default path to the mapping cache."""
        import os
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".biomapper", "mappings.db")
    
    async def map_name_to_chebi(self, name: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Map a metabolite name to ChEBI identifiers.
        
        Args:
            name: Metabolite name to map
            confidence_threshold: Minimum confidence score (0-1) for results
            
        Returns:
            List of mappings with target_id and confidence
        """
        await self.initialize_resources()
        
        results = await self.dispatcher.map_entity(
            source_id=name,
            source_type="compound_name",
            target_type="chebi"
        )
        
        # Filter by confidence threshold
        return [r for r in results if r.get("confidence", 0) >= confidence_threshold]
    
    async def map_name_to_hmdb(self, name: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Map a metabolite name to HMDB identifiers."""
        await self.initialize_resources()
        
        results = await self.dispatcher.map_entity(
            source_id=name,
            source_type="compound_name",
            target_type="hmdb"
        )
        
        return [r for r in results if r.get("confidence", 0) >= confidence_threshold]
    
    async def map_name_to_pubchem(self, name: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Map a metabolite name to PubChem identifiers."""
        await self.initialize_resources()
        
        results = await self.dispatcher.map_entity(
            source_id=name,
            source_type="compound_name",
            target_type="pubchem"
        )
        
        return [r for r in results if r.get("confidence", 0) >= confidence_threshold]
    
    async def map_name_to_multiple(
        self, 
        name: str, 
        target_types: List[str] = ["chebi", "hmdb", "pubchem"],
        confidence_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map a metabolite name to multiple target identifier types.
        
        Args:
            name: Metabolite name to map
            target_types: List of target ontology types
            confidence_threshold: Minimum confidence score (0-1) for results
            
        Returns:
            Dictionary mapping target types to lists of mapping results
        """
        await self.initialize_resources()
        
        results = {}
        tasks = [
            self.dispatcher.map_entity(
                source_id=name,
                source_type="compound_name",
                target_type=target_type
            )
            for target_type in target_types
        ]
        
        all_results = await asyncio.gather(*tasks)
        
        for i, target_type in enumerate(target_types):
            target_results = all_results[i]
            results[target_type] = [
                r for r in target_results 
                if r.get("confidence", 0) >= confidence_threshold
            ]
            
        return results
    
    async def map_batch_names(
        self, 
        names: List[str],
        target_type: str = "chebi", 
        confidence_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map multiple metabolite names in batch.
        
        Args:
            names: List of metabolite names to map
            target_type: Target ontology type
            confidence_threshold: Minimum confidence score (0-1) for results
            
        Returns:
            Dictionary mapping input names to lists of mapping results
        """
        await self.initialize_resources()
        
        results = await self.dispatcher.batch_map_entities(
            source_ids=names,
            source_type="compound_name",
            target_type=target_type
        )
        
        # Filter by confidence threshold
        return {
            name: [r for r in mappings if r.get("confidence", 0) >= confidence_threshold]
            for name, mappings in results.items()
        }
    
    def map_single_name(self, name: str, target_type: str = "chebi") -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for mapping a single name.
        
        This method provides backward compatibility with code expecting
        synchronous behavior.
        
        Args:
            name: Metabolite name to map
            target_type: Target ontology type
            
        Returns:
            List of mappings with target_id and confidence
        """
        return asyncio.run(self.dispatcher.map_entity(
            source_id=name,
            source_type="compound_name",
            target_type=target_type
        ))
```

## Implementation Notes

### 1. Resource Initialization

Resources are initialized on-demand and asynchronously with the `initialize_resources()` method. This:

- Avoids unnecessary initialization for unused resources
- Handles resource failures gracefully
- Allows for resource customization via configuration

### 2. Mapping Methods

Each mapping method follows a consistent pattern:

1. Ensure resources are initialized
2. Delegate mapping to the dispatcher
3. Filter and format results as needed

### 3. Batch Operations

The enhanced mapper provides efficient batch operations, allowing multiple metabolite names to be mapped in a single operation with `map_batch_names()`. This:

- Reduces overhead for large datasets
- Enables parallel processing where supported
- Maintains consistent result format

### 4. Backward Compatibility

To maintain compatibility with existing code, a synchronous `map_single_name()` method is provided that matches the original API.

## Adapter Implementation

To connect existing API clients to the Resource Metadata System, we need API adapters like:

```python
class APIResourceAdapter(BaseResourceAdapter):
    """Adapter for API-based clients."""
    
    def __init__(self, client, name):
        """Initialize with an API client."""
        super().__init__({}, name)
        self.client = client
        
    async def connect(self):
        """Connect to the API (if applicable)."""
        # Some clients may have connect methods
        if hasattr(self.client, 'connect'):
            return await self.client.connect()
        return True
        
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """Map entity using the API client."""
        # Determine which client method to call based on the mapping type
        if hasattr(self.client, f'map_{source_type}_to_{target_type}'):
            method = getattr(self.client, f'map_{source_type}_to_{target_type}')
            raw_results = await method(source_id, **kwargs)
        elif hasattr(self.client, 'search'):
            raw_results = await self.client.search(source_id, target_type)
        else:
            return []
            
        # Transform results to standard format
        return self._normalize_results(raw_results, target_type)
        
    def _normalize_results(self, raw_results, target_type):
        """Convert client-specific results to standard format."""
        # Implementation depends on the client's result format
        # This is a placeholder
        return [
            {
                "target_id": r.get("id"),
                "confidence": r.get("score", 0.9),
                "source": self.name
            }
            for r in raw_results if r.get("id")
        ]
```

## Integration Steps

To integrate this enhanced `MetaboliteNameMapper` with Biomapper:

1. **Implement the `APIResourceAdapter`** to connect API clients to the Resource Metadata System
2. **Create adapter implementations** for each resource type (ChEBI, RefMet, UniChem)
3. **Update imports** in existing code to use the enhanced mapper
4. **Add configuration options** for controlling resource usage
5. **Update tests** to cover the enhanced functionality

## Migration Strategy

To minimize disruption to existing code, follow these steps:

1. Implement the enhanced mapper as a new class (`EnhancedMetaboliteNameMapper`)
2. Maintain the original `MetaboliteNameMapper` temporarily
3. Update the original `MetaboliteNameMapper` to inherit from the enhanced version
4. Gradually migrate code to use async methods for better performance

## Performance Considerations

The enhanced mapper introduces several performance benefits:

1. **Resource Selection**: Automatically selects the fastest/most reliable resources
2. **Parallel Operations**: Performs concurrent mapping when appropriate
3. **Caching**: Automatically caches results from slower resources
4. **Adaptive Timeouts**: Sets timeouts based on historical performance
5. **Resource Reuse**: Avoids redundant resource initializations

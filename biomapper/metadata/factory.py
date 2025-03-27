"""Factory for creating and configuring the resource metadata system."""

import logging
from typing import Dict, List, Optional, Type, Union, Any

from biomapper.cache.manager import CacheManager
from biomapper.db.models_metadata import ResourceType
from biomapper.metadata.adapters import CacheResourceAdapter, SpokeResourceAdapter
from biomapper.metadata.dispatcher import MappingDispatcher
from biomapper.metadata.init import initialize_metadata_system
from biomapper.metadata.manager import ResourceMetadataManager
from biomapper.spoke.client import SPOKEDBClient, SPOKEConfig
from biomapper.utils.config import Config


logger = logging.getLogger(__name__)


class MetadataFactory:
    """Factory for creating and configuring components of the resource metadata system."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the metadata factory.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.metadata_manager = None
        self.adapters = {}
        self.dispatcher = None
    
    def create_metadata_manager(
        self, 
        force_init: bool = False
    ) -> ResourceMetadataManager:
        """Create and initialize the resource metadata manager.
        
        Args:
            force_init: Whether to force initialization even if tables exist
            
        Returns:
            ResourceMetadataManager instance
        """
        if self.metadata_manager is None:
            self.metadata_manager = initialize_metadata_system(
                config=self.config,
                force_init=force_init,
            )
        
        return self.metadata_manager
    
    def create_cache_adapter(self) -> CacheResourceAdapter:
        """Create a cache resource adapter.
        
        Returns:
            CacheResourceAdapter instance
        """
        # Create metadata manager if not already created
        if self.metadata_manager is None:
            self.create_metadata_manager()
        
        # Configure cache manager from config
        cache_config = self.config.get("cache", {})
        data_dir = cache_config.get("data_dir")
        db_name = cache_config.get("db_name")
        
        cache_manager = CacheManager(data_dir=data_dir, db_name=db_name)
        
        # Create adapter
        adapter = CacheResourceAdapter(
            cache_manager=cache_manager,
            metadata_manager=self.metadata_manager,
            resource_name="sqlite_cache",
        )
        
        # Store adapter for reuse
        self.adapters["sqlite_cache"] = adapter
        
        return adapter
    
    def create_spoke_adapter(self) -> SpokeResourceAdapter:
        """Create a SPOKE resource adapter.
        
        Returns:
            SpokeResourceAdapter instance
        """
        # Create metadata manager if not already created
        if self.metadata_manager is None:
            self.create_metadata_manager()
        
        # Configure SPOKE client from config
        spoke_config = self.config.get("spoke", {})
        host = spoke_config.get("host", "localhost")
        port = spoke_config.get("port", 8529)
        database = spoke_config.get("database", "spoke")
        username = spoke_config.get("username")
        password = spoke_config.get("password")
        
        config = SPOKEConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password
        )
        spoke_client = SPOKEDBClient(config)
        
        # Create adapter
        adapter = SpokeResourceAdapter(
            spoke_client=spoke_client,
            metadata_manager=self.metadata_manager,
            resource_name="spoke_graph",
        )
        
        # Store adapter for reuse
        self.adapters["spoke_graph"] = adapter
        
        return adapter
    
    def create_dispatcher(
        self,
        result_class: Optional[Type] = None,
        include_resources: Optional[List[str]] = None,
    ) -> MappingDispatcher:
        """Create a mapping dispatcher with registered resources.
        
        Args:
            result_class: Optional class for mapping results
            include_resources: Optional list of resource names to include
            
        Returns:
            MappingDispatcher instance
        """
        # Create metadata manager if not already created
        if self.metadata_manager is None:
            self.create_metadata_manager()
        
        # Create dispatcher
        dispatcher = MappingDispatcher(
            metadata_manager=self.metadata_manager,
            result_class=result_class,
        )
        
        # If no specific resources requested, use all available
        if include_resources is None:
            include_resources = ["sqlite_cache", "spoke_graph"]
        
        # Register cache adapter if needed
        if "sqlite_cache" in include_resources:
            if "sqlite_cache" not in self.adapters:
                self.create_cache_adapter()
            
            dispatcher.register_resource("sqlite_cache", self.adapters["sqlite_cache"])
        
        # Register SPOKE adapter if needed
        if "spoke_graph" in include_resources:
            if "spoke_graph" not in self.adapters:
                self.create_spoke_adapter()
            
            dispatcher.register_resource("spoke_graph", self.adapters["spoke_graph"])
        
        # Store dispatcher for reuse
        self.dispatcher = dispatcher
        
        return dispatcher
    
    def create_complete_system(
        self,
        result_class: Optional[Type] = None,
        force_init: bool = False,
    ) -> Dict[str, Any]:
        """Create a complete metadata system with all components.
        
        Args:
            result_class: Optional class for mapping results
            force_init: Whether to force initialization even if tables exist
            
        Returns:
            Dictionary with all created components
        """
        # Initialize metadata manager
        metadata_manager = self.create_metadata_manager(force_init=force_init)
        
        # Create adapters
        cache_adapter = self.create_cache_adapter()
        spoke_adapter = self.create_spoke_adapter()
        
        # Create dispatcher
        dispatcher = self.create_dispatcher(result_class=result_class)
        
        return {
            "metadata_manager": metadata_manager,
            "cache_adapter": cache_adapter,
            "spoke_adapter": spoke_adapter,
            "dispatcher": dispatcher,
        }

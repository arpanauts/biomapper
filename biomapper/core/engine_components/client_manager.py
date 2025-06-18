"""
Client Manager for handling client instantiation and caching.

This module contains the ClientManager class which is responsible for:
- Loading client classes dynamically
- Instantiating clients with configuration
- Caching client instances for reuse
- Managing client lifecycle
"""

import importlib
import json
import logging
from typing import Any, Dict

from ..exceptions import ClientInitializationError
from ..db.models import MappingResource


class ClientManager:
    """Manages client instantiation, configuration, and caching."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the ClientManager.
        
        Args:
            logger: Logger instance to use for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self._client_cache: Dict[str, Any] = {}
    
    async def _load_client_class(self, client_class_path: str) -> type:
        """Dynamically load the client class."""
        try:
            module_path, class_name = client_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            ClientClass = getattr(module, class_name)
            return ClientClass
        except (ImportError, AttributeError) as e:
            self.logger.error(
                f"Error loading client class '{client_class_path}': {e}", exc_info=True
            )
            raise ClientInitializationError(
                f"Could not load client class {client_class_path}",
                client_name=client_class_path.split(".")[-1] if "." in client_class_path else client_class_path,
                details={"error": str(e)}
            ) from e

    async def get_client_instance(self, resource: MappingResource) -> Any:
        """Loads and initializes a client instance, using cache for expensive clients.
        
        Args:
            resource: The mapping resource containing client configuration
            
        Returns:
            The initialized client instance
            
        Raises:
            ClientInitializationError: If client initialization fails
        """
        # Create a cache key based on resource name and config
        cache_key = f"{resource.name}_{resource.client_class_path}"
        if resource.config_template:
            # Include config in cache key to handle different configurations
            cache_key += f"_{hash(resource.config_template)}"
        
        # Check if client is already cached
        if cache_key in self._client_cache:
            self.logger.debug(f"OPTIMIZATION: Using cached client for {resource.name}")
            return self._client_cache[cache_key]
        
        try:
            client_class = await self._load_client_class(resource.client_class_path)
            # Parse the config template
            config_for_init = {}
            if resource.config_template:
                try:
                    config_for_init = json.loads(resource.config_template)
                except json.JSONDecodeError as json_err:
                    raise ClientInitializationError(
                        f"Invalid configuration template JSON for {resource.name}",
                        client_name=resource.name,
                        details=str(json_err),
                    )

            # Initialize the client with the config, passing it as 'config'
            self.logger.debug(f"OPTIMIZATION: Creating new client instance for {resource.name}")
            client_instance = client_class(config=config_for_init)
            
            # Cache the client instance for future use
            self._client_cache[cache_key] = client_instance
            self.logger.debug(f"OPTIMIZATION: Cached client for {resource.name}")
            
            return client_instance
        except ImportError as e:
            self.logger.error(
                f"ImportError during client initialization for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Import error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            ) from e
        except AttributeError as e:
            self.logger.error(
                f"AttributeError during client initialization for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Attribute error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            ) from e
        except Exception as e:
            # Catch any other initialization errors
            self.logger.error(
                f"Unexpected error initializing client for resource {resource.name}: {e}",
                exc_info=True,
            )
            raise ClientInitializationError(
                f"Unexpected error initializing client",
                client_name=resource.name if resource else "Unknown",
                details=str(e),
            )
    
    def get_client_cache(self) -> Dict[str, Any]:
        """Get the current client cache dictionary.
        
        Returns:
            Dictionary containing cached client instances
        """
        return self._client_cache
    
    def clear_cache(self) -> None:
        """Clear all cached client instances."""
        self._client_cache.clear()
        self.logger.debug("Client cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the number of cached client instances.
        
        Returns:
            Number of cached clients
        """
        return len(self._client_cache)
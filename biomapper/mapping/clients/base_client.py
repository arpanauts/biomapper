"""Base class and interfaces for biomapper mapping clients.

This module provides a standardized interface for all mapping clients to follow,
ensuring consistent behavior, error handling, and return types across the system.
"""

import abc
import logging
from typing import Dict, List, Optional, Any, Tuple, TypeVar, Generic, Union, Type
import json
import functools
import asyncio
from datetime import datetime

from biomapper.core.exceptions import (
    ClientError,
    ClientInitializationError,
    ClientExecutionError,
    ErrorCode,
)

logger = logging.getLogger(__name__)

# Type variable for input/output identifiers
T = TypeVar('T')
U = TypeVar('U')


class BaseMappingClient(abc.ABC):
    """Abstract base class for all mapping clients.
    
    Provides a standardized interface and common functionality for all clients
    that map identifiers between different ontologies or databases.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the client with optional configuration.
        
        Args:
            config: Optional configuration dictionary with client-specific settings.
                   Subclasses should document their specific configuration options.
        """
        self._config = config or {}
        self._initialized = False
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the provided configuration.
        
        Raises:
            ClientInitializationError: If the configuration is invalid.
        """
        # Basic validation in base class
        required_keys = self.get_required_config_keys()
        missing_keys = [key for key in required_keys if key not in self._config]
        
        if missing_keys:
            missing_keys_str = ', '.join(f"'{k}'" for k in missing_keys)
            error_msg = f"{self.__class__.__name__}: Missing required configuration: {missing_keys_str}"
            logger.error(error_msg)
            raise ClientInitializationError(
                error_msg,
                client_name=self.__class__.__name__,
                details={"missing_keys": missing_keys}
            )
    
    def get_required_config_keys(self) -> List[str]:
        """Return a list of required configuration keys for this client.
        
        Returns:
            List of required configuration key names.
        """
        # Base implementation returns empty list - subclasses should override
        return []
    
    @abc.abstractmethod
    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Map a list of source identifiers to target identifiers.
        
        This is the core method that all mapping clients must implement.
        
        Args:
            identifiers: List of source identifiers to map.
            config: Optional per-call configuration that may override instance config.
            
        Returns:
            A dictionary mapping each input identifier to a tuple containing:
            - The first element is a list of mapped target identifiers or None if mapping failed
            - The second element is the component ID that yielded the match (for composite IDs) or None
        """
        pass
    
    async def reverse_map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Optionally map identifiers in the reverse direction.
        
        This method provides reverse mapping capability for clients that support it.
        The default implementation raises a NotImplementedError.
        
        Args:
            identifiers: List of target identifiers to map back to source identifiers.
            config: Optional per-call configuration that may override instance config.
            
        Returns:
            A dictionary similar to map_identifiers, but mapping in reverse direction.
            
        Raises:
            NotImplementedError: If the client does not support reverse mapping.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement reverse_map_identifiers"
        )
    
    def get_config_value(self, key: str, default: Optional[T] = None) -> T:
        """Get a configuration value with an optional default.
        
        Args:
            key: The configuration key to retrieve.
            default: The default value to return if the key is not found.
            
        Returns:
            The configuration value if found, otherwise the default.
        """
        return self._config.get(key, default)
    
    @staticmethod
    def format_result(
        target_ids: Optional[List[str]] = None, 
        component_id: Optional[str] = None
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        """Format the result tuple in the standardized format.
        
        This helper ensures consistent result formatting across all clients.
        
        Args:
            target_ids: List of mapped target identifiers or None if mapping failed.
            component_id: The component ID that yielded the match (for composite IDs) or None.
            
        Returns:
            A tuple in the format expected by the MappingExecutor.
        """
        return (target_ids, component_id)
    
    async def close(self) -> None:
        """Close any resources used by this client.
        
        This method is called when the client is no longer needed.
        The default implementation does nothing.
        """
        pass


class CachedMappingClientMixin:
    """Mixin that adds caching capabilities to a mapping client.
    
    This mixin provides an in-memory cache for mapping results to improve
    performance when the same identifiers are mapped multiple times.
    """
    
    def __init__(self, cache_size: int = 1024, **kwargs):
        """Initialize the cache.
        
        Args:
            cache_size: Maximum number of entries to store in the cache.
            **kwargs: Additional arguments to pass to the parent class.
        """
        # Initialize parent class first if this is a mixin
        super().__init__(**kwargs)
        
        # Initialize cache
        self._cache: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_initialized = False
        self._cache_lock = asyncio.Lock()  # For thread safety
    
    async def _get_from_cache(self, identifier: str) -> Optional[Tuple[Optional[List[str]], Optional[str]]]:
        """Get a mapping result from the cache.
        
        Args:
            identifier: The source identifier to look up.
            
        Returns:
            The cached result tuple if found, otherwise None.
        """
        async with self._cache_lock:
            if identifier in self._cache:
                self._cache_hits += 1
                return self._cache[identifier]
            self._cache_misses += 1
            return None
    
    async def _add_to_cache(
        self, identifier: str, result: Tuple[Optional[List[str]], Optional[str]]
    ) -> None:
        """Add a mapping result to the cache.
        
        Args:
            identifier: The source identifier.
            result: The mapping result tuple.
        """
        async with self._cache_lock:
            # Simple LRU-like behavior: if cache is full, remove a random entry
            if len(self._cache) >= self._cache_size:
                # Remove an arbitrary key (first one)
                self._cache.pop(next(iter(self._cache)))
            
            self._cache[identifier] = result
    
    async def _add_many_to_cache(
        self, results: Dict[str, Tuple[Optional[List[str]], Optional[str]]]
    ) -> None:
        """Add multiple mapping results to the cache at once.
        
        Args:
            results: Dictionary mapping source identifiers to result tuples.
        """
        async with self._cache_lock:
            # Simple implementation: just add each result individually
            for identifier, result in results.items():
                if len(self._cache) >= self._cache_size:
                    # Remove an arbitrary key (first one)
                    self._cache.pop(next(iter(self._cache)))
                
                self._cache[identifier] = result
    
    async def _preload_cache(self) -> None:
        """Preload the cache with common mappings.
        
        This method is called during initialization to populate the cache
        with frequently used mappings. The default implementation does nothing.
        """
        pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache usage.
        
        Returns:
            Dictionary with cache statistics.
        """
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0,
            "initialized": self._cache_initialized,
        }
    
    async def clear_cache(self) -> None:
        """Clear the cache."""
        async with self._cache_lock:
            self._cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0


class FileLookupClientMixin:
    """Mixin for clients that perform lookups from local files.
    
    This mixin provides common functionality for clients that load
    lookup data from local files, including file validation, loading,
    and error handling.
    """
    
    def __init__(
        self,
        file_path_key: str = "file_path",
        key_column_key: str = "key_column",
        value_column_key: str = "value_column",
        **kwargs
    ):
        """Initialize the file lookup client mixin.
        
        Args:
            file_path_key: The configuration key for the file path.
            key_column_key: The configuration key for the key column name.
            value_column_key: The configuration key for the value column name.
            **kwargs: Additional arguments to pass to the parent class.
        """
        # Initialize parent class first if this is a mixin
        super().__init__(**kwargs)
        
        # Save key names
        self._file_path_key = file_path_key
        self._key_column_key = key_column_key
        self._value_column_key = value_column_key
    
    def get_required_config_keys(self) -> List[str]:
        """Return a list of required configuration keys for this client.
        
        Returns:
            List of required configuration key names.
        """
        # Add file lookup specific keys to any keys required by parent classes
        parent_keys = super().get_required_config_keys() if hasattr(super(), "get_required_config_keys") else []
        return parent_keys + [self._file_path_key, self._key_column_key, self._value_column_key]
    
    def _get_file_path(self) -> str:
        """Get the file path from the configuration.
        
        Returns:
            The file path as a string.
        """
        return self._config.get(self._file_path_key, "")
    
    def _get_key_column(self) -> str:
        """Get the key column name from the configuration.
        
        Returns:
            The key column name as a string.
        """
        return self._config.get(self._key_column_key, "")
    
    def _get_value_column(self) -> str:
        """Get the value column name from the configuration.
        
        Returns:
            The value column name as a string.
        """
        return self._config.get(self._value_column_key, "")
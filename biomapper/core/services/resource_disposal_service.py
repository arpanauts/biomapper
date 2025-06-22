"""
ResourceDisposalService - Manages cleanup and disposal of system resources.

This service handles the proper disposal of database engines, sessions,
client caches, and other resources that need cleanup when the system shuts down.
It provides a centralized place for resource management and cleanup operations.
"""

import logging
from typing import Optional, List, Any, Dict
import asyncio

from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.engine_components.client_manager import ClientManager

logger = logging.getLogger(__name__)


class ResourceDisposalService:
    """
    Service that manages resource cleanup and disposal.
    
    This service is responsible for:
    - Disposing database engines (metamapper and cache)
    - Clearing client caches
    - Managing graceful shutdown of resources
    - Tracking resource lifecycle
    
    It provides a centralized interface for resource disposal operations
    that were previously scattered across different components.
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        client_manager: Optional[ClientManager] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the ResourceDisposalService.
        
        Args:
            session_manager: Manager for database sessions and engines
            client_manager: Optional manager for client connections
            logger: Optional logger instance
        """
        self.session_manager = session_manager
        self.client_manager = client_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Track disposal state
        self._is_disposed = False
        self._disposal_tasks: List[asyncio.Task] = []
        
        self.logger.info("ResourceDisposalService initialized")
    
    # Main Disposal Method
    
    async def dispose_all(self) -> None:
        """
        Dispose of all managed resources.
        
        This method ensures all resources are properly cleaned up,
        including database engines and client caches. It's idempotent
        and can be called multiple times safely.
        """
        if self._is_disposed:
            self.logger.debug("Resources already disposed, skipping")
            return
        
        self.logger.info("Starting resource disposal...")
        
        try:
            # Dispose resources in parallel where possible
            disposal_tasks = []
            
            # Dispose metamapper engine
            if self._has_metamapper_engine():
                disposal_tasks.append(self._dispose_metamapper_engine())
            
            # Dispose cache engine
            if self._has_cache_engine():
                disposal_tasks.append(self._dispose_cache_engine())
            
            # Clear client cache (synchronous operation)
            if self.client_manager:
                self._clear_client_cache()
            
            # Wait for all async disposals to complete
            if disposal_tasks:
                results = await asyncio.gather(*disposal_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Disposal task {i} failed: {result}")
            
            self._is_disposed = True
            self.logger.info("Resource disposal complete")
            
        except Exception as e:
            self.logger.error(f"Error during resource disposal: {e}")
            raise
    
    # Individual Resource Disposal Methods
    
    async def dispose_metamapper_engine(self) -> None:
        """
        Dispose of the metamapper database engine.
        
        This method specifically handles the disposal of the metamapper
        database engine and its associated resources.
        """
        if not self._has_metamapper_engine():
            self.logger.debug("No metamapper engine to dispose")
            return
        
        await self._dispose_metamapper_engine()
    
    async def _dispose_metamapper_engine(self) -> None:
        """Internal method to dispose metamapper engine."""
        try:
            await self.session_manager.async_metamapper_engine.dispose()
            self.logger.info("Metamapper engine disposed")
        except Exception as e:
            self.logger.error(f"Failed to dispose metamapper engine: {e}")
            raise
    
    async def dispose_cache_engine(self) -> None:
        """
        Dispose of the cache database engine.
        
        This method specifically handles the disposal of the cache
        database engine and its associated resources.
        """
        if not self._has_cache_engine():
            self.logger.debug("No cache engine to dispose")
            return
        
        await self._dispose_cache_engine()
    
    async def _dispose_cache_engine(self) -> None:
        """Internal method to dispose cache engine."""
        try:
            await self.session_manager.async_cache_engine.dispose()
            self.logger.info("Cache engine disposed")
        except Exception as e:
            self.logger.error(f"Failed to dispose cache engine: {e}")
            raise
    
    def clear_client_cache(self) -> None:
        """
        Clear the client cache.
        
        This method clears any cached client connections or data,
        ensuring a clean state for future operations.
        """
        if not self.client_manager:
            self.logger.debug("No client manager to clear")
            return
        
        self._clear_client_cache()
    
    def _clear_client_cache(self) -> None:
        """Internal method to clear client cache."""
        try:
            self.client_manager.clear_cache()
            self.logger.info("Client cache cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear client cache: {e}")
            raise
    
    # Resource State Checking Methods
    
    def _has_metamapper_engine(self) -> bool:
        """Check if metamapper engine exists and needs disposal."""
        return (
            hasattr(self.session_manager, 'async_metamapper_engine') 
            and self.session_manager.async_metamapper_engine is not None
        )
    
    def _has_cache_engine(self) -> bool:
        """Check if cache engine exists and needs disposal."""
        return (
            hasattr(self.session_manager, 'async_cache_engine') 
            and self.session_manager.async_cache_engine is not None
        )
    
    @property
    def is_disposed(self) -> bool:
        """Check if resources have been disposed."""
        return self._is_disposed
    
    # Graceful Shutdown Support
    
    async def register_for_shutdown(self) -> None:
        """
        Register this service for graceful shutdown.
        
        This method can be used to register the disposal service
        with application shutdown handlers to ensure resources
        are cleaned up properly on exit.
        """
        # This could be extended to register with signal handlers
        # or application lifecycle events
        self.logger.debug("Registered for graceful shutdown")
    
    async def dispose_on_error(self, error: Exception) -> None:
        """
        Perform emergency disposal on critical error.
        
        This method provides a way to clean up resources when
        a critical error occurs that requires immediate cleanup.
        
        Args:
            error: The error that triggered emergency disposal
        """
        self.logger.error(f"Emergency disposal triggered by error: {error}")
        
        try:
            await self.dispose_all()
        except Exception as disposal_error:
            self.logger.error(f"Failed to dispose resources on error: {disposal_error}")
            # Continue anyway - best effort cleanup
    
    # Context Manager Support
    
    async def __aenter__(self) -> 'ResourceDisposalService':
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and dispose resources."""
        await self.dispose_all()
    
    # Utility Methods
    
    def get_resource_status(self) -> Dict[str, bool]:
        """
        Get the status of managed resources.
        
        Returns:
            Dictionary mapping resource names to their active status
        """
        return {
            'metamapper_engine': self._has_metamapper_engine(),
            'cache_engine': self._has_cache_engine(),
            'client_manager': self.client_manager is not None,
            'is_disposed': self._is_disposed
        }
    
    async def verify_disposal(self) -> bool:
        """
        Verify that all resources have been properly disposed.
        
        Returns:
            True if all resources are disposed, False otherwise
        """
        if not self._is_disposed:
            return False
        
        # Check that resources are actually disposed
        status = self.get_resource_status()
        active_resources = [k for k, v in status.items() if v and k != 'is_disposed']
        
        if active_resources:
            self.logger.warning(f"Resources still active after disposal: {active_resources}")
            return False
        
        return True
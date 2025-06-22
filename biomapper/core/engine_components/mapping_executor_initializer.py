"""
MappingExecutor Initializer for handling MappingExecutor initialization logic.

**DEPRECATED**: This module is deprecated. Use InitializationService instead.

This module contains the MappingExecutorInitializer class which was responsible for:
- Setting up all engine components required by MappingExecutor
- Configuring database connections and sessions
- Initializing performance monitoring and metrics tracking
- Managing component dependencies and lifecycle
- Providing a clean separation of initialization concerns from core execution logic

All this functionality has been moved to InitializationService.
"""

import logging
import os
import warnings
from typing import Optional, Dict, Any

from .initialization_service import InitializationService
from .session_manager import SessionManager
from .client_manager import ClientManager
from .config_loader import ConfigLoader
from .strategy_handler import StrategyHandler
from .path_finder import PathFinder
from .path_execution_manager import PathExecutionManager
from .cache_manager import CacheManager
from .identifier_loader import IdentifierLoader
from .strategy_orchestrator import StrategyOrchestrator
from .checkpoint_manager import CheckpointManager
from .progress_reporter import ProgressReporter

from ..exceptions import BiomapperError, ErrorCode
from sqlalchemy import inspect
from biomapper.config import settings

# Import models for cache DB
from ...db.cache_models import (
    Base as CacheBase,  # Import the Base for cache tables
)

# Import database setup service
from ..services.database_setup_service import DatabaseSetupService


class MappingExecutorInitializer:
    """Handles initialization of MappingExecutor components and dependencies.
    
    **DEPRECATED**: This class is deprecated in favor of InitializationService.
    Use InitializationService.create_components_from_config() instead.
    
    This class was responsible for encapsulating all the complex initialization logic
    required to set up a MappingExecutor instance with all its dependencies properly
    configured and connected. This functionality has been moved to InitializationService
    which provides a cleaner, more centralized approach to component creation.
    
    This class now delegates all initialization to InitializationService for backward
    compatibility and will be removed in a future version.
    """
    
    def __init__(
        self,
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False,
        path_cache_size: int = 100,
        path_cache_expiry_seconds: int = 300,
        max_concurrent_batches: int = 5,
        enable_metrics: bool = True,
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """Initialize the MappingExecutorInitializer with configuration parameters.
        
        **DEPRECATED**: Use InitializationService instead.
        
        Args:
            metamapper_db_url: URL for the metamapper database. If None, uses settings.metamapper_db_url.
            mapping_cache_db_url: URL for the mapping cache database. If None, uses settings.cache_db_url.
            echo_sql: Boolean flag to enable SQL echoing for debugging purposes.
            path_cache_size: Maximum number of paths to cache in memory
            path_cache_expiry_seconds: Cache expiry time in seconds
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            checkpoint_enabled: Enable checkpointing for resumable execution
            checkpoint_dir: Directory for checkpoint files
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
        """
        warnings.warn(
            "MappingExecutorInitializer is deprecated. Use InitializationService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.logger = logging.getLogger(__name__)
        
        # Store configuration parameters
        self.metamapper_db_url = (
            metamapper_db_url
            if metamapper_db_url is not None
            else settings.metamapper_db_url
        )
        self.mapping_cache_db_url = (
            mapping_cache_db_url
            if mapping_cache_db_url is not None
            else settings.cache_db_url
        )
        self.echo_sql = echo_sql
        self.path_cache_size = path_cache_size
        self.path_cache_expiry_seconds = path_cache_expiry_seconds
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_metrics = enable_metrics
        self.checkpoint_enabled = checkpoint_enabled
        self.checkpoint_dir = checkpoint_dir
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize component references
        self.session_manager = None
        self.client_manager = None
        self.config_loader = None
        self.strategy_handler = None
        self.path_finder = None
        self.path_execution_manager = None
        self.cache_manager = None
        self.identifier_loader = None
        self.strategy_orchestrator = None
        self.checkpoint_manager = None
        self.progress_reporter = None
        self._langfuse_tracker = None
        
        self.logger.info("MappingExecutorInitializer configured with:")
        self.logger.info(f"  Metamapper DB URL: {self.metamapper_db_url}")
        self.logger.info(f"  Mapping Cache DB URL: {self.mapping_cache_db_url}")
        self.logger.info(f"  Path cache size: {path_cache_size}, concurrent batches: {max_concurrent_batches}")
        self.logger.info(f"  Metrics enabled: {enable_metrics}, checkpoints enabled: {checkpoint_enabled}")
    
    def initialize_components(self, mapping_executor):
        """Initialize all components required by the MappingExecutor.
        
        **DEPRECATED**: This method now delegates to InitializationService.
        
        Args:
            mapping_executor: The MappingExecutor instance to initialize components for
            
        Returns:
            dict: Dictionary containing all initialized components
        """
        self.logger.info("MappingExecutorInitializer.initialize_components is deprecated, delegating to InitializationService")
        
        # Create configuration dictionary
        config = {
            'metamapper_db_url': self.metamapper_db_url,
            'mapping_cache_db_url': self.mapping_cache_db_url,
            'echo_sql': self.echo_sql,
            'path_cache_size': self.path_cache_size,
            'path_cache_expiry_seconds': self.path_cache_expiry_seconds,
            'max_concurrent_batches': self.max_concurrent_batches,
            'enable_metrics': self.enable_metrics,
            'checkpoint_enabled': self.checkpoint_enabled,
            'checkpoint_dir': self.checkpoint_dir,
            'batch_size': self.batch_size,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
        }
        
        # Use InitializationService to create all components
        initialization_service = InitializationService()
        components = initialization_service.create_components_from_config(config)
        
        # Complete initialization with mapping_executor reference
        components = initialization_service.complete_initialization(mapping_executor, components)
        
        # Store references to components for backward compatibility
        self.session_manager = components['session_manager']
        self.client_manager = components['client_manager']
        self.config_loader = components['config_loader']
        self.strategy_handler = components['strategy_handler']
        self.path_finder = components['path_finder']
        self.path_execution_manager = components['path_execution_manager']
        self.cache_manager = components['cache_manager']
        self.identifier_loader = components['identifier_loader']
        self.strategy_orchestrator = components['strategy_orchestrator']
        self.checkpoint_manager = components['checkpoint_manager']
        self.progress_reporter = components['progress_reporter']
        self._langfuse_tracker = components['langfuse_tracker']
        
        return components
    
    def _initialize_core_components(self):
        """Initialize core components that don't depend on other components.
        
        **DEPRECATED**: This method is no longer used. All initialization is handled by InitializationService.
        """
        warnings.warn(
            "_initialize_core_components is deprecated and no longer used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _initialize_session_manager(self):
        """Initialize the SessionManager and database connections.
        
        **DEPRECATED**: This method is no longer used. All initialization is handled by InitializationService.
        """
        warnings.warn(
            "_initialize_session_manager is deprecated and no longer used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _initialize_cache_manager(self):
        """Initialize the CacheManager with database session factory.
        
        **DEPRECATED**: This method is no longer used. All initialization is handled by InitializationService.
        """
        warnings.warn(
            "_initialize_cache_manager is deprecated and no longer used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _initialize_execution_components(self, mapping_executor):
        """Initialize execution-related components that depend on other components.
        
        **DEPRECATED**: This method is no longer used. All initialization is handled by InitializationService.
        
        Args:
            mapping_executor: The MappingExecutor instance to provide to components
        """
        warnings.warn(
            "_initialize_execution_components is deprecated and no longer used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def _initialize_metrics_tracking(self):
        """Initialize metrics tracking if enabled and available.
        
        **DEPRECATED**: This method is no longer used. All initialization is handled by InitializationService.
        """
        warnings.warn(
            "_initialize_metrics_tracking is deprecated and no longer used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def get_convenience_references(self):
        """Get convenience references for backward compatibility.
        
        **DEPRECATED**: This method now delegates to InitializationService.
        
        Returns:
            dict: Dictionary containing convenience references to engine and session factories
        """
        warnings.warn(
            "get_convenience_references is deprecated. Use InitializationService._get_session_convenience_references instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        if not self.session_manager:
            raise BiomapperError(
                "SessionManager must be initialized before getting convenience references",
                error_code=ErrorCode.CONFIGURATION_ERROR
            )
        
        initialization_service = InitializationService()
        return initialization_service._get_session_convenience_references(self.session_manager)
    
    def set_executor_function_references(self, mapping_executor):
        """Set function references on PathExecutionManager after MappingExecutor is fully initialized.
        
        **DEPRECATED**: This method now delegates to InitializationService.
        
        Args:
            mapping_executor: The fully initialized MappingExecutor instance
        """
        warnings.warn(
            "set_executor_function_references is deprecated. Use InitializationService.set_executor_function_references instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        if self.path_execution_manager:
            initialization_service = InitializationService()
            initialization_service.set_executor_function_references(mapping_executor, self.path_execution_manager)
    

    async def create_executor(self):
        """Asynchronously create and initialize a MappingExecutor instance.
        
        This factory method creates all components needed by MappingExecutor,
        initializes the database tables, and returns a fully configured executor.
        
        Returns:
            An initialized MappingExecutor instance with database tables created
        """
        try:
            # Import here to avoid circular imports
            from ..mapping_executor import MappingExecutor
            
            # Create a dummy executor to pass to components that need it
            # This will be replaced with the real executor after it's created
            dummy_executor = type('DummyExecutor', (), {})()
            
            # Initialize all components
            components = self.initialize_components(dummy_executor)
            
            # Create the executor with pre-initialized components
            executor = MappingExecutor(
                session_manager=components['session_manager'],
                client_manager=components['client_manager'],
                config_loader=components['config_loader'],
                strategy_handler=components['strategy_handler'],
                path_finder=components['path_finder'],
                path_execution_manager=components['path_execution_manager'],
                cache_manager=components['cache_manager'],
                identifier_loader=components['identifier_loader'],
                strategy_orchestrator=components['strategy_orchestrator'],
                checkpoint_manager=components['checkpoint_manager'],
                progress_reporter=components['progress_reporter'],
                langfuse_tracker=components['langfuse_tracker'],
                # Pass configuration parameters for backward compatibility
                batch_size=self.batch_size,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                checkpoint_enabled=self.checkpoint_enabled,
                max_concurrent_batches=self.max_concurrent_batches,
                enable_metrics=self.enable_metrics,
            )
            
            # Now update components that need the real executor reference
            components['strategy_handler'].mapping_executor = executor
            components['strategy_orchestrator'].mapping_executor = executor
            
            # Set function references
            self.set_executor_function_references(executor)
            
            # Initialize cache database tables
            await self._init_db_tables(components['session_manager'].async_cache_engine, CacheBase.metadata)
            
            executor.logger.info("MappingExecutor instance created and database tables initialized.")
            return executor
            
        except Exception as e:
            self.logger.error(f"Failed to create MappingExecutor: {str(e)}", exc_info=True)
            raise BiomapperError(
                f"MappingExecutor creation failed: {str(e)}",
                error_code=ErrorCode.CONFIGURATION_ERROR,
                details={
                    "metamapper_db_url": self.metamapper_db_url,
                    "cache_db_url": self.mapping_cache_db_url,
                    "error": str(e)
                }
            ) from e
    
    async def _init_db_tables(self, engine, metadata):
        """Initialize database tables using the provided engine and metadata.
        
        This method exists for backward compatibility with tests.
        The actual implementation delegates to DatabaseSetupService.
        
        Args:
            engine: The SQLAlchemy async engine
            metadata: The SQLAlchemy metadata object containing table definitions
        """
        # Import DatabaseSetupService
        from ..services.database_setup_service import DatabaseSetupService
        
        # Use DatabaseSetupService to initialize tables
        db_setup_service = DatabaseSetupService(logger=self.logger)
        await db_setup_service.initialize_tables(engine, metadata)
"""
MappingExecutor Initializer for handling MappingExecutor initialization logic.

This module contains the MappingExecutorInitializer class which is responsible for:
- Setting up all engine components required by MappingExecutor
- Configuring database connections and sessions
- Initializing performance monitoring and metrics tracking
- Managing component dependencies and lifecycle
- Providing a clean separation of initialization concerns from core execution logic
"""

import logging
import os
from typing import Optional

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
    
    This class encapsulates all the complex initialization logic required to set up
    a MappingExecutor instance with all its dependencies properly configured and
    connected. It provides a clean separation between initialization concerns and
    core execution logic.
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
        
        Args:
            mapping_executor: The MappingExecutor instance to initialize components for
            
        Returns:
            dict: Dictionary containing all initialized components
        """
        try:
            # Initialize components in dependency order
            self._initialize_core_components()
            self._initialize_session_manager()
            self._initialize_cache_manager()
            self._initialize_execution_components(mapping_executor)
            self._initialize_metrics_tracking()
            
            # Return all components for assignment to MappingExecutor
            return {
                'session_manager': self.session_manager,
                'client_manager': self.client_manager,
                'config_loader': self.config_loader,
                'strategy_handler': self.strategy_handler,
                'path_finder': self.path_finder,
                'path_execution_manager': self.path_execution_manager,
                'cache_manager': self.cache_manager,
                'identifier_loader': self.identifier_loader,
                'strategy_orchestrator': self.strategy_orchestrator,
                'checkpoint_manager': self.checkpoint_manager,
                'progress_reporter': self.progress_reporter,
                'langfuse_tracker': self._langfuse_tracker,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MappingExecutor components: {str(e)}", exc_info=True)
            raise BiomapperError(
                f"MappingExecutor initialization failed: {str(e)}",
                error_code=ErrorCode.CONFIGURATION_ERROR,
                details={
                    "metamapper_db_url": self.metamapper_db_url,
                    "cache_db_url": self.mapping_cache_db_url,
                    "error": str(e)
                }
            ) from e
    
    def _initialize_core_components(self):
        """Initialize core components that don't depend on other components."""
        self.logger.debug("Initializing core components...")
        
        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=self.checkpoint_dir if self.checkpoint_enabled else None,
            logger=self.logger
        )
        
        # Initialize progress reporter
        self.progress_reporter = ProgressReporter()
        
        # Initialize client manager for handling client instantiation and caching
        self.client_manager = ClientManager(logger=self.logger)
        
        # Initialize config loader for handling strategy configuration files
        self.config_loader = ConfigLoader(logger=self.logger)
        
        # Initialize path finder with cache settings
        self.path_finder = PathFinder(
            cache_size=self.path_cache_size,
            cache_expiry_seconds=self.path_cache_expiry_seconds
        )
        
        self.logger.debug("Core components initialized successfully")
    
    def _initialize_session_manager(self):
        """Initialize the SessionManager and database connections."""
        self.logger.debug("Initializing session manager...")
        
        self.session_manager = SessionManager(
            metamapper_db_url=self.metamapper_db_url,
            mapping_cache_db_url=self.mapping_cache_db_url,
            echo_sql=self.echo_sql
        )
        
        self.logger.debug("Session manager initialized successfully")
    
    def _initialize_cache_manager(self):
        """Initialize the CacheManager with database session factory."""
        self.logger.debug("Initializing cache manager...")
        
        if not self.session_manager:
            raise BiomapperError(
                "SessionManager must be initialized before CacheManager",
                error_code=ErrorCode.CONFIGURATION_ERROR
            )
        
        self.cache_manager = CacheManager(
            cache_sessionmaker=self.session_manager.CacheSessionFactory,
            logger=self.logger
        )
        
        self.logger.debug("Cache manager initialized successfully")
    
    def _initialize_execution_components(self, mapping_executor):
        """Initialize execution-related components that depend on other components.
        
        Args:
            mapping_executor: The MappingExecutor instance to provide to components
        """
        self.logger.debug("Initializing execution components...")
        
        # Initialize strategy handler (needs mapping_executor reference)
        self.strategy_handler = StrategyHandler(mapping_executor=mapping_executor)
        
        # Initialize identifier loader
        self.identifier_loader = IdentifierLoader(
            metamapper_session_factory=self.session_manager.MetamapperSessionFactory
        )
        
        # Initialize path execution manager (function references will be set later)
        self.path_execution_manager = PathExecutionManager(
            metamapper_session_factory=self.session_manager.MetamapperSessionFactory,
            cache_manager=None,  # MappingExecutor handles caching directly
            logger=self.logger,
            semaphore=None,  # Will create semaphore as needed
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            batch_size=self.batch_size,
            max_concurrent_batches=self.max_concurrent_batches,
            enable_metrics=self.enable_metrics,
            load_client_func=None,  # Will be set after MappingExecutor is fully initialized
            execute_mapping_step_func=None,  # Will be set after MappingExecutor is fully initialized
            calculate_confidence_score_func=None,  # Will be set after MappingExecutor is fully initialized
            create_mapping_path_details_func=None,  # Will be set after MappingExecutor is fully initialized
            determine_mapping_source_func=None,  # Will be set after MappingExecutor is fully initialized
            track_mapping_metrics_func=None  # Will be set after MappingExecutor is fully initialized
        )
        
        # Initialize strategy orchestrator
        self.strategy_orchestrator = StrategyOrchestrator(
            metamapper_session_factory=self.session_manager.MetamapperSessionFactory,
            cache_manager=self.cache_manager,
            strategy_handler=self.strategy_handler,
            mapping_executor=mapping_executor,  # Pass self for backwards compatibility
            logger=self.logger
        )
        
        self.logger.debug("Execution components initialized successfully")
    
    def _initialize_metrics_tracking(self):
        """Initialize metrics tracking if enabled and available."""
        self.logger.debug("Initializing metrics tracking...")
        
        if not self.enable_metrics:
            self.logger.debug("Metrics tracking disabled")
            return
        
        try:
            import langfuse
            self._langfuse_tracker = langfuse.Langfuse(
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
            )
            self.logger.info("Langfuse metrics tracking initialized")
        except (ImportError, Exception) as e:
            self.logger.warning(f"Langfuse metrics tracking not available: {e}")
            self._langfuse_tracker = None
        
        self.logger.debug("Metrics tracking initialization completed")
    
    def get_convenience_references(self):
        """Get convenience references for backward compatibility.
        
        Returns:
            dict: Dictionary containing convenience references to engine and session factories
        """
        if not self.session_manager:
            raise BiomapperError(
                "SessionManager must be initialized before getting convenience references",
                error_code=ErrorCode.CONFIGURATION_ERROR
            )
        
        return {
            'async_metamapper_engine': self.session_manager.async_metamapper_engine,
            'MetamapperSessionFactory': self.session_manager.MetamapperSessionFactory,
            'async_metamapper_session': self.session_manager.async_metamapper_session,
            'async_cache_engine': self.session_manager.async_cache_engine,
            'CacheSessionFactory': self.session_manager.CacheSessionFactory,
            'async_cache_session': self.session_manager.async_cache_session,
        }
    
    def set_executor_function_references(self, mapping_executor):
        """Set function references on PathExecutionManager after MappingExecutor is fully initialized.
        
        Args:
            mapping_executor: The fully initialized MappingExecutor instance
        """
        if self.path_execution_manager:
            # Set function references
            self.path_execution_manager._load_client = getattr(mapping_executor, '_load_client', None)
            self.path_execution_manager._execute_mapping_step = getattr(mapping_executor, '_execute_mapping_step', None)
            self.path_execution_manager._calculate_confidence_score = getattr(mapping_executor, '_calculate_confidence_score', self.path_execution_manager._calculate_confidence_score)
            self.path_execution_manager._create_mapping_path_details = getattr(mapping_executor, '_create_mapping_path_details', self.path_execution_manager._create_mapping_path_details)
            self.path_execution_manager._determine_mapping_source = getattr(mapping_executor, '_determine_mapping_source', self.path_execution_manager._determine_mapping_source)
            if self.enable_metrics:
                self.path_execution_manager.track_mapping_metrics = getattr(mapping_executor, 'track_mapping_metrics', None)
    
    
    async def _init_db_tables(self, engine, metadata):
        """Initialize database tables using the provided engine and metadata.
        
        Args:
            engine: The SQLAlchemy async engine
            metadata: The SQLAlchemy metadata object containing table definitions
            
        Raises:
            BiomapperError: If database table initialization fails
        """
        try:
            self.logger.debug(f"Checking if tables exist in database: {engine.url}")
            
            # Check if tables already exist
            async with engine.connect() as connection:
                def check_tables_exist(connection):
                    # Check if any tables from our metadata exist
                    try:
                        # Simple check - try to get table names
                        inspector = inspect(connection)
                        existing_tables = inspector.get_table_names()
                        metadata_tables = [table.name for table in metadata.tables.values()]
                        
                        # Return True if any of our tables already exist
                        return any(table in existing_tables for table in metadata_tables)
                    except Exception:
                        # If inspection fails, assume tables don't exist
                        return False
                
                tables_exist = await connection.run_sync(check_tables_exist)
                
                if tables_exist:
                    self.logger.debug("Database tables already exist, skipping creation")
                    return
                    
            self.logger.info("Creating database tables...")
            async with engine.begin() as connection:
                await connection.run_sync(metadata.create_all)
                
            self.logger.info("Database tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database tables: {str(e)}", exc_info=True)
            raise BiomapperError(
                f"Failed to initialize database tables: {str(e)}",
                error_code=ErrorCode.DATABASE_INITIALIZATION_ERROR,
                details={
                    "database_url": str(engine.url),
                    "error": str(e)
                }
            ) from e

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
            from ...db.models import Base as MetamapperBase
            
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
            
            # Initialize both metamapper and cache database tables
            await self._init_db_tables(components['session_manager'].async_metamapper_engine, MetamapperBase.metadata)
            await self._init_db_tables(components['session_manager'].async_cache_engine, CacheBase.metadata)
            
            executor.logger.info("MappingExecutor instance created and all database tables initialized.")
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
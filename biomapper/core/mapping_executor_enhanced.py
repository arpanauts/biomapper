"""
Enhanced MappingExecutor with integrated robust execution capabilities.

This module extends the base MappingExecutor with checkpointing, retry logic,
and progress tracking features.
"""

from typing import Optional

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.mapping_executor_robust import RobustExecutionMixin


class EnhancedMappingExecutor(RobustExecutionMixin, MappingExecutor):
    """
    Enhanced version of MappingExecutor with integrated robust execution features.
    
    This class combines the standard MappingExecutor functionality with:
    - Checkpointing for resumable execution
    - Retry logic for failed operations
    - Progress tracking and reporting
    - Batch processing with configurable sizes
    
    The robust features are opt-in via constructor parameters, maintaining
    backward compatibility with the standard MappingExecutor.
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
        # Robust execution parameters
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize the enhanced mapping executor.
        
        Args:
            metamapper_db_url: URL for the metamapper database
            mapping_cache_db_url: URL for the mapping cache database
            echo_sql: Boolean flag to enable SQL echoing
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
        # Initialize with all parameters
        super().__init__(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=mapping_cache_db_url,
            echo_sql=echo_sql,
            path_cache_size=path_cache_size,
            path_cache_expiry_seconds=path_cache_expiry_seconds,
            max_concurrent_batches=max_concurrent_batches,
            enable_metrics=enable_metrics,
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=checkpoint_dir,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        self.logger.info(
            f"EnhancedMappingExecutor initialized with robust features: "
            f"checkpoint={checkpoint_enabled}, batch_size={batch_size}, "
            f"max_retries={max_retries}"
        )
    
    @classmethod
    async def create(
        cls,
        metamapper_db_url: Optional[str] = None,
        mapping_cache_db_url: Optional[str] = None,
        echo_sql: bool = False,
        path_cache_size: int = 100,
        path_cache_expiry_seconds: int = 300,
        max_concurrent_batches: int = 5,
        enable_metrics: bool = True,
        # Robust execution parameters
        checkpoint_enabled: bool = False,
        checkpoint_dir: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Asynchronously create and initialize an EnhancedMappingExecutor instance.
        
        This factory method creates an enhanced executor with database tables initialized.
        """
        # Create instance with standard constructor
        executor = cls(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=mapping_cache_db_url,
            echo_sql=echo_sql,
            path_cache_size=path_cache_size,
            path_cache_expiry_seconds=path_cache_expiry_seconds,
            max_concurrent_batches=max_concurrent_batches,
            enable_metrics=enable_metrics,
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=checkpoint_dir,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        # Initialize cache database tables
        from biomapper.db.cache_models import Base as CacheBase
        await executor._init_db_tables(executor.async_cache_engine, CacheBase.metadata)
        
        executor.logger.info(
            "EnhancedMappingExecutor instance created with robust features enabled"
        )
        return executor
"""
LifecycleManager - Consolidated lifecycle operations for MappingExecutor.

This service consolidates all lifecycle-related operations from MappingExecutor,
including resource disposal, checkpoint management, and progress reporting.
"""

import logging
from typing import Any, Dict, Optional, List, Callable
from pathlib import Path
from datetime import datetime

from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService
from biomapper.core.engine_components.client_manager import ClientManager

logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    Service that manages lifecycle operations previously handled by MappingExecutor.
    
    This includes:
    - Resource disposal (engines, sessions, clients)
    - Checkpoint directory management
    - Checkpoint save/load operations
    - Progress reporting
    
    The LifecycleManager works alongside the existing ExecutionLifecycleService,
    providing additional lifecycle management capabilities specific to MappingExecutor.
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        execution_lifecycle_service: ExecutionLifecycleService,
        client_manager: Optional[ClientManager] = None
    ):
        """
        Initialize the LifecycleManager.
        
        Args:
            session_manager: Manager for database sessions and engines
            execution_lifecycle_service: Existing lifecycle service for checkpoints/progress
            client_manager: Optional client manager for clearing client caches
        """
        self.session_manager = session_manager
        self.lifecycle_service = execution_lifecycle_service
        self.client_manager = client_manager
        self.logger = logger
        
        # Track checkpoint state
        self._checkpoint_enabled = False
        
        logger.info("LifecycleManager initialized")
    
    # Resource Disposal
    
    async def async_dispose(self) -> None:
        """
        Asynchronously dispose of underlying resources.
        
        This includes database engines and clearing client caches.
        """
        self.logger.info("Disposing of resources via LifecycleManager...")
        
        # Dispose metamapper engine
        if hasattr(self.session_manager, 'async_metamapper_engine') and self.session_manager.async_metamapper_engine:
            await self.session_manager.async_metamapper_engine.dispose()
            self.logger.info("Metamapper engine disposed.")
            
        # Dispose cache engine  
        if hasattr(self.session_manager, 'async_cache_engine') and self.session_manager.async_cache_engine:
            await self.session_manager.async_cache_engine.dispose()
            self.logger.info("Cache engine disposed.")
            
        # Clear client cache
        if self.client_manager:
            self.client_manager.clear_cache()
            self.logger.info("Client cache cleared.")
            
        self.logger.info("Resource disposal complete.")
    
    # Checkpoint Management
    
    @property
    def checkpoint_dir(self) -> Optional[Path]:
        """Get the checkpoint directory path."""
        return self.lifecycle_service.get_checkpoint_directory()
    
    @checkpoint_dir.setter
    def checkpoint_dir(self, value: Optional[str]) -> None:
        """
        Set the checkpoint directory path.
        
        Args:
            value: Path to checkpoint directory or None to disable
        """
        if value is not None:
            checkpoint_path = Path(value)
            self.lifecycle_service.set_checkpoint_directory(checkpoint_path)
            # Ensure directory exists
            checkpoint_path.mkdir(parents=True, exist_ok=True)
            self._checkpoint_enabled = True
            self.logger.info(f"Checkpoint directory set to: {checkpoint_path}")
        else:
            self.lifecycle_service.set_checkpoint_directory(None)
            self._checkpoint_enabled = False
            self.logger.info("Checkpointing disabled")
    
    @property
    def checkpoint_enabled(self) -> bool:
        """Check if checkpointing is enabled."""
        return self._checkpoint_enabled
    
    async def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]) -> None:
        """
        Save checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to checkpoint
        """
        if not self._checkpoint_enabled:
            self.logger.debug(f"Checkpointing disabled, skipping save for {execution_id}")
            return
            
        await self.lifecycle_service.save_checkpoint(execution_id, checkpoint_data)
        self.logger.debug(f"Checkpoint saved for execution {execution_id}")
    
    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        if not self._checkpoint_enabled:
            self.logger.debug(f"Checkpointing disabled, no checkpoint for {execution_id}")
            return None
            
        checkpoint_data = await self.lifecycle_service.load_checkpoint(execution_id)
        if checkpoint_data:
            self.logger.debug(f"Checkpoint loaded for execution {execution_id}")
        else:
            self.logger.debug(f"No checkpoint found for execution {execution_id}")
        
        return checkpoint_data
    
    # Progress Reporting
    
    async def report_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Report progress to registered callbacks and logging.
        
        This method makes the previously private _report_progress method public
        and delegates to the ExecutionLifecycleService.
        
        Args:
            progress_data: Progress information to report
        """
        # Add timestamp if not present
        if 'timestamp' not in progress_data:
            progress_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Log progress at appropriate level
        event_type = progress_data.get('event', progress_data.get('type', 'unknown'))
        if 'error' in progress_data or 'failed' in event_type:
            self.logger.warning(f"Progress: {event_type} - {progress_data}")
        else:
            self.logger.debug(f"Progress: {event_type}")
        
        # Delegate to lifecycle service
        await self.lifecycle_service.report_progress(progress_data)
    
    # Callback Management
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress dict as argument
        """
        self.lifecycle_service.add_progress_callback(callback)
        self.logger.debug(f"Progress callback added: {getattr(callback, '__name__', 'anonymous')}")
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove from callbacks
        """
        self.lifecycle_service.remove_progress_callback(callback)
        self.logger.debug(f"Progress callback removed: {getattr(callback, '__name__', 'anonymous')}")
    
    # Execution Lifecycle
    
    async def start_execution(
        self, 
        execution_id: str, 
        execution_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Signal the start of an execution with type information.
        
        Args:
            execution_id: Unique identifier for the execution
            execution_type: Type of execution (e.g., 'mapping', 'strategy', 'batch')
            metadata: Optional metadata about the execution
        """
        progress_data = {
            'event': 'execution_started',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'metadata': metadata or {}
        }
        await self.report_progress(progress_data)
    
    async def complete_execution(
        self, 
        execution_id: str,
        execution_type: str,
        result_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Signal the completion of an execution with summary.
        
        Args:
            execution_id: Unique identifier for the execution
            execution_type: Type of execution
            result_summary: Optional summary of results
        """
        progress_data = {
            'event': 'execution_completed',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'result_summary': result_summary or {}
        }
        await self.report_progress(progress_data)
    
    async def fail_execution(
        self, 
        execution_id: str,
        execution_type: str,
        error: Exception,
        error_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Signal the failure of an execution with context.
        
        Args:
            execution_id: Unique identifier for the execution
            execution_type: Type of execution
            error: The exception that caused the failure
            error_context: Optional context about the error
        """
        progress_data = {
            'event': 'execution_failed',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'error': str(error),
            'error_type': type(error).__name__,
            'error_context': error_context or {}
        }
        await self.report_progress(progress_data)
    
    # Batch Processing Support
    
    async def report_batch_progress(
        self,
        batch_number: int,
        total_batches: int,
        items_processed: int,
        total_items: int,
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report progress for batch processing operations.
        
        Args:
            batch_number: Current batch number
            total_batches: Total number of batches
            items_processed: Number of items processed so far
            total_items: Total number of items to process
            batch_metadata: Optional metadata about the batch
        """
        await self.lifecycle_service.report_batch_progress(
            batch_number=batch_number,
            total_batches=total_batches,
            items_processed=items_processed,
            total_items=total_items,
            batch_metadata=batch_metadata
        )
    
    async def save_batch_checkpoint(
        self,
        execution_id: str,
        batch_number: int,
        batch_state: Dict[str, Any],
        checkpoint_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save a checkpoint for batch processing.
        
        Args:
            execution_id: Unique identifier for the execution
            batch_number: Current batch number
            batch_state: State to checkpoint
            checkpoint_metadata: Optional metadata about the checkpoint
        """
        if not self._checkpoint_enabled:
            return
            
        await self.lifecycle_service.save_batch_checkpoint(
            execution_id=execution_id,
            batch_number=batch_number,
            batch_state=batch_state,
            checkpoint_metadata=checkpoint_metadata
        )
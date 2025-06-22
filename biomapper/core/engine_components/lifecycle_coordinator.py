"""
LifecycleCoordinator - High-level coordinator for lifecycle operations.

This coordinator replaces the monolithic LifecycleManager by delegating
specific responsibilities to focused services. It maintains backward
compatibility while providing a cleaner separation of concerns.
"""

import logging
from typing import Any, Dict, Optional, Callable
from pathlib import Path

from biomapper.core.services.execution_session_service import ExecutionSessionService
from biomapper.core.services.checkpoint_service import CheckpointService
from biomapper.core.services.resource_disposal_service import ResourceDisposalService

logger = logging.getLogger(__name__)


class LifecycleCoordinator:
    """
    Coordinator that delegates lifecycle operations to specialized services.
    
    This class replaces the original LifecycleManager by composing three
    focused services:
    - ExecutionSessionService: Manages execution lifecycle and progress
    - CheckpointService: Handles checkpoint operations
    - ResourceDisposalService: Manages resource cleanup
    
    It provides the same interface as the original LifecycleManager for
    backward compatibility while delegating actual work to the appropriate
    service.
    """
    
    def __init__(
        self,
        execution_session_service: ExecutionSessionService,
        checkpoint_service: CheckpointService,
        resource_disposal_service: ResourceDisposalService,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the LifecycleCoordinator.
        
        Args:
            execution_session_service: Service for session management
            checkpoint_service: Service for checkpoint operations
            resource_disposal_service: Service for resource disposal
            logger: Optional logger instance
        """
        self.session_service = execution_session_service
        self.checkpoint_service = checkpoint_service
        self.disposal_service = resource_disposal_service
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.info("LifecycleCoordinator initialized")
    
    # Resource Disposal (delegates to ResourceDisposalService)
    
    async def async_dispose(self) -> None:
        """
        Asynchronously dispose of underlying resources.
        
        This includes database engines and clearing client caches.
        """
        await self.disposal_service.dispose_all()
    
    # Checkpoint Management (delegates to CheckpointService)
    
    @property
    def checkpoint_dir(self) -> Optional[Path]:
        """Get the checkpoint directory path."""
        return self.checkpoint_service.checkpoint_directory
    
    @checkpoint_dir.setter
    def checkpoint_dir(self, value: Optional[str]) -> None:
        """
        Set the checkpoint directory path.
        
        Args:
            value: Path to checkpoint directory or None to disable
        """
        self.checkpoint_service.set_checkpoint_directory(value)
    
    @property
    def checkpoint_enabled(self) -> bool:
        """Check if checkpointing is enabled."""
        return self.checkpoint_service.is_enabled
    
    async def save_checkpoint(self, execution_id: str, checkpoint_data: Dict[str, Any]) -> None:
        """
        Save checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to checkpoint
        """
        await self.checkpoint_service.save_checkpoint(execution_id, checkpoint_data)
    
    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        return await self.checkpoint_service.load_checkpoint(execution_id)
    
    # Progress Reporting (delegates to ExecutionSessionService)
    
    async def report_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Report progress to registered callbacks and logging.
        
        Args:
            progress_data: Progress information to report
        """
        await self.session_service.report_progress(progress_data)
    
    # Callback Management (delegates to ExecutionSessionService)
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress dict as argument
        """
        self.session_service.add_progress_callback(callback)
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove from callbacks
        """
        self.session_service.remove_progress_callback(callback)
    
    # Execution Lifecycle (delegates to ExecutionSessionService)
    
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
        await self.session_service.start_session(execution_id, execution_type, metadata)
    
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
            execution_type: Type of execution (ignored - retrieved from session)
            result_summary: Optional summary of results
        """
        await self.session_service.complete_session(execution_id, result_summary)
    
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
            execution_type: Type of execution (ignored - retrieved from session)
            error: The exception that caused the failure
            error_context: Optional context about the error
        """
        await self.session_service.fail_session(execution_id, error, error_context)
    
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
        await self.session_service.report_batch_progress(
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
        await self.checkpoint_service.save_batch_checkpoint(
            execution_id=execution_id,
            batch_number=batch_number,
            batch_state=batch_state,
            checkpoint_metadata=checkpoint_metadata
        )
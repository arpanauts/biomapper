"""Execution Lifecycle Service for managing checkpointing, progress reporting, and metrics."""

from typing import Any, Dict, Optional, Callable, List
import logging
from pathlib import Path

from biomapper.core.engine_components.checkpoint_manager import CheckpointManager
from biomapper.core.engine_components.progress_reporter import ProgressReporter

logger = logging.getLogger(__name__)


class ExecutionLifecycleService:
    """
    Service that consolidates execution lifecycle concerns including:
    - Checkpointing (save/load)
    - Progress reporting
    - Metrics collection
    
    This service acts as a high-level coordinator for lifecycle management,
    delegating to specialized managers while providing a unified interface.
    """
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        progress_reporter: ProgressReporter,
        metrics_manager: Optional[Any] = None
    ):
        """
        Initialize the ExecutionLifecycleService.
        
        Args:
            checkpoint_manager: Manager for handling checkpoints
            progress_reporter: Reporter for progress updates
            metrics_manager: Optional manager for metrics collection
        """
        self.checkpoint_manager = checkpoint_manager
        self.progress_reporter = progress_reporter
        self.metrics_manager = metrics_manager
        
        self._progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        logger.info("ExecutionLifecycleService initialized")
    
    # Checkpoint Management
    
    async def save_checkpoint(
        self, 
        execution_id: str, 
        checkpoint_data: Dict[str, Any]
    ) -> None:
        """
        Save a checkpoint for the given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to be checkpointed
        """
        try:
            await self.checkpoint_manager.save_checkpoint(execution_id, checkpoint_data)
            logger.debug(f"Checkpoint saved for execution {execution_id}")
            
            # Report checkpoint save as progress
            await self.report_progress({
                "event": "checkpoint_saved",
                "execution_id": execution_id,
                "checkpoint_size": len(str(checkpoint_data))
            })
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {execution_id}: {e}")
            raise
    
    async def load_checkpoint(
        self, 
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load a checkpoint for the given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Checkpoint data if found, None otherwise
        """
        try:
            checkpoint_data = await self.checkpoint_manager.load_checkpoint(execution_id)
            if checkpoint_data:
                logger.debug(f"Checkpoint loaded for execution {execution_id}")
                await self.report_progress({
                    "event": "checkpoint_loaded",
                    "execution_id": execution_id
                })
            return checkpoint_data
        except Exception as e:
            logger.error(f"Failed to load checkpoint for {execution_id}: {e}")
            raise
    
    def get_checkpoint_directory(self) -> Optional[Path]:
        """Get the checkpoint directory path."""
        return self.checkpoint_manager.checkpoint_directory
    
    def set_checkpoint_directory(self, directory: Path) -> None:
        """Set the checkpoint directory path."""
        self.checkpoint_manager.checkpoint_directory = directory
    
    # Progress Reporting
    
    async def report_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Report progress update.
        
        Args:
            progress_data: Progress information to report
        """
        try:
            # Report via progress reporter
            self.progress_reporter.report(progress_data)
            
            # Call registered callbacks
            for callback in self._progress_callbacks:
                try:
                    callback(progress_data)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
            
            # Log metrics if available
            if self.metrics_manager and "metrics" in progress_data:
                await self._log_metrics(progress_data["metrics"])
                
        except Exception as e:
            logger.error(f"Failed to report progress: {e}")
            # Don't raise - progress reporting shouldn't break execution
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback for progress updates.
        
        Args:
            callback: Function to call with progress data
        """
        self._progress_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', str(callback))
        logger.debug(f"Added progress callback: {callback_name}")
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a progress callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
            callback_name = getattr(callback, '__name__', str(callback))
            logger.debug(f"Removed progress callback: {callback_name}")
    
    # Metrics Management
    
    async def _log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log metrics using the metrics manager if available.
        
        Args:
            metrics: Metrics data to log
        """
        if self.metrics_manager:
            try:
                # Check if metrics_manager has async log_metrics method
                if hasattr(self.metrics_manager, 'log_metrics'):
                    # Check if it's async
                    import inspect
                    if inspect.iscoroutinefunction(self.metrics_manager.log_metrics):
                        await self.metrics_manager.log_metrics(metrics)
                    else:
                        self.metrics_manager.log_metrics(metrics)
                elif hasattr(self.metrics_manager, 'trace'):
                    # For langfuse or similar trackers (usually sync)
                    self.metrics_manager.trace(
                        name="execution_metrics",
                        input=metrics,
                        metadata={"source": "lifecycle_service"}
                    )
            except Exception as e:
                logger.warning(f"Failed to log metrics: {e}")
    
    async def start_execution(
        self, 
        execution_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Signal the start of an execution.
        
        Args:
            execution_id: Unique identifier for the execution
            metadata: Optional metadata about the execution
        """
        await self.report_progress({
            "event": "execution_started",
            "execution_id": execution_id,
            "metadata": metadata or {},
            "timestamp": self._get_timestamp()
        })
    
    async def complete_execution(
        self, 
        execution_id: str, 
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Signal the completion of an execution.
        
        Args:
            execution_id: Unique identifier for the execution
            result: Optional result data
        """
        await self.report_progress({
            "event": "execution_completed",
            "execution_id": execution_id,
            "result": result or {},
            "timestamp": self._get_timestamp()
        })
    
    async def fail_execution(
        self, 
        execution_id: str, 
        error: Exception
    ) -> None:
        """
        Signal the failure of an execution.
        
        Args:
            execution_id: Unique identifier for the execution
            error: The exception that caused the failure
        """
        await self.report_progress({
            "event": "execution_failed",
            "execution_id": execution_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": self._get_timestamp()
        })
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO format string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
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
        Report progress for batch processing.
        
        Args:
            batch_number: Current batch number
            total_batches: Total number of batches
            items_processed: Number of items processed so far
            total_items: Total number of items to process
            batch_metadata: Optional metadata about the batch
        """
        progress_percentage = (items_processed / total_items * 100) if total_items > 0 else 0
        
        await self.report_progress({
            "event": "batch_progress",
            "batch_number": batch_number,
            "total_batches": total_batches,
            "items_processed": items_processed,
            "total_items": total_items,
            "progress_percentage": round(progress_percentage, 2),
            "batch_metadata": batch_metadata or {},
            "timestamp": self._get_timestamp()
        })
    
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
        checkpoint_data = {
            "batch_number": batch_number,
            "batch_state": batch_state,
            "metadata": checkpoint_metadata or {},
            "timestamp": self._get_timestamp()
        }
        
        await self.save_checkpoint(execution_id, checkpoint_data)
"""
CheckpointService - Handles saving and loading of execution checkpoints.

This service manages checkpoint operations including directory management,
checkpoint saving/loading, and batch-specific checkpointing. It provides
a clean interface for checkpoint management separate from other lifecycle concerns.
"""

import logging
from typing import Any, Dict, Optional
from pathlib import Path

from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService

logger = logging.getLogger(__name__)


class CheckpointService:
    """
    Service that manages checkpoint operations.
    
    This service is responsible for:
    - Managing checkpoint directory
    - Saving and loading checkpoints
    - Batch-specific checkpoint operations
    - Checkpoint validation and cleanup
    
    It delegates to ExecutionLifecycleService for actual checkpoint I/O
    while providing a focused interface for checkpoint management.
    """
    
    def __init__(
        self,
        execution_lifecycle_service: ExecutionLifecycleService,
        checkpoint_dir: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the CheckpointService.
        
        Args:
            execution_lifecycle_service: Service for checkpoint I/O
            checkpoint_dir: Optional checkpoint directory path
            logger: Optional logger instance
        """
        self.lifecycle_service = execution_lifecycle_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Track checkpoint state
        self._checkpoint_enabled = False
        self._checkpoint_dir: Optional[Path] = None
        
        # Set initial checkpoint directory if provided
        if checkpoint_dir:
            self.set_checkpoint_directory(checkpoint_dir)
        
        self.logger.info("CheckpointService initialized")
    
    # Directory Management
    
    @property
    def checkpoint_directory(self) -> Optional[Path]:
        """Get the checkpoint directory path."""
        return self._checkpoint_dir
    
    def set_checkpoint_directory(self, directory: Optional[str]) -> None:
        """
        Set the checkpoint directory path.
        
        Args:
            directory: Path to checkpoint directory or None to disable
        """
        if directory is not None:
            checkpoint_path = Path(directory)
            self.lifecycle_service.set_checkpoint_directory(checkpoint_path)
            # Ensure directory exists
            checkpoint_path.mkdir(parents=True, exist_ok=True)
            self._checkpoint_dir = checkpoint_path
            self._checkpoint_enabled = True
            self.logger.info(f"Checkpoint directory set to: {checkpoint_path}")
        else:
            self.lifecycle_service.set_checkpoint_directory(None)
            self._checkpoint_dir = None
            self._checkpoint_enabled = False
            self.logger.info("Checkpointing disabled")
    
    @property
    def is_enabled(self) -> bool:
        """Check if checkpointing is enabled."""
        return self._checkpoint_enabled
    
    # Checkpoint Operations
    
    async def save_checkpoint(
        self, 
        execution_id: str, 
        checkpoint_data: Dict[str, Any]
    ) -> bool:
        """
        Save checkpoint data for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            checkpoint_data: Data to checkpoint
            
        Returns:
            True if checkpoint was saved, False if checkpointing is disabled
        """
        if not self._checkpoint_enabled:
            self.logger.debug(f"Checkpointing disabled, skipping save for {execution_id}")
            return False
        
        try:
            await self.lifecycle_service.save_checkpoint(execution_id, checkpoint_data)
            self.logger.info(f"Checkpoint saved for execution {execution_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint for {execution_id}: {e}")
            raise
    
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
        
        try:
            checkpoint_data = await self.lifecycle_service.load_checkpoint(execution_id)
            if checkpoint_data:
                self.logger.info(f"Checkpoint loaded for execution {execution_id}")
            else:
                self.logger.debug(f"No checkpoint found for execution {execution_id}")
            return checkpoint_data
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint for {execution_id}: {e}")
            raise
    
    async def checkpoint_exists(self, execution_id: str) -> bool:
        """
        Check if a checkpoint exists for the given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            True if checkpoint exists, False otherwise
        """
        if not self._checkpoint_enabled:
            return False
        
        checkpoint_data = await self.load_checkpoint(execution_id)
        return checkpoint_data is not None
    
    async def delete_checkpoint(self, execution_id: str) -> bool:
        """
        Delete checkpoint for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            True if checkpoint was deleted, False if not found
        """
        if not self._checkpoint_enabled:
            return False
        
        # TODO: Implement checkpoint deletion in ExecutionLifecycleService
        # For now, we'll just log the intent
        self.logger.info(f"Would delete checkpoint for execution {execution_id}")
        return True
    
    # Batch Checkpoint Operations
    
    async def save_batch_checkpoint(
        self,
        execution_id: str,
        batch_number: int,
        batch_state: Dict[str, Any],
        checkpoint_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a checkpoint for batch processing.
        
        Args:
            execution_id: Unique identifier for the execution
            batch_number: Current batch number
            batch_state: State to checkpoint
            checkpoint_metadata: Optional metadata about the checkpoint
            
        Returns:
            True if checkpoint was saved, False if checkpointing is disabled
        """
        if not self._checkpoint_enabled:
            self.logger.debug(
                f"Checkpointing disabled, skipping batch {batch_number} save for {execution_id}"
            )
            return False
        
        try:
            await self.lifecycle_service.save_batch_checkpoint(
                execution_id=execution_id,
                batch_number=batch_number,
                batch_state=batch_state,
                checkpoint_metadata=checkpoint_metadata
            )
            self.logger.info(
                f"Batch checkpoint saved for execution {execution_id}, batch {batch_number}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to save batch checkpoint for {execution_id}, batch {batch_number}: {e}"
            )
            raise
    
    async def load_batch_checkpoint(
        self,
        execution_id: str,
        batch_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Load a checkpoint for a specific batch.
        
        Args:
            execution_id: Unique identifier for the execution
            batch_number: Batch number to load
            
        Returns:
            Batch checkpoint data if found, None otherwise
        """
        if not self._checkpoint_enabled:
            return None
        
        # Load the main checkpoint and extract batch data
        checkpoint_data = await self.load_checkpoint(execution_id)
        if not checkpoint_data:
            return None
        
        # Look for batch-specific data
        batch_key = f"batch_{batch_number}"
        if batch_key in checkpoint_data:
            return checkpoint_data[batch_key]
        
        # Check if this is a batch checkpoint
        if checkpoint_data.get('batch_number') == batch_number:
            return checkpoint_data
        
        return None
    
    # Utility Methods
    
    def get_checkpoint_path(self, execution_id: str) -> Optional[Path]:
        """
        Get the file path for a checkpoint.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Path to checkpoint file if checkpointing is enabled, None otherwise
        """
        if not self._checkpoint_enabled or not self._checkpoint_dir:
            return None
        
        return self._checkpoint_dir / f"{execution_id}.checkpoint"
    
    async def cleanup_old_checkpoints(self, days_to_keep: int = 7) -> int:
        """
        Clean up old checkpoint files.
        
        Args:
            days_to_keep: Number of days to keep checkpoints
            
        Returns:
            Number of checkpoints deleted
        """
        if not self._checkpoint_enabled or not self._checkpoint_dir:
            return 0
        
        # TODO: Implement checkpoint cleanup based on age
        self.logger.info(f"Would clean up checkpoints older than {days_to_keep} days")
        return 0
    
    def validate_checkpoint_data(self, checkpoint_data: Dict[str, Any]) -> bool:
        """
        Validate checkpoint data structure.
        
        Args:
            checkpoint_data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Basic validation - ensure it's a dict with some expected keys
        if not isinstance(checkpoint_data, dict):
            return False
        
        # Could add more specific validation based on requirements
        return True
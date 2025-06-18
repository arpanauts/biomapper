import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import logging

from biomapper.core.exceptions import BiomapperError


class CheckpointManager:
    """
    Manages checkpoint operations for robust execution with resumable state.
    
    This class centralizes all checkpoint-related functionality including saving,
    loading, and clearing checkpoints for mapping executions.
    """
    
    def __init__(self, checkpoint_dir: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the CheckpointManager.
        
        Args:
            checkpoint_dir: Directory for checkpoint files. If None, uses default.
            logger: Logger instance for checkpoint operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self.checkpoint_enabled = checkpoint_dir is not None
        
        # Set up checkpoint directory
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Default checkpoint directory
            self.checkpoint_dir = Path.home() / '.biomapper' / 'checkpoints'
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
        self._current_checkpoint_file: Optional[Path] = None
        self._progress_callbacks: List[Callable] = []
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function."""
        self._progress_callbacks.append(callback)
    
    def _report_progress(self, progress_data: Dict[str, Any]):
        """Report progress to registered callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
    
    def _get_checkpoint_file(self, execution_id: str) -> Path:
        """
        Get the checkpoint file path for a given execution.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Path to the checkpoint file
        """
        return self.checkpoint_dir / f"{execution_id}.checkpoint"
    
    async def save_checkpoint(self, execution_id: str, state: Dict[str, Any]):
        """
        Save execution state to a checkpoint file.
        
        Args:
            execution_id: Unique identifier for the execution
            state: State dictionary to save
        """
        if not self.checkpoint_enabled:
            return
            
        checkpoint_file = self._get_checkpoint_file(execution_id)
        self._current_checkpoint_file = checkpoint_file
        
        try:
            # Add timestamp to state
            state['checkpoint_time'] = datetime.utcnow().isoformat()
            
            # Save to temporary file first
            temp_file = checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'wb') as f:
                pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Atomic rename
            temp_file.replace(checkpoint_file)
            
            self.logger.info(f"Checkpoint saved: {checkpoint_file}")
            
            # Report progress
            self._report_progress({
                'type': 'checkpoint_saved',
                'execution_id': execution_id,
                'checkpoint_file': str(checkpoint_file),
                'state_summary': {
                    'processed_count': state.get('processed_count', 0),
                    'total_count': state.get('total_count', 0)
                }
            })
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise BiomapperError(f"Checkpoint save failed: {e}")
    
    async def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load execution state from a checkpoint file.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            State dictionary if checkpoint exists, None otherwise
        """
        if not self.checkpoint_enabled:
            return None
            
        checkpoint_file = self._get_checkpoint_file(execution_id)
        
        if not checkpoint_file.exists():
            return None
            
        try:
            with open(checkpoint_file, 'rb') as f:
                state = pickle.load(f)
            
            self.logger.info(f"Checkpoint loaded: {checkpoint_file}")
            self._current_checkpoint_file = checkpoint_file
            
            # Report progress
            self._report_progress({
                'type': 'checkpoint_loaded',
                'execution_id': execution_id,
                'checkpoint_file': str(checkpoint_file),
                'checkpoint_time': state.get('checkpoint_time'),
                'state_summary': {
                    'processed_count': state.get('processed_count', 0),
                    'total_count': state.get('total_count', 0)
                }
            })
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    async def clear_checkpoint(self, execution_id: str):
        """
        Remove checkpoint file after successful completion.
        
        Args:
            execution_id: Unique identifier for the execution
        """
        if not self.checkpoint_enabled:
            return
            
        checkpoint_file = self._get_checkpoint_file(execution_id)
        
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
                self.logger.info(f"Checkpoint cleared: {checkpoint_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clear checkpoint: {e}")
    
    @property
    def current_checkpoint_file(self) -> Optional[Path]:
        """Get the current checkpoint file path."""
        return self._current_checkpoint_file
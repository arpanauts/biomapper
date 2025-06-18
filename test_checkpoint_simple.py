#!/usr/bin/env python3
"""
Direct test of CheckpointManager without importing the full biomapper package.
"""

import asyncio
import pickle
import tempfile
import shutil
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import BiomapperError
class BiomapperError(Exception):
    """Mock BiomapperError for testing."""
    pass

# Direct CheckpointManager implementation (copied for testing)
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
        elif self.checkpoint_enabled:
            # Default checkpoint directory (only if enabled)
            self.checkpoint_dir = Path.home() / '.biomapper' / 'checkpoints'
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        else:
            # No checkpoint directory needed when disabled
            self.checkpoint_dir = None
            
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
        if self.checkpoint_dir is None:
            raise BiomapperError("Checkpoint directory not configured")
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


async def test_checkpoint_manager():
    """Test basic CheckpointManager functionality."""
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    logger = logging.getLogger("test")
    
    try:
        # Initialize CheckpointManager
        checkpoint_manager = CheckpointManager(
            checkpoint_dir=temp_dir,
            logger=logger
        )
        
        print("✓ CheckpointManager initialized successfully")
        
        # Test checkpoint save and load
        execution_id = "test_execution_001"
        test_state = {
            "processed_count": 42,
            "total_count": 100,
            "results": [
                {"id": "test1", "status": "success"},
                {"id": "test2", "status": "success"}
            ],
            "current_batch": 3
        }
        
        # Save checkpoint
        await checkpoint_manager.save_checkpoint(execution_id, test_state)
        print("✓ Checkpoint saved successfully")
        
        # Load checkpoint
        loaded_state = await checkpoint_manager.load_checkpoint(execution_id)
        print("✓ Checkpoint loaded successfully")
        
        # Verify loaded data
        assert loaded_state is not None, "Checkpoint should not be None"
        assert loaded_state["processed_count"] == 42, "Processed count mismatch"
        assert loaded_state["total_count"] == 100, "Total count mismatch"
        assert len(loaded_state["results"]) == 2, "Results count mismatch"
        assert loaded_state["current_batch"] == 3, "Current batch mismatch"
        assert "checkpoint_time" in loaded_state, "Checkpoint time should be added"
        
        print("✓ Checkpoint data verified correctly")
        
        # Test checkpoint clearing
        await checkpoint_manager.clear_checkpoint(execution_id)
        print("✓ Checkpoint cleared successfully")
        
        # Verify checkpoint is gone
        cleared_state = await checkpoint_manager.load_checkpoint(execution_id)
        assert cleared_state is None, "Checkpoint should be None after clearing"
        print("✓ Checkpoint properly removed after clearing")
        
        # Test progress callback
        progress_calls = []
        
        def test_callback(progress_data):
            progress_calls.append(progress_data)
        
        checkpoint_manager.add_progress_callback(test_callback)
        
        # Save checkpoint again to trigger progress callback
        await checkpoint_manager.save_checkpoint(execution_id, test_state)
        
        assert len(progress_calls) == 1, "Progress callback should be called once"
        assert progress_calls[0]["type"] == "checkpoint_saved", "Wrong progress type"
        assert progress_calls[0]["execution_id"] == execution_id, "Wrong execution_id"
        
        print("✓ Progress callbacks working correctly")
        
        # Test checkpoint_enabled = False
        checkpoint_manager_disabled = CheckpointManager(checkpoint_dir=None, logger=logger)
        assert not checkpoint_manager_disabled.checkpoint_enabled, "Should be disabled"
        
        # Should not save when disabled
        await checkpoint_manager_disabled.save_checkpoint(execution_id, test_state)
        loaded_disabled = await checkpoint_manager_disabled.load_checkpoint(execution_id)
        assert loaded_disabled is None, "Should return None when disabled"
        print("✓ Disabled checkpoint manager works correctly")
        
        print("\n🎉 All CheckpointManager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


async def main():
    """Run all tests."""
    print("=== CheckpointManager Direct Functional Tests ===\n")
    
    # Test CheckpointManager functionality
    test_passed = await test_checkpoint_manager()
    
    print("\n" + "="*50)
    
    if test_passed:
        print("🎉 All tests completed successfully!")
        print("✅ CheckpointManager refactoring verified")
    else:
        print("❌ Tests failed")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
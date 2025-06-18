"""
Robust execution extensions for MappingExecutor.

This module provides checkpointing, retry logic, and progress tracking
capabilities that can be mixed into the main MappingExecutor class.
"""

import asyncio
import pickle
import os
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from datetime import datetime
from pathlib import Path
import logging

from biomapper.core.exceptions import BiomapperError, MappingExecutionError


class RobustExecutionMixin:
    """
    Mixin class that adds robust execution capabilities to MappingExecutor.
    
    Features:
    - Checkpointing for resumable execution
    - Retry logic for failed operations
    - Progress tracking and reporting
    - Batch processing with configurable sizes
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize robust execution features."""
        # Extract robust-specific parameters
        self.checkpoint_enabled = kwargs.pop('checkpoint_enabled', False)
        self.checkpoint_dir = kwargs.pop('checkpoint_dir', None)
        self.batch_size = kwargs.pop('batch_size', 100)
        self.max_retries = kwargs.pop('max_retries', 3)
        self.retry_delay = kwargs.pop('retry_delay', 5)  # seconds
        
        # Initialize parent class
        super().__init__(*args, **kwargs)
        
        # Set up checkpoint directory
        if self.checkpoint_enabled and self.checkpoint_dir:
            self.checkpoint_dir = Path(self.checkpoint_dir)
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        elif self.checkpoint_enabled:
            # Default checkpoint directory
            self.checkpoint_dir = Path.home() / '.biomapper' / 'checkpoints'
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
        # Progress tracking
        self._progress_callbacks: List[Callable] = []
        self._current_checkpoint_file: Optional[Path] = None
        
        # Logger (assumes parent class has this)
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(__name__)
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress dict as argument
        """
        self._progress_callbacks.append(callback)
    
    def _report_progress(self, progress_data: Dict[str, Any]):
        """
        Report progress to all registered callbacks.
        
        Args:
            progress_data: Dictionary containing progress information
        """
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
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_args: Dict[str, Any],
        operation_name: str,
        retry_exceptions: Tuple[type, ...] = (Exception,)
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Async callable to execute
            operation_args: Arguments to pass to the operation
            operation_name: Name for logging purposes
            retry_exceptions: Tuple of exception types to retry on
            
        Returns:
            Result of the operation
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Report attempt
                self._report_progress({
                    'type': 'retry_attempt',
                    'operation': operation_name,
                    'attempt': attempt + 1,
                    'max_attempts': self.max_retries
                })
                
                # Execute operation
                result = await operation(**operation_args)
                
                # Success - report and return
                if attempt > 0:
                    self.logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
                    
                return result
                
            except retry_exceptions as e:
                last_error = e
                self.logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay)
                    
        # All retries exhausted
        error_msg = f"{operation_name} failed after {self.max_retries} attempts"
        self.logger.error(f"{error_msg}: {last_error}")
        
        # Report failure
        self._report_progress({
            'type': 'retry_exhausted',
            'operation': operation_name,
            'attempts': self.max_retries,
            'last_error': str(last_error)
        })
        
        raise MappingExecutionError(
            error_msg,
            details={
                'operation': operation_name,
                'attempts': self.max_retries,
                'last_error': str(last_error)
            }
        )
    
    async def process_in_batches(
        self,
        items: List[Any],
        processor: Callable,
        processor_name: str,
        checkpoint_key: str,
        execution_id: str,
        checkpoint_state: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Process items in batches with checkpointing.
        
        Args:
            items: List of items to process
            processor: Async callable that processes a batch
            processor_name: Name for logging purposes
            checkpoint_key: Key to store results in checkpoint
            execution_id: Unique identifier for checkpointing
            checkpoint_state: Existing checkpoint state to resume from
            
        Returns:
            List of all results
        """
        # Initialize or restore state
        if checkpoint_state and checkpoint_key in checkpoint_state:
            results = checkpoint_state[checkpoint_key]
            processed_count = checkpoint_state.get('processed_count', 0)
            remaining_items = items[processed_count:]
            self.logger.info(
                f"Resuming {processor_name} from checkpoint: "
                f"{processed_count}/{len(items)} already processed"
            )
        else:
            results = []
            processed_count = 0
            remaining_items = items
            
        total_count = len(items)
        
        # Process in batches
        for i in range(0, len(remaining_items), self.batch_size):
            batch = remaining_items[i:i + self.batch_size]
            batch_num = (processed_count + i) // self.batch_size + 1
            total_batches = (total_count + self.batch_size - 1) // self.batch_size
            
            self.logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} items) for {processor_name}"
            )
            
            # Report batch start
            self._report_progress({
                'type': 'batch_start',
                'processor': processor_name,
                'batch_num': batch_num,
                'total_batches': total_batches,
                'batch_size': len(batch),
                'total_processed': processed_count + i,
                'total_count': total_count
            })
            
            try:
                # Process batch with retry
                batch_results = await self.execute_with_retry(
                    operation=processor,
                    operation_args={'batch': batch},
                    operation_name=f"{processor_name}_batch_{batch_num}",
                    retry_exceptions=(asyncio.TimeoutError, Exception)
                )
                
                # Append results
                results.extend(batch_results)
                
                # Update processed count
                current_processed = processed_count + i + len(batch)
                
                # Save checkpoint
                if self.checkpoint_enabled:
                    checkpoint_data = {
                        checkpoint_key: results,
                        'processed_count': current_processed,
                        'total_count': total_count,
                        'processor': processor_name
                    }
                    
                    # Preserve other checkpoint data
                    if checkpoint_state:
                        for key, value in checkpoint_state.items():
                            if key not in checkpoint_data:
                                checkpoint_data[key] = value
                                
                    await self.save_checkpoint(execution_id, checkpoint_data)
                
                # Report batch completion
                self._report_progress({
                    'type': 'batch_complete',
                    'processor': processor_name,
                    'batch_num': batch_num,
                    'total_batches': total_batches,
                    'batch_results': len(batch_results),
                    'total_processed': current_processed,
                    'total_count': total_count,
                    'progress_percent': (current_processed / total_count * 100)
                })
                
            except Exception as e:
                self.logger.error(
                    f"Batch {batch_num} failed for {processor_name}: {e}"
                )
                
                # Report batch failure
                self._report_progress({
                    'type': 'batch_failed',
                    'processor': processor_name,
                    'batch_num': batch_num,
                    'total_batches': total_batches,
                    'error': str(e)
                })
                
                # Re-raise to trigger retry or abort
                raise
                
        return results
    
    async def execute_yaml_strategy_robust(
        self,
        strategy_name: str,
        input_identifiers: List[str],
        source_endpoint_name: Optional[str] = None,
        target_endpoint_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        resume_from_checkpoint: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a YAML strategy with robust error handling and checkpointing.
        
        This wraps the standard execute_yaml_strategy method with additional
        robustness features.
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of input identifiers
            source_endpoint_name: Source endpoint name (optional, can be auto-detected)
            target_endpoint_name: Target endpoint name (optional, can be auto-detected)
            execution_id: Unique ID for this execution (for checkpointing)
            resume_from_checkpoint: Whether to resume from checkpoint if available
            **kwargs: Additional arguments to pass to execute_yaml_strategy
            
        Returns:
            Strategy execution results with additional robustness metadata
        """
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = f"{strategy_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
        # Try to load checkpoint
        checkpoint_state = None
        if resume_from_checkpoint:
            checkpoint_state = await self.load_checkpoint(execution_id)
            
        start_time = datetime.utcnow()
        
        try:
            # If we have a checkpoint, extract the current state
            if checkpoint_state:
                # This would need to be implemented based on how strategies track state
                # For now, we'll just pass through to the standard method
                self.logger.info(f"Checkpoint found but strategy resumption not yet implemented")
            
            # Build arguments for the strategy execution
            strategy_args = {
                'strategy_name': strategy_name,
                'input_identifiers': input_identifiers,
                **kwargs
            }
            
            # Add endpoint names if provided
            if source_endpoint_name:
                strategy_args['source_endpoint_name'] = source_endpoint_name
            if target_endpoint_name:
                strategy_args['target_endpoint_name'] = target_endpoint_name
            
            # Execute the strategy
            # This assumes the parent class has execute_yaml_strategy method
            result = await self.execute_yaml_strategy(**strategy_args)
            
            # Add robustness metadata
            result['robust_execution'] = {
                'execution_id': execution_id,
                'checkpointing_enabled': self.checkpoint_enabled,
                'checkpoint_used': checkpoint_state is not None,
                'execution_time': (datetime.utcnow() - start_time).total_seconds(),
                'retries_configured': self.max_retries,
                'batch_size': self.batch_size
            }
            
            # Clear checkpoint on success
            if self.checkpoint_enabled:
                await self.clear_checkpoint(execution_id)
                
            return result
            
        except Exception as e:
            # Report execution failure
            self._report_progress({
                'type': 'execution_failed',
                'execution_id': execution_id,
                'strategy': strategy_name,
                'error': str(e),
                'checkpoint_available': self._current_checkpoint_file is not None
            })
            
            # Re-raise with additional context
            raise MappingExecutionError(
                f"Strategy execution failed: {strategy_name}",
                details={
                    'execution_id': execution_id,
                    'checkpoint_available': self._current_checkpoint_file is not None,
                    'error': str(e)
                }
            )
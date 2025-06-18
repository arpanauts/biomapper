"""
Robust Execution Coordinator for BiomMappers.

This module provides the RobustExecutionCoordinator class that handles
the high-level execution lifecycle management including robustness features
like checkpointing and retries.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from biomapper.core.exceptions import MappingExecutionError


class RobustExecutionCoordinator:
    """
    Coordinates robust execution of mapping strategies with checkpointing and retry capabilities.
    
    This class separates high-level execution lifecycle management from core strategy orchestration,
    providing features like checkpoint loading/saving, retry mechanisms, and execution tracking.
    """
    
    def __init__(
        self,
        strategy_orchestrator,
        checkpoint_manager,
        progress_reporter,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
        checkpoint_enabled: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the RobustExecutionCoordinator.
        
        Args:
            strategy_orchestrator: The StrategyOrchestrator instance for executing strategies
            checkpoint_manager: The CheckpointManager instance for handling checkpoints
            progress_reporter: The ProgressReporter instance for reporting execution status
            batch_size: Number of items to process per batch
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay in seconds between retry attempts
            checkpoint_enabled: Whether checkpointing is enabled
            logger: Logger instance for logging
        """
        self.strategy_orchestrator = strategy_orchestrator
        self.checkpoint_manager = checkpoint_manager
        self.progress_reporter = progress_reporter
        
        # Configuration
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.checkpoint_enabled = checkpoint_enabled
        
        # Logger
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute_strategy_robustly(
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
        Execute a strategy with robust error handling and checkpointing.
        
        This method wraps the standard strategy execution with additional
        robustness features including checkpoint loading/saving and error handling.
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of input identifiers
            source_endpoint_name: Source endpoint name (optional, can be auto-detected)
            target_endpoint_name: Target endpoint name (optional, can be auto-detected)
            execution_id: Unique ID for this execution (for checkpointing)
            resume_from_checkpoint: Whether to resume from checkpoint if available
            **kwargs: Additional arguments to pass to strategy execution
            
        Returns:
            Strategy execution results with additional robustness metadata
        """
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = f"{strategy_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
        self.logger.info(f"Starting robust execution of strategy '{strategy_name}' with ID: {execution_id}")
        
        # Try to load checkpoint
        checkpoint_state = None
        if resume_from_checkpoint and self.checkpoint_enabled:
            checkpoint_state = await self.checkpoint_manager.load_checkpoint(execution_id)
            if checkpoint_state:
                self.logger.info(f"Loaded checkpoint for execution ID: {execution_id}")
            
        start_time = datetime.utcnow()
        
        # Report execution start
        self.progress_reporter.report({
            'type': 'execution_started',
            'execution_id': execution_id,
            'strategy': strategy_name,
            'input_count': len(input_identifiers),
            'checkpoint_resumed': checkpoint_state is not None
        })
        
        try:
            # If we have a checkpoint, extract the current state
            if checkpoint_state:
                # This would need to be implemented based on how strategies track state
                # For now, we'll just pass through to the standard method
                self.logger.info(f"Checkpoint found but strategy resumption not yet fully implemented")
            
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
            
            # Execute the strategy via the orchestrator
            result = await self.strategy_orchestrator.execute_strategy(**strategy_args)
            
            # Add robustness metadata
            result['robust_execution'] = {
                'execution_id': execution_id,
                'checkpointing_enabled': self.checkpoint_enabled,
                'checkpoint_used': checkpoint_state is not None,
                'execution_time': (datetime.utcnow() - start_time).total_seconds(),
                'retries_configured': self.max_retries,
                'batch_size': self.batch_size
            }
            
            # Report execution success
            self.progress_reporter.report({
                'type': 'execution_completed',
                'execution_id': execution_id,
                'strategy': strategy_name,
                'execution_time': result['robust_execution']['execution_time'],
                'results_count': len(result.get('results', []))
            })
            
            # Clear checkpoint on success
            if self.checkpoint_enabled:
                await self.checkpoint_manager.clear_checkpoint(execution_id)
                
            self.logger.info(f"Successfully completed execution of strategy '{strategy_name}' with ID: {execution_id}")
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Report execution failure
            self.progress_reporter.report({
                'type': 'execution_failed',
                'execution_id': execution_id,
                'strategy': strategy_name,
                'error': str(e),
                'execution_time': execution_time,
                'checkpoint_available': self.checkpoint_manager.current_checkpoint_file is not None if hasattr(self.checkpoint_manager, 'current_checkpoint_file') else False
            })
            
            self.logger.error(f"Execution failed for strategy '{strategy_name}' with ID: {execution_id}: {str(e)}")
            
            # Re-raise with additional context
            raise MappingExecutionError(
                f"Strategy execution failed: {strategy_name}",
                details={
                    'execution_id': execution_id,
                    'checkpoint_available': self.checkpoint_manager.current_checkpoint_file is not None if hasattr(self.checkpoint_manager, 'current_checkpoint_file') else False,
                    'error': str(e),
                    'execution_time': execution_time
                }
            )
            
    async def execute_with_retry(
        self,
        strategy_name: str,
        input_identifiers: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a strategy with retry logic.
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of input identifiers
            **kwargs: Additional arguments to pass to strategy execution
            
        Returns:
            Strategy execution results
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                return await self.execute_strategy_robustly(
                    strategy_name=strategy_name,
                    input_identifiers=input_identifiers,
                    **kwargs
                )
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for strategy '{strategy_name}': {str(e)}. "
                        f"Retrying in {self.retry_delay} seconds..."
                    )
                    
                    # Report retry
                    self.progress_reporter.report({
                        'type': 'execution_retry',
                        'strategy': strategy_name,
                        'attempt': attempt + 1,
                        'max_retries': self.max_retries,
                        'error': str(e),
                        'retry_delay': self.retry_delay
                    })
                    
                    # Wait before retry
                    import asyncio
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed for strategy '{strategy_name}'"
                    )
        
        # If we get here, all retries failed
        raise MappingExecutionError(
            f"Strategy execution failed after {self.max_retries + 1} attempts: {strategy_name}",
            details={
                'attempts': self.max_retries + 1,
                'final_error': str(last_exception)
            }
        )
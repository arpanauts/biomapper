"""
StrategyExecutionService - Handles YAML strategy execution logic.

This service encapsulates the logic for executing YAML-defined mapping strategies,
including both standard execution and robust execution with checkpointing.
"""

import logging
from typing import List, Dict, Any, Optional, Callable

from biomapper.core.exceptions import ConfigurationError, MappingExecutionError


class StrategyExecutionService:
    """
    Service responsible for executing YAML-defined mapping strategies.
    
    This service provides a clean interface for strategy execution while delegating
    the actual work to the StrategyOrchestrator and RobustExecutionCoordinator.
    """
    
    def __init__(
        self,
        strategy_orchestrator,
        robust_execution_coordinator,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the StrategyExecutionService.
        
        Args:
            strategy_orchestrator: The orchestrator for executing strategies
            robust_execution_coordinator: Coordinator for robust execution with checkpointing
            logger: Optional logger instance
        """
        self.strategy_orchestrator = strategy_orchestrator
        self.robust_execution_coordinator = robust_execution_coordinator
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        batch_size: int = 250,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Execute a YAML-defined mapping strategy using dedicated strategy action classes.
        
        This method executes a multi-step mapping strategy defined in YAML configuration.
        Each step in the strategy is executed sequentially using dedicated action classes
        (ConvertIdentifiersLocalAction, ExecuteMappingPathAction, FilterByTargetPresenceAction),
        with the output of one step becoming the input for the next. The `is_required` field 
        on each step controls whether step failures halt execution or allow it to continue.
        
        Args:
            strategy_name: Name of the strategy defined in YAML configuration
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            input_identifiers: List of identifiers to map
            source_ontology_type: Optional override for source ontology type
            target_ontology_type: Optional override for target ontology type
            use_cache: Whether to use caching (default: True)
            max_cache_age_days: Maximum cache age in days
            progress_callback: Optional callback function(current_step, total_steps, status)
            batch_size: Size of batches for processing (default: 250)
            min_confidence: Minimum confidence threshold (default: 0.0)
            
        Returns:
            Dict[str, Any]: A MappingResultBundle-structured dictionary containing:
                - 'results': Dict[str, Dict] mapping source IDs to their mapped values
                - 'metadata': Dict with execution metadata including step-by-step provenance
                - 'step_results': List[Dict] with detailed results from each step
                - 'statistics': Dict with mapping statistics
                - 'final_identifiers': List of identifiers after all steps
                - 'final_ontology_type': Final ontology type after all conversions
                
        Raises:
            ConfigurationError: If the strategy doesn't exist, is inactive, has no steps,
                               or if source/target endpoints are not found
            MappingExecutionError: If a required step fails during execution
            
        Example:
            >>> service = StrategyExecutionService(orchestrator, coordinator)
            >>> result = await service.execute_strategy(
            ...     strategy_name="ukbb_to_hpa_protein",
            ...     source_endpoint_name="UKBB",
            ...     target_endpoint_name="HPA",
            ...     input_identifiers=["ADAMTS13", "ALB"],
            ...     use_cache=True
            ... )
            >>> print(f"Final identifiers: {result['final_identifiers']}")
            >>> print(f"Step results: {len(result['step_results'])}")
        """
        self.logger.info(
            f"Executing YAML strategy '{strategy_name}' from {source_endpoint_name} to {target_endpoint_name} "
            f"with {len(input_identifiers)} input identifiers"
        )
        
        try:
            # Delegate to StrategyOrchestrator
            result = await self.strategy_orchestrator.execute_strategy(
                strategy_name=strategy_name,
                input_identifiers=input_identifiers,
                source_endpoint_name=source_endpoint_name,
                target_endpoint_name=target_endpoint_name,
                source_ontology_type=source_ontology_type,
                target_ontology_type=target_ontology_type,
                use_cache=use_cache,
                max_cache_age_days=max_cache_age_days,
                progress_callback=progress_callback,
                batch_size=batch_size,
                min_confidence=min_confidence,
            )
            
            self.logger.info(
                f"YAML strategy '{strategy_name}' completed successfully. "
                f"Processed {len(input_identifiers)} input identifiers, "
                f"produced {len(result.get('final_identifiers', []))} final identifiers"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing YAML strategy '{strategy_name}': {str(e)}")
            raise
            
    async def execute_strategy_robust(
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
        
        This wraps the standard strategy execution with additional robustness features
        via the RobustExecutionCoordinator, including:
        - Automatic checkpointing and resume capabilities
        - Enhanced error handling and retry logic
        - Progress tracking and reporting
        - Batch processing with failure isolation
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of input identifiers
            source_endpoint_name: Source endpoint name (optional, can be auto-detected)
            target_endpoint_name: Target endpoint name (optional, can be auto-detected)
            execution_id: Unique ID for this execution (for checkpointing)
            resume_from_checkpoint: Whether to resume from checkpoint if available
            **kwargs: Additional arguments to pass to execute_strategy
            
        Returns:
            Strategy execution results with additional robustness metadata including:
                - Standard strategy execution results
                - Checkpoint information
                - Retry statistics
                - Failure analysis
        """
        self.logger.info(
            f"Executing YAML strategy '{strategy_name}' with robust handling. "
            f"Input identifiers: {len(input_identifiers)}, "
            f"Execution ID: {execution_id}, "
            f"Resume from checkpoint: {resume_from_checkpoint}"
        )
        
        try:
            # Delegate to the RobustExecutionCoordinator
            result = await self.robust_execution_coordinator.execute_strategy_robustly(
                strategy_name=strategy_name,
                input_identifiers=input_identifiers,
                source_endpoint_name=source_endpoint_name,
                target_endpoint_name=target_endpoint_name,
                execution_id=execution_id,
                resume_from_checkpoint=resume_from_checkpoint,
                **kwargs
            )
            
            self.logger.info(
                f"Robust YAML strategy '{strategy_name}' completed. "
                f"Execution ID: {execution_id}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                f"Error in robust execution of YAML strategy '{strategy_name}' "
                f"(execution ID: {execution_id}): {str(e)}"
            )
            raise
            
    async def get_strategy_info(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get information about a specific strategy.
        
        Args:
            strategy_name: Name of the strategy to get info for
            
        Returns:
            Dictionary containing strategy metadata including:
                - Strategy configuration details
                - Step definitions
                - Endpoint requirements
                - Execution statistics (if available)
        """
        self.logger.debug(f"Retrieving strategy info for '{strategy_name}'")
        
        try:
            # This would delegate to the strategy orchestrator or handler
            # to get strategy metadata and configuration details
            strategy_info = await self.strategy_orchestrator.get_strategy_info(strategy_name)
            
            return strategy_info
            
        except Exception as e:
            self.logger.error(f"Error retrieving strategy info for '{strategy_name}': {str(e)}")
            raise
            
    async def list_available_strategies(self) -> List[Dict[str, Any]]:
        """
        List all available YAML strategies.
        
        Returns:
            List of dictionaries containing strategy summaries with:
                - strategy_name: Name of the strategy
                - description: Strategy description
                - source_endpoint: Expected source endpoint (if specified)
                - target_endpoint: Expected target endpoint (if specified)
                - step_count: Number of steps in the strategy
                - is_active: Whether the strategy is currently active
        """
        self.logger.debug("Retrieving list of available strategies")
        
        try:
            # This would delegate to the strategy orchestrator to get the list
            strategies = await self.strategy_orchestrator.list_strategies()
            
            self.logger.info(f"Found {len(strategies)} available strategies")
            return strategies
            
        except Exception as e:
            self.logger.error(f"Error listing available strategies: {str(e)}")
            raise
            
    async def validate_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """
        Validate a strategy configuration without executing it.
        
        Args:
            strategy_name: Name of the strategy to validate
            
        Returns:
            Dictionary containing validation results:
                - is_valid: Boolean indicating if strategy is valid
                - validation_errors: List of validation error messages
                - validation_warnings: List of validation warnings
                - strategy_summary: Basic strategy information
        """
        self.logger.debug(f"Validating strategy '{strategy_name}'")
        
        try:
            # This would delegate to the strategy orchestrator for validation
            validation_result = await self.strategy_orchestrator.validate_strategy(strategy_name)
            
            if validation_result['is_valid']:
                self.logger.info(f"Strategy '{strategy_name}' validation passed")
            else:
                self.logger.warning(
                    f"Strategy '{strategy_name}' validation failed: "
                    f"{len(validation_result['validation_errors'])} errors"
                )
                
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating strategy '{strategy_name}': {str(e)}")
            raise
"""
StrategyCoordinatorService - Consolidates all strategy execution logic.

This service provides a single, clean interface for executing different types of mapping strategies:
- Database-backed strategies (via DbStrategyExecutionService)
- YAML-defined strategies (via YamlStrategyExecutionService)  
- Robust YAML strategies (via RobustExecutionCoordinator)

The service coordinates between these different execution models and simplifies the MappingExecutor facade.
"""

import logging
from typing import List, Dict, Any, Optional

from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError,
    MappingExecutionError
)


class StrategyCoordinatorService:
    """
    Coordinates the execution of different types of mapping strategies.
    
    This service consolidates all strategy execution logic that was previously spread across
    MappingExecutor, providing a cleaner separation of concerns and a single point of control
    for strategy execution.
    """
    
    def __init__(
        self,
        db_strategy_execution_service,
        yaml_strategy_execution_service,
        robust_execution_coordinator,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the StrategyCoordinatorService.
        
        Args:
            db_strategy_execution_service: Service for executing database strategies
            yaml_strategy_execution_service: Service for executing YAML strategies
            robust_execution_coordinator: Coordinator for robust strategy execution
            logger: Optional logger instance
        """
        self.db_strategy_execution_service = db_strategy_execution_service
        self.yaml_strategy_execution_service = yaml_strategy_execution_service
        self.robust_execution_coordinator = robust_execution_coordinator
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute_strategy(
        self,
        strategy_name: str,
        initial_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> MappingResultBundle:
        """
        Execute a named mapping strategy from the database.
        
        This method delegates to the DbStrategyExecutionService for executing database-stored
        mapping strategies. This is the legacy method maintained for backward compatibility.
        
        Args:
            strategy_name: Name of the strategy to execute
            initial_identifiers: List of identifiers to start with
            source_ontology_type: Optional override for source ontology type
            target_ontology_type: Optional override for target ontology type
            entity_type: Optional entity type if not implicitly available
            
        Returns:
            MappingResultBundle containing comprehensive results and provenance
            
        Raises:
            StrategyNotFoundError: If the strategy is not found in the database
            InactiveStrategyError: If the strategy is not active
            MappingExecutionError: If an error occurs during execution
        """
        self.logger.info(f"Executing database strategy '{strategy_name}' with {len(initial_identifiers)} identifiers")
        
        return await self.db_strategy_execution_service.execute(
            strategy_name=strategy_name,
            initial_identifiers=initial_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            entity_type=entity_type,
        )

    async def execute_yaml_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        progress_callback: Optional[callable] = None,
        batch_size: int = 250,
        min_confidence: float = 0.0,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a YAML-defined mapping strategy using dedicated strategy action classes.
        
        This method delegates to the YamlStrategyExecutionService for executing multi-step
        mapping strategies defined in YAML configuration. Each step in the strategy is
        executed sequentially using dedicated action classes, with the output of one step
        becoming the input for the next.
        
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
            initial_context: Optional initial context dictionary to merge into execution context
            
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
        """
        self.logger.info(
            f"Executing YAML strategy '{strategy_name}' from {source_endpoint_name} "
            f"to {target_endpoint_name} with {len(input_identifiers)} identifiers"
        )
        
        return await self.yaml_strategy_execution_service.execute(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            progress_callback=progress_callback,
            batch_size=batch_size,
            min_confidence=min_confidence,
            initial_context=initial_context,
        )
        
    async def execute_robust_yaml_strategy(
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
        robustness features via the RobustExecutionCoordinator.
        
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
        self.logger.info(
            f"Executing robust YAML strategy '{strategy_name}' with {len(input_identifiers)} identifiers"
        )
        
        # Delegate to the RobustExecutionCoordinator
        return await self.robust_execution_coordinator.execute_strategy_robustly(
            strategy_name=strategy_name,
            input_identifiers=input_identifiers,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            execution_id=execution_id,
            resume_from_checkpoint=resume_from_checkpoint,
            **kwargs
        )
"""
StrategyExecutionService - Dedicated service for executing YAML-defined mapping strategies.

This service extracts the high-level logic for executing YAML-defined mapping strategies 
from MappingExecutor into a dedicated service. It serves as the primary entry point for 
running complex, multi-step mapping workflows.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError,
    ConfigurationError,
    MappingExecutionError,
)
from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.core.engine_components.config_loader import ConfigLoader
from biomapper.core.engine_components.robust_execution_coordinator import RobustExecutionCoordinator
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.engine_components.identifier_loader import IdentifierLoader
from biomapper.core.engine_components.progress_reporter import ProgressReporter

# Import models for metamapper DB
from biomapper.db.models import (
    MappingStrategy,
    MappingStrategyStep,
)


class StrategyExecutionService:
    """
    Dedicated service for executing YAML-defined mapping strategies.
    
    This service handles the orchestration of complex, multi-step mapping workflows
    by coordinating with various components including StrategyOrchestrator,
    RobustExecutionCoordinator, and other core engine components.
    
    Core Responsibilities:
    - Load and validate mapping strategies by name
    - Orchestrate execution of strategy steps using StrategyOrchestrator
    - Coordinate robust execution with checkpointing and retries
    - Manage progress reporting for entire strategy execution
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        config_loader: ConfigLoader,
        robust_execution_coordinator: RobustExecutionCoordinator,
        session_manager: SessionManager,
        identifier_loader: IdentifierLoader,
        progress_reporter: ProgressReporter,
    ):
        """
        Initialize the StrategyExecutionService.
        
        Args:
            logger: Logger instance for this service
            config_loader: Configuration loader for strategy configurations
            robust_execution_coordinator: Coordinator for robust execution features
            session_manager: Database session manager
            identifier_loader: Service for loading identifiers
            progress_reporter: Service for reporting execution progress
        """
        self.logger = logger
        self.config_loader = config_loader
        self.robust_execution_coordinator = robust_execution_coordinator
        self.session_manager = session_manager
        self.identifier_loader = identifier_loader
        self.progress_reporter = progress_reporter
        
    async def execute_strategy(
        self,
        strategy_name: str,
        initial_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> MappingResultBundle:
        """
        Execute a named mapping strategy from the database (legacy method).
        
        **LEGACY METHOD**: This method is maintained for backward compatibility with 
        older database-stored strategies that use the action handler approach. It loads 
        a strategy and its steps from the metamapper database and attempts to execute 
        them using legacy `_handle_*` methods.
        
        **IMPORTANT**: The handler methods (`_handle_convert_identifiers_local`, 
        `_handle_execute_mapping_path`, `_handle_filter_identifiers_by_target_presence`) 
        referenced by this method are currently **not implemented** in this class. 
        They exist as references in the action_handlers dictionary but will raise 
        "Handler not found" errors when called.
        
        **Current Status**: This method is incomplete and will fail for strategies 
        that require the missing handler implementations. For functional strategy 
        execution, use `execute_yaml_strategy()` which uses the newer strategy action 
        classes in `biomapper.core.strategy_actions`.
        
        **Usage Notes**: 
        - Use `execute_yaml_strategy()` for YAML-defined strategies (recommended)
        - This method should only be used if the missing handlers are implemented
        - The newer strategy action architecture provides better modularity and testing
        
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
            MappingExecutionError: If an error occurs during execution or if required
                handlers are not implemented
        """
        self.logger.info(f"Starting execution of strategy '{strategy_name}' with {len(initial_identifiers)} identifiers")
        
        # Initialize result bundle
        result_bundle = MappingResultBundle(
            strategy_name=strategy_name,
            initial_identifiers=initial_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type
        )
        
        try:
            # Load the strategy from database
            async with self.session_manager.get_metamapper_session() as session:
                # Query for the strategy
                stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_name)
                result = await session.execute(stmt)
                strategy = result.scalar_one_or_none()
                
                if not strategy:
                    raise StrategyNotFoundError(
                        f"Mapping strategy '{strategy_name}' not found in database",
                        details={"strategy_name": strategy_name}
                    )
                
                if not strategy.is_active:
                    raise InactiveStrategyError(
                        f"Mapping strategy '{strategy_name}' is not active",
                        details={"strategy_name": strategy_name, "is_active": strategy.is_active}
                    )
                
                # Load strategy steps eagerly
                stmt = (
                    select(MappingStrategyStep)
                    .where(MappingStrategyStep.strategy_id == strategy.id)
                    .order_by(MappingStrategyStep.step_order)
                )
                step_result = await session.execute(stmt)
                steps = step_result.scalars().all()
                
                if not steps:
                    raise ConfigurationError(
                        f"Mapping strategy '{strategy_name}' has no steps defined",
                        details={"strategy_name": strategy_name, "strategy_id": strategy.id}
                    )
                
                # Set total steps in result bundle
                result_bundle.total_steps = len(steps)
                
                # Determine effective source and target ontology types
                effective_source_type = source_ontology_type or strategy.default_source_ontology_type
                effective_target_type = target_ontology_type or strategy.default_target_ontology_type
                
                if not effective_source_type:
                    self.logger.warning(f"No source ontology type specified for strategy '{strategy_name}'")
                if not effective_target_type:
                    self.logger.warning(f"No target ontology type specified for strategy '{strategy_name}'")
                
                # Update result bundle with effective types
                result_bundle.source_ontology_type = effective_source_type
                result_bundle.target_ontology_type = effective_target_type
                result_bundle.current_ontology_type = effective_source_type
            
            # Initialize execution state
            current_identifiers = list(initial_identifiers)
            current_source_ontology_type = effective_source_type
            
            # Action handlers mapping - NOTE: These handlers are not implemented in this service
            action_handlers = {
                "CONVERT_IDENTIFIERS_LOCAL": self._handle_convert_identifiers_local,
                "EXECUTE_MAPPING_PATH": self._handle_execute_mapping_path,
                "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE": self._handle_filter_identifiers_by_target_presence,
                # Add other action types as they are defined
            }
            
            # Execute each step
            for step in steps:
                self.logger.info(f"Executing step {step.step_order}: {step.step_id} - {step.description}")
                
                try:
                    # Get the action handler
                    action_type = step.action_type
                    handler = action_handlers.get(action_type)
                    
                    if not handler:
                        error_msg = f"No handler found for action type: {action_type}"
                        self.logger.error(error_msg)
                        
                        # Record the failed step
                        result_bundle.add_step_result(
                            step_id=step.step_id,
                            step_description=step.description or "",
                            action_type=action_type,
                            input_identifiers=current_identifiers,
                            output_identifiers=current_identifiers,  # No change on error
                            status="failed",
                            details={"error": "Handler not found"},
                            error=error_msg
                        )
                        
                        # Decide whether to continue or halt based on is_required flag
                        if step.is_required:
                            raise MappingExecutionError(
                                f"Required step '{step.step_id}' failed: {error_msg}",
                                details={"step_id": step.step_id, "action_type": action_type}
                            )
                        else:
                            self.logger.warning(f"Optional step '{step.step_id}' failed, continuing with next step")
                            continue
                    
                    # Execute the handler
                    handler_result = await handler(
                        current_identifiers=current_identifiers,
                        action_parameters=step.action_parameters or {},
                        current_source_ontology_type=current_source_ontology_type,
                        target_ontology_type=effective_target_type,
                        step_id=step.step_id,
                        step_description=step.description
                    )
                    
                    # Check if handler indicates failure
                    handler_status = handler_result.get("status", "success")
                    
                    # Update state from handler result
                    output_identifiers = handler_result.get("output_identifiers", current_identifiers)
                    output_ontology_type = handler_result.get("output_ontology_type", current_source_ontology_type)
                    
                    # Record step result
                    result_bundle.add_step_result(
                        step_id=step.step_id,
                        step_description=step.description or "",
                        action_type=action_type,
                        input_identifiers=current_identifiers,
                        output_identifiers=output_identifiers,
                        status=handler_status,
                        details=handler_result.get("details", {}),
                        output_ontology_type=output_ontology_type
                    )
                    
                    # Check if step failed and handle based on is_required
                    if handler_status == "failed":
                        error_msg = handler_result.get("error", "Step execution failed")
                        if step.is_required:
                            result_bundle.finalize(status="failed", error=error_msg)
                            raise MappingExecutionError(
                                f"Required step '{step.step_id}' failed",
                                details={"step_id": step.step_id, "status": handler_status}
                            )
                        else:
                            self.logger.warning(f"Optional step '{step.step_id}' failed, continuing with next step")
                            continue
                    
                    # Update current state for next step only if step succeeded
                    current_identifiers = output_identifiers
                    current_source_ontology_type = output_ontology_type
                    
                except Exception as e:
                    error_msg = f"Error executing step '{step.step_id}': {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    
                    # Record the failed step
                    result_bundle.add_step_result(
                        step_id=step.step_id,
                        step_description=step.description or "",
                        action_type=step.action_type,
                        input_identifiers=current_identifiers,
                        output_identifiers=current_identifiers,  # No change on error
                        status="failed",
                        details={"exception": str(type(e).__name__)},
                        error=error_msg
                    )
                    
                    # Decide whether to continue or halt based on is_required flag
                    if step.is_required:
                        result_bundle.finalize(status="failed", error=error_msg)
                        raise MappingExecutionError(
                            f"Required step '{step.step_id}' failed",
                            details={"step_id": step.step_id, "error": str(e)}
                        ) from e
                    else:
                        self.logger.warning(f"Optional step '{step.step_id}' failed with error: {error_msg}")
                        self.logger.warning("Continuing with next step since this step is optional")
                        # Don't update current_identifiers or current_source_ontology_type
                        continue
            
            # Finalize the result bundle
            result_bundle.finalize(status="completed")
            self.logger.info(
                f"Strategy '{strategy_name}' completed successfully. "
                f"Final identifier count: {len(result_bundle.current_identifiers)}"
            )
            
        except (StrategyNotFoundError, InactiveStrategyError, ConfigurationError) as e:
            # These are expected errors, re-raise them
            result_bundle.finalize(status="failed", error=str(e))
            raise
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error executing strategy '{strategy_name}': {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result_bundle.finalize(status="failed", error=error_msg)
            raise MappingExecutionError(error_msg, details={"strategy_name": strategy_name}) from e
        
        return result_bundle
    
    # Placeholder methods for action handlers - these need to be implemented
    async def _handle_convert_identifiers_local(self, **kwargs):
        """Placeholder for convert identifiers local handler - NOT IMPLEMENTED."""
        raise MappingExecutionError("Handler _handle_convert_identifiers_local is not implemented")
    
    async def _handle_execute_mapping_path(self, **kwargs):
        """Placeholder for execute mapping path handler - NOT IMPLEMENTED."""
        raise MappingExecutionError("Handler _handle_execute_mapping_path is not implemented")
    
    async def _handle_filter_identifiers_by_target_presence(self, **kwargs):
        """Placeholder for filter identifiers by target presence handler - NOT IMPLEMENTED."""
        raise MappingExecutionError("Handler _handle_filter_identifiers_by_target_presence is not implemented")
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
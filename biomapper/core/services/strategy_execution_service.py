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
"""
Action executor module for executing individual strategy actions.

This module handles the execution of strategy actions, including:
- Parameter processing and context resolution
- Action execution with proper error handling
- Result validation and normalization
"""

import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.exceptions import MappingExecutionError
from biomapper.core.engine_components.action_loader import ActionLoader
from biomapper.db.models import MappingStrategyStep, Endpoint

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Handles the execution of individual strategy actions."""
    
    def __init__(self, mapping_executor: Any = None):
        """
        Initialize the action executor.
        
        Args:
            mapping_executor: Reference to the main MappingExecutor instance
        """
        self.mapping_executor = mapping_executor
        self.action_loader = ActionLoader()
        self.logger = logger
    
    async def execute_action(
        self,
        step: MappingStrategyStep,
        current_identifiers: List[str],
        current_ontology_type: str,
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        use_cache: bool,
        max_cache_age_days: Optional[int],
        batch_size: int,
        min_confidence: float,
        strategy_context: Dict[str, Any],
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Execute a single strategy action step.
        
        Args:
            step: The MappingStrategyStep containing action type and parameters
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type of the identifiers
            source_endpoint: Source endpoint configuration
            target_endpoint: Target endpoint configuration
            use_cache: Whether to use caching for this action
            max_cache_age_days: Maximum age for cached results
            batch_size: Size of batches for processing
            min_confidence: Minimum confidence threshold for results
            strategy_context: Shared context dictionary that persists across steps
            db_session: Active database session
            
        Returns:
            Dict[str, Any]: Action result containing:
                - output_identifiers: List of identifiers after processing
                - output_ontology_type: Ontology type after processing
                - Additional action-specific metadata and statistics
                
        Raises:
            MappingExecutionError: If the action execution fails
        """
        action_type = step.action_type
        action_params = step.action_parameters or {}
        
        # Process action parameters to handle context references
        processed_params = self._process_action_parameters(action_params, strategy_context)
        
        self.logger.info(f"Executing action type: {action_type} with params: {processed_params}")
        
        # Update strategy context with execution parameters
        self._update_context_for_execution(
            strategy_context,
            db_session,
            use_cache,
            max_cache_age_days,
            batch_size,
            min_confidence
        )
        
        self.logger.debug(f"Context before action: {list(strategy_context.keys())}")
        
        # Load and instantiate the action
        try:
            action = self.action_loader.instantiate_action(action_type, db_session)
        except Exception as e:
            raise MappingExecutionError(
                f"Failed to load action '{action_type}': {str(e)}"
            )
        
        # Execute the action
        try:
            result = await action.execute(
                current_identifiers=current_identifiers,
                current_ontology_type=current_ontology_type,
                action_params=processed_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=strategy_context
            )
            
            # Ensure result has required fields
            result = self._normalize_action_result(result, current_identifiers, current_ontology_type)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing strategy action {action_type}: {str(e)}")
            raise MappingExecutionError(f"Strategy action {action_type} failed: {str(e)}")
    
    def _process_action_parameters(self, action_params: Dict[str, Any], 
                                   strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process action parameters to handle context references.
        
        Args:
            action_params: Raw action parameters from the strategy step
            strategy_context: Current strategy context
            
        Returns:
            Processed parameters with context references resolved
        """
        processed_params = {}
        
        for key, value in action_params.items():
            if isinstance(value, str) and value.startswith("context."):
                # This is a reference to context, strip the prefix
                context_key = value[8:]  # Remove "context." prefix
                processed_params[key] = context_key
            else:
                processed_params[key] = value
        
        return processed_params
    
    def _update_context_for_execution(
        self,
        strategy_context: Dict[str, Any],
        db_session: AsyncSession,
        use_cache: bool,
        max_cache_age_days: Optional[int],
        batch_size: int,
        min_confidence: float
    ):
        """
        Update the strategy context with execution parameters.
        
        Args:
            strategy_context: Context dictionary to update
            db_session: Active database session
            use_cache: Whether caching is enabled
            max_cache_age_days: Maximum cache age
            batch_size: Batch size for processing
            min_confidence: Minimum confidence threshold
        """
        strategy_context.update({
            "db_session": db_session,
            "cache_settings": {
                "use_cache": use_cache,
                "max_cache_age_days": max_cache_age_days
            },
            "mapping_executor": self.mapping_executor,
            "batch_size": batch_size,
            "min_confidence": min_confidence
        })
    
    def _normalize_action_result(
        self, 
        result: Dict[str, Any], 
        current_identifiers: List[str],
        current_ontology_type: str
    ) -> Dict[str, Any]:
        """
        Normalize action result to ensure it has required fields.
        
        Args:
            result: Raw result from action execution
            current_identifiers: Input identifiers
            current_ontology_type: Input ontology type
            
        Returns:
            Normalized result with required fields
        """
        # Ensure output_identifiers exists
        if 'output_identifiers' not in result:
            result['output_identifiers'] = result.get('input_identifiers', current_identifiers)
        
        # Ensure output_ontology_type exists
        if 'output_ontology_type' not in result:
            result['output_ontology_type'] = current_ontology_type
        
        return result
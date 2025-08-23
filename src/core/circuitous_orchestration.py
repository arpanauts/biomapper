"""
Circuitous Pipeline Orchestration Layer
========================================

🔄 This module provides the orchestration layer that ensures smooth context
flow through pipeline stages using the UniversalContext wrapper.

Key Features:
- Transparent context wrapping/unwrapping
- Stage boundary management
- Parameter flow validation
- Handoff verification
"""

import logging
from typing import Any, Dict, Optional
from .universal_context import UniversalContext, ensure_universal_context

logger = logging.getLogger(__name__)


class CircuitousOrchestrator:
    """
    Orchestrator that manages context flow through pipeline stages.
    
    🔄 Circuitous Design: Sits between MinimalStrategyService and actions,
    ensuring smooth context handoffs without modifying either layer.
    """
    
    @staticmethod
    def prepare_context_for_action(
        action_name: str,
        raw_context: Any,
        action_params: Dict[str, Any]
    ) -> UniversalContext:
        """
        Prepare context for action execution.
        
        🔄 Ensures context is in UniversalContext format before handoff.
        """
        logger.debug(f"🔄 Preparing context for action: {action_name}")
        
        # Wrap in UniversalContext
        context = ensure_universal_context(raw_context)
        
        # Log current state for debugging
        datasets = list(context.get_datasets().keys())
        logger.debug(f"🔄 Available datasets before {action_name}: {datasets}")
        
        # Validate parameters are accessible
        if not context.get_parameters():
            logger.warning(f"🔄 No parameters in context for {action_name}")
        
        return context
    
    @staticmethod
    def extract_result_from_context(
        action_name: str,
        context: UniversalContext,
        original_context: Any
    ) -> None:
        """
        Extract results from UniversalContext back to original format.
        
        🔄 Maintains bidirectional flow for compatibility.
        """
        logger.debug(f"🔄 Extracting results from {action_name}")
        
        # Sync changes back to original context
        if original_context is not context:
            context.sync_to(original_context)
            
        # Log what was added/modified
        datasets = list(context.get_datasets().keys())
        logger.debug(f"🔄 Datasets after {action_name}: {datasets}")
    
    @staticmethod
    def validate_stage_transition(
        from_stage: str,
        to_stage: str,
        context: UniversalContext,
        required_datasets: list
    ) -> bool:
        """
        Validate context has required data for stage transition.
        
        🔄 Pre-flight check for smooth handoffs between stages.
        """
        logger.info(f"🔄 Validating transition: {from_stage} → {to_stage}")
        
        # Check required datasets exist
        if not context.validate_handoff(required_datasets):
            logger.error(f"🔄 Stage transition failed: missing required datasets")
            return False
        
        # Check for data integrity
        datasets = context.get_datasets()
        for key in required_datasets:
            data = datasets.get(key)
            if data is None or (hasattr(data, '__len__') and len(data) == 0):
                logger.warning(f"🔄 Dataset '{key}' is empty for transition to {to_stage}")
        
        return True
    
    @staticmethod
    def create_action_wrapper(action_class):
        """
        Create a wrapper for an action that handles context conversion.
        
        🔄 This wrapper ensures actions receive context in the format they expect
        without modifying the action code itself.
        """
        class CircuitousActionWrapper:
            def __init__(self):
                self.action = action_class()
            
            async def execute(self, *args, **kwargs):
                # Find context in arguments
                context_arg = None
                context_idx = None
                
                # Check kwargs first
                if 'context' in kwargs:
                    context_arg = kwargs['context']
                    # Wrap it
                    wrapped_context = ensure_universal_context(context_arg)
                    kwargs['context'] = wrapped_context
                    
                    # Execute action
                    result = await self.action.execute(*args, **kwargs)
                    
                    # Sync back
                    if context_arg is not wrapped_context:
                        wrapped_context.sync_to(context_arg)
                    
                    return result
                
                # Fallback to original behavior
                return await self.action.execute(*args, **kwargs)
            
            def __getattr__(self, name):
                # Delegate all other attributes to original action
                return getattr(self.action, name)
        
        return CircuitousActionWrapper
    
    @staticmethod
    def wrap_action_registry(registry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap all actions in registry with circuitous wrappers.
        
        🔄 This ensures all actions get UniversalContext without modification.
        """
        wrapped_registry = {}
        
        for action_name, action_class in registry.items():
            logger.debug(f"🔄 Wrapping action: {action_name}")
            wrapper_class = CircuitousOrchestrator.create_action_wrapper(action_class)
            wrapped_registry[action_name] = wrapper_class
        
        logger.info(f"🔄 Wrapped {len(wrapped_registry)} actions for circuitous flow")
        return wrapped_registry


# 🔄 Integration helpers for MinimalStrategyService

def apply_circuitous_orchestration(service_instance):
    """
    Apply circuitous orchestration to a MinimalStrategyService instance.
    
    This monkey-patches the service to use UniversalContext for all
    context handling without modifying the service code.
    
    🔄 Circuitous Pattern: Transparent enhancement of existing service.
    """
    original_execute = service_instance.execute_strategy
    
    async def circuitous_execute(strategy_name: str, context: Optional[Dict] = None):
        # Wrap context
        wrapped_context = ensure_universal_context(context or {})
        
        # Log orchestration start
        logger.info(f"🔄 Circuitous orchestration starting for: {strategy_name}")
        logger.debug(f"🔄 Initial context keys: {list(wrapped_context.keys())}")
        
        # Execute with wrapped context
        result = await original_execute(strategy_name, wrapped_context)
        
        # Ensure result has context changes
        if isinstance(result, dict) and context is not None:
            # Sync wrapped context back to original
            wrapped_context.sync_to(context)
        
        logger.info(f"🔄 Circuitous orchestration complete for: {strategy_name}")
        return result
    
    # Replace method
    service_instance.execute_strategy = circuitous_execute
    logger.info("🔄 Circuitous orchestration applied to service")
    
    return service_instance
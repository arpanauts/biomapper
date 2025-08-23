"""
Apply Circuitous Framework Fix to Runtime
=========================================

🔄 This module applies the UniversalContext wrapper to the runtime
environment to fix context flow issues.
"""

import logging
from typing import Any, Dict
from .universal_context import UniversalContext, ensure_universal_context

logger = logging.getLogger(__name__)


def patch_minimal_strategy_service():
    """
    Patch MinimalStrategyService to use UniversalContext.
    
    🔄 Circuitous Pattern: Modifies service behavior without changing code.
    """
    try:
        from core.minimal_strategy_service import MinimalStrategyService
        
        # Store original execute_action method
        original_execute_action = MinimalStrategyService._execute_action
        
        async def circuitous_execute_action(self, action_type: str, action_params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Wrapped execute_action that ensures UniversalContext.
            
            🔄 Ensures actions receive context in compatible format.
            """
            # Wrap context in UniversalContext
            wrapped_context = ensure_universal_context(context)
            
            # Call original method with wrapped context
            result = await original_execute_action(self, action_type, action_params, wrapped_context)
            
            # Sync changes back if needed
            if not isinstance(context, UniversalContext):
                wrapped_context.sync_to(context)
            
            return result
        
        # Replace method
        MinimalStrategyService._execute_action = circuitous_execute_action
        logger.info("🔄 Circuitous fix applied to MinimalStrategyService")
        
    except Exception as e:
        logger.error(f"🔄 Failed to apply circuitous fix: {e}")


def patch_action_registry():
    """
    Patch action registry to wrap contexts automatically.
    
    🔄 Circuitous Pattern: Ensures all actions get UniversalContext.
    """
    try:
        from actions.registry import ACTION_REGISTRY
        
        for action_name, action_class in ACTION_REGISTRY.items():
            # Store original execute
            if hasattr(action_class, 'execute'):
                original_execute = action_class.execute
                
                async def wrapped_execute(self, *args, **kwargs):
                    # Find and wrap context
                    if 'context' in kwargs:
                        kwargs['context'] = ensure_universal_context(kwargs['context'])
                    
                    return await original_execute(*args, **kwargs)
                
                # Replace method
                action_class.execute = wrapped_execute
        
        logger.info(f"🔄 Circuitous fix applied to {len(ACTION_REGISTRY)} actions")
        
    except Exception as e:
        logger.error(f"🔄 Failed to patch action registry: {e}")


# Auto-apply fixes when imported
patch_minimal_strategy_service()
patch_action_registry()

logger.info("🔄 Circuitous framework fixes applied to runtime")
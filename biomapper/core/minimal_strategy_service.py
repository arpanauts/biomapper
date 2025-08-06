"""Minimal YAML strategy execution service."""
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from jinja2 import Template

from biomapper.core.strategy_actions import (
    LoadDatasetIdentifiersAction,
    MergeWithUniprotResolutionAction,
    CalculateSetOverlapAction,
)
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
# No need for StrategyExecutionContext - we'll use a simple dict

logger = logging.getLogger(__name__)


class MinimalStrategyService:
    """Minimal service for executing YAML strategies."""
    
    def __init__(self, strategies_dir: str):
        """Initialize with strategies directory."""
        self.strategies_dir = Path(strategies_dir)
        self.strategies = self._load_strategies()
        self.action_registry = self._build_action_registry()
        
    def _load_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load all YAML strategies from directory."""
        strategies = {}
        
        if not self.strategies_dir.exists():
            logger.warning(f"Strategies directory not found: {self.strategies_dir}")
            return strategies
            
        for yaml_file in self.strategies_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    strategy_data = yaml.safe_load(f)
                    if strategy_data and 'name' in strategy_data:
                        strategies[strategy_data['name']] = strategy_data
                        logger.info(f"Loaded strategy: {strategy_data['name']}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
                
        return strategies
    
    def _substitute_parameters(self, obj: Any, parameters: Dict[str, Any]) -> Any:
        """Recursively substitute parameter placeholders in a nested structure.
        
        Args:
            obj: The object to process (dict, list, str, or other)
            parameters: The parameters dictionary for substitution
            
        Returns:
            The object with all parameter placeholders substituted
        """
        if isinstance(obj, str):
            # Check if the string contains parameter placeholders
            if '${' in obj:
                # Use Jinja2 template for substitution
                # Convert ${parameters.key} to {{ parameters.key }}
                template_str = re.sub(r'\$\{([^}]+)\}', r'{{ \1 }}', obj)
                template = Template(template_str)
                try:
                    return template.render(parameters=parameters)
                except Exception as e:
                    logger.warning(f"Failed to substitute parameters in '{obj}': {e}")
                    return obj
            return obj
        elif isinstance(obj, dict):
            return {key: self._substitute_parameters(value, parameters) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_parameters(item, parameters) for item in obj]
        else:
            return obj
        
    def _build_action_registry(self) -> Dict[str, type[TypedStrategyAction]]:
        """Build registry of available actions."""
        # Import to ensure all actions are registered
        import biomapper.core.strategy_actions  # This triggers all action imports
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
        
        # Use the central action registry which has all registered actions
        logger.info(f"Loaded {len(ACTION_REGISTRY)} actions from registry")
        return ACTION_REGISTRY
        
    async def execute_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str = "",
        target_endpoint_name: str = "",
        input_identifiers: List[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a named strategy."""
        
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found")
            
        strategy = self.strategies[strategy_name]
        
        # Merge default parameters with context overrides
        parameters = strategy.get('parameters', {}).copy()
        if context and 'parameters' in context:
            parameters.update(context['parameters'])
        
        # Initialize execution context as a simple dict (not StrategyExecutionContext)
        execution_context = {
            'current_identifiers': input_identifiers or [],
            'source_endpoint_name': source_endpoint_name,
            'target_endpoint_name': target_endpoint_name,
            'current_ontology_type': 'protein',  # Default for our MVP
            'datasets': {},
            'statistics': {},
            'output_files': {},
        }
        
        # Dummy endpoints for MVP (not used by our actions)
        # Create a simple dict that acts like an endpoint
        dummy_endpoint = type('Endpoint', (), {
            'id': 1,
            'name': 'dummy',
            'description': 'Dummy endpoint for MVP',
            'type': 'file'
        })()
        
        logger.info(f"Executing strategy '{strategy_name}' with {len(strategy.get('steps', []))} steps")
        
        # Execute each step
        for step in strategy.get('steps', []):
            step_name = step.get('name', 'unnamed')
            action_config = step.get('action', {})
            action_type = action_config.get('type')
            # Substitute parameters in action params
            raw_params = action_config.get('params', {})
            action_params = self._substitute_parameters(raw_params, parameters)
            
            logger.info(f"Executing step '{step_name}' with action '{action_type}'")
            
            if action_type not in self.action_registry:
                raise ValueError(f"Unknown action type: {action_type}")
                
            # Create and execute action
            action_class = self.action_registry[action_type]
            action = action_class()
            
            try:
                # Call execute method which handles context conversion
                result_dict = await action.execute(
                    current_identifiers=execution_context['current_identifiers'],
                    current_ontology_type=execution_context.get('current_ontology_type', 'protein'),
                    action_params=action_params,
                    source_endpoint=dummy_endpoint,
                    target_endpoint=dummy_endpoint,
                    context=execution_context
                )
                
                # Update context with results from dict
                if result_dict:
                    # Update standard fields
                    if 'output_identifiers' in result_dict:
                        execution_context['current_identifiers'] = result_dict['output_identifiers']
                    if 'output_ontology_type' in result_dict:
                        execution_context['current_ontology_type'] = result_dict['output_ontology_type']
                    
                    # Merge all result data back into context
                    # This ensures datasets and other action outputs are preserved
                    for key, value in result_dict.items():
                        if key not in ['output_identifiers', 'output_ontology_type']:
                            execution_context[key] = value
                    
            except Exception as e:
                logger.error(f"Action '{action_type}' failed: {str(e)}")
                raise
                
        logger.info(f"Strategy '{strategy_name}' completed successfully")
        
        # Return the context as-is (it's already a dict)
        return {
            'current_identifiers': execution_context.get('current_identifiers', []),
            'current_ontology_type': execution_context.get('current_ontology_type', 'protein'),
            'datasets': execution_context.get('datasets', {}),
            'statistics': execution_context.get('statistics', {}),
            'output_files': execution_context.get('output_files', {}),
        }
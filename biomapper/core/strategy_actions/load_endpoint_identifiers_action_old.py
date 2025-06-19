"""
LoadEndpointIdentifiersAction: Loads identifiers from a specified endpoint.

This action loads identifiers from an endpoint and stores them in the execution context
for use by subsequent actions in a mapping strategy.
"""

from typing import Dict, Any
from biomapper.core.strategy_actions.base import BaseStrategyAction


class LoadEndpointIdentifiersAction(BaseStrategyAction):
    """
    Action that loads identifiers from a specified endpoint.
    
    Parameters:
        - endpoint_name (str, required): Name of the endpoint to load from
        - ontology_type_name (str, optional): Specific ontology type to load
        - output_context_key (str, required): Key to store loaded identifiers in context
    """
    
    def __init__(self, params: Dict[str, Any]):
        """Initialize the action with parameters."""
        super().__init__(params)
        
        # Validate required parameters
        self.endpoint_name = params.get('endpoint_name')
        if not self.endpoint_name:
            raise ValueError("endpoint_name is required for LoadEndpointIdentifiersAction")
            
        self.output_context_key = params.get('output_context_key')
        if not self.output_context_key:
            raise ValueError("output_context_key is required for LoadEndpointIdentifiersAction")
            
        # Optional parameters
        self.ontology_type_name = params.get('ontology_type_name')
    
    async def execute(self, context: Dict[str, Any], executor: 'MappingExecutor') -> Dict[str, Any]:
        """
        Execute the action to load endpoint identifiers.
        
        Args:
            context: Current execution context
            executor: MappingExecutor instance
            
        Returns:
            Updated context with loaded identifiers
        """
        # Log the loading operation
        self.log_info(
            f"Loading identifiers from endpoint '{self.endpoint_name}'"
            f"{f' with ontology type {self.ontology_type_name}' if self.ontology_type_name else ''}"
        )
        
        try:
            # Use executor's method to load identifiers
            identifiers = await executor.load_endpoint_identifiers(
                endpoint_name=self.endpoint_name,
                ontology_type_name=self.ontology_type_name
            )
            
            # Store in context
            context[self.output_context_key] = identifiers
            
            # Log success
            self.log_info(
                f"Successfully loaded {len(identifiers)} identifiers "
                f"into context key '{self.output_context_key}'"
            )
            
        except Exception as e:
            self.log_error(f"Failed to load identifiers from endpoint: {str(e)}")
            raise
            
        return context
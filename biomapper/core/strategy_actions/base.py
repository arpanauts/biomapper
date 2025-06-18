"""Base class for strategy actions."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from biomapper.db.models import Endpoint


class BaseStrategyAction(ABC):
    """Abstract base class for all strategy actions."""
    
    @abstractmethod
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the action.
        
        Args:
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type of the identifiers
            action_params: Parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Additional context (cache settings, etc.)
            
        Returns:
            Dictionary containing:
                - input_identifiers: List of input identifiers
                - output_identifiers: List of output identifiers
                - output_ontology_type: Ontology type of output (if changed)
                - provenance: List of provenance records
                - details: Additional details about the execution
        """
        pass


# Alias for backward compatibility
StrategyAction = BaseStrategyAction

# Type alias for action context (currently just a dictionary)
ActionContext = Dict[str, Any]
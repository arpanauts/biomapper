"""Typed base class for strategy actions with backward compatibility."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, TypeVar, Generic, Type, Optional, cast
from pydantic import BaseModel, ValidationError
import logging

from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.core.strategy_actions.base import BaseStrategyAction

# Type variables for generic parameters and results
TParams = TypeVar('TParams', bound=BaseModel)
TResult = TypeVar('TResult', bound=BaseModel)

class TypedStrategyAction(BaseStrategyAction, Generic[TParams, TResult], ABC):
    """
    Abstract base class for type-safe strategy actions.
    
    This class extends BaseStrategyAction to provide type safety through generics
    while maintaining backward compatibility with the existing execute() method.
    
    Subclasses should:
    1. Specify the parameter and result types as class parameters
    2. Implement execute_typed() instead of execute()
    3. Define get_params_model() and get_result_model() to return the Pydantic models
    
    Example:
        class MyActionParams(BaseModel):
            batch_size: int = 100
            
        class MyActionResult(BaseModel):
            processed_count: int
            errors: List[str] = []
            
        class MyAction(TypedStrategyAction[MyActionParams, MyActionResult]):
            def get_params_model(self) -> Type[MyActionParams]:
                return MyActionParams
                
            def get_result_model(self) -> Type[MyActionResult]:
                return MyActionResult
                
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: MyActionParams,
                source_endpoint: Endpoint,
                target_endpoint: Endpoint,
                context: StrategyExecutionContext
            ) -> MyActionResult:
                # Implementation
                return MyActionResult(processed_count=len(current_identifiers))
    """
    
    def __init__(self, db_session: Any = None, *args: Any, **kwargs: Any) -> None:
        """Initialize the action with logging and optional db_session."""
        super().__init__()  # BaseStrategyAction doesn't take arguments
        self.db_session = db_session  # Store the db_session for actions that need it
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
    
    @abstractmethod
    def get_params_model(self) -> Type[TParams]:
        """Return the Pydantic model class for action parameters."""
        pass
    
    @abstractmethod
    def get_result_model(self) -> Type[TResult]:
        """Return the Pydantic model class for action results."""
        pass
    
    @abstractmethod
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: TParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: StrategyExecutionContext
    ) -> TResult:
        """
        Execute the action with typed parameters and context.
        
        Args:
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type of the identifiers
            params: Typed parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Typed execution context
            
        Returns:
            Typed result object
        """
        pass
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the action (backward compatibility method).
        
        This method provides backward compatibility by:
        1. Converting dict parameters to typed Pydantic models
        2. Converting dict context to StrategyExecutionContext
        3. Calling the typed execute_typed method
        4. Converting the typed result back to a dictionary
        
        Args:
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type of the identifiers
            action_params: Parameters specific to this action (as dict)
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Additional context (as dict)
            
        Returns:
            Dictionary containing the standard action result format
        """
        # Convert parameters to typed model
        try:
            params_model = self.get_params_model()
            typed_params = params_model(**action_params)
        except ValidationError as e:
            self.logger.error(f"Invalid action parameters: {e}")
            # Return error result in standard format
            return {
                'input_identifiers': current_identifiers,
                'output_identifiers': [],
                'output_ontology_type': current_ontology_type,
                'provenance': [],
                'details': {
                    'error': f'Invalid parameters: {str(e)}',
                    'validation_errors': e.errors()
                }
            }
        
        # For MVP actions, use dict context directly
        # Check if this is an MVP action (doesn't require StrategyExecutionContext)
        is_mvp_action = self.__class__.__name__ in [
            'LoadDatasetIdentifiersAction',
            'MergeWithUniprotResolutionAction', 
            'CalculateSetOverlapAction'
        ]
        
        if is_mvp_action:
            # Create a mock context that behaves like StrategyExecutionContext for MVP actions
            class MockContext:
                """Mock context that acts like StrategyExecutionContext for MVP actions."""
                def __init__(self, context_dict):
                    self._dict = context_dict
                    if 'custom_action_data' not in self._dict:
                        self._dict['custom_action_data'] = {}
                
                def set_action_data(self, key: str, value: Any) -> None:
                    if 'custom_action_data' not in self._dict:
                        self._dict['custom_action_data'] = {}
                    self._dict['custom_action_data'][key] = value
                
                def get_action_data(self, key: str, default: Any = None) -> Any:
                    return self._dict.get('custom_action_data', {}).get(key, default)
                
                @property
                def custom_action_data(self):
                    if 'custom_action_data' not in self._dict:
                        self._dict['custom_action_data'] = {}
                    return self._dict['custom_action_data']
                
                # Proxy dict-like access to the underlying dict
                def get(self, key, default=None):
                    return self._dict.get(key, default)
                
                def __getitem__(self, key):
                    return self._dict[key]
                
                def __setitem__(self, key, value):
                    self._dict[key] = value
                
                def __contains__(self, key):
                    return key in self._dict
            
            typed_context = MockContext(context)
        else:
            # Convert context to StrategyExecutionContext for other actions
            typed_context = self._convert_context(context, current_identifiers, current_ontology_type)
        
        try:
            # Execute with typed parameters
            typed_result = await self.execute_typed(
                current_identifiers=current_identifiers,
                current_ontology_type=current_ontology_type,
                params=typed_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=typed_context
            )
            
            # Convert typed result to dict
            result_dict = self._convert_result_to_dict(typed_result, current_identifiers, current_ontology_type)
            
            # Update the original context dict with any changes from typed context
            if not is_mvp_action:
                self._update_context_dict(context, typed_context)
            
            return result_dict
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}", exc_info=True)
            # Re-raise the exception to allow proper error handling by the strategy orchestrator
            raise
    
    def _convert_context(self, context_dict: Dict[str, Any], identifiers: List[str], ontology_type: str) -> Any:
        """
        Convert a context dictionary to StrategyExecutionContext.
        
        Args:
            context_dict: The context as a dictionary
            identifiers: Current identifiers
            ontology_type: Current ontology type
            
        Returns:
            StrategyExecutionContext instance
        """
        # Extract known fields from context
        initial_identifier = context_dict.get('initial_identifier', identifiers[0] if identifiers else '')
        current_identifier = context_dict.get('current_identifier', identifiers[0] if identifiers else '')
        
        # Map ontology type to valid literal
        valid_ontology_types = ["gene", "protein", "metabolite", "variant", "compound", "pathway", "disease"]
        mapped_ontology_type = "protein"  # default
        
        # Simple mapping based on common patterns
        if 'GENE' in ontology_type.upper():
            mapped_ontology_type = "gene"
        elif 'PROTEIN' in ontology_type.upper():
            mapped_ontology_type = "protein"
        elif 'METABOLITE' in ontology_type.upper():
            mapped_ontology_type = "metabolite"
        elif 'VARIANT' in ontology_type.upper():
            mapped_ontology_type = "variant"
        elif 'COMPOUND' in ontology_type.upper():
            mapped_ontology_type = "compound"
        elif 'PATHWAY' in ontology_type.upper():
            mapped_ontology_type = "pathway"
        elif 'DISEASE' in ontology_type.upper():
            mapped_ontology_type = "disease"
        
        # Handle step_results conversion from legacy list format to dict format
        raw_step_results = context_dict.get('step_results', [])
        if isinstance(raw_step_results, list):
            # Convert list format to dict format for backward compatibility
            # For now, just use empty dict since we don't need to validate the structure
            # The typed actions can still access the raw data via custom_action_data
            step_results_dict = {}
        else:
            step_results_dict = raw_step_results
        
        # Create execution context
        typed_context = StrategyExecutionContext(
            initial_identifier=initial_identifier,
            current_identifier=current_identifier,
            ontology_type=cast(Any, mapped_ontology_type),  # Cast to satisfy type checker
            step_results=step_results_dict,
            provenance=context_dict.get('provenance', []),
            custom_action_data=context_dict.get('custom_action_data', {})
        )
        
        # Copy over any additional data to custom_action_data
        for key, value in context_dict.items():
            if key not in ['initial_identifier', 'current_identifier', 'ontology_type', 
                          'step_results', 'provenance', 'custom_action_data']:
                typed_context.set_action_data(key, value)
        
        # Store legacy step_results in custom_action_data for backward compatibility
        if isinstance(raw_step_results, list):
            typed_context.set_action_data('legacy_step_results', raw_step_results)
        
        return typed_context
    
    def _convert_result_to_dict(self, typed_result: TResult, input_identifiers: List[str], ontology_type: str) -> Dict[str, Any]:
        """
        Convert a typed result to the standard dictionary format.
        
        Args:
            typed_result: The typed result from execute_typed
            input_identifiers: The input identifiers
            ontology_type: The current ontology type
            
        Returns:
            Standard result dictionary
        """
        # Get the result as a dictionary
        result_dict = typed_result.model_dump()
        
        # Ensure standard fields are present
        standard_result = {
            'input_identifiers': result_dict.get('input_identifiers', input_identifiers),
            'output_identifiers': result_dict.get('output_identifiers', []),
            'output_ontology_type': result_dict.get('output_ontology_type', ontology_type),
            'provenance': result_dict.get('provenance', []),
            'details': result_dict.get('details', {})
        }
        
        # Add any additional fields to details
        for key, value in result_dict.items():
            if key not in standard_result:
                standard_result['details'][key] = value
        
        return standard_result
    
    def _update_context_dict(self, context_dict: Dict[str, Any], typed_context: StrategyExecutionContext) -> None:
        """
        Update the original context dictionary with changes from typed context.
        
        Args:
            context_dict: Original context dictionary to update
            typed_context: Typed context with potential changes
        """
        # Update standard fields
        context_dict['initial_identifier'] = typed_context.initial_identifier
        context_dict['current_identifier'] = typed_context.current_identifier
        context_dict['step_results'] = typed_context.step_results
        context_dict['provenance'] = typed_context.provenance
        
        # Update custom action data
        for key, value in typed_context.custom_action_data.items():
            context_dict[key] = value

# Optional: Provide a simple result model for common use cases
class StandardActionResult(BaseModel):
    """Standard result model that matches the expected dictionary format."""
    
    input_identifiers: List[str]
    output_identifiers: List[str]
    output_ontology_type: str
    provenance: List[Dict[str, Any]] = []
    details: Dict[str, Any] = {}
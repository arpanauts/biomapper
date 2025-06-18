"""
Strategy action to load all identifiers from an endpoint.

This action loads all identifiers of a specific ontology type from either
the source or target endpoint and stores them in the strategy context.
"""

import logging
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from biomapper.core.strategy_actions.base import StrategyAction
from biomapper.core.exceptions import MappingExecutionError
from biomapper.db.models import Endpoint, EndpointPropertyConfig

logger = logging.getLogger(__name__)


class LoadEndpointIdentifiersAction(StrategyAction):
    def __init__(self, db_session: AsyncSession):
        """Initialize the action with a database session."""
        self.db_session = db_session
    """
    Action that loads all identifiers from an endpoint.
    
    This action is typically used at the beginning of bidirectional mapping
    strategies to load all identifiers from either source or target endpoint
    for comprehensive mapping coverage.
    """
    
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
        Load all identifiers from the specified endpoint.
        
        Args:
            current_identifiers: Not used for this action
            current_ontology_type: Not used for this action
            action_params: Action parameters including:
                - endpoint_context: "SOURCE" or "TARGET"
                - input_ids_context_key: Key to store identifiers in context
            source_endpoint: Source endpoint configuration
            target_endpoint: Target endpoint configuration
            context: Strategy execution context
            
        Returns:
            Result dictionary with loaded identifiers
        """
        # Get parameters
        endpoint_context = action_params.get('endpoint_context', 'SOURCE')
        context_key = action_params.get('input_ids_context_key', 'loaded_identifiers')
        
        # Determine which endpoint to load from
        if endpoint_context == 'SOURCE':
            endpoint = source_endpoint
            endpoint_name = source_endpoint.name
        elif endpoint_context == 'TARGET':
            endpoint = target_endpoint
            endpoint_name = target_endpoint.name
        else:
            raise MappingExecutionError(
                f"Invalid endpoint_context: {endpoint_context}. Must be 'SOURCE' or 'TARGET'"
            )
        
        logger.info(f"Loading all identifiers from {endpoint_context} endpoint: {endpoint_name}")
        
        try:
            # Get the primary property configuration for the endpoint
            stmt = (
                select(EndpointPropertyConfig)
                .where(EndpointPropertyConfig.endpoint_id == endpoint.id)
                .where(EndpointPropertyConfig.is_primary_identifier == True)
            )
            
            result = await self.db_session.execute(stmt)
            primary_config = result.scalar_one_or_none()
            
            if not primary_config:
                raise MappingExecutionError(
                    f"No primary identifier configuration found for endpoint {endpoint_name}"
                )
            
            # Get the ontology type
            ontology_type = primary_config.ontology_type
            logger.info(f"Primary identifier type for {endpoint_name}: {ontology_type}")
            
            # For now, we'll simulate loading identifiers
            # In a real implementation, this would query the actual data source
            # based on the endpoint's connection_details
            loaded_identifiers = []
            
            # Store in context
            context[context_key] = loaded_identifiers
            
            logger.info(
                f"Loaded {len(loaded_identifiers)} identifiers from {endpoint_name} "
                f"and stored in context key '{context_key}'"
            )
            
            return {
                'output_identifiers': loaded_identifiers,
                'output_ontology_type': ontology_type,
                'details': {
                    'endpoint': endpoint_name,
                    'identifier_count': len(loaded_identifiers),
                    'context_key': context_key,
                    'ontology_type': ontology_type
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to load identifiers from {endpoint_name}: {str(e)}")
            raise MappingExecutionError(
                f"Failed to load identifiers from {endpoint_name}: {str(e)}"
            )
"""
LoadEndpointIdentifiersAction: Load all identifiers from a specified endpoint.

This action loads identifiers from a specified endpoint and stores them in the execution context
for use by subsequent actions in a mapping strategy.
"""

import json
import logging
from typing import Dict, Any, List, TYPE_CHECKING
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from biomapper.db.models import Endpoint, EndpointPropertyConfig
from biomapper.mapping.adapters.csv_adapter import CSVAdapter
from biomapper.core.strategy_actions.base import BaseStrategyAction

if TYPE_CHECKING:
    from biomapper.core.mapping_executor import MappingExecutor
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class LoadEndpointIdentifiersAction(BaseStrategyAction):
    """
    Action that loads all identifiers from a specified endpoint.
    
    This action:
    - Loads identifiers for a given endpoint name
    - Extracts the primary identifier column values
    - Stores them in the execution context
    - Supports the UKBB-HPA bidirectional mapping pipeline
    """
    
    def __init__(self, session: 'AsyncSession'):
        """
        Initialize the action with a database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
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
        Execute the action to load endpoint identifiers.
        
        Args:
            current_identifiers: List of identifiers to process (ignored for this action)
            current_ontology_type: Current ontology type (ignored for this action)
            action_params: Parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Additional context
            
        Returns:
            Dictionary containing loaded identifiers and metadata
        """
        # Extract parameters
        endpoint_name = action_params.get('endpoint_name')
        if not endpoint_name:
            raise ValueError("endpoint_name is required for LoadEndpointIdentifiersAction")
        
        output_context_key = action_params.get('output_context_key')
        if not output_context_key:
            raise ValueError("output_context_key is required for LoadEndpointIdentifiersAction")
            
        logger.info(f"Loading identifiers for endpoint '{endpoint_name}'")
        
        try:
            # Find the endpoint by name
            stmt = (
                select(Endpoint)
                .where(Endpoint.name == endpoint_name)
            )
            result = await self.session.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                raise ValueError(f"Endpoint '{endpoint_name}' not found in database")
            
            logger.debug(f"Found endpoint: {endpoint.name} (ID: {endpoint.id})")
            
            # Get the primary property configuration
            stmt = (
                select(EndpointPropertyConfig)
                .options(selectinload(EndpointPropertyConfig.property_extraction_config))
                .where(
                    EndpointPropertyConfig.endpoint_id == endpoint.id,
                    EndpointPropertyConfig.is_primary_identifier == True
                )
            )
            result = await self.session.execute(stmt)
            primary_config = result.scalar_one_or_none()
            
            if not primary_config:
                # Fallback: try to find any property config
                stmt = (
                    select(EndpointPropertyConfig)
                    .options(selectinload(EndpointPropertyConfig.property_extraction_config))
                    .where(EndpointPropertyConfig.endpoint_id == endpoint.id)
                    .limit(1)
                )
                result = await self.session.execute(stmt)
                primary_config = result.scalar_one_or_none()
                
                if not primary_config:
                    raise ValueError(
                        f"No property configuration found for endpoint '{endpoint_name}'"
                    )
                logger.warning(
                    f"No primary identifier config found, using first available: "
                    f"{primary_config.ontology_type}"
                )
            
            # Extract column name from the property configuration
            extraction_config = primary_config.property_extraction_config
            if not extraction_config:
                raise ValueError(
                    f"No extraction configuration found for endpoint '{endpoint_name}'"
                )
            
            extraction_pattern = json.loads(extraction_config.extraction_pattern)
            
            # Determine column name based on extraction method
            if extraction_config.extraction_method == 'column':
                column_name = extraction_pattern.get('column')
            else:
                # For simple patterns, the pattern itself might be the column name
                column_name = extraction_pattern
            
            if not column_name:
                raise ValueError(
                    f"Could not determine column name from extraction config for '{endpoint_name}'"
                )
            
            logger.info(
                f"Loading column '{column_name}' (ontology: {primary_config.ontology_type}) "
                f"from endpoint '{endpoint_name}'"
            )
            
            # Use CSVAdapter to load the data
            adapter = CSVAdapter(endpoint=endpoint)
            df = await adapter.load_data(columns_to_load=[column_name])
            
            # Extract unique identifiers from the specified column
            if df.empty:
                identifiers = []
            else:
                # Get unique values, removing any None/NaN values
                identifiers = df[column_name].dropna().unique().tolist()
                # Convert to strings and clean
                identifiers = [str(id).strip() for id in identifiers if str(id).strip()]
            
            logger.info(
                f"Loaded {len(identifiers)} unique identifiers from '{endpoint_name}'"
            )
            
            # Store identifiers in context under the specified key
            context[output_context_key] = identifiers
            
            # Also store the ontology type for reference
            context[f"{output_context_key}_ontology"] = primary_config.ontology_type
            
            logger.info(
                f"Stored {len(identifiers)} identifiers in context key '{output_context_key}'"
            )
            
            # Return result in expected format
            return {
                'input_identifiers': [],  # No input identifiers for this action
                'output_identifiers': identifiers,
                'output_ontology_type': primary_config.ontology_type,
                'provenance': [{
                    'action': 'LoadEndpointIdentifiersAction',
                    'endpoint': endpoint_name,
                    'column': column_name,
                    'count': len(identifiers)
                }],
                'details': {
                    'endpoint_name': endpoint_name,
                    'output_context_key': output_context_key,
                    'loaded_count': len(identifiers)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to load identifiers from endpoint '{endpoint_name}': {e}")
            raise
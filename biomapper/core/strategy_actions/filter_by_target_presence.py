"""Filter identifiers based on presence in target endpoint."""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("FILTER_IDENTIFIERS_BY_TARGET_PRESENCE")
class FilterByTargetPresenceAction(StrategyAction):
    """
    Filter a list of identifiers, retaining only those that are
    present in the target endpoint's data.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
    
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
        Filter identifiers by target presence.
        
        Required action_params:
            - endpoint_context: Must be "TARGET"
            - ontology_type_to_match: Ontology type to check in target
            - conversion_path_to_match_ontology (optional): Path to convert identifiers before checking
        """
        # Validate parameters
        endpoint_context = action_params.get('endpoint_context')
        if endpoint_context != 'TARGET':
            raise ValueError(f"endpoint_context must be 'TARGET', got: {endpoint_context}")
        
        ontology_type_to_match = action_params.get('ontology_type_to_match')
        if not ontology_type_to_match:
            raise ValueError("ontology_type_to_match is required")
        
        self.logger.info(
            f"Filtering identifiers by presence in target endpoint ({target_endpoint.name}) "
            f"for ontology type: {ontology_type_to_match}"
        )
        
        # Get the endpoint's data loader
        from biomapper.mapping.adapters.csv_adapter import CSVAdapter
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from biomapper.db.models import EndpointPropertyConfig
        
        # Find property configuration for the target ontology type
        # Eagerly load the property_extraction_config relationship to avoid lazy loading issues
        stmt = (
            select(EndpointPropertyConfig)
            .options(selectinload(EndpointPropertyConfig.property_extraction_config))
            .where(
                EndpointPropertyConfig.endpoint_id == target_endpoint.id,
                EndpointPropertyConfig.ontology_type == ontology_type_to_match
            )
        )
        result = await self.session.execute(stmt)
        property_config = result.scalar_one_or_none()
        
        if not property_config:
            raise ValueError(
                f"Target endpoint {target_endpoint.name} does not have configuration "
                f"for ontology type: {ontology_type_to_match}"
            )
        
        # Load the target endpoint data with selective column loading
        adapter = CSVAdapter(endpoint=target_endpoint)
        
        # Get the column name for the ontology type
        # For column extraction method, parse the column name from JSON extraction_pattern
        
        extraction_pattern = json.loads(property_config.property_extraction_config.extraction_pattern)
        if property_config.property_extraction_config.extraction_method == 'column':
            target_col = extraction_pattern.get('column')
        else:
            # For other methods, might need different parsing
            target_col = extraction_pattern
        
        # Load only the column we need for filtering
        self.logger.info(f"Loading only required column for filtering: {target_col}")
        target_data = await adapter.load_data(columns_to_load=[target_col])
        
        # Create a set of all values in the target column
        target_identifiers_set: Set[str] = set()
        for _, row in target_data.iterrows():
            value = str(row.get(target_col, '')).strip()
            if value:
                target_identifiers_set.add(value)
        
        self.logger.info(
            f"Loaded {len(target_identifiers_set)} unique identifiers from target endpoint"
        )
        
        # Check if we need to convert identifiers before filtering
        conversion_path = action_params.get('conversion_path_to_match_ontology')
        identifiers_to_check = current_identifiers
        identifier_mapping = {id: id for id in current_identifiers}  # Default 1:1 mapping
        
        if conversion_path:
            self.logger.info(f"Converting identifiers using path: {conversion_path}")
            # Use ExecuteMappingPathAction to convert
            from .execute_mapping_path import ExecuteMappingPathAction
            
            mapping_action = ExecuteMappingPathAction(self.session)
            conversion_result = await mapping_action.execute(
                current_identifiers=current_identifiers,
                current_ontology_type=current_ontology_type,
                action_params={'path_name': conversion_path},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Build mapping from original to converted identifiers
            identifier_mapping = {}
            for prov in conversion_result['provenance']:
                if prov.get('target_id'):
                    identifier_mapping[prov['source_id']] = prov['target_id']
            
            identifiers_to_check = conversion_result['output_identifiers']
        
        # Now filter based on presence in target
        output_identifiers = []
        provenance = []
        filtered_count = 0
        
        for original_id in current_identifiers:
            # Get the identifier to check (might be converted)
            check_id = identifier_mapping.get(original_id, original_id)
            
            if check_id in target_identifiers_set:
                output_identifiers.append(original_id)
                provenance.append({
                    'source_id': original_id,
                    'action': 'filter_passed',
                    'target_endpoint': target_endpoint.name,
                    'ontology_type_checked': ontology_type_to_match,
                    'checked_value': check_id if check_id != original_id else None
                })
            else:
                filtered_count += 1
                provenance.append({
                    'source_id': original_id,
                    'action': 'filter_failed',
                    'target_endpoint': target_endpoint.name,
                    'ontology_type_checked': ontology_type_to_match,
                    'reason': 'not_found_in_target',
                    'checked_value': check_id if check_id != original_id else None
                })
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': current_ontology_type,  # Type doesn't change
            'provenance': provenance,
            'details': {
                'action': 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE',
                'target_endpoint': target_endpoint.name,
                'ontology_type_checked': ontology_type_to_match,
                'total_input': len(current_identifiers),
                'total_passed': len(output_identifiers),
                'total_filtered': filtered_count
            }
        }
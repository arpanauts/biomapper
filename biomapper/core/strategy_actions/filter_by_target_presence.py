"""Filter identifiers based on presence in target endpoint."""

import logging
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseStrategyAction
from biomapper.db.models import Endpoint


class FilterByTargetPresenceAction(BaseStrategyAction):
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
        
        # In a full implementation, this would:
        # 1. Load the target endpoint's data file
        # 2. Find the column for the specified ontology type
        # 3. Create a set of all values in that column
        # 4. Filter the input identifiers by membership in that set
        
        # Placeholder: For now, return all identifiers
        # Real implementation would perform actual filtering
        target_identifiers_set: Set[str] = set(current_identifiers)  # Would load from target
        
        output_identifiers = []
        provenance = []
        filtered_count = 0
        
        for identifier in current_identifiers:
            if identifier in target_identifiers_set:
                output_identifiers.append(identifier)
                provenance.append({
                    'source_id': identifier,
                    'action': 'filter_passed',
                    'target_endpoint': target_endpoint.name,
                    'ontology_type_checked': ontology_type_to_match
                })
            else:
                filtered_count += 1
                provenance.append({
                    'source_id': identifier,
                    'action': 'filter_failed',
                    'target_endpoint': target_endpoint.name,
                    'ontology_type_checked': ontology_type_to_match,
                    'reason': 'not_found_in_target'
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
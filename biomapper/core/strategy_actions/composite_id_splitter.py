"""
Splits composite protein identifiers into individual components.

This action:
- Splits protein IDs containing multiple UniProt IDs (e.g., Q14213_Q8NEV9)
- Handles custom delimiters for splitting
- Tracks metadata lineage if requested
- Preserves unique identifiers only
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint


@register_action("COMPOSITE_ID_SPLITTER")
class CompositeIdSplitter(BaseStrategyAction):
    """
    Splits composite protein identifiers into individual components.
    
    Required parameters:
    - input_context_key: Key in context to read identifiers from
    - output_context_key: Key in context to store split identifiers
    - delimiter: Character(s) to split on (default: '_')
    
    Optional parameters:
    - track_metadata_lineage: Store mapping from composite to split IDs (default: False)
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
        Execute the composite ID splitting action.
        
        Args:
            current_identifiers: Current list of identifiers (not used directly)
            current_ontology_type: Current ontology type
            action_params: Parameters for this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Standard action result dictionary
        """
        # Validate required parameters
        input_key = action_params.get('input_context_key')
        output_key = action_params.get('output_context_key')
        delimiter = action_params.get('delimiter', '_')
        
        if not input_key:
            raise ValueError("input_context_key is required")
        if not output_key:
            raise ValueError("output_context_key is required")
            
        track_lineage = action_params.get('track_metadata_lineage', False)
        
        # Get identifiers from context
        identifiers = context.get(input_key, [])
        if not identifiers:
            self.logger.warning(f"No identifiers found at context key '{input_key}'")
            return self._empty_result()
            
        self.logger.info(f"Processing {len(identifiers)} identifiers with delimiter '{delimiter}'")
        
        # Process identifiers
        split_identifiers = set()
        lineage_map = {}
        provenance = []
        
        for identifier in identifiers:
            if delimiter in identifier:
                # Split the composite ID
                components = identifier.split(delimiter)
                split_identifiers.update(components)
                
                if track_lineage:
                    lineage_map[identifier] = components
                    
                # Track provenance
                provenance.append({
                    'action': 'composite_split',
                    'input': identifier,
                    'output': components,
                    'delimiter': delimiter
                })
                
                self.logger.debug(f"Split '{identifier}' into {len(components)} components")
            else:
                # Keep non-composite IDs as-is
                split_identifiers.add(identifier)
                
        # Convert back to list
        output_identifiers = list(split_identifiers)
        
        # Store in context
        context[output_key] = output_identifiers
        
        if track_lineage and lineage_map:
            lineage_key = f"{output_key}_lineage"
            context[lineage_key] = lineage_map
            self.logger.debug(f"Stored lineage mapping at '{lineage_key}'")
            
        self.logger.info(f"Split {len(identifiers)} identifiers into {len(output_identifiers)} unique components")
        
        return {
            'input_identifiers': identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': current_ontology_type,  # Type doesn't change
            'provenance': provenance,
            'details': {
                'input_count': len(identifiers),
                'output_count': len(output_identifiers),
                'composite_count': len(lineage_map) if track_lineage else sum(1 for p in provenance if p['action'] == 'composite_split'),
                'delimiter': delimiter,
                'context_keys': {
                    'input': input_key,
                    'output': output_key,
                    'lineage': f"{output_key}_lineage" if track_lineage else None
                }
            }
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return standard empty result."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': None,
            'provenance': [],
            'details': {
                'input_count': 0,
                'output_count': 0,
                'composite_count': 0
            }
        }
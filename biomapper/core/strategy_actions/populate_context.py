"""Populate context with execution metadata for reporting actions."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("POPULATE_CONTEXT")
class PopulateContextAction(StrategyAction):
    """
    Populate context with execution metadata needed by reporting actions.
    
    This action ensures that reporting actions have access to:
    - initial_identifiers: The original input identifiers
    - mapping_results: Final mapping outcomes
    - all_provenance: Complete provenance chain
    - step_results: Results from each step
    
    This is a utility action that should be run before reporting actions.
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
        Populate context with execution metadata.
        
        Action parameters:
            - mode: 'initialize' to set initial values, 'finalize' to compute final results
            - initial_identifiers_key: Context key to read initial identifiers from (for finalize mode)
        """
        mode = action_params.get('mode', 'initialize')
        
        if mode == 'initialize':
            # Store initial identifiers at the beginning of execution
            context['initial_identifiers'] = current_identifiers.copy()
            context['step_results'] = []
            context['all_provenance'] = []
            context['mapping_results'] = {}
            
            self.logger.info(f"Initialized context with {len(current_identifiers)} initial identifiers")
            
        elif mode == 'finalize':
            # Compute final mapping results
            initial_key = action_params.get('initial_identifiers_key', 'initial_identifiers')
            initial_ids = context.get(initial_key, current_identifiers)
            
            # Build mapping results from context data
            mapping_results = {}
            
            # Get all matched pairs from context
            direct_matches = context.get('direct_matches', [])
            all_matches = context.get('all_matches', [])
            
            # Combine all matches
            all_pairs = []
            if isinstance(direct_matches, list):
                all_pairs.extend(direct_matches)
            if isinstance(all_matches, list):
                all_pairs.extend(all_matches)
            
            # Build mapping dictionary
            for source, target in all_pairs:
                if source not in mapping_results:
                    mapping_results[source] = {
                        'mapped_value': target,
                        'confidence': 1.0,
                        'mapping_method': 'strategy_execution',
                        'all_mapped_values': []
                    }
                mapping_results[source]['all_mapped_values'].append(target)
            
            # Update final mapped value to be the last one (or could be a list)
            for source, data in mapping_results.items():
                if data['all_mapped_values']:
                    data['final_mapped_value'] = data['all_mapped_values'][-1]
                    data['hop_count'] = len(data['all_mapped_values'])
            
            # Store in context
            context['mapping_results'] = mapping_results
            context['initial_identifiers'] = list(initial_ids)
            
            # Ensure step_results and all_provenance are lists
            if 'step_results' not in context:
                context['step_results'] = []
            if 'all_provenance' not in context:
                context['all_provenance'] = []
            
            self.logger.info(
                f"Finalized context: {len(mapping_results)} mappings from "
                f"{len(initial_ids)} initial identifiers"
            )
        
        # Create provenance entry
        provenance = [{
            'action': 'populate_context',
            'timestamp': datetime.utcnow().isoformat(),
            'mode': mode,
            'details': {
                'initial_count': len(context.get('initial_identifiers', [])),
                'mapping_count': len(context.get('mapping_results', {}))
            }
        }]
        
        # Return identifiers unchanged - this is a utility action
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'POPULATE_CONTEXT',
                'mode': mode,
                'context_populated': True
            }
        }
"""Collect matched target identifiers from context data structures."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("COLLECT_MATCHED_TARGETS")
class CollectMatchedTargetsAction(StrategyAction):
    """
    Collect target identifiers from various match data structures in context.
    
    This action extracts target identifiers from:
    - Direct match pairs (list of tuples)
    - Match objects (list of dicts with target_ids)
    - Other structured match data
    
    It outputs a flat list of unique target identifiers suitable for conversion.
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
        Collect target identifiers from context match structures.
        
        Action parameters:
            - match_sources: List of context keys containing match data [required]
            - output_key: Context key to save collected identifiers (optional)
        """
        match_sources = action_params.get('match_sources', [])
        output_key = action_params.get('output_key')
        
        if not match_sources:
            raise ValueError("match_sources parameter is required")
        
        self.logger.info(f"Collecting matched targets from {len(match_sources)} sources")
        
        # Collect all target identifiers
        all_targets = set()
        
        for source_key in match_sources:
            data = context.get(source_key, [])
            
            if not data:
                self.logger.debug(f"No data found in context['{source_key}']")
                continue
                
            self.logger.debug(f"Processing {len(data)} items from context['{source_key}']")
            
            # Handle different data structures
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    # Direct match pair (source, target)
                    all_targets.add(item[1])
                elif isinstance(item, dict):
                    # Match object with target_ids
                    if 'target_ids' in item:
                        all_targets.update(item['target_ids'])
                    elif 'target_id' in item:
                        all_targets.add(item['target_id'])
                    elif 'mapped_value' in item:
                        all_targets.add(item['mapped_value'])
                elif isinstance(item, str):
                    # Direct identifier
                    all_targets.add(item)
                else:
                    self.logger.warning(f"Unrecognized match format: {type(item)}")
        
        # Convert to sorted list
        output_identifiers = sorted(list(all_targets))
        
        self.logger.info(f"Collected {len(output_identifiers)} unique target identifiers")
        
        # Save to context if requested
        if output_key:
            context[output_key] = output_identifiers
            self.logger.debug(f"Saved to context['{output_key}']")
        
        # Create provenance
        provenance = [{
            'action': 'collect_matched_targets',
            'timestamp': datetime.utcnow().isoformat(),
            'sources_processed': len(match_sources),
            'targets_collected': len(output_identifiers),
            'details': {
                'match_sources': match_sources,
                'output_key': output_key
            }
        }]
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'COLLECT_MATCHED_TARGETS',
                'sources_processed': len(match_sources),
                'total_collected': len(output_identifiers)
            }
        }
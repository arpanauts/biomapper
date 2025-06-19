"""
Strategy action to reconcile bidirectional mapping results.

This action combines the results from forward (source to target) and 
reverse (target to source) mapping to create a comprehensive mapping
that includes matches found in both directions.
"""

import logging
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import StrategyAction

logger = logging.getLogger(__name__)


class ReconcileBidirectionalAction(StrategyAction):
    def __init__(self, db_session: AsyncSession):
        """Initialize the action with a database session."""
        self.db_session = db_session
    """
    Action that reconciles forward and reverse mapping results.
    
    This action is used in bidirectional mapping strategies to combine
    results from both mapping directions, ensuring maximum coverage by
    including matches found in either direction.
    """
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint,
        target_endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconcile forward and reverse mapping results.
        
        Args:
            current_identifiers: Not used for this action
            current_ontology_type: Not used for this action
            action_params: Action parameters including:
                - forward_context_prefix: Prefix for forward mapping results in context
                - reverse_context_prefix: Prefix for reverse mapping results in context
                - reconciled_context_key: Key to store reconciled results in context
            source_endpoint: Source endpoint configuration
            target_endpoint: Target endpoint configuration
            context: Strategy execution context containing mapping results
            
        Returns:
            Result dictionary with reconciled mappings
        """
        # Get parameters
        forward_prefix = action_params.get('forward_context_prefix', 'forward')
        reverse_prefix = action_params.get('reverse_context_prefix', 'reverse')
        reconciled_key = action_params.get('reconciled_context_key', 'reconciled_results')
        
        logger.info("Reconciling bidirectional mapping results")
        
        # Get forward and reverse results from context
        forward_results = context.get(f"{forward_prefix}_results", {})
        reverse_results = context.get(f"{reverse_prefix}_results", {})
        
        # Initialize reconciled mappings
        reconciled_mappings = {}
        
        # Add all forward mappings
        for source_id, target_info in forward_results.items():
            if isinstance(target_info, dict) and target_info.get('mapped_value'):
                reconciled_mappings[source_id] = {
                    'source_id': source_id,
                    'target_id': target_info['mapped_value'],
                    'confidence': target_info.get('confidence', 1.0),
                    'direction': 'forward',
                    'source': 'forward_mapping'
                }
        
        # Process reverse mappings
        reverse_lookup = {}
        for target_id, source_info in reverse_results.items():
            if isinstance(source_info, dict) and source_info.get('mapped_value'):
                source_id = source_info['mapped_value']
                
                # Create reverse lookup
                if source_id not in reverse_lookup:
                    reverse_lookup[source_id] = []
                reverse_lookup[source_id].append(target_id)
                
                # If this source wasn't found in forward mapping, add it
                if source_id not in reconciled_mappings:
                    reconciled_mappings[source_id] = {
                        'source_id': source_id,
                        'target_id': target_id,
                        'confidence': source_info.get('confidence', 0.8),  # Slightly lower confidence
                        'direction': 'reverse',
                        'source': 'reverse_mapping'
                    }
        
        # Validate bidirectional consistency
        bidirectionally_validated = set()
        for source_id, mapping in reconciled_mappings.items():
            if mapping['direction'] == 'forward':
                target_id = mapping['target_id']
                # Check if reverse mapping confirms this
                if source_id in reverse_lookup and target_id in reverse_lookup[source_id]:
                    bidirectionally_validated.add(source_id)
                    mapping['bidirectionally_validated'] = True
        
        # Calculate statistics
        total_forward = len([m for m in reconciled_mappings.values() if m['direction'] == 'forward'])
        total_reverse_only = len([m for m in reconciled_mappings.values() if m['direction'] == 'reverse'])
        total_validated = len(bidirectionally_validated)
        
        # Store in context
        context[reconciled_key] = reconciled_mappings
        
        # Create identifier lists for downstream processing
        all_source_ids = list(reconciled_mappings.keys())
        all_target_ids = [m['target_id'] for m in reconciled_mappings.values()]
        
        logger.info(
            f"Reconciliation complete: {len(reconciled_mappings)} total mappings "
            f"({total_forward} forward, {total_reverse_only} reverse-only, "
            f"{total_validated} bidirectionally validated)"
        )
        
        return {
            'output_identifiers': all_target_ids,
            'output_ontology_type': current_ontology_type,
            'details': {
                'total_mappings': len(reconciled_mappings),
                'forward_mappings': total_forward,
                'reverse_only_mappings': total_reverse_only,
                'bidirectionally_validated': total_validated,
                'reconciled_context_key': reconciled_key
            },
            'provenance': [
                {
                    'action': 'reconcile_bidirectional',
                    'source_count': len(all_source_ids),
                    'target_count': len(all_target_ids),
                    'bidirectional_validation': True
                }
            ]
        }
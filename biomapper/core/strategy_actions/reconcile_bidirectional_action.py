"""
ReconcileBidirectionalAction: Reconcile forward and reverse mapping results.

This action reconciles forward and reverse mapping results to create a comprehensive
bidirectional mapping between source and target identifiers.

This action:
- Processes results from source->target mapping
- Processes results from target->source mapping
- Identifies bidirectionally confirmed mappings
- Tracks forward-only and reverse-only mappings
- Generates comprehensive statistics

Usage in YAML strategy:
```yaml
- step_id: "S6_RECONCILE_MAPPINGS"
  description: "Reconcile forward and reverse mappings"
  action:
    type: "BIDIRECTIONAL_RECONCILER"
    forward_mapping_key: "forward_mapping_results"
    reverse_mapping_key: "reverse_mapping_results"
    output_reconciled_key: "reconciled_mappings"
```
"""

import logging
from typing import Dict, Any, List, TYPE_CHECKING
from collections import defaultdict
from datetime import datetime

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@register_action("BIDIRECTIONAL_RECONCILER")
class ReconcileBidirectionalAction(BaseStrategyAction):
    """
    Action that reconciles forward and reverse mapping results.
    
    This action identifies bidirectionally confirmed mappings by comparing
    forward (source->target) and reverse (target->source) mapping results.
    A pair is considered bidirectionally confirmed if A->B exists in the
    forward mapping AND B->A exists in the reverse mapping.
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
        Execute the action to reconcile bidirectional mappings.
        
        Args:
            current_identifiers: Not used by this action
            current_ontology_type: Not used by this action
            action_params: Dictionary containing:
                - forward_mapping_key (str): Context key for source->target results
                - reverse_mapping_key (str): Context key for target->source results  
                - output_reconciled_key (str): Key to store reconciled results in context
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Current execution context containing mapping results
            
        Returns:
            Dictionary containing reconciliation results and provenance
        """
        # Validate required parameters
        forward_mapping_key = action_params.get('forward_mapping_key')
        if not forward_mapping_key:
            raise ValueError("forward_mapping_key is required for ReconcileBidirectionalAction")
        
        reverse_mapping_key = action_params.get('reverse_mapping_key')
        if not reverse_mapping_key:
            raise ValueError("reverse_mapping_key is required for ReconcileBidirectionalAction")
        
        output_reconciled_key = action_params.get('output_reconciled_key')
        if not output_reconciled_key:
            raise ValueError("output_reconciled_key is required for ReconcileBidirectionalAction")
        
        logger.info(
            f"Reconciling mappings from '{forward_mapping_key}' and '{reverse_mapping_key}'"
        )
        
        # Retrieve mapping results from context
        # ExecuteMappingPathAction returns a dict with 'output_identifiers' and 'provenance'
        forward_result = context.get(forward_mapping_key, {})
        reverse_result = context.get(reverse_mapping_key, {})
        
        # Extract provenance records which contain the actual mappings
        forward_provenance = forward_result.get('provenance', []) if isinstance(forward_result, dict) else []
        reverse_provenance = reverse_result.get('provenance', []) if isinstance(reverse_result, dict) else []
        
        logger.debug(f"Found {len(forward_provenance)} forward mappings")
        logger.debug(f"Found {len(reverse_provenance)} reverse mappings")
        
        # Build mapping dictionaries from provenance
        # Forward: source_id -> set of target_ids
        forward_mappings = defaultdict(set)
        for prov in forward_provenance:
            source_id = prov.get('source_id')
            target_id = prov.get('target_id')
            if source_id and target_id:
                forward_mappings[source_id].add(target_id)
        
        # Reverse: target_id -> set of source_ids
        reverse_mappings = defaultdict(set)
        for prov in reverse_provenance:
            # In reverse mapping, the "source" is actually the target endpoint
            source_id = prov.get('source_id')  # This is actually a target ID
            target_id = prov.get('target_id')  # This is actually a source ID
            if source_id and target_id:
                reverse_mappings[source_id].add(target_id)
        
        # Find bidirectionally confirmed mappings
        bidirectional_pairs = []
        forward_only_pairs = []
        reverse_only_pairs = []
        provenance_records = []
        
        # Check all forward mappings
        for source_id, target_ids in forward_mappings.items():
            for target_id in target_ids:
                # Check if this mapping is confirmed in reverse direction
                if target_id in reverse_mappings and source_id in reverse_mappings[target_id]:
                    bidirectional_pairs.append({
                        "source": source_id,
                        "target": target_id,
                        "bidirectional": True,
                        "confidence": 1.0,
                        "mapping_method": "bidirectional_confirmed"
                    })
                    provenance_records.append({
                        "action": "ReconcileBidirectionalAction",
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_id": source_id,
                        "target_id": target_id,
                        "method": "bidirectional_confirmed",
                        "confidence": 1.0,
                        "details": {
                            "found_in_forward": True,
                            "found_in_reverse": True
                        }
                    })
                else:
                    forward_only_pairs.append({
                        "source": source_id,
                        "target": target_id,
                        "bidirectional": False,
                        "confidence": 0.5,
                        "mapping_method": "forward_only"
                    })
                    provenance_records.append({
                        "action": "ReconcileBidirectionalAction",
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_id": source_id,
                        "target_id": target_id,
                        "method": "forward_only",
                        "confidence": 0.5,
                        "details": {
                            "found_in_forward": True,
                            "found_in_reverse": False
                        }
                    })
        
        # Find reverse-only mappings
        for target_id, source_ids in reverse_mappings.items():
            for source_id in source_ids:
                # Check if this pair was already processed
                already_processed = any(
                    pair["source"] == source_id and pair["target"] == target_id
                    for pair in bidirectional_pairs + forward_only_pairs
                )
                if not already_processed:
                    reverse_only_pairs.append({
                        "source": source_id,
                        "target": target_id,
                        "bidirectional": False,
                        "confidence": 0.5,
                        "mapping_method": "reverse_only"
                    })
                    provenance_records.append({
                        "action": "ReconcileBidirectionalAction",
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_id": source_id,
                        "target_id": target_id,
                        "method": "reverse_only",
                        "confidence": 0.5,
                        "details": {
                            "found_in_forward": False,
                            "found_in_reverse": True
                        }
                    })
        
        # Combine all pairs
        all_pairs = bidirectional_pairs + forward_only_pairs + reverse_only_pairs
        
        # Calculate statistics
        statistics = {
            "total_reconciled": len(all_pairs),
            "bidirectionally_confirmed": len(bidirectional_pairs),
            "forward_only_count": len(forward_only_pairs),
            "reverse_only_count": len(reverse_only_pairs),
            "unique_source_ids": len(set(pair["source"] for pair in all_pairs)),
            "unique_target_ids": len(set(pair["target"] for pair in all_pairs)),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Create reconciled result structure
        reconciled_result = {
            "reconciled_pairs": all_pairs,
            "bidirectional_pairs": bidirectional_pairs,
            "forward_only_pairs": forward_only_pairs,
            "reverse_only_pairs": reverse_only_pairs,
            "statistics": statistics,
            "metadata": {
                "forward_mapping_key": forward_mapping_key,
                "reverse_mapping_key": reverse_mapping_key,
                "action": "ReconcileBidirectionalAction"
            }
        }
        
        logger.info(
            f"Reconciliation complete: {statistics['total_reconciled']} total mappings "
            f"({statistics['bidirectionally_confirmed']} bidirectional, "
            f"{statistics['forward_only_count']} forward-only, "
            f"{statistics['reverse_only_count']} reverse-only)"
        )
        
        # Store reconciled result in context
        context[output_reconciled_key] = reconciled_result
        logger.info(f"Stored reconciled results in context key '{output_reconciled_key}'")
        
        # Extract unique identifiers for output
        # Since this is a reconciliation action, we output the unique source identifiers
        # that have any kind of mapping (bidirectional, forward-only, or reverse-only)
        output_identifiers = sorted(list(set(pair["source"] for pair in all_pairs)))
        
        # Return the standard action result format
        return {
            "input_identifiers": current_identifiers,  # Pass through input
            "output_identifiers": output_identifiers,
            "output_ontology_type": current_ontology_type,  # Ontology type doesn't change
            "provenance": provenance_records,
            "details": {
                "statistics": statistics,
                "reconciled_result_key": output_reconciled_key
            }
        }
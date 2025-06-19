"""
ReconcileBidirectionalAction: Reconcile forward and reverse mapping results.

This action reconciles forward and reverse mapping results to create a comprehensive
bidirectional mapping between source and target identifiers.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING
from collections import defaultdict
from datetime import datetime

from biomapper.core.strategy_actions.base import BaseStrategyAction

if TYPE_CHECKING:
    from biomapper.core.mapping_executor import MappingExecutor

logger = logging.getLogger(__name__)


class ReconcileBidirectionalAction(BaseStrategyAction):
    """
    Action that reconciles forward and reverse mapping results.
    
    This action:
    - Processes results from source->target mapping
    - Processes results from target->source mapping
    - Identifies bidirectionally confirmed mappings
    - Tracks forward-only and reverse-only mappings
    - Generates comprehensive statistics
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize the action with parameters.
        
        Args:
            params: Dictionary containing:
                - forward_mapping_key (str): Context key for source->target results
                - reverse_mapping_key (str): Context key for target->source results  
                - output_reconciled_key (str): Key to store reconciled results in context
        """
        self.params = params
        
        # Validate required parameters
        self.forward_mapping_key = params.get('forward_mapping_key')
        if not self.forward_mapping_key:
            raise ValueError("forward_mapping_key is required for ReconcileBidirectionalAction")
        
        self.reverse_mapping_key = params.get('reverse_mapping_key')
        if not self.reverse_mapping_key:
            raise ValueError("reverse_mapping_key is required for ReconcileBidirectionalAction")
        
        self.output_reconciled_key = params.get('output_reconciled_key')
        if not self.output_reconciled_key:
            raise ValueError("output_reconciled_key is required for ReconcileBidirectionalAction")
    
    async def execute(self, context: Dict[str, Any], executor: 'MappingExecutor') -> Dict[str, Any]:
        """
        Execute the action to reconcile bidirectional mappings.
        
        Args:
            context: Current execution context containing mapping results
            executor: MappingExecutor instance
            
        Returns:
            Updated context with reconciled results
        """
        logger.info(
            f"Reconciling mappings from '{self.forward_mapping_key}' and '{self.reverse_mapping_key}'"
        )
        
        # Retrieve mapping results from context
        # ExecuteMappingPathAction returns a dict with 'output_identifiers' and 'provenance'
        forward_result = context.get(self.forward_mapping_key, {})
        reverse_result = context.get(self.reverse_mapping_key, {})
        
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
                else:
                    forward_only_pairs.append({
                        "source": source_id,
                        "target": target_id,
                        "bidirectional": False,
                        "confidence": 0.5,
                        "mapping_method": "forward_only"
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
                "forward_mapping_key": self.forward_mapping_key,
                "reverse_mapping_key": self.reverse_mapping_key,
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
        context[self.output_reconciled_key] = reconciled_result
        logger.info(f"Stored reconciled results in context key '{self.output_reconciled_key}'")
        
        # Return the updated context
        return context
"""
RESOLVE_AND_MATCH_REVERSE action - resolves target identifiers and matches to source.

This is the reverse direction of RESOLVE_AND_MATCH_FORWARD. It resolves target
identifiers via UniProt Historical API and matches them against remaining source
identifiers, maximizing match coverage for bidirectional mapping strategies.
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

from .base import BaseStrategyAction
from biomapper.db.models import Endpoint
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

logger = logging.getLogger(__name__)


class ResolveAndMatchReverse(BaseStrategyAction):
    """
    Resolves target identifiers via UniProt Historical API and matches to source.
    
    This action:
    - Reads unmatched target identifiers from context
    - Resolves them via UniProt Historical API
    - Matches resolved IDs against remaining source identifiers
    - Handles composite identifiers by default
    - Supports many-to-many mappings
    - Tracks detailed provenance of reverse matches
    
    Parameters:
        input_from (str): Context key for target IDs to resolve (default: 'unmatched_target')
        match_against_remaining (str): Context key for remaining source IDs (default: 'unmatched_source')
        resolver (str): Resolver type to use (default: 'UNIPROT_HISTORICAL_API')
        source_ontology (str): Required - ontology type in source dataset
        append_matched_to (str): Context key to append matches to (default: 'all_matches')
        save_final_unmatched (str): Context key for final unmatched IDs (default: 'final_unmatched')
        composite_handling (str): How to handle composite IDs (default: 'split_and_match')
        match_mode (str): Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        batch_size (int): Batch size for API calls (default: 100)
    """
    
    def __init__(self, session):
        """Initialize with database session."""
        self.session = session
        self._resolver_client = None
        
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
        Execute the reverse resolution and matching action.
        
        Args:
            current_identifiers: List of identifiers to process (typically empty)
            current_ontology_type: Current ontology type of the identifiers
            action_params: Parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Dictionary containing:
                - input_identifiers: List of input identifiers
                - output_identifiers: List of output identifiers
                - output_ontology_type: Ontology type of output
                - provenance: List of provenance records
                - details: Additional execution details
                
        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If action execution fails
        """
        # Extract parameters
        input_from = action_params.get('input_from', 'unmatched_target')
        match_against_remaining = action_params.get('match_against_remaining', 'unmatched_source')
        resolver = action_params.get('resolver', 'UNIPROT_HISTORICAL_API')
        source_ontology = action_params.get('source_ontology')
        append_matched_to = action_params.get('append_matched_to', 'all_matches')
        save_final_unmatched = action_params.get('save_final_unmatched', 'final_unmatched')
        composite_handling = action_params.get('composite_handling', 'split_and_match')
        match_mode = action_params.get('match_mode', 'many_to_many')
        batch_size = action_params.get('batch_size', 100)
        
        # Validate required parameters
        if not source_ontology:
            raise ValueError("source_ontology is required")
            
        # Get target IDs to resolve and source IDs to match against
        unmatched_target = context.get(input_from, [])
        remaining_source = context.get(match_against_remaining, [])
        
        # Early exit for empty input
        if not unmatched_target or not remaining_source:
            logger.info(
                f"RESOLVE_AND_MATCH_REVERSE: No identifiers to process "
                f"(target: {len(unmatched_target)}, source: {len(remaining_source)})"
            )
            return self._empty_result()
            
        # Log action start
        logger.info(
            f"Executing RESOLVE_AND_MATCH_REVERSE with {len(unmatched_target)} target IDs "
            f"to match against {len(remaining_source)} source IDs, "
            f"mode: {match_mode}, composite handling: {composite_handling}"
        )
        logger.debug(f"Action parameters: {action_params}")
        logger.debug(f"First 5 target IDs: {unmatched_target[:5]}")
        logger.debug(f"First 5 source IDs: {remaining_source[:5]}")
        
        # Initialize tracking
        matched_pairs = []  # List of (source_id, target_id) tuples
        provenance_records = []
        still_unmatched_source = set(remaining_source)
        still_unmatched_target = set(unmatched_target)
        resolved_count = 0
        match_count = 0
        
        try:
            # Step 1: Handle composite identifiers if needed
            expanded_target = unmatched_target
            expanded_source = remaining_source
            
            if composite_handling != 'none':
                expanded_target = self._handle_composites(
                    unmatched_target, 
                    composite_handling
                )
                expanded_source = self._handle_composites(
                    remaining_source,
                    composite_handling
                )
                logger.debug(
                    f"Expanded {len(unmatched_target)} target IDs to {len(expanded_target)}, "
                    f"{len(remaining_source)} source IDs to {len(expanded_source)} "
                    f"after composite handling"
                )
            
            # Create mapping from expanded to original IDs
            expanded_to_original_target = self._create_expansion_map(unmatched_target, expanded_target)
            expanded_to_original_source = self._create_expansion_map(remaining_source, expanded_source)
            
            # Step 2: Initialize resolver client
            if not self._resolver_client:
                self._resolver_client = UniProtHistoricalResolverClient()
                
            # Step 3: Resolve target IDs in batches
            logger.info(f"Resolving {len(expanded_target)} target identifiers via {resolver}")
            
            # Create reverse lookup: resolved_id -> original_target_ids
            reverse_lookup = defaultdict(set)
            
            for i in range(0, len(expanded_target), batch_size):
                batch = expanded_target[i:i + batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1} with {len(batch)} IDs")
                
                try:
                    # Call the resolver
                    resolution_results = await self._resolver_client.map_identifiers(batch)
                    
                    # Process resolution results
                    for target_id, (resolved_ids, metadata) in resolution_results.items():
                        if resolved_ids:
                            resolved_count += 1
                            # Map each resolved ID back to the original target
                            for resolved_id in resolved_ids:
                                # Get original target IDs this expanded ID came from
                                original_targets = expanded_to_original_target.get(target_id, {target_id})
                                reverse_lookup[resolved_id].update(original_targets)
                                
                            # Create provenance for resolution
                            for original_target in expanded_to_original_target.get(target_id, {target_id}):
                                provenance_records.append({
                                    'action': 'RESOLVE_AND_MATCH_REVERSE',
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'input': original_target,
                                    'resolved_to': resolved_ids,
                                    'method': f'{resolver}_resolution',
                                    'metadata': metadata,
                                    'details': {
                                        'resolver': resolver,
                                        'direction': 'reverse'
                                    }
                                })
                                
                except Exception as e:
                    logger.warning(f"Failed to resolve batch {i//batch_size + 1}: {e}")
                    
            logger.info(f"Resolved {resolved_count} of {len(expanded_target)} target identifiers")
            logger.debug(f"Reverse lookup has {len(reverse_lookup)} unique resolved IDs")
            
            # Step 4: Match resolved target IDs against remaining source IDs
            logger.info("Matching resolved target IDs against remaining source IDs")
            
            # Convert source list to set for O(1) lookup
            source_set = set(expanded_source)
            
            # Track used items for one-to-one mode
            used_sources = set()
            used_targets = set()
            
            for resolved_id, original_targets in reverse_lookup.items():
                if resolved_id in source_set:
                    # Found a match!
                    match_count += 1
                    
                    # Get original source IDs this resolved ID maps to
                    original_sources = expanded_to_original_source.get(resolved_id, {resolved_id})
                    
                    # Create matches for all combinations (if many-to-many)
                    match_found = False
                    for source_id in original_sources:
                        if match_mode == 'one_to_one' and source_id in used_sources:
                            continue
                            
                        for target_id in original_targets:
                            if match_mode == 'one_to_one' and target_id in used_targets:
                                continue
                                
                            matched_pairs.append((source_id, target_id))
                            
                            # Remove from unmatched sets
                            still_unmatched_source.discard(source_id)
                            still_unmatched_target.discard(target_id)
                            
                            # Track used items for one-to-one mode
                            if match_mode == 'one_to_one':
                                used_sources.add(source_id)
                                used_targets.add(target_id)
                            
                            # Create provenance for match
                            provenance_records.append({
                                'action': 'RESOLVE_AND_MATCH_REVERSE',
                                'timestamp': datetime.utcnow().isoformat(),
                                'source_id': source_id,
                                'target_id': target_id,
                                'resolved_id': resolved_id,
                                'method': 'reverse_resolution_match',
                                'confidence': 1.0,
                                'details': {
                                    'match_direction': 'reverse',
                                    'resolver': resolver,
                                    'source_ontology': source_ontology
                                }
                            })
                            
                            if match_mode == 'one_to_one':
                                # In one-to-one mode, only use first match
                                match_found = True
                                break
                        if match_mode == 'one_to_one' and match_found:
                            break
                            
            # Step 5: Update context with results
            # Append matches to existing matches
            if append_matched_to:
                existing_matches = context.get(append_matched_to, [])
                all_matches = existing_matches + matched_pairs
                context[append_matched_to] = all_matches
                logger.debug(f"Appended {len(matched_pairs)} matches to context['{append_matched_to}']")
                
            # Save final unmatched identifiers
            if save_final_unmatched:
                context[save_final_unmatched] = {
                    'source': list(still_unmatched_source),
                    'target': list(still_unmatched_target)
                }
                logger.debug(
                    f"Saved final unmatched to context['{save_final_unmatched}']: "
                    f"{len(still_unmatched_source)} source, {len(still_unmatched_target)} target"
                )
                
            # Step 6: Build final result
            logger.info(
                f"RESOLVE_AND_MATCH_REVERSE completed: resolved {resolved_count} target IDs, "
                f"found {len(matched_pairs)} matches, "
                f"remaining unmatched: {len(still_unmatched_source)} source, {len(still_unmatched_target)} target"
            )
            
            # Output identifiers are the matched source IDs
            output_identifiers = [pair[0] for pair in matched_pairs]
            
            return {
                'input_identifiers': unmatched_target,  # Original target IDs we tried to resolve
                'output_identifiers': output_identifiers,  # Matched source IDs
                'output_ontology_type': source_ontology,  # Output is in source ontology
                'provenance': provenance_records,
                'details': {
                    'action': 'RESOLVE_AND_MATCH_REVERSE',
                    'total_target_input': len(unmatched_target),
                    'total_source_candidates': len(remaining_source),
                    'total_resolved': resolved_count,
                    'total_matches': len(matched_pairs),
                    'unique_matched_source': len(set(pair[0] for pair in matched_pairs)),
                    'unique_matched_target': len(set(pair[1] for pair in matched_pairs)),
                    'remaining_unmatched_source': len(still_unmatched_source),
                    'remaining_unmatched_target': len(still_unmatched_target),
                    'parameters': action_params,
                    'composite_handling': composite_handling,
                    'match_mode': match_mode,
                    'resolver': resolver
                }
            }
            
        except Exception as e:
            logger.error(f"RESOLVE_AND_MATCH_REVERSE failed: {e}", exc_info=True)
            raise RuntimeError(f"Action execution failed: {e}") from e
            
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for early exit."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': None,
            'provenance': [],
            'details': {
                'action': 'RESOLVE_AND_MATCH_REVERSE',
                'skipped': 'empty_input'
            }
        }
        
    def _handle_composites(
        self, 
        identifiers: List[str], 
        strategy: str = 'split_and_match'
    ) -> List[str]:
        """
        Handle composite identifiers according to strategy.
        
        Args:
            identifiers: List of potentially composite identifiers
            strategy: How to handle composites
                - 'split_and_match': Split and include components
                - 'match_whole': Keep composites as-is
                - 'both': Include both composite and components
                
        Returns:
            Expanded list of identifiers
        """
        if strategy == 'match_whole':
            return identifiers
            
        expanded = []
        delimiter = '_'  # Standard composite delimiter
        
        for identifier in identifiers:
            # Always include original
            if strategy == 'both' or delimiter not in identifier:
                expanded.append(identifier)
                
            # Add components if composite
            if delimiter in identifier and strategy in ('split_and_match', 'both'):
                components = identifier.split(delimiter)
                expanded.extend(components)
                
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for item in expanded:
            if item not in seen:
                seen.add(item)
                result.append(item)
                
        return result
        
    def _create_expansion_map(
        self, 
        original_ids: List[str], 
        expanded_ids: List[str]
    ) -> Dict[str, Set[str]]:
        """
        Create a mapping from expanded IDs back to their original IDs.
        
        Args:
            original_ids: Original list of identifiers
            expanded_ids: Expanded list after composite handling
            
        Returns:
            Dictionary mapping expanded ID -> set of original IDs it came from
        """
        expansion_map = defaultdict(set)
        delimiter = '_'
        
        for original_id in original_ids:
            # Map the original to itself
            expansion_map[original_id].add(original_id)
            
            # If it's a composite, map its components too
            if delimiter in original_id:
                components = original_id.split(delimiter)
                for component in components:
                    expansion_map[component].add(original_id)
                    
        return dict(expansion_map)
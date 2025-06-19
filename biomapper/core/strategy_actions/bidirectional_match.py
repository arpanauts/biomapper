"""
Bidirectional match action for intelligent matching between source and target endpoints.

This action performs bidirectional matching with support for:
- Composite identifier handling
- Many-to-many mapping relationships
- Tracking of matched and unmatched identifiers
"""

import logging
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
from datetime import datetime

from .base import StrategyAction
from .registry import register_action
from biomapper.db.models import Endpoint

logger = logging.getLogger(__name__)


@register_action("BIDIRECTIONAL_MATCH")
class BidirectionalMatchAction(StrategyAction):
    """
    Performs intelligent bidirectional matching between source and target endpoints.
    
    This action:
    - Loads data from both endpoints for specified ontology types
    - Handles composite identifiers by default (e.g., Q14213_Q8NEV9)
    - Performs matching based on configurable match_mode
    - Tracks matched pairs and unmatched identifiers from both sides
    - Supports many-to-many and one-to-one matching modes
    
    Parameters:
        source_ontology (str): Required - ontology type in source endpoint
        target_ontology (str): Required - ontology type in target endpoint
        match_mode (str): Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        composite_handling (str): How to handle composite IDs - 'split_and_match', 'match_whole', 'both' (default: 'split_and_match')
        track_unmatched (bool): Whether to track unmatched identifiers (default: True)
        save_matched_to (str): Context key to save matched pairs (default: 'matched_identifiers')
        save_unmatched_source_to (str): Context key for unmatched source IDs (default: 'unmatched_source')
        save_unmatched_target_to (str): Context key for unmatched target IDs (default: 'unmatched_target')
    """
    
    def __init__(self, session):
        """Initialize with database session."""
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
        Execute bidirectional matching.
        
        Args:
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type of the identifiers
            action_params: Parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Dictionary containing:
                - input_identifiers: List of input identifiers
                - output_identifiers: List of matched identifiers
                - output_ontology_type: Ontology type of output
                - provenance: List of provenance records
                - details: Additional execution details
                
        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If action execution fails
        """
        # Early exit for empty input
        if not current_identifiers:
            return self._empty_result()
            
        # Validate required parameters
        source_ontology = action_params.get('source_ontology')
        target_ontology = action_params.get('target_ontology')
        
        if not source_ontology:
            raise ValueError("source_ontology is required")
        if not target_ontology:
            raise ValueError("target_ontology is required")
            
        # Extract optional parameters with defaults
        match_mode = action_params.get('match_mode', 'many_to_many')
        composite_handling = action_params.get('composite_handling', 'split_and_match')
        track_unmatched = action_params.get('track_unmatched', True)
        save_matched_to = action_params.get('save_matched_to', 'matched_identifiers')
        save_unmatched_source_to = action_params.get('save_unmatched_source_to', 'unmatched_source')
        save_unmatched_target_to = action_params.get('save_unmatched_target_to', 'unmatched_target')
        
        # Log action start
        logger.info(
            f"Executing BIDIRECTIONAL_MATCH with {len(current_identifiers)} identifiers, "
            f"mode: {match_mode}, composite handling: {composite_handling}"
        )
        logger.debug(f"Action parameters: {action_params}")
        logger.debug(f"First 5 identifiers: {current_identifiers[:5]}")
        
        # Initialize tracking
        matched_pairs = []
        provenance_records = []
        
        try:
            # Step 1: Load data from both endpoints
            source_data = await self._load_endpoint_data(source_endpoint, source_ontology)
            target_data = await self._load_endpoint_data(target_endpoint, target_ontology)
            
            logger.info(
                f"Loaded {len(source_data)} identifiers from source, "
                f"{len(target_data)} identifiers from target"
            )
            
            # Step 2: Handle composite identifiers if needed
            source_working = self._prepare_identifiers_for_matching(
                list(source_data), composite_handling
            )
            target_working = self._prepare_identifiers_for_matching(
                list(target_data), composite_handling
            )
            
            # Filter source identifiers to only those in current_identifiers
            current_expanded = self._prepare_identifiers_for_matching(
                current_identifiers, composite_handling
            )
            source_working = {
                'original_to_expanded': {
                    orig: exp for orig, exp in source_working['original_to_expanded'].items()
                    if orig in current_identifiers or any(e in current_expanded['all_identifiers'] for e in exp)
                },
                'expanded_to_original': source_working['expanded_to_original'],
                'all_identifiers': source_working['all_identifiers'].intersection(current_expanded['all_identifiers'])
            }
            
            # Step 3: Perform matching
            matches = self._perform_matching(
                source_working, 
                target_working,
                match_mode
            )
            
            # Step 4: Extract results
            for source_orig, target_orig in matches:
                matched_pairs.append((source_orig, target_orig))
                
                # Create provenance record
                provenance_records.append({
                    'action': 'BIDIRECTIONAL_MATCH',
                    'timestamp': datetime.utcnow().isoformat(),
                    'input': source_orig,
                    'output': target_orig,
                    'confidence': 1.0,
                    'method': f'{match_mode}_match',
                    'details': {
                        'source_ontology': source_ontology,
                        'target_ontology': target_ontology,
                        'composite_handling': composite_handling
                    }
                })
            
            # Step 5: Track unmatched if requested
            unmatched_source = []
            unmatched_target = []
            
            if track_unmatched:
                matched_source_ids = {pair[0] for pair in matched_pairs}
                matched_target_ids = {pair[1] for pair in matched_pairs}
                
                unmatched_source = [
                    id for id in current_identifiers 
                    if id not in matched_source_ids
                ]
                unmatched_target = [
                    id for id in target_data 
                    if id not in matched_target_ids
                ]
            
            # Step 6: Update context
            if save_matched_to:
                context[save_matched_to] = matched_pairs
                logger.info(f"Saved {len(matched_pairs)} matched pairs to context['{save_matched_to}']")
                logger.debug(f"Matched pairs sample: {matched_pairs[:3]}")
                
            if track_unmatched:
                if save_unmatched_source_to:
                    context[save_unmatched_source_to] = unmatched_source
                    logger.info(f"Saved {len(unmatched_source)} unmatched source IDs to context['{save_unmatched_source_to}']")
                    logger.debug(f"Unmatched source sample: {unmatched_source[:5]}")
                    
                if save_unmatched_target_to:
                    context[save_unmatched_target_to] = unmatched_target
                    logger.info(f"Saved {len(unmatched_target)} unmatched target IDs to context['{save_unmatched_target_to}']")
            
            # Extract unique matched target identifiers for output
            output_identifiers = list(set(pair[1] for pair in matched_pairs))
            
            # Step 7: Build final result
            logger.info(
                f"BIDIRECTIONAL_MATCH completed: {len(matched_pairs)} matches found, "
                f"{len(unmatched_source)} unmatched source, {len(unmatched_target)} unmatched target"
            )
            
            return {
                'input_identifiers': current_identifiers,
                'output_identifiers': output_identifiers,
                'output_ontology_type': target_ontology,
                'provenance': provenance_records,
                'details': {
                    'action': 'BIDIRECTIONAL_MATCH',
                    'total_input': len(current_identifiers),
                    'total_matches': len(matched_pairs),
                    'unique_matched_targets': len(output_identifiers),
                    'unmatched_source': len(unmatched_source),
                    'unmatched_target': len(unmatched_target),
                    'parameters': action_params,
                    'composite_handling': composite_handling,
                    'match_mode': match_mode
                }
            }
            
        except Exception as e:
            logger.error(f"BIDIRECTIONAL_MATCH failed: {e}", exc_info=True)
            raise RuntimeError(f"Action execution failed: {e}") from e
            
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for early exit."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': None,
            'provenance': [],
            'details': {
                'action': 'BIDIRECTIONAL_MATCH',
                'skipped': 'empty_input'
            }
        }
        
    async def _load_endpoint_data(
        self,
        endpoint: Endpoint,
        ontology_type: str
    ) -> Set[str]:
        """
        Load identifiers from an endpoint for a specific ontology type.
        
        Args:
            endpoint: Endpoint to load from
            ontology_type: Ontology type to filter by
            
        Returns:
            Set of unique identifiers
        """
        try:
            from biomapper.mapping.adapters.csv_adapter import CSVAdapter
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from biomapper.db.models import EndpointPropertyConfig
            import json
            
            # Find property configuration for the ontology type
            stmt = (
                select(EndpointPropertyConfig)
                .options(selectinload(EndpointPropertyConfig.property_extraction_config))
                .where(
                    EndpointPropertyConfig.endpoint_id == endpoint.id,
                    EndpointPropertyConfig.ontology_type == ontology_type
                )
            )
            result = await self.session.execute(stmt)
            property_config = result.scalar_one_or_none()
            
            if not property_config:
                logger.warning(
                    f"Endpoint {endpoint.name} does not have configuration "
                    f"for ontology type: {ontology_type}"
                )
                return set()
            
            # Get the column name from extraction pattern
            extraction_pattern = json.loads(property_config.property_extraction_config.extraction_pattern)
            if property_config.property_extraction_config.extraction_method == 'column':
                column_name = extraction_pattern.get('column')
            else:
                column_name = extraction_pattern
            
            # Load the endpoint data
            adapter = CSVAdapter(endpoint=endpoint)
            logger.debug(f"Loading column '{column_name}' from {endpoint.name}")
            df = await adapter.load_data(columns_to_load=[column_name])
            
            # Extract unique identifiers
            if df.empty:
                return set()
                
            identifiers = set()
            for _, row in df.iterrows():
                value = str(row.get(column_name, '')).strip()
                if value:
                    identifiers.add(value)
            
            logger.debug(f"Loaded {len(identifiers)} unique identifiers from {endpoint.name}")
            return identifiers
                
        except Exception as e:
            logger.error(f"Failed to load data from {endpoint.name}: {e}")
            raise
            
    def _prepare_identifiers_for_matching(
        self,
        identifiers: List[str],
        composite_handling: str
    ) -> Dict[str, Any]:
        """
        Prepare identifiers for matching, handling composites as needed.
        
        Returns a structure that tracks:
        - Original to expanded mappings
        - Expanded to original mappings
        - All unique identifiers for matching
        """
        original_to_expanded = {}
        expanded_to_original = defaultdict(set)
        all_identifiers = set()
        
        delimiter = '_'
        
        for identifier in identifiers:
            expanded = []
            
            if composite_handling == 'match_whole':
                expanded = [identifier]
            elif composite_handling == 'split_and_match':
                if delimiter in identifier:
                    expanded = identifier.split(delimiter)
                else:
                    expanded = [identifier]
            elif composite_handling == 'both':
                expanded = [identifier]
                if delimiter in identifier:
                    expanded.extend(identifier.split(delimiter))
            
            original_to_expanded[identifier] = expanded
            for exp in expanded:
                expanded_to_original[exp].add(identifier)
                all_identifiers.add(exp)
        
        return {
            'original_to_expanded': original_to_expanded,
            'expanded_to_original': dict(expanded_to_original),
            'all_identifiers': all_identifiers
        }
        
    def _perform_matching(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        match_mode: str
    ) -> List[Tuple[str, str]]:
        """
        Perform the actual matching between source and target identifiers.
        
        Returns list of (source_original, target_original) tuples.
        """
        matches = []
        
        # Find intersection at the expanded level
        common_expanded = source_data['all_identifiers'].intersection(
            target_data['all_identifiers']
        )
        
        logger.debug(f"Found {len(common_expanded)} common expanded identifiers")
        
        if match_mode == 'many_to_many':
            # Use a set to avoid duplicates
            matches_set = set()
            
            # For each common expanded identifier, create all possible original pairs
            for expanded_id in common_expanded:
                source_originals = source_data['expanded_to_original'].get(expanded_id, set())
                target_originals = target_data['expanded_to_original'].get(expanded_id, set())
                
                for source_orig in source_originals:
                    for target_orig in target_originals:
                        matches_set.add((source_orig, target_orig))
            
            matches = list(matches_set)
                        
        elif match_mode == 'one_to_one':
            # For one-to-one, we need to be more selective
            # Match each source to at most one target
            used_targets = set()
            
            for expanded_id in common_expanded:
                source_originals = source_data['expanded_to_original'].get(expanded_id, set())
                target_originals = target_data['expanded_to_original'].get(expanded_id, set())
                
                # Sort for consistent behavior
                source_originals = sorted(source_originals)
                target_originals = sorted(target_originals)
                
                for source_orig in source_originals:
                    # Find first unused target
                    for target_orig in target_originals:
                        if target_orig not in used_targets:
                            matches.append((source_orig, target_orig))
                            used_targets.add(target_orig)
                            break
        
        return matches
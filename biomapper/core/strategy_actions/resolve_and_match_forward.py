"""
Resolve source identifiers via UniProt Historical API and match against target.

This action reads unmatched identifiers from context, resolves them to current
IDs using the UniProt Historical Resolver, and performs matching with composite/M2M support.
"""

import logging
from typing import Dict, Any, List, Set
from collections import defaultdict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction
from .registry import register_action
from biomapper.db.models import Endpoint
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

logger = logging.getLogger(__name__)


@register_action("RESOLVE_AND_MATCH_FORWARD")
class ResolveAndMatchForwardAction(StrategyAction):
    """
    Resolve historical/secondary identifiers and match against target.
    
    This action:
    - Reads identifiers from context (default: 'unmatched_source')
    - Resolves via UniProt API to get current/primary accessions
    - Handles composite identifiers in both input and resolved results
    - Matches resolved IDs against target endpoint
    - Supports many-to-many mappings
    - Updates context with matched and remaining unmatched
    
    Parameters:
        input_from (str): Context key to read from (default: 'unmatched_source')
        match_against (str): Which endpoint to match against (default: 'TARGET')
        resolver (str): Which resolver to use (default: 'UNIPROT_HISTORICAL_API')
        target_ontology (str): Required - ontology type to match in target
        append_matched_to (str): Where to append matches (default: 'all_matches')
        update_unmatched (str): Update unmatched list (default: 'unmatched_source')
        composite_handling (str): How to handle composite IDs (default: 'split_and_match')
        match_mode (str): Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        batch_size (int): Batch size for API calls (default: 100)
    """
    
    def __init__(self, session: AsyncSession):
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
        Execute the resolve and match forward action.
        
        Args:
            current_identifiers: List of identifiers to process (typically empty, reads from context)
            current_ontology_type: Current ontology type of the identifiers
            action_params: Parameters specific to this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Dictionary containing:
                - input_identifiers: List of input identifiers
                - output_identifiers: List of output identifiers (resolved)
                - output_ontology_type: Ontology type of output
                - provenance: List of provenance records
                - details: Additional execution details
                
        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If action execution fails
        """
        # Extract parameters with defaults
        input_from = action_params.get('input_from', 'unmatched_source')
        match_against = action_params.get('match_against', 'TARGET')
        resolver = action_params.get('resolver', 'UNIPROT_HISTORICAL_API')
        target_ontology = action_params.get('target_ontology')
        append_matched_to = action_params.get('append_matched_to', 'all_matches')
        update_unmatched = action_params.get('update_unmatched', 'unmatched_source')
        composite_handling = action_params.get('composite_handling', 'split_and_match')
        match_mode = action_params.get('match_mode', 'many_to_many')
        batch_size = action_params.get('batch_size', 100)
        
        # Validate required parameters
        if not target_ontology:
            raise ValueError("target_ontology is required")
            
        if match_against != 'TARGET':
            raise ValueError(f"match_against must be 'TARGET', got: {match_against}")
            
        if resolver != 'UNIPROT_HISTORICAL_API':
            raise ValueError(f"Only UNIPROT_HISTORICAL_API resolver is supported, got: {resolver}")
        
        # Get identifiers from context or use current_identifiers
        unmatched_ids = context.get(input_from, []) if input_from else current_identifiers
        logger.info(f"Looking for '{input_from}' in context, found: {len(unmatched_ids)} identifiers")
        logger.debug(f"Context keys: {list(context.keys())}")
        
        # Early exit for empty input
        if not unmatched_ids:
            return self._empty_result()
            
        # Log action start
        logger.info(
            f"Executing RESOLVE_AND_MATCH_FORWARD with {len(unmatched_ids)} identifiers, "
            f"resolver: {resolver}, target_ontology: {target_ontology}, "
            f"mode: {match_mode}, composite handling: {composite_handling}"
        )
        logger.debug(f"Action parameters: {action_params}")
        logger.debug(f"First 5 identifiers: {unmatched_ids[:5]}")
        
        # Initialize tracking
        all_matches = []
        still_unmatched = []
        provenance_records = []
        resolved_count = 0
        matched_count = 0
        failed_count = 0
        
        try:
            # Step 1: Handle composite identifiers if needed
            working_identifiers = unmatched_ids
            composite_mapping = {}  # Maps expanded ID back to original
            
            if composite_handling != 'none':
                working_identifiers, composite_mapping = self._handle_composites_with_mapping(
                    unmatched_ids, 
                    composite_handling
                )
                logger.debug(
                    f"Expanded {len(unmatched_ids)} identifiers to "
                    f"{len(working_identifiers)} after composite handling"
                )
            
            # Step 2: Initialize UniProt resolver client
            if not self._resolver_client:
                self._resolver_client = UniProtHistoricalResolverClient(
                    cache_size=10000,
                    timeout=30
                )
            
            # Step 3: Resolve identifiers in batches
            resolved_mappings = {}  # Map from old ID to resolution result
            
            for i in range(0, len(working_identifiers), batch_size):
                batch = working_identifiers[i:i+batch_size]
                logger.info(f"Resolving batch {i//batch_size + 1}/{(len(working_identifiers) + batch_size - 1)//batch_size}")
                
                try:
                    # Call the resolver
                    batch_results = await self._resolver_client.map_identifiers(batch)
                    
                    # Process results
                    for old_id, (primary_ids, metadata) in batch_results.items():
                        resolved_mappings[old_id] = {
                            'current': primary_ids or [],
                            'status': metadata,
                            'resolved': bool(primary_ids)
                        }
                        if primary_ids:
                            resolved_count += 1
                            
                except Exception as e:
                    logger.warning(f"Failed to resolve batch starting at {i}: {e}")
                    # Mark batch as failed
                    for old_id in batch:
                        resolved_mappings[old_id] = {
                            'current': [],
                            'status': f'error:{str(e)}',
                            'resolved': False
                        }
                        failed_count += 1
            
            # Step 4: Load target data for matching
            logger.info(f"Loading target data for ontology type: {target_ontology}")
            target_identifiers = await self._load_target_identifiers(
                target_endpoint,
                target_ontology
            )
            
            # Step 5: Match resolved IDs against target
            matches_by_original = defaultdict(set)  # Original ID -> set of matched target IDs
            
            for old_id, resolution in resolved_mappings.items():
                if resolution['resolved']:
                    # Check each resolved ID against target
                    for resolved_id in resolution['current']:
                        if resolved_id in target_identifiers:
                            # Find original ID(s) this maps back to
                            original_ids = composite_mapping.get(old_id, [old_id])
                            for orig_id in original_ids:
                                matches_by_original[orig_id].add(resolved_id)
                                
                            # Create provenance for successful match
                            provenance_records.append({
                                'action': 'RESOLVE_AND_MATCH_FORWARD',
                                'timestamp': datetime.utcnow().isoformat(),
                                'input': old_id,
                                'resolved_to': resolved_id,
                                'matched_in_target': True,
                                'resolution_status': resolution['status'],
                                'target_ontology': target_ontology,
                                'confidence': 0.9 if resolution['status'] == 'primary' else 0.8,
                                'method': 'uniprot_historical_resolution',
                                'details': {
                                    'resolver': resolver,
                                    'all_resolved_ids': resolution['current']
                                }
                            })
            
            # Step 6: Build final results based on original identifiers
            for orig_id in unmatched_ids:
                if orig_id in matches_by_original:
                    # This ID matched after resolution
                    matched_ids = list(matches_by_original[orig_id])
                    matched_count += 1
                    
                    # Add to matches based on match_mode
                    if match_mode == 'one_to_one' and len(matched_ids) > 1:
                        # Take only first match for one-to-one mode
                        all_matches.append({
                            'source_id': orig_id,
                            'target_ids': [matched_ids[0]],
                            'method': 'resolve_and_match',
                            'confidence': 0.85
                        })
                    else:
                        # Many-to-many mode - include all matches
                        all_matches.append({
                            'source_id': orig_id,
                            'target_ids': matched_ids,
                            'method': 'resolve_and_match',
                            'confidence': 0.85
                        })
                else:
                    # Still unmatched after resolution
                    still_unmatched.append(orig_id)
                    
                    # Add provenance for unmatched
                    provenance_records.append({
                        'action': 'RESOLVE_AND_MATCH_FORWARD',
                        'timestamp': datetime.utcnow().isoformat(),
                        'input': orig_id,
                        'resolved_to': None,
                        'matched_in_target': False,
                        'resolution_status': 'no_match_after_resolution',
                        'target_ontology': target_ontology,
                        'confidence': 0.0,
                        'method': 'uniprot_historical_resolution',
                        'details': {
                            'resolver': resolver
                        }
                    })
            
            # Step 7: Update context
            if append_matched_to:
                existing_matches = context.get(append_matched_to, [])
                context[append_matched_to] = existing_matches + all_matches
                logger.debug(f"Appended {len(all_matches)} matches to context['{append_matched_to}']")
                
            if update_unmatched:
                context[update_unmatched] = still_unmatched
                logger.debug(f"Updated context['{update_unmatched}'] with {len(still_unmatched)} unmatched IDs")
                
            # Step 8: Build final result
            logger.info(
                f"RESOLVE_AND_MATCH_FORWARD completed: resolved {resolved_count}, "
                f"matched {matched_count}, still unmatched {len(still_unmatched)}, "
                f"failed {failed_count}"
            )
            
            # Output identifiers are the resolved IDs that matched
            output_identifiers = []
            for match in all_matches:
                output_identifiers.extend(match['target_ids'])
            
            return {
                'input_identifiers': unmatched_ids,
                'output_identifiers': output_identifiers,
                'output_ontology_type': target_ontology,
                'provenance': provenance_records,
                'details': {
                    'action': 'RESOLVE_AND_MATCH_FORWARD',
                    'total_input': len(unmatched_ids),
                    'total_resolved': resolved_count,
                    'total_matched': matched_count,
                    'total_unmatched': len(still_unmatched),
                    'total_failed': failed_count,
                    'parameters': action_params,
                    'composite_handling': composite_handling,
                    'match_mode': match_mode,
                    'resolver': resolver
                }
            }
            
        except Exception as e:
            logger.error(f"RESOLVE_AND_MATCH_FORWARD failed: {e}", exc_info=True)
            raise RuntimeError(f"Action execution failed: {e}") from e
            
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for early exit."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': None,
            'provenance': [],
            'details': {
                'action': 'RESOLVE_AND_MATCH_FORWARD',
                'skipped': 'empty_input'
            }
        }
        
    def _handle_composites_with_mapping(
        self, 
        identifiers: List[str], 
        strategy: str = 'split_and_match'
    ) -> tuple[List[str], Dict[str, List[str]]]:
        """
        Handle composite identifiers according to strategy, maintaining mapping.
        
        Args:
            identifiers: List of potentially composite identifiers
            strategy: How to handle composites
                - 'split_and_match': Split and include components
                - 'match_whole': Keep composites as-is
                - 'both': Include both composite and components
                
        Returns:
            Tuple of (expanded list of identifiers, mapping from expanded to original)
        """
        if strategy == 'match_whole':
            return identifiers, {id: [id] for id in identifiers}
            
        expanded = []
        mapping = defaultdict(list)  # Expanded ID -> list of original IDs
        delimiter = '_'  # Standard composite delimiter
        
        for identifier in identifiers:
            # Always include original in mapping
            if strategy == 'both' or delimiter not in identifier:
                expanded.append(identifier)
                mapping[identifier].append(identifier)
                
            # Add components if composite
            if delimiter in identifier and strategy in ('split_and_match', 'both'):
                components = identifier.split(delimiter)
                for component in components:
                    if component:  # Skip empty components
                        expanded.append(component)
                        mapping[component].append(identifier)
                
        # Remove duplicates while preserving order
        seen = set()
        result = []
        final_mapping = {}
        
        for item in expanded:
            if item not in seen:
                seen.add(item)
                result.append(item)
                final_mapping[item] = mapping[item]
                
        return result, final_mapping
        
    async def _load_target_identifiers(
        self,
        target_endpoint: Endpoint,
        target_ontology: str
    ) -> Set[str]:
        """
        Load identifiers from target endpoint for the specified ontology type.
        
        Args:
            target_endpoint: Target endpoint object
            target_ontology: Ontology type to load
            
        Returns:
            Set of identifiers present in target
        """
        import json
        from biomapper.mapping.adapters.csv_adapter import CSVAdapter
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from biomapper.db.models import EndpointPropertyConfig
        
        # Find property configuration for the target ontology type
        stmt = (
            select(EndpointPropertyConfig)
            .options(selectinload(EndpointPropertyConfig.property_extraction_config))
            .where(
                EndpointPropertyConfig.endpoint_id == target_endpoint.id,
                EndpointPropertyConfig.ontology_type == target_ontology
            )
        )
        result = await self.session.execute(stmt)
        property_config = result.scalar_one_or_none()
        
        if not property_config:
            raise ValueError(
                f"Target endpoint {target_endpoint.name} does not have configuration "
                f"for ontology type: {target_ontology}"
            )
        
        # Load the target endpoint data with selective column loading
        adapter = CSVAdapter(endpoint=target_endpoint)
        
        # Get the column name for the ontology type
        extraction_pattern = json.loads(property_config.property_extraction_config.extraction_pattern)
        if property_config.property_extraction_config.extraction_method == 'column':
            target_col = extraction_pattern.get('column')
        else:
            target_col = extraction_pattern
        
        # Load only the column we need
        logger.info(f"Loading target column: {target_col}")
        target_data = await adapter.load_data(columns_to_load=[target_col])
        
        # Create a set of all values in the target column
        target_identifiers = set()
        for _, row in target_data.iterrows():
            value = str(row.get(target_col, '')).strip()
            if value:
                # Handle potential composites in target too
                if '_' in value:
                    # Add both composite and components
                    target_identifiers.add(value)
                    components = value.split('_')
                    target_identifiers.update(c for c in components if c)
                else:
                    target_identifiers.add(value)
        
        logger.info(f"Loaded {len(target_identifiers)} unique identifiers from target endpoint")
        return target_identifiers
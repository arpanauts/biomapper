"""
UniProt Historical Resolver Action

This action resolves historical, secondary, or obsolete UniProt identifiers to their
current primary accessions using the UniProt REST API.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient


@register_action("UNIPROT_HISTORICAL_RESOLVER")
class UniProtHistoricalResolver(BaseStrategyAction):
    """
    Resolves historical/secondary UniProt identifiers to current primary accessions.
    
    This action uses the UniProt REST API to resolve:
    - Secondary accessions to their current primary accession
    - Demerged accessions (one ID split into multiple entries)
    - Obsolete/deleted accessions
    - Composite identifiers (e.g., "Q14213_Q8NEV9")
    
    The action provides detailed provenance tracking, including the resolution type
    (primary, secondary, demerged, obsolete) for each identifier.
    
    Required parameters:
    - output_ontology_type: Should be "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    
    Optional parameters:
    - input_context_key: Read identifiers from this context key
    - output_context_key: Store resolved identifiers in this context key
    - batch_size: Number of IDs to resolve per API call (default: 100)
    - include_obsolete: Whether to include obsolete IDs in output (default: False)
    - composite_delimiter: Delimiter for composite IDs (default: '_')
    - expand_composites: Whether to expand composite IDs (default: True)
    
    Example usage in strategy YAML:
    ```yaml
    - name: RESOLVE_HISTORICAL_UNIPROT_IDS
      action:
        type: UNIPROT_HISTORICAL_RESOLVER
        params:
          input_context_key: "outdated_uniprot_ids"
          output_context_key: "current_uniprot_ids"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          batch_size: 200
          include_obsolete: false
    ```
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
        self._resolver_client: Optional[UniProtHistoricalResolverClient] = None
    
    async def _get_resolver_client(self) -> UniProtHistoricalResolverClient:
        """Get or create the UniProt resolver client."""
        if self._resolver_client is None:
            self._resolver_client = UniProtHistoricalResolverClient(
                cache_size=10000,
                timeout=30
            )
        return self._resolver_client
    
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
        Execute UniProt historical resolution.
        
        Args:
            current_identifiers: List of identifiers to resolve
            current_ontology_type: Current ontology type
            action_params: Parameters for this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Standard action result dictionary
        """
        # Extract parameters
        input_context_key = action_params.get('input_context_key')
        output_context_key = action_params.get('output_context_key')
        output_ontology_type = action_params.get('output_ontology_type', 'PROTEIN_UNIPROTKB_AC_ONTOLOGY')
        batch_size = action_params.get('batch_size', 100)
        include_obsolete = action_params.get('include_obsolete', False)
        composite_delimiter = action_params.get('composite_delimiter', '_')
        expand_composites = action_params.get('expand_composites', True)
        
        # Get identifiers to resolve
        if input_context_key:
            identifiers_to_resolve = context.get(input_context_key, [])
            self.logger.info(f"Reading {len(identifiers_to_resolve)} identifiers from context['{input_context_key}']")
        else:
            identifiers_to_resolve = current_identifiers
        
        # Early exit for empty input
        if not identifiers_to_resolve:
            return self._empty_result(output_ontology_type)
        
        # Expand composite identifiers if needed
        if expand_composites:
            expanded_identifiers, composite_mapping = self._expand_composites(
                identifiers_to_resolve, 
                composite_delimiter
            )
        else:
            expanded_identifiers = identifiers_to_resolve
            composite_mapping = {}
        
        self.logger.info(f"Resolving {len(expanded_identifiers)} UniProt identifiers (expanded from {len(identifiers_to_resolve)})")
        
        # Get resolver client
        resolver = await self._get_resolver_client()
        
        # Process in batches
        all_resolved = {}
        provenance = []
        
        for i in range(0, len(expanded_identifiers), batch_size):
            batch = expanded_identifiers[i:i+batch_size]
            self.logger.debug(f"Processing batch {i//batch_size + 1}/{(len(expanded_identifiers) + batch_size - 1)//batch_size}")
            
            try:
                # Call the resolver
                batch_results = await resolver.map_identifiers(batch)
                
                # Process results
                for old_id, (primary_ids, metadata) in batch_results.items():
                    if primary_ids:
                        all_resolved[old_id] = primary_ids
                        
                        # Create provenance for each resolved ID
                        for primary_id in primary_ids:
                            provenance.append({
                                'action': 'UNIPROT_HISTORICAL_RESOLVER',
                                'source_id': old_id,
                                'target_id': primary_id,
                                'resolution_type': metadata,
                                'method': 'uniprot_rest_api',
                                'confidence': self._get_confidence(metadata),
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    elif include_obsolete:
                        # Include obsolete IDs if requested
                        all_resolved[old_id] = []
                        provenance.append({
                            'action': 'UNIPROT_HISTORICAL_RESOLVER',
                            'source_id': old_id,
                            'target_id': None,
                            'resolution_type': 'obsolete',
                            'method': 'uniprot_rest_api',
                            'confidence': 0.0,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        
            except Exception as e:
                self.logger.error(f"Failed to resolve batch starting at index {i}: {e}")
                # Continue with next batch
        
        # Collect all unique resolved IDs
        output_identifiers = []
        seen = set()
        
        for primary_ids in all_resolved.values():
            for pid in primary_ids:
                if pid not in seen:
                    output_identifiers.append(pid)
                    seen.add(pid)
        
        # Store in context if specified
        if output_context_key:
            context[output_context_key] = output_identifiers
            self.logger.info(f"Stored {len(output_identifiers)} resolved identifiers in context['{output_context_key}']")
        
        # Create summary statistics
        resolution_stats = defaultdict(int)
        for record in provenance:
            resolution_stats[record['resolution_type']] += 1
        
        self.logger.info(
            f"Resolution complete: {len(output_identifiers)} current IDs from {len(identifiers_to_resolve)} input IDs. "
            f"Stats: {dict(resolution_stats)}"
        )
        
        return {
            'input_identifiers': identifiers_to_resolve,
            'output_identifiers': output_identifiers,
            'output_ontology_type': output_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'UNIPROT_HISTORICAL_RESOLVER',
                'total_input': len(identifiers_to_resolve),
                'total_expanded': len(expanded_identifiers),
                'total_resolved': len(all_resolved),
                'total_current_ids': len(output_identifiers),
                'resolution_statistics': dict(resolution_stats),
                'include_obsolete': include_obsolete,
                'batch_size': batch_size
            }
        }
    
    def _expand_composites(self, identifiers: List[str], delimiter: str = '_') -> tuple[List[str], Dict[str, List[str]]]:
        """
        Expand composite identifiers into individual components.
        
        Args:
            identifiers: List of identifiers to expand
            delimiter: Delimiter for composite IDs
            
        Returns:
            Tuple of (expanded identifiers list, mapping of composite to components)
        """
        expanded = []
        composite_mapping = {}
        
        for identifier in identifiers:
            if delimiter in identifier:
                components = identifier.split(delimiter)
                expanded.extend(components)
                composite_mapping[identifier] = components
                self.logger.debug(f"Expanded composite '{identifier}' into {len(components)} components")
            else:
                expanded.append(identifier)
        
        return expanded, composite_mapping
    
    def _get_confidence(self, resolution_type: str) -> float:
        """
        Get confidence score based on resolution type.
        
        Args:
            resolution_type: Type of resolution (primary, secondary, demerged, obsolete)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_map = {
            'primary': 1.0,      # Already a primary accession
            'secondary': 0.9,    # Secondary to primary mapping
            'demerged': 0.8,     # Split into multiple entries
            'obsolete': 0.0,     # No longer exists
            'error': 0.0         # Resolution error
        }
        
        # Handle secondary:XXXXX format
        if resolution_type.startswith('secondary:'):
            return confidence_map['secondary']
        
        return confidence_map.get(resolution_type, 0.5)
    
    def _empty_result(self, output_ontology_type: str) -> Dict[str, Any]:
        """Return standard empty result."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': output_ontology_type,
            'provenance': [],
            'details': {
                'action': 'UNIPROT_HISTORICAL_RESOLVER',
                'status': 'skipped',
                'reason': 'empty_input'
            }
        }
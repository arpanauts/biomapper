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
    
    This action is essential for handling composite identifiers in bioinformatics datasets,
    particularly from sources like UKBB that concatenate multiple protein IDs using delimiters.
    It preserves unique identifiers, tracks provenance, and optionally maintains lineage mapping.
    
    Required parameters:
    - input_context_key: Key in context to read identifiers from
    - output_context_key: Key in context to store split identifiers
    
    Optional parameters:
    - delimiter: Character(s) to split on (default: '_')
    - track_metadata_lineage: Store mapping from composite to split IDs (default: False)
    
    Example YAML configuration:
    ```yaml
    strategies:
      - name: ukbb_protein_splitter
        actions:
          - action_type: COMPOSITE_ID_SPLITTER
            params:
              input_context_key: ukbb_protein_ids
              output_context_key: split_protein_ids
              delimiter: "_"
              track_metadata_lineage: true
    ```
    
    Example usage in a larger pipeline:
    ```yaml
    strategies:
      - name: ukbb_to_hpa_mapping
        actions:
          # Load UKBB identifiers
          - action_type: LOAD_ENDPOINT_IDENTIFIERS
            params:
              endpoint_name: ukbb_proteins
              context_key: ukbb_protein_ids
          
          # Split composite IDs
          - action_type: COMPOSITE_ID_SPLITTER
            params:
              input_context_key: ukbb_protein_ids
              output_context_key: split_protein_ids
              delimiter: "_"
              track_metadata_lineage: true
          
          # Convert to target type
          - action_type: CONVERT_IDENTIFIERS_LOCAL
            params:
              input_context_key: split_protein_ids
              output_context_key: converted_ids
              target_ontology_type: HPA_GENE
    ```
    
    Notes:
    - Removes duplicates automatically (uses set internally)
    - Handles None values gracefully by skipping them
    - Preserves empty strings and whitespace
    - Supports multi-character delimiters
    - Lineage mapping stored at {output_context_key}_lineage when enabled
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
            # Skip None values
            if identifier is None:
                self.logger.debug("Skipping None identifier")
                continue
                
            # Convert to string to handle any non-string types
            identifier_str = str(identifier)
            
            if delimiter in identifier_str:
                # Split the composite ID
                components = identifier_str.split(delimiter)
                split_identifiers.update(components)
                
                if track_lineage:
                    lineage_map[identifier_str] = components
                    
                # Track provenance
                provenance.append({
                    'action': 'composite_split',
                    'input': identifier_str,
                    'output': components,
                    'delimiter': delimiter
                })
                
                self.logger.debug(f"Split '{identifier_str}' into {len(components)} components")
            else:
                # Keep non-composite IDs as-is
                split_identifiers.add(identifier_str)
                
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
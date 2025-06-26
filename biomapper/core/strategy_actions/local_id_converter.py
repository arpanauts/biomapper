"""
Convert identifiers using a local mapping file.

This action:
- Reads identifier mappings from a local CSV/TSV file
- Supports one-to-many mappings
- Handles composite identifiers (e.g., Q14213_Q8NEV9)
- Provides detailed provenance tracking

Example usage in a strategy YAML:

```yaml
- action_type: LOCAL_ID_CONVERTER
  parameters:
    mapping_file: "${DATA_DIR}/uniprot_to_ensembl.tsv"
    source_column: uniprot_id
    target_column: ensembl_id
    output_ontology_type: PROTEIN_ENSEMBL
    expand_composites: true
    composite_delimiter: "_"

# Reading from context:
- action_type: LOCAL_ID_CONVERTER
  parameters:
    mapping_file: "${DATA_DIR}/gene_to_protein.csv"
    source_column: gene_symbol
    target_column: protein_id
    output_ontology_type: PROTEIN_UNIPROT
    input_context_key: filtered_genes
    output_context_key: mapped_proteins
```
"""

import csv
import logging
import os
from typing import Dict, Any, List, Set, Tuple
from pathlib import Path

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint


@register_action("LOCAL_ID_CONVERTER")
class LocalIdConverter(BaseStrategyAction):
    """
    Convert identifiers using a local mapping file.
    
    This action reads a mapping file (CSV/TSV) and uses it to transform
    identifiers from one ontology type to another. It supports one-to-many
    mappings and handles composite identifiers.
    
    Required parameters in action_params:
    - mapping_file: Path to the mapping file (CSV/TSV)
    - source_column: Column name containing source identifiers
    - target_column: Column name containing target identifiers
    - output_ontology_type: Target ontology type
    
    Optional parameters:
    - input_context_key: Read identifiers from this context key
    - output_context_key: Store results in this context key
    - delimiter: Delimiter for the mapping file (auto-detected if not specified)
    - composite_delimiter: Delimiter for composite IDs (default: '_')
    - expand_composites: Whether to expand composite IDs (default: True)
    """
    
    def __init__(self, session):
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
        Execute local identifier conversion.
        
        Args:
            current_identifiers: List of identifiers to convert
            current_ontology_type: Current ontology type of identifiers
            action_params: Parameters for this action
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Standard action result dictionary
        """
        # Extract and validate parameters
        mapping_file = action_params.get('mapping_file')
        if not mapping_file:
            raise ValueError("mapping_file parameter is required")
            
        source_column = action_params.get('source_column')
        if not source_column:
            raise ValueError("source_column parameter is required")
            
        target_column = action_params.get('target_column')
        if not target_column:
            raise ValueError("target_column parameter is required")
            
        output_ontology_type = action_params.get('output_ontology_type')
        if not output_ontology_type:
            raise ValueError("output_ontology_type parameter is required")
        
        # Optional parameters
        input_context_key = action_params.get('input_context_key')
        output_context_key = action_params.get('output_context_key')
        delimiter = action_params.get('delimiter')
        composite_delimiter = action_params.get('composite_delimiter', '_')
        expand_composites = action_params.get('expand_composites', True)
        
        # Get identifiers from context if specified
        if input_context_key:
            identifiers_to_convert = context.get(input_context_key, [])
            self.logger.info(f"Reading {len(identifiers_to_convert)} identifiers from context['{input_context_key}']")
        else:
            identifiers_to_convert = current_identifiers
        
        # Early exit for empty input
        if not identifiers_to_convert:
            return self._empty_result(output_ontology_type)
        
        # Resolve file path (handle environment variables)
        resolved_path = os.path.expandvars(mapping_file)
        if not os.path.isabs(resolved_path):
            # Make relative paths absolute
            resolved_path = os.path.abspath(resolved_path)
        
        if not os.path.exists(resolved_path):
            raise ValueError(f"Mapping file not found: {resolved_path}")
        
        self.logger.info(f"Loading mappings from: {resolved_path}")
        
        # Load the mapping file
        mapping_dict = self._load_mapping_file(
            resolved_path, 
            source_column, 
            target_column, 
            delimiter
        )
        
        # Expand composite identifiers if needed
        if expand_composites:
            expanded_identifiers = self._expand_composites(
                identifiers_to_convert, 
                composite_delimiter
            )
        else:
            expanded_identifiers = identifiers_to_convert
        
        # Convert identifiers
        output_identifiers = []
        provenance = []
        unmapped_identifiers = []
        
        for identifier in expanded_identifiers:
            if identifier in mapping_dict:
                # Get all mapped values (supports one-to-many)
                mapped_values = mapping_dict[identifier]
                output_identifiers.extend(mapped_values)
                
                # Create provenance for each mapping
                for target_id in mapped_values:
                    provenance.append({
                        'action': 'LOCAL_ID_CONVERTER',
                        'source_id': identifier,
                        'source_ontology': current_ontology_type,
                        'target_id': target_id,
                        'target_ontology': output_ontology_type,
                        'method': 'local_file_mapping',
                        'mapping_file': os.path.basename(resolved_path),
                        'confidence': 1.0
                    })
            else:
                unmapped_identifiers.append(identifier)
                self.logger.debug(f"No mapping found for: {identifier}")
        
        # Remove duplicates while preserving order
        output_identifiers = list(dict.fromkeys(output_identifiers))
        
        # Store results in context if specified
        if output_context_key:
            context[output_context_key] = output_identifiers
            self.logger.info(f"Stored {len(output_identifiers)} identifiers in context['{output_context_key}']")
        
        self.logger.info(
            f"Converted {len(expanded_identifiers) - len(unmapped_identifiers)}/{len(expanded_identifiers)} "
            f"identifiers from {current_ontology_type} to {output_ontology_type}"
        )
        
        return {
            'input_identifiers': identifiers_to_convert,
            'output_identifiers': output_identifiers,
            'output_ontology_type': output_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'LOCAL_ID_CONVERTER',
                'mapping_file': os.path.basename(resolved_path),
                'conversion': f"{current_ontology_type} -> {output_ontology_type}",
                'total_input': len(identifiers_to_convert),
                'total_expanded': len(expanded_identifiers) if expand_composites else len(identifiers_to_convert),
                'total_mapped': len(expanded_identifiers) - len(unmapped_identifiers),
                'total_unmapped': len(unmapped_identifiers),
                'total_output': len(output_identifiers),
                'unmapped_identifiers': unmapped_identifiers[:10] if unmapped_identifiers else []  # First 10 for debugging
            }
        }
    
    def _load_mapping_file(
        self, 
        file_path: str, 
        source_column: str, 
        target_column: str, 
        delimiter: str = None
    ) -> Dict[str, List[str]]:
        """
        Load mapping file and create a dictionary of source -> [targets].
        
        Args:
            file_path: Path to the mapping file
            source_column: Column name for source identifiers
            target_column: Column name for target identifiers
            delimiter: File delimiter (auto-detected if None)
            
        Returns:
            Dictionary mapping source IDs to lists of target IDs
        """
        # Auto-detect delimiter if not specified
        if delimiter is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if '\t' in first_line:
                    delimiter = '\t'
                else:
                    delimiter = ','
            self.logger.debug(f"Auto-detected delimiter: '{delimiter}'")
        
        mapping_dict = {}
        row_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Validate columns exist
            if source_column not in reader.fieldnames:
                raise ValueError(f"Source column '{source_column}' not found in file. Available columns: {reader.fieldnames}")
            if target_column not in reader.fieldnames:
                raise ValueError(f"Target column '{target_column}' not found in file. Available columns: {reader.fieldnames}")
            
            for row in reader:
                row_count += 1
                source_id = row[source_column].strip()
                target_id = row[target_column].strip()
                
                if source_id and target_id:
                    if source_id not in mapping_dict:
                        mapping_dict[source_id] = []
                    if target_id not in mapping_dict[source_id]:
                        mapping_dict[source_id].append(target_id)
        
        self.logger.info(f"Loaded {len(mapping_dict)} unique mappings from {row_count} rows")
        return mapping_dict
    
    def _expand_composites(self, identifiers: List[str], delimiter: str = '_') -> List[str]:
        """
        Expand composite identifiers into individual components.
        
        Args:
            identifiers: List of identifiers to expand
            delimiter: Delimiter for composite IDs
            
        Returns:
            List of expanded identifiers (includes originals)
        """
        expanded = set()
        composite_count = 0
        
        for identifier in identifiers:
            expanded.add(identifier)  # Always include original
            
            if delimiter in identifier:
                composite_count += 1
                components = identifier.split(delimiter)
                expanded.update(components)
                self.logger.debug(f"Expanded '{identifier}' into {len(components)} components")
        
        if composite_count > 0:
            self.logger.info(f"Expanded {composite_count} composite identifiers")
        
        return list(expanded)
    
    def _empty_result(self, output_ontology_type: str) -> Dict[str, Any]:
        """Return standard empty result."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': output_ontology_type,
            'provenance': [],
            'details': {
                'action': 'LOCAL_ID_CONVERTER',
                'skipped': 'empty_input'
            }
        }
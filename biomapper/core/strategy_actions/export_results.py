"""Export mapping results in various formats."""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("EXPORT_RESULTS")
class ExportResultsAction(StrategyAction):
    """
    Export mapping results in various structured formats.
    
    This action:
    - Exports results as CSV, JSON, or TSV
    - Supports custom column selection
    - Includes mapping metadata and provenance
    - Handles composite identifiers properly
    - Supports both file and context output
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
        Export mapping results.
        
        Action parameters:
            - output_format: Format for export ('csv', 'json', 'tsv') [required]
            - output_file: File path for saving results [required unless save_to_context]
            - columns: List of columns to include (default: all available)
            - include_metadata: Include mapping metadata columns [default: True]
            - include_provenance: Include provenance information [default: False]
            - save_to_context: Optional context key to save exported data
        """
        # Validate required parameters
        output_format = action_params.get('output_format', 'csv').lower()
        output_file = action_params.get('output_file')
        save_to_context = action_params.get('save_to_context')
        
        if not output_file and not save_to_context:
            raise ValueError("Either output_file or save_to_context must be specified")
        
        if output_format not in ['csv', 'json', 'tsv']:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Extract other parameters
        columns = action_params.get('columns')
        include_metadata = action_params.get('include_metadata', True)
        include_provenance = action_params.get('include_provenance', False)
        
        self.logger.info(f"Exporting results in {output_format} format")
        
        # Gather all available data
        initial_identifiers = context.get('initial_identifiers', [])
        mapping_results = context.get('mapping_results', {})
        all_provenance = context.get('all_provenance', [])
        step_results = context.get('step_results', [])
        
        # Build the export data
        export_rows = self._build_export_data(
            initial_identifiers=initial_identifiers,
            current_identifiers=current_identifiers,
            current_ontology_type=current_ontology_type,
            mapping_results=mapping_results,
            all_provenance=all_provenance,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            include_metadata=include_metadata,
            include_provenance=include_provenance
        )
        
        # Filter columns if specified
        if columns and export_rows:
            filtered_rows = []
            for row in export_rows:
                filtered_row = {col: row.get(col, '') for col in columns}
                filtered_rows.append(filtered_row)
            export_rows = filtered_rows
        
        # Export based on format
        if output_format == 'json':
            export_data = {
                'metadata': {
                    'exported_at': datetime.utcnow().isoformat(),
                    'source_endpoint': source_endpoint.name,
                    'target_endpoint': target_endpoint.name,
                    'total_results': len(export_rows)
                },
                'results': export_rows
            }
            
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.logger.info(f"Results exported to {output_file}")
            
            if save_to_context:
                context[save_to_context] = export_data
                
        elif output_format in ['csv', 'tsv']:
            # Use pandas for better handling of complex data
            df = pd.DataFrame(export_rows)
            
            if output_file:
                if output_format == 'csv':
                    df.to_csv(output_file, index=False)
                else:  # tsv
                    df.to_csv(output_file, sep='\t', index=False)
                self.logger.info(f"Results exported to {output_file}")
            
            if save_to_context:
                context[save_to_context] = df.to_dict('records')
        
        # Log export statistics
        self.logger.info(f"Exported {len(export_rows)} rows with {len(export_rows[0]) if export_rows else 0} columns")
        
        # Create provenance entry
        provenance = [{
            'action': 'export_results',
            'timestamp': datetime.utcnow().isoformat(),
            'output_format': output_format,
            'output_file': output_file,
            'rows_exported': len(export_rows),
            'columns_exported': len(export_rows[0]) if export_rows else 0
        }]
        
        # Return identifiers unchanged - this is a reporting action
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'EXPORT_RESULTS',
                'export_successful': True,
                'output_format': output_format,
                'rows_exported': len(export_rows)
            }
        }
    
    def _build_export_data(
        self,
        initial_identifiers: List[str],
        current_identifiers: List[str],
        current_ontology_type: str,
        mapping_results: Dict[str, Any],
        all_provenance: List[Dict],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        include_metadata: bool,
        include_provenance: bool
    ) -> List[Dict[str, Any]]:
        """Build the export data rows."""
        rows = []
        
        # Create a set of current identifiers for quick lookup
        current_set = set(current_identifiers)
        
        # Build provenance lookup if needed
        provenance_by_id = {}
        if include_provenance:
            for prov in all_provenance:
                source_id = prov.get('source_id')
                if source_id:
                    if source_id not in provenance_by_id:
                        provenance_by_id[source_id] = []
                    provenance_by_id[source_id].append(prov)
        
        # Process each initial identifier
        for input_id in initial_identifiers:
            row = {
                'input_identifier': input_id,
                'input_ontology_type': current_ontology_type
            }
            
            # Check if this identifier was successfully mapped
            if input_id in current_set:
                row['mapping_status'] = 'MAPPED'
                row['output_identifier'] = input_id  # May have been transformed
                row['output_ontology_type'] = current_ontology_type
            else:
                row['mapping_status'] = 'UNMAPPED'
                row['output_identifier'] = None
                row['output_ontology_type'] = None
            
            # Add mapping results if available
            if input_id in mapping_results:
                result = mapping_results[input_id]
                row['final_mapped_value'] = result.get('final_mapped_value')
                row['all_mapped_values'] = ','.join(result.get('all_mapped_values', []))
                
                if include_metadata:
                    row['mapping_method'] = result.get('mapping_method')
                    row['confidence_score'] = result.get('confidence_score')
                    row['hop_count'] = result.get('hop_count')
            
            # Add composite identifier flag
            row['is_composite'] = '_' in str(input_id)
            
            # Add provenance if requested
            if include_provenance and input_id in provenance_by_id:
                # Summarize provenance
                prov_summary = []
                for prov in provenance_by_id[input_id]:
                    action = prov.get('action', 'unknown')
                    target = prov.get('target_id', 'none')
                    prov_summary.append(f"{action}:{target}")
                row['provenance_summary'] = '|'.join(prov_summary)
                row['provenance_steps'] = len(provenance_by_id[input_id])
            
            # Add endpoint information
            if include_metadata:
                row['source_endpoint'] = source_endpoint.name
                row['target_endpoint'] = target_endpoint.name
                row['export_timestamp'] = datetime.utcnow().isoformat()
            
            rows.append(row)
        
        # Also add any new identifiers that appeared during mapping
        new_identifiers = current_set - set(initial_identifiers)
        for new_id in new_identifiers:
            row = {
                'input_identifier': None,
                'input_ontology_type': None,
                'mapping_status': 'NEW',
                'output_identifier': new_id,
                'output_ontology_type': current_ontology_type,
                'is_composite': '_' in str(new_id)
            }
            
            if include_metadata:
                row['source_endpoint'] = source_endpoint.name
                row['target_endpoint'] = target_endpoint.name
                row['export_timestamp'] = datetime.utcnow().isoformat()
                row['mapping_method'] = 'introduced_during_mapping'
            
            rows.append(row)
        
        return rows
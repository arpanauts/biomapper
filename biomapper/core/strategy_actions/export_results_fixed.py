"""Fixed export action that properly links source to target mappings."""

import csv
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from .base import BaseStrategyAction


class FixedExportResultsAction(BaseStrategyAction):
    """Export mapping results with proper source-to-target linkage."""
    
    async def execute(self, current_identifiers, current_ontology_type, 
                     action_params, source_endpoint, target_endpoint, context):
        """Export with proper source-to-target mapping."""
        
        output_file = action_params['output_file']
        
        # Get mapping results from context
        initial_identifiers = context.get('initial_identifiers', [])
        mapping_results = context.get('mapping_results', {})
        
        rows = []
        for input_id in initial_identifiers:
            if input_id in mapping_results:
                # Get the mapping result
                result = mapping_results[input_id]
                final_value = result.get('final_mapped_value')
                
                if final_value:
                    # Successfully mapped
                    rows.append({
                        'input_identifier': input_id,
                        'output_identifier': final_value,
                        'mapping_status': 'MAPPED',
                        'mapping_method': result.get('mapping_method', 'unknown'),
                        'confidence': result.get('confidence_score', 1.0)
                    })
                else:
                    # Not mapped
                    rows.append({
                        'input_identifier': input_id,
                        'output_identifier': None,
                        'mapping_status': 'UNMAPPED',
                        'mapping_method': 'no_match',
                        'confidence': 0.0
                    })
            else:
                # No result found
                rows.append({
                    'input_identifier': input_id,
                    'output_identifier': None,
                    'mapping_status': 'UNMAPPED',
                    'mapping_method': 'not_processed',
                    'confidence': 0.0
                })
        
        # Save to CSV
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False)
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'details': {'rows_exported': len(rows)}
        }

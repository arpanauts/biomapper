"""
Strategy action to format and save mapping results.

This action takes reconciled mapping results and saves them to files
in various formats (CSV, JSON) for downstream analysis and use.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import StrategyAction
from biomapper.core.exceptions import MappingExecutionError

logger = logging.getLogger(__name__)


class FormatAndSaveResultsAction(StrategyAction):
    def __init__(self, db_session: AsyncSession):
        """Initialize the action with a database session."""
        self.db_session = db_session
    """
    Action that formats and saves mapping results to files.
    
    This action is typically used at the end of a mapping strategy to
    persist the results in a format suitable for analysis and downstream use.
    """
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint,
        target_endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format and save mapping results to files.
        
        Args:
            current_identifiers: Current list of identifiers
            current_ontology_type: Current ontology type
            action_params: Action parameters including:
                - input_context_key: Key containing results to save
                - output_dir: Directory to save results
                - execution_id: Unique execution identifier
                - csv_filename_template: Template for CSV filename
                - json_summary_filename_template: Template for JSON summary filename
            source_endpoint: Source endpoint configuration
            target_endpoint: Target endpoint configuration
            context: Strategy execution context containing results
            
        Returns:
            Result dictionary with saved file information
        """
        # Get parameters
        input_key = action_params.get('input_context_key', 'reconciled_results')
        output_dir = action_params.get('output_dir', os.environ.get('OUTPUT_DIR', '/tmp'))
        execution_id = action_params.get('execution_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        csv_template = action_params.get('csv_filename_template', 'mapping_results_{execution_id}.csv')
        json_template = action_params.get('json_summary_filename_template', 'mapping_summary_{execution_id}.json')
        
        logger.info(f"Formatting and saving results from context key '{input_key}'")
        
        # Get results from context
        mapping_results = context.get(input_key, {})
        
        if not mapping_results:
            logger.warning("No mapping results found to save")
            return {
                'output_identifiers': current_identifiers,
                'output_ontology_type': current_ontology_type,
                'details': {
                    'status': 'no_results',
                    'message': 'No mapping results found to save'
                }
            }
        
        try:
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Format filenames
            csv_filename = csv_template.format(execution_id=execution_id)
            json_filename = json_template.format(execution_id=execution_id)
            csv_path = os.path.join(output_dir, csv_filename)
            json_path = os.path.join(output_dir, json_filename)
            
            # Convert results to DataFrame for CSV export
            rows = []
            for source_id, mapping_info in mapping_results.items():
                if isinstance(mapping_info, dict):
                    row = {
                        'source_id': source_id,
                        'target_id': mapping_info.get('target_id', ''),
                        'confidence': mapping_info.get('confidence', 0.0),
                        'direction': mapping_info.get('direction', ''),
                        'source': mapping_info.get('source', ''),
                        'bidirectionally_validated': mapping_info.get('bidirectionally_validated', False)
                    }
                    rows.append(row)
            
            df = pd.DataFrame(rows)
            
            # Save CSV
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved {len(df)} mappings to CSV: {csv_path}")
            
            # Create summary statistics
            summary = {
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat(),
                'source_endpoint': source_endpoint.name,
                'target_endpoint': target_endpoint.name,
                'total_mappings': len(df),
                'statistics': {
                    'forward_mappings': len(df[df['direction'] == 'forward']),
                    'reverse_mappings': len(df[df['direction'] == 'reverse']),
                    'bidirectionally_validated': len(df[df['bidirectionally_validated'] == True]),
                    'average_confidence': float(df['confidence'].mean()) if len(df) > 0 else 0.0
                },
                'files': {
                    'csv': csv_path,
                    'json': json_path
                }
            }
            
            # Save JSON summary
            with open(json_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Saved summary to JSON: {json_path}")
            
            return {
                'output_identifiers': current_identifiers,
                'output_ontology_type': current_ontology_type,
                'details': {
                    'status': 'success',
                    'mappings_saved': len(df),
                    'csv_path': csv_path,
                    'json_path': json_path,
                    'execution_id': execution_id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise MappingExecutionError(f"Failed to save results: {str(e)}")
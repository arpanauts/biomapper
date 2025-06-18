"""
SaveBidirectionalResultsAction: Save bidirectional mapping results to files.

This action saves reconciled bidirectional mapping results to CSV and JSON summary files,
replicating the output functionality from the UKBB-HPA pipeline script.
"""

import os
import json
import logging
from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime
import pandas as pd

from biomapper.core.strategy_actions.base import BaseStrategyAction

if TYPE_CHECKING:
    from biomapper.core.mapping_executor import MappingExecutor

logger = logging.getLogger(__name__)


class SaveBidirectionalResultsAction(BaseStrategyAction):
    """
    Action that saves bidirectional mapping results to files.
    
    This action:
    - Retrieves reconciled results from context
    - Formats them for output as CSV and JSON
    - Saves mapping pairs to CSV file
    - Saves comprehensive summary to JSON file
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize the action with parameters.
        
        Args:
            params: Dictionary containing:
                - reconciled_data_key (str): Context key for reconciled results
                - output_dir_key (str): Context key for output directory path
                - csv_filename (str): Name of the CSV output file
                - json_summary_filename (str): Name of the JSON summary file
        """
        self.params = params
        
        # Validate required parameters
        self.reconciled_data_key = params.get('reconciled_data_key')
        if not self.reconciled_data_key:
            raise ValueError("reconciled_data_key is required for SaveBidirectionalResultsAction")
        
        self.output_dir_key = params.get('output_dir_key')
        if not self.output_dir_key:
            raise ValueError("output_dir_key is required for SaveBidirectionalResultsAction")
        
        self.csv_filename = params.get('csv_filename')
        if not self.csv_filename:
            raise ValueError("csv_filename is required for SaveBidirectionalResultsAction")
        
        self.json_summary_filename = params.get('json_summary_filename')
        if not self.json_summary_filename:
            raise ValueError("json_summary_filename is required for SaveBidirectionalResultsAction")
    
    async def execute(self, context: Dict[str, Any], executor: 'MappingExecutor') -> Dict[str, Any]:
        """
        Execute the action to save bidirectional results.
        
        Args:
            context: Current execution context containing reconciled results
            executor: MappingExecutor instance
            
        Returns:
            Updated context with file paths added
        """
        logger.info(f"Saving results from context key '{self.reconciled_data_key}'")
        
        # Retrieve output directory from context
        output_dir = context.get(self.output_dir_key)
        if not output_dir:
            # Try specific environment variable as primary fallback
            output_dir = os.environ.get('STRATEGY_OUTPUT_DIRECTORY')
            if output_dir:
                logger.info(
                    f"No output directory in context key '{self.output_dir_key}', "
                    f"using STRATEGY_OUTPUT_DIRECTORY from environment: {output_dir}"
                )
            else:
                # Fallback to OUTPUT_DIR or default if STRATEGY_OUTPUT_DIRECTORY is also not set
                output_dir = os.environ.get('OUTPUT_DIR', '/home/ubuntu/biomapper/data/results')
                logger.info(
                    f"Neither context key '{self.output_dir_key}' nor STRATEGY_OUTPUT_DIRECTORY env var found, "
                    f"using OUTPUT_DIR or default: {output_dir}"
                )
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Retrieve reconciled data from context
        reconciled_data = context.get(self.reconciled_data_key, {})
        
        if not reconciled_data:
            logger.warning("No reconciled data found to save")
            return context
        
        # Extract data components
        all_pairs = reconciled_data.get('reconciled_pairs', [])
        bidirectional_pairs = reconciled_data.get('bidirectional_pairs', [])
        forward_only_pairs = reconciled_data.get('forward_only_pairs', [])
        reverse_only_pairs = reconciled_data.get('reverse_only_pairs', [])
        statistics = reconciled_data.get('statistics', {})
        metadata = reconciled_data.get('metadata', {})
        
        # Construct full file paths
        csv_path = os.path.join(output_dir, self.csv_filename)
        json_path = os.path.join(output_dir, self.json_summary_filename)
        
        try:
            # Save CSV file
            if all_pairs:
                # Convert to DataFrame for easy CSV export
                df_data = []
                for pair in all_pairs:
                    df_data.append({
                        'source_id': pair.get('source'),
                        'target_id': pair.get('target'),
                        'bidirectional': pair.get('bidirectional', False),
                        'confidence': pair.get('confidence', 0.0),
                        'mapping_method': pair.get('mapping_method', 'unknown')
                    })
                
                df = pd.DataFrame(df_data)
                
                # Sort by confidence (descending) and then by source_id
                df = df.sort_values(
                    by=['confidence', 'source_id'], 
                    ascending=[False, True]
                )
                
                # Save to CSV
                df.to_csv(csv_path, index=False)
                logger.info(f"Saved {len(df)} mapping pairs to: {csv_path}")
            else:
                logger.warning("No mapping pairs to save to CSV")
            
            # Prepare comprehensive summary
            summary = {
                'execution_metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'SaveBidirectionalResultsAction',
                    'csv_output': csv_path,
                    'json_output': json_path
                },
                'mapping_statistics': statistics,
                'mapping_breakdown': {
                    'total_mappings': len(all_pairs),
                    'bidirectional_confirmed': len(bidirectional_pairs),
                    'forward_only': len(forward_only_pairs),
                    'reverse_only': len(reverse_only_pairs)
                },
                'sample_mappings': {
                    'bidirectional_sample': bidirectional_pairs[:5] if bidirectional_pairs else [],
                    'forward_only_sample': forward_only_pairs[:5] if forward_only_pairs else [],
                    'reverse_only_sample': reverse_only_pairs[:5] if reverse_only_pairs else []
                },
                'reconciliation_metadata': metadata,
                'environment': {
                    'output_directory': output_dir,
                    'csv_filename': self.csv_filename,
                    'json_filename': self.json_summary_filename
                }
            }
            
            # Add execution context if available
            if 'execution_id' in context:
                summary['execution_metadata']['execution_id'] = context['execution_id']
            if 'strategy_name' in context:
                summary['execution_metadata']['strategy_name'] = context['strategy_name']
            
            # Save JSON summary
            with open(json_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Saved mapping summary to: {json_path}")
            
            # Add file paths to context for downstream use
            context['saved_csv_path'] = csv_path
            context['saved_json_path'] = json_path
            
            # Log summary statistics
            logger.info("=" * 60)
            logger.info("MAPPING SUMMARY:")
            logger.info(f"Total mappings: {statistics.get('total_reconciled', 0)}")
            logger.info(f"Bidirectionally confirmed: {statistics.get('bidirectionally_confirmed', 0)}")
            logger.info(f"Forward-only mappings: {statistics.get('forward_only_count', 0)}")
            logger.info(f"Reverse-only mappings: {statistics.get('reverse_only_count', 0)}")
            logger.info(f"Unique source IDs: {statistics.get('unique_source_ids', 0)}")
            logger.info(f"Unique target IDs: {statistics.get('unique_target_ids', 0)}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
        
        # Return the updated context
        return context
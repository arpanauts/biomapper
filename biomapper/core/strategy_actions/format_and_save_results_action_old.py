"""
FormatAndSaveResultsAction: Formats mapping results and saves to CSV and JSON summary.

This action replicates the results processing, DataFrame creation, CSV saving, and JSON summary
saving logic from the run_full_ukbb_hpa_mapping_bidirectional.py script.
"""

import os
import json
import pandas as pd
from typing import Dict, Any
from datetime import datetime
from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.utils.placeholder_resolver import resolve_file_path


class FormatAndSaveResultsAction(BaseStrategyAction):
    """
    Action that formats mapping results and saves them to CSV and JSON files.
    
    Parameters:
        - mapped_data_context_key (str, required): Key for mapped data in context
        - unmapped_source_context_key (str, required): Key for unmapped source data
        - new_target_context_key (str, optional): Key for new target data
        - source_id_column_name (str, default "source_id"): Column name for source IDs
        - target_id_column_name (str, default "target_id"): Column name for target IDs
        - mapping_type_column_name (str, default "mapping_type"): Column name for mapping type
        - output_csv_path (str, required): Path to save CSV file (supports ${OUTPUT_DIR})
        - output_json_summary_path (str, required): Path to save JSON summary (supports ${OUTPUT_DIR})
        - execution_id_context_key (str, optional): Key for execution ID in context
    """
    
    def __init__(self, params: Dict[str, Any]):
        """Initialize the action with parameters."""
        super().__init__(params)
        
        # Validate required parameters
        self.mapped_data_context_key = params.get('mapped_data_context_key')
        if not self.mapped_data_context_key:
            raise ValueError("mapped_data_context_key is required for FormatAndSaveResultsAction")
            
        self.unmapped_source_context_key = params.get('unmapped_source_context_key')
        if not self.unmapped_source_context_key:
            raise ValueError("unmapped_source_context_key is required for FormatAndSaveResultsAction")
            
        self.output_csv_path = params.get('output_csv_path')
        if not self.output_csv_path:
            raise ValueError("output_csv_path is required for FormatAndSaveResultsAction")
            
        self.output_json_summary_path = params.get('output_json_summary_path')
        if not self.output_json_summary_path:
            raise ValueError("output_json_summary_path is required for FormatAndSaveResultsAction")
        
        # Optional parameters with defaults
        self.new_target_context_key = params.get('new_target_context_key')
        self.source_id_column_name = params.get('source_id_column_name', 'source_id')
        self.target_id_column_name = params.get('target_id_column_name', 'target_id')
        self.mapping_type_column_name = params.get('mapping_type_column_name', 'mapping_type')
        self.execution_id_context_key = params.get('execution_id_context_key', 'execution_id')
    
    
    async def execute(self, context: Dict[str, Any], executor: 'MappingExecutor') -> Dict[str, Any]:
        """
        Execute the action to format and save results.
        
        Args:
            context: Current execution context
            executor: MappingExecutor instance
            
        Returns:
            Updated context with paths to saved files
        """
        self.log_info("Starting FormatAndSaveResultsAction")
        
        try:
            # Get data from context
            mapped_data = context.get(self.mapped_data_context_key, [])
            unmapped_source = context.get(self.unmapped_source_context_key, [])
            new_targets = context.get(self.new_target_context_key, []) if self.new_target_context_key else []
            
            # Get execution metadata from context or environment
            execution_id = context.get(self.execution_id_context_key) or os.environ.get('EXECUTION_ID', 'unknown')
            start_time_str = context.get('start_time') or os.environ.get('START_TIME')
            if start_time_str and isinstance(start_time_str, str):
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                except:
                    start_time = datetime.now()
            elif start_time_str:
                start_time = start_time_str
            else:
                start_time = datetime.now()
            
            # Get input identifiers (should be set by LoadEndpointIdentifiersAction)
            input_identifiers = context.get('initial_source_identifiers', [])
            
            # Extract bidirectional tracking information
            direct_matches = context.get('direct_matches', [])
            all_matches = context.get('all_matches', [])
            unmatched_ukbb = context.get('unmatched_ukbb', [])
            unmatched_hpa = context.get('unmatched_hpa', [])
            
            # Build output rows for DataFrame
            output_rows = []
            results_dict = context.get('results', {})
            final_identifiers = set(context.get('final_identifiers', []))
            
            # Process each input identifier
            for input_id in input_identifiers:
                # Default values
                final_mapped_id = None
                mapping_status = 'UNMAPPED'
                mapping_method = 'Unknown'
                confidence = 0.0
                
                # Check if this ID has results
                if input_id in results_dict:
                    mapping_result = results_dict[input_id]
                    all_mapped_values = mapping_result.get('all_mapped_values', [])
                    
                    # Check if this identifier made it to the final set
                    if all_mapped_values and any(val in final_identifiers for val in all_mapped_values):
                        # Successfully mapped
                        final_mapped_id = all_mapped_values[-1]  # Last value is the HPA gene
                        mapping_status = 'MAPPED'
                        
                        # Determine mapping method from context
                        if input_id in [m[0] for m in direct_matches if isinstance(m, tuple)]:
                            mapping_method = 'DIRECT_MATCH'
                            confidence = 1.0
                        elif input_id in all_matches:
                            mapping_method = 'RESOLVED_MATCH'
                            confidence = 0.9
                        else:
                            mapping_method = 'INDIRECT_MATCH'
                            confidence = 0.8
                    else:
                        # Not mapped
                        mapping_status = 'UNMAPPED'
                        mapping_method = 'NO_MATCH_FOUND'
                
                output_rows.append({
                    'Input_UKBB_UniProt_ID': input_id,
                    'Final_Mapped_HPA_Gene': final_mapped_id,
                    'Mapping_Status': mapping_status,
                    'Mapping_Method': mapping_method,
                    'Confidence': confidence,
                    'Is_Composite': '_' in str(input_id)
                })
            
            # Create DataFrame and save to CSV
            output_df = pd.DataFrame(output_rows)
            csv_path = resolve_file_path(self.output_csv_path, context, create_dirs=True)
            output_df.to_csv(csv_path, index=False)
            self.log_info(f"Results saved to CSV: {csv_path}")
            
            # Create comprehensive summary
            summary = context.get('summary', {})
            step_results = summary.get('step_results', [])
            
            # Enhanced summary with bidirectional tracking
            enhanced_summary = {
                'execution_info': {
                    'strategy': context.get('strategy_name') or os.environ.get('STRATEGY_NAME', 'UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT'),
                    'start_time': start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time),
                    'end_time': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds() if isinstance(start_time, datetime) else 0,
                    'execution_id': execution_id,
                    'robust_features': {
                        'checkpoint_enabled': context.get('checkpoint_enabled', False),
                        'checkpoint_used': context.get('checkpoint_used', False),
                        'batch_size': context.get('batch_size', 250),
                        'max_retries': context.get('max_retries', 3),
                        'progress_tracking': context.get('progress_tracking', True)
                    }
                },
                'input_analysis': {
                    'total_input': len(input_identifiers),
                    'composite_identifiers': sum(1 for id in input_identifiers if '_' in str(id)),
                    'unique_identifiers': len(set(input_identifiers))
                },
                'mapping_results': {
                    'direct_matches': len(direct_matches),
                    'resolved_matches': len(all_matches) - len(direct_matches) if len(all_matches) > len(direct_matches) else 0,
                    'total_mapped': len([r for r in output_rows if r['Mapping_Status'] == 'MAPPED']),
                    'total_unmapped': len([r for r in output_rows if r['Mapping_Status'] == 'UNMAPPED'])
                },
                'step_performance': [],
                'mapping_methods': output_df['Mapping_Method'].value_counts().to_dict() if 'Mapping_Method' in output_df.columns else {},
                'robust_execution_metadata': context.get('robust_execution', {}),
                'original_summary': summary
            }
            
            # Add step performance details
            for step in step_results:
                enhanced_summary['step_performance'].append({
                    'step_id': step.get('step_id'),
                    'action_type': step.get('action_type'),
                    'success': step.get('success', False),
                    'input_count': step.get('input_count', 0),
                    'output_count': step.get('output_count', 0),
                    'duration': step.get('duration', 0)
                })
            
            # Save enhanced summary
            json_path = resolve_file_path(self.output_json_summary_path, context, create_dirs=True)
            with open(json_path, 'w') as f:
                json.dump(enhanced_summary, f, indent=2)
            self.log_info(f"Enhanced summary saved to JSON: {json_path}")
            
            # Log summary statistics
            self.log_info("=" * 80)
            self.log_info("MAPPING SUMMARY:")
            self.log_info(f"Total input identifiers: {enhanced_summary['input_analysis']['total_input']}")
            self.log_info(f"Composite identifiers: {enhanced_summary['input_analysis']['composite_identifiers']}")
            self.log_info(f"Direct matches: {enhanced_summary['mapping_results']['direct_matches']}")
            self.log_info(f"Resolved matches: {enhanced_summary['mapping_results']['resolved_matches']}")
            self.log_info(f"Total successfully mapped: {enhanced_summary['mapping_results']['total_mapped']}")
            self.log_info(f"Total unmapped: {enhanced_summary['mapping_results']['total_unmapped']}")
            
            # Mapping method breakdown
            if enhanced_summary['mapping_methods']:
                self.log_info("\nMapping method breakdown:")
                for method, count in enhanced_summary['mapping_methods'].items():
                    self.log_info(f"  {method}: {count}")
            
            # Store paths in context for potential downstream use
            context['saved_csv_path'] = csv_path
            context['saved_json_summary_path'] = json_path
            context['formatted_summary'] = enhanced_summary
            
        except Exception as e:
            self.log_error(f"Failed to format and save results: {str(e)}")
            raise
        
        return context
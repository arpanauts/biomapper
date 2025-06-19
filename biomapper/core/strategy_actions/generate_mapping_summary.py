"""Generate a summary of mapping results."""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("GENERATE_MAPPING_SUMMARY")
class GenerateMappingSummaryAction(StrategyAction):
    """
    Generate a high-level summary of mapping results.
    
    This action:
    - Aggregates statistics from all previous mapping steps
    - Calculates coverage metrics
    - Reports timing information
    - Provides both console and file output options
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
        Generate mapping summary.
        
        Action parameters:
            - output_format: Format for output ('console', 'json', 'csv') [default: 'console']
            - include_statistics: Include detailed statistics [default: True]
            - output_file: Optional file path for saving summary
            - save_to_context: Optional context key to save summary data
        """
        # Extract parameters with defaults
        output_format = action_params.get('output_format', 'console')
        include_statistics = action_params.get('include_statistics', True)
        output_file = action_params.get('output_file')
        save_to_context = action_params.get('save_to_context')
        
        self.logger.info(f"Generating mapping summary in {output_format} format")
        
        # Gather data from context
        initial_identifiers = context.get('initial_identifiers', [])
        step_results = context.get('step_results', [])
        start_time = context.get('execution_start_time')
        
        # Calculate basic statistics
        summary_data = {
            'execution_info': {
                'source_endpoint': source_endpoint.name,
                'target_endpoint': target_endpoint.name,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': datetime.utcnow().isoformat(),
                'duration_seconds': (datetime.utcnow() - start_time).total_seconds() if start_time else None
            },
            'input_analysis': {
                'total_input': len(initial_identifiers),
                'unique_input': len(set(initial_identifiers)),
                'composite_identifiers': sum(1 for id in initial_identifiers if '_' in str(id))
            },
            'output_analysis': {
                'total_output': len(current_identifiers),
                'unique_output': len(set(current_identifiers)),
                'output_ontology_type': current_ontology_type
            },
            'mapping_coverage': {
                'coverage_percentage': (len(current_identifiers) / len(initial_identifiers) * 100) if initial_identifiers else 0,
                'unmapped_count': len(initial_identifiers) - len(current_identifiers) if len(initial_identifiers) > len(current_identifiers) else 0
            }
        }
        
        # Add detailed statistics if requested
        if include_statistics and step_results:
            summary_data['step_performance'] = []
            for step in step_results:
                step_summary = {
                    'step_id': step.get('step_id'),
                    'action_type': step.get('action_type'),
                    'input_count': step.get('input_count', 0),
                    'output_count': step.get('output_count', 0),
                    'duration': step.get('duration', 0),
                    'success': step.get('success', False)
                }
                summary_data['step_performance'].append(step_summary)
            
            # Calculate cumulative metrics
            total_duration = sum(step.get('duration', 0) for step in step_results)
            summary_data['performance_metrics'] = {
                'total_step_duration': total_duration,
                'average_step_duration': total_duration / len(step_results) if step_results else 0,
                'slowest_step': max(step_results, key=lambda x: x.get('duration', 0)).get('step_id') if step_results else None
            }
        
        # Format output based on requested format
        if output_format == 'console':
            summary_text = self._format_console_summary(summary_data)
            self.logger.info("\n" + "=" * 80)
            self.logger.info("MAPPING SUMMARY")
            self.logger.info("=" * 80)
            self.logger.info(summary_text)
            self.logger.info("=" * 80)
            
        elif output_format == 'json':
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(summary_data, f, indent=2)
                self.logger.info(f"Summary saved to {output_file}")
            else:
                self.logger.info(json.dumps(summary_data, indent=2))
                
        elif output_format == 'csv':
            # For CSV, flatten the summary data
            import csv
            flattened = self._flatten_dict(summary_data)
            if output_file:
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=flattened.keys())
                    writer.writeheader()
                    writer.writerow(flattened)
                self.logger.info(f"Summary saved to {output_file}")
        
        # Save to context if requested
        if save_to_context:
            context[save_to_context] = summary_data
            self.logger.debug(f"Summary data saved to context key: {save_to_context}")
        
        # Create provenance entry
        provenance = [{
            'action': 'generate_mapping_summary',
            'timestamp': datetime.utcnow().isoformat(),
            'output_format': output_format,
            'statistics_included': include_statistics,
            'output_file': output_file
        }]
        
        # Return identifiers unchanged - this is a reporting action
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'GENERATE_MAPPING_SUMMARY',
                'summary_generated': True,
                'output_format': output_format,
                'summary_data': summary_data
            }
        }
    
    def _format_console_summary(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data for console output."""
        lines = []
        
        # Execution info
        exec_info = summary_data['execution_info']
        lines.append(f"Source Endpoint: {exec_info['source_endpoint']}")
        lines.append(f"Target Endpoint: {exec_info['target_endpoint']}")
        if exec_info['duration_seconds']:
            lines.append(f"Execution Time: {exec_info['duration_seconds']:.2f} seconds")
        lines.append("")
        
        # Input analysis
        input_info = summary_data['input_analysis']
        lines.append("INPUT ANALYSIS:")
        lines.append(f"  Total identifiers: {input_info['total_input']}")
        lines.append(f"  Unique identifiers: {input_info['unique_input']}")
        lines.append(f"  Composite identifiers: {input_info['composite_identifiers']}")
        lines.append("")
        
        # Output analysis
        output_info = summary_data['output_analysis']
        lines.append("OUTPUT ANALYSIS:")
        lines.append(f"  Total identifiers: {output_info['total_output']}")
        lines.append(f"  Unique identifiers: {output_info['unique_output']}")
        lines.append(f"  Output ontology type: {output_info['output_ontology_type']}")
        lines.append("")
        
        # Coverage
        coverage = summary_data['mapping_coverage']
        lines.append("MAPPING COVERAGE:")
        lines.append(f"  Coverage: {coverage['coverage_percentage']:.1f}%")
        lines.append(f"  Unmapped: {coverage['unmapped_count']}")
        
        # Step performance if available
        if 'step_performance' in summary_data:
            lines.append("\nSTEP PERFORMANCE:")
            for step in summary_data['step_performance']:
                lines.append(f"  {step['step_id']}: {step['input_count']} → {step['output_count']} ({step['duration']:.2f}s)")
        
        return "\n".join(lines)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary for CSV output."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)
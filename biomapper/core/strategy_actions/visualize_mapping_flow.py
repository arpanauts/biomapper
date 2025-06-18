"""Visualize the mapping flow through strategy steps."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseStrategyAction
from biomapper.db.models import Endpoint


class VisualizeMappingFlowAction(BaseStrategyAction):
    """
    Generate visual representation of mapping process.
    
    This action:
    - Creates flow diagrams showing identifier movement
    - Generates charts for step-by-step statistics
    - Supports multiple visualization types (sankey, bar, flow)
    - Can output as JSON data for frontend rendering
    - Optionally uses matplotlib/plotly for direct image generation
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
        Generate mapping flow visualization.
        
        Action parameters:
            - output_file: File path for saving visualization [required]
            - chart_type: Type of chart ('sankey', 'bar', 'flow', 'json') [default: 'json']
            - show_statistics: Include detailed statistics [default: True]
            - save_to_context: Optional context key to save visualization data
        """
        # Extract parameters
        output_file = action_params.get('output_file')
        if not output_file:
            raise ValueError("output_file is required for visualization")
        
        chart_type = action_params.get('chart_type', 'json')
        show_statistics = action_params.get('show_statistics', True)
        save_to_context = action_params.get('save_to_context')
        
        self.logger.info(f"Generating {chart_type} visualization of mapping flow")
        
        # Gather data from context
        initial_identifiers = context.get('initial_identifiers', [])
        step_results = context.get('step_results', [])
        all_provenance = context.get('all_provenance', [])
        
        # Build visualization data
        viz_data = self._build_visualization_data(
            initial_identifiers=initial_identifiers,
            current_identifiers=current_identifiers,
            step_results=step_results,
            all_provenance=all_provenance,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            show_statistics=show_statistics
        )
        
        # Generate visualization based on type
        if chart_type == 'json':
            # Export raw data for frontend visualization libraries
            with open(output_file, 'w') as f:
                json.dump(viz_data, f, indent=2)
            self.logger.info(f"Visualization data saved to {output_file}")
            
        elif chart_type == 'sankey':
            # Generate Sankey diagram data
            sankey_data = self._generate_sankey_data(viz_data)
            with open(output_file, 'w') as f:
                json.dump(sankey_data, f, indent=2)
            self.logger.info(f"Sankey diagram data saved to {output_file}")
            
        elif chart_type == 'bar':
            # Generate bar chart using matplotlib (if available)
            self._generate_bar_chart(viz_data, output_file)
            
        elif chart_type == 'flow':
            # Generate flow diagram data
            flow_data = self._generate_flow_data(viz_data)
            with open(output_file, 'w') as f:
                json.dump(flow_data, f, indent=2)
            self.logger.info(f"Flow diagram data saved to {output_file}")
        
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # Save to context if requested
        if save_to_context:
            context[save_to_context] = viz_data
            self.logger.debug(f"Visualization data saved to context key: {save_to_context}")
        
        # Create provenance entry
        provenance = [{
            'action': 'visualize_mapping_flow',
            'timestamp': datetime.utcnow().isoformat(),
            'chart_type': chart_type,
            'output_file': output_file,
            'statistics_included': show_statistics
        }]
        
        # Return identifiers unchanged - this is a reporting action
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'VISUALIZE_MAPPING_FLOW',
                'visualization_generated': True,
                'chart_type': chart_type,
                'output_file': output_file
            }
        }
    
    def _build_visualization_data(
        self,
        initial_identifiers: List[str],
        current_identifiers: List[str],
        step_results: List[Dict],
        all_provenance: List[Dict],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        show_statistics: bool
    ) -> Dict[str, Any]:
        """Build the core visualization data structure."""
        viz_data = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'source_endpoint': source_endpoint.name,
                'target_endpoint': target_endpoint.name,
                'total_steps': len(step_results)
            },
            'flow': {
                'initial_count': len(initial_identifiers),
                'final_count': len(current_identifiers),
                'steps': []
            }
        }
        
        # Track identifier flow through steps
        current_count = len(initial_identifiers)
        
        for i, step in enumerate(step_results):
            step_data = {
                'step_number': i + 1,
                'step_id': step.get('step_id'),
                'action_type': step.get('action_type'),
                'input_count': step.get('input_count', current_count),
                'output_count': step.get('output_count', 0),
                'reduction': step.get('input_count', 0) - step.get('output_count', 0),
                'retention_rate': (step.get('output_count', 0) / step.get('input_count', 1) * 100) if step.get('input_count', 0) > 0 else 0
            }
            
            if show_statistics:
                step_data['duration'] = step.get('duration', 0)
                step_data['success'] = step.get('success', False)
                step_data['parameters'] = step.get('parameters', {})
            
            viz_data['flow']['steps'].append(step_data)
            current_count = step.get('output_count', current_count)
        
        # Add identifier categories if statistics enabled
        if show_statistics:
            viz_data['identifier_categories'] = self._categorize_identifiers(
                initial_identifiers, current_identifiers, all_provenance
            )
        
        return viz_data
    
    def _categorize_identifiers(
        self,
        initial_identifiers: List[str],
        current_identifiers: List[str],
        all_provenance: List[Dict]
    ) -> Dict[str, Any]:
        """Categorize identifiers by their mapping outcomes."""
        initial_set = set(initial_identifiers)
        current_set = set(current_identifiers)
        
        # Track mapping methods used
        method_counts = defaultdict(int)
        for prov in all_provenance:
            method = prov.get('method') or prov.get('action')
            if method:
                method_counts[method] += 1
        
        categories = {
            'successfully_mapped': len(initial_set & current_set),
            'unmapped': len(initial_set - current_set),
            'newly_introduced': len(current_set - initial_set),
            'composite_identifiers': sum(1 for id in initial_identifiers if '_' in str(id)),
            'mapping_methods': dict(method_counts)
        }
        
        return categories
    
    def _generate_sankey_data(self, viz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data structure for Sankey diagram."""
        nodes = []
        links = []
        
        # Add nodes for each step
        nodes.append({'id': 0, 'name': 'Initial Input'})
        
        for i, step in enumerate(viz_data['flow']['steps']):
            nodes.append({
                'id': i + 1,
                'name': f"{step['step_id']} ({step['action_type']})"
            })
        
        nodes.append({'id': len(nodes), 'name': 'Final Output'})
        
        # Add links between steps
        initial_count = viz_data['flow']['initial_count']
        
        # First link: Initial -> First step
        if viz_data['flow']['steps']:
            first_step = viz_data['flow']['steps'][0]
            links.append({
                'source': 0,
                'target': 1,
                'value': first_step['input_count']
            })
        
        # Links between steps
        for i in range(len(viz_data['flow']['steps']) - 1):
            current_step = viz_data['flow']['steps'][i]
            next_step = viz_data['flow']['steps'][i + 1]
            
            # Successful flow
            links.append({
                'source': i + 1,
                'target': i + 2,
                'value': current_step['output_count']
            })
            
            # Lost identifiers (if any)
            lost = current_step['input_count'] - current_step['output_count']
            if lost > 0:
                links.append({
                    'source': i + 1,
                    'target': len(nodes) - 1,  # To "Lost" node
                    'value': lost,
                    'color': 'rgba(255, 0, 0, 0.3)'  # Red for lost
                })
        
        # Final link: Last step -> Final output
        if viz_data['flow']['steps']:
            last_step = viz_data['flow']['steps'][-1]
            links.append({
                'source': len(viz_data['flow']['steps']),
                'target': len(nodes) - 1,
                'value': last_step['output_count']
            })
        
        return {
            'type': 'sankey',
            'nodes': nodes,
            'links': links,
            'metadata': viz_data['metadata']
        }
    
    def _generate_flow_data(self, viz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data for flow diagram."""
        flow_data = {
            'type': 'flow',
            'metadata': viz_data['metadata'],
            'nodes': [],
            'edges': []
        }
        
        # Create nodes
        y_position = 100
        for i, step in enumerate(viz_data['flow']['steps']):
            flow_data['nodes'].append({
                'id': f"step_{i}",
                'label': step['step_id'],
                'subtitle': step['action_type'],
                'position': {'x': 200 + i * 300, 'y': y_position},
                'data': {
                    'input': step['input_count'],
                    'output': step['output_count'],
                    'retention': f"{step['retention_rate']:.1f}%"
                }
            })
        
        # Create edges
        for i in range(len(viz_data['flow']['steps']) - 1):
            current_step = viz_data['flow']['steps'][i]
            flow_data['edges'].append({
                'id': f"edge_{i}",
                'source': f"step_{i}",
                'target': f"step_{i+1}",
                'label': f"{current_step['output_count']} ids",
                'animated': True
            })
        
        return flow_data
    
    def _generate_bar_chart(self, viz_data: Dict[str, Any], output_file: str) -> None:
        """Generate bar chart using matplotlib (if available)."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            # Extract step data
            steps = viz_data['flow']['steps']
            step_labels = [f"{s['step_id'][:20]}" for s in steps]
            input_counts = [s['input_count'] for s in steps]
            output_counts = [s['output_count'] for s in steps]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Bar positions
            x = range(len(steps))
            width = 0.35
            
            # Create bars
            bars1 = ax.bar([i - width/2 for i in x], input_counts, width, label='Input', color='skyblue')
            bars2 = ax.bar([i + width/2 for i in x], output_counts, width, label='Output', color='lightgreen')
            
            # Add labels and title
            ax.set_xlabel('Processing Steps')
            ax.set_ylabel('Number of Identifiers')
            ax.set_title(f'Identifier Flow: {viz_data["metadata"]["source_endpoint"]} → {viz_data["metadata"]["target_endpoint"]}')
            ax.set_xticks(x)
            ax.set_xticklabels(step_labels, rotation=45, ha='right')
            ax.legend()
            
            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(f'{int(height)}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom',
                               fontsize=8)
            
            # Add retention rate line
            ax2 = ax.twinx()
            retention_rates = [s['retention_rate'] for s in steps]
            line = ax2.plot(x, retention_rates, 'r-o', label='Retention %')
            ax2.set_ylabel('Retention Rate (%)')
            ax2.set_ylim(0, 105)
            
            # Combined legend
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc='upper right')
            
            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Bar chart saved to {output_file}")
            
        except ImportError:
            self.logger.warning("matplotlib not available, saving data for external visualization")
            # Fall back to JSON data
            bar_data = {
                'type': 'bar',
                'labels': [s['step_id'] for s in viz_data['flow']['steps']],
                'datasets': [
                    {
                        'label': 'Input Count',
                        'data': [s['input_count'] for s in viz_data['flow']['steps']]
                    },
                    {
                        'label': 'Output Count', 
                        'data': [s['output_count'] for s in viz_data['flow']['steps']]
                    },
                    {
                        'label': 'Retention Rate',
                        'data': [s['retention_rate'] for s in viz_data['flow']['steps']],
                        'yAxisID': 'y2'
                    }
                ]
            }
            with open(output_file, 'w') as f:
                json.dump(bar_data, f, indent=2)
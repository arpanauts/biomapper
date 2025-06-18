"""Generate a detailed mapping report with comprehensive analysis."""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict, Counter
from sqlalchemy.ext.asyncio import AsyncSession

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import Endpoint


@register_action("GENERATE_DETAILED_REPORT")
class GenerateDetailedReportAction(StrategyAction):
    """
    Generate a comprehensive mapping analysis report.
    
    This action:
    - Provides detailed breakdown by mapping step
    - Analyzes unmatched identifiers
    - Tracks provenance and mapping paths
    - Supports grouping by step or ontology
    - Includes many-to-many relationship analysis
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
        Generate detailed mapping report.
        
        Action parameters:
            - output_file: Optional file path for saving report
            - include_unmatched: Include analysis of unmatched identifiers [default: True]
            - grouping_strategy: How to group results ('by_step', 'by_ontology', 'by_method') [default: 'by_step']
            - format: Output format ('json', 'markdown', 'html') [default: 'markdown']
            - save_to_context: Optional context key to save report data
        """
        # Extract parameters with defaults
        output_file = action_params.get('output_file')
        include_unmatched = action_params.get('include_unmatched', True)
        grouping_strategy = action_params.get('grouping_strategy', 'by_step')
        output_format = action_params.get('format', 'markdown')
        save_to_context = action_params.get('save_to_context')
        
        self.logger.info(f"Generating detailed report with grouping: {grouping_strategy}")
        
        # Gather comprehensive data from context
        initial_identifiers = set(context.get('initial_identifiers', []))
        step_results = context.get('step_results', [])
        all_provenance = context.get('all_provenance', [])
        mapping_results = context.get('mapping_results', {})
        
        # Build the report data structure
        report_data = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'source_endpoint': source_endpoint.name,
                'target_endpoint': target_endpoint.name,
                'grouping_strategy': grouping_strategy,
                'total_steps': len(step_results)
            },
            'overview': self._generate_overview(
                initial_identifiers, current_identifiers, step_results
            ),
            'step_details': self._analyze_steps(step_results, grouping_strategy),
            'mapping_paths': self._analyze_mapping_paths(all_provenance),
            'identifier_flow': self._track_identifier_flow(step_results, initial_identifiers)
        }
        
        # Add unmatched analysis if requested
        if include_unmatched:
            report_data['unmatched_analysis'] = self._analyze_unmatched(
                initial_identifiers, current_identifiers, mapping_results
            )
        
        # Add many-to-many analysis
        report_data['relationship_analysis'] = self._analyze_relationships(
            all_provenance, mapping_results
        )
        
        # Format and output the report
        if output_format == 'json':
            report_content = json.dumps(report_data, indent=2)
        elif output_format == 'markdown':
            report_content = self._format_markdown_report(report_data)
        elif output_format == 'html':
            report_content = self._format_html_report(report_data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            self.logger.info(f"Detailed report saved to {output_file}")
        else:
            # Log first 1000 chars to console
            self.logger.info(f"Report preview:\n{report_content[:1000]}...")
        
        # Save to context if requested
        if save_to_context:
            context[save_to_context] = report_data
            self.logger.debug(f"Report data saved to context key: {save_to_context}")
        
        # Create provenance entry
        provenance = [{
            'action': 'generate_detailed_report',
            'timestamp': datetime.utcnow().isoformat(),
            'grouping_strategy': grouping_strategy,
            'include_unmatched': include_unmatched,
            'output_format': output_format,
            'output_file': output_file
        }]
        
        # Return identifiers unchanged - this is a reporting action
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'GENERATE_DETAILED_REPORT',
                'report_generated': True,
                'output_format': output_format,
                'sections_included': list(report_data.keys())
            }
        }
    
    def _generate_overview(
        self, initial_ids: Set[str], current_ids: List[str], step_results: List[Dict]
    ) -> Dict[str, Any]:
        """Generate overview statistics."""
        current_set = set(current_ids)
        
        # Calculate retention through pipeline
        retention_rate = (len(current_set) / len(initial_ids) * 100) if initial_ids else 0
        
        # Count successful vs failed steps
        successful_steps = sum(1 for step in step_results if step.get('success', False))
        
        return {
            'initial_count': len(initial_ids),
            'final_count': len(current_set),
            'retention_rate': retention_rate,
            'identifiers_lost': len(initial_ids) - len(current_set),
            'total_steps': len(step_results),
            'successful_steps': successful_steps,
            'failed_steps': len(step_results) - successful_steps
        }
    
    def _analyze_steps(
        self, step_results: List[Dict], grouping_strategy: str
    ) -> Dict[str, Any]:
        """Analyze mapping steps based on grouping strategy."""
        if grouping_strategy == 'by_step':
            return self._group_by_step(step_results)
        elif grouping_strategy == 'by_ontology':
            return self._group_by_ontology(step_results)
        elif grouping_strategy == 'by_method':
            return self._group_by_method(step_results)
        else:
            raise ValueError(f"Unknown grouping strategy: {grouping_strategy}")
    
    def _group_by_step(self, step_results: List[Dict]) -> List[Dict]:
        """Group results by execution step order."""
        grouped = []
        for i, step in enumerate(step_results):
            step_info = {
                'step_number': i + 1,
                'step_id': step.get('step_id'),
                'action_type': step.get('action_type'),
                'input_count': step.get('input_count', 0),
                'output_count': step.get('output_count', 0),
                'reduction': step.get('input_count', 0) - step.get('output_count', 0),
                'duration': step.get('duration', 0),
                'success': step.get('success', False),
                'error': step.get('error'),
                'parameters': step.get('parameters', {})
            }
            grouped.append(step_info)
        return grouped
    
    def _group_by_ontology(self, step_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group results by ontology type transitions."""
        grouped = defaultdict(list)
        for step in step_results:
            input_onto = step.get('input_ontology_type', 'unknown')
            output_onto = step.get('output_ontology_type', input_onto)
            key = f"{input_onto} → {output_onto}"
            grouped[key].append(step)
        return dict(grouped)
    
    def _group_by_method(self, step_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Group results by action type/method."""
        grouped = defaultdict(list)
        for step in step_results:
            action_type = step.get('action_type', 'unknown')
            grouped[action_type].append(step)
        return dict(grouped)
    
    def _analyze_mapping_paths(self, all_provenance: List[Dict]) -> Dict[str, Any]:
        """Analyze the mapping paths taken by identifiers."""
        path_counter = Counter()
        method_counter = Counter()
        
        # Track unique paths
        identifier_paths = defaultdict(list)
        for prov in all_provenance:
            source_id = prov.get('source_id')
            action = prov.get('action', 'unknown')
            if source_id:
                identifier_paths[source_id].append(action)
        
        # Count path patterns
        for path in identifier_paths.values():
            path_str = " → ".join(path)
            path_counter[path_str] += 1
        
        # Count methods used
        for prov in all_provenance:
            method = prov.get('method') or prov.get('action')
            if method:
                method_counter[method] += 1
        
        return {
            'unique_paths': len(path_counter),
            'most_common_paths': path_counter.most_common(10),
            'methods_used': dict(method_counter),
            'average_path_length': sum(len(p) for p in identifier_paths.values()) / len(identifier_paths) if identifier_paths else 0
        }
    
    def _track_identifier_flow(
        self, step_results: List[Dict], initial_ids: Set[str]
    ) -> Dict[str, Any]:
        """Track how identifiers flow through the pipeline."""
        flow_data = {
            'step_retention': [],
            'cumulative_loss': [],
            'new_identifiers_introduced': []
        }
        
        current_ids = initial_ids.copy()
        cumulative_lost = 0
        
        for i, step in enumerate(step_results):
            input_count = step.get('input_count', 0)
            output_count = step.get('output_count', 0)
            
            # Calculate retention for this step
            if input_count > 0:
                retention = (output_count / input_count) * 100
            else:
                retention = 0
            
            flow_data['step_retention'].append({
                'step': i + 1,
                'retention_percentage': retention,
                'identifiers_lost': input_count - output_count
            })
            
            cumulative_lost += max(0, input_count - output_count)
            flow_data['cumulative_loss'].append({
                'step': i + 1,
                'total_lost': cumulative_lost
            })
        
        return flow_data
    
    def _analyze_unmatched(
        self, initial_ids: Set[str], current_ids: List[str], mapping_results: Dict
    ) -> Dict[str, Any]:
        """Analyze unmatched identifiers."""
        current_set = set(current_ids)
        unmatched_ids = initial_ids - current_set
        
        # Categorize unmatched identifiers
        unmatched_analysis = {
            'total_unmatched': len(unmatched_ids),
            'unmatched_percentage': (len(unmatched_ids) / len(initial_ids) * 100) if initial_ids else 0,
            'categories': {
                'composite': [],
                'single': [],
                'by_prefix': defaultdict(list)
            }
        }
        
        for unmatched_id in list(unmatched_ids)[:1000]:  # Limit to first 1000
            if '_' in str(unmatched_id):
                unmatched_analysis['categories']['composite'].append(unmatched_id)
            else:
                unmatched_analysis['categories']['single'].append(unmatched_id)
            
            # Group by prefix (first 3 chars)
            prefix = str(unmatched_id)[:3]
            unmatched_analysis['categories']['by_prefix'][prefix].append(unmatched_id)
        
        # Summarize categories
        unmatched_analysis['summary'] = {
            'composite_count': len(unmatched_analysis['categories']['composite']),
            'single_count': len(unmatched_analysis['categories']['single']),
            'prefix_distribution': {
                prefix: len(ids) for prefix, ids in unmatched_analysis['categories']['by_prefix'].items()
            }
        }
        
        return unmatched_analysis
    
    def _analyze_relationships(
        self, all_provenance: List[Dict], mapping_results: Dict
    ) -> Dict[str, Any]:
        """Analyze many-to-many relationships in the mapping."""
        # Track one-to-many and many-to-one relationships
        source_to_targets = defaultdict(set)
        target_to_sources = defaultdict(set)
        
        for prov in all_provenance:
            source_id = prov.get('source_id')
            target_id = prov.get('target_id')
            if source_id and target_id:
                source_to_targets[source_id].add(target_id)
                target_to_sources[target_id].add(source_id)
        
        # Calculate relationship statistics
        one_to_many = sum(1 for targets in source_to_targets.values() if len(targets) > 1)
        many_to_one = sum(1 for sources in target_to_sources.values() if len(sources) > 1)
        
        # Find the most connected identifiers
        most_connected_sources = sorted(
            source_to_targets.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )[:10]
        
        most_connected_targets = sorted(
            target_to_sources.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )[:10]
        
        return {
            'one_to_many_count': one_to_many,
            'many_to_one_count': many_to_one,
            'average_targets_per_source': sum(len(t) for t in source_to_targets.values()) / len(source_to_targets) if source_to_targets else 0,
            'average_sources_per_target': sum(len(s) for s in target_to_sources.values()) / len(target_to_sources) if target_to_sources else 0,
            'most_connected_sources': [
                {'id': src, 'target_count': len(tgts)} 
                for src, tgts in most_connected_sources
            ],
            'most_connected_targets': [
                {'id': tgt, 'source_count': len(srcs)} 
                for tgt, srcs in most_connected_targets
            ]
        }
    
    def _format_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Format report data as Markdown."""
        lines = []
        
        # Header
        lines.append("# Detailed Mapping Report")
        lines.append(f"\nGenerated: {report_data['metadata']['generated_at']}")
        lines.append(f"Source: {report_data['metadata']['source_endpoint']} → Target: {report_data['metadata']['target_endpoint']}")
        lines.append("")
        
        # Overview
        overview = report_data['overview']
        lines.append("## Overview")
        lines.append(f"- Initial identifiers: {overview['initial_count']:,}")
        lines.append(f"- Final identifiers: {overview['final_count']:,}")
        lines.append(f"- Retention rate: {overview['retention_rate']:.1f}%")
        lines.append(f"- Total steps: {overview['total_steps']}")
        lines.append(f"- Successful steps: {overview['successful_steps']}")
        lines.append("")
        
        # Step details
        lines.append("## Step Analysis")
        if isinstance(report_data['step_details'], list):
            for step in report_data['step_details']:
                lines.append(f"\n### Step {step['step_number']}: {step['step_id']}")
                lines.append(f"- Action: {step['action_type']}")
                lines.append(f"- Input: {step['input_count']:,} → Output: {step['output_count']:,}")
                lines.append(f"- Reduction: {step['reduction']:,}")
                lines.append(f"- Duration: {step['duration']:.2f}s")
                lines.append(f"- Success: {step['success']}")
        
        # Mapping paths
        paths = report_data['mapping_paths']
        lines.append("\n## Mapping Path Analysis")
        lines.append(f"- Unique paths: {paths['unique_paths']}")
        lines.append(f"- Average path length: {paths['average_path_length']:.1f}")
        lines.append("\n### Most Common Paths:")
        for path, count in paths['most_common_paths']:
            lines.append(f"- {path}: {count:,} identifiers")
        
        # Relationship analysis
        rels = report_data['relationship_analysis']
        lines.append("\n## Relationship Analysis")
        lines.append(f"- One-to-many mappings: {rels['one_to_many_count']:,}")
        lines.append(f"- Many-to-one mappings: {rels['many_to_one_count']:,}")
        lines.append(f"- Avg targets per source: {rels['average_targets_per_source']:.2f}")
        lines.append(f"- Avg sources per target: {rels['average_sources_per_target']:.2f}")
        
        # Unmatched analysis
        if 'unmatched_analysis' in report_data:
            unmatched = report_data['unmatched_analysis']
            lines.append("\n## Unmatched Identifier Analysis")
            lines.append(f"- Total unmatched: {unmatched['total_unmatched']:,} ({unmatched['unmatched_percentage']:.1f}%)")
            lines.append(f"- Composite identifiers: {unmatched['summary']['composite_count']:,}")
            lines.append(f"- Single identifiers: {unmatched['summary']['single_count']:,}")
        
        return "\n".join(lines)
    
    def _format_html_report(self, report_data: Dict[str, Any]) -> str:
        """Format report data as HTML."""
        # Simple HTML formatting - could be enhanced with CSS
        html = ["<html><head><title>Mapping Report</title></head><body>"]
        html.append("<h1>Detailed Mapping Report</h1>")
        
        # Convert markdown content to HTML-ish format
        md_content = self._format_markdown_report(report_data)
        for line in md_content.split('\n'):
            if line.startswith('# '):
                html.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith('## '):
                html.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith('### '):
                html.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith('- '):
                html.append(f"<li>{line[2:]}</li>")
            elif line:
                html.append(f"<p>{line}</p>")
        
        html.append("</body></html>")
        return "\n".join(html)
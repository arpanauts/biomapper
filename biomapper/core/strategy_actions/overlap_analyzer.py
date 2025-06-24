"""
Analyzes overlap between two protein datasets.

This action:
- Compares two sets of protein identifiers
- Calculates intersection statistics
- Generates detailed overlap metrics
- Supports custom dataset naming
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint


@register_action("DATASET_OVERLAP_ANALYZER")
class DatasetOverlapAnalyzer(BaseStrategyAction):
    """
    Analyzes overlap between two protein datasets.
    
    Required parameters:
    - dataset1_context_key: Key in context for first dataset
    - dataset2_context_key: Key in context for second dataset
    - output_context_key: Key to store overlap results
    
    Optional parameters:
    - dataset1_name: Display name for dataset 1 (default: 'dataset1')
    - dataset2_name: Display name for dataset 2 (default: 'dataset2')
    - generate_statistics: Whether to generate detailed statistics (default: False)
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
        Execute the dataset overlap analysis.
        
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
        dataset1_key = action_params.get('dataset1_context_key')
        dataset2_key = action_params.get('dataset2_context_key')
        output_key = action_params.get('output_context_key')
        
        if not dataset1_key:
            raise ValueError("dataset1_context_key is required")
        if not dataset2_key:
            raise ValueError("dataset2_context_key is required")
        if not output_key:
            raise ValueError("output_context_key is required")
            
        # Optional parameters
        dataset1_name = action_params.get('dataset1_name', 'dataset1')
        dataset2_name = action_params.get('dataset2_name', 'dataset2')
        generate_statistics = action_params.get('generate_statistics', False)
        
        # Get datasets from context
        dataset1 = context.get(dataset1_key, [])
        dataset2 = context.get(dataset2_key, [])
        
        if not dataset1 and not dataset2:
            self.logger.warning(f"Both datasets are empty")
            return self._empty_result(dataset1_name, dataset2_name)
            
        self.logger.info(f"Analyzing overlap between {dataset1_name} ({len(dataset1)} proteins) and {dataset2_name} ({len(dataset2)} proteins)")
        
        # Convert to sets for efficient intersection
        set1 = set(dataset1)
        set2 = set(dataset2)
        
        # Calculate overlap
        overlap = set1.intersection(set2)
        overlap_list = sorted(list(overlap))  # Sort for consistent output
        
        # Prepare result
        result_data = {
            'overlapping_proteins': overlap_list,
            'overlap_count': len(overlap)
        }
        
        # Generate statistics if requested
        if generate_statistics:
            # Calculate unique counts
            unique_to_dataset1 = set1 - set2
            unique_to_dataset2 = set2 - set1
            
            statistics = {
                'counts': {
                    dataset1_name: {
                        'total': len(dataset1),
                        'unique': len(set1),
                        'unique_to_dataset': len(unique_to_dataset1)
                    },
                    dataset2_name: {
                        'total': len(dataset2),
                        'unique': len(set2),
                        'unique_to_dataset': len(unique_to_dataset2)
                    },
                    'overlap': len(overlap)
                },
                'percentages': {
                    f'overlap_in_{dataset1_name}': (len(overlap) / len(set1) * 100) if set1 else 0,
                    f'overlap_in_{dataset2_name}': (len(overlap) / len(set2) * 100) if set2 else 0
                }
            }
            
            result_data['statistics'] = statistics
            
            self.logger.info(
                f"Overlap analysis complete: {len(overlap)} proteins shared "
                f"({statistics['percentages'][f'overlap_in_{dataset1_name}']:.1f}% of {dataset1_name}, "
                f"{statistics['percentages'][f'overlap_in_{dataset2_name}']:.1f}% of {dataset2_name})"
            )
        else:
            self.logger.info(f"Found {len(overlap)} overlapping proteins")
        
        # Store in context
        context[output_key] = result_data
        
        # Create provenance
        provenance = [{
            'action': 'dataset_overlap_analysis',
            'datasets': {
                dataset1_name: {
                    'key': dataset1_key,
                    'count': len(dataset1),
                    'unique': len(set1)
                },
                dataset2_name: {
                    'key': dataset2_key,
                    'count': len(dataset2),
                    'unique': len(set2)
                }
            },
            'overlap_count': len(overlap),
            'output_key': output_key
        }]
        
        return {
            'input_identifiers': overlap_list,  # The overlapping proteins
            'output_identifiers': overlap_list,  # Same as input for this action
            'output_ontology_type': current_ontology_type,
            'provenance': provenance,
            'details': {
                'dataset1_name': dataset1_name,
                'dataset2_name': dataset2_name,
                'dataset1_count': len(set1),
                'dataset2_count': len(set2),
                'overlap_count': len(overlap),
                'statistics_generated': generate_statistics,
                'context_keys': {
                    'dataset1': dataset1_key,
                    'dataset2': dataset2_key,
                    'output': output_key
                }
            }
        }
    
    def _empty_result(self, dataset1_name: str, dataset2_name: str) -> Dict[str, Any]:
        """Return standard empty result."""
        return {
            'input_identifiers': [],
            'output_identifiers': [],
            'output_ontology_type': None,
            'provenance': [],
            'details': {
                'dataset1_name': dataset1_name,
                'dataset2_name': dataset2_name,
                'dataset1_count': 0,
                'dataset2_count': 0,
                'overlap_count': 0,
                'statistics_generated': False
            }
        }
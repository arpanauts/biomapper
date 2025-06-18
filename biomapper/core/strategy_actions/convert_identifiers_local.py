"""Convert identifiers using local endpoint data."""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig


@register_action("CONVERT_IDENTIFIERS_LOCAL")
class ConvertIdentifiersLocalAction(StrategyAction):
    """
    Convert identifiers from one ontology type to another using
    local data within a single endpoint.
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
        Execute local identifier conversion.
        
        Required action_params:
            - endpoint_context: "SOURCE" or "TARGET"
            - output_ontology_type: Target ontology type
            - input_ontology_type (optional): Override current ontology type
            - mapping_path_name (optional): Use specific mapping path for property selection
        """
        # Validate parameters
        endpoint_context = action_params.get('endpoint_context')
        if endpoint_context not in ['SOURCE', 'TARGET']:
            raise ValueError(f"Invalid endpoint_context: {endpoint_context}")
        
        output_ontology_type = action_params.get('output_ontology_type')
        if not output_ontology_type:
            raise ValueError("output_ontology_type is required")
        
        input_ontology_type = action_params.get('input_ontology_type', current_ontology_type)
        mapping_path_name = action_params.get('mapping_path_name')
        
        # Check if we should read from context
        input_from = action_params.get('input_from')
        if input_from:
            # Read identifiers from context
            context_value = context.get(input_from)
            if isinstance(context_value, list):
                # If it's a list of pairs (from matched results), extract the target identifiers
                if context_value and isinstance(context_value[0], (list, tuple)) and len(context_value[0]) == 2:
                    current_identifiers = [pair[1] for pair in context_value]  # Use target (second) identifiers
                    self.logger.info(f"Using {len(current_identifiers)} target identifiers from context['{input_from}']")
                else:
                    current_identifiers = context_value
                    self.logger.info(f"Using {len(current_identifiers)} identifiers from context['{input_from}']")
            else:
                self.logger.warning(f"Context key '{input_from}' is not a list, using current_identifiers")
        
        # Early exit for empty input
        if not current_identifiers:
            return {
                'input_identifiers': [],
                'output_identifiers': [],
                'output_ontology_type': output_ontology_type,
                'provenance': [],
                'details': {
                    'action': 'CONVERT_IDENTIFIERS_LOCAL',
                    'skipped': 'empty_input'
                }
            }
        
        # Select the appropriate endpoint
        endpoint = source_endpoint if endpoint_context == 'SOURCE' else target_endpoint
        
        self.logger.info(
            f"Converting identifiers from {input_ontology_type} to {output_ontology_type} "
            f"using {endpoint_context} endpoint ({endpoint.name})"
        )
        
        # Get the endpoint's data loader
        from biomapper.mapping.adapters.csv_adapter import CSVAdapter
        from sqlalchemy.orm import selectinload
        
        # Find property configurations for input and output ontology types
        # If mapping_path_name is provided, use it to determine specific properties
        mapping_path = None
        if mapping_path_name:
            # Get the mapping path to understand which properties to use
            from biomapper.db.models import MappingPath
            path_stmt = select(MappingPath).where(MappingPath.name == mapping_path_name)
            path_result = await self.session.execute(path_stmt)
            mapping_path = path_result.scalar_one_or_none()
            
            if not mapping_path:
                raise ValueError(f"Mapping path '{mapping_path_name}' not found")
            
            self.logger.info(f"Using mapping path '{mapping_path_name}' to determine properties")
            
            # For local conversion, we need to find the endpoint properties that match
            # the source and target types of the mapping path
            search_types = [mapping_path.source_type, mapping_path.target_type]
        else:
            search_types = [input_ontology_type, output_ontology_type]
        
        # Eagerly load the property_extraction_config relationship to avoid lazy loading issues
        stmt = (
            select(EndpointPropertyConfig)
            .options(selectinload(EndpointPropertyConfig.property_extraction_config))
            .where(
                EndpointPropertyConfig.endpoint_id == endpoint.id,
                EndpointPropertyConfig.ontology_type.in_(search_types)
            )
        )
        result = await self.session.execute(stmt)
        property_configs = result.scalars().all()
        
        input_config = None
        output_config = None
        
        if mapping_path:
            # When source and target types are the same, we need to check the mapping resource
            # to understand which properties to use
            if mapping_path.source_type == mapping_path.target_type:
                # Get the first step of the mapping path to find the resource
                from biomapper.db.models import MappingPathStep, MappingResource
                from sqlalchemy.orm import selectinload
                
                steps_stmt = (
                    select(MappingPathStep)
                    .options(selectinload(MappingPathStep.mapping_resource))
                    .where(MappingPathStep.mapping_path_id == mapping_path.id)
                    .order_by(MappingPathStep.step_order)
                )
                steps_result = await self.session.execute(steps_stmt)
                steps = steps_result.scalars().all()
                
                if steps:
                    step = steps[0]  # Use first step
                    resource = step.mapping_resource
                    
                    # Parse the resource config to understand column mappings
                    resource_config = json.loads(resource.config_template) if resource.config_template else {}
                    key_column = resource_config.get('key_column')  # Input column
                    value_column = resource_config.get('value_column')  # Output column
                    
                    self.logger.info(f"Using resource mapping: {key_column} -> {value_column}")
                    
                    # Find the property configs that match these columns
                    for config in property_configs:
                        config_pattern = json.loads(config.property_extraction_config.extraction_pattern)
                        if config.property_extraction_config.extraction_method == 'column':
                            column_name = config_pattern.get('column')
                            if column_name == key_column:
                                input_config = config
                            elif column_name == value_column:
                                output_config = config
                else:
                    raise ValueError(f"Mapping path '{mapping_path_name}' has no steps")
            else:
                # Use mapping path source/target types to determine input/output
                for config in property_configs:
                    if config.ontology_type == mapping_path.source_type:
                        input_config = config
                    elif config.ontology_type == mapping_path.target_type:
                        output_config = config
        else:
            # Use ontology types directly
            for config in property_configs:
                if config.ontology_type == input_ontology_type:
                    input_config = config
                elif config.ontology_type == output_ontology_type:
                    output_config = config
        
        if not input_config or not output_config:
            missing = []
            if not input_config:
                missing.append(input_ontology_type)
            if not output_config:
                missing.append(output_ontology_type)
            raise ValueError(
                f"Endpoint {endpoint.name} does not have configurations for ontology types: {missing}"
            )
        
        # Load the endpoint data using CSVAdapter with selective column loading
        adapter = CSVAdapter(endpoint=endpoint)
        
        # Determine which columns we need for this conversion
        # For column extraction method, parse the column name from JSON extraction_pattern
        
        # Parse extraction patterns
        input_extraction = json.loads(input_config.property_extraction_config.extraction_pattern)
        output_extraction = json.loads(output_config.property_extraction_config.extraction_pattern)
        
        # For column extraction method, get the column name
        if input_config.property_extraction_config.extraction_method == 'column':
            input_col = input_extraction.get('column')
        else:
            # For other methods, might need different parsing
            input_col = input_extraction
            
        if output_config.property_extraction_config.extraction_method == 'column':
            output_col = output_extraction.get('column')
        else:
            # For other methods, might need different parsing
            output_col = output_extraction
            
        columns_needed = [input_col, output_col]
        
        # Remove duplicates while preserving order
        columns_needed = list(dict.fromkeys(columns_needed))
        
        self.logger.info(f"Loading only required columns for conversion: {columns_needed}")
        endpoint_data = await adapter.load_data(columns_to_load=columns_needed)
        
        # Create conversion mapping
        # Build a dictionary mapping input values to output values
        conversion_map = {}
        
        for _, row in endpoint_data.iterrows():
            input_value = str(row.get(input_col, '')).strip()
            output_value = str(row.get(output_col, '')).strip()
            
            if input_value and output_value:
                # Handle one-to-many mappings by storing as lists
                if input_value not in conversion_map:
                    conversion_map[input_value] = []
                if output_value not in conversion_map[input_value]:
                    conversion_map[input_value].append(output_value)
        
        # Convert identifiers
        output_identifiers = []
        provenance = []
        unmapped_count = 0
        
        for identifier in current_identifiers:
            if identifier in conversion_map:
                # Handle one-to-many mappings
                mapped_values = conversion_map[identifier]
                for mapped_value in mapped_values:
                    output_identifiers.append(mapped_value)
                    provenance.append({
                        'source_id': identifier,
                        'source_ontology': input_ontology_type,
                        'target_id': mapped_value,
                        'target_ontology': output_ontology_type,
                        'method': 'local_conversion',
                        'endpoint': endpoint.name,
                        'confidence': 1.0
                    })
            else:
                # Keep unmapped identifier as-is
                unmapped_count += 1
                self.logger.debug(f"No conversion found for {identifier}")
        
        self.logger.info(
            f"Converted {len(current_identifiers) - unmapped_count}/{len(current_identifiers)} identifiers"
        )
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': output_ontology_type,
            'provenance': provenance,
            'details': {
                'action': 'CONVERT_IDENTIFIERS_LOCAL',
                'endpoint_used': endpoint.name,
                'conversion': f"{input_ontology_type} -> {output_ontology_type}",
                'total_input': len(current_identifiers),
                'total_converted': len(current_identifiers) - unmapped_count,
                'total_unmapped': unmapped_count,
                'total_output': len(output_identifiers)
            }
        }
"""Execute a predefined mapping path."""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import StrategyAction, ActionContext
from .registry import register_action
from biomapper.db.models import MappingPath, MappingPathStep, MappingResource, Endpoint


@register_action("EXECUTE_MAPPING_PATH")
class ExecuteMappingPathAction(StrategyAction):
    """
    Execute a predefined mapping path from the database.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            session: Database session for metamapper.db
        """
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
        Execute a mapping path.
        
        Required action_params:
            - path_name: Name of the mapping path to execute
        """
        # Validate parameters
        path_name = action_params.get('path_name')
        if not path_name:
            raise ValueError("path_name is required")
        
        self.logger.info(f"Executing mapping path: {path_name}")
        
        # Load the mapping path with eagerly loaded relationships
        from sqlalchemy.orm import selectinload
        stmt = (
            select(MappingPath)
            .options(
                selectinload(MappingPath.steps)
                .selectinload(MappingPathStep.mapping_resource)
            )
            .where(MappingPath.name == path_name)
        )
        result = await self.session.execute(stmt)
        mapping_path = result.scalar_one_or_none()
        
        if not mapping_path:
            raise ValueError(f"Mapping path '{path_name}' not found")
        
        # Get the mapping executor from context if available
        mapping_executor = context.get('mapping_executor')
        if not mapping_executor:
            raise ValueError("MappingExecutor not provided in context")
        
        # Use the mapping executor's _execute_path method
        # We need to pass the mapping path object and identifiers
        try:
            # Execute the path using the mapping executor
            result = await mapping_executor._execute_path(
                session=self.session,
                path=mapping_path,
                input_identifiers=current_identifiers,
                source_ontology=current_ontology_type,
                target_ontology=mapping_path.target_type,
                batch_size=context.get('batch_size', 250),
                filter_confidence=context.get('min_confidence', 0.0)
            )
            
            # Extract output identifiers and provenance from result
            output_identifiers = []
            provenance = []
            
            # The result is a dictionary mapping input IDs to mapping results
            # IMPORTANT: Iterate in the order of current_identifiers to preserve order
            for source_id in current_identifiers:
                if source_id not in result:
                    continue  # Skip if no result for this identifier
                mapping_result_dict = result[source_id]
                self.logger.info(f"ACTION_DEBUG: For source_id {source_id}, received mapping_result_dict: {mapping_result_dict}")
                # Use target_identifiers instead of mapped_value to handle multiple IDs
                if mapping_result_dict and 'target_identifiers' in mapping_result_dict:
                    target_ids = mapping_result_dict['target_identifiers']
                    if target_ids and isinstance(target_ids, list):
                        # Add all target IDs (e.g., when UniProt Historical Resolver returns multiple current IDs)
                        for target_id in target_ids:
                            if target_id:  # Skip None/empty values
                                output_identifiers.append(target_id)
                                provenance.append({
                                    'source_id': source_id,
                                    'source_ontology': current_ontology_type,
                                    'target_id': target_id,
                                    'target_ontology': mapping_path.target_type,
                                    'method': 'mapping_path',
                                    'path_name': path_name,
                                    'confidence': mapping_result_dict.get('confidence_score', 1.0),
                                    'mapping_source': mapping_result_dict.get('mapping_source', 'unknown')
                                })
                elif mapping_result_dict and 'mapped_value' in mapping_result_dict:
                    # Fallback to mapped_value for backward compatibility
                    mapped_value = mapping_result_dict['mapped_value']
                    if mapped_value:
                        output_identifiers.append(mapped_value)
                        provenance.append({
                            'source_id': source_id,
                            'source_ontology': current_ontology_type,
                            'target_id': mapped_value,
                            'target_ontology': mapping_path.target_type,
                            'method': 'mapping_path',
                            'path_name': path_name,
                            'confidence': mapping_result_dict.get('confidence_score', 1.0),
                            'mapping_source': mapping_result_dict.get('mapping_source', 'unknown')
                        })
            
            self.logger.info(
                f"Executed mapping path {path_name}: "
                f"{len(output_identifiers)}/{len(current_identifiers)} mapped"
            )
            
        except Exception as e:
            self.logger.error(f"Error executing mapping path {path_name}: {str(e)}")
            raise
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': mapping_path.target_type,
            'provenance': provenance,
            'details': {
                'action': 'EXECUTE_MAPPING_PATH',
                'path_name': path_name,
                'path_source_type': mapping_path.source_type,
                'path_target_type': mapping_path.target_type,
                'total_input': len(current_identifiers),
                'total_mapped': len(output_identifiers),
                'total_unmapped': len(current_identifiers) - len([p for p in provenance if p['target_id']])
            }
        }
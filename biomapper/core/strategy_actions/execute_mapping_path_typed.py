"""Execute a predefined mapping path - typed version."""

import logging
from typing import Dict, Any, List, Type, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, field_validator

from .typed_base import TypedStrategyAction, StandardActionResult
from .registry import register_action
from biomapper.db.models import MappingPath, MappingPathStep, Endpoint
from biomapper.core.models.execution_context import StrategyExecutionContext


class ExecuteMappingPathParams(BaseModel):
    """Parameters for ExecuteMappingPathAction."""
    
    path_name: str = Field(
        ...,
        description="Name of the mapping path to execute",
        min_length=1
    )
    batch_size: int = Field(
        default=250,
        description="Batch size for processing identifiers",
        gt=0,
        le=1000
    )
    min_confidence: float = Field(
        default=0.0,
        description="Minimum confidence score to accept a mapping",
        ge=0.0,
        le=1.0
    )
    
    @field_validator('path_name')
    @classmethod
    def validate_path_name(cls, v: str) -> str:
        """Ensure path name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("path_name cannot be empty or whitespace")
        return v.strip()


class MappingProvenanceRecord(BaseModel):
    """Detailed provenance record for a mapping."""
    
    source_id: str
    source_ontology: str
    target_id: str
    target_ontology: str
    method: str = "mapping_path"
    path_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    mapping_source: str = "unknown"


class ExecuteMappingPathResult(StandardActionResult):
    """Result of executing a mapping path."""
    
    # Additional fields specific to mapping path execution
    path_source_type: str = Field(description="Source type of the mapping path")
    path_target_type: str = Field(description="Target type of the mapping path")
    total_input: int = Field(description="Total number of input identifiers")
    total_mapped: int = Field(description="Total number of successfully mapped identifiers")
    total_unmapped: int = Field(description="Total number of unmapped identifiers")
    
    # Override provenance with typed version
    provenance: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Mapping provenance records"
    )


@register_action("EXECUTE_MAPPING_PATH_TYPED")
class ExecuteMappingPathTypedAction(TypedStrategyAction[ExecuteMappingPathParams, ExecuteMappingPathResult]):
    """
    Execute a predefined mapping path from the database - typed version.
    
    This is a typed implementation that provides:
    - Type-safe parameter validation
    - Structured result objects
    - Better IDE support and autocomplete
    - Backward compatibility with legacy execute() method
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            session: Database session for metamapper.db
        """
        super().__init__()
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def get_params_model(self) -> Type[ExecuteMappingPathParams]:
        """Return the parameters model class."""
        return ExecuteMappingPathParams
    
    def get_result_model(self) -> Type[ExecuteMappingPathResult]:
        """Return the result model class."""
        return ExecuteMappingPathResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ExecuteMappingPathParams,
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: StrategyExecutionContext
    ) -> ExecuteMappingPathResult:
        """
        Execute a mapping path with typed parameters.
        
        Args:
            current_identifiers: List of identifiers to map
            current_ontology_type: Current ontology type of the identifiers
            params: Typed parameters with path_name, batch_size, and min_confidence
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Typed execution context
            
        Returns:
            ExecuteMappingPathResult with mapping results and provenance
            
        Raises:
            ValueError: If mapping path not found or mapping executor not in context
        """
        self.logger.info(f"Executing mapping path: {params.path_name}")
        
        # Load the mapping path with eagerly loaded relationships
        stmt = (
            select(MappingPath)
            .options(
                selectinload(MappingPath.steps)
                .selectinload(MappingPathStep.mapping_resource)
            )
            .where(MappingPath.name == params.path_name)
        )
        result = await self.session.execute(stmt)
        mapping_path = result.scalar_one_or_none()
        
        if not mapping_path:
            raise ValueError(f"Mapping path '{params.path_name}' not found")
        
        # Get the mapping executor from context
        mapping_executor = context.get_action_data('mapping_executor')
        if not mapping_executor:
            raise ValueError("MappingExecutor not provided in context")
        
        # Execute the path using the mapping executor
        try:
            # Execute the path
            mapping_results = await mapping_executor._execute_path(
                session=self.session,
                path=mapping_path,
                input_identifiers=current_identifiers,
                source_ontology=current_ontology_type,
                target_ontology=mapping_path.target_type,
                batch_size=params.batch_size,
                filter_confidence=params.min_confidence
            )
            
            # Process results maintaining order
            output_identifiers: List[str] = []
            provenance_records: List[Dict[str, Any]] = []
            mapped_count = 0
            
            # Iterate in the order of current_identifiers to preserve order
            for source_id in current_identifiers:
                if source_id not in mapping_results:
                    continue  # Skip if no result for this identifier
                    
                mapping_result_dict = mapping_results[source_id]
                self.logger.debug(
                    f"For source_id {source_id}, received mapping_result_dict: {mapping_result_dict}"
                )
                
                # Handle multiple target IDs (e.g., from UniProt Historical Resolver)
                if mapping_result_dict and 'target_identifiers' in mapping_result_dict:
                    target_ids = mapping_result_dict['target_identifiers']
                    if target_ids and isinstance(target_ids, list):
                        mapped_count += 1
                        for target_id in target_ids:
                            if target_id:  # Skip None/empty values
                                output_identifiers.append(target_id)
                                
                                # Create typed provenance record
                                prov_record = MappingProvenanceRecord(
                                    source_id=source_id,
                                    source_ontology=current_ontology_type,
                                    target_id=target_id,
                                    target_ontology=mapping_path.target_type,
                                    path_name=params.path_name,
                                    confidence=mapping_result_dict.get('confidence_score', 1.0),
                                    mapping_source=mapping_result_dict.get('mapping_source', 'unknown')
                                )
                                provenance_records.append(prov_record.model_dump())
                                
                elif mapping_result_dict and 'mapped_value' in mapping_result_dict:
                    # Fallback to mapped_value for backward compatibility
                    mapped_value = mapping_result_dict['mapped_value']
                    if mapped_value:
                        mapped_count += 1
                        output_identifiers.append(mapped_value)
                        
                        # Create typed provenance record
                        prov_record = MappingProvenanceRecord(
                            source_id=source_id,
                            source_ontology=current_ontology_type,
                            target_id=mapped_value,
                            target_ontology=mapping_path.target_type,
                            path_name=params.path_name,
                            confidence=mapping_result_dict.get('confidence_score', 1.0),
                            mapping_source=mapping_result_dict.get('mapping_source', 'unknown')
                        )
                        provenance_records.append(prov_record.model_dump())
            
            # Calculate unmapped count
            unmapped_count = len(current_identifiers) - mapped_count
            
            self.logger.info(
                f"Executed mapping path {params.path_name}: "
                f"{len(output_identifiers)} output IDs from {mapped_count}/{len(current_identifiers)} mapped"
            )
            
            # Add execution details to context
            context.add_step_result(
                step_name=f"execute_mapping_path_{params.path_name}",
                data={
                    'path_name': params.path_name,
                    'total_input': len(current_identifiers),
                    'total_mapped': mapped_count,
                    'total_output': len(output_identifiers),
                    'batch_size': params.batch_size,
                    'min_confidence': params.min_confidence
                },
                success=True
            )
            
            # Create and return typed result
            return ExecuteMappingPathResult(
                input_identifiers=current_identifiers,
                output_identifiers=output_identifiers,
                output_ontology_type=mapping_path.target_type,
                provenance=provenance_records,
                path_source_type=mapping_path.source_type,
                path_target_type=mapping_path.target_type,
                total_input=len(current_identifiers),
                total_mapped=mapped_count,
                total_unmapped=unmapped_count,
                details={
                    'action': 'EXECUTE_MAPPING_PATH_TYPED',
                    'path_name': params.path_name,
                    'batch_size': params.batch_size,
                    'min_confidence': params.min_confidence,
                    'path_steps': len(mapping_path.steps) if mapping_path.steps else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error executing mapping path {params.path_name}: {str(e)}")
            
            # Add failure to context
            context.add_step_result(
                step_name=f"execute_mapping_path_{params.path_name}",
                data={'error': str(e), 'error_type': type(e).__name__},
                success=False
            )
            
            # Re-raise the exception to be handled by the base class
            raise


# Also register as the original name for backward compatibility
@register_action("EXECUTE_MAPPING_PATH")
class ExecuteMappingPathActionTyped(ExecuteMappingPathTypedAction):
    """Alias for backward compatibility - uses the typed implementation."""
    pass
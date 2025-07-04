"""
Example implementation of a typed strategy action.

This example shows how to create a new strategy action using the TypedStrategyAction
base class with full type safety while maintaining backward compatibility.
"""

from typing import List, Type, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction, StandardActionResult
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.db.models import Endpoint


# Step 1: Define your parameter model
class ProteinNormalizerParams(BaseModel):
    """Parameters for protein ID normalization."""
    
    # Required parameters
    normalization_type: str = Field(
        description="Type of normalization: 'uniprot', 'ensembl', or 'refseq'"
    )
    
    # Optional parameters with defaults
    strip_version: bool = Field(
        default=True,
        description="Whether to strip version numbers (e.g., P12345.2 -> P12345)"
    )
    include_isoforms: bool = Field(
        default=False,
        description="Whether to include protein isoforms"
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of IDs to process in each batch"
    )
    
    # Optional context keys for input/output
    input_context_key: Optional[str] = Field(
        default=None,
        description="Read identifiers from this context key instead of current_identifiers"
    )
    output_context_key: Optional[str] = Field(
        default=None,
        description="Store normalized identifiers in this context key"
    )


# Step 2: Define your result model (optional - can use StandardActionResult)
class ProteinNormalizerResult(StandardActionResult):
    """Result of protein normalization with additional statistics."""
    
    # Additional fields beyond the standard ones
    normalization_stats: dict = Field(
        default_factory=dict,
        description="Statistics about the normalization process"
    )
    stripped_versions: List[str] = Field(
        default_factory=list,
        description="IDs that had version numbers stripped"
    )
    invalid_format: List[str] = Field(
        default_factory=list,
        description="IDs with invalid format for the normalization type"
    )


# Step 3: Implement your action
@register_action("PROTEIN_NORMALIZER")
class ProteinNormalizer(TypedStrategyAction[ProteinNormalizerParams, ProteinNormalizerResult]):
    """
    Normalizes protein identifiers according to database-specific rules.
    
    This action demonstrates:
    - Type-safe parameter handling
    - Custom result fields
    - Context integration
    - Provenance tracking
    - Error handling
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        super().__init__()
        self.session = session
    
    def get_params_model(self) -> Type[ProteinNormalizerParams]:
        """Return the parameter model class."""
        return ProteinNormalizerParams
    
    def get_result_model(self) -> Type[ProteinNormalizerResult]:
        """Return the result model class."""
        return ProteinNormalizerResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ProteinNormalizerParams,
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: StrategyExecutionContext
    ) -> ProteinNormalizerResult:
        """
        Execute protein normalization with type safety.
        
        Args:
            current_identifiers: List of protein IDs to normalize
            current_ontology_type: Current ontology type
            params: Typed parameters for normalization
            source_endpoint: Source endpoint
            target_endpoint: Target endpoint
            context: Typed execution context
            
        Returns:
            Typed result with normalized IDs and statistics
        """
        # Get input identifiers from context if specified
        if params.input_context_key:
            input_ids = context.get_action_data(params.input_context_key, [])
            self.logger.info(f"Reading {len(input_ids)} IDs from context key: {params.input_context_key}")
        else:
            input_ids = current_identifiers
        
        # Initialize tracking
        normalized_ids = []
        stripped_versions = []
        invalid_format = []
        provenance_records = []
        
        # Process identifiers
        for identifier in input_ids:
            normalized_id = identifier
            
            # Strip version if requested
            if params.strip_version and '.' in identifier:
                base_id = identifier.split('.')[0]
                stripped_versions.append(identifier)
                normalized_id = base_id
                
                provenance_records.append({
                    "action": "strip_version",
                    "source": params.normalization_type,
                    "original": identifier,
                    "normalized": normalized_id,
                    "details": {"version_stripped": True}
                })
            
            # Validate format based on normalization type
            if params.normalization_type == "uniprot":
                # UniProt format: [OPQ][0-9][A-Z0-9]{3}[0-9]
                if not self._is_valid_uniprot(normalized_id):
                    invalid_format.append(identifier)
                    continue
            elif params.normalization_type == "ensembl":
                # Ensembl format: ENSP followed by numbers
                if not normalized_id.startswith("ENSP"):
                    invalid_format.append(identifier)
                    continue
            
            normalized_ids.append(normalized_id)
            
            # Add provenance if ID was normalized
            if normalized_id != identifier:
                provenance_records.append({
                    "action": "normalize",
                    "source": params.normalization_type,
                    "original": identifier,
                    "normalized": normalized_id,
                    "endpoint": source_endpoint.name
                })
        
        # Store in context if requested
        if params.output_context_key:
            context.set_action_data(params.output_context_key, normalized_ids)
            self.logger.info(f"Stored {len(normalized_ids)} normalized IDs in context key: {params.output_context_key}")
        
        # Update context with step result
        context.add_step_result(
            step_name="protein_normalization",
            data={
                "normalized_count": len(normalized_ids),
                "invalid_count": len(invalid_format),
                "stripped_count": len(stripped_versions)
            }
        )
        
        # Create result
        return ProteinNormalizerResult(
            input_identifiers=input_ids,
            output_identifiers=normalized_ids,
            output_ontology_type=current_ontology_type,
            provenance=provenance_records,
            details={
                "normalization_type": params.normalization_type,
                "total_processed": len(input_ids),
                "parameters": params.model_dump()
            },
            normalization_stats={
                "total_input": len(input_ids),
                "normalized": len(normalized_ids),
                "invalid_format": len(invalid_format),
                "versions_stripped": len(stripped_versions),
                "success_rate": len(normalized_ids) / len(input_ids) if input_ids else 0.0
            },
            stripped_versions=stripped_versions,
            invalid_format=invalid_format
        )
    
    def _is_valid_uniprot(self, identifier: str) -> bool:
        """Check if identifier matches UniProt format."""
        import re
        # Simplified UniProt regex
        pattern = r'^[OPQ][0-9][A-Z0-9]{3}[0-9]$'
        return bool(re.match(pattern, identifier))


# Example usage in a strategy YAML:
"""
strategies:
  - name: normalize_protein_ids
    description: Normalize protein identifiers for consistent formatting
    steps:
      - name: normalize_uniprot
        action:
          type: PROTEIN_NORMALIZER
          params:
            normalization_type: uniprot
            strip_version: true
            include_isoforms: false
            batch_size: 200
            output_context_key: normalized_proteins
            
      - name: save_results
        action:
          type: SAVE_RESULTS
          params:
            input_context_key: normalized_proteins
            output_file: normalized_proteins.csv
"""
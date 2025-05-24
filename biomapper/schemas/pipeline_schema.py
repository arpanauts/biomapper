"""
Schema definitions for the MVP0 Pipeline Orchestrator.

This module defines the Pydantic models and enums used throughout
the pipeline, including the main result model and status taxonomy.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from biomapper.schemas.mvp0_schema import QdrantSearchResultItem, PubChemAnnotation
from biomapper.mvp0_pipeline.llm_mapper import LLMChoice


class PipelineStatus(str, Enum):
    """
    Detailed status taxonomy for pipeline execution results.
    
    This enum captures all possible states of a pipeline run,
    from successful completion to various error conditions.
    """
    # Success states
    SUCCESS = "SUCCESS"  # Full pipeline success with confident mapping
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # Pipeline completed but with caveats
    
    # No result states
    NO_QDRANT_HITS = "NO_QDRANT_HITS"  # Qdrant search returned no candidates
    INSUFFICIENT_ANNOTATIONS = "INSUFFICIENT_ANNOTATIONS"  # Candidates found but couldn't be annotated
    LLM_NO_MATCH = "LLM_NO_MATCH"  # LLM evaluated candidates but found no good match
    
    # Error states by component
    COMPONENT_ERROR_QDRANT = "COMPONENT_ERROR_QDRANT"  # Error during Qdrant search
    COMPONENT_ERROR_PUBCHEM = "COMPONENT_ERROR_PUBCHEM"  # Error during PubChem annotation
    COMPONENT_ERROR_LLM = "COMPONENT_ERROR_LLM"  # Error during LLM evaluation
    
    # Other error states
    CONFIG_ERROR = "CONFIG_ERROR"  # Configuration validation or loading error
    VALIDATION_ERROR = "VALIDATION_ERROR"  # Input validation error
    UNKNOWN_ERROR = "UNKNOWN_ERROR"  # Unexpected error condition


class PipelineMappingResult(BaseModel):
    """
    Comprehensive result model for a single biochemical name mapping.
    
    This model captures all aspects of the pipeline execution including
    intermediate results, final decision, confidence metrics, and any
    errors encountered during processing.
    """
    # Input
    input_biochemical_name: str = Field(
        description="The original biochemical name that was processed"
    )
    
    # Status and overall outcome
    status: PipelineStatus = Field(
        description="The overall status of the pipeline execution"
    )
    
    # Final mapping result (if successful)
    selected_cid: Optional[int] = Field(
        default=None,
        description="The PubChem CID selected as the best match, or None if no match found"
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Confidence level of the mapping (e.g., 'High', 'Medium', 'Low')"
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Explanation for the mapping decision or lack thereof"
    )
    
    # Intermediate results from pipeline stages
    qdrant_results: Optional[List[QdrantSearchResultItem]] = Field(
        default=None,
        description="Raw results from Qdrant similarity search"
    )
    pubchem_annotations: Optional[Dict[int, PubChemAnnotation]] = Field(
        default=None,
        description="PubChem annotations keyed by CID"
    )
    llm_choice: Optional[LLMChoice] = Field(
        default=None,
        description="Detailed LLM decision including confidence and rationale"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        description="Detailed error message if any component failed"
    )
    
    # Additional processing metadata
    processing_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about processing (e.g., timings, retries)"
    )
    
    def is_successful(self) -> bool:
        """Check if the mapping was successful."""
        return self.status in [PipelineStatus.SUCCESS, PipelineStatus.PARTIAL_SUCCESS]
    
    def has_mapping(self) -> bool:
        """Check if a CID mapping was produced."""
        return self.selected_cid is not None
    
    def get_confidence_score(self) -> Optional[float]:
        """
        Get a numerical confidence score if available.
        
        Returns:
            Float between 0.0 and 1.0, or None if not available
        """
        if self.llm_choice and self.llm_choice.llm_confidence is not None:
            return self.llm_choice.llm_confidence
        
        # Convert string confidence to score if needed
        if self.confidence:
            confidence_map = {
                "high": 0.9,
                "medium": 0.6,
                "low": 0.3
            }
            return confidence_map.get(self.confidence.lower())
        
        return None
    
    def summary(self) -> str:
        """
        Generate a human-readable summary of the mapping result.
        
        Returns:
            String summary of the mapping outcome
        """
        if self.is_successful() and self.has_mapping():
            conf_str = f" (confidence: {self.confidence})" if self.confidence else ""
            return f"Successfully mapped '{self.input_biochemical_name}' to CID {self.selected_cid}{conf_str}"
        elif self.status == PipelineStatus.NO_QDRANT_HITS:
            return f"No candidates found for '{self.input_biochemical_name}' in Qdrant search"
        elif self.status == PipelineStatus.LLM_NO_MATCH:
            return f"No suitable match found for '{self.input_biochemical_name}' among {len(self.qdrant_results or [])} candidates"
        elif self.error_message:
            return f"Failed to map '{self.input_biochemical_name}': {self.error_message}"
        else:
            return f"Mapping for '{self.input_biochemical_name}' completed with status: {self.status}"
    
    class Config:
        """Pydantic model configuration."""
        # Allow using the enum values as strings in JSON
        use_enum_values = True


# Batch result model for processing multiple names
class BatchMappingResult(BaseModel):
    """
    Result model for batch processing of multiple biochemical names.
    """
    total_processed: int = Field(
        description="Total number of names processed"
    )
    successful_mappings: int = Field(
        description="Number of successful mappings (with CID)"
    )
    failed_mappings: int = Field(
        description="Number of failed mappings"
    )
    results: List[PipelineMappingResult] = Field(
        description="Individual results for each biochemical name"
    )
    processing_time_seconds: Optional[float] = Field(
        default=None,
        description="Total processing time in seconds"
    )
    
    def get_success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.successful_mappings / self.total_processed) * 100
    
    def get_results_by_status(self, status: PipelineStatus) -> List[PipelineMappingResult]:
        """Get all results with a specific status."""
        return [r for r in self.results if r.status == status]
    
    def summary(self) -> str:
        """Generate a summary of the batch processing."""
        return (
            f"Processed {self.total_processed} biochemical names: "
            f"{self.successful_mappings} successful mappings "
            f"({self.get_success_rate():.1f}% success rate)"
        )


# Example usage and validation
if __name__ == "__main__":
    print("Testing Pipeline Schema Models...")
    print("-" * 60)
    
    # Test PipelineStatus enum
    print("Pipeline Status Values:")
    for status in PipelineStatus:
        print(f"  - {status.value}")
    
    print("\n" + "-" * 60)
    
    # Test creating a successful result
    success_result = PipelineMappingResult(
        input_biochemical_name="glucose",
        status=PipelineStatus.SUCCESS,
        selected_cid=5793,
        confidence="High",
        rationale="Direct title match with common synonym",
        qdrant_results=[
            QdrantSearchResultItem(cid=5793, score=0.95),
            QdrantSearchResultItem(cid=107526, score=0.88)
        ],
        processing_details={
            "qdrant_search_time": 0.125,
            "pubchem_annotation_time": 0.850,
            "llm_decision_time": 1.234
        }
    )
    
    print("Success Result Example:")
    print(f"  Name: {success_result.input_biochemical_name}")
    print(f"  Status: {success_result.status}")
    print(f"  Selected CID: {success_result.selected_cid}")
    print(f"  Summary: {success_result.summary()}")
    
    print("\n" + "-" * 60)
    
    # Test creating an error result
    error_result = PipelineMappingResult(
        input_biochemical_name="unknown_compound_xyz",
        status=PipelineStatus.NO_QDRANT_HITS,
        error_message="No similar compounds found in the vector database"
    )
    
    print("Error Result Example:")
    print(f"  Name: {error_result.input_biochemical_name}")
    print(f"  Status: {error_result.status}")
    print(f"  Summary: {error_result.summary()}")
    
    print("\n" + "-" * 60)
    
    # Test batch result
    batch_result = BatchMappingResult(
        total_processed=3,
        successful_mappings=2,
        failed_mappings=1,
        results=[success_result, error_result],
        processing_time_seconds=5.67
    )
    
    print("Batch Result Example:")
    print(f"  {batch_result.summary()}")
    print(f"  Processing time: {batch_result.processing_time_seconds:.2f}s")
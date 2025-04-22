"""
Models related to mapping operations.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field


class MappingStatus(str, Enum):
    """Status of a mapping job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MappingJobCreate(BaseModel):
    """Request model for creating a mapping job."""
    session_id: str
    id_columns: List[str] = Field(..., description="Columns containing identifiers to map")
    target_ontologies: List[str] = Field(..., description="Target ontologies to map to")
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional mapping options"
    )


class MappingJobResponse(BaseModel):
    """Response model for mapping job creation."""
    job_id: str
    session_id: str
    created_at: datetime
    status: MappingStatus = MappingStatus.PENDING


class JobStatus(BaseModel):
    """Response model for job status."""
    job_id: str
    status: MappingStatus
    progress: Optional[float] = Field(
        default=None, description="Progress percentage (0-100)"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: datetime
    updated_at: datetime


class MappingResultSummary(BaseModel):
    """Summary statistics for mapping results."""
    total_records: int
    mapped_records: int
    mapping_rate: float
    ontologies_used: List[str]
    column_stats: Dict[str, Dict[str, Any]]


class MappingResults(BaseModel):
    """Response model for mapping results."""
    job_id: str
    summary: MappingResultSummary
    preview: List[Dict[str, Any]]
    download_url: str
    completed_at: datetime


class RelationshipMappingRequest(BaseModel):
    """Request model for endpoint-to-endpoint relationship mapping."""
    relationship_id: int = Field(..., description="ID of the relationship to use for mapping")
    source_data: Dict[str, Any] = Field(
        ..., description="Source data containing values to be mapped (e.g., HMDB IDs, names, etc.)"
    )


class MappingResult(BaseModel):
    """Model for a single mapping result."""
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    confidence: float
    path_id: Optional[int] = None


class RelationshipMappingResponse(BaseModel):
    """Response model for endpoint-to-endpoint relationship mapping."""
    relationship_id: int
    source_data: Dict[str, Any]
    results: List[MappingResult]
    timestamp: datetime = Field(default_factory=datetime.now)

"""Action result models for biomapper core."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Status(str, Enum):
    """Status of an action result."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class ProvenanceRecord(BaseModel):
    """Record of data provenance for tracking sources and transformations.

    Attributes:
        source: The data source (e.g., "UniProt", "HGNC")
        timestamp: When the data was retrieved or action performed
        version: Optional version of the data source
        confidence_score: Optional confidence score between 0 and 1
        method: Optional method used for mapping
        evidence_codes: Optional list of evidence codes
    """

    model_config = ConfigDict(strict=True)

    source: str
    timestamp: datetime
    version: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    method: Optional[str] = None
    evidence_codes: Optional[List[str]] = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source is not empty."""
        if not v:
            raise ValueError("source cannot be empty")
        return v


class ActionResult(BaseModel):
    """Result of an action execution.

    Attributes:
        action_type: Type of action performed
        identifier: The input identifier
        source_type: Source identifier type
        target_type: Target identifier type
        mapped_identifier: The mapped identifier (if successful)
        status: Status of the action (success, failed, pending)
        provenance: Optional provenance information
        metadata: Additional metadata about the mapping
        error: Error message if action failed
    """

    model_config = ConfigDict(strict=False)  # Allow string to Status conversion

    action_type: str
    identifier: str
    source_type: str
    target_type: str
    mapped_identifier: Optional[str] = None
    status: Status
    provenance: Optional[ProvenanceRecord] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate identifier is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("identifier cannot be empty or whitespace")
        return v

    @field_validator("action_type", "source_type", "target_type")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are not empty."""
        if not v:
            raise ValueError("Field cannot be empty")
        return v

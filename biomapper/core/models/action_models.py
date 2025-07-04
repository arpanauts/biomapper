"""Action parameter models for biomapper core."""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ExecuteMappingPathParams(BaseModel):
    """Parameters for executing a mapping path action.

    Attributes:
        identifier: The identifier to map
        source_type: The source identifier type
        target_type: The target identifier type
        batch_size: Number of items to process in a batch
        min_confidence: Minimum confidence score (0-1)
        include_deprecated: Whether to include deprecated mappings
        max_retries: Maximum number of retry attempts
    """

    model_config = ConfigDict(strict=True)

    identifier: str
    source_type: str
    target_type: str
    batch_size: int = Field(default=50, gt=0)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    include_deprecated: bool = False
    max_retries: int = Field(default=3, ge=0)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate identifier is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("identifier cannot be empty or whitespace")
        return v

    @field_validator("source_type", "target_type")
    @classmethod
    def validate_type_fields(cls, v: str) -> str:
        """Validate type fields are not empty."""
        if not v:
            raise ValueError("Type field cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_source_target_different(self) -> "ExecuteMappingPathParams":
        """Validate that source and target types are different."""
        if self.source_type == self.target_type:
            raise ValueError("source_type and target_type cannot be the same")
        return self

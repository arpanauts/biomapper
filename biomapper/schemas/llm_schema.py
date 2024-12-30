"""Schema definitions for LLM-based mapping components."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MatchConfidence(str, Enum):
    """Confidence level for a mapping match."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class LLMMatch(BaseModel):
    """Represents a single mapping match from the LLM."""

    target_id: str = Field(..., description="Target identifier in the mapped ontology")
    target_name: str = Field(
        ..., description="Target name/label in the mapped ontology"
    )
    confidence: MatchConfidence = Field(
        ..., description="Confidence level of the match"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Numerical confidence score")
    reasoning: str = Field(..., description="LLM's reasoning for the match")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )


class LLMMapperMetrics(BaseModel):
    """Metrics for LLM mapping operations."""

    tokens_used: int = Field(..., description="Number of tokens used in the operation")
    latency_ms: float = Field(..., description="Operation latency in milliseconds")
    provider: str = Field(..., description="LLM provider used (e.g., OpenAI)")
    model: str = Field(..., description="Model identifier used")
    cost: float = Field(..., description="Estimated cost of the operation in USD")


class LLMMapperResult(BaseModel):
    """Complete result from an LLM mapping operation."""

    query_term: str = Field(..., description="Original query term")
    matches: List[LLMMatch] = Field(..., description="List of potential matches")
    best_match: Optional[LLMMatch] = Field(None, description="Best match if available")
    metrics: LLMMapperMetrics = Field(..., description="Operation metrics")
    trace_id: str = Field(..., description="Langfuse trace identifier")

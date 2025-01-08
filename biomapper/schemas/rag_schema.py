from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class CompoundDocument(BaseModel):
    """Schema for compound documents in vector store."""

    content: str
    metadata: Dict[str, str]
    embedding: Optional[List[float]] = None


class PromptTemplate(BaseModel):
    """Schema for prompt templates."""

    name: str
    template: str
    version: str
    metrics: Optional[Dict[str, float]] = None


class Match(BaseModel):
    """Schema for a single compound match."""

    id: str
    name: str
    confidence: str
    reasoning: str
    target_name: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMMapperResult(BaseModel):
    """Schema for LLM mapper results."""

    query_term: str
    best_match: Match
    matches: List[Match]
    trace_id: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    error: Optional[str] = None


class OptimizationMetrics(BaseModel):
    """Schema for optimization metrics."""

    accuracy: float
    latency: float
    cost: Optional[float] = None
    custom_metrics: Optional[Dict[str, Any]] = None


class RAGMetrics(BaseModel):
    """Schema for RAG operation metrics."""

    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    tokens_used: int
    context_relevance: Optional[float] = None
    answer_faithfulness: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary with standardized keys.

        Returns:
            dict[str, Any]: Dictionary of metrics with standardized keys
        """
        return {
            "retrieval_latency": self.retrieval_latency_ms,
            "generation_latency": self.generation_latency_ms,
            "total_latency": self.total_latency_ms,
            "tokens": self.tokens_used,
            "context_relevance": self.context_relevance,
            "faithfulness": self.answer_faithfulness,
        }

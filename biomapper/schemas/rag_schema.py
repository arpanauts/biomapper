from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class MappingResultItem(BaseModel):
    """Schema for individual mapping result with confidence scores.

    Attributes:
        identifier: The input identifier that was mapped
        target_ids: List of mapped target identifiers (e.g., ["PUBCHEM:123456"])
        component_id: Component identifier or additional info (often stores confidence as string)
        confidence: General confidence score (0.0 to 1.0)
        qdrant_similarity_score: Raw similarity score from Qdrant vector search.
                               For cosine distance: higher values (closer to 1.0) indicate better similarity.
                               For Euclidean distance: lower values (closer to 0.0) indicate better similarity.
        metadata: Additional metadata including all scores, distance metric, and interpretation
    """

    identifier: str
    target_ids: Optional[List[str]] = None
    component_id: Optional[str] = None
    confidence: Optional[float] = None
    qdrant_similarity_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MappingOutput(BaseModel):
    """Schema for complete mapping output.

    Attributes:
        results: List of MappingResultItem objects containing detailed mapping results
        metadata: Global metadata about the mapping operation including:
                 - collection: Qdrant collection name used
                 - embedding_model: Name of the embedding model
                 - distance_metric: Distance metric used (e.g., "Cosine")
                 - top_k: Number of top results requested
                 - score_threshold: Minimum score threshold used
    """

    results: List[MappingResultItem]
    metadata: Optional[Dict[str, Any]] = None


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

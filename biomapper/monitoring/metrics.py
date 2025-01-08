"""Metrics tracking for RAG operations."""
from typing import Optional

from langfuse.decorators import observe
from biomapper.monitoring.langfuse_tracker import LangfuseTracker
from biomapper.schemas.rag_schema import RAGMetrics


class MetricsTracker:
    """Track and record RAG metrics."""

    def __init__(self, langfuse: Optional[LangfuseTracker] = None) -> None:
        """Initialize metrics tracker.

        Args:
            langfuse: Optional Langfuse tracker for observability
        """
        self.langfuse = langfuse

    @observe(name="record_metrics")  # type: ignore[misc]
    def record_metrics(self, metrics: RAGMetrics, trace_id: str) -> None:
        """Record metrics with optional Langfuse integration.

        Args:
            metrics: RAG metrics to record
            trace_id: Trace ID for Langfuse
        """
        if not self.langfuse or not self.langfuse.client:
            return

        try:
            trace = self.langfuse.client.trace(trace_id)
            trace.metrics()  # Initialize metrics recording

            # Record individual metrics
            trace.score(
                name="retrieval_latency",
                value=metrics.retrieval_latency_ms,
                comment="Time taken for context retrieval",
            )
            trace.score(
                name="generation_latency",
                value=metrics.generation_latency_ms,
                comment="Time taken for answer generation",
            )
            trace.score(
                name="total_latency",
                value=metrics.total_latency_ms,
                comment="Total processing time",
            )
            trace.score(
                name="tokens",
                value=metrics.tokens_used,
                comment="Number of tokens used",
            )

            if metrics.context_relevance is not None:
                trace.score(
                    name="context_relevance",
                    value=metrics.context_relevance,
                    comment="Relevance of retrieved context",
                )

            if metrics.answer_faithfulness is not None:
                trace.score(
                    name="faithfulness",
                    value=metrics.answer_faithfulness,
                    comment="Faithfulness of generated answer",
                )

        except Exception as e:
            print(f"[ERROR] Failed to record metrics in Langfuse: {e}")

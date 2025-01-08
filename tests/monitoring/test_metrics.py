"""Tests for metrics tracking."""
import pytest
from unittest.mock import Mock

from biomapper.monitoring.metrics import MetricsTracker
from biomapper.schemas.rag_schema import RAGMetrics
from biomapper.monitoring.langfuse_tracker import LangfuseTracker


@pytest.fixture
def sample_metrics() -> RAGMetrics:
    """Sample RAG metrics."""
    return RAGMetrics(
        retrieval_latency_ms=100.0,
        generation_latency_ms=200.0,
        total_latency_ms=300.0,
        tokens_used=100,
        context_relevance=0.9,
        answer_faithfulness=0.85,
    )


def test_metrics_to_dict(sample_metrics: RAGMetrics) -> None:
    """Test converting metrics to dictionary."""
    metrics_dict = sample_metrics.to_dict()
    assert metrics_dict["retrieval_latency"] == 100.0
    assert metrics_dict["generation_latency"] == 200.0
    assert metrics_dict["tokens"] == 100
    assert metrics_dict["context_relevance"] == 0.9
    assert metrics_dict["faithfulness"] == 0.85


def test_metrics_tracker_without_langfuse() -> None:
    """Test metrics tracker without Langfuse."""
    tracker = MetricsTracker()
    metrics = RAGMetrics(
        retrieval_latency_ms=100.0,
        generation_latency_ms=200.0,
        total_latency_ms=300.0,
        tokens_used=100,
    )

    # Should not raise any errors
    tracker.record_metrics(metrics, "test_trace")


def test_metrics_tracker_with_langfuse() -> None:
    """Test metrics tracker with Langfuse."""
    mock_langfuse = Mock()
    mock_trace = Mock()
    mock_langfuse.client.trace.return_value = mock_trace

    tracker = MetricsTracker(LangfuseTracker())
    tracker.langfuse = mock_langfuse

    metrics = RAGMetrics(
        retrieval_latency_ms=100.0,
        generation_latency_ms=200.0,
        total_latency_ms=300.0,
        tokens_used=100,
    )

    tracker.record_metrics(metrics, "test_trace")
    mock_trace.metrics.assert_called_once()


def test_metrics_recording() -> None:
    """Test recording metrics with Langfuse."""
    # Mock Langfuse tracker
    mock_trace = Mock()
    mock_client = Mock()
    mock_client.trace.return_value = mock_trace

    mock_tracker = Mock(spec=LangfuseTracker)
    mock_tracker.client = mock_client

    # Create metrics
    metrics = RAGMetrics(
        retrieval_latency_ms=100.0,
        generation_latency_ms=200.0,
        total_latency_ms=300.0,
        tokens_used=1000,
    )

    # Record metrics
    tracker = MetricsTracker(mock_tracker)
    tracker.record_metrics(metrics, "test_trace")

    # Verify Langfuse calls
    mock_client.trace.assert_called_once_with("test_trace")
    mock_trace.score.assert_any_call(
        name="retrieval_latency",
        value=100.0,
        comment="Time taken for context retrieval",
    )
    mock_trace.score.assert_any_call(
        name="generation_latency",
        value=200.0,
        comment="Time taken for answer generation",
    )


def test_metrics_recording_no_langfuse() -> None:
    """Test recording metrics without Langfuse."""
    tracker = MetricsTracker(None)
    metrics = RAGMetrics(
        retrieval_latency_ms=100.0,
        generation_latency_ms=200.0,
        total_latency_ms=300.0,
        tokens_used=1000,
    )
    tracker.record_metrics(metrics, None)  # Should not raise any errors

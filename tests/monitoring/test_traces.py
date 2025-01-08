"""Tests for trace management."""
import pytest
from unittest.mock import Mock
from typing import List, Dict, Any

from biomapper.monitoring.traces import TraceManager
from biomapper.monitoring.langfuse_tracker import LangfuseTracker


@pytest.fixture
def mock_traces() -> List[Dict[str, Any]]:
    """Mock trace data."""
    return [
        {"id": "trace1", "duration": 100, "error": None},
        {"id": "trace2", "duration": 200, "error": {"type": "validation_error"}},
    ]


def test_analyze_traces_without_langfuse() -> None:
    """Test trace analysis without Langfuse."""
    manager = TraceManager()
    analysis = manager.analyze_traces()
    assert analysis == {}


def test_analyze_traces_with_langfuse(mock_traces: List[Dict[str, Any]]) -> None:
    """Test trace analysis with Langfuse."""
    mock_langfuse = Mock()
    mock_langfuse.client.traces.return_value = mock_traces

    manager = TraceManager(LangfuseTracker())
    manager.langfuse = mock_langfuse

    analysis = manager.analyze_traces("24h")

    assert analysis["total_traces"] == 2
    assert analysis["success_rate"] == 0.5
    assert analysis["error_types"]["validation_error"] == 1
    assert "avg_latency" in analysis


def test_analyze_traces_empty() -> None:
    """Test trace analysis with no traces."""
    mock_langfuse = Mock()
    mock_langfuse.client.traces.return_value = []

    manager = TraceManager(LangfuseTracker())
    manager.langfuse = mock_langfuse

    analysis = manager.analyze_traces()
    assert analysis == {}

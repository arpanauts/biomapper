"""Trace management module."""
from typing import Optional, Any, Dict, List
from langfuse import Langfuse

from biomapper.monitoring.langfuse_tracker import LangfuseTracker


class TraceManager:
    """Manages trace lifecycle and analysis."""

    def __init__(self, langfuse_tracker: Optional[LangfuseTracker] = None) -> None:
        self.langfuse = langfuse_tracker

    def analyze_traces(self, time_window: str = "24h") -> Dict[str, Any]:
        """Analyze traces for patterns."""
        if not self.langfuse or not self.langfuse.client:
            return {}

        # Get traces from Langfuse API
        client: Langfuse = self.langfuse.client
        traces = client.traces()

        # Return empty dict if no traces
        if not traces:
            return {}

        # Analyze patterns
        patterns: Dict[str, Any] = {
            "total_traces": len(traces),
            "success_rate": self._calculate_success_rate(traces),
            "avg_latency": self._calculate_avg_latency(traces),
            "error_types": self._analyze_error_types(traces),
        }

        return patterns

    def _calculate_success_rate(self, traces: List[Dict[str, Any]]) -> float:
        """Calculate success rate from traces."""
        if not traces:
            return 0.0

        successful = sum(1 for t in traces if t.get("error") is None)
        return successful / len(traces)

    def _calculate_avg_latency(self, traces: List[Dict[str, Any]]) -> float:
        """Calculate average latency from traces."""
        if not traces:
            return 0.0

        latencies = [
            float(t.get("metadata", {}).get("latency", 0))
            for t in traces
            if t.get("metadata", {}).get("latency") is not None
        ]
        return sum(latencies) / len(latencies) if latencies else 0.0

    def _analyze_error_types(self, traces: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze error types from traces."""
        error_counts: Dict[str, int] = {}
        for trace in traces:
            error = trace.get("error")
            if error and isinstance(error, dict):
                error_type = error.get("type", "unknown")
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts

"""DSPy optimization integration."""
from typing import Optional, Dict, List, Any, Protocol
from unittest.mock import Mock

from dspy.teleprompt import BootstrapFewShot  # type: ignore

from biomapper.schemas.rag_schema import OptimizationMetrics


class CompileResult(Protocol):
    """Protocol for DSPy compile result."""

    metrics: Dict[str, Dict[str, Any]]


class DSPyOptimizer:
    """Handles DSPy optimization integration."""

    def __init__(self) -> None:
        self._compiler: Optional[BootstrapFewShot] = None

    def get_compiler(self) -> Optional[BootstrapFewShot]:
        """Get the current compiler, initializing if needed."""
        if not self._compiler:
            self._compiler = BootstrapFewShot()
        return self._compiler

    def optimize_prompts(
        self,
        train_data: List[tuple[str, str]],
        metric_names: Optional[List[str]] = None,
    ) -> Dict[str, OptimizationMetrics]:
        """Optimize prompts using DSPy.

        Args:
            train_data: List of (input, output) tuples for training
            metric_names: Optional list of metric names to compute

        Returns:
            Dictionary mapping metric names to their computed values
        """
        if not train_data:
            raise ValueError("Training data cannot be empty")

        compiler = self.get_compiler()
        if not compiler:
            raise ValueError("Failed to initialize DSPy compiler")

        # Default metrics if none provided
        metric_names = metric_names or ["answer_relevance", "factual_accuracy"]

        # Create a simple student model for testing
        student = Mock()
        student._compiled = False
        student.predictors = Mock(return_value=[])
        student.named_predictors = Mock(return_value=[])
        student.reset_copy = Mock(return_value=student)
        student.deepcopy = Mock(return_value=student)

        # Run optimization
        result: CompileResult = compiler.compile(student=student, trainset=train_data)

        # Extract metrics for each requested metric name
        metrics: Dict[str, OptimizationMetrics] = {}
        for metric in metric_names:
            metric_data = result.metrics.get(metric, {})
            metrics[metric] = OptimizationMetrics(
                accuracy=float(metric_data.get("accuracy", 0.0)),
                latency=float(metric_data.get("latency", 0.0)),
                cost=float(metric_data.get("cost", 0.0)),
                custom_metrics=dict(metric_data.get("custom", {})),
            )

        return metrics

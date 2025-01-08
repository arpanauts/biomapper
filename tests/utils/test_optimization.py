"""Tests for optimization utilities."""
import pytest
from unittest.mock import Mock, patch
from typing import Any, Dict

from biomapper.utils.optimization import DSPyOptimizer
from biomapper.schemas.rag_schema import OptimizationMetrics


@pytest.fixture
def mock_metrics() -> Dict[str, Dict[str, Any]]:
    """Get mock metrics with proper types."""
    return {
        "answer_relevance": {
            "accuracy": 0.9,
            "latency": 100.0,
            "cost": 0.01,
            "custom": {"f1": 0.85},
        },
        "factual_accuracy": {
            "accuracy": 0.85,
            "latency": 120.0,
            "cost": 0.015,
            "custom": {"precision": 0.88},
        },
        "custom_metric1": {
            "accuracy": 0.92,
            "latency": 90.0,
            "cost": 0.02,
            "custom": {},
        },
        "custom_metric2": {
            "accuracy": 0.88,
            "latency": 110.0,
            "cost": 0.018,
            "custom": {},
        },
    }


@pytest.fixture
def mock_dspy_compiler(mock_metrics: Dict[str, Dict[str, Any]]) -> Mock:
    """Mock DSPy compiler."""
    # Create a mock result with metrics as a real dictionary
    mock_result = Mock()
    mock_result.metrics = mock_metrics

    # Create a mock BootstrapFewShot class
    mock_bootstrap = Mock()
    # Create a mock compiler instance
    mock_compiler_instance = Mock()
    mock_compiler_instance.compile = Mock(return_value=mock_result)
    mock_bootstrap.return_value = mock_compiler_instance

    return mock_bootstrap


def test_optimize_prompts(mock_dspy_compiler: Mock) -> None:
    """Test prompt optimization."""
    # Patch the exact import path used in DSPyOptimizer
    with patch("biomapper.utils.optimization.BootstrapFewShot", mock_dspy_compiler):
        optimizer = DSPyOptimizer()

        # Data format doesn't matter since we're fully mocking
        train_data = [("input1", "output1"), ("input2", "output2")]
        metrics = optimizer.optimize_prompts(train_data)

        # Verify metrics structure
        assert isinstance(metrics, dict)
        assert "answer_relevance" in metrics
        assert "factual_accuracy" in metrics
        assert isinstance(metrics["answer_relevance"], OptimizationMetrics)
        assert metrics["answer_relevance"].accuracy == 0.9
        assert metrics["answer_relevance"].latency == 100.0


def test_optimize_prompts_custom_metrics(mock_dspy_compiler: Mock) -> None:
    """Test optimization with custom metrics."""
    # Patch the exact import path used in DSPyOptimizer
    with patch("biomapper.utils.optimization.BootstrapFewShot", mock_dspy_compiler):
        optimizer = DSPyOptimizer()

        train_data = [("input1", "output1")]
        custom_metrics = ["custom_metric1", "custom_metric2"]
        metrics = optimizer.optimize_prompts(train_data, metric_names=custom_metrics)

        # Verify metrics structure
        assert set(metrics.keys()) == set(custom_metrics)
        for metric in custom_metrics:
            assert isinstance(metrics[metric], OptimizationMetrics)
            assert metrics[metric].accuracy > 0
            assert metrics[metric].latency > 0
            assert metrics[metric].cost is not None


def test_optimize_prompts_no_data() -> None:
    """Test optimization with empty training data."""
    optimizer = DSPyOptimizer()

    with pytest.raises(ValueError):
        optimizer.optimize_prompts([])

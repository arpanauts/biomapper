"""Tests for base mapping interfaces."""

import pytest
from unittest.mock import Mock, AsyncMock
import time
from typing import List, Optional

from biomapper.mapping.base import (
    MappingProvider,
    MappingResult,
    MetricsContext,
    MappingError,
    ValidationError,
    ConnectionError,
    RateLimitError,
)


class MockProvider(MappingProvider):
    """Mock provider for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validate_calls: List[str] = []
        self.map_calls: List[str] = []
        self.should_fail = False

    async def validate_identifier(self, identifier: str) -> bool:
        self.validate_calls.append(identifier)
        if self.should_fail:
            raise ValidationError("Mock validation error")
        return True

    async def map_identifier(
        self, identifier: str, target_type: Optional[str] = None, **kwargs
    ):
        self.map_calls.append(identifier)
        if self.should_fail:
            raise MappingError("Mock mapping error")
        return MappingResult(
            input_value=identifier, target_id="MOCK:123", confidence_score=0.9
        )

    async def map_batch(
        self, identifiers: List[str], target_type: Optional[str] = None, **kwargs
    ):
        results = []
        for identifier in identifiers:
            results.append(await self.map_identifier(identifier, target_type, **kwargs))
        return results


@pytest.fixture
def mock_metrics():
    """Create mock metrics tracker."""
    return Mock(
        start_operation=Mock(return_value="trace_123"),
        end_operation=Mock(),
        record_error=Mock(),
    )


@pytest.fixture
def mock_langfuse():
    """Create mock Langfuse tracker."""
    return Mock(record_duration=AsyncMock())


@pytest.fixture
def provider(mock_metrics, mock_langfuse):
    """Create mock provider with metrics."""
    return MockProvider(metrics=mock_metrics, langfuse=mock_langfuse)


async def test_metrics_context_success(mock_metrics, mock_langfuse):
    """Test metrics are recorded on successful operation."""
    async with MetricsContext("test_op", mock_metrics, mock_langfuse) as ctx:
        assert ctx.operation == "test_op"
        time.sleep(0.1)  # Simulate work

    mock_metrics.start_operation.assert_called_once_with("test_op")
    mock_metrics.end_operation.assert_called_once()
    mock_langfuse.record_duration.assert_called_once()

    # Verify duration was recorded
    duration = mock_metrics.end_operation.call_args[0][1]["duration"]
    assert duration >= 0.1


async def test_metrics_context_error(mock_metrics):
    """Test error is recorded in metrics."""
    with pytest.raises(ValueError):
        async with MetricsContext("test_op", mock_metrics):
            raise ValueError("Test error")

    mock_metrics.record_error.assert_called_once_with("test_op_error", "Test error")


async def test_provider_validation(provider):
    """Test identifier validation."""
    assert await provider.validate_identifier("test:123")
    assert "test:123" in provider.validate_calls


async def test_provider_mapping(provider):
    """Test identifier mapping."""
    result = await provider.map_identifier("test:123")
    assert isinstance(result, MappingResult)
    assert result.input_value == "test:123"
    assert result.target_id == "MOCK:123"
    assert "test:123" in provider.map_calls


async def test_provider_batch_mapping(provider):
    """Test batch mapping."""
    results = await provider.map_batch(["test:1", "test:2"])
    assert len(results) == 2
    assert all(isinstance(r, MappingResult) for r in results)
    assert "test:1" in provider.map_calls
    assert "test:2" in provider.map_calls


async def test_provider_error_handling(provider):
    """Test error handling."""
    provider.should_fail = True

    with pytest.raises(ValidationError):
        await provider.validate_identifier("test:123")

    with pytest.raises(MappingError):
        await provider.map_identifier("test:123")


async def test_operation_tracking(provider):
    """Test operation tracking wrapper."""
    result = await provider._track_operation(
        "test_op", provider.map_identifier, "test:123"
    )

    assert isinstance(result, MappingResult)
    provider.metrics.start_operation.assert_called_once_with("test_op")
    provider.metrics.end_operation.assert_called_once()
    await provider.langfuse.record_duration.assert_called_once()

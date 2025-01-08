"""Tests for Langfuse tracking."""
import os
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from biomapper.monitoring.langfuse_tracker import (
    LangfuseTracker,
    create_langfuse_client,
)


@pytest.fixture
def mock_langfuse_context() -> Generator[Mock, None, None]:
    """Mock Langfuse context."""
    with patch(
        "biomapper.monitoring.langfuse_tracker.langfuse_context"
    ) as mock_context:
        mock_context.get_current_trace_id.return_value = "test_trace_id"
        yield mock_context


@pytest.fixture
def env_vars() -> dict[str, str]:
    """Test environment variables."""
    return {
        "LANGFUSE_PUBLIC_KEY": "test_public_key",
        "LANGFUSE_SECRET_KEY": "test_secret_key",
        "LANGFUSE_HOST": "https://test.langfuse.com",
    }


def test_create_langfuse_client(env_vars: dict[str, str]) -> None:
    """Test Langfuse client creation function."""
    with patch("biomapper.monitoring.langfuse_tracker.Langfuse") as mock_langfuse_cls:
        mock_client = Mock()
        mock_langfuse_cls.return_value = mock_client

        # Test with valid credentials
        client = create_langfuse_client(
            public_key=env_vars["LANGFUSE_PUBLIC_KEY"],
            secret_key=env_vars["LANGFUSE_SECRET_KEY"],
            host=env_vars["LANGFUSE_HOST"],
        )

        assert client == mock_client
        mock_langfuse_cls.assert_called_once_with(
            public_key="test_public_key",
            secret_key="test_secret_key",
            host="https://test.langfuse.com",
        )

        # Test with invalid credentials
        mock_langfuse_cls.reset_mock()
        client = create_langfuse_client(public_key=None, secret_key=None)
        assert client is None
        mock_langfuse_cls.assert_not_called()


def test_tracker_initialization() -> None:
    """Test tracker initialization without environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        print("\n[DEBUG] test_tracker_initialization: Environment cleared")
        with patch(
            "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
        ) as mock_create:
            tracker = LangfuseTracker(load_env=False)
            assert not tracker.enabled
            assert tracker.client is None
            mock_create.assert_not_called()


def test_tracker_initialization_with_env(env_vars: dict[str, str]) -> None:
    """Test tracker initialization with environment variables."""
    print("\n[DEBUG] test_tracker_initialization_with_env: Starting test")
    print(f"[DEBUG] test_tracker_initialization_with_env: env_vars={env_vars}")

    # First patch the client creation function
    with patch(
        "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
    ) as mock_create:
        mock_client = Mock()
        mock_create.return_value = mock_client
        print("[DEBUG] test_tracker_initialization_with_env: Client creation mocked")

        # Then set environment variables
        with patch.dict(os.environ, env_vars, clear=True):
            print(
                "[DEBUG] test_tracker_initialization_with_env: Environment variables set"
            )
            print(f"[DEBUG] LANGFUSE_PUBLIC_KEY={os.getenv('LANGFUSE_PUBLIC_KEY')}")
            print(f"[DEBUG] LANGFUSE_SECRET_KEY={os.getenv('LANGFUSE_SECRET_KEY')}")
            print(f"[DEBUG] LANGFUSE_HOST={os.getenv('LANGFUSE_HOST')}")

            # Create tracker
            tracker = LangfuseTracker(load_env=False)

            # Verify initialization
            assert (
                tracker.enabled
            ), "Tracker should be enabled with environment variables"
            assert tracker.client == mock_client, "Client should be initialized"
            mock_create.assert_called_once_with(
                public_key="test_public_key",
                secret_key="test_secret_key",
                host="https://test.langfuse.com",
            )


def test_trace_mapping(mock_langfuse_context: Mock, env_vars: dict[str, str]) -> None:
    """Test creating a mapping trace."""
    with patch.dict(os.environ, env_vars, clear=True):
        with patch(
            "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
        ) as mock_create:
            mock_create.return_value = Mock()
            tracker = LangfuseTracker(load_env=False)
            trace_id = tracker.trace_mapping(query="test query")

            assert trace_id == "test_trace_id"
            mock_langfuse_context.update_current_observation.assert_called_once_with(
                metadata={"query": "test query", "type": "rag"}
            )


def test_trace_mapping_disabled() -> None:
    """Test trace creation when disabled."""
    with patch.dict(os.environ, {}, clear=True):
        with patch(
            "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
        ) as mock_create:
            tracker = LangfuseTracker(load_env=False)
            trace_id = tracker.trace_mapping(query="test query")
            assert trace_id is None
            mock_create.assert_not_called()


def test_record_error(mock_langfuse_context: Mock, env_vars: dict[str, str]) -> None:
    """Test recording an error."""
    with patch.dict(os.environ, env_vars, clear=True):
        with patch(
            "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
        ) as mock_create:
            mock_create.return_value = Mock()
            tracker = LangfuseTracker(load_env=False)
            tracker.record_error(trace_id="test_trace", error="test error")

            mock_langfuse_context.update_current_observation.assert_called_once_with(
                metadata={"error": "test error", "trace_id": "test_trace"}
            )


def test_record_span(mock_langfuse_context: Mock, env_vars: dict[str, str]) -> None:
    """Test recording a span."""
    with patch.dict(os.environ, env_vars, clear=True):
        with patch(
            "biomapper.monitoring.langfuse_tracker.create_langfuse_client"
        ) as mock_create:
            mock_create.return_value = Mock()
            tracker = LangfuseTracker(load_env=False)
            input_data = {"input": "test"}
            output_data = {"output": "test"}

            tracker.record_span(
                trace_id="test_trace",
                span_name="test_span",
                input_data=input_data,
                output_data=output_data,
            )

            mock_langfuse_context.update_current_observation.assert_called_once_with(
                input=input_data,
                output=output_data,
                metadata={"span_name": "test_span"},
            )

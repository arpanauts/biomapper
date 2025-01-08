"""Tests for the LLM mapper module."""

from typing import Any
import pytest
from unittest.mock import Mock

from openai.types.chat import ChatCompletion

from biomapper.mapping.llm_mapper import LLMMapper
from biomapper.schemas.llm_schema import MatchConfidence


@pytest.fixture
def mock_openai_response() -> ChatCompletion:
    """Create a mock OpenAI API response."""
    message: Any = {
        "role": "assistant",
        "content": "The most appropriate ontology term for glucose is CHEBI:17234 (D-glucose). This is a monosaccharide commonly found in biological systems.",
    }
    choice: Any = {
        "finish_reason": "stop",
        "index": 0,
        "message": message,
        "logprobs": None,
    }
    usage: Any = {"completion_tokens": 50, "prompt_tokens": 50, "total_tokens": 100}

    return ChatCompletion(
        id="test_id",
        model="gpt-4",
        object="chat.completion",
        created=1234567890,
        choices=[choice],
        usage=usage,
    )


@pytest.fixture
def mock_openai_client(mock_openai_response: ChatCompletion) -> Mock:
    """Create a mock OpenAI instance."""
    instance = Mock()
    instance.chat.completions.create.return_value = mock_openai_response
    return instance


@pytest.fixture
def mock_langfuse() -> Mock:
    """Create a mock Langfuse client."""
    mock = Mock()
    mock.trace.return_value.id = "test_trace_id"
    return mock


@pytest.fixture
def mock_llm_mapper(
    mock_openai_client: Mock, mock_langfuse: Mock, monkeypatch: pytest.MonkeyPatch
) -> LLMMapper:
    """Create a mock LLMMapper instance with mocked dependencies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-key")

    mapper = LLMMapper()
    mapper.client = mock_openai_client
    mapper.langfuse = mock_langfuse
    return mapper


@pytest.mark.parametrize(
    "term,target_ontology,expected_response",
    [
        (
            "glucose",
            None,
            "The most appropriate ontology term for glucose is CHEBI:17234 (D-glucose). This is a monosaccharide commonly found in biological systems.",
        ),
        (
            "glucose",
            "chebi",
            "The most appropriate ontology term for glucose is CHEBI:17234 (D-glucose). This is a monosaccharide commonly found in biological systems.",
        ),
    ],
)
def test_map_term(
    mock_llm_mapper: LLMMapper,
    term: str,
    target_ontology: str | None,
    expected_response: str,
) -> None:
    """Test mapping a single term."""
    # Map term
    result = mock_llm_mapper.map_term(term, target_ontology)

    # Check result
    assert len(result.matches) == 1
    assert result.matches[0].target_name == expected_response
    assert result.matches[0].confidence == MatchConfidence.MEDIUM
    assert result.matches[0].score == 0.8


def test_estimate_cost(mock_llm_mapper: LLMMapper) -> None:
    """Test cost estimation."""
    cost = mock_llm_mapper._estimate_cost(1000)
    assert cost > 0


def test_map_term_with_metadata(mock_llm_mapper: LLMMapper) -> None:
    """Test mapping a term with additional metadata."""
    # Map term with metadata
    metadata = {"source": "test"}
    result = mock_llm_mapper.map_term("glucose", metadata=metadata)

    # Check result
    assert len(result.matches) == 1
    assert result.matches[0].metadata == metadata

"""Tests for DSPy integration."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

# Mark entire module as requiring external services (DSPy/RAG)
pytestmark = pytest.mark.requires_external_services

from biomapper.mapping.rag import RAGCompoundMapper
from biomapper.schemas.store_schema import VectorStoreConfig
from biomapper.schemas.rag_schema import LLMMapperResult, CompoundDocument


@dataclass
class MockMatch:
    """Mock match result."""

    id: str
    name: str
    confidence: str
    reasoning: str


@pytest.fixture
def mock_dspy_predictor() -> Any:
    """Create a mock DSPy predictor."""

    class MockPrediction:
        """Mock prediction result."""

        def __init__(self) -> None:
            self.matches = [
                MockMatch(
                    id="CHEBI:123",
                    name="Test Compound",
                    confidence="high",
                    reasoning="Test match",
                )
            ]
            self.tokens_used = 100

    class MockPredictor:
        """Mock DSPy predictor."""

        def __init__(self) -> None:
            self.input_prefix = ""
            self.output_prefix = ""

        def __call__(self, query: str, context: str) -> MockPrediction:
            """Return a mock prediction."""
            return MockPrediction()

    return MockPredictor()


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock store."""
    store = MagicMock()
    store.get_relevant_compounds.return_value = [
        CompoundDocument(
            content="Test compound content",
            metadata={"id": "CHEBI:123", "name": "Test Compound"},
            embedding=None,
        )
    ]
    return store


@pytest.fixture
def mock_embedding_manager() -> MagicMock:
    """Create a mock embedding manager."""
    manager = MagicMock()
    manager.embed_text.return_value = [0.1] * 768  # Match embedding dimension
    return manager


@pytest.fixture
def test_store_config(tmp_path: Path) -> VectorStoreConfig:
    """Create a test store configuration."""
    return VectorStoreConfig(
        persist_directory=tmp_path / "test_store", collection_name="test_collection"
    )


def test_predictor_initialization(test_store_config: VectorStoreConfig) -> None:
    """Test that DSPy predictor is initialized correctly."""
    mapper = RAGCompoundMapper(store_config=test_store_config)
    assert mapper.optimizer is not None
    assert mapper.prompt_manager is not None


def test_mapping_with_mock_predictor(
    mock_dspy_predictor: Any,
    mock_store: MagicMock,
    mock_embedding_manager: MagicMock,
    test_store_config: VectorStoreConfig,
) -> None:
    """Test mapping with a mock predictor."""
    mapper = RAGCompoundMapper(store_config=test_store_config)
    mapper.store = mock_store
    mapper.embedding_manager = mock_embedding_manager

    # Mock the get_compiler method to return our mock predictor
    with patch.object(
        mapper.optimizer, "get_compiler", return_value=mock_dspy_predictor
    ):
        result = mapper.map_compound("test compound")
        assert isinstance(result, LLMMapperResult)
        assert len(result.matches) > 0
        assert result.matches[0].id == "CHEBI:123"
        assert result.matches[0].name == "Test Compound"
        assert result.matches[0].confidence == "high"
        assert result.matches[0].reasoning == "Test match"


def test_error_handling(test_store_config: VectorStoreConfig) -> None:
    """Test error handling in mapping process."""
    mapper = RAGCompoundMapper(store_config=test_store_config)

    # Mock the get_compiler method to raise an exception
    with patch.object(
        mapper.optimizer, "get_compiler", side_effect=Exception("Test error")
    ):
        result = mapper.map_compound("test compound")
        assert isinstance(result, LLMMapperResult)
        assert len(result.matches) == 0
        assert result.error == "Test error"

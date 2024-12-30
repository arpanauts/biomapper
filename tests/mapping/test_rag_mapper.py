"""Tests for the RAG mapper module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from biomapper.mapping.rag_mapper import RAGMapper
from biomapper.schemas.llm_schema import MatchConfidence


@pytest.fixture
def sample_compounds_df():
    """Create a sample compounds DataFrame."""
    return pd.DataFrame(
        {
            "id": ["CHEBI:17234", "CHEBI:17925"],
            "name": ["glucose", "glucose-6-phosphate"],
            "description": ["A monosaccharide", "A glucose derivative"],
            "synonyms": ["dextrose", "G6P"],
        }
    )


@pytest.fixture
def compounds_file(tmp_path, sample_compounds_df):
    """Create a temporary compounds file."""
    file_path = tmp_path / "compounds.tsv"
    sample_compounds_df.to_csv(file_path, sep="\t", index=False)
    return file_path


@pytest.fixture
def mock_dspy_predictor():
    """Create a mock DSPy predictor."""
    mock = Mock()
    mock.return_value.matches = {
        "matches": [
            {
                "id": "CHEBI:17234",
                "name": "glucose",
                "confidence": "high",
                "reasoning": "Exact match found",
            }
        ]
    }
    return mock


@pytest.fixture
def mock_langfuse():
    """Create a mock Langfuse client."""
    trace_mock = Mock()
    trace_mock.id = "test_trace_id"

    mock = Mock()
    mock.trace.return_value = trace_mock
    return mock


@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    with patch("biomapper.mapping.llm_mapper.OpenAI") as mock:
        yield mock


def test_rag_mapper_initialization(compounds_file, mock_openai):
    """Test RAGMapper initialization."""
    mapper = RAGMapper(compounds_path=str(compounds_file))
    assert mapper.compounds_path == Path(compounds_file)
    assert mapper.chunk_size == 1000
    assert mapper.overlap == 100
    assert isinstance(mapper.knowledge_base, pd.DataFrame)


def test_load_knowledge_base(compounds_file, sample_compounds_df, mock_openai):
    """Test knowledge base loading and processing."""
    mapper = RAGMapper(compounds_path=str(compounds_file))
    kb = mapper.knowledge_base

    assert len(kb) == len(sample_compounds_df)
    assert "text" in kb.columns
    assert not kb["text"].isna().any()


@patch("biomapper.mapping.rag_mapper.BootstrapFewShot")
def test_initialize_predictor(mock_bootstrap, compounds_file, mock_openai):
    """Test predictor initialization."""
    mock_bootstrap.return_value.compile.return_value = Mock()

    mapper = RAGMapper(compounds_path=str(compounds_file))
    assert mapper.predictor is not None


def test_retrieve_context(compounds_file, mock_openai):
    """Test context retrieval."""
    mapper = RAGMapper(compounds_path=str(compounds_file))
    context = mapper._retrieve_context("glucose")

    assert isinstance(context, str)
    assert "glucose" in context.lower()
    assert "CHEBI:17234" in context


def test_map_term(compounds_file, mock_dspy_predictor, mock_langfuse, mock_openai):
    """Test term mapping."""
    # Create mapper with mocked predictor
    mapper = RAGMapper(compounds_path=str(compounds_file))
    mapper.predictor = mock_dspy_predictor
    mapper.langfuse = mock_langfuse

    # Map term
    result = mapper.map_term("glucose", target_ontology="CHEBI")

    # Verify result
    assert result.query_term == "glucose"
    assert len(result.matches) == 1
    assert result.best_match is not None
    if result.best_match:
        assert result.best_match.target_id == "CHEBI:17234"
        assert result.best_match.confidence == MatchConfidence.HIGH
    assert result.trace_id == "test_trace_id"


def test_process_predictor_output(compounds_file, mock_openai):
    """Test predictor output processing."""
    mapper = RAGMapper(compounds_path=str(compounds_file))

    # Mock output from DSPy predictor
    output = {
        "matches": [
            {
                "id": "CHEBI:17234",
                "name": "glucose",
                "confidence": "HIGH",
                "score": 0.95,
                "reasoning": "Exact match found",
            }
        ],
    }

    result = mapper._process_predictor_output(
        output=output,
        query_term="glucose",
        latency=100.0,
        tokens_used=50,
    )

    assert result.query_term == "glucose"
    assert len(result.matches) == 1
    if result.best_match:
        assert result.best_match.target_id == "CHEBI:17234"
        assert result.best_match.confidence == MatchConfidence.HIGH

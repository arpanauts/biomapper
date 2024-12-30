"""Tests for the multi-provider RAG mapper."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from biomapper.mapping.multi_provider_rag import (
    MultiProviderMapper,
    CrossReferenceResult,
)
from biomapper.schemas.llm_schema import LLMMatch, MatchConfidence
from biomapper.schemas.provider_schemas import (
    ProviderType,
    ProviderConfig,
)


@pytest.fixture
def sample_chebi_df():
    """Create a sample ChEBI DataFrame."""
    return pd.DataFrame(
        {
            "chebi_id": ["CHEBI:17234"],
            "name": ["glucose"],
            "definition": ["A monosaccharide"],
            "formula": ["C6H12O6"],
            "synonyms": ["dextrose"],
        }
    )


@pytest.fixture
def sample_unichem_df():
    """Create a sample UniChem DataFrame."""
    return pd.DataFrame(
        {
            "unichem_id": ["UC123"],
            "name": ["glucose"],
            "source_id": ["SRC1"],
            "source_name": ["PubChem"],
        }
    )


@pytest.fixture
def sample_refmet_df():
    """Create a sample RefMet DataFrame."""
    return pd.DataFrame(
        {
            "refmet_id": ["RM123"],
            "name": ["glucose"],
            "systematic_name": ["D-glucose"],
            "formula": ["C6H12O6"],
            "main_class": ["Carbohydrates"],
        }
    )


@pytest.fixture
def provider_files(tmp_path, sample_chebi_df, sample_unichem_df, sample_refmet_df):
    """Create temporary provider files."""
    chebi_path = tmp_path / "chebi.tsv"
    unichem_path = tmp_path / "unichem.tsv"
    refmet_path = tmp_path / "refmet.tsv"

    sample_chebi_df.to_csv(chebi_path, sep="\t", index=False)
    sample_unichem_df.to_csv(unichem_path, sep="\t", index=False)
    sample_refmet_df.to_csv(refmet_path, sep="\t", index=False)

    return {
        ProviderType.CHEBI: chebi_path,
        ProviderType.UNICHEM: unichem_path,
        ProviderType.REFMET: refmet_path,
    }


@pytest.fixture
def provider_configs(tmp_path):
    """Create provider configurations for testing."""
    # Create test data files
    chebi_path = tmp_path / "chebi.tsv"
    chebi_path.write_text(
        "id\tname\tdescription\n" "CHEBI:17234\tglucose\tA monosaccharide...\n"
    )

    unichem_path = tmp_path / "unichem.tsv"
    unichem_path.write_text(
        "id\tname\tdescription\n" "UNICHEM:123\tglucose\tA sugar molecule...\n"
    )

    # Return provider configs
    return {
        ProviderType.CHEBI: ProviderConfig(
            name=ProviderType.CHEBI,
            base_url=None,
            api_key=None,
            data_path=str(chebi_path),
            chunk_size=1000,
            overlap=100,
            embedding_model=None,
            additional_config={},
        ),
        ProviderType.UNICHEM: ProviderConfig(
            name=ProviderType.UNICHEM,
            base_url=None,
            api_key=None,
            data_path=str(unichem_path),
            chunk_size=1000,
            overlap=100,
            embedding_model=None,
            additional_config={},
        ),
    }


@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    with patch("biomapper.mapping.llm_mapper.OpenAI") as mock:
        yield mock


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
    mock.return_value.tokens_used = 100  # Add explicit tokens_used value
    return mock


def test_multi_provider_mapper_initialization(provider_configs, mock_openai):
    """Test MultiProviderMapper initialization."""
    mapper = MultiProviderMapper(providers=provider_configs)
    assert isinstance(mapper, MultiProviderMapper)
    assert mapper.providers == provider_configs


def test_load_provider_kb(provider_configs, mock_openai):
    """Test loading provider knowledge bases."""
    mapper = MultiProviderMapper(providers=provider_configs)
    mapper._load_provider_kb(ProviderType.CHEBI, provider_configs[ProviderType.CHEBI])
    assert ProviderType.CHEBI in mapper.knowledge_bases


def test_retrieve_multi_context(provider_configs, mock_openai):
    """Test multi-provider context retrieval."""
    mapper = MultiProviderMapper(providers=provider_configs)
    context = mapper._retrieve_multi_context("glucose", [ProviderType.CHEBI])
    assert context


@patch("biomapper.mapping.llm_mapper.Langfuse")
def test_map_term(
    mock_langfuse_cls, provider_configs, mock_dspy_predictor, mock_openai
):
    """Test term mapping with multiple providers."""
    # Use a fixed trace ID for testing
    test_trace_id = "test-trace-123"

    # Setup mock for Langfuse.trace()
    mock_trace = Mock()
    mock_trace.id = test_trace_id
    mock_trace.update = Mock()

    # Setup Langfuse mock to return our mock trace
    mock_langfuse = Mock()
    mock_langfuse.trace = Mock(return_value=mock_trace)
    mock_langfuse_cls.return_value = mock_langfuse

    # Create mapper with mocked predictor
    mapper = MultiProviderMapper(providers=provider_configs)
    mapper.predictor = mock_dspy_predictor

    # Configure mock predictor to return latency
    mock_dspy_predictor.return_value.latency = 100.0

    # Map term with trace ID in metadata
    result = mapper.map_term(
        "glucose",
        target_ontology=ProviderType.CHEBI.value,
        metadata={"trace_id": test_trace_id},
    )

    # Verify the result
    assert result is not None
    assert result.query_term == "glucose"
    assert result.trace_id == test_trace_id
    assert result.metrics is not None
    assert result.metrics.cost > 0


@patch("biomapper.mapping.llm_mapper.Langfuse")
def test_map_term_error(
    mock_langfuse_cls, provider_configs, mock_dspy_predictor, mock_openai
):
    """Test error handling in term mapping."""
    # Use a fixed trace ID for testing
    test_trace_id = "test-trace-error-123"

    # Setup mock for Langfuse.trace()
    mock_trace = Mock()
    mock_trace.id = test_trace_id
    mock_trace.update = Mock()

    # Setup Langfuse mock to return our mock trace
    mock_langfuse = Mock()
    mock_langfuse.trace = Mock(return_value=mock_trace)
    mock_langfuse_cls.return_value = mock_langfuse

    # Create mapper with mocked predictor that raises an error
    mapper = MultiProviderMapper(providers=provider_configs)
    mock_dspy_predictor.side_effect = ValueError("Test error")
    mapper.predictor = mock_dspy_predictor

    # Map term should raise error
    with pytest.raises(ValueError, match="Test error"):
        mapper.map_term(
            "glucose",
            target_ontology=ProviderType.CHEBI.value,
            metadata={"trace_id": test_trace_id},
        )


def test_resolve_cross_references(provider_configs, mock_openai):
    """Test cross-reference resolution."""
    mapper = MultiProviderMapper(providers=provider_configs)

    matches = [
        LLMMatch(
            target_id="CHEBI:17234",
            target_name="glucose",
            confidence=MatchConfidence.HIGH,
            score=0.9,
            reasoning="Primary match",
            metadata={},
        )
    ]

    results = mapper._resolve_cross_references(
        matches, [ProviderType.UNICHEM, ProviderType.REFMET]
    )

    assert len(results) == 1
    assert isinstance(results[0], CrossReferenceResult)
    assert results[0].primary_match == matches[0]


def test_find_xrefs(provider_configs, mock_openai):
    """Test finding cross-references."""
    mapper = MultiProviderMapper(providers=provider_configs)

    # Create a test match
    match = LLMMatch(
        target_id="CHEBI:17234",
        target_name="glucose",
        confidence=MatchConfidence.HIGH,
        score=0.9,
        reasoning="Test match",
        metadata={},
    )

    xrefs = mapper._find_xrefs(match, ProviderType.UNICHEM)
    assert isinstance(xrefs, list)

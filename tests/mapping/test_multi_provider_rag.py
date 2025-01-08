"""Tests for the multi-provider RAG mapper."""

from unittest.mock import Mock, patch
from pathlib import Path
from typing import Dict, Generator
import os

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
def sample_chebi_df() -> pd.DataFrame:
    """Create a sample ChEBI DataFrame."""
    return pd.DataFrame(
        {
            "id": ["CHEBI:17234"],
            "name": ["glucose"],
            "description": ["A monosaccharide"],
            "text": ["glucose is a monosaccharide sugar with formula C6H12O6"],
            "formula": ["C6H12O6"],
            "synonyms": ["dextrose"],
        }
    )


@pytest.fixture
def sample_unichem_df() -> pd.DataFrame:
    """Create a sample UniChem DataFrame."""
    return pd.DataFrame(
        {
            "id": ["UC123"],
            "name": ["glucose"],
            "description": ["A sugar molecule"],
            "text": ["glucose is a sugar molecule found in PubChem"],
            "source_id": ["SRC1"],
            "source_name": ["PubChem"],
        }
    )


@pytest.fixture
def sample_refmet_df() -> pd.DataFrame:
    """Create a sample RefMet DataFrame."""
    return pd.DataFrame(
        {
            "id": ["RM123"],
            "name": ["glucose"],
            "description": ["A carbohydrate"],
            "text": ["glucose is a carbohydrate with systematic name D-glucose"],
            "systematic_name": ["D-glucose"],
            "formula": ["C6H12O6"],
            "main_class": ["Carbohydrates"],
        }
    )


@pytest.fixture
def provider_files(
    tmp_path: Path,
    sample_chebi_df: pd.DataFrame,
    sample_unichem_df: pd.DataFrame,
    sample_refmet_df: pd.DataFrame,
) -> Dict[ProviderType, Path]:
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
def provider_configs(
    tmp_path: Path,
    sample_chebi_df: pd.DataFrame,
    sample_unichem_df: pd.DataFrame,
    sample_refmet_df: pd.DataFrame,
) -> Dict[ProviderType, ProviderConfig]:
    """Create provider configurations for testing."""
    # Create test data files
    chebi_path = tmp_path / "chebi.tsv"
    unichem_path = tmp_path / "unichem.tsv"
    refmet_path = tmp_path / "refmet.tsv"

    # Write the DataFrames to TSV files
    sample_chebi_df.to_csv(chebi_path, sep="\t", index=False)
    sample_unichem_df.to_csv(unichem_path, sep="\t", index=False)
    sample_refmet_df.to_csv(refmet_path, sep="\t", index=False)

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
def mock_openai() -> Generator[Mock, None, None]:
    """Create a mock OpenAI client."""
    with patch("biomapper.mapping.llm_mapper.OpenAI") as mock:
        yield mock


@pytest.fixture
def mock_dspy_predictor() -> Mock:
    """Create a mock DSPy predictor that returns LLMMatch objects in .matches."""
    mock_predictor = Mock()

    # Create a real LLMMatch with a float .score
    mock_match = LLMMatch(
        target_id="CHEBI:17234",
        target_name="glucose",
        confidence=MatchConfidence.HIGH,
        score=0.9,  # Real float for numeric operations
        reasoning="Exact match found",
        metadata={"provider": ProviderType.CHEBI.value},
    )

    # Create a predictor output that includes the LLMMatch
    class PredictorOutput:
        def __init__(self) -> None:
            # matches must be a list of LLMMatch objects
            self.matches = [mock_match]
            self.latency = 0.5
            self.tokens_used = 100
            # Optional but good to have for completeness
            self.contexts = {"chebi": "glucose is a monosaccharide sugar"}
            self.query = "glucose"
            self.target_providers = ["chebi"]

    mock_predictor.return_value = PredictorOutput()
    return mock_predictor


def test_multi_provider_mapper_initialization(
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_openai: Mock,
) -> None:
    """Test MultiProviderMapper initialization."""
    mapper = MultiProviderMapper(providers=provider_configs)
    assert isinstance(mapper, MultiProviderMapper)
    assert mapper.providers == provider_configs


def test_load_provider_kb(
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_openai: Mock,
) -> None:
    """Test loading provider knowledge bases."""
    mapper = MultiProviderMapper(providers=provider_configs)
    mapper._load_provider_kb(ProviderType.CHEBI, provider_configs[ProviderType.CHEBI])
    assert ProviderType.CHEBI in mapper.knowledge_bases


def test_retrieve_multi_context(
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_openai: Mock,
) -> None:
    """Test multi-provider context retrieval."""
    mapper = MultiProviderMapper(providers=provider_configs)
    context = mapper._retrieve_multi_context("glucose", [ProviderType.CHEBI])
    assert context


@patch("biomapper.mapping.llm_mapper.Langfuse")
def test_map_term(
    mock_langfuse_cls: Mock,
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_dspy_predictor: Mock,
    mock_openai: Mock,
) -> None:
    """Test term mapping with multiple providers."""
    # Use a fixed trace ID for testing
    test_trace_id = "test-trace-123"

    # Setup mock for Langfuse context
    with patch("biomapper.mapping.multi_provider_rag.langfuse_context") as mock_context:
        # Mock environment variables for Langfuse
        with patch.dict(
            os.environ,
            {
                "LANGFUSE_PUBLIC_KEY": "test_public_key",
                "LANGFUSE_SECRET_KEY": "test_secret_key",
                "LANGFUSE_HOST": "https://test.langfuse.com",
            },
        ):
            # Create mapper with mocked predictor
            mapper = MultiProviderMapper(providers=provider_configs)
            mapper.predictor = mock_dspy_predictor

            # Configure mock predictor to return latency
            mock_dspy_predictor.return_value.latency = 100.0

            # Configure mock predictor to return matches
            mock_dspy_predictor.return_value.matches = [
                LLMMatch(
                    target_id="CHEBI:17234",
                    target_name="glucose",
                    confidence=MatchConfidence.HIGH,
                    score=0.9,
                    reasoning="Exact match found",
                    metadata={"provider": ProviderType.CHEBI.value},
                )
            ]

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
            assert result.metrics["latency_ms"] >= 0

            # Verify the matches
            assert len(result.matches) == 1
            assert result.matches[0].target_id == "CHEBI:17234"
            assert result.matches[0].target_name == "glucose"
            assert (
                float(result.matches[0].confidence) == 0.9
            )  # Now checking float value
            assert (
                result.matches[0].reasoning
                == f"Exact ID match from {ProviderType.CHEBI}"
            )

            # Verify Langfuse context was updated
            mock_context.update_current_trace.assert_called_once_with(id=test_trace_id)


@patch("biomapper.mapping.llm_mapper.Langfuse")
def test_map_term_error(
    mock_langfuse_cls: Mock,
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_dspy_predictor: Mock,
    mock_openai: Mock,
) -> None:
    """Test error handling in term mapping."""
    # Use a fixed trace ID for testing
    test_trace_id = "test-trace-error-123"

    # Setup mock for Langfuse context
    with patch("biomapper.mapping.multi_provider_rag.langfuse_context") as mock_context:
        # Mock environment variables for Langfuse
        with patch.dict(
            os.environ,
            {
                "LANGFUSE_PUBLIC_KEY": "test_public_key",
                "LANGFUSE_SECRET_KEY": "test_secret_key",
                "LANGFUSE_HOST": "https://test.langfuse.com",
            },
        ):
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

            # Verify Langfuse context was updated
            mock_context.update_current_trace.assert_called_once_with(id=test_trace_id)

            # Verify error was recorded
            assert mapper.tracker.enabled
            assert mapper.tracker.client is not None


def test_resolve_cross_references(
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_openai: Mock,
) -> None:
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


def test_find_xrefs(
    provider_configs: Dict[ProviderType, ProviderConfig],
    mock_openai: Mock,
) -> None:
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

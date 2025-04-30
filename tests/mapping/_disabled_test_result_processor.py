"""Tests for the result processor module."""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from biomapper.mapping.result_processor import (
    ResultProcessor,
    ProcessedResult,
    MappingSource,
    ConfidenceLevel,
)
from biomapper.mapping.metabolite.name import MetaboliteMapping, MetaboliteClass


@pytest.fixture
def processor() -> ResultProcessor:
    """Create a result processor instance."""
    return ResultProcessor(
        high_confidence_threshold=0.8,
        medium_confidence_threshold=0.5
    )


@pytest.fixture
def mock_name_mapping() -> MetaboliteMapping:
    """Create a mock name mapping result."""
    return MetaboliteMapping(
        input_name="glucose",
        compound_class=MetaboliteClass.SIMPLE,
        primary_compound="glucose",
        refmet_id="REFMET:123",
        refmet_name="D-Glucose",
        chebi_id="CHEBI:4167",
        chebi_name="glucose",
        pubchem_id="5793",
        mapping_source="test"
    )


@pytest.fixture
def mock_spoke_mapping() -> Dict[str, Any]:
    """Create a mock SPOKE mapping result."""
    return {
        "input_name": "glucose",
        "spoke_id": "Compound/123",
        "node_type": "Compound",
        "properties": {"name": "glucose"},
        "confidence_score": 0.9,
        "metadata": {"source": "spoke_test"}
    }


@pytest.fixture
def mock_rag_mapping() -> Dict[str, Any]:
    """Create a mock RAG mapping result."""
    return {
        "query_term": "glucose",
        "best_match": {
            "target_id": "CHEBI:4167",
            "target_name": "glucose",
            "confidence": "0.85",
            "metadata": {"source": "rag_test"}
        },
        "matches": [{"test": "data"}],
        "metrics": {"latency_ms": 100}
    }


def test_initialization(processor: ResultProcessor) -> None:
    """Test processor initialization."""
    assert processor.high_confidence_threshold == 0.8
    assert processor.medium_confidence_threshold == 0.5
    assert processor.metrics is None
    assert processor.langfuse is None


def test_process_name_mapping_refmet(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping
) -> None:
    """Test processing RefMet name mapping."""
    result = processor.process_name_mapping(mock_name_mapping)

    assert isinstance(result, ProcessedResult)
    assert result.input_name == "glucose"
    assert result.mapped_id == "REFMET:123"
    assert result.mapped_name == "D-Glucose"
    assert result.source == MappingSource.REFMET
    assert result.confidence == ConfidenceLevel.HIGH
    assert result.confidence_score >= processor.high_confidence_threshold


def test_process_name_mapping_fallback(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping
) -> None:
    """Test fallback to ChEBI when RefMet unavailable."""
    mock_name_mapping.refmet_id = None
    mock_name_mapping.refmet_name = None

    result = processor.process_name_mapping(mock_name_mapping)

    assert result.mapped_id == "CHEBI:4167"
    assert result.source == MappingSource.CHEBI
    assert result.confidence == ConfidenceLevel.HIGH


def test_process_spoke_mapping(
    processor: ResultProcessor,
    mock_spoke_mapping: Dict[str, Any]
) -> None:
    """Test processing SPOKE mapping."""
    result = processor.process_spoke_mapping(mock_spoke_mapping)

    assert result.input_name == "glucose"
    assert result.mapped_id == "Compound/123"
    assert result.source == MappingSource.SPOKE
    assert result.confidence == ConfidenceLevel.HIGH
    assert "spoke_node_type" in result.metadata
    assert "spoke_properties" in result.metadata


def test_process_spoke_mapping_with_base(
    processor: ResultProcessor,
    mock_spoke_mapping: Dict[str, Any]
) -> None:
    """Test SPOKE mapping with existing base result."""
    base_result = ProcessedResult(
        input_name="glucose",
        compound_class=MetaboliteClass.SIMPLE,
        primary_compound="glucose"
    )

    result = processor.process_spoke_mapping(mock_spoke_mapping, base_result)

    assert result.input_name == "glucose"
    assert result.compound_class == MetaboliteClass.SIMPLE
    assert result.primary_compound == "glucose"
    assert result.mapped_id == "Compound/123"
    assert result.source == MappingSource.SPOKE


def test_process_rag_mapping(
    processor: ResultProcessor,
    mock_rag_mapping: Dict[str, Any]
) -> None:
    """Test processing RAG mapping."""
    result = processor.process_rag_mapping(mock_rag_mapping)

    assert result.input_name == "glucose"
    assert result.mapped_id == "CHEBI:4167"
    assert result.mapped_name == "glucose"
    assert result.source == MappingSource.RAG
    assert result.confidence == ConfidenceLevel.HIGH
    assert "rag_matches" in result.metadata
    assert "rag_metrics" in result.metadata


def test_confidence_level_assignment(processor: ResultProcessor) -> None:
    """Test confidence level assignment based on scores."""
    assert processor._get_confidence_level(0.9) == ConfidenceLevel.HIGH
    assert processor._get_confidence_level(0.7) == ConfidenceLevel.MEDIUM
    assert processor._get_confidence_level(0.3) == ConfidenceLevel.LOW
    assert processor._get_confidence_level(0.0) == ConfidenceLevel.UNKNOWN


def test_should_try_rag(processor: ResultProcessor) -> None:
    """Test RAG attempt decision logic."""
    # Should try RAG with no mapping
    empty_result = ProcessedResult(input_name="test")
    assert processor.should_try_rag(empty_result) is True

    # Should try RAG with low confidence
    low_conf_result = ProcessedResult(
        input_name="test",
        mapped_id="123",
        confidence_score=0.3
    )
    assert processor.should_try_rag(low_conf_result) is True

    # Should not try RAG with high confidence
    high_conf_result = ProcessedResult(
        input_name="test",
        mapped_id="123",
        mapped_name="test",
        confidence_score=0.9
    )
    assert processor.should_try_rag(high_conf_result) is False


def test_combine_results(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping,
    mock_spoke_mapping: Dict[str, Any],
    mock_rag_mapping: Dict[str, Any]
) -> None:
    """Test combining results from multiple sources."""
    result = processor.combine_results(
        name_result=mock_name_mapping,
        spoke_result=mock_spoke_mapping,
        rag_result=mock_rag_mapping
    )

    assert isinstance(result, ProcessedResult)
    assert result.input_name == "glucose"
    assert result.mapped_id is not None
    assert result.confidence == ConfidenceLevel.HIGH
    assert result.metadata.get("has_refmet") is True
    assert "spoke_node_type" in result.metadata
    assert "rag_matches" in result.metadata


def test_combine_results_partial(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping
) -> None:
    """Test combining results with partial data."""
    result = processor.combine_results(name_result=mock_name_mapping)

    assert isinstance(result, ProcessedResult)
    assert result.input_name == "glucose"
    assert result.mapped_id == "REFMET:123"
    assert result.source == MappingSource.REFMET


def test_process_batch(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping,
    mock_spoke_mapping: Dict[str, Any],
    mock_rag_mapping: Dict[str, Any]
) -> None:
    """Test batch processing of results."""
    names = ["glucose", "fructose"]
    name_results = [mock_name_mapping, mock_name_mapping]
    spoke_results = [mock_spoke_mapping, mock_spoke_mapping]
    rag_results = [mock_rag_mapping, mock_rag_mapping]

    results = processor.process_batch(
        names,
        name_results=name_results,
        spoke_results=spoke_results,
        rag_results=rag_results
    )

    assert len(results) == 2
    assert all(isinstance(r, ProcessedResult) for r in results)
    assert all(r.confidence == ConfidenceLevel.HIGH for r in results)
    assert all(r.mapped_id is not None for r in results)


def test_process_batch_missing_results(processor: ResultProcessor) -> None:
    """Test batch processing with missing results."""
    names = ["glucose", "fructose"]
    results = processor.process_batch(names)

    assert len(results) == 2
    assert all(isinstance(r, ProcessedResult) for r in results)
    assert all(r.confidence == ConfidenceLevel.UNKNOWN for r in results)
    assert results[0].input_name == "glucose"
    assert results[1].input_name == "fructose"


def test_metrics_tracking(
    processor: ResultProcessor,
    mock_name_mapping: MetaboliteMapping
) -> None:
    """Test metrics tracking integration."""
    mock_metrics = Mock()
    processor.metrics = mock_metrics

    mock_name_mapping.metadata = {"trace_id": "test-trace"}
    processor.process_name_mapping(mock_name_mapping)

    mock_metrics.record_metrics.assert_called_once()

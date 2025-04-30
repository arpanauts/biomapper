"""Test suite for compound mapping functionality."""

import pytest
from unittest.mock import Mock, patch

from biomapper.core.base_client import APIResponse
from biomapper.pipelines.compounds.compound_mapper import (
    CompoundMapper,
    CompoundDocument,
    CompoundClass,
)


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = Mock()
    client.search.return_value = APIResponse(
        success=True,
        data={
            "refmet_id": "REFMET:123",
            "refmet_name": "glucose",
            "chebi_id": "CHEBI:17234",
            "chebi_name": "glucose",
            "hmdb_id": "HMDB0000122",
        },
    )
    return client


@pytest.fixture
def compound_mapper(mock_api_client):
    """Create a compound mapper with mock client."""
    return CompoundMapper([mock_api_client])


@pytest.mark.asyncio
async def test_map_entity_success(compound_mapper):
    """Test successful compound mapping."""
    result = await compound_mapper.map_entity("glucose")

    assert result.mapped_entity is not None
    assert result.mapped_entity.name == "glucose"
    assert result.mapped_entity.refmet_id == "REFMET:123"
    assert result.mapped_entity.chebi_id == "CHEBI:17234"
    assert result.confidence > 0.8


@pytest.mark.asyncio
async def test_map_entity_with_context(compound_mapper, mock_api_client):
    """Test compound mapping with context."""
    context = {"organism": "human"}
    await compound_mapper.map_entity("glucose", context)

    # Verify context was used in API call
    mock_api_client.search.assert_called_once()
    args = mock_api_client.search.call_args[0]
    assert "human" in args[0]


@pytest.mark.asyncio
async def test_map_entity_no_match(compound_mapper, mock_api_client):
    """Test behavior when no match is found."""
    mock_api_client.search.return_value = APIResponse(success=True, data=None)

    result = await compound_mapper.map_entity("unknown_compound")

    assert result.mapped_entity is None
    assert result.confidence == 0.0
    assert "No data" in result.metadata["error"]


@pytest.mark.asyncio
async def test_map_entity_api_error(compound_mapper, mock_api_client):
    """Test handling of API errors."""
    mock_api_client.search.side_effect = Exception("API Error")

    result = await compound_mapper.map_entity("glucose")

    assert result.mapped_entity is None
    assert result.confidence == 0.0
    assert "API Error" in result.metadata["error"]


@pytest.mark.asyncio
async def test_confidence_calculation(compound_mapper, mock_api_client):
    """Test confidence score calculation."""
    # Test with varying numbers of matched IDs
    test_cases = [
        (
            {"refmet_id": "R1", "chebi_id": "C1", "hmdb_id": "H1", "pubchem_id": "P1"},
            1.0,  # All IDs present
        ),
        (
            {"refmet_id": "R1", "chebi_id": "C1"},
            0.5,  # 2/4 IDs present
        ),
        (
            {"refmet_id": "R1"},
            0.25,  # 1/4 IDs present
        ),
        (
            {},
            0.0,  # No IDs present
        ),
    ]

    for data, expected_confidence in test_cases:
        mock_api_client.search.return_value = APIResponse(success=True, data=data)

        result = await compound_mapper.map_entity("test")
        assert result.confidence == expected_confidence


@pytest.mark.asyncio
async def test_multiple_api_clients(mock_api_client):
    """Test using multiple API clients."""
    # Create two mock clients with different responses
    client1 = Mock()
    client1.search.return_value = APIResponse(success=True, data={"refmet_id": "R1"})

    client2 = Mock()
    client2.search.return_value = APIResponse(
        success=True, data={"chebi_id": "C1", "hmdb_id": "H1"}
    )

    mapper = CompoundMapper([client1, client2])
    result = await mapper.map_entity("test")

    # Should use result from client2 as it has more IDs
    assert result.mapped_entity is not None
    assert result.confidence == 0.5  # 2/4 IDs present


def test_compound_document_rag_update():
    """Test updating compound document with RAG results."""
    doc = CompoundDocument(name="test", compound_class=CompoundClass.SIMPLE)

    rag_result = Mock()
    rag_result.mapped_entity = CompoundDocument(
        name="test",
        compound_class=CompoundClass.SIMPLE,
        refmet_id="R1",
        chebi_id="C1",
        confidence=0.9,
    )
    rag_result.confidence = 0.9
    rag_result.metadata = {"source": "rag"}

    doc.update_from_rag(rag_result)

    assert doc.refmet_id == "R1"
    assert doc.chebi_id == "C1"
    assert doc.confidence == 0.9
    assert doc.source == "rag"
    assert doc.metadata == {"source": "rag"}

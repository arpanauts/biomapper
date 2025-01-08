"""Test suite for ChEBI client functionality."""

from unittest.mock import Mock, patch
import pytest
from biomapper.mapping.clients.chebi_client import ChEBIClient, ChEBIResult


@pytest.fixture
def chebi_client() -> ChEBIClient:
    """Create a ChEBIClient instance for testing."""
    return ChEBIClient()


@pytest.fixture
def mock_entity() -> Mock:
    """Create a mock ChEBI entity with standard properties."""
    entity = Mock()
    entity.get_id.return_value = "12345"
    entity.get_name.return_value = "Test Compound"
    entity.get_formula.return_value = "C6H12O6"
    entity.get_charge.return_value = 0
    entity.get_mass.return_value = 180.156
    entity.get_smiles.return_value = "O=C=O"

    # Add strict specification to prevent any unmocked calls
    entity.configure_mock(
        spec=[
            "get_id",
            "get_name",
            "get_formula",
            "get_charge",
            "get_mass",
            "get_smiles",
        ]
    )
    return entity


def test_get_entity_by_id_success(chebi_client: ChEBIClient, mock_entity: Mock) -> None:
    """Test successful entity retrieval with all properties."""
    with patch("biomapper.mapping.clients.chebi_client.ChebiEntity") as mock_chebi:
        mock_chebi.return_value = mock_entity
        result = chebi_client.get_entity_by_id("12345")
        assert result is not None
        assert isinstance(result, ChEBIResult)
        assert result.chebi_id == "CHEBI:12345"
        assert result.name == "Test Compound"
        assert result.formula == "C6H12O6"
        assert result.charge == 0
        assert result.mass == 180.156
        assert result.smiles == "O=C=O"

        # Verify the mock was called correctly
        mock_chebi.assert_called_once_with("12345")


def test_get_entity_missing_properties(
    chebi_client: ChEBIClient, mock_entity: Mock
) -> None:
    """Test handling of missing or erroring properties."""
    mock_entity.get_formula.side_effect = ValueError
    mock_entity.get_charge.side_effect = AttributeError
    mock_entity.get_mass.side_effect = ValueError
    mock_entity.get_smiles.side_effect = AttributeError

    with patch(
        "biomapper.mapping.clients.chebi_client.ChebiEntity", return_value=mock_entity
    ):
        result = chebi_client.get_entity_by_id("12345")
        assert result is not None
        assert result.chebi_id == "CHEBI:12345"
        assert result.name == "Test Compound"  # Required fields should still work
        assert result.formula is None
        assert result.charge is None
        assert result.mass is None
        assert result.smiles is None


def test_search_by_name_success(chebi_client: ChEBIClient, mock_entity: Mock) -> None:
    """Test successful name search with multiple results."""
    entities = [mock_entity, mock_entity]  # Two identical entities for testing

    with patch(
        "biomapper.mapping.clients.chebi_client.chebi_search", return_value=entities
    ):
        results = chebi_client.search_by_name("test")
        assert results is not None
        assert isinstance(results, list)  # Verify it's a list
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ChEBIResult)
            assert result.chebi_id == "CHEBI:12345"
            assert result.smiles == "O=C=O"


def test_search_by_name_partial_failures(
    chebi_client: ChEBIClient, mock_entity: Mock
) -> None:
    """Test search handling when some entities fail processing."""
    good_entity = mock_entity
    bad_entity = Mock()
    bad_entity.get_id.side_effect = ValueError("Bad ID")

    with patch(
        "biomapper.mapping.clients.chebi_client.chebi_search",
        return_value=[good_entity, bad_entity],
    ):
        results = chebi_client.search_by_name("test")
        assert results is not None
        assert isinstance(results, list)  # Verify it's a list
        assert len(results) == 1  # Only good entity should be included
        assert results[0].chebi_id == "CHEBI:12345"


def test_max_results_limit(chebi_client: ChEBIClient, mock_entity: Mock) -> None:
    """Test respecting max_results parameter."""
    entities = [mock_entity] * 10  # Create 10 identical entities

    with patch("libchebipy.search", return_value=entities):
        results = chebi_client.search_by_name("test", max_results=3)
        assert results is not None
        assert isinstance(results, list)  # Verify it's a list
        assert len(results) == 3


def test_get_safe_property(chebi_client: ChEBIClient) -> None:
    """Test safe property getter with various scenarios."""

    def good_getter() -> str:
        return "test"

    def bad_getter() -> None:
        raise ValueError("test error")

    assert chebi_client._get_safe_property(good_getter) == "test"
    assert chebi_client._get_safe_property(bad_getter) is None
    assert (
        chebi_client._get_safe_property(
            bad_getter, error_types=(ValueError, AttributeError)
        )
        is None
    )


def test_chebi_id_prefix_handling(chebi_client: ChEBIClient, mock_entity: Mock) -> None:
    """Test proper handling of ChEBI ID prefixes."""
    # Test cases for different ID formats
    test_cases = [
        ("12345", "CHEBI:12345"),  # No prefix
        ("CHEBI:12345", "CHEBI:12345"),  # Single prefix
        ("CHEBI:CHEBI:12345", "CHEBI:12345"),  # Double prefix
    ]

    for input_id, expected_id in test_cases:
        mock_entity.get_id.return_value = input_id
        with patch("libchebipy.ChebiEntity", return_value=mock_entity):
            result = chebi_client.get_entity_by_id(input_id)
            assert (
                result is not None
            ), f"Result should not be None for input: {input_id}"
            assert result.chebi_id == expected_id, f"Failed for input: {input_id}"

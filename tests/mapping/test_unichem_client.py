"""Tests for the UniChem API client"""

from unittest.mock import Mock, patch

import pytest
import requests

from biomapper.mapping.unichem_client import (
    UniChemClient,
    UniChemConfig,
    UniChemError,
)


# Test fixtures
@pytest.fixture
def unichem_client() -> UniChemClient:
    """Create a UniChemClient instance for testing"""
    return UniChemClient()


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock response object with default values"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = []
    return mock


# Test basic client initialization
def test_client_initialization() -> None:
    """Test that client initializes with default config"""
    client = UniChemClient()
    assert isinstance(client.config, UniChemConfig)
    assert client.config.base_url == "https://www.ebi.ac.uk/unichem/rest"
    assert client.config.timeout == 30


def test_client_custom_config() -> None:
    """Test that client accepts custom config"""
    custom_config = UniChemConfig(base_url="https://custom.url", timeout=60)
    client = UniChemClient(config=custom_config)
    assert client.config.base_url == "https://custom.url"
    assert client.config.timeout == 60


# Test API endpoint calls
@patch("requests.Session.get")
def test_get_compound_info_success(
    mock_get: Mock, unichem_client: UniChemClient, mock_response: Mock
) -> None:
    """Test successful compound info retrieval"""
    mock_response.json.return_value = [
        {"src_compound_id": "CHEMBL123", "src_id": 1},
        {"src_compound_id": "CHEBI:123", "src_id": 7},
    ]
    mock_get.return_value = mock_response

    result = unichem_client.get_compound_info_by_inchikey("TEST-INCHIKEY")
    assert "chembl_ids" in result
    assert "chebi_ids" in result
    assert len(result["chembl_ids"]) == 1
    assert len(result["chebi_ids"]) == 1


@patch("requests.Session.get")
def test_get_compound_info_error(mock_get: Mock, unichem_client: UniChemClient) -> None:
    """Test error handling for compound info retrieval"""
    mock_get.side_effect = requests.exceptions.RequestException("API Error")

    with pytest.raises(UniChemError):
        unichem_client.get_compound_info_by_inchikey("TEST-INCHIKEY")


@patch("requests.Session.get")
def test_get_source_information(
    mock_get: Mock, unichem_client: UniChemClient, mock_response: Mock
) -> None:
    """Test source information retrieval"""
    mock_response.json.return_value = {"sources": []}
    mock_get.return_value = mock_response

    result = unichem_client.get_source_information()
    assert isinstance(result, dict)


def test_structure_search_invalid_type(unichem_client: UniChemClient) -> None:
    """Test structure search with invalid search type"""
    with pytest.raises(ValueError):
        unichem_client.get_structure_search("C1=CC=CC=C1", "invalid_type")


@patch("requests.Session.get")
def test_structure_search_success(
    mock_get: Mock, unichem_client: UniChemClient, mock_response: Mock
) -> None:
    """Test successful structure search"""
    mock_response.json.return_value = {"results": []}
    mock_get.return_value = mock_response

    result = unichem_client.get_structure_search("C1=CC=CC=C1", "smiles")
    assert isinstance(result, dict)


def test_process_compound_result_empty() -> None:
    """Test processing empty compound result"""
    client = UniChemClient()
    result = client._process_compound_result([])
    assert all(len(ids) == 0 for ids in result.values())


def test_process_compound_result_invalid() -> None:
    """Test processing invalid compound result"""
    client = UniChemClient()
    result = client._process_compound_result(
        [{"src_id": "invalid", "src_compound_id": "invalid"}]
    )
    assert isinstance(result, dict)
    assert all(len(ids) == 0 for ids in result.values())


@patch("requests.Session.get")
def test_retry_behavior(
    mock_get: Mock, unichem_client: UniChemClient, mock_response: Mock
) -> None:
    """Test retry behavior on server errors"""
    # Set up mock response for success case
    mock_response.status_code = 200
    mock_response.json.return_value = {"sources": []}

    # First call fails, second succeeds
    mock_get.side_effect = [
        requests.exceptions.RequestException("Server Error"),
        mock_response,
    ]

    with pytest.raises(UniChemError):
        unichem_client.get_source_information()


@patch("requests.Session.get")
def test_timeout_handling(mock_get: Mock, unichem_client: UniChemClient) -> None:
    """Test timeout handling"""
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")

    with pytest.raises(UniChemError) as exc_info:
        unichem_client.get_source_information()
    assert "Timeout" in str(exc_info.value)


@patch("requests.Session.get")
def test_complex_compound_result(
    mock_get: Mock, unichem_client: UniChemClient, mock_response: Mock
) -> None:
    """Test processing complex compound result with multiple sources"""
    mock_response.json.return_value = [
        {"src_compound_id": "CHEMBL123", "src_id": 1},
        {"src_compound_id": "CHEBI:123", "src_id": 7},
        {"src_compound_id": "CID123", "src_id": 22},
        {"src_compound_id": "C12345", "src_id": 6},
        {"src_compound_id": "HMDB123", "src_id": 2},
        {"src_compound_id": "UNKNOWN123", "src_id": 999},  # Unknown source
    ]
    mock_get.return_value = mock_response

    result = unichem_client.get_compound_info_by_inchikey("TEST-INCHIKEY")

    # Verify each source type is processed correctly
    assert "CHEMBL123" in result["chembl_ids"]
    assert "CHEBI:123" in result["chebi_ids"]
    assert "CID123" in result["pubchem_ids"]
    assert "C12345" in result["kegg_ids"]
    assert "HMDB123" in result["hmdb_ids"]

    # Check that unknown source was ignored
    for ids in result.values():
        assert "UNKNOWN123" not in ids

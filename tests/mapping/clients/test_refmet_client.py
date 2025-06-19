"""Test suite for RefMet client functionality."""

from typing import Optional
from unittest.mock import Mock, patch, MagicMock, call

import pytest
import requests
from requests_mock import Mocker

from biomapper.mapping.clients.refmet_client import RefMetClient, RefMetConfig


@pytest.fixture
def refmet_client() -> RefMetClient:
    """Create a RefMetClient instance for testing."""
    config = RefMetConfig(use_local_cache=False)
    return RefMetClient(config=config)


@pytest.fixture
def mock_response() -> Mock:
    """Create mock response with valid tab-separated data."""
    response = Mock()
    response.status_code = 200
    response.content = True
    response.text = (
        "Input name\tRefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\t"
        "PubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
        "glucose\tRM0135901\tGlucose\tC6H12O6\t180.0634\tWQZGKKKJIJFFOK-GASJEMHNSA-N\t"
        "5793\t4167\tHMDB0000122\tC00031"
    )
    return response


def test_client_initialization() -> None:
    """Test client initialization with default config."""
    client = RefMetClient()
    assert isinstance(client.config, RefMetConfig)
    assert "metabolomicsworkbench.org" in client.config.base_url


def test_client_custom_config() -> None:
    """Test client initialization with custom config."""
    custom_config = RefMetConfig(base_url="https://custom.url", timeout=60)
    client = RefMetClient(config=custom_config)
    assert client.config.base_url == "https://custom.url"
    assert client.config.timeout == 60


def test_successful_search(refmet_client: RefMetClient, mock_response: Mock) -> None:
    """Test successful metabolite name search."""
    mock_response.status_code = 200
    mock_response.content = True
    mock_response.text = (
        "Input name\tRefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\t"
        "PubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
        "glucose\tRM0135901\tGlucose\tC6H12O6\t180.0634\tTEST123\t5793\t4167\t"
        "HMDB0000122\tC00031\n"
    )
    mock_response.raise_for_status.return_value = None

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is not None
        assert result["refmet_id"] == "RM0135901"  # Raw ID without prefix
        assert result["name"] == "Glucose"
        assert result["formula"] == "C6H12O6"
        assert result["exact_mass"] == "180.0634"
        assert result["inchikey"] == "TEST123"
        assert result["pubchem_id"] == "5793"
        assert result["chebi_id"] == "CHEBI:4167"  # ChEBI ID with prefix


def test_empty_response(refmet_client: RefMetClient) -> None:
    """Test handling of empty response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = False
    mock_response.raise_for_status.return_value = None

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("nonexistent")
        assert result is None


def test_malformed_response(refmet_client: RefMetClient) -> None:
    """Test handling of malformed response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = True
    mock_response.text = "invalid\tdata"
    mock_response.raise_for_status.return_value = None

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_name_cleaning(refmet_client: RefMetClient, mock_response: Mock) -> None:
    """Test cleaning of metabolite names."""
    mock_response.status_code = 200
    mock_response.content = True
    mock_response.raise_for_status.return_value = None
    
    with patch.object(refmet_client.session, "post", return_value=mock_response) as mock_post, \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("Glucose (alpha)")
        assert result is not None

        # Verify cleaned name was used in API call
        assert mock_post.call_args is not None  # Type safety check
        assert "metabolite_name" in mock_post.call_args[1]["data"]
        assert mock_post.call_args[1]["data"]["metabolite_name"] == "glucose alpha"


def test_pandas_error_handling(refmet_client: RefMetClient) -> None:
    """Test handling of pandas DataFrame errors."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = True
    mock_response.text = (
        "header1\theader2\nvalue1"  # Malformed TSV - missing required columns
    )
    mock_response.raise_for_status.return_value = None

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_request_exception(refmet_client: RefMetClient) -> None:
    """Test handling of request exception."""
    with patch.object(refmet_client.session, "post", side_effect=requests.exceptions.RequestException("Test error")), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_empty_dataframe(refmet_client: RefMetClient) -> None:
    """Test handling of empty DataFrame result."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = True
    mock_response.text = "refmet_id\tname\tformula\texact_mass\tinchikey\tpubchem_id\n"
    mock_response.raise_for_status.return_value = None

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_retry_mechanism(refmet_client: RefMetClient) -> None:
    """Test retry mechanism for failed requests."""
    with patch.object(refmet_client.session, "post") as mock_post, \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        # Configure mock to fail twice then succeed
        success_mock = Mock()
        success_mock.status_code = 200
        success_mock.content = True
        success_mock.text = "No results found"
        success_mock.raise_for_status.return_value = None
        
        mock_post.side_effect = [
            requests.exceptions.RequestException("Timeout"),
            success_mock,
        ]

        result = refmet_client.search_by_name("glucose")
        assert result is None
        assert mock_post.call_count == 2  # Initial try + one retry


def test_http_error(refmet_client: RefMetClient) -> None:
    """Test handling of HTTP errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Error"
    )

    with patch.object(refmet_client.session, "post", return_value=mock_response), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_search_compounds_error(refmet_client: RefMetClient) -> None:
    """Test error handling in search compounds."""
    mock_post = MagicMock(spec=requests.Session.post)
    mock_post.side_effect = requests.exceptions.RequestException("Test error")

    with patch.object(refmet_client.session, "post", mock_post), \
         patch.object(refmet_client.session, "get", side_effect=requests.exceptions.RequestException("Mock GET failure")):
        result = refmet_client.search_by_name("glucose")
        assert result is None
        assert mock_post.call_args == call(
            f"{refmet_client.config.base_url}/name_to_refmet_new_minID.php",
            data={"metabolite_name": "glucose"},
            timeout=refmet_client.config.timeout,
        )


@pytest.mark.parametrize(
    "input_name,mock_response,expected_result",
    [
        (
            "glucose",
            (
                "Input name\tRefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\tPubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
                "glucose\tRM0135901\tGlucose\tC6H12O6\t180.0634\tWQZGKKKJIJFFOK-GASJEMHNSA-N\t5793\t4167\tHMDB0000122\tC00031\n"
            ),
            {
                "refmet_id": "RM0135901",
                "name": "Glucose",
                "formula": "C6H12O6",
                "exact_mass": "180.0634",
                "inchikey": "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                "pubchem_id": "5793",
                "chebi_id": "CHEBI:4167",
                "hmdb_id": "HMDB0000122",
                "kegg_id": "C00031",
            },
        ),
        (
            "invalid-compound",
            (
                "Input name\tStandardized name\tFormula\tExact mass\tINCHI_KEY\tPubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
                "invalid-compound\t-\t-\t-\t-\t-\t-\t-\t-\n"
            ),
            None,
        ),
        (
            "empty-result",
            (
                "Input name\tStandardized name\tFormula\tExact mass\tINCHI_KEY\tPubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
            ),
            None,
        ),
    ],
)
def test_search_by_name(
    refmet_client: RefMetClient,
    requests_mock: Mocker,
    input_name: str,
    mock_response: str,
    expected_result: Optional[dict[str, str]],
) -> None:
    """Test RefMet name search with actual response format."""
    # Mock GET requests to REST API to fail, forcing fallback to POST endpoint
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/match/{input_name.lower()}",
        status_code=404
    )
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/name/{input_name.lower()}/all",
        status_code=404
    )
    
    # Mock the POST endpoint that should be used as fallback
    requests_mock.post(
        f"{refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=mock_response,
    )

    result = refmet_client.search_by_name(input_name)
    assert result == expected_result


def test_search_by_name_request_error(
    refmet_client: RefMetClient,
    requests_mock: Mocker,
) -> None:
    """Test handling of request errors."""
    # Mock GET requests to REST API to fail, forcing fallback to POST endpoint
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/match/glucose",
        status_code=404
    )
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/name/glucose/all",
        status_code=404
    )
    
    requests_mock.post(
        f"{refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        status_code=500,
    )

    result = refmet_client.search_by_name("glucose")
    assert result is None


def test_search_by_name_complex_terms(
    refmet_client: RefMetClient, requests_mock: Mocker
) -> None:
    """Test searching with complex terms."""
    # Clean name for the search
    clean_name = "total hdl cholesterol concentration"
    
    # Mock GET requests to REST API to fail, forcing fallback to POST endpoint
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/match/{clean_name}",
        status_code=404
    )
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/name/{clean_name}/all",
        status_code=404
    )
    
    # Also need to mock the preprocessed terms
    requests_mock.get(
        f"{refmet_client.config.rest_url}/refmet/name/hdl cholesterol/all",
        status_code=404
    )
    
    requests_mock.post(
        f"{refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=(
            "RefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\t"
            "PubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
            "REFMET:0001\tHDL\tC10H20\t140.15\tKEY123\t12345\t67890\tHMDB123\tC12345"
        ),
    )

    result = refmet_client.search_by_name("Total HDL cholesterol concentration")

    assert result is not None
    assert result["refmet_id"] == "REFMET:0001"
    assert result["name"] == "HDL"


def create_mock_response(content: str) -> requests.Response:
    """Create a mock response with the given content."""
    response = requests.Response()
    response._content = content.encode()
    response.status_code = 200
    return response

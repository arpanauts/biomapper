"""Test suite for RefMet client functionality."""

from unittest.mock import Mock, patch, MagicMock, call

import pytest
import requests

from biomapper.mapping.refmet_client import RefMetClient, RefMetConfig


@pytest.fixture
def refmet_client() -> RefMetClient:
    """Create a RefMetClient instance for testing."""
    return RefMetClient()


@pytest.fixture
def mock_response() -> Mock:
    """Create mock response with valid tab-separated data."""
    response = Mock()
    response.status_code = 200
    response.content = True
    response.text = (
        "refmet_id\tname\tformula\texact_mass\tinchikey\tpubchem_id\n"
        "REFMET:0001\tGlucose\tC6H12O6\t180.0634\tTESTKEY\t5793"
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
    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("glucose")
        assert result is not None
        assert result["refmet_id"] == "REFMET:0001"
        assert result["name"] == "Glucose"
        assert result["formula"] == "C6H12O6"
        assert result["exact_mass"] == "180.0634"
        assert result["inchikey"] == "TESTKEY"
        assert result["pubchem_id"] == "5793"


def test_empty_response(refmet_client: RefMetClient) -> None:
    """Test handling of empty response."""
    mock_response = Mock()
    mock_response.content = False

    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("nonexistent")
        assert result is None


def test_malformed_response(refmet_client: RefMetClient) -> None:
    """Test handling of malformed response."""
    mock_response = Mock()
    mock_response.content = True
    mock_response.text = "invalid\tdata"

    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_name_cleaning(refmet_client: RefMetClient, mock_response: Mock) -> None:
    """Test cleaning of metabolite names."""
    with patch.object(
        refmet_client.session, "post", return_value=mock_response
    ) as mock_post:
        result = refmet_client.search_by_name("Glucose (alpha)")
        assert result is not None

        # Verify cleaned name was used in API call
        assert mock_post.call_args is not None  # Type safety check
        assert "metabolite_name" in mock_post.call_args[1]["data"]
        assert mock_post.call_args[1]["data"]["metabolite_name"] == "Glucose alpha"


def test_pandas_error_handling(refmet_client: RefMetClient) -> None:
    """Test handling of pandas DataFrame errors."""
    mock_response = Mock()
    mock_response.content = True
    mock_response.text = (
        "header1\theader2\nvalue1"  # Malformed TSV - missing required columns
    )

    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_request_exception(refmet_client: RefMetClient) -> None:
    """Test handling of request exception."""
    with patch.object(
        refmet_client.session,
        "post",
        side_effect=requests.exceptions.RequestException("Test error"),
    ):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_empty_dataframe(refmet_client: RefMetClient) -> None:
    """Test handling of empty DataFrame result."""
    mock_response = Mock()
    mock_response.content = True
    mock_response.text = "refmet_id\tname\tformula\texact_mass\tinchikey\tpubchem_id\n"

    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_retry_mechanism(refmet_client: RefMetClient, mock_response: Mock) -> None:
    """Test retry mechanism for failed requests."""
    with patch.object(refmet_client.session, "post") as mock_post:
        # First call fails, second call succeeds
        mock_post.side_effect = [
            requests.exceptions.RequestException("Timeout"),
            mock_response,
        ]

        # The retry should be handled by the requests Session retry mechanism
        # Our method should just return None on any request exception
        result = refmet_client.search_by_name("glucose")
        assert result is None
        assert mock_post.call_count == 1  # We only try once at this level


def test_http_error(refmet_client: RefMetClient) -> None:
    """Test handling of HTTP errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Error"
    )

    with patch.object(refmet_client.session, "post", return_value=mock_response):
        result = refmet_client.search_by_name("glucose")
        assert result is None


def test_search_compounds_error(refmet_client: RefMetClient) -> None:
    """Test error handling in search compounds."""
    mock_post = MagicMock(spec=requests.Session.post)
    mock_post.side_effect = requests.exceptions.RequestException("Test error")

    with patch.object(refmet_client.session, "post", mock_post):
        result = refmet_client.search_by_name("glucose")
        assert result is None
        assert mock_post.call_args == call(
            f"{refmet_client.config.base_url}/name_to_refmet_new_minID.php",
            data={"metabolite_name": "glucose"},
            timeout=refmet_client.config.timeout,
        )
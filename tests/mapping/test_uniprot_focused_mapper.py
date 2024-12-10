"""Test suite for UniProt focused mapper functionality."""

from unittest.mock import Mock, patch

import pytest
import requests
from requests import Response, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from biomapper.mapping.uniprot_focused_mapper import UniProtConfig, UniprotFocusedMapper


@pytest.fixture
def config() -> UniProtConfig:
    """Create a test configuration."""
    return UniProtConfig(
        base_url="https://test.uniprot.org",
        polling_interval=1,
        max_retries=2,
        timeout=5,
    )


@pytest.fixture
def mapper(config: UniProtConfig) -> UniprotFocusedMapper:
    """Create a UniprotFocusedMapper instance with test config."""
    return UniprotFocusedMapper(config=config)


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock Response object."""
    response = Mock(spec=Response)
    response.status_code = 200
    response.json.return_value = {"jobId": "test_job_id"}
    return response


@pytest.fixture
def mock_session(mock_response: Mock) -> Mock:
    """Create a mock requests.Session with properly typed responses."""
    session = Mock()

    # Mock successful job submission
    session.post.return_value = mock_response

    # Mock successful job completion
    status_response = Mock(spec=Response)
    status_response.status_code = 303
    status_response.headers = {"Location": "https://test.uniprot.org/results"}

    results_response = Mock(spec=Response)
    results_response.status_code = 200
    results_response.json.return_value = {
        "results": [
            {
                "from": "P12345",
                "to": {"id": "TEST123", "name": "Test Protein"},
            }
        ]
    }

    session.get.side_effect = [status_response, results_response]
    return session


# Core functionality tests
def test_initialization() -> None:
    """Test mapper initialization with default config."""
    mapper = UniprotFocusedMapper()
    assert isinstance(mapper.config, UniProtConfig)
    assert mapper.config.base_url == "https://rest.uniprot.org"


def test_custom_config(config: UniProtConfig) -> None:
    """Test mapper initialization with custom config."""
    mapper = UniprotFocusedMapper(config=config)
    assert mapper.config.base_url == "https://test.uniprot.org"
    assert mapper.config.polling_interval == 1
    assert mapper.config.max_retries == 2


def test_get_available_mappings(mapper: UniprotFocusedMapper) -> None:
    """Test retrieving available mapping categories."""
    mappings = mapper.get_available_mappings()
    assert isinstance(mappings, dict)
    assert "Protein/Gene" in mappings
    assert "Pathways" in mappings
    assert "Chemical/Drug" in mappings
    assert "Disease" in mappings


# Mapping functionality tests
def test_map_id_all_categories(
    mapper: UniprotFocusedMapper, mock_session: Mock
) -> None:
    """Test mapping protein to all target databases."""
    mapper.session = mock_session
    result = mapper.map_id("P12345", "Ensembl")
    assert isinstance(result, dict)
    mock_session.post.assert_called()


def test_map_id_specific_category(
    mapper: UniprotFocusedMapper, mock_session: Mock
) -> None:
    """Test mapping protein to specific target database."""
    mapper.session = mock_session
    result = mapper.map_id("P12345", "GeneCards")
    assert isinstance(result, dict)
    mock_session.post.assert_called()


def test_map_id_invalid_target(mapper: UniprotFocusedMapper) -> None:
    """Test handling of invalid target database."""
    with pytest.raises(ValueError, match="Invalid target database"):
        mapper.map_id("P12345", "InvalidTarget")


def test_map_id_failed_mapping(mapper: UniprotFocusedMapper) -> None:
    """Test handling of failed mappings in map_id."""
    with patch.object(mapper, "_submit_job", return_value=None):
        result = mapper.map_id("P05067", "Ensembl")
        assert result == {}


def test_map_id_with_exception(mapper: UniprotFocusedMapper) -> None:
    """Test map_id handling when mapping fails with an exception."""
    with patch.object(
        mapper, "_submit_job", side_effect=Exception("Test error")
    ), patch.object(mapper, "_check_job_status", return_value=None):
        with pytest.raises(Exception, match="Test error"):
            mapper.map_id("P05067", "Ensembl")


# Database mapping tests
def test_map_to_database(mapper: UniprotFocusedMapper, mock_session: Mock) -> None:
    """Test internal database mapping method."""
    # Mock successful job submission
    submit_response = Mock(spec=Response)
    submit_response.status_code = 200
    submit_response.json.return_value = {"jobId": "test_job_id"}

    # Mock successful status check
    status_response = Mock(spec=Response)
    status_response.status_code = 303
    status_response.json.return_value = {"jobStatus": "COMPLETE"}
    status_response.headers = {"Location": "https://test.uniprot.org/results"}

    # Mock results
    results_response = Mock(spec=Response)
    results_response.status_code = 200
    results_response.json.return_value = {"results": [{"test": "data"}]}

    mock_session.post.return_value = submit_response
    mock_session.get.side_effect = [status_response, results_response]

    mapper.session = mock_session
    result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P12345"])

    assert isinstance(result, dict)
    assert "results" in result


def test_map_to_database_submit_failure(mapper: UniprotFocusedMapper) -> None:
    """Test _map_to_database when job submission fails."""
    with patch.object(mapper, "_submit_job", return_value=None):
        result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P05067"])
        assert result == {}


def test_map_to_database_request_exception(mapper: UniprotFocusedMapper) -> None:
    """Test _map_to_database handling of RequestException."""
    with patch.object(
        mapper, "_submit_job", side_effect=requests.exceptions.RequestException
    ):
        result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P05067"])
        assert result == {}


# Job handling tests
@patch("time.sleep")  # Prevent actual sleeping in tests
def test_job_polling(
    mock_sleep: Mock, mapper: UniprotFocusedMapper, mock_session: Mock
) -> None:
    """Test job status polling logic."""
    responses = [
        Mock(
            spec=Response,
            status_code=200,
            json=Mock(return_value={"jobStatus": "RUNNING"}),
        ),
        Mock(
            spec=Response,
            status_code=303,
            headers={"Location": "https://test.uniprot.org/results"},
        ),
        Mock(
            spec=Response,
            status_code=200,
            json=Mock(return_value={"results": [{"test": "data"}]}),
        ),
    ]
    mock_session.get = Mock(side_effect=responses)
    mapper.session = mock_session

    result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P12345"])
    assert result == {"results": [{"test": "data"}]}
    assert mock_sleep.called


def test_failed_job_status(mapper: UniprotFocusedMapper) -> None:
    """Test handling of failed job status."""
    failed_response = Mock(spec=Response)
    failed_response.status_code = 200
    failed_response.json.return_value = {"jobStatus": "FAILED", "message": "Job failed"}
    failed_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "get", return_value=failed_response):
        result = mapper._check_job_status("test_job_id")
        assert result is None


def test_check_job_status_invalid_response(mapper: UniprotFocusedMapper) -> None:
    """Test handling of invalid response in _check_job_status."""
    mock_response = Mock()
    mock_response.json.return_value = "not a dict"
    mock_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "get", return_value=mock_response):
        result = mapper._check_job_status("test_job_id")
        assert result is None


def test_check_job_status_missing_location(mapper: UniprotFocusedMapper) -> None:
    """Test handling of missing Location header."""
    mock_response = Mock(spec=Response)
    mock_response.status_code = 303  # Redirect status
    mock_response.json.return_value = {"jobStatus": "COMPLETE"}
    mock_response.headers = {}  # No Location header
    mock_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "get", return_value=mock_response):
        result = mapper._check_job_status("test_job_id")
        assert result is None


# Request handling and retry tests
def test_retry_request(mapper: UniprotFocusedMapper) -> None:
    """Test retry mechanism for failed requests."""
    url = "https://example.com/test"
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_response.raise_for_status.return_value = None

    with patch(
        "requests.get",
        side_effect=[requests.exceptions.RequestException, mock_response],
    ) as mock_get:
        result = mapper._retry_request(url)
        assert result == {"test": "data"}
        assert mock_get.call_count == 2


def test_make_request_success(mapper: UniprotFocusedMapper) -> None:
    """Test successful request in _make_request."""
    url = "https://example.com/test"
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = mapper._make_request(url)
        assert result == {"test": "data"}
        mock_get.assert_called_once_with(url, timeout=mapper.config.timeout)


def test_make_request_retry(mapper: UniprotFocusedMapper) -> None:
    """Test retry mechanism in _make_request."""
    url = "https://example.com/test"

    with patch.object(mapper, "_should_retry", return_value=True), patch.object(
        mapper, "_retry_request", return_value={"retry": "data"}
    ) as mock_retry:
        result = mapper._make_request(url)
        assert result == {"retry": "data"}
        mock_retry.assert_called_once_with(url)


def test_retry_request_all_attempts_fail(mapper: UniprotFocusedMapper) -> None:
    """Test _retry_request when all retry attempts fail."""
    url = "https://example.com/test"
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Test error")
        result = mapper._retry_request(url)
        assert result == {}
        assert mock_get.call_count == mapper.config.max_retries


# Error handling tests
@pytest.mark.parametrize(
    "http_code",
    [500, 502, 503, 504],
    ids=["server_error", "bad_gateway", "service_unavailable", "gateway_timeout"],
)
def test_retry_on_error_codes(
    http_code: int,
    mapper: UniprotFocusedMapper,
    mock_response: Mock,
    mock_session: Mock,
) -> None:
    """Test retry behavior for different error codes."""
    error_response = Mock(spec=Response)
    error_response.status_code = http_code
    error_response.raise_for_status.side_effect = requests.exceptions.RequestException(
        f"Error {http_code}"
    )

    mock_session.post.side_effect = [error_response, mock_response]
    mapper.session = mock_session

    result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P12345"])
    assert isinstance(result, dict)
    assert mock_session.post.call_count <= mapper.config.max_retries + 1


def test_should_retry_timeout(mapper: UniprotFocusedMapper) -> None:
    """Test _should_retry with timeout error."""
    error = requests.exceptions.RequestException()
    error.response = None  # No response attribute
    assert mapper._should_retry(error) is False


def test_should_retry_timeout_with_max_retries(mapper: UniprotFocusedMapper) -> None:
    """Test retry behavior with timeout errors."""
    mock_response = Mock()
    mock_response.side_effect = exceptions.Timeout()

    with patch("requests.get", mock_response):
        result = mapper._make_request("https://test.url")
        assert result == {}
        assert mock_response.call_count == mapper.config.max_retries + 1


def test_should_retry_connection_error(mapper: UniprotFocusedMapper) -> None:
    """Test _should_retry with connection error."""
    error = requests.exceptions.ConnectionError()
    assert mapper._should_retry(error) is True


def test_should_retry_connection_error_with_max_retries(
    mapper: UniprotFocusedMapper,
) -> None:
    """Test retry behavior with connection errors."""
    mock_response = Mock()
    mock_response.side_effect = exceptions.ConnectionError()

    with patch("requests.get", mock_response):
        result = mapper._make_request("https://test.url")
        assert result == {}
        assert mock_response.call_count == mapper.config.max_retries + 1


def test_should_retry_response_error(mapper: UniprotFocusedMapper) -> None:
    """Test _should_retry with response error."""
    error = requests.exceptions.RequestException()
    mock_response = Mock()
    mock_response.status_code = 503
    error.response = mock_response
    assert mapper._should_retry(error) is True


# Session configuration tests
def test_session_retry_configuration(mapper: UniprotFocusedMapper) -> None:
    """Test session retry configuration."""
    session = mapper._create_session()
    adapter = session.get_adapter("https://")
    assert isinstance(adapter, HTTPAdapter)
    retry = getattr(adapter, "max_retries", None)
    assert isinstance(retry, Retry)
    assert retry.total == mapper.config.max_retries
    assert retry.backoff_factor == 0.25
    assert set(retry.status_forcelist) == {500, 502, 503, 504}


def test_session_configuration() -> None:
    """Test session configuration and retry settings."""
    mapper = UniprotFocusedMapper()
    adapter = mapper.session.get_adapter("http://")
    assert isinstance(adapter, HTTPAdapter)
    retry = getattr(adapter, "max_retries", None)
    assert isinstance(retry, Retry)
    assert retry.total == mapper.config.max_retries
    assert retry.backoff_factor == 0.25
    assert set(retry.status_forcelist) == {500, 502, 503, 504}


# Job result handling tests
def test_get_job_results_retry(mapper: UniprotFocusedMapper) -> None:
    """Test retry mechanism in _get_job_results."""
    url = "https://example.com/test"
    mock_response = Mock(
        spec=Response,
        status_code=200,
        json=Mock(return_value={"retry": "data"}),
        raise_for_status=Mock(),
    )

    # Set up the session mock to handle retries properly
    with patch.object(
        mapper.session,
        "get",
        side_effect=[
            requests.exceptions.RequestException("Test error"),
            mock_response,
        ],
    ) as mock_get:
        # Don't patch _should_retry - let the actual implementation handle it
        with patch("time.sleep"):  # Just prevent actual sleeping
            result = mapper._get_job_results(url)
            assert result == {"retry": "data"}
            assert mock_get.call_count == 2


def test_get_job_results_no_retry(mapper: UniprotFocusedMapper) -> None:
    """Test _get_job_results when retry is not needed."""
    url = "https://example.com/test"

    with patch.object(mapper.session, "get") as mock_get:
        # Simulate a request exception that shouldn't be retried
        mock_get.side_effect = requests.exceptions.RequestException("Test error")
        with patch.object(mapper, "_should_retry", return_value=False):
            result = mapper._get_job_results(url)
            assert result == {}


# Invalid response handling tests
def test_submit_job_invalid_response(mapper: UniprotFocusedMapper) -> None:
    """Test handling of invalid response in _submit_job."""
    mock_response = Mock()
    mock_response.json.return_value = "not a dict"  # Invalid response
    mock_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "post", return_value=mock_response):
        result = mapper._submit_job("UniProtKB_AC-ID", "GeneCards", ["P05067"])
        assert result is None


def test_submit_job_request_exception(mapper: UniprotFocusedMapper) -> None:
    """Test _submit_job handling of RequestException."""
    with patch.object(mapper.session, "post") as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException("Test error")
        result = mapper._submit_job("UniProtKB_AC-ID", "GeneCards", ["P05067"])
        assert result is None


def test_remove_source_database_from_results(
    mapper: UniprotFocusedMapper, mock_session: Mock
) -> None:
    """Test removal of source database from mapping results."""
    mapper.session = mock_session
    result = mapper.map_id("P12345", "Ensembl")
    assert "UniProtKB_AC-ID" not in result


def test_should_retry_other_exception(mapper: UniprotFocusedMapper) -> None:
    """Test _should_retry with other RequestException types."""
    error = requests.exceptions.RequestException()
    error.response = None  # No response attribute
    assert mapper._should_retry(error) is False


# Additional error handling tests
def test_get_job_results_error_no_retry(mapper: UniprotFocusedMapper) -> None:
    """Test handling of non-retriable errors in get_job_results."""
    url = "https://example.com/test"
    error = requests.exceptions.RequestException("Test error")

    with patch.object(mapper.session, "get", side_effect=error), patch.object(
        mapper, "_should_retry", return_value=False
    ):
        result = mapper._get_job_results(url)
        assert result == {}


def test_submit_job_non_json_response(mapper: UniprotFocusedMapper) -> None:
    """Test handling of non-JSON response in submit_job."""
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "post", return_value=mock_response):
        try:
            result = mapper._submit_job("UniProtKB_AC-ID", "GeneCards", ["P05067"])
            assert result is None
        except ValueError:
            pytest.fail("Should handle JSON parsing error gracefully")


def test_check_job_status_non_json_response(mapper: UniprotFocusedMapper) -> None:
    """Test handling of non-JSON response in check_job_status."""
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status.return_value = None

    with patch.object(mapper.session, "get", return_value=mock_response):
        try:
            result = mapper._check_job_status("test_job_id")
            assert result is None
        except ValueError:
            pytest.fail("Should handle JSON parsing error gracefully")


def test_map_to_database_invalid_job_id(mapper: UniprotFocusedMapper) -> None:
    """Test mapping behavior with invalid job ID."""
    with patch.object(
        mapper, "_submit_job", return_value="invalid_job_id"
    ), patch.object(mapper, "_check_job_status", return_value=None):
        result = mapper._map_to_database("UniProtKB_AC-ID", "GeneCards", ["P05067"])
        assert result == {}


def test_check_job_status_request_exception(mapper: UniprotFocusedMapper) -> None:
    """Test handling of RequestException in check_job_status."""
    session_mock = Mock()
    session_mock.get.side_effect = requests.exceptions.RequestException(
        "Connection error"
    )
    mapper.session = session_mock

    result = mapper._check_job_status("test_job_id")
    assert result is None

    # Update assertion to include allow_redirects=False
    session_mock.get.assert_called_once_with(
        f"{mapper.config.base_url}/idmapping/status/test_job_id",
        timeout=mapper.config.timeout,
        allow_redirects=False,
    )

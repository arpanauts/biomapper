"""Tests for the MetaboAnalyst client."""

from unittest import mock
import pytest
import requests
import requests_mock

from biomapper.mapping.clients.metaboanalyst_client import (
    MetaboAnalystClient,
    MetaboAnalystConfig,
    MetaboAnalystError,
    MetaboAnalystResult,
)


class TestMetaboAnalystClient:
    """Tests for MetaboAnalystClient."""

    def test_init_default_config(self) -> None:
        """Test client initialization with default config."""
        client = MetaboAnalystClient()
        assert client.config.base_url == "https://rest.xialab.ca/api"
        assert client.config.timeout == 30
        assert client.config.max_retries == 3
        assert client.config.backoff_factor == 0.5

    def test_init_custom_config(self) -> None:
        """Test client initialization with custom config."""
        config = MetaboAnalystConfig(
            base_url="https://custom-url.com/api",
            timeout=60,
            max_retries=5,
            backoff_factor=1.0,
        )
        client = MetaboAnalystClient(config=config)
        assert client.config.base_url == "https://custom-url.com/api"
        assert client.config.timeout == 60
        assert client.config.max_retries == 5
        assert client.config.backoff_factor == 1.0

    def test_map_compounds_empty_list(self) -> None:
        """Test mapping with empty compound list."""
        client = MetaboAnalystClient()
        results = client.map_compounds([])
        assert results == []

    def test_map_compounds_invalid_input_type(self) -> None:
        """Test mapping with invalid input type."""
        client = MetaboAnalystClient()
        with pytest.raises(ValueError, match="Invalid input_type"):
            client.map_compounds(["glucose"], input_type="invalid")

    def test_map_compounds_success(self, requests_mock: requests_mock.Mocker) -> None:
        """Test successful compound mapping."""
        # Mock API response
        mock_response = {
            "matches": [
                {
                    "query": "glucose",
                    "name": "D-Glucose",
                    "hmdb": "HMDB0000122",
                    "kegg": "C00031",
                    "pubchem": "5793",
                    "chebi": "17234",
                    "metlin": "3520",
                },
                {
                    "query": "caffeine",
                    "name": "Caffeine",
                    "hmdb": "HMDB0001847",
                    "kegg": "C07481",
                    "pubchem": "2519",
                    "chebi": "27732",
                    "metlin": "63",
                },
            ]
        }

        client = MetaboAnalystClient()
        url = f"{client.config.base_url}/mapcompounds"
        requests_mock.post(url, json=mock_response)

        # Call the client method
        results = client.map_compounds(["glucose", "caffeine", "unknown_compound"])

        # Verify expected results
        assert len(results) == 3

        # Check first result
        assert results[0].input_id == "glucose"
        assert results[0].name == "D-Glucose"
        assert results[0].hmdb_id == "HMDB0000122"
        assert results[0].kegg_id == "C00031"
        assert results[0].pubchem_id == "5793"
        assert results[0].chebi_id == "17234"
        assert results[0].metlin_id == "3520"
        assert results[0].match_found is True

        # Check second result
        assert results[1].input_id == "caffeine"
        assert results[1].name == "Caffeine"
        assert results[1].hmdb_id == "HMDB0001847"
        assert results[1].match_found is True

        # Check third result (no match)
        assert results[2].input_id == "unknown_compound"
        assert results[2].hmdb_id is None
        assert results[2].match_found is False

    def test_map_compounds_api_error(self, requests_mock: requests_mock.Mocker) -> None:
        """Test API error handling."""
        client = MetaboAnalystClient()
        url = f"{client.config.base_url}/mapcompounds"

        # Mock API error response
        error_response = {"error": "Invalid input format"}
        requests_mock.post(url, json=error_response, status_code=400)

        # Call the client method and check for exception
        with pytest.raises(MetaboAnalystError, match="API request failed"):
            client.map_compounds(["glucose"])

    def test_map_compounds_http_error(
        self, requests_mock: requests_mock.Mocker
    ) -> None:
        """Test HTTP error handling."""
        client = MetaboAnalystClient()
        url = f"{client.config.base_url}/mapcompounds"

        # Mock server error
        requests_mock.post(url, status_code=500)

        # Call the client method and check for exception
        with pytest.raises(MetaboAnalystError, match="API request failed"):
            client.map_compounds(["glucose"])

    def test_map_compounds_unexpected_response(
        self, requests_mock: requests_mock.Mocker
    ) -> None:
        """Test handling of unexpected API response format."""
        client = MetaboAnalystClient()
        url = f"{client.config.base_url}/mapcompounds"

        # Mock unexpected response format
        unexpected_response = {"unexpected_field": "value"}
        requests_mock.post(url, json=unexpected_response)

        # Call the client method - should handle gracefully
        results = client.map_compounds(["glucose"])

        # Should return non-matched result
        assert len(results) == 1
        assert results[0].input_id == "glucose"
        assert results[0].match_found is False

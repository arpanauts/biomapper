"""Test suite for RaMP API client functionality."""

# ruff: noqa: S101

from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests

from biomapper.standardization.ramp_client import (
    AnalyteType,
    PathwayStats,
    RaMPAPIError,
    RaMPClient,
    RaMPConfig,
)


# Test fixtures
@pytest.fixture
def ramp_client() -> RaMPClient:
    """Create a RaMPClient instance for testing."""
    return RaMPClient()


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock response object with default values."""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {"result": [], "function_call": [], "numFoundIds": []}
    return mock


# Test basic client initialization
def test_client_initialization() -> None:
    """Test that client initializes with default configuration."""
    client = RaMPClient()
    assert isinstance(client.config, RaMPConfig)
    assert client.config.base_url == "https://rampdb.nih.gov/api"
    assert client.config.timeout == 30


def test_client_custom_config() -> None:
    """Test that client accepts custom configuration."""
    custom_config = RaMPConfig(base_url="https://custom.url", timeout=60)
    client = RaMPClient(config=custom_config)
    assert client.config.base_url == "https://custom.url"
    assert client.config.timeout == 60


# Test API endpoint calls
@patch("requests.Session.request")
def test_get_source_versions(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test source versions endpoint."""
    mock_request.return_value = mock_response
    response = ramp_client.get_source_versions()
    mock_request.assert_called_with(
        method="GET", url="https://rampdb.nih.gov/api/source-versions", timeout=30
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_valid_id_types(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test ID types endpoint."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}
    response = ramp_client.get_valid_id_types()
    mock_request.assert_called_with(
        method="GET", url="https://rampdb.nih.gov/api/validIdTypes", timeout=30
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_pathways_from_analytes(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test pathways endpoint."""
    test_analytes = ["hmdb:HMDB0000064", "uniprot:P31323"]
    mock_request.return_value = mock_response
    response = ramp_client.get_pathways_from_analytes(test_analytes)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/pathways-from-analytes",
        timeout=30,
        json={"analytes": test_analytes},
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_chemical_properties(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test chemical properties endpoint."""
    test_metabolites = ["hmdb:HMDB0000064"]
    mock_request.return_value = mock_response
    response = ramp_client.get_chemical_properties(test_metabolites)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/chemical-properties",
        timeout=30,
        json={"metabolites": test_metabolites},
    )
    assert isinstance(response, dict)


# Test error handling
@patch("requests.Session.request")
def test_api_error_handling(mock_request: Mock, ramp_client: RaMPClient) -> None:
    """Test that API errors are properly handled."""
    mock_request.side_effect = requests.exceptions.RequestException("API Error")
    with pytest.raises(RaMPAPIError):
        ramp_client.get_source_versions()


# Test analysis methods
def test_analyze_pathway_stats() -> None:
    """Test pathway statistics analysis."""
    client = RaMPClient()
    test_data = {
        "result": [
            {
                "inputId": "hmdb:test1",
                "pathwayName": "Test Pathway 1",
                "pathwaySource": "kegg",
            },
            {
                "inputId": "hmdb:test1",
                "pathwayName": "Test Pathway 2",
                "pathwaySource": "wiki",
            },
        ]
    }
    stats = client.analyze_pathway_stats(test_data)
    assert isinstance(stats, dict)
    assert "hmdb:test1" in stats
    assert isinstance(stats["hmdb:test1"], PathwayStats)
    assert stats["hmdb:test1"].total_pathways == 2


def test_find_pathway_overlaps() -> None:
    """Test pathway overlap analysis."""
    client = RaMPClient()
    test_data = {
        "result": [
            {
                "inputId": "hmdb:test1",
                "pathwayName": "Common Pathway",
                "pathwaySource": "kegg",
            },
            {
                "inputId": "hmdb:test2",
                "pathwayName": "Common Pathway",
                "pathwaySource": "kegg",
            },
        ]
    }
    overlaps = client.find_pathway_overlaps(test_data)
    assert isinstance(overlaps, dict)
    assert overlaps["Common Pathway"] == 2


@patch("requests.Session.request")
def test_get_ontologies_from_metabolites(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test getting ontology mappings for metabolites with both IDs and names."""
    mock_request.return_value = mock_response

    # Test with IDs
    test_ids = ["hmdb:HMDB0000064"]
    response = ramp_client.get_ontologies_from_metabolites(test_ids)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/ontologies-from-metabolites",
        timeout=30,
        json={"metabolite": test_ids, "namesOrIds": "ids"},
    )
    assert isinstance(response, dict)

    # Test with names
    test_names = ["glucose"]
    response = ramp_client.get_ontologies_from_metabolites(
        test_names, names_or_ids="names"
    )
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/ontologies-from-metabolites",
        timeout=30,
        json={"metabolite": test_names, "namesOrIds": "names"},
    )
    assert isinstance(response, dict)

    # Test error handling
    mock_request.side_effect = requests.exceptions.RequestException("Test error")
    with pytest.raises(RaMPAPIError) as exc_info:
        ramp_client.get_ontologies_from_metabolites(test_ids)
    assert "Test error" in str(exc_info.value)


@patch("requests.Session.request")
def test_get_metabolites_from_ontologies(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test metabolites from ontology terms endpoint."""
    mock_request.return_value = mock_response

    test_ontologies = ["CHEBI:15903"]
    response = ramp_client.get_metabolites_from_ontologies(test_ontologies)
    assert isinstance(response, dict)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/metabolites-from-ontologies",
        timeout=30,
        json={"ontology": test_ontologies, "format": "json"},
    )

    # Test different output format
    response = ramp_client.get_metabolites_from_ontologies(
        test_ontologies, output_format="csv"
    )
    assert isinstance(response, dict)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/metabolites-from-ontologies",
        timeout=30,
        json={"ontology": test_ontologies, "format": "csv"},
    )


@patch("requests.Session.request")
def test_get_chemical_classes(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test getting chemical classes for metabolites."""
    mock_request.return_value = mock_response

    # Test normal case
    test_metabolites = ["hmdb:HMDB0000064"]
    response = ramp_client.get_chemical_classes(test_metabolites)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/chemical-classes",
        timeout=30,
        json={"metabolites": test_metabolites},
    )
    assert isinstance(response, dict)

    # Test error handling
    mock_request.side_effect = requests.exceptions.RequestException("Test error")
    with pytest.raises(RaMPAPIError) as exc_info:
        ramp_client.get_chemical_classes(test_metabolites)
    assert "Test error" in str(exc_info.value)


@patch("requests.Session.request")
def test_get_common_reaction_analytes(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test getting common reaction analytes."""
    mock_request.return_value = mock_response

    test_analytes = ["uniprot:P31323", "hmdb:HMDB0000122"]
    response = ramp_client.get_common_reaction_analytes(test_analytes)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/common-reaction-analytes",
        timeout=30,
        json={"analyte": test_analytes},
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_reactions_from_analytes(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test getting reactions from analytes."""
    mock_request.return_value = mock_response

    test_analytes = ["uniprot:P31323", "hmdb:HMDB0000122"]
    response = ramp_client.get_reactions_from_analytes(test_analytes)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/reactions-from-analytes",
        timeout=30,
        json={"analytes": test_analytes},
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_reaction_classes(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test getting reaction classes."""
    mock_request.return_value = mock_response

    test_analytes = ["uniprot:P31323", "hmdb:HMDB0000122"]
    response = ramp_client.get_reaction_classes(test_analytes)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/reaction-classes-from-analytes",
        timeout=30,
        json={"analytes": test_analytes},
    )
    assert isinstance(response, dict)


def test_empty_response_handling() -> None:
    """Test handling of empty responses."""
    client = RaMPClient()
    empty_data: dict[str, list[Any]] = {"result": []}
    stats = client.analyze_pathway_stats(empty_data)
    overlaps = client.find_pathway_overlaps(empty_data)
    assert len(stats) == 0
    assert len(overlaps) == 0


@patch("requests.Session.request")
def test_timeout_handling(mock_request: Mock, ramp_client: RaMPClient) -> None:
    """Test timeout handling."""
    mock_request.side_effect = requests.exceptions.Timeout("Timeout")
    with pytest.raises(RaMPAPIError) as exc_info:
        ramp_client.get_source_versions()
    assert "Timeout" in str(exc_info.value)


# Integration-style tests
@patch("requests.Session.request")
def test_full_pathway_analysis_flow(mock_request: Mock) -> None:
    """Test complete pathway analysis workflow with mocked responses."""
    # Create mock response with realistic test data
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": [
            {
                "inputId": "hmdb:HMDB0000064",
                "pathwayName": "Glycolysis",
                "pathwaySource": "kegg",
            },
            {
                "inputId": "hmdb:HMDB0000064",
                "pathwayName": "Gluconeogenesis",
                "pathwaySource": "reactome",
            },
        ]
    }
    mock_request.return_value = mock_response

    client = RaMPClient()
    test_metabolites = ["hmdb:HMDB0000064"]

    pathways = client.get_pathways_from_analytes(test_metabolites)
    stats = client.analyze_pathway_stats(pathways)
    overlaps = client.find_pathway_overlaps(pathways)

    assert isinstance(pathways, dict)
    assert isinstance(stats, dict)
    assert isinstance(overlaps, dict)

    # Verify the actual results
    assert len(stats) == 1
    assert "hmdb:HMDB0000064" in stats
    assert stats["hmdb:HMDB0000064"].total_pathways == 2
    assert len(overlaps) == 2


def test_analyze_pathway_stats_empty_result() -> None:
    """Test pathway statistics analysis with empty result."""
    client = RaMPClient()
    test_data: dict[str, list[Any]] = {"no_result": []}  # Missing 'result' key
    stats = client.analyze_pathway_stats(test_data)
    assert isinstance(stats, dict)
    assert len(stats) == 0


def test_find_pathway_overlaps_empty_result() -> None:
    """Test pathway overlap analysis with empty result."""
    client = RaMPClient()
    test_data: dict[str, list[Any]] = {"no_result": []}  # Missing 'result' key
    overlaps = client.find_pathway_overlaps(test_data)
    assert isinstance(overlaps, dict)
    assert len(overlaps) == 0


@patch("requests.Session.request")
def test_perform_chemical_enrichment(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test performing chemical enrichment analysis."""
    mock_request.return_value = mock_response

    test_metabolites = ["hmdb:HMDB0000064", "hmdb:HMDB0000148"]
    response = ramp_client.perform_chemical_enrichment(test_metabolites)
    mock_request.assert_called_with(
        method="POST",
        url="https://rampdb.nih.gov/api/chemical-enrichment",
        timeout=30,
        json={"metabolites": test_metabolites},
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_full_metabolite_workflow(mock_request: Mock) -> None:
    """Test complete metabolite analysis workflow with mocked responses."""
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": [{"metabolite_data": "test_data"}]}
    mock_request.return_value = mock_response

    client = RaMPClient()
    test_metabolites = ["hmdb:HMDB0000064", "hmdb:HMDB0000148"]

    # Test complete workflow
    properties = client.get_chemical_properties(test_metabolites)
    classes = client.get_chemical_classes(test_metabolites)
    ontologies = client.get_ontologies_from_metabolites(test_metabolites)
    enrichment = client.perform_chemical_enrichment(test_metabolites)

    assert all(
        isinstance(x, dict) for x in [properties, classes, ontologies, enrichment]
    )


@patch("requests.Session.request")
def test_full_analyte_workflow(mock_request: Mock) -> None:
    """Test complete analyte workflow with mocked responses."""
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": [{"reaction_data": "test_data"}]}
    mock_request.return_value = mock_response

    client = RaMPClient()
    test_analytes = ["hmdb:HMDB0000064", "uniprot:P31323"]

    # Test complete workflow
    pathways = client.get_pathways_from_analytes(test_analytes)
    reactions = client.get_reactions_from_analytes(test_analytes)
    reaction_classes = client.get_reaction_classes(test_analytes)
    common_reactions = client.get_common_reaction_analytes(test_analytes)

    assert all(
        isinstance(x, dict)
        for x in [pathways, reactions, reaction_classes, common_reactions]
    )


def test_pathwaystats_dataclass() -> None:
    """Test PathwayStats dataclass initialization and attributes."""
    test_stats = PathwayStats(
        total_pathways=5,
        pathways_by_source={"kegg": 2, "reactome": 3},
        unique_pathway_names={"path1", "path2", "path3"},
        pathway_sources={"kegg", "reactome"},
    )

    assert test_stats.total_pathways == 5
    assert test_stats.pathways_by_source == {"kegg": 2, "reactome": 3}
    assert test_stats.unique_pathway_names == {"path1", "path2", "path3"}
    assert test_stats.pathway_sources == {"kegg", "reactome"}


@patch("requests.Session.request")
def test_get_pathway_by_analyte_basic(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test basic pathway retrieval by analyte ID."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_pathway_by_analyte(["test_id"])
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/pathwayFromAnalyte",
        timeout=30,
        params={"sourceId": ["test_id"], "queryType": "both"},
    )


@patch("requests.Session.request")
def test_get_pathway_by_analyte_with_type(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test pathway retrieval with specific analyte type."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_pathway_by_analyte(["test_id"], AnalyteType.METABOLITE)
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/pathwayFromAnalyte",
        timeout=30,
        params={"sourceId": ["test_id"], "queryType": "metabolite"},
    )


@patch("requests.Session.request")
def test_get_pathway_by_name(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test pathway retrieval by name search."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_pathway_by_name("glycolysis")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/pathwayFromName",
        timeout=30,
        params={"pathway": "glycolysis"},
    )


@patch("requests.Session.request")
def test_get_pathway_by_ontology(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test pathway retrieval using ontology ID."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_pathway_by_ontology("GO:0006096")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/pathwayFromOntology",
        timeout=30,
        params={"ontologyId": "GO:0006096"},
    )


@patch("requests.Session.request")
def test_get_analytes_by_pathway(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test analyte retrieval for a pathway."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_analytes_by_pathway("path_123")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/analyteFromPathway",
        timeout=30,
        params={"pathwayId": "path_123", "queryType": "both"},
    )


@patch("requests.Session.request")
def test_get_analytes_by_ontology(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test analyte retrieval using ontology ID."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": []}  # Add mock response data
    ramp_client.get_analytes_by_ontology("GO:0006096")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/analyteFromOntology",
        timeout=30,
        params={"ontologyId": "GO:0006096", "queryType": "both"},
    )


def test_pathway_stats() -> None:
    """Test pathway statistics calculation."""
    client = RaMPClient()
    result = client.analyze_pathway_stats({"result": []})
    assert isinstance(result, dict)


def test_analyze_pathway_stats_invalid_data() -> None:
    """Test pathway statistics analysis with invalid data structure."""
    client = RaMPClient()

    # Test with invalid data structure
    invalid_data: dict[str, list[Any]] = {"wrong_key": []}
    stats = client.analyze_pathway_stats(invalid_data)
    assert isinstance(stats, dict)
    assert len(stats) == 0


def test_find_pathway_overlaps_invalid_data() -> None:
    """Test pathway overlap analysis with invalid data structure."""
    client = RaMPClient()

    # Test with invalid data structure
    invalid_data: dict[str, list[Any]] = {"wrong_key": []}
    overlaps = client.find_pathway_overlaps(invalid_data)
    assert isinstance(overlaps, dict)
    assert len(overlaps) == 0


@patch("requests.Session.request")
def test_get_pathway_info(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test retrieving detailed pathway information."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": [{"pathway_data": "test_data"}]}

    response = ramp_client.get_pathway_info("path_123")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/pathwayInfo/path_123",
        timeout=30,
    )
    assert isinstance(response, dict)


@patch("requests.Session.request")
def test_get_metabolite_info(
    mock_request: Mock, ramp_client: RaMPClient, mock_response: Mock
) -> None:
    """Test retrieving detailed metabolite information."""
    mock_request.return_value = mock_response
    mock_response.json.return_value = {"result": [{"metabolite_data": "test_data"}]}

    response = ramp_client.get_metabolite_info("hmdb:HMDB0000064")
    mock_request.assert_called_with(
        method="GET",
        url="https://rampdb.nih.gov/api/metaboliteInfo/hmdb:HMDB0000064",
        timeout=30,
    )
    assert isinstance(response, dict)

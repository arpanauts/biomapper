"""Unit tests for the TranslatorNameResolverClient."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient
from biomapper.core.exceptions import ClientExecutionError


@pytest.fixture
def name_resolver_client():
    """Create a TranslatorNameResolverClient instance for testing."""
    return TranslatorNameResolverClient({
        "target_db": "CHEBI"
    })


@pytest.fixture
def mock_api_response():
    """Create a mock API response for name resolution."""
    return [
        {
            "curie": "CHEBI:15377",
            "label": "glucose",
            "score": 0.9876,
            "types": ["biolink:SmallMolecule", "biolink:ChemicalSubstance"]
        },
        {
            "curie": "CHEBI:17925",
            "label": "D-glucose",
            "score": 0.8765,
            "types": ["biolink:SmallMolecule", "biolink:ChemicalSubstance"]
        },
        {
            "curie": "PUBCHEM.COMPOUND:5793",
            "label": "glucose",
            "score": 0.7654,
            "types": ["biolink:SmallMolecule", "biolink:ChemicalSubstance"]
        }
    ]


@pytest.mark.asyncio
async def test_init():
    """Test TranslatorNameResolverClient initialization with different configurations."""
    # Test with default config values
    client = TranslatorNameResolverClient({
        "target_db": "CHEBI"
    })
    assert client.target_db == "CHEBI"
    assert client.match_threshold == 0.5
    
    # Test with custom match threshold
    client = TranslatorNameResolverClient({
        "target_db": "CHEBI",
        "match_threshold": 0.75
    })
    assert client.target_db == "CHEBI"
    assert client.match_threshold == 0.75
    
    # Test with lowercase database name (should be converted to uppercase)
    client = TranslatorNameResolverClient({
        "target_db": "chebi"
    })
    assert client.target_db == "CHEBI"


@pytest.mark.asyncio
async def test_filter_matches_by_target_db(name_resolver_client, mock_api_response):
    """Test _filter_matches_by_target_db method."""
    # Filter for CHEBI (should get 2 matches)
    filtered = name_resolver_client._filter_matches_by_target_db(mock_api_response)
    assert len(filtered) == 2
    assert filtered[0]["curie"] == "CHEBI:15377"
    assert filtered[1]["curie"] == "CHEBI:17925"
    
    # Change target DB to PUBCHEM (should get 1 match)
    name_resolver_client.target_db = "PUBCHEM"
    filtered = name_resolver_client._filter_matches_by_target_db(mock_api_response)
    assert len(filtered) == 1
    assert filtered[0]["curie"] == "PUBCHEM.COMPOUND:5793"
    
    # Change to unsupported DB (should return empty list)
    name_resolver_client.target_db = "UNSUPPORTED"
    filtered = name_resolver_client._filter_matches_by_target_db(mock_api_response)
    assert len(filtered) == 0


@pytest.mark.asyncio
async def test_extract_identifier_from_curie(name_resolver_client):
    """Test _extract_identifier_from_curie method."""
    # Test standard format
    identifier = name_resolver_client._extract_identifier_from_curie("CHEBI:15377")
    assert identifier == "15377"
    
    # Test with no colon
    identifier = name_resolver_client._extract_identifier_from_curie("CHEBI15377")
    assert identifier == "CHEBI15377"
    
    # Test with multiple colons
    identifier = name_resolver_client._extract_identifier_from_curie("MESH:D:12345")
    assert identifier == "D:12345"


@pytest.mark.asyncio
async def test_map_identifiers(name_resolver_client, mock_api_response):
    """Test map_identifiers method."""
    # Mock the _lookup_entity_name method
    with patch.object(name_resolver_client, '_lookup_entity_name', new_callable=AsyncMock) as mock_lookup:
        # Setup the mock to return a valid response
        mock_lookup.return_value = [
            {
                "curie": "CHEBI:15377",
                "label": "glucose",
                "score": 0.9876,
                "types": ["biolink:SmallMolecule", "biolink:ChemicalSubstance"]
            },
            {
                "curie": "CHEBI:17925",
                "label": "D-glucose",
                "score": 0.8765,
                "types": ["biolink:SmallMolecule", "biolink:ChemicalSubstance"]
            }
        ]
        
        # Test mapping a single name
        result = await name_resolver_client.map_identifiers(["glucose"])
        assert "glucose" in result
        assert result["glucose"][0] == ["15377", "17925"]  # First element of tuple is the mapped IDs
        assert result["glucose"][1] == "0.9876"  # Second element is the best score
        
        # Verify the biolink type used in the request
        mock_lookup.assert_called_once()
        call_args = mock_lookup.call_args[0]
        assert call_args[0] == "glucose"
        assert call_args[1] == "biolink:SmallMolecule"


@pytest.mark.asyncio
async def test_map_identifiers_empty_input(name_resolver_client):
    """Test map_identifiers with empty input."""
    result = await name_resolver_client.map_identifiers([])
    assert result == {}


@pytest.mark.asyncio
async def test_map_identifiers_no_results(name_resolver_client):
    """Test map_identifiers when no results are found."""
    # Mock the _lookup_entity_name method to return empty result
    with patch.object(name_resolver_client, '_lookup_entity_name', new_callable=AsyncMock) as mock_lookup:
        mock_lookup.return_value = []
        
        # Test mapping a name with no results
        result = await name_resolver_client.map_identifiers(["nonexistent"])
        assert "nonexistent" in result
        assert result["nonexistent"][0] is None  # No mapping found
        assert result["nonexistent"][1] is None  # No score


@pytest.mark.asyncio
async def test_map_identifiers_multiple_names(name_resolver_client):
    """Test map_identifiers with multiple names."""
    # Mock the _lookup_entity_name method
    with patch.object(name_resolver_client, '_lookup_entity_name', new_callable=AsyncMock) as mock_lookup:
        # Setup different responses for different inputs
        async def mock_lookup_side_effect(name, _):
            if name == "glucose":
                return [
                    {
                        "curie": "CHEBI:15377",
                        "label": "glucose",
                        "score": 0.9876,
                        "types": ["biolink:SmallMolecule"]
                    }
                ]
            elif name == "aspirin":
                return [
                    {
                        "curie": "CHEBI:15365",
                        "label": "aspirin",
                        "score": 0.9543,
                        "types": ["biolink:SmallMolecule"]
                    }
                ]
            else:
                return []
        
        mock_lookup.side_effect = mock_lookup_side_effect
        
        # Test mapping multiple names
        result = await name_resolver_client.map_identifiers(["glucose", "aspirin", "nonexistent"])
        
        # Check glucose results
        assert "glucose" in result
        assert result["glucose"][0] == ["15377"]
        assert result["glucose"][1] == "0.9876"
        
        # Check aspirin results
        assert "aspirin" in result
        assert result["aspirin"][0] == ["15365"]
        assert result["aspirin"][1] == "0.9543"
        
        # Check nonexistent results
        assert "nonexistent" in result
        assert result["nonexistent"][0] is None
        assert result["nonexistent"][1] is None


@pytest.mark.asyncio
async def test_lookup_entity_name(name_resolver_client, mock_api_response):
    """Test _lookup_entity_name method."""
    # Mock the _perform_request method
    with patch.object(name_resolver_client, '_perform_request', new_callable=AsyncMock) as mock_perform_request:
        # Setup the mock to return a valid response
        mock_perform_request.return_value = mock_api_response
        
        # Test looking up a name
        result = await name_resolver_client._lookup_entity_name("glucose", "biolink:SmallMolecule")
        
        # Should filter to just CHEBI results (2 matches)
        assert len(result) == 2
        assert result[0]["curie"] == "CHEBI:15377"
        assert result[1]["curie"] == "CHEBI:17925"
        
        # Verify the URL and parameters used in the request
        mock_perform_request.assert_called_once()
        call_args, call_kwargs = mock_perform_request.call_args
        
        # Check URL
        assert "https://name-resolution-sri.renci.org/lookup" in call_args[0]
        
        # Check parameters
        params = call_kwargs["params"]
        assert params["string"] == "glucose"
        assert params["biolink_type"] == "biolink:SmallMolecule"
        assert "limit" in params
        assert "offset" in params


@pytest.mark.asyncio
async def test_perform_request_success(name_resolver_client, mock_api_response):
    """Test _perform_request method with successful response."""
    # Create a mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_api_response)
    
    # Mock the session's get method
    name_resolver_client._session = MagicMock()
    name_resolver_client._session.get = MagicMock()
    name_resolver_client._session.get.return_value.__aenter__.return_value = mock_response
    
    # Call the method
    result = await name_resolver_client._perform_request(
        "https://name-resolution-sri.renci.org/lookup",
        {"string": "glucose", "biolink_type": "biolink:SmallMolecule"}
    )
    
    # Verify the result
    assert result == mock_api_response


@pytest.mark.asyncio
async def test_perform_request_failure(name_resolver_client):
    """Test _perform_request method with error response."""
    # Create a mock response with error
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    
    # Mock the session's get method
    name_resolver_client._session = MagicMock()
    name_resolver_client._session.get = MagicMock()
    name_resolver_client._session.get.return_value.__aenter__.return_value = mock_response
    
    # Set a low max_retries for faster test
    name_resolver_client._config["max_retries"] = 1
    name_resolver_client._config["backoff_factor"] = 0.01
    
    # Call the method and expect an exception
    with pytest.raises(ClientExecutionError):
        await name_resolver_client._perform_request(
            "https://name-resolution-sri.renci.org/lookup",
            {"string": "glucose", "biolink_type": "biolink:SmallMolecule"}
        )


@pytest.mark.asyncio
async def test_reverse_map_identifiers(name_resolver_client):
    """Test reverse_map_identifiers method (should raise NotImplementedError)."""
    with pytest.raises(NotImplementedError):
        await name_resolver_client.reverse_map_identifiers(["CHEBI:15377"])


@pytest.mark.asyncio
async def test_caching(name_resolver_client):
    """Test that results are properly cached."""
    # Mock the _lookup_entity_name method
    with patch.object(name_resolver_client, '_lookup_entity_name', new_callable=AsyncMock) as mock_lookup:
        # Setup the mock to return a valid response
        mock_lookup.return_value = [
            {
                "curie": "CHEBI:15377",
                "label": "glucose",
                "score": 0.9876,
                "types": ["biolink:SmallMolecule"]
            }
        ]
        
        # First call should use the lookup
        result1 = await name_resolver_client.map_identifiers(["glucose"])
        assert mock_lookup.call_count == 1
        
        # Second call with same input should use the cache
        result2 = await name_resolver_client.map_identifiers(["glucose"])
        assert mock_lookup.call_count == 1  # Still only called once
        
        # Results should be the same
        assert result1 == result2
        
        # Verify cache stats show a hit
        cache_stats = name_resolver_client.get_cache_stats()
        assert cache_stats["cache_hits"] == 1


@pytest.mark.asyncio
async def test_close(name_resolver_client):
    """Test close method."""
    # Create a mock session
    mock_session = MagicMock()
    mock_session.close = AsyncMock()
    name_resolver_client._session = mock_session
    name_resolver_client._initialized = True
    
    # Call close method
    await name_resolver_client.close()
    
    # Verify session.close was called
    mock_session.close.assert_called_once()
    assert name_resolver_client._session is None
    assert name_resolver_client._initialized is False
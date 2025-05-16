"""Unit tests for the UniChemClient."""

import pytest
import aiohttp
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from biomapper.mapping.clients.unichem_client import UniChemClient
from biomapper.core.exceptions import ClientExecutionError


@pytest.fixture
def unichem_client():
    """Create a UniChemClient instance for testing."""
    return UniChemClient({
        "source_db": "PUBCHEM",
        "target_db": "CHEBI"
    })


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    mock = MagicMock()
    mock.status = 200
    mock.json = AsyncMock(return_value=[
        {
            "src_id": 7,
            "src_name": "CHEBI",
            "src_compound_id": "CHEBI:123456"
        }
    ])
    return mock


@pytest.mark.asyncio
async def test_init():
    """Test UniChemClient initialization with different configurations."""
    # Test with default config values
    client = UniChemClient({
        "source_db": "PUBCHEM",
        "target_db": "CHEBI"
    })
    assert client.source_db == "PUBCHEM"
    assert client.target_db == "CHEBI"
    
    # Test with lowercase database names (should be converted to uppercase)
    client = UniChemClient({
        "source_db": "pubchem",
        "target_db": "chebi"
    })
    assert client.source_db == "PUBCHEM"
    assert client.target_db == "CHEBI"


@pytest.mark.asyncio
async def test_get_unichem_source_id(unichem_client):
    """Test _get_unichem_source_id method."""
    # Test valid database
    source_id = await unichem_client._get_unichem_source_id("CHEBI")
    assert source_id == 7
    
    # Test database name case insensitivity
    source_id = await unichem_client._get_unichem_source_id("chebi")
    assert source_id == 7
    
    # Test invalid database
    with pytest.raises(ClientExecutionError):
        await unichem_client._get_unichem_source_id("INVALID_DB")


@pytest.mark.asyncio
async def test_map_identifiers(unichem_client, mock_response):
    """Test map_identifiers method."""
    # Mock the _perform_request method
    with patch.object(unichem_client, '_perform_request', new_callable=AsyncMock) as mock_perform_request:
        # Setup the mock to return a valid response
        mock_perform_request.return_value = [
            {
                "src_id": 7,
                "src_name": "CHEBI",
                "src_compound_id": "CHEBI:123456"
            }
        ]
        
        # Test mapping a single identifier
        result = await unichem_client.map_identifiers(["123"])
        assert "123" in result
        assert result["123"][0] == ["CHEBI:123456"]  # First element of tuple is the mapped IDs
        assert result["123"][1] is None  # Second element should be None (no component ID)
        
        # Verify the URL used in the request
        mock_perform_request.assert_called_once()
        call_args = mock_perform_request.call_args[0][0]
        assert "src_compound_id/123/src_id/22" in call_args  # PUBCHEM source_id is 22


@pytest.mark.asyncio
async def test_map_identifiers_empty_input(unichem_client):
    """Test map_identifiers with empty input."""
    result = await unichem_client.map_identifiers([])
    assert result == {}


@pytest.mark.asyncio
async def test_map_identifiers_missing_mapping(unichem_client):
    """Test map_identifiers when no mapping is found."""
    # Mock the _perform_request method to return empty result
    with patch.object(unichem_client, '_perform_request', new_callable=AsyncMock) as mock_perform_request:
        mock_perform_request.return_value = []
        
        # Test mapping an identifier with no mapping
        result = await unichem_client.map_identifiers(["123"])
        assert "123" in result
        assert result["123"][0] is None  # No mapping found


@pytest.mark.asyncio
async def test_reverse_map_identifiers(unichem_client, mock_response):
    """Test reverse_map_identifiers method."""
    # Mock the map_identifiers method to verify it's called with swapped source/target
    with patch.object(unichem_client, 'map_identifiers', new_callable=AsyncMock) as mock_map:
        mock_map.return_value = {"CHEBI:123": (["123"], None)}
        
        # Call reverse_map_identifiers
        await unichem_client.reverse_map_identifiers(["CHEBI:123"])
        
        # Verify map_identifiers was called with swapped source/target
        mock_map.assert_called_once()
        _, kwargs = mock_map.call_args
        assert "config" in kwargs
        assert kwargs["config"]["source_db"] == "CHEBI"
        assert kwargs["config"]["target_db"] == "PUBCHEM"


@pytest.mark.asyncio
async def test_close(unichem_client):
    """Test close method."""
    # Create a mock session
    unichem_client._session = MagicMock()
    unichem_client._session.close = AsyncMock()
    
    # Call close method
    await unichem_client.close()
    
    # Verify session.close was called
    unichem_client._session.close.assert_called_once()
    assert unichem_client._session is None
    assert unichem_client._initialized is False

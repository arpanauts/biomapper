"""Unit tests for the UMLSClient."""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

from biomapper.mapping.clients.umls_client import UMLSClient
from biomapper.core.exceptions import ClientInitializationError


@pytest.fixture
def umls_client():
    """Create a UMLSClient instance for testing."""
    return UMLSClient({
        "api_key": "dummy-api-key",
        "target_db": "CHEBI"
    })


@pytest.fixture
def mock_tgt_response():
    """Create a mock TGT response for authentication testing."""
    return """
    <html>
        <head><title>TGT Response</title></head>
        <body>
            <form action="https://utslogin.nlm.nih.gov/cas/v1/api-key/TGT-12345-67890-abcde">
                <input type="hidden" name="service" value="service_url" />
                <input type="submit" value="Submit" />
            </form>
        </body>
    </html>
    """


@pytest.fixture
def mock_search_response():
    """Create a mock search response."""
    return {
        "result": {
            "results": [
                {
                    "ui": "C0017725",
                    "name": "D-Glucose",
                    "rootSource": "MTH",
                    "uri": "https://uts-ws.nlm.nih.gov/rest/content/current/CUI/C0017725",
                    "rootSource": "MTH"
                },
                {
                    "ui": "C0017743",
                    "name": "Glucose",
                    "rootSource": "MTH",
                    "uri": "https://uts-ws.nlm.nih.gov/rest/content/current/CUI/C0017743",
                    "rootSource": "MTH"
                }
            ],
            "pageSize": 100,
            "pageNumber": 1,
            "totalResults": 2
        }
    }


@pytest.fixture
def mock_concept_details():
    """Create mock concept details."""
    return {
        "ui": "C0017743",
        "name": "Glucose",
        "rootSource": "MTH",
        "atoms": [],
        "definitions": [],
        "relations": [],
        "semanticTypes": [
            {
                "name": "Organic Chemical",
                "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T109"
            },
            {
                "name": "Carbohydrate",
                "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T118"
            }
        ]
    }


@pytest.fixture
def mock_atoms_response():
    """Create mock atoms response."""
    return [
        {
            "ui": "A12345678",
            "name": "Glucose",
            "rootSource": "CHEBI",
            "code": "15377",
            "termType": "PT"
        },
        {
            "ui": "A87654321",
            "name": "D-Glucose",
            "rootSource": "CHEBI",
            "code": "4167",
            "termType": "SY"
        },
        {
            "ui": "A11223344",
            "name": "Glucose",
            "rootSource": "PUBCHEM",
            "code": "5793",
            "termType": "PT"
        }
    ]


@pytest.mark.asyncio
async def test_init():
    """Test UMLSClient initialization."""
    # Test with default config values
    client = UMLSClient({
        "api_key": "dummy-api-key",
        "target_db": "CHEBI"
    })
    assert client.target_db == "CHEBI"
    
    # Test with lowercase database name (should be converted to uppercase)
    client = UMLSClient({
        "api_key": "dummy-api-key",
        "target_db": "chebi"
    })
    assert client.target_db == "CHEBI"
    
    # Test without API key (should raise an error)
    with pytest.raises(ClientInitializationError):
        UMLSClient({
            "target_db": "CHEBI"
        })


@pytest.mark.asyncio
async def test_get_tgt(umls_client, mock_tgt_response):
    """Test _get_tgt method."""
    # Mock the session's post method
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.text = AsyncMock(return_value=mock_tgt_response)
    
    # Setup the mock
    umls_client._session = MagicMock()
    umls_client._session.post = MagicMock()
    umls_client._session.post.return_value.__aenter__.return_value = mock_response
    
    # Test getting a TGT
    tgt = await umls_client._get_tgt()
    
    # Verify the result
    assert tgt is not None
    assert "TGT-12345-67890-abcde" in tgt
    
    # Verify the post call was made with the right parameters
    umls_client._session.post.assert_called_once()
    call_args, call_kwargs = umls_client._session.post.call_args
    assert call_args[0] == umls_client._config["auth_url"]
    assert call_kwargs["data"] == {"apikey": "dummy-api-key"}


@pytest.mark.asyncio
async def test_get_service_ticket(umls_client):
    """Test _get_service_ticket method."""
    # Mock the TGT
    tgt_url = "https://utslogin.nlm.nih.gov/cas/v1/api-key/TGT-12345-67890-abcde"
    
    # Mock the session's post method
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="ST-12345-67890-abcde")
    
    # Setup the mock
    umls_client._session = MagicMock()
    umls_client._session.post = MagicMock()
    umls_client._session.post.return_value.__aenter__.return_value = mock_response
    
    # Mock the _get_tgt method to return our test TGT
    with patch.object(umls_client, '_get_tgt', new_callable=AsyncMock) as mock_get_tgt:
        mock_get_tgt.return_value = tgt_url
        
        # Test getting a service ticket
        service_ticket = await umls_client._get_service_ticket()
        
        # Verify the result
        assert service_ticket == "ST-12345-67890-abcde"
        
        # Verify the post call was made with the right parameters
        umls_client._session.post.assert_called_once()
        call_args, call_kwargs = umls_client._session.post.call_args
        assert call_args[0] == tgt_url
        assert "service" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_perform_search(umls_client, mock_search_response):
    """Test _perform_search method."""
    # Mock the service ticket
    service_ticket = "ST-12345-67890-abcde"
    
    # Mock the session's get method
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_search_response)
    
    # Setup the mock
    umls_client._session = MagicMock()
    umls_client._session.get = MagicMock()
    umls_client._session.get.return_value.__aenter__.return_value = mock_response
    
    # Mock the _get_service_ticket method
    with patch.object(umls_client, '_get_service_ticket', new_callable=AsyncMock) as mock_get_st:
        mock_get_st.return_value = service_ticket
        
        # Test performing a search
        results = await umls_client._perform_search("glucose", search_type="exact")
        
        # Verify the results
        assert len(results) == 2
        assert results[0]["ui"] == "C0017725"
        assert results[0]["name"] == "D-Glucose"
        assert results[1]["ui"] == "C0017743"
        assert results[1]["name"] == "Glucose"
        
        # Verify the get call was made with the right parameters
        umls_client._session.get.assert_called_once()
        call_args, call_kwargs = umls_client._session.get.call_args
        assert umls_client._config["base_url"] in call_args[0]
        assert call_kwargs["params"]["string"] == "glucose"
        assert call_kwargs["params"]["searchType"] == "exact"
        assert call_kwargs["params"]["ticket"] == service_ticket


@pytest.mark.asyncio
async def test_get_concept_details(umls_client, mock_concept_details):
    """Test _get_concept_details method."""
    # Mock the service ticket
    service_ticket = "ST-12345-67890-abcde"
    
    # Mock the session's get method
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": mock_concept_details})
    
    # Setup the mock
    umls_client._session = MagicMock()
    umls_client._session.get = MagicMock()
    umls_client._session.get.return_value.__aenter__.return_value = mock_response
    
    # Mock the _get_service_ticket method
    with patch.object(umls_client, '_get_service_ticket', new_callable=AsyncMock) as mock_get_st:
        mock_get_st.return_value = service_ticket
        
        # Test getting concept details
        concept = await umls_client._get_concept_details("C0017743")
        
        # Verify the results
        assert concept["ui"] == "C0017743"
        assert concept["name"] == "Glucose"
        assert len(concept["semanticTypes"]) == 2
        assert concept["semanticTypes"][0]["name"] == "Organic Chemical"
        
        # Verify the get call was made with the right parameters
        umls_client._session.get.assert_called_once()
        call_args, call_kwargs = umls_client._session.get.call_args
        assert "C0017743" in call_args[0]
        assert call_kwargs["params"]["ticket"] == service_ticket


@pytest.mark.asyncio
async def test_get_concept_atoms(umls_client, mock_atoms_response):
    """Test _get_concept_atoms method."""
    # Mock the service ticket
    service_ticket = "ST-12345-67890-abcde"
    
    # Mock the session's get method
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": mock_atoms_response})
    
    # Setup the mock
    umls_client._session = MagicMock()
    umls_client._session.get = MagicMock()
    umls_client._session.get.return_value.__aenter__.return_value = mock_response
    
    # Mock the _get_service_ticket method
    with patch.object(umls_client, '_get_service_ticket', new_callable=AsyncMock) as mock_get_st:
        mock_get_st.return_value = service_ticket
        
        # Test getting concept atoms
        atoms = await umls_client._get_concept_atoms("C0017743")
        
        # Verify the results
        assert len(atoms) == 3
        assert atoms[0]["rootSource"] == "CHEBI"
        assert atoms[0]["code"] == "15377"
        assert atoms[1]["rootSource"] == "CHEBI"
        assert atoms[1]["code"] == "4167"
        assert atoms[2]["rootSource"] == "PUBCHEM"
        assert atoms[2]["code"] == "5793"
        
        # Verify the get call was made with the right parameters
        umls_client._session.get.assert_called_once()
        call_args, call_kwargs = umls_client._session.get.call_args
        assert "C0017743" in call_args[0]
        assert "atoms" in call_args[0]
        assert call_kwargs["params"]["ticket"] == service_ticket


@pytest.mark.asyncio
async def test_extract_target_identifiers(umls_client, mock_atoms_response):
    """Test _extract_target_identifiers method."""
    # Test extracting CHEBI identifiers
    chebi_ids = umls_client._extract_target_identifiers(mock_atoms_response, "CHEBI")
    assert len(chebi_ids) == 2
    assert "15377" in chebi_ids
    assert "4167" in chebi_ids
    
    # Test extracting PUBCHEM identifiers
    pubchem_ids = umls_client._extract_target_identifiers(mock_atoms_response, "PUBCHEM")
    assert len(pubchem_ids) == 1
    assert "5793" in pubchem_ids
    
    # Test extracting identifiers for an unsupported source
    unsupported_ids = umls_client._extract_target_identifiers(mock_atoms_response, "UNSUPPORTED")
    assert len(unsupported_ids) == 0


@pytest.mark.asyncio
async def test_is_metabolite_concept(umls_client, mock_concept_details):
    """Test _is_metabolite_concept method."""
    # Test with a concept that has metabolite semantic types
    assert umls_client._is_metabolite_concept(mock_concept_details) is True
    
    # Test with a concept that doesn't have metabolite semantic types
    non_metabolite_concept = mock_concept_details.copy()
    non_metabolite_concept["semanticTypes"] = [
        {
            "name": "Disease or Syndrome",
            "uri": "https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T047"
        }
    ]
    assert umls_client._is_metabolite_concept(non_metabolite_concept) is False
    
    # Test with a concept that has no semantic types
    no_types_concept = mock_concept_details.copy()
    no_types_concept["semanticTypes"] = []
    assert umls_client._is_metabolite_concept(no_types_concept) is False


@pytest.mark.asyncio
async def test_resolve_term(umls_client, mock_search_response, mock_concept_details, mock_atoms_response):
    """Test _resolve_term method."""
    # Mock the necessary methods
    with patch.object(umls_client, '_perform_search', new_callable=AsyncMock) as mock_search, \
         patch.object(umls_client, '_get_concept_details', new_callable=AsyncMock) as mock_details, \
         patch.object(umls_client, '_get_concept_atoms', new_callable=AsyncMock) as mock_atoms:
        
        # Setup the mocks
        mock_search.return_value = mock_search_response["result"]["results"]
        mock_details.return_value = mock_concept_details
        mock_atoms.return_value = mock_atoms_response
        
        # Test resolving a term
        results = await umls_client._resolve_term("glucose")
        
        # Verify the results
        assert len(results) == 2  # Two concepts from the search
        assert results[0]["ui"] == "C0017743"
        assert results[0]["name"] == "Glucose"
        assert "atoms" in results[0]
        assert "score" in results[0]
        
        # Verify the method calls
        mock_search.assert_called_once()
        assert mock_details.call_count == 2  # Once for each concept
        assert mock_atoms.call_count == 2  # Once for each concept


@pytest.mark.asyncio
async def test_map_identifiers(umls_client):
    """Test map_identifiers method."""
    # Mock the _resolve_term method
    with patch.object(umls_client, '_resolve_term', new_callable=AsyncMock) as mock_resolve:
        # Setup the mock to return a valid response for glucose
        mock_resolve.return_value = [
            {
                "ui": "C0017743",
                "name": "Glucose",
                "score": 0.95,
                "atoms": [
                    {
                        "rootSource": "CHEBI",
                        "code": "15377"
                    },
                    {
                        "rootSource": "CHEBI",
                        "code": "4167"
                    }
                ]
            }
        ]
        
        # Test mapping a single term
        result = await umls_client.map_identifiers(["glucose"])
        
        # Verify the results
        assert "glucose" in result
        assert result["glucose"][0] == ["15377", "4167"]  # First element of tuple is the mapped IDs
        assert result["glucose"][1] == "0.95"  # Second element is the score
        
        # Setup the mock to return an empty response for an unknown term
        mock_resolve.side_effect = lambda term: [] if term == "unknown" else mock_resolve.return_value
        
        # Test mapping multiple terms
        result = await umls_client.map_identifiers(["glucose", "unknown"])
        
        # Verify the results
        assert "glucose" in result
        assert result["glucose"][0] == ["15377", "4167"]
        assert result["glucose"][1] == "0.95"
        
        assert "unknown" in result
        assert result["unknown"][0] is None  # No mapping found
        assert result["unknown"][1] is None  # No score


@pytest.mark.asyncio
async def test_map_identifiers_empty_input(umls_client):
    """Test map_identifiers with empty input."""
    result = await umls_client.map_identifiers([])
    assert result == {}


@pytest.mark.asyncio
async def test_reverse_map_identifiers(umls_client):
    """Test reverse_map_identifiers method."""
    # Mock the _perform_search method
    with patch.object(umls_client, '_perform_search', new_callable=AsyncMock) as mock_search:
        # Setup the mock to return a valid response
        mock_search.return_value = [
            {
                "ui": "C0017743",
                "name": "Glucose",
                "rootSource": "MTH"
            }
        ]
        
        # Test reverse mapping an identifier
        result = await umls_client.reverse_map_identifiers(["15377"])
        
        # Verify the results
        assert "15377" in result
        assert result["15377"][0] == ["Glucose"]  # First element is the names
        assert result["15377"][1] is not None  # Second element is the score
        
        # Setup the mock to return an empty response for an unknown identifier
        mock_search.side_effect = lambda term, **kwargs: [] if "unknown" in term else mock_search.return_value
        
        # Test reverse mapping multiple identifiers
        result = await umls_client.reverse_map_identifiers(["15377", "unknown"])
        
        # Verify the results
        assert "15377" in result
        assert result["15377"][0] == ["Glucose"]
        
        assert "unknown" in result
        assert result["unknown"][0] is None  # No mapping found
        assert result["unknown"][1] is None  # No score


@pytest.mark.asyncio
async def test_close(umls_client):
    """Test close method."""
    # Create a mock session
    mock_session = MagicMock()
    mock_session.close = AsyncMock()
    umls_client._session = mock_session
    umls_client._initialized = True
    umls_client._tgt = "TGT-12345-67890-abcde"
    umls_client._tgt_timestamp = time.time()
    
    # Call close method
    await umls_client.close()
    
    # Verify session.close was called
    mock_session.close.assert_called_once()
    assert umls_client._session is None
    assert umls_client._initialized is False
    assert umls_client._tgt is None
    assert umls_client._tgt_timestamp == 0
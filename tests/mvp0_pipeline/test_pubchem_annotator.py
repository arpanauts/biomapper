import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from biomapper.mvp0_pipeline.pubchem_annotator import fetch_pubchem_annotations, fetch_single_cid_annotation
from biomapper.schemas.mvp0_schema import PubChemAnnotation


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def mock_response_data():
    """Sample response data for testing."""
    return {
        "properties": {
            "PropertyTable": {
                "Properties": [{
                    "CID": 5793,
                    "Title": "D-Glucose",
                    "IUPACName": "(3R,4S,5S,6R)-6-(hydroxymethyl)oxane-2,3,4,5-tetrol",
                    "MolecularFormula": "C6H12O6",
                    "CanonicalSMILES": "C(C1C(C(C(C(O1)O)O)O)O)O",
                    "InChIKey": "WQZGKKKJIJFFOK-GASJEMHNSA-N"
                }]
            }
        },
        "synonyms": {
            "InformationList": {
                "Information": [{
                    "CID": 5793,
                    "Synonym": ["D-Glucose", "Dextrose", "Grape sugar", "Blood sugar"]
                }]
            }
        },
        "description": {
            "InformationList": {
                "Information": [{
                    "CID": 5793,
                    "Description": "D-glucopyranose is a glucopyranose having D-configuration."
                }]
            }
        }
    }


class TestPubChemAnnotator:
    """Test cases for the PubChem annotator module."""
    
    @pytest.mark.asyncio
    async def test_fetch_single_cid_annotation_success(self, mock_httpx_client, mock_response_data):
        """Test successful annotation of a single CID."""
        # Mock successful responses
        mock_prop_response = MagicMock()
        mock_prop_response.status_code = 200
        mock_prop_response.json = MagicMock(return_value=mock_response_data["properties"])
        mock_prop_response.raise_for_status = MagicMock()
        
        mock_syn_response = MagicMock()
        mock_syn_response.status_code = 200
        mock_syn_response.json = MagicMock(return_value=mock_response_data["synonyms"])
        
        mock_desc_response = MagicMock()
        mock_desc_response.status_code = 200
        mock_desc_response.json = MagicMock(return_value=mock_response_data["description"])
        
        # Configure client to return appropriate responses
        mock_httpx_client.get.side_effect = [
            mock_prop_response,
            mock_syn_response,
            mock_desc_response
        ]
        
        # Test the function
        result = await fetch_single_cid_annotation(mock_httpx_client, 5793)
        
        # Verify result
        assert isinstance(result, PubChemAnnotation)
        assert result.cid == 5793
        assert result.title == "D-Glucose"
        assert result.iupac_name == "(3R,4S,5S,6R)-6-(hydroxymethyl)oxane-2,3,4,5-tetrol"
        assert result.molecular_formula == "C6H12O6"
        assert len(result.synonyms) == 4
        assert result.description == "D-glucopyranose is a glucopyranose having D-configuration."
    
    @pytest.mark.asyncio
    async def test_fetch_single_cid_annotation_not_found(self, mock_httpx_client):
        """Test handling of non-existent CID."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        
        mock_httpx_client.get.return_value = mock_response
        
        # Test the function
        result = await fetch_single_cid_annotation(mock_httpx_client, 999999999)
        
        # Verify result
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_pubchem_annotations_multiple_cids(self):
        """Test fetching annotations for multiple CIDs."""
        test_cids = [5793, 2244, 999999999]
        
        with patch('biomapper.mvp0_pipeline.pubchem_annotator.fetch_single_cid_annotation') as mock_fetch:
            # Mock successful annotations for first two CIDs, None for the last
            mock_fetch.side_effect = [
                PubChemAnnotation(cid=5793, title="D-Glucose"),
                PubChemAnnotation(cid=2244, title="Aspirin"),
                None  # Non-existent CID
            ]
            
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                # Test the function
                result = await fetch_pubchem_annotations(test_cids)
        
        # Verify results
        assert len(result) == 2
        assert 5793 in result
        assert 2244 in result
        assert 999999999 not in result
        assert result[5793].title == "D-Glucose"
        assert result[2244].title == "Aspirin"
    
    @pytest.mark.asyncio
    async def test_fetch_pubchem_annotations_empty_list(self):
        """Test handling of empty CID list."""
        result = await fetch_pubchem_annotations([])
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_fetch_pubchem_annotations_with_errors(self):
        """Test error handling during batch processing."""
        test_cids = [5793, 2244]
        
        with patch('biomapper.mvp0_pipeline.pubchem_annotator.fetch_single_cid_annotation') as mock_fetch:
            # Mock one successful and one exception
            mock_fetch.side_effect = [
                PubChemAnnotation(cid=5793, title="D-Glucose"),
                Exception("Network error")
            ]
            
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                # Test the function
                result = await fetch_pubchem_annotations(test_cids)
        
        # Verify results - should still get the successful one
        assert len(result) == 1
        assert 5793 in result
        assert 2244 not in result
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiting is respected."""
        # This is a basic test to ensure the semaphore is used
        # In a real scenario, you'd test timing but that's complex in unit tests
        test_cids = list(range(20))  # 20 CIDs to test batching
        
        with patch('biomapper.mvp0_pipeline.pubchem_annotator.fetch_single_cid_annotation') as mock_fetch:
            # Mock all as successful
            mock_fetch.return_value = PubChemAnnotation(cid=1, title="Test")
            
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                # Test the function
                result = await fetch_pubchem_annotations(test_cids)
        
        # Verify batching occurred (should be called 20 times for 20 CIDs)
        assert mock_fetch.call_count == 20
        # Note: More sophisticated timing tests would require careful mocking of asyncio.sleep
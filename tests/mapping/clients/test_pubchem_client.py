"""Tests for the PubChem API client."""

import unittest
from unittest.mock import patch, MagicMock
import json

from biomapper.mapping.clients.pubchem_client import PubChemClient, PubChemError


class TestPubChemClient(unittest.TestCase):
    """Test case for the PubChem API client."""

    def setUp(self):
        """Set up test resources."""
        self.client = PubChemClient()
        
    @patch("biomapper.mapping.clients.pubchem_client.requests.Session")
    def test_get_entity_by_id_success(self, mock_session):
        """Test successful entity retrieval by ID."""
        # Mock the property response
        mock_property_response = MagicMock()
        mock_property_response.json.return_value = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 2244,
                        "MolecularFormula": "C8H10N4O2",
                        "MolecularWeight": 194.19,
                        "CanonicalSMILES": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
                        "InChI": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                        "InChIKey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                        "IUPACName": "1,3,7-trimethylpurine-2,6-dione"
                    }
                ]
            }
        }
        
        # Mock the xref response
        mock_xref_response = MagicMock()
        mock_xref_response.json.return_value = {
            "InformationList": {
                "Information": [
                    {
                        "CID": 2244,
                        "HMDB": ["HMDB0001847"],
                        "ChEBI": ["27732"],
                        "KEGG": ["C07481"]
                    }
                ]
            }
        }
        
        # Configure mock session to return our mock responses
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = [
            mock_property_response,
            mock_xref_response
        ]
        
        # Call the method to test
        result = self.client.get_entity_by_id("2244")
        
        # Verify the result
        self.assertEqual(result.pubchem_cid, "CID:2244")
        self.assertEqual(result.name, "1,3,7-trimethylpurine-2,6-dione")
        self.assertEqual(result.formula, "C8H10N4O2")
        self.assertEqual(result.mass, 194.19)
        self.assertEqual(result.smiles, "CN1C=NC2=C1C(=O)N(C)C(=O)N2C")
        self.assertEqual(result.inchi, "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3")
        self.assertEqual(result.inchikey, "RYYVLZVUVIJVGH-UHFFFAOYSA-N")
        self.assertEqual(result.xrefs["hmdb"], "HMDB0001847")
        self.assertEqual(result.xrefs["chebi"], "CHEBI:27732")
        self.assertEqual(result.xrefs["kegg"], "C07481")

    @patch("biomapper.mapping.clients.pubchem_client.requests.Session")
    def test_search_by_name_success(self, mock_session):
        """Test successful compound search by name."""
        # Mock the search response
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {
            "IdentifierList": {
                "CID": [2244, 66095]
            }
        }
        
        # Mock the property responses for each CID
        mock_property_response1 = MagicMock()
        mock_property_response1.json.return_value = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 2244,
                        "MolecularFormula": "C8H10N4O2",
                        "MolecularWeight": 194.19,
                        "CanonicalSMILES": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
                        "InChI": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                        "InChIKey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                        "IUPACName": "Caffeine"
                    }
                ]
            }
        }
        
        mock_property_response2 = MagicMock()
        mock_property_response2.json.return_value = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 66095,
                        "MolecularFormula": "C8H10N4O2",
                        "MolecularWeight": 194.19,
                        "CanonicalSMILES": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
                        "InChI": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                        "InChIKey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                        "IUPACName": "Caffeine Anhydrous"
                    }
                ]
            }
        }
        
        # Mock the xref responses
        mock_xref_response1 = MagicMock()
        mock_xref_response1.json.return_value = {
            "InformationList": {
                "Information": [
                    {
                        "CID": 2244,
                        "HMDB": ["HMDB0001847"],
                        "ChEBI": ["27732"],
                        "KEGG": ["C07481"]
                    }
                ]
            }
        }
        
        mock_xref_response2 = MagicMock()
        mock_xref_response2.json.return_value = {
            "InformationList": {
                "Information": [
                    {
                        "CID": 66095,
                        "HMDB": ["HMDB0001847"],
                        "ChEBI": ["27732"]
                    }
                ]
            }
        }
        
        # Configure mock session to return our mock responses
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = [
            mock_search_response,
            mock_property_response1,
            mock_xref_response1,
            mock_property_response2,
            mock_xref_response2
        ]
        
        # Call the method to test
        results = self.client.search_by_name("caffeine")
        
        # Verify the results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].pubchem_cid, "CID:2244")
        self.assertEqual(results[0].name, "Caffeine")
        self.assertEqual(results[1].pubchem_cid, "CID:66095")
        self.assertEqual(results[1].name, "Caffeine Anhydrous")

    @patch("biomapper.mapping.clients.pubchem_client.requests.Session")
    def test_get_entity_by_id_error(self, mock_session):
        """Test entity retrieval with error handling."""
        # Configure mock to raise an exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = Exception("API error")
        
        # Verify that the method raises PubChemError
        with self.assertRaises(PubChemError):
            self.client.get_entity_by_id("2244")

    @patch("biomapper.mapping.clients.pubchem_client.requests.Session")
    def test_search_by_name_no_results(self, mock_session):
        """Test search with no results."""
        # Mock a response with no results
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "IdentifierList": {
                "CID": []
            }
        }
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response
        
        # Call the method
        results = self.client.search_by_name("nonexistent compound")
        
        # Verify an empty list is returned
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()

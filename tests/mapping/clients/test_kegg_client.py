"""Tests for the KEGG API client."""

import unittest
from unittest.mock import patch, MagicMock

from biomapper.mapping.clients.kegg_client import KEGGClient, KEGGError


class TestKEGGClient(unittest.TestCase):
    """Test case for the KEGG API client."""

    def setUp(self):
        """Set up test resources."""
        self.client = KEGGClient()

    @patch("biomapper.mapping.clients.kegg_client.requests.Session")
    def test_get_entity_by_id_success(self, mock_session):
        """Test successful entity retrieval by ID."""
        # Mock the API response text for a glucose compound
        mock_response = MagicMock()
        mock_response.text = """ENTRY       C00031                      Compound
NAME        D-Glucose, Grape sugar, Dextrose
FORMULA     C6H12O6
EXACT_MASS  180.06339
MOL_WEIGHT  180.1559
PATHWAY     map00010  Glycolysis / Gluconeogenesis
            map00030  Pentose phosphate pathway
DBLINKS     CAS: 50-99-7
            PubChem: 5793
            ChEBI: 15903
            HMDB: HMDB0000122
///"""
        
        # Configure mock session to return our mock response
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response
        
        # Call the method to test
        result = self.client.get_entity_by_id("C00031")
        
        # Verify the result
        self.assertEqual(result.kegg_id, "cpd:C00031")
        self.assertEqual(result.name, "D-Glucose, Grape sugar, Dextrose")
        self.assertEqual(result.formula, "C6H12O6")
        self.assertEqual(result.exact_mass, 180.06339)
        self.assertEqual(result.mol_weight, 180.1559)
        self.assertEqual(result.other_dbs["chebi"], "CHEBI:15903")
        self.assertEqual(result.other_dbs["pubchem"], "CID:5793")
        self.assertEqual(result.other_dbs["hmdb"], "HMDB0000122")
        self.assertIn("map00010", result.pathway_ids)
        self.assertIn("map00030", result.pathway_ids)

    @patch("biomapper.mapping.clients.kegg_client.requests.Session")
    def test_search_by_name_success(self, mock_session):
        """Test successful compound search by name."""
        # Mock the search response
        mock_search_response = MagicMock()
        mock_search_response.text = """cpd:C00031  D-Glucose; Grape sugar; Dextrose; Glucose
cpd:C00267  alpha-D-Glucose; Glucopyranose; alpha-Glucopyranose
cpd:C00221  beta-D-Glucose; beta-Glucopyranose"""
        
        # Mock the entity response for the first result
        mock_entity_response = MagicMock()
        mock_entity_response.text = """ENTRY       C00031                      Compound
NAME        D-Glucose, Grape sugar, Dextrose
FORMULA     C6H12O6
EXACT_MASS  180.06339
MOL_WEIGHT  180.1559
DBLINKS     CAS: 50-99-7
            PubChem: 5793
            ChEBI: 15903
            HMDB: HMDB0000122
///"""
        
        # Configure mock session to return our mock responses
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = [
            mock_search_response,
            mock_entity_response
        ]
        
        # Call the method to test with max_results=1
        results = self.client.search_by_name("glucose", max_results=1)
        
        # Verify the results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].kegg_id, "cpd:C00031")
        self.assertEqual(results[0].name, "D-Glucose, Grape sugar, Dextrose")

    @patch("biomapper.mapping.clients.kegg_client.requests.Session")
    def test_get_entity_by_id_error(self, mock_session):
        """Test entity retrieval with error handling."""
        # Configure mock to raise an exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = Exception("API error")
        
        # Verify that the method raises KEGGError
        with self.assertRaises(KEGGError):
            self.client.get_entity_by_id("C00031")

    @patch("biomapper.mapping.clients.kegg_client.requests.Session")
    def test_search_by_name_no_results(self, mock_session):
        """Test search with no results."""
        # Mock a response with no results
        mock_response = MagicMock()
        mock_response.text = ""
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response
        
        # Call the method
        results = self.client.search_by_name("nonexistent compound")
        
        # Verify an empty list is returned
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for the ArivaleReverseLookupClient."""

import os
import asyncio
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from biomapper.core.exceptions import ClientInitializationError, ClientExecutionError
from biomapper.mapping.clients.arivale_reverse_lookup_client import ArivaleReverseLookupClient


class TestArivaleReverseLookupClient:
    """Tests for ArivaleReverseLookupClient."""

    @pytest.fixture
    def mock_csv_file(self, tmp_path):
        """Creates a mock CSV file with test data."""
        csv_content = """# This is a comment
uniprot	name	gene_name	gene_id
P12345	SAMP_P12345	GENE1	ENSG001
P67890	SAMP_P67890	GENE2	ENSG002
P11223	SAMP_P11223	GENE3	ENSG003
P11223,P44556	SAMP_COMP1	GENE4	ENSG004
P99887,P55443	SAMP_COMP2	GENE5	ENSG005
"""
        csv_path = tmp_path / "mock_arivale_data.tsv"
        csv_path.write_text(csv_content)
        return str(csv_path)

    @pytest.fixture
    def client_with_mock_data(self, mock_csv_file):
        """Creates an ArivaleReverseLookupClient with mock data."""
        config = {
            "file_path": mock_csv_file,
            "key_column": "uniprot",
            "value_column": "name",
        }
        return ArivaleReverseLookupClient(config=config)

    @pytest.mark.asyncio
    async def test_initialize_client(self, mock_csv_file):
        """Test that the client initializes correctly with a valid config."""
        config = {
            "file_path": mock_csv_file,
            "key_column": "uniprot",
            "value_column": "name",
        }

        client = ArivaleReverseLookupClient(config=config)
        
        # Verify that the forward client is initialized
        assert client._forward_client is not None
        assert client._initialized is True

    @pytest.mark.asyncio
    async def test_map_identifiers(self, client_with_mock_data):
        """Test mapping Arivale IDs to UniProt IDs (reverse mapping)."""
        # This is the primary purpose of the reverse client
        identifiers = ["SAMP_P12345", "SAMP_P67890", "SAMP_COMP1", "NONEXISTENT"]
        results = await client_with_mock_data.map_identifiers(identifiers)
        
        # Verify all identifiers were processed
        assert len(results) == len(identifiers)
        
        # Verify successful mappings
        assert results["SAMP_P12345"][0] is not None
        assert "P12345" in results["SAMP_P12345"][0]
        
        assert results["SAMP_P67890"][0] is not None
        assert "P67890" in results["SAMP_P67890"][0]
        
        assert results["SAMP_COMP1"][0] is not None
        assert "P11223,P44556" in results["SAMP_COMP1"][0]
        
        # Verify unsuccessful mapping
        assert results["NONEXISTENT"][0] is None
        assert results["NONEXISTENT"][1] is None

    @pytest.mark.asyncio
    async def test_reverse_map_identifiers(self, client_with_mock_data):
        """Test mapping UniProt IDs to Arivale IDs (forward mapping)."""
        # This is the reverse of the primary purpose
        identifiers = ["P12345", "P67890", "P11223,P44556", "NONEXISTENT"]
        results = await client_with_mock_data.reverse_map_identifiers(identifiers)
        
        # Verify all identifiers were processed
        assert len(results) == len(identifiers)
        
        # Verify successful mappings
        assert results["P12345"][0] is not None
        assert "SAMP_P12345" in results["P12345"][0]
        
        assert results["P67890"][0] is not None
        assert "SAMP_P67890" in results["P67890"][0]
        
        assert results["P11223,P44556"][0] is not None
        assert "SAMP_COMP1" in results["P11223,P44556"][0]
        
        # Verify unsuccessful mapping
        assert results["NONEXISTENT"][0] is None
        assert results["NONEXISTENT"][1] is None
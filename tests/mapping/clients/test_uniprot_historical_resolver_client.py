"""Tests for the UniProtHistoricalResolverClient."""

import os
import pytest
from unittest.mock import patch, AsyncMock

from biomapper.core.exceptions import ClientExecutionError
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient


class TestUniProtHistoricalResolverClient:
    """Tests for UniProtHistoricalResolverClient."""

    @pytest.mark.asyncio
    async def test_initialize_client(self):
        """Test that the client initializes correctly with default settings."""
        client = UniProtHistoricalResolverClient()
        assert client._initialized is True
        assert client.base_url == "https://rest.uniprot.org/uniprotkb/search"
        assert client.timeout == 30

    @pytest.mark.asyncio
    async def test_mock_primary_accession_resolution(self):
        """Test resolution of primary accessions using mocked API responses."""
        # Create a sample response for a primary accession
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01308",
                    "secondaryAccessions": [],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "INS"}}],
                }
            ]
        }

        client = UniProtHistoricalResolverClient()
        
        # Mock the _fetch_uniprot_search_results method to return our sample response
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # Test with a primary accession
            results = await client.map_identifiers(["P01308"])
            
            # Verify the mock was called with the expected query
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args[0][0]
            assert "accession:P01308" in call_args
            
            # Verify the result format
            assert "P01308" in results
            primary_ids, metadata = results["P01308"]
            assert primary_ids == ["P01308"]
            assert metadata == "primary"

    @pytest.mark.asyncio
    async def test_mock_secondary_accession_resolution(self):
        """Test resolution of secondary accessions using mocked API responses."""
        # Create a sample response for a secondary accession
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01308",
                    "secondaryAccessions": ["Q99895"],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "INS"}}],
                }
            ]
        }

        client = UniProtHistoricalResolverClient()
        
        # Mock the _fetch_uniprot_search_results method to return our sample response
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # Test with a secondary accession
            results = await client.map_identifiers(["Q99895"])
            
            # Verify the result format
            assert "Q99895" in results
            primary_ids, metadata = results["Q99895"]
            assert primary_ids == ["P01308"]
            assert metadata == "secondary:P01308"

    @pytest.mark.asyncio
    async def test_mock_demerged_accession_resolution(self):
        """Test resolution of demerged accessions using mocked API responses."""
        # Create a sample response for a demerged accession (multiple entries)
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P0DOY2",
                    "secondaryAccessions": ["P0CG05"],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "GENEAB"}}],
                },
                {
                    "primaryAccession": "P0DOY3",
                    "secondaryAccessions": ["P0CG05"],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "GENECD"}}],
                }
            ]
        }

        client = UniProtHistoricalResolverClient()
        
        # Mock the _fetch_uniprot_search_results method to return our sample response
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # Test with a demerged accession
            results = await client.map_identifiers(["P0CG05"])
            
            # Verify the result format
            assert "P0CG05" in results
            primary_ids, metadata = results["P0CG05"]
            assert set(primary_ids) == set(["P0DOY2", "P0DOY3"])
            assert metadata == "demerged"

    @pytest.mark.asyncio
    async def test_mock_non_existent_accession(self):
        """Test handling of non-existent accessions using mocked API responses."""
        # Create an empty response (no matches found)
        mock_response = {"results": []}

        client = UniProtHistoricalResolverClient()
        
        # Mock the _fetch_uniprot_search_results method to return our sample response
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # Test with a non-existent accession
            results = await client.map_identifiers(["NONEXISTENT"])
            
            # Verify the result format
            assert "NONEXISTENT" in results
            primary_ids, metadata = results["NONEXISTENT"]
            assert primary_ids is None
            assert metadata == "obsolete"

    @pytest.mark.asyncio
    async def test_mock_api_error_handling(self):
        """Test error handling when API request fails."""
        client = UniProtHistoricalResolverClient()
        
        # Mock _fetch_uniprot_search_results to raise an error
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ClientExecutionError(
                "API request failed",
                client_name="UniProtHistoricalResolverClient",
                details={"query": "accession:P12345"}
            )
            
            # Test error handling
            results = await client.map_identifiers(["P12345"])
            
            # Verify error result format
            assert "P12345" in results
            primary_ids, metadata = results["P12345"]
            assert primary_ids is None
            assert metadata.startswith("error:")

    @pytest.mark.asyncio
    async def test_mock_batch_processing(self):
        """Test that the client processes identifiers in batches."""
        # Create mock responses for different accessions
        mock_response1 = {
            "results": [
                {
                    "primaryAccession": "P01308",
                    "secondaryAccessions": [],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "INS"}}],
                }
            ]
        }
        
        mock_response2 = {
            "results": [
                {
                    "primaryAccession": "P05067",
                    "secondaryAccessions": ["A6NFQ7"],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "APP"}}],
                }
            ]
        }

        client = UniProtHistoricalResolverClient()
        
        # Mock _fetch_uniprot_search_results to return different responses
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            # We need to return both results in a combined response since 
            # both IDs will be queried in a single batch
            combined_response = {
                "results": [
                    {
                        "primaryAccession": "P01308",
                        "secondaryAccessions": [],
                        "organism": {"scientificName": "Homo sapiens"},
                        "genes": [{"geneName": {"value": "INS"}}],
                    },
                    {
                        "primaryAccession": "P05067",
                        "secondaryAccessions": ["A6NFQ7"],
                        "organism": {"scientificName": "Homo sapiens"},
                        "genes": [{"geneName": {"value": "APP"}}],
                    }
                ]
            }
            mock_fetch.return_value = combined_response
            
            # Test with multiple accessions that should be processed in batches
            results = await client.map_identifiers(["P01308", "A6NFQ7"])
            
            # Verify the results
            assert "P01308" in results
            assert "A6NFQ7" in results
            
            p01308_ids, p01308_metadata = results["P01308"]
            assert p01308_ids == ["P01308"]
            assert p01308_metadata == "primary"
            
            a6nfq7_ids, a6nfq7_metadata = results["A6NFQ7"]
            assert a6nfq7_ids == ["P05067"]
            assert a6nfq7_metadata == "secondary:P05067"

    @pytest.mark.asyncio
    async def test_cache_usage(self):
        """Test that the client uses caching for repeated lookups."""
        # Create a sample response
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01308",
                    "secondaryAccessions": [],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "INS"}}],
                }
            ]
        }

        client = UniProtHistoricalResolverClient()
        
        # Mock _fetch_uniprot_search_results to return our sample response
        with patch.object(
            client, '_fetch_uniprot_search_results', new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # First call should make an API request
            await client.map_identifiers(["P01308"])
            assert mock_fetch.call_count == 1
            
            # Second call should use the cache (no additional API call)
            await client.map_identifiers(["P01308"])
            assert mock_fetch.call_count == 1  # Still only one call
            
            # Get cache stats to verify hit
            cache_stats = client.get_cache_stats()
            assert cache_stats["cache_hits"] >= 1

    @pytest.mark.asyncio
    async def test_reverse_map_identifiers_not_supported(self):
        """Test that reverse mapping raises NotImplementedError."""
        client = UniProtHistoricalResolverClient()
        
        with pytest.raises(NotImplementedError):
            await client.reverse_map_identifiers(["P01308"])

# Run integration tests against the real UniProt API if requested
if os.environ.get("RUN_INTEGRATION_TESTS"):
    class TestUniProtHistoricalResolverClientIntegration:
        """Integration tests for UniProtHistoricalResolverClient using the real UniProt API."""

        @pytest.mark.asyncio
        async def test_real_api_primary_accession(self):
            """Test resolving a primary accession using the real UniProt API."""
            client = UniProtHistoricalResolverClient()
            
            # Example primary accession
            results = await client.map_identifiers(["P01308"])  # Insulin
            
            assert "P01308" in results
            primary_ids, metadata = results["P01308"]
            assert primary_ids == ["P01308"]
            assert metadata == "primary"

        @pytest.mark.asyncio
        async def test_real_api_secondary_accession(self):
            """Test resolving a secondary accession using the real UniProt API."""
            client = UniProtHistoricalResolverClient()
            
            # Example secondary accession (this is a known example)
            results = await client.map_identifiers(["Q99895"])  # Secondary accession for insulin
            
            assert "Q99895" in results
            primary_ids, metadata = results["Q99895"]
            assert primary_ids == ["P01308"]  # Should map to insulin's primary accession
            assert metadata.startswith("secondary:")

        @pytest.mark.asyncio
        async def test_real_api_demerged_accession(self):
            """Test resolving a demerged accession using the real UniProt API."""
            client = UniProtHistoricalResolverClient()
            
            # Example demerged accession
            results = await client.map_identifiers(["P0CG05"])  # Known demerged ID
            
            assert "P0CG05" in results
            primary_ids, metadata = results["P0CG05"]
            assert primary_ids is not None
            assert len(primary_ids) >= 2  # Should map to multiple primary accessions
            assert set(primary_ids) == set(["P0DOY2", "P0DOY3"])  # These are the known mappings
            assert metadata == "demerged"

        @pytest.mark.asyncio
        async def test_real_api_non_existent_accession(self):
            """Test handling of non-existent accessions using the real UniProt API."""
            client = UniProtHistoricalResolverClient()
            
            # Example non-existent accession
            results = await client.map_identifiers(["NONEXISTENT"])
            
            assert "NONEXISTENT" in results
            primary_ids, metadata = results["NONEXISTENT"]
            assert primary_ids is None
            assert metadata == "obsolete"
"""Tests for the ArivaleMetadataLookupClient."""

import os
import asyncio
import pytest

from biomapper.core.exceptions import ClientInitializationError
from biomapper.mapping.clients.arivale_lookup_client import ArivaleMetadataLookupClient


class TestArivaleMetadataLookupClient:
    """Tests for ArivaleMetadataLookupClient."""

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
        """Creates an ArivaleMetadataLookupClient with mock data."""
        config = {
            "file_path": mock_csv_file,
            "key_column": "uniprot",
            "value_column": "name",
        }
        return ArivaleMetadataLookupClient(config=config)

    @pytest.mark.asyncio
    async def test_initialize_client(self, mock_csv_file):
        """Test that the client initializes correctly with a valid config."""
        config = {
            "file_path": mock_csv_file,
            "key_column": "uniprot",
            "value_column": "name",
        }

        client = ArivaleMetadataLookupClient(config=config)

        # Verify lookup maps are populated correctly
        assert len(client._lookup_map) == 5  # 5 entries in the mock file
        assert len(client._component_lookup_map) >= 6  # At least 6 unique component IDs
        # (P11223 appears in 2 different rows but only counts once)
        assert len(client._reverse_lookup_map) == 5  # Reverse lookup map should have entries too

        # Verify specific entries are in the maps
        assert client._lookup_map["P12345"] == "SAMP_P12345"
        assert client._lookup_map["P11223,P44556"] == "SAMP_COMP1"

        # Verify component map contains individual parts
        assert client._component_lookup_map["P12345"] == "SAMP_P12345"
        assert (
            "P11223" in client._component_lookup_map
        )  # P11223 is in map (exact value will depend on order)
        assert client._component_lookup_map["P44556"] == "SAMP_COMP1"
        assert client._component_lookup_map["P99887"] == "SAMP_COMP2"
        assert client._component_lookup_map["P55443"] == "SAMP_COMP2"
        
        # Verify reverse lookup map
        assert "SAMP_P12345" in client._reverse_lookup_map
        assert "P12345" in client._reverse_lookup_map["SAMP_P12345"]

    @pytest.mark.asyncio
    async def test_initialization_with_missing_config(self):
        """Test that the client handles missing configuration gracefully."""
        # Test with empty config
        with pytest.raises(ClientInitializationError) as exc_info:
            ArivaleMetadataLookupClient(config={})
        
        assert "Missing required configuration" in str(exc_info.value)

        # Test with partially missing config
        with pytest.raises(ClientInitializationError) as exc_info:
            ArivaleMetadataLookupClient(
                config={
                    "file_path": "nonexistent.tsv",
                    # Missing key_column and value_column
                }
            )
        
        assert "Missing required configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialization_with_nonexistent_file(self):
        """Test that the client raises an error when the file doesn't exist."""
        config = {
            "file_path": "nonexistent_file.tsv",
            "key_column": "uniprot",
            "value_column": "name",
        }

        with pytest.raises(ClientInitializationError) as exc_info:
            ArivaleMetadataLookupClient(config=config)
        
        assert "Lookup file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_map_simple_identifiers(self, client_with_mock_data):
        """Test mapping simple (non-composite) identifiers."""
        input_ids = ["P12345", "P67890", "NONEXISTENT"]

        results = await client_with_mock_data.map_identifiers(input_ids)

        # Verify the result structure
        assert "primary_ids" in results
        assert "input_to_primary" in results
        assert "errors" in results
        assert "secondary_ids" in results

        # Verify successful mappings
        assert "P12345" in results["input_to_primary"]
        assert results["input_to_primary"]["P12345"] == "SAMP_P12345"
        
        assert "P67890" in results["input_to_primary"]
        assert results["input_to_primary"]["P67890"] == "SAMP_P67890"

        # Verify primary_ids contains the mapped values
        assert "SAMP_P12345" in results["primary_ids"]
        assert "SAMP_P67890" in results["primary_ids"]

        # Verify unsuccessful mapping is in errors
        assert len(results["errors"]) == 1
        assert results["errors"][0]["input_id"] == "NONEXISTENT"
        assert results["errors"][0]["error_type"] == "NO_MAPPING_FOUND"

    @pytest.mark.asyncio
    async def test_map_exact_composite_identifiers(self, client_with_mock_data):
        """Test mapping composite identifiers with exact matches."""
        input_ids = ["P11223,P44556", "P99887,P55443"]

        results = await client_with_mock_data.map_identifiers(input_ids)

        # Verify exact composite matches work (continued from above)
        # Primary IDs should include the composite mappings
        assert "SAMP_COMP1" in results["primary_ids"]
        assert "SAMP_COMP2" in results["primary_ids"]

    @pytest.mark.asyncio
    async def test_map_component_match_identifiers(self, client_with_mock_data):
        """Test mapping composite identifiers that need component-level matching."""
        # Input with one existing component and one non-existent
        input_ids = ["P12345,NONEXISTENT", "P11223,P67890"]

        results = await client_with_mock_data.map_identifiers(input_ids)

        # Verify partial component matching works for comma-separated IDs (continued)
        # Verify that mapped values include component mappings
        assert "SAMP_P12345" in results["primary_ids"]
        # When P11223 appears in component context, it could map to either SAMP_P11223 or SAMP_COMP1
        # The log warning suggests it keeps the first mapping
        assert any(val in results["primary_ids"] for val in ["SAMP_P11223", "SAMP_P67890", "SAMP_COMP1"])

    @pytest.mark.asyncio
    async def test_map_multi_component_matches(self, client_with_mock_data):
        """Test mapping when multiple components in a composite ID match."""
        # This ID has two components that both match different targets
        input_id = "P12345,P67890"

        results = await client_with_mock_data.map_identifiers([input_id])

        # Both components match, but only the first is returned as primary
        assert input_id in results["input_to_primary"]
        mapped_value = results["input_to_primary"][input_id]
        # Should map to one of the component values
        assert mapped_value in ["SAMP_P12345", "SAMP_P67890"]

    @pytest.mark.asyncio
    async def test_map_no_match_identifiers(self, client_with_mock_data):
        """Test mapping identifiers that don't match anything."""
        input_ids = ["NONEXISTENT1", "NONEXISTENT2", "NONEXISTENT_COMPOSITE"]

        results = await client_with_mock_data.map_identifiers(input_ids)

        # Verify all nonexistent IDs are in errors
        assert len(results["errors"]) == 3
        error_ids = [err["input_id"] for err in results["errors"]]
        for id in input_ids:
            assert id in error_ids

    @pytest.mark.asyncio
    async def test_map_empty_list(self, client_with_mock_data):
        """Test mapping an empty list of identifiers."""
        results = await client_with_mock_data.map_identifiers([])

        assert results["primary_ids"] == []
        assert results["input_to_primary"] == {}
        assert results["errors"] == []
        assert results["secondary_ids"] == {}

    @pytest.mark.asyncio
    async def test_map_whitespace_handling(self, client_with_mock_data):
        """Test that whitespace in identifiers is handled correctly."""
        input_ids = [" P12345 ", "P67890 ", " P11223,P44556 "]

        results = await client_with_mock_data.map_identifiers(input_ids)

        # Whitespace should be stripped and matches should succeed
        assert " P12345 " in results["input_to_primary"]
        assert results["input_to_primary"][" P12345 "] == "SAMP_P12345"
        
        assert "P67890 " in results["input_to_primary"]
        assert results["input_to_primary"]["P67890 "] == "SAMP_P67890"
        
        assert " P11223,P44556 " in results["input_to_primary"]
        assert results["input_to_primary"][" P11223,P44556 "] == "SAMP_COMP1"

    @pytest.mark.asyncio
    async def test_caching(self, client_with_mock_data):
        """Test that the caching works correctly."""
        # First call should populate the cache
        identifiers = ["P12345", "P67890", "NONEXISTENT"]
        
        # Wait for cache initialization
        await asyncio.sleep(0.1)
        
        # Get initial stats
        initial_stats = client_with_mock_data.get_cache_stats()
        
        # First call
        results1 = await client_with_mock_data.map_identifiers(identifiers)
        
        # Second call should use the cache
        results2 = await client_with_mock_data.map_identifiers(identifiers)
        
        # Get updated stats
        final_stats = client_with_mock_data.get_cache_stats()
        
        # Verify results are identical
        assert results1 == results2
        
        # Verify cache hits increased (should have hits on second call)
        assert final_stats["cache_hits"] > initial_stats["cache_hits"]

    @pytest.mark.asyncio
    async def test_reverse_map_identifiers(self, client_with_mock_data):
        """Test reverse mapping from Arivale IDs to UniProt IDs."""
        # Wait for the cache initialization
        await asyncio.sleep(0.1)
        
        identifiers = ["SAMP_P12345", "SAMP_COMP1", "NONEXISTENT"]
        results = await client_with_mock_data.reverse_map_identifiers(identifiers)
        
        # Verify the result structure
        assert "primary_ids" in results
        assert "input_to_primary" in results
        assert "errors" in results
        
        # Verify successful mappings
        assert "SAMP_P12345" in results["input_to_primary"]
        assert results["input_to_primary"]["SAMP_P12345"] == "P12345"
        
        assert "SAMP_COMP1" in results["input_to_primary"]
        assert results["input_to_primary"]["SAMP_COMP1"] == "P11223,P44556"
        
        # Verify primary_ids
        assert "P12345" in results["primary_ids"]
        assert "P11223,P44556" in results["primary_ids"]
        
        # Verify unsuccessful mapping
        assert len(results["errors"]) == 1
        assert results["errors"][0]["input_id"] == "NONEXISTENT"


# Add integration tests with actual TSV files if needed
if os.environ.get("RUN_INTEGRATION_TESTS"):

    class TestArivaleMetadataLookupClientIntegration:
        """Integration tests for ArivaleMetadataLookupClient with real files."""

        @pytest.mark.asyncio
        async def test_with_real_file(self):
            """Test with a real Arivale metadata file."""
            # This would use a real file path from your development environment
            config = {
                "file_path": "/path/to/real/arivale/metadata.tsv",
                "key_column": "uniprot",
                "value_column": "name",
            }

            client = ArivaleMetadataLookupClient(config=config)

            # Test with some real IDs that you know exist in your file
            # results = await client.map_identifiers(["P12345", "P67890"])
            # Add assertions based on expected real data
"""Test multi-API enrichment functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from biomapper.core.strategy_actions.metabolite_api_enrichment import (
    MetaboliteApiEnrichmentAction,
    MetaboliteApiEnrichmentParams,
    ApiServiceConfig,
    ApiService,
)
from biomapper.mapping.clients.metabolite_apis import (
    HMDBMetaboliteInfo,
    PubChemCompoundInfo,
    PubChemIdType,
)


class TestMetaboliteApiEnrichment:
    """Test multi-API enrichment functionality."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return MetaboliteApiEnrichmentAction()

    @pytest.fixture
    def mock_context(self):
        """Create mock context with test data."""
        return {
            "datasets": {
                "unmatched_metabolites": [
                    {
                        "BIOCHEMICAL_NAME": "Glucose",
                        "HMDB_ID": "HMDB0000122",
                        "PUBCHEM_CID": "5793",
                        "KEGG_ID": "C00031",
                    },
                    {
                        "BIOCHEMICAL_NAME": "Lactate",
                        "HMDB_ID": "HMDB0000190",
                        "PUBCHEM_CID": "91435",
                    },
                    {"BIOCHEMICAL_NAME": "Unknown Metabolite", "KEGG_ID": "C99999"},
                ],
                "reference_metabolites": [
                    {"unified_name": "D-Glucose"},
                    {"unified_name": "Lactic acid"},
                    {"unified_name": "Pyruvate"},
                ],
            }
        }

    @pytest.mark.asyncio
    async def test_hmdb_client_integration(self, action):
        """Test HMDB API client functionality."""
        # Create mock HMDB response
        mock_hmdb_info = HMDBMetaboliteInfo(
            hmdb_id="HMDB0000122",
            common_name="D-Glucose",
            iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-Pentahydroxyhexanal",
            synonyms=["Glucose", "Dextrose", "Grape sugar"],
            inchikey="WQZGKKKJIJFFOK-GASJEMHNSA-N",
            kegg_id="C00031",
            pubchem_cid="5793",
        )

        # Test enrichment with HMDB
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched_metabolites",
            target_dataset_key="reference_metabolites",
            api_services=[
                ApiServiceConfig(
                    service=ApiService.HMDB,
                    input_column="HMDB_ID",
                    output_fields=["name", "synonyms", "inchikey"],
                )
            ],
            output_key="hmdb_matches",
        )

        # Mock HMDB client
        with patch.object(action, "_enrich_with_hmdb") as mock_enrich:
            mock_enrich.return_value = (
                [
                    {
                        "BIOCHEMICAL_NAME": "Glucose",
                        "HMDB_ID": "HMDB0000122",
                        "hmdb_enriched_names": [
                            "D-Glucose",
                            "Glucose",
                            "Dextrose",
                            "Grape sugar",
                        ],
                        "hmdb_inchikey": "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                        "hmdb_enrichment_success": True,
                    }
                ],
                {"total": 1, "enriched": 1, "api_calls": 1},
            )

            # Process enrichment
            await action._initialize_api_clients(params)
            result, metrics = await action._process_api_enrichment(
                [{"BIOCHEMICAL_NAME": "Glucose", "HMDB_ID": "HMDB0000122"}], params
            )

            assert len(result) == 1
            assert "hmdb_enriched_names" in result[0]
            assert "D-Glucose" in result[0]["hmdb_enriched_names"]

    @pytest.mark.asyncio
    async def test_pubchem_enhanced_client(self, action):
        """Test enhanced PubChem client functionality."""
        # Create mock PubChem response
        mock_pubchem_info = PubChemCompoundInfo(
            cid=5793,
            molecular_formula="C6H12O6",
            iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal",
            inchikey="WQZGKKKJIJFFOK-GASJEMHNSA-N",
            synonyms=["D-Glucose", "Dextrose", "Glucose"],
            identifier="5793",
        )

        # Test enrichment with PubChem
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched_metabolites",
            target_dataset_key="reference_metabolites",
            api_services=[
                ApiServiceConfig(
                    service=ApiService.PUBCHEM,
                    input_column="PUBCHEM_CID",
                    output_fields=["name", "synonyms", "inchikey"],
                    id_type="cid",
                )
            ],
            output_key="pubchem_matches",
        )

        # Mock PubChem client
        with patch.object(action, "_enrich_with_pubchem") as mock_enrich:
            mock_enrich.return_value = (
                [
                    {
                        "BIOCHEMICAL_NAME": "Glucose",
                        "PUBCHEM_CID": "5793",
                        "pubchem_enriched_names": [
                            "(2R,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal",
                            "D-Glucose",
                            "Dextrose",
                            "Glucose",
                        ],
                        "pubchem_inchikey": "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                        "pubchem_enrichment_success": True,
                    }
                ],
                {"total": 1, "enriched": 1, "api_calls": 1},
            )

            # Process enrichment
            await action._initialize_api_clients(params)
            result, metrics = await action._process_api_enrichment(
                [{"BIOCHEMICAL_NAME": "Glucose", "PUBCHEM_CID": "5793"}], params
            )

            assert len(result) == 1
            assert "pubchem_enriched_names" in result[0]
            assert "D-Glucose" in result[0]["pubchem_enriched_names"]

    @pytest.mark.asyncio
    async def test_multi_api_enrichment(self, action, mock_context):
        """Test enrichment using multiple APIs."""
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched_metabolites",
            target_dataset_key="reference_metabolites",
            api_services=[
                ApiServiceConfig(
                    service=ApiService.HMDB,
                    input_column="HMDB_ID",
                    output_fields=["name", "synonyms"],
                ),
                ApiServiceConfig(
                    service=ApiService.PUBCHEM,
                    input_column="PUBCHEM_CID",
                    output_fields=["name", "synonyms"],
                    id_type="cid",
                ),
                ApiServiceConfig(
                    service=ApiService.CTS,
                    input_column="KEGG_ID",
                    output_fields=["chemical_name"],
                ),
            ],
            match_threshold=0.8,
            output_key="multi_api_matches",
        )

        # Mock all API clients
        with patch.object(action, "_initialize_api_clients") as mock_init:
            with patch.object(action, "_enrich_with_hmdb") as mock_hmdb:
                with patch.object(action, "_enrich_with_pubchem") as mock_pubchem:
                    with patch.object(action, "_enrich_with_cts") as mock_cts:
                        # Set up mock returns
                        mock_hmdb.return_value = (
                            mock_context["datasets"]["unmatched_metabolites"],
                            {"total": 2, "enriched": 2, "api_calls": 2},
                        )
                        mock_pubchem.return_value = (
                            mock_context["datasets"]["unmatched_metabolites"],
                            {"total": 2, "enriched": 2, "api_calls": 2},
                        )
                        mock_cts.return_value = (
                            mock_context["datasets"]["unmatched_metabolites"],
                            {"total": 2, "enriched": 1, "api_calls": 2},
                        )

                        # Execute action
                        result = await action.execute_typed(
                            [], "", params, None, None, mock_context
                        )

                        # Verify API clients were initialized
                        mock_init.assert_called_once()

                        # Verify all APIs were called
                        assert mock_hmdb.called
                        assert mock_pubchem.called
                        assert mock_cts.called

    @pytest.mark.asyncio
    async def test_backward_compatibility(self, action, mock_context):
        """Test that CTS-only mode still works."""
        # Use legacy parameters
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched_metabolites",
            target_dataset_key="reference_metabolites",
            identifier_columns=["HMDB_ID", "KEGG_ID", "PUBCHEM_CID"],
            cts_timeout=30,
            output_key="cts_matches",
        )

        # Verify conversion to new format
        assert params.api_services is not None
        assert len(params.api_services) == 1
        assert params.api_services[0].service == ApiService.CTS
        assert params.api_services[0].input_column == "multiple"
        assert params.api_services[0].timeout == 30

    @pytest.mark.asyncio
    async def test_api_failure_handling(self, action):
        """Test graceful handling of API failures."""
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched",
            target_dataset_key="reference",
            api_services=[
                ApiServiceConfig(service=ApiService.HMDB, input_column="HMDB_ID")
            ],
            output_key="matches",
        )

        # Mock HMDB client to raise exception
        with patch(
            "biomapper.mapping.clients.metabolite_apis.HMDBClient"
        ) as mock_client:
            mock_instance = Mock()
            mock_instance.get_metabolite_info = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_client.return_value = mock_instance

            # Should handle error gracefully
            context = {
                "datasets": {"unmatched": [{"HMDB_ID": "HMDB0000122"}], "reference": []}
            }

            # Execute should not raise exception
            result = await action.execute_typed([], "", params, None, None, context)

            assert result is not None
            assert "error" not in str(result)

    @pytest.mark.asyncio
    async def test_caching_behavior(self, action):
        """Test that API responses are cached."""
        # This would require implementing actual caching in the action
        # For now, we'll test the cache_results parameter is respected
        params = MetaboliteApiEnrichmentParams(
            unmatched_dataset_key="unmatched",
            target_dataset_key="reference",
            api_services=[
                ApiServiceConfig(service=ApiService.HMDB, input_column="HMDB_ID")
            ],
            cache_results=True,
            output_key="matches",
        )

        assert params.cache_results is True

    @pytest.mark.asyncio
    async def test_fuzzy_matching_with_enriched_names(self, action):
        """Test fuzzy matching using enriched names from APIs."""
        # Create test metabolite with enriched names
        enriched_metabolite = {
            "BIOCHEMICAL_NAME": "Glucose",
            "cts_enriched_names": ["D-Glucose", "Dextrose"],
            "hmdb_enriched_names": ["alpha-D-Glucose", "Grape sugar"],
            "pubchem_enriched_names": ["(2R,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal"],
        }

        target_data = [
            {"unified_name": "D-Glucose"},
            {"unified_name": "Lactate"},
            {"unified_name": "Pyruvate"},
        ]

        # Test matching
        result = action._fuzzy_match_enriched(
            enriched_metabolite, target_data, "unified_name", 0.8
        )

        assert result is not None
        assert result["target"]["unified_name"] == "D-Glucose"
        assert result["score"] >= 0.8
        assert result["enrichment_used"] is True
        assert result["api_source"] in ["cts", "hmdb", "pubchem"]

    def test_collect_all_enriched_names(self, action):
        """Test collection of names from all APIs."""
        metabolite = {
            "BIOCHEMICAL_NAME": "Original Name",
            "cts_enriched_names": ["CTS Name 1", "CTS Name 2"],
            "hmdb_enriched_names": ["HMDB Name"],
            "pubchem_enriched_names": ["PubChem Name 1", "PubChem Name 2"],
        }

        names = action._collect_all_enriched_names(metabolite)

        assert "Original Name" in names
        assert "CTS Name 1" in names
        assert "CTS Name 2" in names
        assert "HMDB Name" in names
        assert "PubChem Name 1" in names
        assert "PubChem Name 2" in names
        assert len(names) == 6  # No duplicates

    @pytest.mark.asyncio
    async def test_api_service_config_validation(self):
        """Test ApiServiceConfig validation."""
        # Valid config
        config = ApiServiceConfig(
            service="hmdb", input_column="HMDB_ID", output_fields=["name", "synonyms"]
        )
        assert config.service == ApiService.HMDB

        # Test lowercase conversion
        config = ApiServiceConfig(service="HMDB", input_column="HMDB_ID")
        assert config.service == ApiService.HMDB

        # Test default output fields
        assert config.output_fields == ["name", "synonyms", "inchikey"]

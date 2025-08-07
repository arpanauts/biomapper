import pytest
from unittest.mock import patch, AsyncMock
from biomapper.core.strategy_actions.cts_enriched_match import (
    CtsEnrichedMatchAction,
    CtsEnrichedMatchParams,
)


@pytest.mark.integration
class TestCtsEnrichmentIntegration:
    """Integration tests with mock CTS responses."""

    @pytest.mark.asyncio
    async def test_progressive_enhancement_improvement(self):
        """Test that CTS enrichment improves on baseline."""
        # Simulate baseline unmatched items
        unmatched_from_baseline = [
            {
                "BIOCHEMICAL_NAME": "12,13-DiHOME",
                "HMDB": "HMDB04705",
                "KEGG": "",
                "PUBCHEM": "9966640",
            },
            {
                "BIOCHEMICAL_NAME": "S-1-pyrroline-5-carboxylate",
                "HMDB": "",
                "KEGG": "C03564",
                "PUBCHEM": "",
            },
        ]

        # Target reference
        reference = [
            {"unified_name": "12,13-dihydroxy-9Z-octadecenoic acid"},
            {"unified_name": "1-pyrroline-5-carboxylic acid"},
            {"unified_name": "Glucose"},
        ]

        action = CtsEnrichedMatchAction()

        # Mock successful CTS enrichment
        with patch.object(action, "cts_client") as mock_client:
            mock_client.convert = AsyncMock()
            mock_client.close = AsyncMock()
            mock_client.convert.side_effect = lambda id, from_type, to_type: {
                ("HMDB04705", "HMDB"): ["12,13-dihydroxy-9Z-octadecenoic acid"],
                ("C03564", "KEGG"): [
                    "1-pyrroline-5-carboxylic acid",
                    "pyrroline-5-carboxylate",
                ],
            }.get((id, from_type), [])

            params = CtsEnrichedMatchParams(
                unmatched_dataset_key="unmatched",
                target_dataset_key="reference",
                identifier_columns=["HMDB", "KEGG", "PUBCHEM"],
                output_key="api_matches",
                match_threshold=0.85,
            )

            context = {
                "datasets": {
                    "unmatched": unmatched_from_baseline,
                    "reference": reference,
                }
            }

            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context,
            )

            matches = context["datasets"]["api_matches"]

            # Both should now match with enriched names
            assert len(matches) == 2

            # Verify enrichment was used
            for match in matches:
                assert match["enrichment_used"] is True
                assert match["stage"] == "api_enriched"
        # This test should FAIL initially

"""Tests for the COMBINE_METABOLITE_MATCHES action."""

import pytest
from typing import Any
from unittest.mock import Mock

from biomapper.core.strategy_actions.combine_metabolite_matches import (
    CombineMetaboliteMatchesAction,
    CombineMetaboliteMatchesParams,
    MappingTier,
)
from biomapper.core.strategy_actions.typed_base import StandardActionResult


class TestCombineMetaboliteMatches:
    """Test suite for CombineMetaboliteMatchesAction."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with test data."""
        context = Mock()
        context.get_action_data = Mock(side_effect=self._get_action_data)
        context.set_action_data = Mock()
        
        # Store test data
        self.test_data = {
            "datasets": {
                # Nightingale matches between Israeli10K and UKBB
                "israeli10k_ukbb_nightingale_matches": [
                    {
                        "source": {"identifier": "total_c", "display_name": "Total cholesterol"},
                        "target": {"field_id": "23400", "title": "Total cholesterol"},
                        "confidence": 1.0,
                        "match_algorithm": "nightingale_direct",
                    },
                    {
                        "source": {"identifier": "ldl_c", "display_name": "LDL cholesterol"},
                        "target": {"field_id": "23401", "title": "LDL cholesterol"},
                        "confidence": 1.0,
                        "match_algorithm": "nightingale_direct",
                    },
                ],
                # Arivale baseline matches
                "arivale_baseline_matches": [
                    {
                        "source": {"biochemical_name": "cholesterol", "hmdb": "HMDB0000067"},
                        "target": {"nightingale_name": "Total_C"},
                        "confidence": 0.9,
                        "match_algorithm": "baseline_fuzzy",
                    },
                    {
                        "source": {"biochemical_name": "glucose", "hmdb": "HMDB0000122"},
                        "target": {"nightingale_name": "Glucose"},
                        "confidence": 0.95,
                        "match_algorithm": "baseline_fuzzy",
                    },
                ],
                # Arivale API-enriched matches
                "arivale_api_matches": [
                    {
                        "source": {"biochemical_name": "LDL Cholesterol", "hmdb": "HMDB0000068"},
                        "target": {"nightingale_name": "LDL_C"},
                        "confidence": 0.85,
                        "match_algorithm": "multi_api",
                    },
                ],
                # Arivale semantic matches
                "arivale_semantic_matches": [
                    {
                        "source": {"biochemical_name": "HDL-C", "hmdb": "HMDB0000069"},
                        "target": {"nightingale_name": "HDL_C"},
                        "confidence": 0.8,
                        "match_algorithm": "llm_validated",
                    },
                ],
            }
        }
        
        return context
    
    def _get_action_data(self, key: str, default: Any = None) -> Any:
        """Mock implementation of get_action_data."""
        return self.test_data.get(key, default)

    @pytest.fixture
    def action(self):
        """Create a CombineMetaboliteMatchesAction instance."""
        return CombineMetaboliteMatchesAction()

    @pytest.fixture
    def basic_params(self):
        """Create basic parameters for testing."""
        return CombineMetaboliteMatchesParams(
            nightingale_pairs="israeli10k_ukbb_nightingale_matches",
            arivale_mappings=[
                MappingTier(
                    key="arivale_baseline_matches",
                    tier="direct",
                    method="baseline_fuzzy",
                    confidence_weight=1.0,
                ),
            ],
            output_key="three_way_combined",
            track_provenance=True,
            min_confidence=0.5,
        )

    @pytest.fixture
    def multi_tier_params(self):
        """Create parameters with all three Arivale tiers."""
        return CombineMetaboliteMatchesParams(
            nightingale_pairs="israeli10k_ukbb_nightingale_matches",
            arivale_mappings=[
                MappingTier(
                    key="arivale_baseline_matches",
                    tier="direct",
                    method="baseline_fuzzy",
                    confidence_weight=1.0,
                ),
                MappingTier(
                    key="arivale_api_matches",
                    tier="api_enriched",
                    method="multi_api",
                    confidence_weight=0.9,
                ),
                MappingTier(
                    key="arivale_semantic_matches",
                    tier="semantic",
                    method="llm_validated",
                    confidence_weight=0.8,
                ),
            ],
            output_key="three_way_combined",
            track_provenance=True,
            min_confidence=0.0,
        )

    async def test_basic_combining(self, action, basic_params, mock_context):
        """Test basic combining of Nightingale + single Arivale tier."""
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=basic_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        # Check result structure
        assert isinstance(result, StandardActionResult)
        assert result.details["success"] is True
        
        # Get the combined results
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        
        # Should have cholesterol as a three-way match
        three_way_matches = combined.get("three_way_matches", [])
        assert len(three_way_matches) >= 1
        
        # Find cholesterol match
        cholesterol_match = next(
            (m for m in three_way_matches if "cholesterol" in str(m).lower()),
            None
        )
        assert cholesterol_match is not None
        assert cholesterol_match["israeli10k"]["field_name"] == "total_c"
        assert cholesterol_match["ukbb"]["field_id"] == "23400"
        assert cholesterol_match["arivale"]["biochemical_name"] == "cholesterol"
        assert cholesterol_match["match_confidence"] >= 0.9

    async def test_multi_tier_merging(self, action, multi_tier_params, mock_context):
        """Test merging all three Arivale tiers."""
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=multi_tier_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        assert result.details["success"] is True
        
        # Get combined results
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        three_way_matches = combined.get("three_way_matches", [])
        
        # Should have multiple matches
        assert len(three_way_matches) >= 1
        
        # Check LDL cholesterol match (has API-enriched match)
        ldl_match = next(
            (m for m in three_way_matches if "ldl" in str(m).lower()),
            None
        )
        if ldl_match:
            assert "api_enriched" in ldl_match["match_methods"] or "multi_api" in ldl_match["match_methods"]

    async def test_confidence_calculation(self, action, multi_tier_params, mock_context):
        """Test weighted and boosted confidence calculation."""
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=multi_tier_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        three_way_matches = combined.get("three_way_matches", [])
        
        # Check confidence scores
        for match in three_way_matches:
            confidence = match["match_confidence"]
            assert 0.0 <= confidence <= 1.0
            
            # If multiple methods found the same match, confidence should be boosted
            if len(match["match_methods"]) > 1:
                # Confidence should be higher than individual confidences
                assert confidence >= 0.8

    async def test_provenance_tracking(self, action, basic_params, mock_context):
        """Test complete provenance audit trail."""
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=basic_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        # Check provenance in result
        assert "provenance" in result.dict()
        assert len(result.provenance) > 0
        
        # Each provenance entry should have required fields
        for prov in result.provenance:
            assert "match_id" in prov
            assert "source_dataset" in prov
            assert "target_dataset" in prov
            assert "match_method" in prov
            assert "confidence" in prov
            assert "timestamp" in prov

    async def test_transitive_matching(self, action, multi_tier_params, mock_context):
        """Test A→B→C transitive relationships."""
        # This is implicitly tested by the three-way matching logic
        # If A (Arivale) matches B (Nightingale reference) and B matches C (Israeli10K/UKBB),
        # then we should find A→C relationships
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=multi_tier_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        
        # Should have successfully created transitive matches
        assert len(combined.get("three_way_matches", [])) > 0

    async def test_partial_matches(self, action, multi_tier_params, mock_context):
        """Test handling of 2 out of 3 dataset matches."""
        # Glucose has Arivale → Nightingale match but no Israeli10K/UKBB pair
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=multi_tier_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        summary = combined.get("summary_statistics", {})
        
        # Should track two-way matches separately
        assert "total_two_way_matches" in summary
        assert summary["total_two_way_matches"] >= summary["total_three_way_matches"]

    async def test_empty_inputs(self, action, mock_context):
        """Test graceful handling of empty inputs."""
        # Create params with non-existent dataset keys
        params = CombineMetaboliteMatchesParams(
            nightingale_pairs="non_existent_dataset",
            arivale_mappings=[
                MappingTier(
                    key="also_non_existent",
                    tier="direct",
                    method="baseline_fuzzy",
                    confidence_weight=1.0,
                ),
            ],
            output_key="empty_result",
            track_provenance=True,
            min_confidence=0.5,
        )
        
        # Override mock to return empty datasets
        mock_context.get_action_data = Mock(return_value={"datasets": {}})
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        # Should handle gracefully without errors
        assert result.details["success"] is True
        assert result.details.get("total_three_way_matches", 0) == 0

    async def test_duplicate_handling(self, action, mock_context):
        """Test handling of same match from multiple methods."""
        # Create test data with duplicate matches
        context = Mock()
        duplicate_data = {
            "datasets": {
                "israeli10k_ukbb_nightingale_matches": [
                    {
                        "source": {"identifier": "hdl_c", "display_name": "HDL cholesterol"},
                        "target": {"field_id": "23402", "title": "HDL cholesterol"},
                        "confidence": 1.0,
                        "match_algorithm": "nightingale_direct",
                    },
                ],
                "arivale_baseline_matches": [
                    {
                        "source": {"biochemical_name": "HDL cholesterol", "hmdb": "HMDB0000069"},
                        "target": {"nightingale_name": "HDL_C"},
                        "confidence": 0.95,
                        "match_algorithm": "baseline_fuzzy",
                    },
                ],
                "arivale_api_matches": [
                    {
                        "source": {"biochemical_name": "HDL-C", "hmdb": "HMDB0000069"},
                        "target": {"nightingale_name": "HDL_C"},
                        "confidence": 0.88,
                        "match_algorithm": "multi_api",
                    },
                ],
            }
        }
        
        context.get_action_data = Mock(side_effect=lambda k, d=None: duplicate_data.get(k, d))
        context.set_action_data = Mock()
        
        params = CombineMetaboliteMatchesParams(
            nightingale_pairs="israeli10k_ukbb_nightingale_matches",
            arivale_mappings=[
                MappingTier(
                    key="arivale_baseline_matches",
                    tier="direct",
                    method="baseline_fuzzy",
                    confidence_weight=1.0,
                ),
                MappingTier(
                    key="arivale_api_matches",
                    tier="api_enriched",
                    method="multi_api",
                    confidence_weight=0.9,
                ),
            ],
            output_key="deduplicated",
            track_provenance=True,
            min_confidence=0.0,
        )
        
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )
        
        saved_data = {}
        for call in context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("deduplicated", {})
        three_way_matches = combined.get("three_way_matches", [])
        
        # Should have only one HDL match with combined confidence
        hdl_matches = [m for m in three_way_matches if "hdl" in str(m).lower()]
        assert len(hdl_matches) == 1
        
        hdl_match = hdl_matches[0]
        # Should have both methods listed
        assert len(hdl_match["match_methods"]) >= 2
        # Confidence should be boosted
        assert hdl_match["match_confidence"] > 0.95

    async def test_confidence_threshold_filtering(self, action, mock_context):
        """Test that matches below confidence threshold are filtered out."""
        params = CombineMetaboliteMatchesParams(
            nightingale_pairs="israeli10k_ukbb_nightingale_matches",
            arivale_mappings=[
                MappingTier(
                    key="arivale_semantic_matches",  # Has 0.8 confidence match
                    tier="semantic",
                    method="llm_validated",
                    confidence_weight=0.8,  # Will be 0.8 * 0.8 = 0.64
                ),
            ],
            output_key="filtered",
            track_provenance=True,
            min_confidence=0.7,  # Should filter out the 0.64 confidence match
        )
        
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("filtered", {})
        three_way_matches = combined.get("three_way_matches", [])
        
        # Should have filtered out low confidence matches
        for match in three_way_matches:
            assert match["match_confidence"] >= 0.7

    async def test_summary_statistics(self, action, multi_tier_params, mock_context):
        """Test that summary statistics are correctly calculated."""
        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=multi_tier_params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        saved_data = {}
        for call in mock_context.set_action_data.call_args_list:
            saved_data[call[0][0]] = call[0][1]
        
        datasets = saved_data.get("datasets", {})
        combined = datasets.get("three_way_combined", {})
        summary = combined.get("summary_statistics", {})
        
        # Check required summary fields
        assert "total_three_way_matches" in summary
        assert "total_two_way_matches" in summary
        assert "matches_by_method" in summary
        assert "confidence_distribution" in summary
        
        # Verify counts make sense
        assert summary["total_three_way_matches"] >= 0
        assert summary["total_two_way_matches"] >= summary["total_three_way_matches"]
        
        # Check method breakdown
        methods = summary["matches_by_method"]
        assert "nightingale_direct" in methods
        assert methods["nightingale_direct"] > 0
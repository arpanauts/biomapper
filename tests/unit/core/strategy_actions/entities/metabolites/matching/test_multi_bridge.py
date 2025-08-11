"""
Unit tests for METABOLITE_MULTI_BRIDGE action.

Tests multi-bridge identifier resolution with fallback mechanisms.
Written using TDD approach - tests first, implementation second.
"""

import pytest
import pandas as pd
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from biomapper.core.strategy_actions.entities.metabolites.matching.multi_bridge import (
    MetaboliteMultiBridgeAction,
    MetaboliteMultiBridgeParams,
    MetaboliteMultiBridgeResult,
)
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY


class TestMetaboliteMultiBridge:
    """Test suite for METABOLITE_MULTI_BRIDGE action."""

    @pytest.fixture
    def sample_source_data(self) -> pd.DataFrame:
        """Create sample source metabolite data."""
        return pd.DataFrame(
            {
                "metabolite_id": [
                    "compound_1",
                    "compound_2",
                    "compound_3",
                    "compound_4",
                ],
                "hmdb_id": ["HMDB0001234", None, "HMDB0003456", "HMDB0007890"],
                "inchikey": [
                    None,
                    "QNAYBMKLOCPYGJ-REOHCLBHSA-N",
                    None,
                    "BADFORMAT-INVALID-X",
                ],
                "chebi_id": ["CHEBI:28001", "CHEBI:456", None, None],
                "kegg_id": [None, None, "C00315", "C00999"],
                "name": [
                    "Metabolite 1",
                    "Metabolite 2",
                    "Metabolite 3",
                    "Metabolite 4",
                ],
            }
        )

    @pytest.fixture
    def sample_target_data(self) -> pd.DataFrame:
        """Create sample target metabolite data."""
        return pd.DataFrame(
            {
                "target_id": [
                    "target_1",
                    "target_2",
                    "target_3",
                    "target_4",
                    "target_5",
                ],
                "hmdb_id": ["HMDB0001234", "HMDB0002468", None, "HMDB0007890", None],
                "inchikey": [
                    None,
                    "QNAYBMKLOCPYGJ-REOHCLBHSA-N",
                    "DIFFERENTKEY-UHFFFAOYSA-N",
                    None,
                    "ANOTHER-KEY-FORMAT-Z",
                ],
                "chebi_id": ["CHEBI:28001", None, "CHEBI:789", None, "CHEBI:456"],
                "kegg_id": ["C00123", None, "C00315", "C00999", None],
                "description": [
                    "Target 1",
                    "Target 2",
                    "Target 3",
                    "Target 4",
                    "Target 5",
                ],
            }
        )

    @pytest.fixture
    def basic_params(self) -> Dict[str, Any]:
        """Basic parameters for multi-bridge matching."""
        return {
            "source_key": "source_metabolites",
            "target_key": "target_metabolites",
            "output_key": "multi_bridge_matches",
            "bridge_types": ["hmdb", "inchikey", "chebi", "kegg"],
            "bridge_priority": ["hmdb", "inchikey", "chebi", "kegg"],
            "confidence_weights": {
                "hmdb": 0.95,
                "inchikey": 0.90,
                "chebi": 0.85,
                "kegg": 0.80,
            },
            "min_confidence_threshold": 0.75,
            "use_cts_fallback": True,
            "use_semantic_fallback": False,
            "max_attempts_per_bridge": 3,
            "combine_strategy": "highest_confidence",
        }

    @pytest.fixture
    def mock_context(self, sample_source_data, sample_target_data) -> Dict[str, Any]:
        """Create mock execution context."""
        return {
            "datasets": {
                "source_metabolites": sample_source_data,
                "target_metabolites": sample_target_data,
            },
            "statistics": {},
        }

    def test_action_registration(self):
        """Test that action is properly registered."""
        assert "METABOLITE_MULTI_BRIDGE" in ACTION_REGISTRY
        assert ACTION_REGISTRY["METABOLITE_MULTI_BRIDGE"] == MetaboliteMultiBridgeAction

    def test_params_model_validation(self):
        """Test parameter model validation."""
        # Valid params
        params = MetaboliteMultiBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            bridge_types=["hmdb", "inchikey"],
        )
        assert params.bridge_priority == [
            "hmdb",
            "inchikey",
        ]  # Should default to bridge_types
        assert params.min_confidence_threshold == 0.8  # Default
        assert params.use_cts_fallback is True  # Default
        assert params.combine_strategy == "highest_confidence"  # Default

        # Invalid bridge type
        with pytest.raises(ValueError):
            MetaboliteMultiBridgeParams(
                source_key="source",
                target_key="target",
                output_key="output",
                bridge_types=["invalid_bridge"],
            )

        # Invalid combine strategy
        with pytest.raises(ValueError):
            MetaboliteMultiBridgeParams(
                source_key="source",
                target_key="target",
                output_key="output",
                bridge_types=["hmdb"],
                combine_strategy="invalid_strategy",
            )

    @pytest.mark.asyncio
    async def test_direct_bridge_matches(self, mock_context, basic_params):
        """Test direct bridge matching without fallback."""
        action = MetaboliteMultiBridgeAction()
        basic_params["use_cts_fallback"] = False
        basic_params["use_semantic_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        matches_df = mock_context["datasets"]["multi_bridge_matches"]

        # Check for expected direct matches
        # compound_1 (HMDB0001234) should match target_1 (HMDB0001234)
        hmdb_matches = matches_df[matches_df["bridge_type"] == "hmdb"]
        assert len(hmdb_matches[hmdb_matches["source_id"] == "compound_1"]) > 0

        # compound_2 (InChIKey) should match target_2
        inchikey_matches = matches_df[matches_df["bridge_type"] == "inchikey"]
        assert len(inchikey_matches[inchikey_matches["source_id"] == "compound_2"]) > 0

        # compound_4 (HMDB0007890) should match target_4
        hmdb_matches_4 = matches_df[
            (matches_df["bridge_type"] == "hmdb")
            & (matches_df["source_id"] == "compound_4")
        ]
        assert len(hmdb_matches_4) > 0

    @pytest.mark.asyncio
    async def test_bridge_priority_ordering(self, mock_context, basic_params):
        """Test that bridges are tried in priority order."""
        # Set up data where multiple bridges could match
        source_data = pd.DataFrame(
            {
                "metabolite_id": ["compound_1"],
                "hmdb_id": ["HMDB0001234"],
                "chebi_id": ["CHEBI:28001"],
                "name": ["Test Compound"],
            }
        )

        target_data = pd.DataFrame(
            {
                "target_id": ["target_1", "target_2"],
                "hmdb_id": ["HMDB0001234", None],
                "chebi_id": [None, "CHEBI:28001"],
                "description": ["Target via HMDB", "Target via ChEBI"],
            }
        )

        mock_context["datasets"]["source_metabolites"] = source_data
        mock_context["datasets"]["target_metabolites"] = target_data

        action = MetaboliteMultiBridgeAction()
        basic_params["bridge_priority"] = ["hmdb", "chebi"]  # HMDB should be preferred
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        matches_df = mock_context["datasets"]["multi_bridge_matches"]
        compound_1_matches = matches_df[matches_df["source_id"] == "compound_1"]

        # Should prefer HMDB match due to higher priority
        if len(compound_1_matches) > 0:
            best_match = compound_1_matches.loc[
                compound_1_matches["confidence"].idxmax()
            ]
            assert best_match["bridge_type"] == "hmdb"

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, mock_context, basic_params):
        """Test confidence score calculation."""
        action = MetaboliteMultiBridgeAction()
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        matches_df = mock_context["datasets"]["multi_bridge_matches"]

        # Check confidence scores match expected weights
        hmdb_matches = matches_df[matches_df["bridge_type"] == "hmdb"]
        if len(hmdb_matches) > 0:
            assert all(
                hmdb_matches["confidence"]
                >= basic_params["confidence_weights"]["hmdb"] * 0.9
            )  # Allow some variance

        inchikey_matches = matches_df[matches_df["bridge_type"] == "inchikey"]
        if len(inchikey_matches) > 0:
            assert all(
                inchikey_matches["confidence"]
                >= basic_params["confidence_weights"]["inchikey"] * 0.9
            )

    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, mock_context, basic_params):
        """Test that matches below confidence threshold are filtered."""
        action = MetaboliteMultiBridgeAction()
        basic_params["min_confidence_threshold"] = 0.95  # Very high threshold
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        matches_df = mock_context["datasets"]["multi_bridge_matches"]

        # All remaining matches should be above threshold
        assert all(matches_df["confidence"] >= 0.95)

    @pytest.mark.asyncio
    async def test_combine_strategy_highest_confidence(
        self, mock_context, basic_params
    ):
        """Test highest confidence combination strategy."""
        # Set up data where one compound matches via multiple bridges
        source_data = pd.DataFrame(
            {
                "metabolite_id": ["compound_1"],
                "hmdb_id": ["HMDB0001234"],
                "chebi_id": ["CHEBI:28001"],
                "name": ["Test Compound"],
            }
        )

        target_data = pd.DataFrame(
            {
                "target_id": ["target_1"],
                "hmdb_id": ["HMDB0001234"],
                "chebi_id": ["CHEBI:28001"],  # Same compound, multiple bridges
                "description": ["Target with multiple IDs"],
            }
        )

        mock_context["datasets"]["source_metabolites"] = source_data
        mock_context["datasets"]["target_metabolites"] = target_data

        action = MetaboliteMultiBridgeAction()
        basic_params["combine_strategy"] = "highest_confidence"
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        matches_df = mock_context["datasets"]["multi_bridge_matches"]
        compound_1_matches = matches_df[matches_df["source_id"] == "compound_1"]

        # Should have matches from both bridges
        bridge_types = set(compound_1_matches["bridge_type"])
        assert "hmdb" in bridge_types
        assert "chebi" in bridge_types

    @pytest.mark.asyncio
    async def test_combine_strategy_consensus(self, mock_context, basic_params):
        """Test consensus combination strategy."""
        action = MetaboliteMultiBridgeAction()
        basic_params["combine_strategy"] = "consensus"
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        # Should succeed even if fewer matches due to consensus requirement
        assert result.success is True
        matches_df = mock_context["datasets"]["multi_bridge_matches"]

        # All matches in consensus mode should have high confidence
        if len(matches_df) > 0:
            assert matches_df["confidence"].mean() >= 0.8

    @pytest.mark.asyncio
    @patch(
        "biomapper.core.strategy_actions.entities.metabolites.matching.multi_bridge.CTSTranslator"
    )
    async def test_cts_fallback_mechanism(self, mock_cts, mock_context, basic_params):
        """Test CTS fallback when direct bridges fail."""
        # Mock CTS translator
        mock_cts_instance = Mock()
        mock_cts_instance.translate_batch = AsyncMock(
            return_value={
                "compound_3": ["HMDB0009999"]  # Successful translation
            }
        )
        mock_cts.return_value = mock_cts_instance

        action = MetaboliteMultiBridgeAction()
        basic_params["use_cts_fallback"] = True

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True

        # Should have attempted CTS translation for unmatched compounds
        assert mock_cts_instance.translate_batch.called

    @pytest.mark.asyncio
    @patch(
        "biomapper.core.strategy_actions.entities.metabolites.matching.multi_bridge.SemanticMatcher"
    )
    async def test_semantic_fallback_mechanism(
        self, mock_semantic, mock_context, basic_params
    ):
        """Test semantic fallback when other methods fail."""
        # Mock semantic matcher
        mock_semantic_instance = Mock()
        mock_semantic_instance.find_matches = AsyncMock(
            return_value=[
                {"source_id": "compound_3", "target_id": "target_3", "confidence": 0.82}
            ]
        )
        mock_semantic.return_value = mock_semantic_instance

        action = MetaboliteMultiBridgeAction()
        basic_params["use_semantic_fallback"] = True
        basic_params["semantic_threshold"] = 0.8

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True

        # Should have attempted semantic matching
        assert mock_semantic_instance.find_matches.called

    @pytest.mark.asyncio
    async def test_max_attempts_per_bridge(self, mock_context, basic_params):
        """Test that bridges are retried up to max attempts."""
        action = MetaboliteMultiBridgeAction()
        basic_params["max_attempts_per_bridge"] = 2
        basic_params["use_cts_fallback"] = False

        # Mock a bridge method to fail initially
        original_method = action._match_via_bridge
        attempt_counts = {"hmdb": 0}

        async def mock_bridge_method(
            source_df, target_df, bridge_type, confidence_weight
        ):
            attempt_counts[bridge_type] = attempt_counts.get(bridge_type, 0) + 1
            if bridge_type == "hmdb" and attempt_counts[bridge_type] < 2:
                raise Exception("Simulated failure")
            return await original_method(
                source_df, target_df, bridge_type, confidence_weight
            )

        with patch.object(action, "_match_via_bridge", mock_bridge_method):
            params = MetaboliteMultiBridgeParams(**basic_params)
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context,
            )

        # Should have retried HMDB bridge
        assert attempt_counts["hmdb"] == 2

    @pytest.mark.asyncio
    async def test_empty_source_dataset(self, mock_context, basic_params):
        """Test handling of empty source dataset."""
        mock_context["datasets"]["source_metabolites"] = pd.DataFrame(
            columns=["metabolite_id", "hmdb_id"]
        )

        action = MetaboliteMultiBridgeAction()
        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        assert result.data.total_source_compounds == 0
        assert result.data.total_matches == 0

    @pytest.mark.asyncio
    async def test_missing_dataset_error(self, mock_context, basic_params):
        """Test error handling when required dataset is missing."""
        del mock_context["datasets"]["source_metabolites"]

        action = MetaboliteMultiBridgeAction()
        params = MetaboliteMultiBridgeParams(**basic_params)

        with pytest.raises(Exception):  # Should raise appropriate error
            await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context,
            )

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, mock_context, basic_params):
        """Test that comprehensive statistics are tracked."""
        action = MetaboliteMultiBridgeAction()
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        stats = result.data

        # Check all required statistics are present
        assert hasattr(stats, "total_source_compounds")
        assert hasattr(stats, "total_target_compounds")
        assert hasattr(stats, "total_matches")
        assert hasattr(stats, "matches_by_bridge")
        assert hasattr(stats, "confidence_distribution")
        assert hasattr(stats, "fallback_usage")

        # Check reasonable values
        assert stats.total_source_compounds == 4  # From sample data
        assert stats.total_target_compounds == 5  # From sample data
        assert stats.total_matches >= 0

    @pytest.mark.asyncio
    async def test_performance_large_dataset(self, mock_context, basic_params):
        """Test performance with large dataset (1000 compounds)."""
        import time

        # Create large datasets
        large_source = pd.DataFrame(
            {
                "metabolite_id": [f"compound_{i}" for i in range(1000)],
                "hmdb_id": [f"HMDB{str(i).zfill(7)}" for i in range(1000)],
                "name": [f"Metabolite {i}" for i in range(1000)],
            }
        )

        large_target = pd.DataFrame(
            {
                "target_id": [f"target_{i}" for i in range(500)],
                "hmdb_id": [
                    f"HMDB{str(i).zfill(7)}" for i in range(500)
                ],  # 50% overlap
                "description": [f"Target {i}" for i in range(500)],
            }
        )

        mock_context["datasets"]["source_metabolites"] = large_source
        mock_context["datasets"]["target_metabolites"] = large_target

        action = MetaboliteMultiBridgeAction()
        basic_params["bridge_types"] = ["hmdb"]  # Single bridge for performance
        basic_params["use_cts_fallback"] = False
        basic_params["use_semantic_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)

        start_time = time.time()
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        execution_time = time.time() - start_time

        assert result.success is True
        assert execution_time < 10.0  # Should complete within 10 seconds

        # Should find matches (500 compounds have matching HMDB IDs)
        assert result.data.total_matches > 400  # Allow for some processing variations

    @pytest.mark.asyncio
    async def test_multi_bridge_result_model(self):
        """Test the result model validation."""
        # Test valid result
        result_data = MetaboliteMultiBridgeResult(
            total_source_compounds=100,
            total_target_compounds=200,
            total_matches=50,
            matches_by_bridge={"hmdb": 30, "inchikey": 20},
            confidence_distribution={"high": 25, "medium": 15, "low": 10},
            fallback_usage={"cts": 10, "semantic": 5},
            execution_time_seconds=5.2,
            bridge_performance={"hmdb": 0.8, "inchikey": 0.6},
        )

        assert result_data.total_source_compounds == 100
        assert result_data.matches_by_bridge["hmdb"] == 30
        assert result_data.execution_time_seconds == 5.2

    @pytest.mark.asyncio
    async def test_complex_multi_identifier_scenario(self, mock_context, basic_params):
        """Test complex scenario with compounds having multiple identifier types."""
        # Create complex data with overlapping identifiers
        complex_source = pd.DataFrame(
            {
                "metabolite_id": ["comp_1", "comp_2", "comp_3"],
                "hmdb_id": ["HMDB0001234", None, "HMDB0003456"],
                "inchikey": [None, "QNAYBMKLOCPYGJ-REOHCLBHSA-N", None],
                "chebi_id": ["CHEBI:28001", "CHEBI:456", None],
                "kegg_id": [None, None, "C00315"],
                "pubchem_id": ["680956", None, None],
            }
        )

        complex_target = pd.DataFrame(
            {
                "target_id": ["tgt_1", "tgt_2", "tgt_3", "tgt_4"],
                "hmdb_id": ["HMDB0001234", None, "HMDB0003456", None],
                "inchikey": [
                    None,
                    "QNAYBMKLOCPYGJ-REOHCLBHSA-N",
                    None,
                    "DIFFERENT-KEY-FORMAT-Z",
                ],
                "chebi_id": ["CHEBI:28001", "CHEBI:456", None, "CHEBI:999"],
                "kegg_id": [None, None, "C00315", "C00777"],
            }
        )

        mock_context["datasets"]["source_metabolites"] = complex_source
        mock_context["datasets"]["target_metabolites"] = complex_target

        action = MetaboliteMultiBridgeAction()
        basic_params["bridge_types"] = ["hmdb", "inchikey", "chebi", "kegg"]
        basic_params["use_cts_fallback"] = False

        params = MetaboliteMultiBridgeParams(**basic_params)
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        matches_df = mock_context["datasets"]["multi_bridge_matches"]

        # Should find multiple matches across different bridge types
        bridge_types_found = set(matches_df["bridge_type"])
        assert len(bridge_types_found) > 1  # Multiple bridge types should be used

        # Each compound should have at least one match
        unique_sources = set(matches_df["source_id"])
        assert len(unique_sources) >= 2  # At least 2 compounds should match

"""Tests for MERGE_WITH_UNIPROT_RESOLUTION action."""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from pathlib import Path

from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import (
    MergeWithUniprotResolutionParams,
    MergeWithUniprotResolutionAction,
)


class TestMergeWithUniprotResolutionParams:
    """Test parameter validation for MERGE_WITH_UNIPROT_RESOLUTION."""

    def test_valid_params(self):
        """Test that valid parameters are accepted."""
        params = MergeWithUniprotResolutionParams(
            source_dataset_key="ukbb",
            target_dataset_key="hpa",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
        )
        assert params.source_dataset_key == "ukbb"
        assert params.target_dataset_key == "hpa"
        assert params.source_id_column == "UniProt"
        assert params.target_id_column == "uniprot"
        assert params.output_key == "merged"
        assert params.composite_separator == "_"  # default
        assert params.use_api is True  # default
        assert params.api_batch_size == 100  # default
        assert params.api_cache_results is True  # default
        assert params.confidence_threshold == 0.0  # default

    def test_missing_required_params(self):
        """Test that missing required parameters raise ValidationError."""
        # Missing source_dataset_key
        with pytest.raises(ValidationError) as exc_info:
            MergeWithUniprotResolutionParams(
                target_dataset_key="hpa",
                source_id_column="UniProt",
                target_id_column="uniprot",
                output_key="merged",
            )
        assert "source_dataset_key" in str(exc_info.value)

        # Missing target_dataset_key
        with pytest.raises(ValidationError) as exc_info:
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                source_id_column="UniProt",
                target_id_column="uniprot",
                output_key="merged",
            )
        assert "target_dataset_key" in str(exc_info.value)

        # Missing source_id_column
        with pytest.raises(ValidationError) as exc_info:
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                target_dataset_key="hpa",
                target_id_column="uniprot",
                output_key="merged",
            )
        assert "source_id_column" in str(exc_info.value)

        # Missing target_id_column
        with pytest.raises(ValidationError) as exc_info:
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                target_dataset_key="hpa",
                source_id_column="UniProt",
                output_key="merged",
            )
        assert "target_id_column" in str(exc_info.value)

        # Missing output_key
        with pytest.raises(ValidationError) as exc_info:
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                target_dataset_key="hpa",
                source_id_column="UniProt",
                target_id_column="uniprot",
            )
        assert "output_key" in str(exc_info.value)

    def test_optional_params(self):
        """Test optional parameters."""
        params = MergeWithUniprotResolutionParams(
            source_dataset_key="ukbb",
            target_dataset_key="hpa",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            composite_separator="__",
            use_api=False,
            api_batch_size=50,
            api_cache_results=False,
            confidence_threshold=0.8,
        )
        assert params.composite_separator == "__"
        assert params.use_api is False
        assert params.api_batch_size == 50
        assert params.api_cache_results is False
        assert params.confidence_threshold == 0.8

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation."""
        # Valid threshold (0.0 - 1.0)
        params = MergeWithUniprotResolutionParams(
            source_dataset_key="ukbb",
            target_dataset_key="hpa",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            confidence_threshold=0.5,
        )
        assert params.confidence_threshold == 0.5

        # Invalid threshold (negative)
        with pytest.raises(ValidationError):
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                target_dataset_key="hpa",
                source_id_column="UniProt",
                target_id_column="uniprot",
                output_key="merged",
                confidence_threshold=-0.1,
            )

        # Invalid threshold (> 1.0)
        with pytest.raises(ValidationError):
            MergeWithUniprotResolutionParams(
                source_dataset_key="ukbb",
                target_dataset_key="hpa",
                source_id_column="UniProt",
                target_id_column="uniprot",
                output_key="merged",
                confidence_threshold=1.1,
            )


class TestMergeWithUniprotResolutionAction:
    """Test MERGE_WITH_UNIPROT_RESOLUTION action implementation."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return MergeWithUniprotResolutionAction()

    def _create_context(self, datasets=None):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        # Initialize datasets
        if datasets:
            context.set_action_data("datasets", datasets)
        else:
            context.set_action_data("datasets", {})
        context.set_action_data("metadata", {})
        return context

    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = MagicMock()
        target = MagicMock()
        return source, target

    @pytest.fixture
    def sample_source_data(self):
        """Create sample source dataset (UKBB-like)."""
        return [
            {"UniProt": "P12345", "Assay": "EBI3", "Panel": "Inflammation"},
            {"UniProt": "Q14213_Q8NEV9", "Assay": "IL27", "Panel": "Inflammation"},
            {"UniProt": "P67890", "Assay": "TNF", "Panel": "Inflammation"},
            {"UniProt": "Q99999", "Assay": "HIST1", "Panel": "Epigenetics"},
        ]

    @pytest.fixture
    def sample_target_data(self):
        """Create sample target dataset (HPA-like)."""
        return [
            {"uniprot": "P12345", "gene": "IL27", "organ": "lymph_node"},
            {"uniprot": "Q14213", "gene": "EBI3", "organ": "spleen"},
            {"uniprot": "Q8NEV9", "gene": "IL27B", "organ": "liver"},
            {"uniprot": "P11111", "gene": "UNIQUE", "organ": "brain"},
        ]

    # Direct Matching Tests
    @pytest.mark.asyncio
    async def test_direct_exact_match(self, action, mock_endpoints):
        """Test exact ID matching."""
        source_data = [{"UniProt": "P12345", "Assay": "Test"}]
        target_data = [{"uniprot": "P12345", "gene": "TEST"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,  # Only direct matching
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have one matched row
        assert len(merged_data) == 1
        assert merged_data[0]["UniProt"] == "P12345"
        assert merged_data[0]["uniprot"] == "P12345"
        assert merged_data[0]["match_value"] == "P12345"
        assert merged_data[0]["match_type"] == "direct"
        assert merged_data[0]["match_confidence"] == 1.0
        assert merged_data[0]["match_status"] == "matched"
        assert merged_data[0]["api_resolved"] is False

    @pytest.mark.asyncio
    async def test_composite_to_single_match(self, action, mock_endpoints):
        """Test composite ID matching single ID."""
        source_data = [{"UniProt": "Q14213_Q8NEV9", "Assay": "Test"}]
        target_data = [
            {"uniprot": "Q14213", "gene": "EBI3"},
            {"uniprot": "Q8NEV9", "gene": "IL27B"},
        ]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have TWO matched rows (one for each composite part)
        assert len(merged_data) == 2

        # Check first match
        match1 = next(row for row in merged_data if row["match_value"] == "Q14213")
        assert match1["UniProt"] == "Q14213_Q8NEV9"
        assert match1["uniprot"] == "Q14213"
        assert match1["match_type"] == "composite"
        assert match1["match_confidence"] == 1.0
        assert match1["match_status"] == "matched"
        assert match1["gene"] == "EBI3"

        # Check second match
        match2 = next(row for row in merged_data if row["match_value"] == "Q8NEV9")
        assert match2["UniProt"] == "Q14213_Q8NEV9"
        assert match2["uniprot"] == "Q8NEV9"
        assert match2["match_type"] == "composite"
        assert match2["match_confidence"] == 1.0
        assert match2["match_status"] == "matched"
        assert match2["gene"] == "IL27B"

    @pytest.mark.asyncio
    async def test_composite_to_composite_match(self, action, mock_endpoints):
        """Test composite ID matching composite ID."""
        source_data = [{"UniProt": "Q14213_Q8NEV9", "Assay": "Test"}]
        target_data = [{"uniprot": "Q14213_P12345", "gene": "MULTI"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have one matched row (common part: Q14213)
        assert len(merged_data) == 1
        assert merged_data[0]["UniProt"] == "Q14213_Q8NEV9"
        assert merged_data[0]["uniprot"] == "Q14213_P12345"
        assert merged_data[0]["match_value"] == "Q14213"
        assert merged_data[0]["match_type"] == "composite"
        assert merged_data[0]["match_confidence"] == 1.0
        assert merged_data[0]["match_status"] == "matched"

    @pytest.mark.asyncio
    async def test_custom_composite_separator(self, action, mock_endpoints):
        """Test custom composite separator."""
        source_data = [{"UniProt": "Q14213__Q8NEV9", "Assay": "Test"}]
        target_data = [{"uniprot": "Q14213", "gene": "EBI3"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            composite_separator="__",  # Custom separator
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should match using custom separator
        assert len(merged_data) == 1
        assert merged_data[0]["match_value"] == "Q14213"
        assert merged_data[0]["match_type"] == "composite"

    # Output Structure Tests
    @pytest.mark.asyncio
    async def test_match_metadata_columns(self, action, mock_endpoints):
        """Test that all match metadata columns are present."""
        source_data = [{"UniProt": "P12345", "Assay": "Test"}]
        target_data = [{"uniprot": "P12345", "gene": "TEST"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]
        row = merged_data[0]

        # Check all required metadata columns
        assert "match_value" in row
        assert "match_type" in row
        assert "match_confidence" in row
        assert "match_status" in row
        assert "api_resolved" in row

        # Check data types
        assert isinstance(row["match_value"], str)
        assert isinstance(row["match_type"], str)
        assert isinstance(row["match_confidence"], float)
        assert isinstance(row["match_status"], str)
        assert isinstance(row["api_resolved"], bool)

    @pytest.mark.asyncio
    async def test_all_rows_preserved(self, action, mock_endpoints):
        """Test that no rows are lost in merging."""
        source_data = [
            {"UniProt": "P12345", "Assay": "Test1"},
            {"UniProt": "P99999", "Assay": "Test2"},  # Unmatched
        ]
        target_data = [
            {"uniprot": "P12345", "gene": "TEST1"},
            {"uniprot": "P88888", "gene": "TEST2"},  # Unmatched
        ]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have 3 rows: 1 matched + 1 source_only + 1 target_only
        assert len(merged_data) == 3

        statuses = [row["match_status"] for row in merged_data]
        assert "matched" in statuses
        assert "source_only" in statuses
        assert "target_only" in statuses

    @pytest.mark.asyncio
    async def test_column_suffixes(self, action, mock_endpoints):
        """Test column conflict resolution with suffixes."""
        source_data = [{"UniProt": "P12345", "name": "Source Name"}]
        target_data = [{"uniprot": "P12345", "name": "Target Name"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]
        row = merged_data[0]

        # ID columns should not have suffixes
        assert "UniProt" in row
        assert "uniprot" in row

        # Conflicting columns should have suffixes
        assert "name_source" in row
        assert "name_target" in row
        assert row["name_source"] == "Source Name"
        assert row["name_target"] == "Target Name"

    # API Resolution Tests
    @pytest.mark.asyncio
    async def test_api_resolution_called_for_unmatched(self, action, mock_endpoints):
        """Test that API is called only for unmatched IDs."""
        source_data = [
            {"UniProt": "P12345", "Assay": "Test1"},  # Will match directly
            {"UniProt": "OLD123", "Assay": "Test2"},  # Will need API resolution
        ]
        target_data = [
            {"uniprot": "P12345", "gene": "TEST1"},
            {"uniprot": "NEW123", "gene": "TEST2"},  # OLD123 resolves to this
        ]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=True,
        )

        # Mock the API resolver to return OLD123 -> NEW123
        mock_api_result = (
            [
                {
                    "source_idx": 1,
                    "target_idx": 1,
                    "source_id": "OLD123",
                    "target_id": "NEW123",
                    "match_value": "OLD123->NEW123",
                    "match_type": "historical",
                    "match_confidence": 0.9,
                    "api_resolved": True,
                }
            ],
            1,  # api_calls_made
        )

        with patch.object(action, "_resolve_with_api", return_value=mock_api_result):
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have 2 matched rows
        matched_rows = [row for row in merged_data if row["match_status"] == "matched"]
        assert len(matched_rows) == 2

        # Check direct match
        direct_match = next(
            row for row in matched_rows if row["match_type"] == "direct"
        )
        assert direct_match["UniProt"] == "P12345"
        assert direct_match["api_resolved"] is False

        # Check API resolved match
        api_match = next(
            row for row in matched_rows if row["match_type"] == "historical"
        )
        assert api_match["UniProt"] == "OLD123"
        assert api_match["uniprot"] == "NEW123"
        assert api_match["match_value"] == "OLD123->NEW123"
        assert api_match["match_confidence"] == 0.9
        assert api_match["api_resolved"] is True

    @pytest.mark.asyncio
    async def test_api_disabled(self, action, mock_endpoints):
        """Test with use_api=False."""
        source_data = [
            {"UniProt": "P12345", "Assay": "Test1"},
            {"UniProt": "OLD123", "Assay": "Test2"},  # Won't resolve without API
        ]
        target_data = [
            {"uniprot": "P12345", "gene": "TEST1"},
            {"uniprot": "NEW123", "gene": "TEST2"},
        ]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have 1 matched + 1 source_only + 1 target_only
        assert len(merged_data) == 3
        matched_rows = [row for row in merged_data if row["match_status"] == "matched"]
        assert len(matched_rows) == 1
        assert matched_rows[0]["UniProt"] == "P12345"

        # Check no API resolution occurred
        for row in merged_data:
            assert row["api_resolved"] is False

    # Edge Cases
    @pytest.mark.asyncio
    async def test_empty_datasets(self, action, mock_endpoints):
        """Test with empty input datasets."""
        datasets = {"source": [], "target": []}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        merged_data = context.get_action_data("datasets", {})["merged"]
        assert len(merged_data) == 0

    @pytest.mark.asyncio
    async def test_missing_datasets(self, action, mock_endpoints):
        """Test error when datasets don't exist in context."""
        context = self._create_context({})

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="missing_source",
            target_dataset_key="missing_target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
        )

        with pytest.raises(ValueError) as exc_info:
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

        assert "missing_source" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_id_columns(self, action, mock_endpoints):
        """Test error when ID columns don't exist."""
        source_data = [{"wrong_column": "P12345"}]
        target_data = [{"uniprot": "P12345"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",  # Doesn't exist
            target_id_column="uniprot",
            output_key="merged",
        )

        with pytest.raises(ValueError) as exc_info:
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

        assert "UniProt" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, action, mock_endpoints):
        """Test that matches below confidence threshold are filtered out."""
        source_data = [{"UniProt": "OLD123", "Assay": "Test"}]
        target_data = [{"uniprot": "NEW123", "gene": "TEST"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            confidence_threshold=0.9,  # High threshold
        )

        # Mock API to return low confidence match
        mock_api_result = (
            [
                {
                    "source_idx": 0,
                    "target_idx": 0,
                    "source_id": "OLD123",
                    "target_id": "NEW123",
                    "match_value": "OLD123->NEW123",
                    "match_type": "historical",
                    "match_confidence": 0.5,  # Low confidence
                    "api_resolved": True,
                }
            ],
            1,  # api_calls_made
        )

        with patch.object(action, "_resolve_with_api", return_value=mock_api_result):
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

        merged_data = context.get_action_data("datasets", {})["merged"]

        # Should have 2 unmatched rows (confidence too low)
        assert len(merged_data) == 2
        matched_rows = [row for row in merged_data if row["match_status"] == "matched"]
        assert len(matched_rows) == 0


class TestRealData:
    """Test with real biological data files."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return MergeWithUniprotResolutionAction()

    def _create_context(self, datasets=None):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        if datasets:
            context.set_action_data("datasets", datasets)
        else:
            context.set_action_data("datasets", {})
        context.set_action_data("metadata", {})
        return context

    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = MagicMock()
        target = MagicMock()
        return source, target

    @pytest.mark.asyncio
    async def test_load_real_data_first(self, action, mock_endpoints):
        """Test loading real data files first."""
        # This test depends on having the data loaded with LOAD_DATASET_IDENTIFIERS
        # We'll skip if the data files don't exist
        ukbb_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/ukbb/UKBB_Protein_Meta.tsv"
        hpa_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/isb_osp/hpa_osps.csv"

        if not Path(ukbb_file).exists() or not Path(hpa_file).exists():
            pytest.skip("Real data files not found")

        # This test would require loading the data first with LOAD_DATASET_IDENTIFIERS
        # For now, we'll create a placeholder that confirms the files exist
        assert Path(ukbb_file).exists()
        assert Path(hpa_file).exists()

    @pytest.mark.asyncio
    async def test_metadata_structure(self, action, mock_endpoints):
        """Test that metadata has correct structure."""
        source_data = [{"UniProt": "P12345", "Assay": "Test"}]
        target_data = [{"uniprot": "P12345", "gene": "TEST"}]

        datasets = {"source": source_data, "target": target_data}
        context = self._create_context(datasets)

        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="UniProt",
            target_id_column="uniprot",
            output_key="merged",
            use_api=False,
        )

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        metadata = context.get_action_data("metadata", {})["merged"]

        # Check required metadata fields
        assert "total_source_rows" in metadata
        assert "total_target_rows" in metadata
        assert "total_output_rows" in metadata
        assert "matches_by_type" in metadata
        assert "unmatched_source" in metadata
        assert "unmatched_target" in metadata
        assert "api_calls_made" in metadata
        assert "unique_source_ids" in metadata
        assert "unique_target_ids" in metadata
        assert "processing_time" in metadata

        # Check values
        assert metadata["total_source_rows"] == 1
        assert metadata["total_target_rows"] == 1
        assert metadata["total_output_rows"] == 1
        assert metadata["matches_by_type"]["direct"] == 1
        assert metadata["matches_by_type"]["composite"] == 0
        assert metadata["matches_by_type"]["historical"] == 0
        assert metadata["unmatched_source"] == 0
        assert metadata["unmatched_target"] == 0
        assert metadata["api_calls_made"] == 0
        assert metadata["unique_source_ids"] == 1
        assert metadata["unique_target_ids"] == 1
        assert metadata["processing_time"] > 0

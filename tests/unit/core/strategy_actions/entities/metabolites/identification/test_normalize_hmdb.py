"""Tests for METABOLITE_NORMALIZE_HMDB action.

Following TDD approach - these tests are written BEFORE implementation.
"""

import pytest
import pandas as pd
import numpy as np
import time

from biomapper.core.strategy_actions.entities.metabolites.identification.normalize_hmdb import (
    MetaboliteNormalizeHmdb,
    MetaboliteNormalizeHmdbParams,
    normalize_hmdb_id,
    handle_secondary_accessions,
    validate_hmdb_format,
    extract_hmdb_number,
    clean_hmdb_prefix,
)
from biomapper.core.exceptions import BiomapperError


class TestHmdbNormalizationFunctions:
    """Test individual normalization functions."""

    def test_normalize_hmdb_id_basic_padding(self):
        """Test basic HMDB ID padding normalization."""
        # 4-digit to 7-digit
        assert normalize_hmdb_id("HMDB1234", "7digit") == "HMDB0001234"

        # 5-digit to 7-digit
        assert normalize_hmdb_id("HMDB01234", "7digit") == "HMDB0001234"

        # Already 7-digit
        assert normalize_hmdb_id("HMDB0001234", "7digit") == "HMDB0001234"

        # Just number to 7-digit
        assert normalize_hmdb_id("1234", "7digit") == "HMDB0001234"

    def test_normalize_hmdb_id_different_formats(self):
        """Test different target format options."""
        # 7-digit format
        assert normalize_hmdb_id("HMDB1234", "7digit") == "HMDB0001234"

        # 5-digit format
        assert normalize_hmdb_id("HMDB1234", "5digit") == "HMDB01234"

        # Minimal format (no padding)
        assert normalize_hmdb_id("HMDB1234", "minimal") == "HMDB1234"
        assert normalize_hmdb_id("1234", "minimal") == "HMDB1234"

    def test_normalize_hmdb_id_case_insensitive(self):
        """Test case insensitive normalization."""
        assert normalize_hmdb_id("hmdb1234", "7digit") == "HMDB0001234"
        assert normalize_hmdb_id("HmDb1234", "7digit") == "HMDB0001234"
        assert normalize_hmdb_id("HMDB1234", "7digit") == "HMDB0001234"

    def test_normalize_hmdb_id_with_whitespace(self):
        """Test handling of whitespace."""
        assert normalize_hmdb_id("  HMDB1234  ", "7digit") == "HMDB0001234"
        assert normalize_hmdb_id("\nHMDB1234\t", "7digit") == "HMDB0001234"

    def test_normalize_hmdb_id_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Empty or None
        assert pd.isna(normalize_hmdb_id(None, "7digit"))
        assert pd.isna(normalize_hmdb_id(np.nan, "7digit"))
        assert pd.isna(normalize_hmdb_id(pd.NA, "7digit"))

        # Invalid format should return None
        assert normalize_hmdb_id("NOTHMDB1234", "7digit") is None
        assert normalize_hmdb_id("ABC123", "7digit") is None
        assert normalize_hmdb_id("HMDB", "7digit") is None
        assert normalize_hmdb_id("", "7digit") is None

    def test_clean_hmdb_prefix(self):
        """Test cleaning of various HMDB prefix formats."""
        assert clean_hmdb_prefix("HMDB:1234") == "HMDB1234"
        assert clean_hmdb_prefix("HMDB_1234") == "HMDB1234"
        assert clean_hmdb_prefix("HMDB-1234") == "HMDB1234"
        assert clean_hmdb_prefix("hmdb:1234") == "HMDB1234"
        assert clean_hmdb_prefix("HMDB1234") == "HMDB1234"
        assert clean_hmdb_prefix("1234") == "1234"

    def test_handle_secondary_accessions(self):
        """Test handling of secondary HMDB accessions."""
        # Single ID
        result = handle_secondary_accessions("HMDB1234", "7digit")
        assert result == ["HMDB0001234"]

        # Multiple IDs separated by semicolon
        result = handle_secondary_accessions("HMDB1234;HMDB5678", "7digit")
        assert result == ["HMDB0001234", "HMDB0005678"]

        # Multiple IDs with spaces
        result = handle_secondary_accessions("HMDB1234 ; HMDB5678 ; HMDB9999", "7digit")
        assert result == ["HMDB0001234", "HMDB0005678", "HMDB0009999"]

        # Mixed formats
        result = handle_secondary_accessions("HMDB01234;5678;HMDB0009999", "7digit")
        assert result == ["HMDB0001234", "HMDB0005678", "HMDB0009999"]

    def test_validate_hmdb_format(self):
        """Test HMDB format validation."""
        # Valid formats
        assert validate_hmdb_format("HMDB0001234") is True
        assert validate_hmdb_format("HMDB01234") is True
        assert validate_hmdb_format("HMDB1234") is True

        # Invalid formats
        assert validate_hmdb_format("NOTHMDB1234") is False
        assert validate_hmdb_format("1234") is False
        assert validate_hmdb_format("HMDB") is False
        assert validate_hmdb_format("") is False
        assert validate_hmdb_format(None) is False
        assert validate_hmdb_format(pd.NA) is False

    def test_extract_hmdb_number(self):
        """Test extraction of numeric part from HMDB ID."""
        assert extract_hmdb_number("HMDB0001234") == 1234
        assert extract_hmdb_number("HMDB01234") == 1234
        assert extract_hmdb_number("HMDB1234") == 1234
        assert extract_hmdb_number("HMDB00000001") == 1

        # Invalid inputs
        assert extract_hmdb_number("NOT_HMDB1234") is None
        assert extract_hmdb_number("1234") is None
        assert extract_hmdb_number("HMDB") is None
        assert extract_hmdb_number("HMDBabc") is None


class TestMetaboliteNormalizeHmdbAction:
    """Test the METABOLITE_NORMALIZE_HMDB action."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return MetaboliteNormalizeHmdb()

    @pytest.fixture
    def sample_dataset(self):
        """Create sample dataset with various HMDB formats."""
        return pd.DataFrame(
            {
                "metabolite_name": [
                    "Glucose",
                    "Lactate",
                    "Pyruvate",
                    "Citrate",
                    "Alanine",
                ],
                "hmdb_id": [
                    "HMDB1234",
                    "HMDB01234",
                    "HMDB0001234",
                    "5678",
                    "HMDB:9999",
                ],
                "secondary_hmdb": [
                    "HMDB111;HMDB222",
                    None,
                    "HMDB333",
                    None,
                    "HMDB444;HMDB555;HMDB666",
                ],
                "other_id": ["CTS123", "CTS456", "CTS789", "CTS012", "CTS345"],
            }
        )

    @pytest.fixture
    def context_with_dataset(self, sample_dataset):
        """Create context with sample dataset."""
        return {"datasets": {"test_data": sample_dataset}, "statistics": {}}

    @pytest.mark.asyncio
    async def test_basic_normalization(self, action, context_with_dataset):
        """Test basic HMDB normalization."""
        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["hmdb_id"],
            target_format="7digit",
            output_key="normalized_data",
        )

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )

        assert result.output_ontology_type == "HMDB"
        assert "normalized_data" in context_with_dataset["datasets"]

        normalized_df = context_with_dataset["datasets"]["normalized_data"]

        # Check normalization results
        expected_hmdb = [
            "HMDB0001234",  # HMDB1234 -> HMDB0001234
            "HMDB0001234",  # HMDB01234 -> HMDB0001234
            "HMDB0001234",  # HMDB0001234 -> HMDB0001234
            "HMDB0005678",  # 5678 -> HMDB0005678
            "HMDB0009999",  # HMDB:9999 -> HMDB0009999
        ]

        assert normalized_df["hmdb_id"].tolist() == expected_hmdb

    @pytest.mark.asyncio
    async def test_multiple_columns_normalization(self, action, context_with_dataset):
        """Test normalizing multiple HMDB columns."""
        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["hmdb_id", "secondary_hmdb"],
            target_format="7digit",
            handle_secondary=True,
            output_key="normalized_data",
        )

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )

        assert result.output_ontology_type == "HMDB"
        normalized_df = context_with_dataset["datasets"]["normalized_data"]

        # Check primary column
        assert normalized_df["hmdb_id"][0] == "HMDB0001234"

        # Check secondary column with multiple IDs
        assert normalized_df["secondary_hmdb"][0] == "HMDB0000111;HMDB0000222"
        assert pd.isna(normalized_df["secondary_hmdb"][1])
        assert normalized_df["secondary_hmdb"][2] == "HMDB0000333"

    @pytest.mark.asyncio
    async def test_different_target_formats(self, action, context_with_dataset):
        """Test different target format options."""
        # Test 5-digit format
        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["hmdb_id"],
            target_format="5digit",
            output_key="normalized_5digit",
        )

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )
        assert result.output_ontology_type == "HMDB"

        df_5digit = context_with_dataset["datasets"]["normalized_5digit"]
        assert df_5digit["hmdb_id"][0] == "HMDB01234"

        # Test minimal format
        params.target_format = "minimal"
        params.output_key = "normalized_minimal"

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )
        assert result.output_ontology_type == "HMDB"

        df_minimal = context_with_dataset["datasets"]["normalized_minimal"]
        assert df_minimal["hmdb_id"][0] == "HMDB1234"

    @pytest.mark.asyncio
    async def test_normalization_logging(self, action, context_with_dataset):
        """Test that normalization changes are logged."""
        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["hmdb_id"],
            target_format="7digit",
            add_normalization_log=True,
            output_key="normalized_with_log",
        )

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )

        assert result.output_ontology_type == "HMDB"
        normalized_df = context_with_dataset["datasets"]["normalized_with_log"]

        # Check that log columns were added
        assert "hmdb_id_original" in normalized_df.columns
        assert "hmdb_id_normalized" in normalized_df.columns

        # Check log values
        assert normalized_df["hmdb_id_original"][0] == "HMDB1234"
        assert normalized_df["hmdb_id_normalized"][0] == True

    @pytest.mark.asyncio
    async def test_validation_mode(self, action, context_with_dataset):
        """Test format validation."""
        # Add some invalid HMDB IDs
        context_with_dataset["datasets"]["test_data"].loc[0, "hmdb_id"] = "INVALID123"
        context_with_dataset["datasets"]["test_data"].loc[1, "hmdb_id"] = ""

        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["hmdb_id"],
            target_format="7digit",
            validate_format=True,
            output_key="validated_data",
        )

        result = await action.execute_typed(
            [], "HMDB", params, None, None, context_with_dataset
        )

        assert result.output_ontology_type == "HMDB"

        # Check that statistics were recorded
        assert "hmdb_normalization" in result.details
        stats = result.details["hmdb_normalization"]
        assert stats["invalid_count"] == 2
        assert stats["valid_count"] == 3

    @pytest.mark.asyncio
    async def test_error_on_missing_column(self, action, context_with_dataset):
        """Test error handling for missing columns."""
        params = MetaboliteNormalizeHmdbParams(
            input_key="test_data",
            hmdb_columns=["nonexistent_column"],
            target_format="7digit",
            output_key="error_test",
        )

        with pytest.raises(BiomapperError) as exc_info:
            await action.execute_typed(
                [], "HMDB", params, None, None, context_with_dataset
            )

        assert "Column 'nonexistent_column' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_on_missing_dataset(self, action):
        """Test error handling for missing dataset."""
        params = MetaboliteNormalizeHmdbParams(
            input_key="missing_data",
            hmdb_columns=["hmdb_id"],
            target_format="7digit",
            output_key="error_test",
        )

        context = {"datasets": {}}

        with pytest.raises(BiomapperError) as exc_info:
            await action.execute_typed([], "HMDB", params, None, None, context)

        assert "Dataset 'missing_data' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_performance_large_dataset(self, action):
        """Test performance with large dataset (10k rows)."""
        # Create large dataset
        large_df = pd.DataFrame(
            {
                "hmdb_id": [f"HMDB{i:04d}" for i in range(10000)],
                "secondary": [
                    f"HMDB{i:05d};HMDB{i+10000:05d}" if i % 2 == 0 else None
                    for i in range(10000)
                ],
            }
        )

        context = {"datasets": {"large_data": large_df}}

        params = MetaboliteNormalizeHmdbParams(
            input_key="large_data",
            hmdb_columns=["hmdb_id", "secondary"],
            target_format="7digit",
            handle_secondary=True,
            output_key="normalized_large",
        )

        start_time = time.time()
        result = await action.execute_typed([], "HMDB", params, None, None, context)
        elapsed_time = time.time() - start_time

        assert result.output_ontology_type == "HMDB"
        assert elapsed_time < 3.0  # Should process 10k rows in under 3 seconds

        # Verify some results
        normalized_df = context["datasets"]["normalized_large"]
        assert len(normalized_df) == 10000
        assert normalized_df["hmdb_id"][0] == "HMDB0000000"
        assert normalized_df["hmdb_id"][9999] == "HMDB0009999"

    @pytest.mark.asyncio
    async def test_real_world_edge_cases(self, action):
        """Test real-world edge cases from actual data."""
        # Create dataset with real-world edge cases
        edge_cases_df = pd.DataFrame(
            {
                "hmdb_id": [
                    "HMDB00001",  # 5-digit with leading zeros
                    "HMDB0000001",  # 7-digit with leading zeros
                    "hmdb:01234",  # Lowercase with prefix
                    "HMDB_5678",  # Underscore prefix
                    "HMDB-9999",  # Dash prefix
                    "    HMDB1234  ",  # Whitespace
                    "HMDB123456",  # 6-digit
                    "HMDB12345678",  # 8-digit (should truncate or handle)
                    None,  # None value
                    pd.NA,  # Pandas NA
                    "",  # Empty string
                    "NOT_AN_HMDB",  # Invalid format
                ]
            }
        )

        context = {"datasets": {"edge_cases": edge_cases_df}}

        params = MetaboliteNormalizeHmdbParams(
            input_key="edge_cases",
            hmdb_columns=["hmdb_id"],
            target_format="7digit",
            validate_format=True,
            output_key="normalized_edges",
        )

        result = await action.execute_typed([], "HMDB", params, None, None, context)

        assert result.output_ontology_type == "HMDB"
        normalized_df = context["datasets"]["normalized_edges"]

        # Check specific normalizations
        assert normalized_df["hmdb_id"][0] == "HMDB0000001"
        assert normalized_df["hmdb_id"][1] == "HMDB0000001"
        assert normalized_df["hmdb_id"][2] == "HMDB0001234"
        assert normalized_df["hmdb_id"][3] == "HMDB0005678"
        assert normalized_df["hmdb_id"][4] == "HMDB0009999"
        assert normalized_df["hmdb_id"][5] == "HMDB0001234"
        assert normalized_df["hmdb_id"][6] == "HMDB0123456"

        # Check invalid entries
        assert pd.isna(normalized_df["hmdb_id"][8])  # None
        assert pd.isna(normalized_df["hmdb_id"][9])  # pd.NA
        assert pd.isna(normalized_df["hmdb_id"][10])  # Empty string
        assert pd.isna(normalized_df["hmdb_id"][11])  # Invalid format


class TestActionRegistration:
    """Test that action is properly registered."""

    def test_action_is_registered(self):
        """Test that METABOLITE_NORMALIZE_HMDB is registered in ACTION_REGISTRY."""
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

        assert "METABOLITE_NORMALIZE_HMDB" in ACTION_REGISTRY
        assert ACTION_REGISTRY["METABOLITE_NORMALIZE_HMDB"] == MetaboliteNormalizeHmdb

    def test_action_params_model(self):
        """Test that action returns correct params model."""
        action = MetaboliteNormalizeHmdb()
        assert action.get_params_model() == MetaboliteNormalizeHmdbParams

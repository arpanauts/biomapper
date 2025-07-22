"""Tests for LOAD_DATASET_IDENTIFIERS action."""

import pytest
from pydantic import ValidationError
from pathlib import Path
import tempfile
import os

from biomapper.core.strategy_actions.typed_base import StandardActionResult
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.core.strategy_actions.load_dataset_identifiers import (
    LoadDatasetIdentifiersParams,
    LoadDatasetIdentifiersAction,
)
from unittest.mock import MagicMock


class TestLoadDatasetIdentifiersParams:
    """Test parameter validation for LOAD_DATASET_IDENTIFIERS."""

    def test_valid_params(self):
        """Test that valid parameters are accepted."""
        params = LoadDatasetIdentifiersParams(
            file_path="/path/to/file.csv",
            identifier_column="id",
            output_key="test_output",
        )
        assert params.file_path == "/path/to/file.csv"
        assert params.identifier_column == "id"
        assert params.output_key == "test_output"
        assert params.file_type == "auto"  # default
        assert params.drop_empty_ids is True  # default
        assert params.filter_mode == "include"  # default

    def test_missing_required_params(self):
        """Test that missing required parameters raise ValidationError."""
        # Missing file_path
        with pytest.raises(ValidationError) as exc_info:
            LoadDatasetIdentifiersParams(identifier_column="id", output_key="test")
        assert "file_path" in str(exc_info.value)

        # Missing identifier_column
        with pytest.raises(ValidationError) as exc_info:
            LoadDatasetIdentifiersParams(
                file_path="/path/to/file.csv", output_key="test"
            )
        assert "identifier_column" in str(exc_info.value)

        # Missing output_key
        with pytest.raises(ValidationError) as exc_info:
            LoadDatasetIdentifiersParams(
                file_path="/path/to/file.csv", identifier_column="id"
            )
        assert "output_key" in str(exc_info.value)

    def test_invalid_file_type(self):
        """Test that invalid file_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadDatasetIdentifiersParams(
                file_path="/path/to/file.csv",
                identifier_column="id",
                output_key="test",
                file_type="invalid",
            )
        assert "file_type" in str(exc_info.value)

    def test_optional_params(self):
        """Test optional parameters."""
        params = LoadDatasetIdentifiersParams(
            file_path="/path/to/file.csv",
            identifier_column="id",
            output_key="test",
            strip_prefix="UniProtKB:",
            filter_column="source",
            filter_values=["^UniProtKB:"],
            filter_mode="exclude",
            drop_empty_ids=False,
        )
        assert params.strip_prefix == "UniProtKB:"
        assert params.filter_column == "source"
        assert params.filter_values == ["^UniProtKB:"]
        assert params.filter_mode == "exclude"
        assert params.drop_empty_ids is False


class TestLoadDatasetIdentifiersAction:
    """Test LOAD_DATASET_IDENTIFIERS action implementation."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return LoadDatasetIdentifiersAction()

    def _create_context(self):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        # Initialize datasets and metadata
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
    def temp_csv_file(self):
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name,category\n")
            f.write("P12345,Protein A,enzyme\n")
            f.write("Q67890,Protein B,receptor\n")
            f.write("P54321,Protein C,enzyme\n")
            f.write(",Protein D,unknown\n")  # Empty ID
            f.write("Q11111,Protein E,receptor\n")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_tsv_file(self):
        """Create a temporary TSV file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write("UniProt\tGeneName\tType\n")
            f.write("P12345\tGENE1\tProtein\n")
            f.write("Q67890\tGENE2\tProtein\n")
            f.write("P54321\tGENE3\tProtein\n")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_prefix_file(self):
        """Create a CSV file with prefixed identifiers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name\n")
            f.write("UniProtKB:P12345,Protein A\n")
            f.write("UniProtKB:Q67890,Protein B\n")
            f.write("P54321,Protein C\n")  # No prefix
            f.write("UniProtKB:Q11111,Protein D\n")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_load_simple_csv(self, action, temp_csv_file, mock_endpoints):
        """Test loading a basic CSV file."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file, identifier_column="id", output_key="test_data"
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        assert len(result.output_identifiers) == 4
        assert "test_data" in context.get_action_data("datasets", {})

        # Check data structure
        dataset = context.get_action_data("datasets", {})["test_data"]
        assert isinstance(dataset, list)
        assert len(dataset) == 4  # 5 original - 1 empty

        # Check columns
        first_row = dataset[0]
        assert isinstance(first_row, dict)
        assert "id" in first_row
        assert "name" in first_row
        assert "category" in first_row
        assert "_source_file" in first_row
        assert "_row_number" in first_row

        # Check metadata
        assert "test_data" in context.get_action_data("metadata", {})
        metadata = context.get_action_data("metadata", {})["test_data"]
        assert metadata["row_count"] == 4
        assert metadata["identifier_column"] == "id"
        assert metadata["source_file"] == temp_csv_file

    @pytest.mark.asyncio
    async def test_load_tsv_file(self, action, temp_tsv_file, mock_endpoints):
        """Test loading a TSV file."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_tsv_file,
            identifier_column="UniProt",
            output_key="tsv_data",
            file_type="tsv",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["tsv_data"]
        assert len(dataset) == 3
        assert dataset[0]["UniProt"] == "P12345"

    @pytest.mark.asyncio
    async def test_file_type_auto_detection(
        self, action, temp_csv_file, temp_tsv_file, mock_endpoints
    ):
        """Test automatic file type detection."""
        # CSV auto-detection
        params_csv = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file, identifier_column="id", output_key="csv_auto"
        )
        context = self._create_context()
        result = await action.execute_typed(
            [], "unknown", params_csv, mock_endpoints[0], mock_endpoints[1], context
        )
        assert isinstance(result, StandardActionResult)

        # TSV auto-detection
        params_tsv = LoadDatasetIdentifiersParams(
            file_path=temp_tsv_file, identifier_column="UniProt", output_key="tsv_auto"
        )
        result = await action.execute_typed(
            [], "unknown", params_tsv, mock_endpoints[0], mock_endpoints[1], context
        )
        assert isinstance(result, StandardActionResult)

    @pytest.mark.asyncio
    async def test_strip_prefix(self, action, temp_prefix_file, mock_endpoints):
        """Test prefix removal with original preservation."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_prefix_file,
            identifier_column="id",
            strip_prefix="UniProtKB:",
            output_key="stripped_data",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["stripped_data"]

        # Check stripped values
        assert dataset[0]["id"] == "P12345"
        assert dataset[1]["id"] == "Q67890"
        assert dataset[2]["id"] == "P54321"  # No prefix originally

        # Check original preservation
        assert dataset[0]["id_original"] == "UniProtKB:P12345"
        assert dataset[1]["id_original"] == "UniProtKB:Q67890"
        assert dataset[2]["id_original"] == "P54321"

        # Check metadata
        assert (
            context.get_action_data("metadata", {})["stripped_data"]["prefix_stripped"]
            is True
        )

    @pytest.mark.asyncio
    async def test_filter_include_mode(self, action, temp_csv_file, mock_endpoints):
        """Test filtering rows to include matches."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file,
            identifier_column="id",
            filter_column="category",
            filter_values=["enzyme"],
            filter_mode="include",
            output_key="filtered_data",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["filtered_data"]
        assert len(dataset) == 2  # Only enzymes

        for row in dataset:
            assert row["category"] == "enzyme"

        # Check filter stats
        filter_stats = context.get_action_data("metadata", {})["filtered_data"][
            "filter_stats"
        ]
        assert filter_stats["original_count"] == 5
        assert filter_stats["filtered_count"] == 2

    @pytest.mark.asyncio
    async def test_filter_exclude_mode(self, action, temp_csv_file, mock_endpoints):
        """Test filtering rows to exclude matches."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file,
            identifier_column="id",
            filter_column="category",
            filter_values=["enzyme"],
            filter_mode="exclude",
            output_key="filtered_data",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["filtered_data"]
        assert len(dataset) == 2  # receptor + unknown (empty ID removed)

        for row in dataset:
            assert row["category"] != "enzyme"

    @pytest.mark.asyncio
    async def test_filter_regex_pattern(self, action, temp_prefix_file, mock_endpoints):
        """Test regex pattern matching."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_prefix_file,
            identifier_column="id",
            filter_column="id",
            filter_values=["^UniProtKB:"],  # Starts with
            filter_mode="include",
            output_key="regex_filtered",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["regex_filtered"]
        assert len(dataset) == 3  # Only those starting with UniProtKB:

    @pytest.mark.asyncio
    async def test_drop_empty_ids_true(self, action, temp_csv_file, mock_endpoints):
        """Test removal of rows with empty identifier column."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file,
            identifier_column="id",
            output_key="no_empty",
            drop_empty_ids=True,  # Default
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["no_empty"]
        assert len(dataset) == 4  # 5 - 1 empty

        # Verify no empty IDs
        for row in dataset:
            assert row["id"] != ""
            assert row["id"] is not None

    @pytest.mark.asyncio
    async def test_keep_empty_ids(self, action, temp_csv_file, mock_endpoints):
        """Test keeping rows when drop_empty_ids=False."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file,
            identifier_column="id",
            output_key="with_empty",
            drop_empty_ids=False,
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["with_empty"]
        assert len(dataset) == 5  # All rows kept

    @pytest.mark.asyncio
    async def test_missing_identifier_column(
        self, action, temp_csv_file, mock_endpoints
    ):
        """Test error when specified column doesn't exist."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file,
            identifier_column="missing_column",
            output_key="error_test",
        )
        context = self._create_context()

        with pytest.raises(ValueError) as exc_info:
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

        error_msg = str(exc_info.value)
        assert "missing_column" in error_msg
        assert "not found" in error_msg.lower()
        assert "available" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_empty_file(self, action, mock_endpoints):
        """Test handling of empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name\n")  # Header only
            temp_path = f.name

        try:
            params = LoadDatasetIdentifiersParams(
                file_path=temp_path, identifier_column="id", output_key="empty_test"
            )
            context = self._create_context()

            result = await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

            assert isinstance(result, StandardActionResult)
            dataset = context.get_action_data("datasets", {})["empty_test"]
            assert len(dataset) == 0
            assert (
                context.get_action_data("metadata", {})["empty_test"]["row_count"] == 0
            )
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_file_not_found(self, action, mock_endpoints):
        """Test handling of missing file."""
        params = LoadDatasetIdentifiersParams(
            file_path="/nonexistent/file.csv",
            identifier_column="id",
            output_key="missing_file",
        )
        context = self._create_context()

        with pytest.raises(FileNotFoundError):
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )

    @pytest.mark.asyncio
    async def test_metadata_columns_added(self, action, temp_csv_file, mock_endpoints):
        """Test that metadata columns are added correctly."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_csv_file, identifier_column="id", output_key="metadata_test"
        )
        context = self._create_context()

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        dataset = context.get_action_data("datasets", {})["metadata_test"]

        # Check _source_file
        for row in dataset:
            assert row["_source_file"] == temp_csv_file

        # Check _row_number (1-based)
        assert dataset[0]["_row_number"] == 2  # First data row (after header)
        assert dataset[1]["_row_number"] == 3
        assert dataset[2]["_row_number"] == 4
        assert dataset[3]["_row_number"] == 6  # Row 5 was empty ID

    @pytest.mark.asyncio
    async def test_complex_filtering_and_stripping(
        self, action, temp_prefix_file, mock_endpoints
    ):
        """Test combination of filtering and prefix stripping."""
        params = LoadDatasetIdentifiersParams(
            file_path=temp_prefix_file,
            identifier_column="id",
            strip_prefix="UniProtKB:",
            filter_column="id",
            filter_values=["^UniProtKB:"],
            filter_mode="include",
            output_key="complex_test",
        )
        context = self._create_context()

        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        dataset = context.get_action_data("datasets", {})["complex_test"]
        assert len(dataset) == 3  # Only UniProtKB entries

        # Check both filtering and stripping worked
        for row in dataset:
            assert not row["id"].startswith("UniProtKB:")  # Stripped
            assert row["id_original"].startswith("UniProtKB:")  # Original preserved


class TestRealData:
    """Test with real biological data files."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return LoadDatasetIdentifiersAction()

    def _create_context(self):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        # Initialize datasets and metadata
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
    async def test_load_ukbb_real_data(self, action, mock_endpoints):
        """Test with actual UKBB data structure."""
        ukbb_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/ukbb/UKBB_Protein_Meta.tsv"

        if not Path(ukbb_file).exists():
            pytest.skip(f"Test data not found: {ukbb_file}")

        params = LoadDatasetIdentifiersParams(
            file_path=ukbb_file,
            identifier_column="UniProt",
            output_key="ukbb_proteins",
            file_type="tsv",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["ukbb_proteins"]
        assert len(dataset) > 0

        # Check UKBB-specific columns exist
        first_row = dataset[0]
        assert "UniProt" in first_row
        assert first_row["UniProt"]  # Not empty

    @pytest.mark.asyncio
    async def test_load_hpa_real_data(self, action, mock_endpoints):
        """Test with HPA OSP data."""
        hpa_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/isb_osp/hpa_osps.csv"

        if not Path(hpa_file).exists():
            pytest.skip(f"Test data not found: {hpa_file}")

        params = LoadDatasetIdentifiersParams(
            file_path=hpa_file,
            identifier_column="uniprot",  # Using correct column name
            output_key="hpa_data",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["hpa_data"]
        assert len(dataset) > 0

    @pytest.mark.asyncio
    async def test_load_kg2c_with_filtering(self, action, mock_endpoints):
        """Test KG2C loading with prefix strip and filter."""
        kg2c_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/kg2c_ontologies/test_uniprot_nodes.csv"

        if not Path(kg2c_file).exists():
            pytest.skip(f"Test data not found: {kg2c_file}")

        params = LoadDatasetIdentifiersParams(
            file_path=kg2c_file,
            identifier_column="id",
            strip_prefix="UniProtKB:",
            filter_column="id",
            filter_values=["^UniProtKB:"],
            filter_mode="include",
            output_key="kg2c_proteins",
        )
        context = self._create_context()

        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )

        assert isinstance(result, StandardActionResult)
        dataset = context.get_action_data("datasets", {})["kg2c_proteins"]

        # Should have filtered to only UniProtKB entries
        assert len(dataset) > 0

        # Check stripping worked
        for row in dataset:
            assert not row["id"].startswith("UniProtKB:")
            assert "id_original" in row

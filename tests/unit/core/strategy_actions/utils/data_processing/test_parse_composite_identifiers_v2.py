"""Test suite for ParseCompositeIdentifiersAction - WRITE THIS FIRST!"""

import pytest
from typing import Dict, Any
import pandas as pd

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.utils.data_processing.parse_composite_identifiers_v2 import (
    ParseCompositeIdentifiersAction,
    ParseCompositeIdentifiersParams,
)


class TestParseCompositeIdentifiersAction:
    """Comprehensive test suite for composite identifier parsing."""

    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Create sample context with composite identifiers."""
        return {
            "datasets": {
                "proteins": [
                    {"uniprot": "P12345", "name": "Protein1", "value": 1.5},
                    {"uniprot": "Q67890,Q11111", "name": "Protein2", "value": 2.0},
                    {
                        "uniprot": "A12345;B67890;C99999",
                        "name": "Protein3",
                        "value": 3.0,
                    },
                    {"uniprot": "D55555|E66666", "name": "Protein4", "value": 4.0},
                    {"uniprot": "F77777", "name": "Protein5", "value": 5.0},
                    {"uniprot": "", "name": "Empty", "value": 0.0},
                    {"uniprot": None, "name": "Null", "value": -1.0},
                ]
            },
            "statistics": {},
            "output_files": {},
        }

    @pytest.fixture
    def action(self) -> ParseCompositeIdentifiersAction:
        """Create action instance."""
        return ParseCompositeIdentifiersAction()

    @pytest.mark.asyncio
    async def test_basic_comma_separation(self, action, sample_context):
        """Test parsing comma-separated identifiers."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_expanded",
            track_expansion=True,
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success is True
        assert "proteins_expanded" in sample_context["datasets"]

        expanded = sample_context["datasets"]["proteins_expanded"]

        # Check Q67890,Q11111 was expanded to 2 rows
        q_rows = [r for r in expanded if r["uniprot"] in ["Q67890", "Q11111"]]
        assert len(q_rows) == 2

        # Both rows should preserve other fields
        for row in q_rows:
            assert row["name"] == "Protein2"
            assert row["value"] == 2.0
            assert row.get("_original_composite") == "Q67890,Q11111"
            assert row.get("_expansion_count") == 2

    @pytest.mark.asyncio
    async def test_multiple_separators(self, action, sample_context):
        """Test handling multiple separator types."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[",", ";", "|"],
            output_key="proteins_multi_sep",
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success is True
        expanded = sample_context["datasets"]["proteins_multi_sep"]

        # Count total rows (should expand all composite IDs)
        # P12345 (1) + Q67890,Q11111 (2) + A12345;B67890;C99999 (3) + D55555|E66666 (2) + F77777 (1) + "" (1) + None (1) = 11
        assert len(expanded) == 11

        # Check semicolon separation
        semicolon_rows = [
            r
            for r in expanded
            if r.get("_original_composite") == "A12345;B67890;C99999"
        ]
        assert len(semicolon_rows) == 3
        assert set(r["uniprot"] for r in semicolon_rows) == {
            "A12345",
            "B67890",
            "C99999",
        }

        # Check pipe separation
        pipe_rows = [
            r for r in expanded if r.get("_original_composite") == "D55555|E66666"
        ]
        assert len(pipe_rows) == 2

    @pytest.mark.asyncio
    async def test_empty_and_null_handling(self, action, sample_context):
        """Test proper handling of empty and null values."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_clean",
            skip_empty=True,
        )

        await action.execute_typed(params, sample_context)

        expanded = sample_context["datasets"]["proteins_clean"]

        # Should skip empty and None values
        assert all(r["uniprot"] for r in expanded if r["name"] not in ["Empty", "Null"])

        # Empty/Null rows should be preserved but marked
        empty_rows = [r for r in expanded if r["name"] in ["Empty", "Null"]]
        assert len(empty_rows) == 2
        for row in empty_rows:
            assert row.get("_skipped", False) is True

    @pytest.mark.asyncio
    async def test_expansion_statistics(self, action, sample_context):
        """Test that expansion statistics are tracked correctly."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[",", ";", "|"],
            output_key="proteins_stats",
            track_expansion=True,
        )

        result = await action.execute_typed(params, sample_context)

        # Check statistics were recorded
        assert "composite_expansion" in sample_context["statistics"]
        stats = sample_context["statistics"]["composite_expansion"]

        assert stats["total_input_rows"] == 7
        assert stats["total_output_rows"] == 11
        assert stats["expansion_factor"] == pytest.approx(11 / 7, rel=0.01)
        assert stats["rows_with_composites"] == 3
        assert stats["max_components"] == 3  # A12345;B67890;C99999

        # Check result object
        assert result.rows_processed == 7
        assert result.rows_expanded == 11
        assert result.composite_count == 3

    @pytest.mark.asyncio
    async def test_custom_separator_with_trim(self, action, sample_context):
        """Test custom separator with whitespace trimming."""
        # Add data with spaces
        sample_context["datasets"]["spaced"] = [
            {"ids": "A123 , B456 , C789", "type": "test"}
        ]

        params = ParseCompositeIdentifiersParams(
            dataset_key="spaced",
            id_field="ids",
            separators=[","],
            output_key="spaced_clean",
            trim_whitespace=True,
        )

        await action.execute_typed(params, sample_context)

        expanded = sample_context["datasets"]["spaced_clean"]
        assert len(expanded) == 3
        assert expanded[0]["ids"] == "A123"  # Trimmed
        assert expanded[1]["ids"] == "B456"  # Trimmed
        assert expanded[2]["ids"] == "C789"  # Trimmed

    @pytest.mark.asyncio
    async def test_preserve_row_order(self, action, sample_context):
        """Test that row order and indices are preserved."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_ordered",
            preserve_order=True,
        )

        await action.execute_typed(params, sample_context)

        expanded = sample_context["datasets"]["proteins_ordered"]

        # Check that original row indices are preserved
        for row in expanded:
            if "_original_index" in row:
                # Pandas might convert to float, so check if it's numeric and not NaN
                index_val = row["_original_index"]
                if pd.notna(index_val):  # Only check non-NaN values
                    assert isinstance(index_val, (int, float))
                    assert 0 <= index_val < 7

    @pytest.mark.asyncio
    async def test_error_handling(self, action):
        """Test error handling for invalid inputs."""
        # Test missing dataset
        context = {"datasets": {}}
        params = ParseCompositeIdentifiersParams(
            dataset_key="nonexistent", id_field="id", output_key="output"
        )

        result = await action.execute_typed(params, context)

        assert result.success is False
        assert "not found" in result.message.lower()

        # Test missing field
        context = {"datasets": {"data": [{"other": "value"}]}}
        params = ParseCompositeIdentifiersParams(
            dataset_key="data", id_field="missing_field", output_key="output"
        )

        result = await action.execute_typed(params, context)

        assert result.success is False
        assert "field" in result.message.lower()

    @pytest.mark.asyncio
    async def test_context_compatibility(self, action):
        """Test handling of different context types."""
        # Test with dict context
        dict_context = {"datasets": {"test": [{"id": "A,B"}]}, "statistics": {}}

        params = ParseCompositeIdentifiersParams(
            dataset_key="test", id_field="id", output_key="expanded"
        )

        result = await action.execute_typed(params, dict_context)
        assert result.success is True

        # Test with MockContext (create a simple version for testing)
        class MockContext:
            def __init__(self, data):
                self._dict = data

        mock_context = MockContext(dict_context)

        result = await action.execute_typed(params, mock_context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action):
        """Test performance with larger dataset."""
        # Create dataset with 1000 rows, 30% having composite IDs
        import random

        large_data = []
        for i in range(1000):
            if random.random() < 0.3:
                # Composite ID
                num_components = random.randint(2, 5)
                ids = ",".join(f"ID{i}_{j}" for j in range(num_components))
            else:
                # Single ID
                ids = f"ID{i}"
            large_data.append({"identifier": ids, "value": i})

        context = {"datasets": {"large": large_data}, "statistics": {}}

        params = ParseCompositeIdentifiersParams(
            dataset_key="large",
            id_field="identifier",
            separators=[","],
            output_key="large_expanded",
            track_expansion=True,
        )

        import time

        start = time.time()
        result = await action.execute_typed(params, context)
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 1.0  # Should process 1000 rows in under 1 second

        # Verify expansion worked
        expanded = context["datasets"]["large_expanded"]
        assert len(expanded) > 1000  # Should have expanded some rows

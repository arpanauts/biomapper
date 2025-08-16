"""
Tests for PARSE_COMPOSITE_IDENTIFIERS action.

This module tests the parsing of composite identifiers (e.g., "P12345,Q67890")
into individual components with various separator patterns and configurations.
"""

import pytest

# Mark entire module as requiring external services (advanced parsing)
pytestmark = pytest.mark.requires_external_services

from biomapper.core.strategy_actions.utils.data_processing.parse_composite_identifiers_v2 import (
    ParseCompositeIdentifiersAction,
    ParseCompositeIdentifiersParams,
    CompositePattern,
    parse_composite_string,
    expand_dataset_rows,
)


class TestParseCompositeString:
    """Test the parse_composite_string utility function."""

    def test_single_identifier(self):
        """Single identifiers should pass through unchanged."""
        assert parse_composite_string("P12345") == ["P12345"]
        assert parse_composite_string("ENSG001") == ["ENSG001"]

    def test_comma_separated(self):
        """Test comma-separated identifiers."""
        assert parse_composite_string("P12345,Q67890") == ["P12345", "Q67890"]
        assert parse_composite_string("A,B,C") == ["A", "B", "C"]

    def test_pipe_separated(self):
        """Test pipe-separated identifiers."""
        assert parse_composite_string("ENSG001|ENSG002", separators=["|"]) == [
            "ENSG001",
            "ENSG002",
        ]

    def test_semicolon_separated(self):
        """Test semicolon-separated identifiers."""
        assert parse_composite_string("ID1;ID2;ID3", separators=[";"]) == [
            "ID1",
            "ID2",
            "ID3",
        ]

    def test_mixed_separators(self):
        """Test handling of mixed separators with multiple patterns."""
        # Should split on first matching separator
        assert parse_composite_string(
            "P12345,Q67890|A12345", separators=[",", "|"]
        ) == ["P12345", "Q67890|A12345"]
        # If we want to split on both, need to handle differently
        assert parse_composite_string("P12345,Q67890", separators=[",", "|"]) == [
            "P12345",
            "Q67890",
        ]

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert parse_composite_string("P12345 , Q67890") == ["P12345", "Q67890"]
        assert parse_composite_string(" A , B , C ") == ["A", "B", "C"]

    def test_empty_values(self):
        """Test handling of empty values."""
        assert parse_composite_string("") == []
        assert parse_composite_string(None) == []
        assert parse_composite_string("P12345,,Q67890") == [
            "P12345",
            "Q67890",
        ]  # Empty values removed

    def test_no_separator_found(self):
        """Test when no separator is found."""
        assert parse_composite_string("P12345", separators=["|", ";"]) == ["P12345"]


class TestExpandDatasetRows:
    """Test the expand_dataset_rows utility function."""

    def test_expand_simple_dataset(self):
        """Test expanding rows with composite identifiers."""
        data = [{"uniprot": "P1,P2", "gene": "G1"}, {"uniprot": "P3", "gene": "G2"}]

        result = expand_dataset_rows(data, "uniprot")

        assert len(result) == 3
        assert result[0] == {
            "uniprot": "P1",
            "gene": "G1",
            "_original_uniprot": "P1,P2",
            "_parsed_ids": ["P1", "P2"],
        }
        assert result[1] == {
            "uniprot": "P2",
            "gene": "G1",
            "_original_uniprot": "P1,P2",
            "_parsed_ids": ["P1", "P2"],
        }
        assert result[2] == {
            "uniprot": "P3",
            "gene": "G2",
            "_original_uniprot": "P3",
            "_parsed_ids": ["P3"],
        }

    def test_expand_with_empty_values(self):
        """Test handling of empty/null values during expansion."""
        data = [
            {"uniprot": "", "gene": "G1"},
            {"uniprot": None, "gene": "G2"},
            {"uniprot": "P1", "gene": "G3"},
        ]

        result = expand_dataset_rows(data, "uniprot")

        # Empty/null values should be preserved but not expanded
        assert len(result) == 3
        assert result[2]["uniprot"] == "P1"

    def test_expand_multiple_composites(self):
        """Test expanding multiple composite fields."""
        data = [
            {"uniprot": "P1,P2,P3", "gene": "G1"},
            {"uniprot": "P4,P5", "gene": "G2"},
        ]

        result = expand_dataset_rows(data, "uniprot")

        assert len(result) == 5
        # Check that all original data is preserved
        for row in result[:3]:
            assert row["gene"] == "G1"
            assert row["_original_uniprot"] == "P1,P2,P3"
        for row in result[3:]:
            assert row["gene"] == "G2"
            assert row["_original_uniprot"] == "P4,P5"


@pytest.mark.asyncio
class TestParseCompositeIdentifiersAction:
    """Test the main PARSE_COMPOSITE_IDENTIFIERS action."""

    async def test_basic_comma_split(self):
        """Test basic comma-separated splitting."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {
                "test_data": [
                    {"id": "P12345", "name": "Protein1"},
                    {"id": "Q8NEV9,Q14213", "name": "Protein2"},
                    {"id": "A12345", "name": "Protein3"},
                ]
            },
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="id",
            patterns=[CompositePattern(separator=",", trim_whitespace=True)],
            output_format="flat",
            output_context_key="parsed_data",
            preserve_original=True,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        assert "parsed_data" in context["datasets"]
        parsed = context["datasets"]["parsed_data"]

        # Should have 4 rows after expansion (1 + 2 + 1)
        assert len(parsed) == 4

        # Check statistics
        stats = context["statistics"]["composite_tracking"]
        assert stats["total_input"] == 3
        assert stats["composite_count"] == 1
        assert stats["individual_count"] == 4
        assert stats["patterns_used"][","] == 1

    async def test_pipe_separated_identifiers(self):
        """Test pipe-separated identifier parsing."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {
                "test_data": [
                    {"xrefs": "UniProtKB:P12345|RefSeq:NP_001234"},
                    {"xrefs": "UniProtKB:Q67890"},
                ]
            },
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="xrefs",
            patterns=[CompositePattern(separator="|", trim_whitespace=True)],
            output_format="flat",
            output_context_key="parsed_xrefs",
            preserve_original=False,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        parsed = context["datasets"]["parsed_xrefs"]
        assert len(parsed) == 3  # 2 from first row, 1 from second

    async def test_multiple_patterns(self):
        """Test applying multiple splitting patterns."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {"test_data": [{"ids": "A,B|C"}, {"ids": "D;E"}]},
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="ids",
            patterns=[
                CompositePattern(separator=","),
                CompositePattern(separator="|"),
                CompositePattern(separator=";"),
            ],
            output_format="flat",
            output_context_key="all_ids",
            preserve_original=False,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        parsed = context["datasets"]["all_ids"]
        # Should handle all separators
        assert len(parsed) >= 3  # At least A, B|C from first, D, E from second

    async def test_preserve_original_option(self):
        """Test preserving original composite IDs."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {"test_data": [{"uniprot": "P12345,Q67890"}]},
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="uniprot",
            patterns=[CompositePattern(separator=",")],
            output_format="flat",
            output_context_key="with_original",
            preserve_original=True,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        parsed = context["datasets"]["with_original"]
        # Check that original is preserved
        assert any(row.get("_original_uniprot") == "P12345,Q67890" for row in parsed)

    async def test_validation_of_uniprot_format(self):
        """Test validation of UniProt accession format."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {"test_data": [{"uniprot": "P12345,INVALID,Q67890"}]},
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="uniprot",
            patterns=[CompositePattern(separator=",")],
            output_format="flat",
            output_context_key="validated",
            preserve_original=False,
            validate_format=True,
            entity_type="uniprot",
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        parsed = context["datasets"]["validated"]
        # Invalid ID should be filtered out
        assert len(parsed) == 2
        assert all(row["uniprot"] in ["P12345", "Q67890"] for row in parsed)

    async def test_error_handling(self):
        """Test error handling for missing data."""
        action = ParseCompositeIdentifiersAction()
        context = {"datasets": {}, "statistics": {}}

        params = ParseCompositeIdentifiersParams(
            input_context_key="missing_data", id_field="id", output_context_key="output"
        )

        with pytest.raises(KeyError):
            await action.execute_typed([], "", params, None, None, context)

    async def test_statistics_tracking(self):
        """Test comprehensive statistics tracking."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {
                "test_data": [
                    {"id": "A,B,C"},
                    {"id": "D"},
                    {"id": "E,F"},
                    {"id": "G,H,I,J"},
                ]
            },
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="id",
            patterns=[CompositePattern(separator=",")],
            output_format="flat",
            output_context_key="expanded",
            preserve_original=False,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        stats = context["statistics"]["composite_tracking"]
        assert stats["total_input"] == 4
        assert stats["composite_count"] == 3  # Three composite IDs
        assert stats["individual_count"] == 10  # Total individual IDs
        assert stats["expansion_factor"] == 2.5  # 10/4
        assert stats["patterns_used"][","] == 3

    async def test_handling_whitespace_in_composites(self):
        """Test proper whitespace handling in composite IDs."""
        action = ParseCompositeIdentifiersAction()
        context = {
            "datasets": {
                "test_data": [{"protein": " P12345 , Q67890 "}, {"protein": "A12345"}]
            },
            "statistics": {},
        }

        params = ParseCompositeIdentifiersParams(
            input_context_key="test_data",
            id_field="protein",
            patterns=[CompositePattern(separator=",", trim_whitespace=True)],
            output_format="flat",
            output_context_key="cleaned",
            preserve_original=False,
        )

        result = await action.execute_typed([], "", params, None, None, context)

        assert result.success
        parsed = context["datasets"]["cleaned"]
        # Whitespace should be trimmed
        assert parsed[0]["protein"] == "P12345"
        assert parsed[1]["protein"] == "Q67890"
        assert parsed[2]["protein"] == "A12345"


@pytest.mark.asyncio
class TestIntegrationWithMockContext:
    """Test integration with MockContext from the framework."""

    async def test_mock_context_compatibility(self):
        """Test that the action works with MockContext."""

        # MockContext is defined inline in typed_base.py, so we'll create a simple version here
        class MockContext:
            def __init__(self):
                self._dict = {"datasets": {}, "statistics": {}}

            def __getitem__(self, key):
                return self._dict[key]

            def __setitem__(self, key, value):
                self._dict[key] = value

        action = ParseCompositeIdentifiersAction()
        mock_context = MockContext()
        mock_context["datasets"] = {"proteins": [{"uniprot": "P1,P2", "gene": "GENE1"}]}

        params = ParseCompositeIdentifiersParams(
            input_context_key="proteins",
            id_field="uniprot",
            patterns=[CompositePattern(separator=",")],
            output_context_key="expanded_proteins",
        )

        result = await action.execute_typed([], "", params, None, None, mock_context)

        assert result.success
        assert "expanded_proteins" in mock_context["datasets"]

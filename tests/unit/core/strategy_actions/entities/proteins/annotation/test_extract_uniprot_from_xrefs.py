"""
Test module for PROTEIN_EXTRACT_UNIPROT_FROM_XREFS action.

This module follows strict TDD principles - all tests were written BEFORE implementation.
"""

import pandas as pd
import pytest

# These imports will fail initially - that's expected in TDD
from biomapper.core.strategy_actions.entities.proteins.annotation.extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction,
    ExtractUniProtFromXrefsParams,
    ExtractUniProtFromXrefsResult,
)


class TestExtractUniProtFromXrefsParams:
    """Test parameter validation for the action."""

    def test_default_parameters(self):
        """Test that default parameters are set correctly."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="test_proteins", xrefs_column="xrefs"
        )
        assert params.dataset_key == "test_proteins"
        assert params.xrefs_column == "xrefs"
        assert params.output_column == "uniprot_id"
        assert params.handle_multiple == "list"
        assert params.keep_isoforms is False
        assert params.drop_na is True

    def test_custom_parameters(self):
        """Test custom parameter values."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="proteins",
            xrefs_column="external_refs",
            output_column="uniprot_accession",
            handle_multiple="expand_rows",
            keep_isoforms=True,
            drop_na=False,
        )
        assert params.dataset_key == "proteins"
        assert params.xrefs_column == "external_refs"
        assert params.output_column == "uniprot_accession"
        assert params.handle_multiple == "expand_rows"
        assert params.keep_isoforms is True
        assert params.drop_na is False

    def test_invalid_handle_multiple(self):
        """Test that invalid handle_multiple values raise ValidationError."""
        with pytest.raises(ValueError):
            ExtractUniProtFromXrefsParams(
                dataset_key="test",
                xrefs_column="xrefs",
                handle_multiple="invalid_option",
            )


class TestProteinExtractUniProtFromXrefsAction:
    """Test the main action functionality."""

    @pytest.fixture
    def action(self):
        """Create action instance for testing."""
        return ProteinExtractUniProtFromXrefsAction()

    @pytest.fixture
    def sample_data_basic(self):
        """Sample data with basic UniProt xrefs."""
        return pd.DataFrame(
            {
                "protein_id": ["PROT001", "PROT002", "PROT003"],
                "xrefs": [
                    "UniProtKB:P12345",
                    "UniProtKB:Q14213|RefSeq:NP_001234",
                    "RefSeq:NP_005678|KEGG:K12345",
                ],
                "name": ["Protein A", "Protein B", "Protein C"],
            }
        )

    @pytest.fixture
    def sample_data_complex(self):
        """Sample data with complex xrefs patterns."""
        return pd.DataFrame(
            {
                "protein_id": ["PROT001", "PROT002", "PROT003", "PROT004", "PROT005"],
                "xrefs": [
                    "UniProtKB:P12345|UniProtKB:Q14213|RefSeq:NP_001",
                    "UniProtKB:P00750-1|RefSeq:NP_000421.1",
                    "RefSeq:NP_005678|KEGG:K12345",
                    "",
                    "UniProtKB:invalid_format|UniProtKB:P98765",
                ],
                "name": [
                    "Multi UniProt",
                    "Isoform",
                    "No UniProt",
                    "Empty",
                    "Mixed Valid/Invalid",
                ],
            }
        )

    @pytest.fixture
    def context_basic(self, sample_data_basic):
        """Basic execution context."""
        return {
            "datasets": {"test_proteins": sample_data_basic},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

    @pytest.fixture
    def context_complex(self, sample_data_complex):
        """Complex execution context."""
        return {
            "datasets": {"complex_proteins": sample_data_complex},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

    # Test 1: Basic extraction - Single UniProt ID from xrefs
    def test_basic_single_uniprot_extraction(self, action, context_basic):
        """Test basic extraction of single UniProt IDs from xrefs."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="test_proteins",
            xrefs_column="xrefs",
            drop_na=False,  # Keep all rows for this test
        )

        result = action.execute_typed(params, context_basic)

        # Check result structure
        assert isinstance(result, ExtractUniProtFromXrefsResult)
        assert result.success is True
        assert "test_proteins" in result.data

        # Check extracted UniProt IDs
        df = result.data["test_proteins"]
        assert "uniprot_id" in df.columns
        assert df.loc[0, "uniprot_id"] == ["P12345"]
        assert df.loc[1, "uniprot_id"] == ["Q14213"]
        assert len(df.loc[2, "uniprot_id"]) == 0  # No UniProt in third row

    # Test 2: Multiple IDs - Multiple UniProt IDs in one xrefs field
    def test_multiple_uniprot_ids_list_mode(self, action, context_complex):
        """Test extraction of multiple UniProt IDs in list mode."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", handle_multiple="list"
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # First row has multiple UniProt IDs
        assert df.loc[0, "uniprot_id"] == ["P12345", "Q14213"]
        assert df.loc[1, "uniprot_id"] == ["P00750"]  # Isoform removed by default
        assert df.loc[4, "uniprot_id"] == ["P98765"]  # Only valid ID extracted

    def test_multiple_uniprot_ids_first_mode(self, action, context_complex):
        """Test extraction taking only first UniProt ID."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins",
            xrefs_column="xrefs",
            handle_multiple="first",
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # Should take only first valid UniProt ID
        assert df.loc[0, "uniprot_id"] == "P12345"
        assert df.loc[1, "uniprot_id"] == "P00750"
        assert df.loc[4, "uniprot_id"] == "P98765"

    def test_multiple_uniprot_ids_expand_rows_mode(self, action, context_complex):
        """Test extraction expanding multiple IDs into separate rows."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins",
            xrefs_column="xrefs",
            handle_multiple="expand_rows",
            drop_na=False,  # Keep rows without UniProt IDs for this test
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # Should have more rows due to expansion
        original_rows = 5
        expanded_rows = len(df)
        assert expanded_rows > original_rows

        # Check that first protein expanded into 2 rows
        first_protein_rows = df[df["protein_id"] == "PROT001"]
        assert len(first_protein_rows) == 2
        uniprot_ids = set(first_protein_rows["uniprot_id"].tolist())
        assert uniprot_ids == {"P12345", "Q14213"}

    # Test 3: Isoforms - Handling P12345-1 format
    def test_isoform_handling_keep_false(self, action, context_complex):
        """Test isoform handling when keep_isoforms=False."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", keep_isoforms=False
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # Isoform should be stripped
        assert df.loc[1, "uniprot_id"] == ["P00750"]

    def test_isoform_handling_keep_true(self, action, context_complex):
        """Test isoform handling when keep_isoforms=True."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", keep_isoforms=True
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # Isoform should be kept
        assert df.loc[1, "uniprot_id"] == ["P00750-1"]

    # Test 4: Mixed xrefs - UniProt mixed with other ID types
    def test_mixed_xrefs_extraction(self, action, context_basic):
        """Test extraction from xrefs containing mixed ID types."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="test_proteins",
            xrefs_column="xrefs",
            drop_na=False,  # Keep all rows for this test
        )

        result = action.execute_typed(params, context_basic)
        df = result.data["test_proteins"]

        # Should only extract UniProt IDs, ignoring RefSeq and KEGG
        assert df.loc[0, "uniprot_id"] == ["P12345"]
        assert df.loc[1, "uniprot_id"] == ["Q14213"]  # RefSeq ignored
        assert len(df.loc[2, "uniprot_id"]) == 0  # No UniProt IDs

    # Test 5: Edge cases - Empty xrefs, malformed patterns
    def test_empty_xrefs_handling(self, action, context_complex):
        """Test handling of empty xrefs."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", drop_na=False
        )

        result = action.execute_typed(params, context_complex)
        df = result.data["complex_proteins"]

        # Empty xrefs should result in empty list
        assert len(df.loc[3, "uniprot_id"]) == 0

    def test_drop_na_functionality(self, action, sample_data_complex):
        """Test drop_na parameter functionality."""
        # Create separate contexts to avoid modification conflicts
        context_drop = {
            "datasets": {"complex_proteins": sample_data_complex.copy()},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

        context_keep = {
            "datasets": {"complex_proteins": sample_data_complex.copy()},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

        params_drop = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", drop_na=True
        )

        params_keep = ExtractUniProtFromXrefsParams(
            dataset_key="complex_proteins", xrefs_column="xrefs", drop_na=False
        )

        result_drop = action.execute_typed(params_drop, context_drop)
        result_keep = action.execute_typed(params_keep, context_keep)

        # With drop_na=True, should have fewer rows
        assert len(result_drop.data["complex_proteins"]) < len(
            result_keep.data["complex_proteins"]
        )

    def test_malformed_uniprot_patterns(self, action):
        """Test handling of malformed UniProt patterns."""
        malformed_data = pd.DataFrame(
            {
                "protein_id": ["PROT001", "PROT002", "PROT003"],
                "xrefs": [
                    "UniProtKB:",  # Empty after colon
                    "UniProtKB:123",  # Too short
                    "UniProtKB:P12345TOOLONG123",  # Too long
                ],
            }
        )

        context = {
            "datasets": {"malformed_proteins": malformed_data},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

        params = ExtractUniProtFromXrefsParams(
            dataset_key="malformed_proteins", xrefs_column="xrefs"
        )

        result = action.execute_typed(params, context)
        df = result.data["malformed_proteins"]

        # All malformed patterns should result in empty lists
        for idx in range(len(df)):
            assert len(df.loc[idx, "uniprot_id"]) == 0

    # Test 6: Real data patterns based on KG2c
    def test_real_kg2c_patterns(self, action):
        """Test with realistic KG2c protein data patterns."""
        kg2c_like_data = pd.DataFrame(
            {
                "id": ["UniProtKB:P12345", "UniProtKB:Q14213", "UniProtKB:P00750"],
                "xrefs": [
                    "RefSeq:NP_000001.1|HGNC:1234|Ensembl:ENSG00000123456",
                    "UniProtKB:Q14213|RefSeq:NP_000002.1|HGNC:5678",
                    "UniProtKB:P00750-1|UniProtKB:P00750-2|RefSeq:NP_000421.1",
                ],
                "name": ["Protein Alpha", "Protein Beta", "Protein Gamma"],
            }
        )

        context = {
            "datasets": {"kg2c_proteins": kg2c_like_data},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

        params = ExtractUniProtFromXrefsParams(
            dataset_key="kg2c_proteins",
            xrefs_column="xrefs",
            drop_na=False,  # Keep all rows for this test
        )

        result = action.execute_typed(params, context)
        df = result.data["kg2c_proteins"]

        # Verify expected extractions
        assert len(df.loc[0, "uniprot_id"]) == 0  # No UniProt in first xrefs
        assert df.loc[1, "uniprot_id"] == ["Q14213"]
        assert df.loc[2, "uniprot_id"] == [
            "P00750",
            "P00750",
        ]  # Duplicates from isoforms

    # Test 7: Error handling
    def test_missing_dataset_key(self, action):
        """Test error handling for missing dataset key."""
        context = {
            "datasets": {},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }

        params = ExtractUniProtFromXrefsParams(
            dataset_key="nonexistent_dataset", xrefs_column="xrefs"
        )

        with pytest.raises(KeyError):
            action.execute_typed(params, context)

    def test_missing_xrefs_column(self, action, context_basic):
        """Test error handling for missing xrefs column."""
        params = ExtractUniProtFromXrefsParams(
            dataset_key="test_proteins", xrefs_column="nonexistent_column"
        )

        with pytest.raises(KeyError):
            action.execute_typed(params, context_basic)

    def test_action_registration(self, action):
        """Test that action is properly registered."""
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

        assert "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS" in ACTION_REGISTRY

    def test_get_params_model(self, action):
        """Test that action returns correct params model."""
        assert action.get_params_model() == ExtractUniProtFromXrefsParams

    def test_regex_pattern_validation(self, action):
        """Test the UniProt regex pattern directly."""
        test_patterns = [
            ("UniProtKB:P12345", ["P12345"]),
            ("UniProtKB:Q14213-1", ["Q14213-1"]),
            ("UniProtKB:P00750-12", ["P00750-12"]),
            ("UniProtKB:A0A123B4C5", ["A0A123B4C5"]),
            ("UniProtKB:P12345|UniProtKB:Q14213", ["P12345", "Q14213"]),
            ("RefSeq:NP_001234|UniProtKB:P12345|KEGG:K12345", ["P12345"]),
            ("UniProtKB:invalid", []),  # Too short
            ("UniProtKB:", []),  # Empty
            ("P12345", []),  # Missing prefix
        ]

        import re

        pattern = r"UniProtKB:([A-Z0-9]+(?:-\d+)?)"

        for test_string, expected in test_patterns:
            matches = re.findall(pattern, test_string)
            assert matches == expected, f"Pattern failed for: {test_string}"

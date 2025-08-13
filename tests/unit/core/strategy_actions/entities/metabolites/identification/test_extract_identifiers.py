"""
Unit tests for METABOLITE_EXTRACT_IDENTIFIERS action.

Tests extraction of multiple metabolite identifier types from compound datasets.
Written using TDD approach - tests first, implementation second.
"""

import pytest
import pandas as pd
from typing import Dict, Any

from biomapper.core.strategy_actions.entities.metabolites.identification.extract_identifiers import (
    MetaboliteExtractIdentifiersAction,
    MetaboliteExtractIdentifiersParams,
)
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY


class TestMetaboliteExtractIdentifiersAction:
    """Test suite for METABOLITE_EXTRACT_IDENTIFIERS action."""

    @pytest.fixture
    def sample_metabolite_data(self) -> pd.DataFrame:
        """Create sample metabolite data with various identifier formats."""
        return pd.DataFrame(
            {
                "compound_xrefs": [
                    "HMDB:HMDB0001234,CHEBI:28001,KEGG.COMPOUND:C00315",
                    "InChIKey:QNAYBMKLOCPYGJ-REOHCLBHSA-N,PUBCHEM.COMPOUND:680956",
                    "HMDB0005678,HMDB:HMDB00123",  # Multiple HMDB formats
                    "CHEBI:456,KEGG:C00123,PubChem:123456",
                    "",  # Empty
                    "INVALID_ID,HMDB01234",  # Mixed valid/invalid
                    None,  # None value
                ],
                "synonyms": [
                    "Some name,HMDB00111",
                    "QNAYBMKLOCPYGJ-UHFFFAOYSA-N",  # InChIKey without prefix
                    "C00999",  # KEGG without prefix
                    "789012",  # Could be CHEBI or PubChem
                    "Random text",
                    "",
                    None,
                ],
                "name": [
                    "Metabolite 1",
                    "Metabolite 2",
                    "Metabolite 3",
                    "Metabolite 4",
                    "Metabolite 5",
                    "Metabolite 6",
                    "Metabolite 7",
                ],
            }
        )

    @pytest.fixture
    def basic_params(self) -> Dict[str, Any]:
        """Basic parameters for action execution."""
        return {
            "input_key": "test_metabolites",
            "id_types": ["hmdb", "inchikey", "chebi", "kegg", "pubchem"],
            "source_columns": {
                "hmdb": "compound_xrefs,synonyms",
                "inchikey": "compound_xrefs,synonyms",
                "chebi": "compound_xrefs",
                "kegg": "compound_xrefs,synonyms",
                "pubchem": "compound_xrefs",
            },
            "output_key": "extracted_ids",
            "normalize_ids": True,
            "validate_formats": True,
            "handle_multiple": "expand_rows",
        }

    @pytest.fixture
    def mock_context(self, sample_metabolite_data) -> Dict[str, Any]:
        """Create mock execution context."""
        return {
            "datasets": {"test_metabolites": sample_metabolite_data},
            "statistics": {},
        }

    def test_action_registration(self):
        """Test that action is properly registered."""
        assert "METABOLITE_EXTRACT_IDENTIFIERS" in ACTION_REGISTRY
        assert (
            ACTION_REGISTRY["METABOLITE_EXTRACT_IDENTIFIERS"]
            == MetaboliteExtractIdentifiersAction
        )

    def test_params_model_validation(self):
        """Test parameter model validation."""
        # Valid params
        params = MetaboliteExtractIdentifiersParams(
            input_key="test",
            id_types=["hmdb", "inchikey"],
            source_columns={"hmdb": "col1", "inchikey": "col2"},
            output_key="output",
        )
        assert params.normalize_ids is True  # Default
        assert params.validate_formats is True  # Default
        assert params.handle_multiple == "expand_rows"  # Default

        # Invalid handle_multiple value
        with pytest.raises(ValueError):
            MetaboliteExtractIdentifiersParams(
                input_key="test",
                id_types=["hmdb"],
                source_columns={"hmdb": "col1"},
                output_key="output",
                handle_multiple="invalid",
            )

    @pytest.mark.asyncio
    async def test_hmdb_extraction_all_formats(self, mock_context):
        """Test extraction of HMDB IDs in various formats."""
        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs,synonyms"},
            output_key="hmdb_ids",
            normalize_ids=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        extracted_df = mock_context["datasets"]["hmdb_ids"]

        # Check that HMDB IDs are extracted and normalized
        hmdb_ids = extracted_df["hmdb"].dropna().tolist()
        assert "HMDB0001234" in hmdb_ids  # From HMDB:HMDB0001234
        assert "HMDB0005678" in hmdb_ids  # From HMDB0005678
        assert "HMDB0000123" in hmdb_ids  # From HMDB:HMDB00123 (normalized)
        assert "HMDB0001234" in hmdb_ids  # From HMDB01234 (normalized)
        assert "HMDB0000111" in hmdb_ids  # From synonyms HMDB00111

    @pytest.mark.asyncio
    async def test_inchikey_extraction_and_validation(self, mock_context):
        """Test extraction and validation of InChIKey identifiers."""
        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["inchikey"],
            source_columns={"inchikey": "compound_xrefs,synonyms"},
            output_key="inchikey_ids",
            validate_formats=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        extracted_df = mock_context["datasets"]["inchikey_ids"]

        # Check InChIKey extraction
        inchikeys = extracted_df["inchikey"].dropna().tolist()
        assert "QNAYBMKLOCPYGJ-REOHCLBHSA-N" in inchikeys
        assert "QNAYBMKLOCPYGJ-UHFFFAOYSA-N" in inchikeys

        # All extracted InChIKeys should be valid format
        for key in inchikeys:
            assert len(key.split("-")) == 3
            parts = key.split("-")
            assert len(parts[0]) == 14
            assert len(parts[1]) == 10
            assert len(parts[2]) == 1

    @pytest.mark.asyncio
    async def test_chebi_kegg_pubchem_extraction(self, mock_context):
        """Test extraction of CHEBI, KEGG, and PubChem identifiers."""
        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["chebi", "kegg", "pubchem"],
            source_columns={
                "chebi": "compound_xrefs",
                "kegg": "compound_xrefs,synonyms",
                "pubchem": "compound_xrefs",
            },
            output_key="multi_ids",
            normalize_ids=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        extracted_df = mock_context["datasets"]["multi_ids"]

        # Check CHEBI extraction
        chebi_ids = extracted_df["chebi"].dropna().tolist()
        assert "28001" in chebi_ids  # From CHEBI:28001
        assert "456" in chebi_ids  # From CHEBI:456

        # Check KEGG extraction
        kegg_ids = extracted_df["kegg"].dropna().tolist()
        assert "C00315" in kegg_ids  # From KEGG.COMPOUND:C00315
        assert "C00123" in kegg_ids  # From KEGG:C00123
        assert "C00999" in kegg_ids  # From synonyms

        # Check PubChem extraction
        pubchem_ids = extracted_df["pubchem"].dropna().tolist()
        assert "680956" in pubchem_ids  # From PUBCHEM.COMPOUND:680956
        assert "123456" in pubchem_ids  # From PubChem:123456

    @pytest.mark.asyncio
    async def test_handle_multiple_expand_rows(self, mock_context):
        """Test expanding rows when multiple IDs are found."""
        # Create data with multiple IDs in one row
        test_data = pd.DataFrame(
            {
                "compound_xrefs": ["HMDB:HMDB0001234,HMDB:HMDB0005678"],
                "name": ["Test Metabolite"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs"},
            output_key="expanded",
            handle_multiple="expand_rows",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        expanded_df = mock_context["datasets"]["expanded"]

        # Should have 2 rows (one for each HMDB ID)
        assert len(expanded_df) == 2
        assert set(expanded_df["hmdb"].tolist()) == {"HMDB0001234", "HMDB0005678"}
        # Both rows should have the same name
        assert all(expanded_df["name"] == "Test Metabolite")

    @pytest.mark.asyncio
    async def test_handle_multiple_list(self, mock_context):
        """Test keeping multiple IDs as list."""
        test_data = pd.DataFrame(
            {
                "compound_xrefs": ["HMDB:HMDB0001234,HMDB:HMDB0005678"],
                "name": ["Test Metabolite"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs"},
            output_key="listed",
            handle_multiple="list",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        listed_df = mock_context["datasets"]["listed"]

        # Should have 1 row with list of IDs
        assert len(listed_df) == 1
        hmdb_value = listed_df.iloc[0]["hmdb"]
        assert isinstance(hmdb_value, list)
        assert set(hmdb_value) == {"HMDB0001234", "HMDB0005678"}

    @pytest.mark.asyncio
    async def test_handle_multiple_first(self, mock_context):
        """Test taking only first ID when multiple found."""
        test_data = pd.DataFrame(
            {
                "compound_xrefs": ["HMDB:HMDB0001234,HMDB:HMDB0005678"],
                "name": ["Test Metabolite"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs"},
            output_key="first_only",
            handle_multiple="first",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        first_df = mock_context["datasets"]["first_only"]

        # Should have 1 row with first ID only
        assert len(first_df) == 1
        assert first_df.iloc[0]["hmdb"] == "HMDB0001234"

    @pytest.mark.asyncio
    async def test_empty_and_null_handling(self, mock_context):
        """Test handling of empty strings and null values."""
        test_data = pd.DataFrame(
            {
                "compound_xrefs": ["", None, "HMDB:HMDB0001234"],
                "synonyms": [None, "", "test"],
                "name": ["Met1", "Met2", "Met3"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs,synonyms"},
            output_key="null_handled",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        handled_df = mock_context["datasets"]["null_handled"]

        # Should handle nulls gracefully
        assert len(handled_df) == 3
        # First two rows should have NaN for hmdb
        assert pd.isna(handled_df.iloc[0]["hmdb"])
        assert pd.isna(handled_df.iloc[1]["hmdb"])
        # Third row should have the HMDB ID
        assert handled_df.iloc[2]["hmdb"] == "HMDB0001234"

    @pytest.mark.asyncio
    async def test_invalid_format_validation(self, mock_context):
        """Test that invalid formats are filtered when validation is enabled."""
        test_data = pd.DataFrame(
            {
                "compound_xrefs": [
                    "HMDB:INVALID",  # Invalid HMDB format
                    "BADKEY-BADFORMAT-X",  # Invalid InChIKey
                    "HMDB:HMDB0001234",  # Valid
                ],
                "name": ["Met1", "Met2", "Met3"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb", "inchikey"],
            source_columns={"hmdb": "compound_xrefs", "inchikey": "compound_xrefs"},
            output_key="validated",
            validate_formats=True,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        validated_df = mock_context["datasets"]["validated"]

        # Invalid formats should be filtered out
        assert pd.isna(validated_df.iloc[0]["hmdb"])  # Invalid HMDB
        assert pd.isna(validated_df.iloc[1]["inchikey"])  # Invalid InChIKey
        assert validated_df.iloc[2]["hmdb"] == "HMDB0001234"  # Valid HMDB

    @pytest.mark.asyncio
    async def test_no_validation(self, mock_context):
        """Test that invalid formats are kept when validation is disabled."""
        test_data = pd.DataFrame(
            {
                "compound_xrefs": ["HMDB:INVALID", "BADKEY-FORMAT"],
                "name": ["Met1", "Met2"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "compound_xrefs"},
            output_key="not_validated",
            validate_formats=False,
            normalize_ids=False,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        not_validated_df = mock_context["datasets"]["not_validated"]

        # Invalid formats should be kept
        assert not_validated_df.iloc[0]["hmdb"] == "INVALID"

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, mock_context):
        """Test that extraction statistics are properly tracked."""
        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb", "inchikey", "chebi"],
            source_columns={
                "hmdb": "compound_xrefs,synonyms",
                "inchikey": "compound_xrefs,synonyms",
                "chebi": "compound_xrefs",
            },
            output_key="stats_test",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        assert "metabolite_extraction_stats" in result.statistics

        stats = result.statistics["metabolite_extraction_stats"]
        assert "total_rows_processed" in stats
        assert "identifiers_extracted" in stats
        assert "hmdb" in stats["identifiers_extracted"]
        assert "inchikey" in stats["identifiers_extracted"]
        assert "chebi" in stats["identifiers_extracted"]

        # Check counts are reasonable
        assert stats["total_rows_processed"] == 7  # Original sample data has 7 rows
        assert stats["identifiers_extracted"]["hmdb"]["count"] > 0
        assert stats["identifiers_extracted"]["inchikey"]["count"] > 0

    @pytest.mark.asyncio
    async def test_missing_input_dataset(self, mock_context):
        """Test error handling when input dataset is missing."""
        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="missing_dataset",
            id_types=["hmdb"],
            source_columns={"hmdb": "col1"},
            output_key="output",
        )

        mock_context["datasets"] = {}  # No datasets

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_source_columns(self, mock_context):
        """Test handling when specified source columns don't exist."""
        test_data = pd.DataFrame(
            {"other_column": ["data1", "data2"], "name": ["Met1", "Met2"]}
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb"],
            source_columns={"hmdb": "nonexistent_column"},
            output_key="output",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        # Should handle gracefully - create output with NaN values
        assert result.success is True
        output_df = mock_context["datasets"]["output"]
        assert "hmdb" in output_df.columns
        assert all(pd.isna(output_df["hmdb"]))

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, mock_context):
        """Test performance with a large dataset (10k rows)."""
        import time

        # Create large dataset
        large_data = pd.DataFrame(
            {
                "compound_xrefs": [
                    f"HMDB:HMDB{str(i).zfill(7)},CHEBI:{i},KEGG:C{str(i).zfill(5)}"
                    for i in range(10000)
                ],
                "synonyms": [f"Synonym_{i}" for i in range(10000)],
                "name": [f"Metabolite_{i}" for i in range(10000)],
            }
        )
        mock_context["datasets"]["large_metabolites"] = large_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="large_metabolites",
            id_types=["hmdb", "chebi", "kegg"],
            source_columns={
                "hmdb": "compound_xrefs",
                "chebi": "compound_xrefs",
                "kegg": "compound_xrefs",
            },
            output_key="large_output",
            handle_multiple="expand_rows",
        )

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
        # Should complete within reasonable time (< 5 seconds for 10k rows)
        assert execution_time < 5.0

        output_df = mock_context["datasets"]["large_output"]
        # Should have extracted all IDs
        assert (
            len(output_df) >= 10000
        )  # May be more if expand_rows creates additional rows

    @pytest.mark.asyncio
    async def test_hmdb_normalization_edge_cases(self):
        """Test HMDB normalization for various edge cases."""
        action = MetaboliteExtractIdentifiersAction()

        # Test normalization method directly
        assert action._normalize_hmdb("HMDB0001234") == "HMDB0001234"
        assert action._normalize_hmdb("HMDB01234") == "HMDB0001234"
        assert action._normalize_hmdb("HMDB1234") == "HMDB0001234"
        assert (
            action._normalize_hmdb("HMDB00001234") == "HMDB0001234"
        )  # Already correct
        assert action._normalize_hmdb("HMDB123") == "HMDB0000123"
        assert action._normalize_hmdb("HMDB12") == "HMDB0000012"
        assert action._normalize_hmdb("HMDB1") == "HMDB0000001"
        assert action._normalize_hmdb("1234") == "HMDB0001234"  # Just number
        assert (
            action._normalize_hmdb("HMDB:HMDB0001234") == "HMDB0001234"
        )  # With prefix

    @pytest.mark.asyncio
    async def test_complex_multi_column_extraction(self, mock_context):
        """Test extraction from multiple columns with overlapping data."""
        test_data = pd.DataFrame(
            {
                "xrefs1": ["HMDB:HMDB0001234", "CHEBI:123", None],
                "xrefs2": ["KEGG:C00123", "HMDB:HMDB0001234", "CHEBI:456"],
                "synonyms": [
                    "HMDB0005678",
                    "C00999",
                    "InChIKey:QNAYBMKLOCPYGJ-REOHCLBHSA-N",
                ],
                "name": ["Met1", "Met2", "Met3"],
            }
        )
        mock_context["datasets"]["test_metabolites"] = test_data

        action = MetaboliteExtractIdentifiersAction()
        params = MetaboliteExtractIdentifiersParams(
            input_key="test_metabolites",
            id_types=["hmdb", "chebi", "kegg", "inchikey"],
            source_columns={
                "hmdb": "xrefs1,xrefs2,synonyms",
                "chebi": "xrefs1,xrefs2",
                "kegg": "xrefs2,synonyms",
                "inchikey": "synonyms",
            },
            output_key="complex_multi",
            handle_multiple="first",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        output_df = mock_context["datasets"]["complex_multi"]

        # Check extraction from different columns
        assert output_df.iloc[0]["hmdb"] == "HMDB0001234"  # From xrefs1
        assert output_df.iloc[0]["kegg"] == "C00123"  # From xrefs2
        assert output_df.iloc[1]["chebi"] == "123"  # From xrefs1
        assert (
            output_df.iloc[1]["hmdb"] == "HMDB0001234"
        )  # From xrefs2 (duplicate handling)
        assert (
            output_df.iloc[2]["inchikey"] == "QNAYBMKLOCPYGJ-REOHCLBHSA-N"
        )  # From synonyms

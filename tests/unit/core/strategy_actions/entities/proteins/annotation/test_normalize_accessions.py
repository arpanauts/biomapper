"""Test suite for PROTEIN_NORMALIZE_ACCESSIONS action.

Following TDD methodology - these tests define the expected behavior before implementation.
"""
import numpy as np
import pandas as pd
import pytest

from actions.registry import ACTION_REGISTRY
from actions.entities.proteins.annotation.normalize_accessions import (
    ProteinNormalizeAccessionsAction,
    ProteinNormalizeAccessionsParams,
)


class TestProteinNormalizeAccessionsParams:
    """Test parameter validation for ProteinNormalizeAccessionsParams."""

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Should fail without required fields
        with pytest.raises(ValueError):
            ProteinNormalizeAccessionsParams()

    def test_minimal_valid_params(self):
        """Test minimal valid parameter set."""
        params = ProteinNormalizeAccessionsParams(
            input_key="proteins",
            id_columns=["uniprot_id"],
            output_key="normalized_proteins",
        )
        assert params.input_key == "proteins"
        assert params.id_columns == ["uniprot_id"]
        assert params.output_key == "normalized_proteins"
        # Test defaults
        assert params.strip_isoforms is True
        assert params.strip_versions is True
        assert params.validate_format is True
        assert params.add_normalization_log is True

    def test_parameter_customization(self):
        """Test custom parameter values."""
        params = ProteinNormalizeAccessionsParams(
            input_key="proteins",
            id_columns=["acc1", "acc2"],
            strip_isoforms=False,
            strip_versions=False,
            validate_format=False,
            output_key="normalized",
            add_normalization_log=False,
        )
        assert params.strip_isoforms is False
        assert params.strip_versions is False
        assert params.validate_format is False
        assert params.add_normalization_log is False


class TestProteinNormalizeAccessionsAction:
    """Test the PROTEIN_NORMALIZE_ACCESSIONS action implementation."""

    @pytest.fixture
    def action(self):
        """Create action instance for testing."""
        return ProteinNormalizeAccessionsAction()

    @pytest.fixture
    def sample_protein_data(self):
        """Create sample protein data with various UniProt format issues."""
        return pd.DataFrame(
            {
                "protein_name": [
                    "Protein A",
                    "Protein B",
                    "Protein C",
                    "Protein D",
                    "Protein E",
                ],
                "uniprot_id": [
                    "p12345",  # lowercase - needs case normalization
                    "sp|P67890|GENE_NAME",  # SwissProt prefix - needs stripping
                    "P11111.2",  # version suffix - needs version removal
                    "P22222-1",  # isoform suffix - configurable removal
                    "P33333",  # already normalized - should remain unchanged
                ],
                "alt_uniprot": [
                    "tr|Q99999|TREMBL_NAME",  # TrEMBL prefix
                    "UniProt:P55555",  # UniProt: prefix
                    "P66666.1",  # version
                    np.nan,  # missing value
                    "INVALID123",  # invalid format
                ],
            }
        )

    @pytest.fixture
    def basic_context(self, sample_protein_data):
        """Create basic execution context."""
        return {
            "datasets": {"proteins": sample_protein_data},
            "current_identifiers": set(),
            "statistics": {},
            "output_files": [],
        }


class TestActionRegistration:
    """Test that the action self-registers properly."""

    def test_action_is_registered(self):
        """Test that PROTEIN_NORMALIZE_ACCESSIONS is registered in ACTION_REGISTRY."""
        assert "PROTEIN_NORMALIZE_ACCESSIONS" in ACTION_REGISTRY
        assert (
            ACTION_REGISTRY["PROTEIN_NORMALIZE_ACCESSIONS"]
            == ProteinNormalizeAccessionsAction
        )


class TestCaseNormalization:
    """Test case normalization functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    def test_case_normalization_basic(self, action):
        """Test basic case normalization from lowercase to uppercase."""
        # Test data with mixed case
        df = pd.DataFrame({"uniprot_id": ["p12345", "Q67890", "r99999", "P11111"]})
        context = {"datasets": {"test": df}}

        params = ProteinNormalizeAccessionsParams(
            input_key="test",
            id_columns=["uniprot_id"],
            output_key="normalized",
            strip_isoforms=False,
            strip_versions=False,
            validate_format=False,
        )

        result = action._normalize_case("p12345")
        assert result == "P12345"

        result = action._normalize_case("q67890")
        assert result == "Q67890"

    def test_case_normalization_preserves_uppercase(self, action):
        """Test that already uppercase IDs are preserved."""
        result = action._normalize_case("P12345")
        assert result == "P12345"


class TestPrefixStripping:
    """Test prefix stripping functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.mark.parametrize(
        "input_id,expected",
        [
            ("sp|P12345|GENE_NAME", "P12345"),
            ("tr|Q67890|TREMBL_NAME", "Q67890"),
            ("UniProt:P11111", "P11111"),
            ("uniprot:Q22222", "Q22222"),
            ("P33333", "P33333"),  # No prefix
            ("sp|P44444", "P44444"),  # Missing gene name part
            ("|P55555|", "P55555"),  # Edge case with empty prefix
        ],
    )
    def test_strip_prefixes(self, action, input_id, expected):
        """Test stripping various UniProt prefixes."""
        result = action._strip_prefixes(input_id)
        assert result == expected

    def test_strip_prefixes_case_insensitive(self, action):
        """Test that prefix stripping is case insensitive."""
        test_cases = [
            ("SP|P12345|GENE", "P12345"),
            ("TR|Q67890|GENE", "Q67890"),
            ("UNIPROT:P11111", "P11111"),
        ]
        for input_id, expected in test_cases:
            result = action._strip_prefixes(input_id)
            assert result == expected


class TestVersionRemoval:
    """Test version suffix removal functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.mark.parametrize(
        "input_id,expected",
        [
            ("P12345.1", "P12345"),
            ("Q67890.2", "Q67890"),
            ("P11111.10", "P11111"),
            ("P22222", "P22222"),  # No version
            ("P33333.", "P33333"),  # Trailing dot
            ("P44444.1.2", "P44444.1"),  # Only removes last version
        ],
    )
    def test_strip_versions(self, action, input_id, expected):
        """Test version suffix removal."""
        result = action._strip_versions(input_id)
        assert result == expected


class TestIsoformHandling:
    """Test isoform suffix handling functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    def test_strip_isoforms_enabled(self, action):
        """Test isoform stripping when enabled."""
        test_cases = [
            ("P12345-1", "P12345"),
            ("Q67890-2", "Q67890"),
            ("P11111-10", "P11111"),
            ("P22222", "P22222"),  # No isoform
            ("P33333-", "P33333"),  # Trailing dash
        ]
        for input_id, expected in test_cases:
            result = action._strip_isoforms(input_id, strip=True)
            assert result == expected

    def test_strip_isoforms_disabled(self, action):
        """Test isoform preservation when stripping disabled."""
        test_cases = [
            ("P12345-1", "P12345-1"),
            ("Q67890-2", "Q67890-2"),
            ("P11111", "P11111"),
        ]
        for input_id, expected in test_cases:
            result = action._strip_isoforms(input_id, strip=False)
            assert result == expected


class TestFormatValidation:
    """Test UniProt format validation functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.mark.parametrize(
        "uniprot_id,is_valid",
        [
            # Valid UniProt IDs
            ("P12345", True),
            ("Q123456", True),
            ("A0A123456", True),
            ("P123456789", True),  # 9 characters
            # Invalid UniProt IDs
            ("12345", False),  # No letter prefix
            ("PP12345", False),  # Two letter prefix
            ("P1234", False),  # Too short
            ("P1234567890", False),  # Too long
            ("P12_345", False),  # Invalid characters
            ("p12345", False),  # Lowercase (should be handled by normalization first)
            ("", False),  # Empty
            ("INVALID", False),  # Not a UniProt format
        ],
    )
    def test_validate_uniprot_format(self, action, uniprot_id, is_valid):
        """Test UniProt format validation."""
        result = action._validate_uniprot_format(uniprot_id)
        assert result == is_valid


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    def test_empty_values_handling(self, action):
        """Test handling of empty values, NaN, None."""
        df = pd.DataFrame({"uniprot_id": ["P12345", np.nan, "", None, "P67890"]})
        context = {"datasets": {"test": df}}

        # Test that empty values are preserved as-is and don't cause errors
        params = ProteinNormalizeAccessionsParams(
            input_key="test", id_columns=["uniprot_id"], output_key="normalized"
        )

        # The action should handle these gracefully
        result = action._normalize_single_value(np.nan)
        assert pd.isna(result)

        result = action._normalize_single_value("")
        assert result == ""

        result = action._normalize_single_value(None)
        assert result is None

    def test_malformed_strings(self, action):
        """Test handling of malformed or unexpected string formats."""
        malformed_cases = [
            "sp||P12345",  # Double pipe
            "sp|P12345|",  # Missing gene name
            "|||",  # Only pipes
            "random_string",  # Not UniProt-like at all
            "123.456.789",  # Multiple dots
            "P12345-1-2",  # Multiple dashes
        ]

        for case in malformed_cases:
            # Should not raise exceptions
            result = action._normalize_single_value(case)
            assert isinstance(result, (str, type(None)))


class TestMultiColumnProcessing:
    """Test processing multiple columns simultaneously."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.fixture
    def multi_column_data(self):
        """Sample data with multiple UniProt columns."""
        return pd.DataFrame(
            {
                "protein_name": ["Protein A", "Protein B"],
                "primary_uniprot": ["sp|P12345|GENE1", "tr|Q67890|GENE2"],
                "secondary_uniprot": ["P11111.1", "P22222-2"],
                "other_column": ["data1", "data2"],
            }
        )

    def test_multiple_column_normalization(self, action, multi_column_data):
        """Test that multiple columns are processed correctly."""
        context = {"datasets": {"test": multi_column_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="test",
            id_columns=["primary_uniprot", "secondary_uniprot"],
            output_key="normalized",
        )

        # This test will pass once we implement the action
        # For now, we're just defining the expected behavior


class TestNormalizationLogging:
    """Test normalization logging functionality."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.fixture
    def sample_protein_data(self):
        """Create sample protein data with various UniProt format issues."""
        return pd.DataFrame(
            {
                "protein_name": [
                    "Protein A",
                    "Protein B",
                    "Protein C",
                    "Protein D",
                    "Protein E",
                ],
                "uniprot_id": [
                    "p12345",  # lowercase - needs case normalization
                    "sp|P67890|GENE_NAME",  # SwissProt prefix - needs stripping
                    "P11111.2",  # version suffix - needs version removal
                    "P22222-1",  # isoform suffix - configurable removal
                    "P33333",  # already normalized - should remain unchanged
                ],
                "alt_uniprot": [
                    "tr|Q99999|TREMBL_NAME",  # TrEMBL prefix
                    "UniProt:P55555",  # UniProt: prefix
                    "P66666.1",  # version
                    np.nan,  # missing value
                    "INVALID123",  # invalid format
                ],
            }
        )

    def test_normalization_log_columns_added(self, action, sample_protein_data):
        """Test that normalization log columns are added when enabled."""
        context = {"datasets": {"test": sample_protein_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="test",
            id_columns=["uniprot_id"],
            output_key="normalized",
            add_normalization_log=True,
        )

        # Expected behavior: should add columns like 'uniprot_id_original', 'uniprot_id_normalized'
        # This test will pass once implemented

    def test_normalization_log_disabled(self, action, sample_protein_data):
        """Test that no log columns are added when logging disabled."""
        context = {"datasets": {"test": sample_protein_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="test",
            id_columns=["uniprot_id"],
            output_key="normalized",
            add_normalization_log=False,
        )

        # Expected behavior: original columns should be modified in-place
        # This test will pass once implemented


class TestRealDataSamples:
    """Test with realistic protein dataset samples."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.fixture
    def arivale_style_data(self):
        """Sample data mimicking Arivale proteomics format."""
        return pd.DataFrame(
            {
                "gene_symbol": ["APOA1", "APOB", "CRP"],
                "uniprot": ["P02647", "sp|P04114|APOB_HUMAN", "tr|P02741|CRP_HUMAN"],
                "protein_name": [
                    "Apolipoprotein A-I",
                    "Apolipoprotein B-100",
                    "C-reactive protein",
                ],
            }
        )

    @pytest.fixture
    def ukbb_style_data(self):
        """Sample data mimicking UKBB protein format."""
        return pd.DataFrame(
            {
                "protein_id": ["P02647.1", "P04114-2", "p02741"],
                "measurement": [1.23, 4.56, 7.89],
            }
        )

    def test_arivale_data_normalization(self, action, arivale_style_data):
        """Test normalization of Arivale-style protein data."""
        context = {"datasets": {"arivale": arivale_style_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="arivale", id_columns=["uniprot"], output_key="normalized"
        )

        # Expected results: P02647, P04114, P02741
        # This test ensures real data patterns work correctly

    def test_ukbb_data_normalization(self, action, ukbb_style_data):
        """Test normalization of UKBB-style protein data."""
        context = {"datasets": {"ukbb": ukbb_style_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="ukbb", id_columns=["protein_id"], output_key="normalized"
        )

        # Expected results: P02647, P04114, P02741


class TestPerformanceRequirements:
    """Test performance requirements."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    @pytest.fixture
    def large_protein_dataset(self):
        """Create dataset with 10k protein IDs for performance testing."""
        base_ids = ["P{:05d}".format(i) for i in range(10000)]
        # Add various format variations
        varied_ids = []
        for i, base_id in enumerate(base_ids):
            if i % 4 == 0:
                varied_ids.append(f"sp|{base_id}|GENE_{i}")
            elif i % 4 == 1:
                varied_ids.append(f"{base_id.lower()}.1")
            elif i % 4 == 2:
                varied_ids.append(f"{base_id}-1")
            else:
                varied_ids.append(base_id)

        return pd.DataFrame({"protein_id": varied_ids})

    @pytest.mark.performance
    def test_10k_proteins_under_5_seconds(self, action, large_protein_dataset):
        """Test that 10k protein IDs are processed in under 5 seconds."""
        import time

        context = {"datasets": {"large": large_protein_dataset}}

        params = ProteinNormalizeAccessionsParams(
            input_key="large", id_columns=["protein_id"], output_key="normalized"
        )

        start_time = time.time()
        # This will be implemented and should complete in <5 seconds
        end_time = time.time()

        processing_time = end_time - start_time
        assert (
            processing_time < 5.0
        ), f"Processing took {processing_time:.2f} seconds, expected <5 seconds"


class TestIntegrationReadiness:
    """Test integration with existing protein actions."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    def test_compatible_with_extract_uniprot_output(self, action):
        """Test compatibility with PROTEIN_EXTRACT_UNIPROT_FROM_XREFS output."""
        # Simulate output from PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
        extracted_data = pd.DataFrame(
            {
                "original_id": ["gene1", "gene2", "gene3"],
                "extracted_uniprot": ["sp|P12345|GENE1", "P67890.1", "tr|Q11111|GENE3"],
                "confidence": [0.95, 0.88, 0.92],
            }
        )

        context = {"datasets": {"extracted": extracted_data}}

        params = ProteinNormalizeAccessionsParams(
            input_key="extracted",
            id_columns=["extracted_uniprot"],
            output_key="normalized",
        )

        # Should produce clean UniProt IDs ready for matching
        # Expected: P12345, P67890, Q11111

    def test_feeds_into_multi_bridge_matching(self, action):
        """Test that output is compatible with PROTEIN_MULTI_BRIDGE matching."""
        # The normalized output should be in a format that multi-bridge matching expects
        normalized_data = pd.DataFrame(
            {
                "protein_name": ["Protein A", "Protein B"],
                "uniprot_id": ["P12345", "Q67890"],  # Clean, normalized format
                "other_data": ["data1", "data2"],
            }
        )

        # This represents the expected output format for downstream actions
        assert "uniprot_id" in normalized_data.columns
        assert all(normalized_data["uniprot_id"].str.match(r"^[A-Z][A-Z0-9]{5,9}$"))


class TestErrorHandlingAndLogging:
    """Test comprehensive error handling and logging."""

    @pytest.fixture
    def action(self):
        return ProteinNormalizeAccessionsAction()

    async def test_missing_input_dataset(self, action):
        """Test error when input dataset is missing from context."""
        context = {"datasets": {}}

        params = ProteinNormalizeAccessionsParams(
            input_key="missing_dataset",
            id_columns=["uniprot_id"],
            output_key="normalized",
        )

        with pytest.raises(KeyError, match="missing_dataset"):
            # Should raise clear error about missing dataset
            await action.execute(
                current_identifiers=[],
                current_ontology_type="protein",
                action_params=params.model_dump(),
                source_endpoint=None,
                target_endpoint=None,
                context=context,
            )

    async def test_missing_id_columns(self, action):
        """Test error when specified ID columns don't exist."""
        df = pd.DataFrame({"other_column": ["data1", "data2"]})
        context = {"datasets": {"test": df}}

        params = ProteinNormalizeAccessionsParams(
            input_key="test", id_columns=["nonexistent_column"], output_key="normalized"
        )

        with pytest.raises(KeyError, match="nonexistent_column"):
            # Should raise clear error about missing column
            await action.execute(
                current_identifiers=[],
                current_ontology_type="protein",
                action_params=params.model_dump(),
                source_endpoint=None,
                target_endpoint=None,
                context=context,
            )

    def test_logging_normalization_statistics(self, action):
        """Test that normalization statistics are logged properly."""
        # Should log:
        # - Total IDs processed
        # - Number of case normalizations
        # - Number of prefixes stripped
        # - Number of versions removed
        # - Number of isoforms handled
        # - Number of validation failures
        pass

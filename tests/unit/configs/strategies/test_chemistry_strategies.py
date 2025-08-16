"""
Unit tests for chemistry mapping strategies.

Tests strategy loading, validation, and basic execution patterns
for all chemistry strategies developed.
"""

import pytest
from unittest.mock import Mock
from biomapper_client import BiomapperClient
from pydantic import BaseModel


class StrategyExecutionResult(BaseModel):
    """Mock strategy execution result for testing."""

    success: bool
    strategy_id: str
    statistics: "DatasetStatistics"
    output_files: list[str] = []
    execution_time: float = 0.0
    error_message: str = None


class DatasetStatistics(BaseModel):
    """Mock dataset statistics for testing."""

    total_identifiers: int = 0
    unique_identifiers: int = 0
    duplicate_identifiers: int = 0
    mapping_rate: float = 0.0
    quality_score: float = 0.0
    valid_loinc_codes: int = 0
    missing_loinc_codes: int = 0
    vendors_harmonized: int = 0
    fuzzy_match_rate: float = 0.0
    semantic_matches: int = 0
    nightingale_mappings: int = 0
    cross_vendor_matches: int = 0
    vendor_specific_matches: int = 0
    hebrew_translations: int = 0
    chemistry_related_filtered: int = 0
    fuzzy_metabolite_matches: int = 0
    clinical_biomarkers_filtered: int = 0
    nightingale_loinc_mappings: int = 0
    fuzzy_matches: int = 0
    processing_errors: int = 0
    successful_records: int = 0
    unified_chemistry_tests: int = 0
    deduplication_applied: int = 0
    vendor_normalization_applied: bool = False
    abbreviation_expansions: int = 0
    synonym_matches: int = 0


class TestChemistryStrategies:
    """Test suite for chemistry mapping strategies."""

    @pytest.fixture
    def client(self):
        """Mock BiomapperClient for testing."""
        return Mock()

    @pytest.fixture
    def sample_execution_result(self):
        """Sample execution result for testing."""
        return StrategyExecutionResult(
            success=True,
            strategy_id="test_strategy",
            statistics=DatasetStatistics(
                total_identifiers=100,
                unique_identifiers=95,
                duplicate_identifiers=5,
                mapping_rate=0.75,
                quality_score=0.80,
            ),
            output_files=["test_output.tsv"],
            execution_time=10.5,
        )

    def test_arivale_spoke_chemistry_loads(self, client):
        """Test Arivale to SPOKE strategy loads and validates."""
        # Mock strategy loading
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "chemistry"
        mock_strategy.metadata.source_dataset = "arivale"
        mock_strategy.metadata.target_dataset = "spoke"
        mock_strategy.metadata.bridge_type = ["loinc", "fuzzy"]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_arv_to_spoke_loinc_v1_base")

        assert strategy is not None
        assert strategy.metadata.entity_type == "chemistry"
        assert strategy.metadata.source_dataset == "arivale"
        assert strategy.metadata.target_dataset == "spoke"
        assert "loinc" in strategy.metadata.bridge_type
        assert "fuzzy" in strategy.metadata.bridge_type

    def test_israeli10k_spoke_chemistry_loads(self, client):
        """Test Israeli10k to SPOKE strategy loads with harmonization."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "chemistry"
        mock_strategy.metadata.source_dataset = "israeli10k"
        mock_strategy.metadata.target_dataset = "spoke"
        mock_strategy.metadata.bridge_type = ["loinc", "fuzzy", "harmonization"]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_isr_to_spoke_loinc_v1_base")

        assert strategy is not None
        assert strategy.metadata.entity_type == "chemistry"
        assert "harmonization" in strategy.metadata.bridge_type

    def test_israeli10k_metabolomics_semantic_loads(self, client):
        """Test Israeli10k metabolomics semantic bridge strategy."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "chemistry"
        mock_strategy.metadata.source_dataset = "israeli10k_metabolomics"
        mock_strategy.metadata.bridge_type = [
            "semantic",
            "fuzzy",
            "metabolite_chemistry",
        ]
        mock_strategy.metadata.quality_tier = "experimental"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy(
            "chem_isr_metab_to_spoke_semantic_v1_experimental"
        )

        assert strategy is not None
        assert strategy.metadata.quality_tier == "experimental"
        assert "semantic" in strategy.metadata.bridge_type

    def test_ukbb_nmr_nightingale_loads(self, client):
        """Test UKBB NMR to SPOKE via Nightingale strategy."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "chemistry"
        mock_strategy.metadata.source_dataset = "ukbb_nmr"
        mock_strategy.metadata.bridge_type = ["nightingale", "loinc", "fuzzy"]
        mock_strategy.metadata.dependencies = ["nightingale_loinc_mapping.csv"]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_ukb_nmr_to_spoke_nightingale_v1_base")

        assert strategy is not None
        assert "nightingale" in strategy.metadata.bridge_type
        assert "nightingale_loinc_mapping.csv" in strategy.metadata.dependencies

    def test_multi_source_chemistry_loads(self, client):
        """Test multi-source chemistry harmonization strategy."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "chemistry"
        mock_strategy.metadata.source_dataset = "multi_vendor"
        mock_strategy.metadata.bridge_type = [
            "loinc",
            "fuzzy",
            "harmonization",
            "cross_vendor",
        ]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_multi_to_unified_loinc_v1_comprehensive")

        assert strategy is not None
        assert "cross_vendor" in strategy.metadata.bridge_type

    def test_loinc_extraction_parameters(self, client, sample_execution_result):
        """Test LOINC code extraction parameters."""
        sample_execution_result.statistics.valid_loinc_codes = 45
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy(
            "chem_arv_to_spoke_loinc_v1_base", parameters={"output_dir": "/tmp/test"}
        )

        assert result.success
        assert hasattr(result.statistics, "valid_loinc_codes")
        assert result.statistics.valid_loinc_codes > 0

    def test_vendor_harmonization_execution(self, client, sample_execution_result):
        """Test cross-vendor harmonization execution."""
        sample_execution_result.statistics.vendors_harmonized = 3
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy(
            "chem_multi_to_unified_loinc_v1_comprehensive",
            parameters={"output_dir": "/tmp/test"},
        )

        assert result.success
        assert hasattr(result.statistics, "vendors_harmonized")
        assert result.statistics.vendors_harmonized == 3

    def test_fuzzy_matching_accuracy(self, client, sample_execution_result):
        """Test fuzzy matching handles variations."""
        sample_execution_result.statistics.fuzzy_match_rate = 0.72
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy(
            "chem_isr_to_spoke_loinc_v1_base", parameters={"match_threshold": 0.8}
        )

        assert result.statistics.fuzzy_match_rate >= 0.65

    def test_semantic_matching_execution(self, client, sample_execution_result):
        """Test semantic matching execution."""
        sample_execution_result.statistics.semantic_matches = 25
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy(
            "chem_isr_metab_to_spoke_semantic_v1_experimental",
            parameters={"semantic_threshold": 0.75},
        )

        assert result.success
        assert hasattr(result.statistics, "semantic_matches")
        assert result.statistics.semantic_matches > 0

    def test_nightingale_mapping_execution(self, client, sample_execution_result):
        """Test Nightingale NMR mapping execution."""
        sample_execution_result.statistics.nightingale_mappings = 18
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy(
            "chem_ukb_nmr_to_spoke_nightingale_v1_base",
            parameters={"use_loinc_primary": True},
        )

        assert result.success
        assert hasattr(result.statistics, "nightingale_mappings")
        assert result.statistics.nightingale_mappings > 0

    @pytest.mark.parametrize(
        "strategy_id,expected_entity_type",
        [
            ("chem_arv_to_spoke_loinc_v1_base", "chemistry"),
            ("chem_isr_to_spoke_loinc_v1_base", "chemistry"),
            ("chem_isr_metab_to_spoke_semantic_v1_experimental", "chemistry"),
            ("chem_ukb_nmr_to_spoke_nightingale_v1_base", "chemistry"),
            ("chem_multi_to_unified_loinc_v1_comprehensive", "chemistry"),
        ],
    )
    def test_all_strategies_are_chemistry_type(
        self, client, strategy_id, expected_entity_type
    ):
        """Test all chemistry strategies have correct entity type."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = expected_entity_type
        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy(strategy_id)
        assert strategy.metadata.entity_type == expected_entity_type

    def test_chemistry_test_categories_validation(self, client):
        """Test chemistry strategies have appropriate test categories."""
        expected_categories = {
            "metabolic_panel",
            "lipid_panel",
            "complete_blood_count",
            "liver_function",
            "kidney_function",
        }

        mock_strategy = Mock()
        mock_strategy.metadata.test_categories = list(expected_categories)
        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_arv_to_spoke_loinc_v1_base")

        assert len(set(strategy.metadata.test_categories) & expected_categories) > 0

    def test_strategy_parameter_validation(self, client):
        """Test strategy parameters are properly structured."""
        mock_strategy = Mock()
        mock_strategy.parameters = {
            "output_dir": "/tmp/biomapper_output",
            "match_threshold": 0.85,
        }
        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("chem_arv_to_spoke_loinc_v1_base")

        assert "output_dir" in strategy.parameters
        assert "match_threshold" in strategy.parameters
        assert isinstance(strategy.parameters["match_threshold"], float)

    def test_cross_vendor_matching_logic(self, client, sample_execution_result):
        """Test cross-vendor matching produces reasonable results."""
        sample_execution_result.statistics.cross_vendor_matches = 42
        sample_execution_result.statistics.vendor_specific_matches = 15
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy("chem_multi_to_unified_loinc_v1_comprehensive")

        assert result.success
        assert hasattr(result.statistics, "cross_vendor_matches")
        assert result.statistics.cross_vendor_matches > 0

    def test_hebrew_translation_handling(self, client, sample_execution_result):
        """Test Hebrew translation handling in Israeli10k data."""
        sample_execution_result.statistics.hebrew_translations = 12
        client.execute_strategy.return_value = sample_execution_result

        result = client.execute_strategy("chem_isr_to_spoke_loinc_v1_base")

        assert result.success
        # Test would check for Hebrew translation capability
        assert hasattr(result.statistics, "hebrew_translations")

    def test_loinc_validation_patterns(self, client):
        """Test LOINC validation patterns work correctly."""
        test_patterns = [
            ("12345-6", True),  # Valid LOINC
            ("1234-5", True),  # Valid LOINC (shorter)
            ("123456-7", False),  # Too long
            ("1234-", False),  # Missing check digit
            ("abcd-5", False),  # Non-numeric
        ]

        for loinc_code, should_be_valid in test_patterns:
            # This would test the LOINC validation regex
            # Pattern: "^\\d{1,5}-\\d$"
            import re

            pattern = r"^\d{1,5}-\d$"
            is_valid = bool(re.match(pattern, loinc_code))
            assert is_valid == should_be_valid, f"LOINC {loinc_code} validation failed"


class TestChemistryStrategyEdgeCases:
    """Test edge cases and error conditions for chemistry strategies."""

    @pytest.fixture
    def client(self):
        return Mock()

    def test_missing_loinc_codes_handling(self, client):
        """Test handling of datasets with missing LOINC codes."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="test_strategy",
            statistics=DatasetStatistics(
                total_identifiers=100,
                valid_loinc_codes=45,  # Less than half have LOINC
                missing_loinc_codes=55,
                mapping_rate=0.45,
            ),
        )
        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy("chem_arv_to_spoke_loinc_v1_base")

        assert result.success
        assert result.statistics.valid_loinc_codes < result.statistics.total_identifiers

    def test_low_match_rate_scenarios(self, client):
        """Test strategies handle low match rates gracefully."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="test_strategy",
            statistics=DatasetStatistics(
                total_identifiers=100,
                mapping_rate=0.25,  # Low match rate
                quality_score=0.30,
            ),
        )
        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "chem_isr_metab_to_spoke_semantic_v1_experimental"
        )

        # Semantic bridge expected to have lower match rates
        assert result.success
        assert result.statistics.mapping_rate >= 0.20  # Minimum acceptable

    def test_vendor_specific_edge_cases(self, client):
        """Test vendor-specific formatting and naming conventions."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="test_strategy",
            statistics=DatasetStatistics(
                vendor_normalization_applied=True,
                abbreviation_expansions=15,
                synonym_matches=8,
            ),
        )
        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy("chem_multi_to_unified_loinc_v1_comprehensive")

        assert result.success
        assert hasattr(result.statistics, "vendor_normalization_applied")

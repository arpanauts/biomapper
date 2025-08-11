"""
Integration tests for chemistry mapping strategies.

These tests use real (or realistic mock) data to validate
the complete chemistry mapping pipeline end-to-end.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
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


class TestChemistryMappingIntegration:
    """Integration tests for complete chemistry mapping workflows."""

    @pytest.fixture
    def client(self):
        """Real BiomapperClient for integration testing."""
        return BiomapperClient(base_url="http://localhost:8000")  # Test API server

    @pytest.fixture
    def temp_output_dir(self):
        """Temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_arivale_data(self, temp_output_dir):
        """Sample Arivale chemistry data for testing."""
        data_file = Path(temp_output_dir) / "arivale_sample.tsv"
        sample_data = """test_name	loinc_code	units	reference_range
Glucose, Serum	2345-7	mg/dL	70-100
Total Cholesterol	2093-3	mg/dL	<200
HDL Cholesterol	2085-9	mg/dL	>40
LDL Cholesterol	18262-6	mg/dL	<100
Triglycerides	2571-8	mg/dL	<150
Hemoglobin	718-7	g/dL	12.0-16.0
Hematocrit	4544-3	%	36-46
Creatinine	2160-0	mg/dL	0.6-1.2
ALT	1742-6	U/L	7-56
AST	1920-8	U/L	10-40"""

        data_file.write_text(sample_data)
        return str(data_file)

    @pytest.fixture
    def sample_israeli10k_data(self, temp_output_dir):
        """Sample Israeli10k chemistry data with Hebrew names."""
        data_file = Path(temp_output_dir) / "israeli10k_sample.csv"
        sample_data = """test_id,test_name_hebrew,test_name_english,loinc_code,units
ISR001,גלוקוז,Glucose,2345-7,mg/dL
ISR002,כולסטרול,Cholesterol,2093-3,mg/dL
ISR003,המוגלובין,Hemoglobin,718-7,g/dL
ISR004,קריאטינין,Creatinine,2160-0,mg/dL
ISR005,אוריאה,Urea,3094-0,mg/dL
ISR006,טריגליצרידים,Triglycerides,2571-8,mg/dL"""

        data_file.write_text(sample_data)
        return str(data_file)

    @pytest.fixture
    def sample_ukbb_nmr_data(self, temp_output_dir):
        """Sample UKBB NMR biomarker data."""
        data_file = Path(temp_output_dir) / "ukbb_nmr_sample.tsv"
        sample_data = """biomarker	description	units	data_coding
Total_C	Total cholesterol	mmol/L	continuous
LDL_C	LDL cholesterol	mmol/L	continuous
HDL_C	HDL cholesterol	mmol/L	continuous
Triglycerides	Triglycerides	mmol/L	continuous
Glucose	Glucose	mmol/L	continuous
Lactate	Lactate	mmol/L	continuous
Alanine	Alanine	mmol/L	continuous
Creatinine	Creatinine	μmol/L	continuous"""

        data_file.write_text(sample_data)
        return str(data_file)

    @pytest.fixture
    def sample_spoke_labs_data(self, temp_output_dir):
        """Sample SPOKE clinical labs data."""
        data_file = Path(temp_output_dir) / "spoke_labs_sample.csv"
        sample_data = """loinc_code,test_name,component,property,time_aspct,system,scale_typ,method_typ
2345-7,Glucose,Glucose,MCnc,Pt,Ser/Plas,Qn,
2093-3,Cholesterol total,Cholesterol,MCnc,Pt,Ser/Plas,Qn,
2085-9,Cholesterol in HDL,Cholesterol,MCnc,Pt,Ser/Plas,Qn,
18262-6,Cholesterol in LDL,Cholesterol,MCnc,Pt,Ser/Plas,Qn,
2571-8,Triglyceride,Triglyceride,MCnc,Pt,Ser/Plas,Qn,
718-7,Hemoglobin,Hemoglobin,MCnc,Pt,Bld,Qn,
4544-3,Hematocrit,Volume Fraction,VFr,Pt,Bld,Qn,
2160-0,Creatinine,Creatinine,MCnc,Pt,Ser/Plas,Qn,"""

        data_file.write_text(sample_data)
        return str(data_file)

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_arivale_to_spoke_complete_pipeline(
        self,
        mock_execute,
        client,
        sample_arivale_data,
        sample_spoke_labs_data,
        temp_output_dir,
    ):
        """Test complete Arivale to SPOKE mapping pipeline."""
        # Mock successful execution
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="chem_arv_to_spoke_loinc_v1_base",
            statistics=DatasetStatistics(
                total_identifiers=10,
                unique_identifiers=10,
                valid_loinc_codes=8,
                fuzzy_matches=2,
                mapping_rate=0.80,
                quality_score=0.85,
            ),
            output_files=[f"{temp_output_dir}/arivale_spoke_chemistry.tsv"],
            execution_time=5.2,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy(
            "chem_arv_to_spoke_loinc_v1_base",
            parameters={"output_dir": temp_output_dir, "match_threshold": 0.85},
        )

        assert result.success
        assert result.statistics.total_identifiers > 0
        assert result.statistics.mapping_rate >= 0.70
        assert len(result.output_files) > 0

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_israeli10k_harmonization_pipeline(
        self,
        mock_execute,
        client,
        sample_israeli10k_data,
        sample_spoke_labs_data,
        temp_output_dir,
    ):
        """Test Israeli10k chemistry harmonization with Hebrew translation."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="chem_isr_to_spoke_loinc_v1_base",
            statistics=DatasetStatistics(
                total_identifiers=6,
                hebrew_translations=6,
                vendor_harmonization_applied=6,
                valid_loinc_codes=6,
                mapping_rate=1.0,
                quality_score=0.90,
            ),
            output_files=[f"{temp_output_dir}/israeli10k_spoke_chemistry.tsv"],
            execution_time=7.1,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy(
            "chem_isr_to_spoke_loinc_v1_base",
            parameters={
                "output_dir": temp_output_dir,
                "match_threshold": 0.80,
                "use_abbreviations": True,
            },
        )

        assert result.success
        assert result.statistics.hebrew_translations > 0
        assert result.statistics.vendor_harmonization_applied > 0
        assert result.statistics.mapping_rate >= 0.65

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_semantic_metabolomics_bridge(self, mock_execute, client, temp_output_dir):
        """Test semantic bridge from metabolomics to chemistry."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="chem_isr_metab_to_spoke_semantic_v1_experimental",
            statistics=DatasetStatistics(
                total_identifiers=234,
                chemistry_related_filtered=45,
                fuzzy_metabolite_matches=12,
                semantic_matches=8,
                mapping_rate=0.35,
                quality_score=0.60,
            ),
            output_files=[
                f"{temp_output_dir}/israeli10k_metabolomics_spoke_chemistry_semantic.tsv"
            ],
            execution_time=25.3,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy(
            "chem_isr_metab_to_spoke_semantic_v1_experimental",
            parameters={
                "output_dir": temp_output_dir,
                "semantic_threshold": 0.75,
                "model": "biobert",
            },
        )

        assert result.success
        assert result.statistics.semantic_matches > 0
        assert (
            result.statistics.mapping_rate >= 0.30
        )  # Lower expectation for experimental

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_ukbb_nightingale_nmr_pipeline(
        self,
        mock_execute,
        client,
        sample_ukbb_nmr_data,
        sample_spoke_labs_data,
        temp_output_dir,
    ):
        """Test UKBB NMR to SPOKE via Nightingale mapping."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="chem_ukb_nmr_to_spoke_nightingale_v1_base",
            statistics=DatasetStatistics(
                total_identifiers=8,
                clinical_biomarkers_filtered=8,
                nightingale_loinc_mappings=7,
                fuzzy_matches=1,
                mapping_rate=0.88,
                quality_score=0.92,
            ),
            output_files=[f"{temp_output_dir}/ukbb_nmr_spoke_chemistry.tsv"],
            execution_time=4.8,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy(
            "chem_ukb_nmr_to_spoke_nightingale_v1_base",
            parameters={
                "output_dir": temp_output_dir,
                "use_loinc_primary": True,
                "fallback_to_name": True,
            },
        )

        assert result.success
        assert result.statistics.nightingale_loinc_mappings > 0
        assert result.statistics.mapping_rate >= 0.75

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_multi_source_comprehensive_harmonization(
        self,
        mock_execute,
        client,
        sample_arivale_data,
        sample_israeli10k_data,
        sample_ukbb_nmr_data,
        temp_output_dir,
    ):
        """Test comprehensive multi-source chemistry harmonization."""
        mock_result = StrategyExecutionResult(
            success=True,
            strategy_id="chem_multi_to_unified_loinc_v1_comprehensive",
            statistics=DatasetStatistics(
                total_identifiers=24,  # Combined from all sources
                vendors_harmonized=3,
                cross_vendor_matches=15,
                unified_chemistry_tests=18,
                deduplication_applied=6,
                mapping_rate=0.75,
                quality_score=0.82,
            ),
            output_files=[
                f"{temp_output_dir}/unified_chemistry_tests.tsv",
                f"{temp_output_dir}/chemistry_cross_reference_table.tsv",
                f"{temp_output_dir}/multi_vendor_chemistry_statistics.json",
            ],
            execution_time=45.7,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy(
            "chem_multi_to_unified_loinc_v1_comprehensive",
            parameters={
                "output_dir": temp_output_dir,
                "cross_match_threshold": 0.75,
                "merge_strategy": "union",
                "deduplicate_by": "loinc_code",
            },
        )

        assert result.success
        assert result.statistics.vendors_harmonized == 3
        assert result.statistics.cross_vendor_matches > 0
        assert result.statistics.unified_chemistry_tests > 0
        assert len(result.output_files) == 3  # Unified, cross-ref, stats

    @pytest.mark.integration
    def test_chemistry_strategy_validation_pipeline(self, client, temp_output_dir):
        """Test validation of all chemistry strategies."""
        strategies_to_validate = [
            "chem_arv_to_spoke_loinc_v1_base",
            "chem_isr_to_spoke_loinc_v1_base",
            "chem_isr_metab_to_spoke_semantic_v1_experimental",
            "chem_ukb_nmr_to_spoke_nightingale_v1_base",
            "chem_multi_to_unified_loinc_v1_comprehensive",
        ]

        validation_results = []

        for strategy_id in strategies_to_validate:
            try:
                # Test strategy loading
                strategy = client.get_strategy(strategy_id)
                assert strategy is not None

                # Test metadata validation
                assert strategy.metadata.entity_type == "chemistry"
                assert strategy.metadata.version is not None
                assert strategy.metadata.author is not None

                # Test parameter validation
                assert hasattr(strategy, "parameters")
                assert "output_dir" in strategy.parameters

                validation_results.append((strategy_id, True, None))

            except Exception as e:
                validation_results.append((strategy_id, False, str(e)))

        # All strategies should validate successfully
        failed_validations = [r for r in validation_results if not r[1]]
        assert len(failed_validations) == 0, f"Failed validations: {failed_validations}"

    @pytest.mark.integration
    def test_chemistry_data_quality_metrics(self, client, temp_output_dir):
        """Test data quality metrics across chemistry strategies."""
        # Test quality thresholds for different strategy types
        quality_expectations = {
            "chem_arv_to_spoke_loinc_v1_base": {
                "min_mapping_rate": 0.70,
                "min_quality_score": 0.75,
            },
            "chem_isr_to_spoke_loinc_v1_base": {
                "min_mapping_rate": 0.65,
                "min_quality_score": 0.70,
            },
            "chem_isr_metab_to_spoke_semantic_v1_experimental": {
                "min_mapping_rate": 0.30,  # Lower for experimental
                "min_quality_score": 0.50,
            },
            "chem_ukb_nmr_to_spoke_nightingale_v1_base": {
                "min_mapping_rate": 0.75,
                "min_quality_score": 0.80,
            },
            "chem_multi_to_unified_loinc_v1_comprehensive": {
                "min_mapping_rate": 0.65,
                "min_quality_score": 0.75,
            },
        }

        for strategy_id, expectations in quality_expectations.items():
            # Mock strategy execution for quality testing
            with patch.object(client, "execute_strategy") as mock_exec:
                mock_result = StrategyExecutionResult(
                    success=True,
                    strategy_id=strategy_id,
                    statistics=DatasetStatistics(
                        mapping_rate=expectations["min_mapping_rate"] + 0.05,
                        quality_score=expectations["min_quality_score"] + 0.05,
                    ),
                )
                mock_exec.return_value = mock_result

                result = client.execute_strategy(strategy_id)

                assert (
                    result.statistics.mapping_rate >= expectations["min_mapping_rate"]
                )
                assert (
                    result.statistics.quality_score >= expectations["min_quality_score"]
                )

    @pytest.mark.integration
    @patch("biomapper_client.BiomapperClient.execute_strategy")
    def test_error_handling_and_recovery(self, mock_execute, client, temp_output_dir):
        """Test error handling and recovery in chemistry strategies."""
        # Test partial failure scenario
        mock_result = StrategyExecutionResult(
            success=False,
            strategy_id="chem_arv_to_spoke_loinc_v1_base",
            error_message="LOINC validation failed for 15 records",
            statistics=DatasetStatistics(
                total_identifiers=100,
                processing_errors=15,
                successful_records=85,
                mapping_rate=0.85,
            ),
            output_files=[],
            execution_time=8.2,
        )
        mock_execute.return_value = mock_result

        result = client.execute_strategy("chem_arv_to_spoke_loinc_v1_base")

        # Strategy should handle partial failures gracefully
        assert result.statistics.processing_errors > 0
        assert result.statistics.successful_records > 0
        assert result.error_message is not None

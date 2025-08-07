"""
Test suite for CHEMISTRY_VENDOR_HARMONIZATION action.

This test suite comprehensively tests the chemistry vendor harmonization
functionality including vendor detection, test name harmonization, unit
conversion, and reference range standardization across multiple vendors.

Following TDD approach - these tests are written first to drive implementation.
"""

import pytest
import pandas as pd

from biomapper.core.strategy_actions.entities.chemistry.harmonization.vendor_harmonization import (
    ChemistryVendorHarmonizationAction,
    ChemistryVendorHarmonizationParams,
    ChemistryVendorHarmonizationResult,
    VendorProfile,
    TestNameHarmonizer,
    UnitConverter,
    ReferenceRangeHarmonizer,
)


class TestVendorProfile:
    """Test vendor detection functionality."""

    def test_detect_labcorp_vendor_by_test_codes(self):
        """Test LabCorp vendor detection by test code patterns."""
        df = pd.DataFrame(
            {
                "test_code": ["LC001453", "LC001123", "LC001172", "LC002100"],
                "test_name": ["Glucose", "Cholesterol", "LDL", "Triglycerides"],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(
            df, {"test_name": "test_name", "test_code": "test_code"}
        )

        assert detected_vendor == "labcorp"

    def test_detect_quest_vendor_by_test_codes(self):
        """Test Quest vendor detection by test code patterns."""
        df = pd.DataFrame(
            {
                "test_code": ["QD483", "QD234", "QD345", "QD678"],
                "test_name": ["Glucose", "Cholesterol", "LDL", "HDL"],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(
            df, {"test_name": "test_name", "test_code": "test_code"}
        )

        assert detected_vendor == "quest"

    def test_detect_mayo_vendor_by_test_codes(self):
        """Test Mayo vendor detection by test code patterns."""
        df = pd.DataFrame(
            {
                "test_code": ["GLU", "CHOL1", "LDLC", "HDLC"],
                "test_name": ["Glucose", "Cholesterol", "LDL", "HDL"],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(
            df, {"test_name": "test_name", "test_code": "test_code"}
        )

        assert detected_vendor == "mayo"

    def test_detect_arivale_vendor_by_test_names(self):
        """Test Arivale vendor detection by test name patterns."""
        df = pd.DataFrame(
            {
                "test_name": [
                    "Glucose, Serum (2345-7)",
                    "ALT (1742-6)",
                    "Cholesterol, Total (2093-3)",
                    "Creatinine (2160-0)",
                ]
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(df, {"test_name": "test_name"})

        assert detected_vendor == "arivale"

    def test_detect_ukbb_vendor_by_field_ids(self):
        """Test UK Biobank vendor detection by field ID patterns."""
        df = pd.DataFrame(
            {
                "test_name": ["30000", "30690", "30780", "30870"],
                "value": [95.5, 4.2, 2.3, 1.4],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(df, {"test_name": "test_name"})

        assert detected_vendor == "ukbb"

    def test_detect_israeli10k_vendor_by_numeric_codes(self):
        """Test Israeli10k vendor detection by numeric test codes."""
        df = pd.DataFrame(
            {
                "test_code": ["1234", "5678", "9101", "1121"],
                "test_name": ["Glucose", "Cholesterol", "LDL", "HDL"],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(
            df, {"test_name": "test_name", "test_code": "test_code"}
        )

        assert detected_vendor == "israeli10k"

    def test_detect_generic_vendor_fallback(self):
        """Test fallback to generic when no patterns match."""
        df = pd.DataFrame(
            {
                "test_name": ["Random Test 1", "Another Test", "Custom Assay"],
                "value": [100, 200, 300],
            }
        )

        vendor_profile = VendorProfile()
        detected_vendor = vendor_profile.detect_vendor(df, {"test_name": "test_name"})

        assert detected_vendor == "generic"


class TestTestNameHarmonizer:
    """Test test name harmonization functionality."""

    def test_harmonize_glucose_variations(self):
        """Test harmonization of glucose test name variations."""
        harmonizer = TestNameHarmonizer()

        test_cases = [
            ("glucose", "generic", "Glucose"),
            ("glucose, serum", "arivale", "Glucose"),
            ("glucose, plasma", "labcorp", "Glucose"),
            ("glucose, fasting", "quest", "Glucose (Fasting)"),
            ("blood sugar", "generic", "Glucose"),
            ("GLU", "mayo", "Glucose"),
            ("glucose (2345-7)", "arivale", "Glucose"),
        ]

        for test_name, vendor, expected in test_cases:
            result = harmonizer.harmonize_test_name(test_name, vendor)
            assert (
                result == expected
            ), f"Failed for {test_name} -> expected {expected}, got {result}"

    def test_harmonize_cholesterol_variations(self):
        """Test harmonization of cholesterol test name variations."""
        harmonizer = TestNameHarmonizer()

        test_cases = [
            ("cholesterol", "generic", "Cholesterol, Total"),
            ("cholesterol, total", "labcorp", "Cholesterol, Total"),
            ("total cholesterol", "quest", "Cholesterol, Total"),
            ("CHOL", "mayo", "Cholesterol, Total"),
            ("ldl cholesterol", "generic", "Cholesterol, LDL"),
            ("ldl-c", "quest", "Cholesterol, LDL"),
            ("ldl cholesterol direct", "quest", "Cholesterol, LDL"),
            ("hdl cholesterol", "generic", "Cholesterol, HDL"),
            ("hdl-c", "labcorp", "Cholesterol, HDL"),
        ]

        for test_name, vendor, expected in test_cases:
            result = harmonizer.harmonize_test_name(test_name, vendor)
            assert (
                result == expected
            ), f"Failed for {test_name} -> expected {expected}, got {result}"

    def test_harmonize_liver_function_tests(self):
        """Test harmonization of liver function test variations."""
        harmonizer = TestNameHarmonizer()

        test_cases = [
            ("alt", "generic", "Alanine Aminotransferase (ALT)"),
            ("alanine aminotransferase", "labcorp", "Alanine Aminotransferase (ALT)"),
            ("sgpt", "quest", "Alanine Aminotransferase (ALT)"),
            ("ast", "mayo", "Aspartate Aminotransferase (AST)"),
            (
                "aspartate aminotransferase",
                "generic",
                "Aspartate Aminotransferase (AST)",
            ),
            ("sgot", "labcorp", "Aspartate Aminotransferase (AST)"),
        ]

        for test_name, vendor, expected in test_cases:
            result = harmonizer.harmonize_test_name(test_name, vendor)
            assert result == expected

    def test_harmonize_kidney_function_tests(self):
        """Test harmonization of kidney function test variations."""
        harmonizer = TestNameHarmonizer()

        test_cases = [
            ("creatinine", "generic", "Creatinine"),
            ("creatinine, serum", "labcorp", "Creatinine"),
            ("CR", "mayo", "Creatinine"),
            ("bun", "quest", "Blood Urea Nitrogen"),
            ("urea nitrogen", "generic", "Blood Urea Nitrogen"),
            ("blood urea nitrogen", "labcorp", "Blood Urea Nitrogen"),
            ("egfr", "mayo", "eGFR"),
            ("estimated gfr", "generic", "eGFR"),
        ]

        for test_name, vendor, expected in test_cases:
            result = harmonizer.harmonize_test_name(test_name, vendor)
            assert result == expected

    def test_remove_arivale_suffixes(self):
        """Test removal of Arivale-specific suffixes."""
        harmonizer = TestNameHarmonizer()

        test_cases = [
            ("Glucose, Serum (2345-7)", "arivale", "Glucose"),
            ("ALT (1742-6)", "arivale", "Alanine Aminotransferase (ALT)"),
            ("Cholesterol, Total (2093-3)", "arivale", "Cholesterol, Total"),
        ]

        for test_name, vendor, expected in test_cases:
            result = harmonizer.harmonize_test_name(test_name, vendor)
            assert result == expected

    def test_handle_empty_or_null_names(self):
        """Test handling of empty or null test names."""
        harmonizer = TestNameHarmonizer()

        assert harmonizer.harmonize_test_name("", "generic") == ""
        assert harmonizer.harmonize_test_name(None, "labcorp") == ""
        assert harmonizer.harmonize_test_name("   ", "quest") == "   "


class TestUnitConverter:
    """Test unit conversion functionality."""

    def test_convert_glucose_mg_to_mmol(self):
        """Test glucose unit conversion from mg/dL to mmol/L."""
        converter = UnitConverter()

        # 100 mg/dL = 5.55 mmol/L
        value, unit = converter.standardize_unit(100, "mg/dL", "mmol/L", "glucose")
        assert abs(value - 5.55) < 0.01
        assert unit == "mmol/L"

    def test_convert_cholesterol_mg_to_mmol(self):
        """Test cholesterol unit conversion from mg/dL to mmol/L."""
        converter = UnitConverter()

        # 200 mg/dL = 5.17 mmol/L
        value, unit = converter.standardize_unit(200, "mg/dL", "mmol/L", "cholesterol")
        expected_value = 200 * 0.0259  # 5.18
        assert abs(value - expected_value) < 0.01
        assert unit == "mmol/L"

    def test_convert_creatinine_mg_to_umol(self):
        """Test creatinine unit conversion from mg/dL to umol/L."""
        converter = UnitConverter()

        # 1.0 mg/dL = 88.4 umol/L
        value, unit = converter.standardize_unit(1.0, "mg/dL", "umol/L", "creatinine")
        assert abs(value - 88.4) < 0.1
        assert unit == "umol/L"

    def test_convert_triglycerides_mg_to_mmol(self):
        """Test triglycerides unit conversion from mg/dL to mmol/L."""
        converter = UnitConverter()

        # 150 mg/dL = 1.695 mmol/L
        value, unit = converter.standardize_unit(
            150, "mg/dL", "mmol/L", "triglycerides"
        )
        expected_value = 150 * 0.0113  # 1.695
        assert abs(value - expected_value) < 0.01
        assert unit == "mmol/L"

    def test_convert_protein_g_to_gl(self):
        """Test protein unit conversion from g/dL to g/L."""
        converter = UnitConverter()

        # 7.0 g/dL = 70.0 g/L
        value, unit = converter.standardize_unit(7.0, "g/dL", "g/L", "protein")
        assert abs(value - 70.0) < 0.1
        assert unit == "g/L"

    def test_no_conversion_same_units(self):
        """Test no conversion when units are already the same."""
        converter = UnitConverter()

        value, unit = converter.standardize_unit(40, "U/L", "U/L", "enzyme")
        assert value == 40
        assert unit == "U/L"

    def test_no_conversion_missing_units(self):
        """Test handling of missing units."""
        converter = UnitConverter()

        value, unit = converter.standardize_unit(100, None, "mmol/L", "glucose")
        assert value == 100
        assert unit is None

    def test_get_standard_unit_si_system(self):
        """Test getting standard units for SI system."""
        converter = UnitConverter()

        test_cases = [
            ("Glucose", "SI", "mmol/L"),
            ("Cholesterol, Total", "SI", "mmol/L"),
            ("Creatinine", "SI", "umol/L"),
            ("Alanine Aminotransferase (ALT)", "SI", "U/L"),
            ("Albumin", "SI", "g/L"),
            ("Sodium", "SI", "mmol/L"),
        ]

        for test_name, system, expected_unit in test_cases:
            result = converter.get_standard_unit(test_name, system)
            assert result == expected_unit

    def test_get_standard_unit_us_system(self):
        """Test getting standard units for US system."""
        converter = UnitConverter()

        test_cases = [
            ("Glucose", "US", "mg/dL"),
            ("Cholesterol, Total", "US", "mg/dL"),
            ("Creatinine", "US", "mg/dL"),
            ("Albumin", "US", "g/dL"),
            ("Sodium", "US", "mEq/L"),
        ]

        for test_name, system, expected_unit in test_cases:
            result = converter.get_standard_unit(test_name, system)
            assert result == expected_unit


class TestReferenceRangeHarmonizer:
    """Test reference range harmonization functionality."""

    def test_parse_reference_range_dash_format(self):
        """Test parsing dash-separated reference ranges."""
        harmonizer = ReferenceRangeHarmonizer()

        test_cases = [
            ("70-100", (70.0, 100.0)),
            ("3.9-5.6", (3.9, 5.6)),
            ("0.5-1.2", (0.5, 1.2)),
            ("10-40", (10.0, 40.0)),
        ]

        for range_str, expected in test_cases:
            result = harmonizer.parse_reference_range(range_str, "generic")
            assert result == expected

    def test_parse_reference_range_to_format(self):
        """Test parsing 'to' separated reference ranges."""
        harmonizer = ReferenceRangeHarmonizer()

        test_cases = [
            ("70 to 100", (70.0, 100.0)),
            ("3.9 to 5.6", (3.9, 5.6)),
            ("0.5to1.2", (0.5, 1.2)),
        ]

        for range_str, expected in test_cases:
            result = harmonizer.parse_reference_range(range_str, "generic")
            assert result == expected

    def test_parse_reference_range_inequality_formats(self):
        """Test parsing inequality reference ranges."""
        harmonizer = ReferenceRangeHarmonizer()

        test_cases = [
            ("<100", (0, 100.0)),
            (">70", (70.0, float("inf"))),
            ("≤100", (0, 100.0)),
            ("≥70", (70.0, float("inf"))),
        ]

        for range_str, expected in test_cases:
            result = harmonizer.parse_reference_range(range_str, "generic")
            assert result == expected

    def test_parse_invalid_reference_ranges(self):
        """Test parsing invalid or empty reference ranges."""
        harmonizer = ReferenceRangeHarmonizer()

        test_cases = ["", None, "invalid", "text only", "70-", "-100"]

        for range_str in test_cases:
            result = harmonizer.parse_reference_range(range_str, "generic")
            assert result == (None, None)

    def test_harmonize_standard_reference_ranges(self):
        """Test harmonization using standard reference ranges."""
        harmonizer = ReferenceRangeHarmonizer()

        # Test glucose in normal range
        result = harmonizer.harmonize_reference_range(
            "Glucose", 5.0, "70-100 mg/dL", "labcorp"
        )
        assert result["low"] == 3.9
        assert result["high"] == 5.6
        assert result["in_range"] is True
        assert result["standard_unit"] == "mmol/L"

    def test_flag_out_of_range_values_high(self):
        """Test flagging high out-of-range values."""
        harmonizer = ReferenceRangeHarmonizer()

        # Glucose 10.0 mmol/L is high (normal: 3.9-5.6)
        result = harmonizer.harmonize_reference_range("Glucose", 10.0, "", "generic")
        assert result["in_range"] is False

    def test_flag_out_of_range_values_low(self):
        """Test flagging low out-of-range values."""
        harmonizer = ReferenceRangeHarmonizer()

        # Glucose 2.0 mmol/L is low (normal: 3.9-5.6)
        result = harmonizer.harmonize_reference_range("Glucose", 2.0, "", "generic")
        assert result["in_range"] is False

    def test_harmonize_unknown_test_fallback(self):
        """Test fallback to vendor range for unknown tests."""
        harmonizer = ReferenceRangeHarmonizer()

        result = harmonizer.harmonize_reference_range(
            "Unknown Test", 50, "40-60", "generic"
        )
        assert result["low"] == 40
        assert result["high"] == 60
        assert result["in_range"] is True


class TestChemistryVendorHarmonizationParams:
    """Test parameter validation."""

    def test_valid_parameters(self):
        """Test valid parameter combinations."""
        params = ChemistryVendorHarmonizationParams(
            input_key="raw_data", output_key="harmonized_data"
        )
        assert params.input_key == "raw_data"
        assert params.output_key == "harmonized_data"
        assert params.vendor == "auto"
        assert params.target_unit_system == "SI"

    def test_custom_parameters(self):
        """Test custom parameter values."""
        params = ChemistryVendorHarmonizationParams(
            input_key="input",
            output_key="output",
            vendor="labcorp",
            target_unit_system="US",
            standardize_test_names=False,
        )
        assert params.vendor == "labcorp"
        assert params.target_unit_system == "US"
        assert params.standardize_test_names is False


class TestChemistryVendorHarmonizationAction:
    """Test the main harmonization action."""

    @pytest.fixture
    def sample_labcorp_data(self):
        """Sample LabCorp data for testing."""
        return pd.DataFrame(
            {
                "test_name": [
                    "GLUCOSE",
                    "CHOLESTEROL, TOTAL",
                    "LDL CHOLESTEROL",
                    "ALT",
                ],
                "value": [95, 180, 120, 25],
                "unit": ["mg/dL", "mg/dL", "mg/dL", "U/L"],
                "reference_range": ["70-100", "0-200", "0-130", "0-40"],
            }
        )

    @pytest.fixture
    def sample_quest_data(self):
        """Sample Quest data for testing."""
        return pd.DataFrame(
            {
                "test_name": [
                    "Glucose",
                    "Total Cholesterol",
                    "LDL-C",
                    "Alanine Aminotransferase",
                ],
                "value": [5.3, 4.7, 3.1, 30],
                "unit": ["mmol/L", "mmol/L", "mmol/L", "U/L"],
                "reference_range": ["3.9-5.6", "0-5.2", "0-3.4", "0-40"],
            }
        )

    @pytest.fixture
    def sample_arivale_data(self):
        """Sample Arivale data for testing."""
        return pd.DataFrame(
            {
                "test_name": [
                    "Glucose, Serum (2345-7)",
                    "ALT (1742-6)",
                    "Cholesterol, Total (2093-3)",
                ],
                "value": [100, 35, 190],
                "unit": ["mg/dL", "U/L", "mg/dL"],
                "reference_range": ["70-100", "0-40", "0-200"],
            }
        )

    @pytest.fixture
    def sample_mixed_vendor_data(self):
        """Mixed vendor data for testing cross-vendor harmonization."""
        return pd.DataFrame(
            {
                "test_name": ["GLUCOSE", "GLU", "Glucose, Serum"],
                "vendor": ["labcorp", "mayo", "arivale"],
                "value": [95, 5.3, 100],
                "unit": ["mg/dL", "mmol/L", "mg/dL"],
            }
        )

    def test_action_registration(self):
        """Test that action is properly registered."""
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

        assert "CHEMISTRY_VENDOR_HARMONIZATION" in ACTION_REGISTRY

    def test_get_params_model(self):
        """Test parameter model retrieval."""
        action = ChemistryVendorHarmonizationAction()
        params_model = action.get_params_model()
        assert params_model == ChemistryVendorHarmonizationParams

    def test_get_result_model(self):
        """Test result model retrieval."""
        action = ChemistryVendorHarmonizationAction()
        result_model = action.get_result_model()
        assert result_model == ChemistryVendorHarmonizationResult

    def test_harmonize_labcorp_data(self, sample_labcorp_data):
        """Test harmonization of LabCorp data."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="labcorp_data", output_key="harmonized_data", vendor="labcorp"
        )

        context = {"datasets": {"labcorp_data": sample_labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        assert result.total_tests == 4
        assert result.harmonized_tests == 4
        assert "labcorp" in result.vendors_processed
        assert len(result.unit_conversions) > 0  # Should have conversions

    def test_harmonize_quest_data(self, sample_quest_data):
        """Test harmonization of Quest data."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="quest_data", output_key="harmonized_data", vendor="quest"
        )

        context = {"datasets": {"quest_data": sample_quest_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        assert result.total_tests == 4
        assert "quest" in result.vendors_processed

    def test_harmonize_arivale_data(self, sample_arivale_data):
        """Test harmonization of Arivale data."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="arivale_data", output_key="harmonized_data", vendor="arivale"
        )

        context = {"datasets": {"arivale_data": sample_arivale_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        # Should handle Arivale suffix removal
        harmonized_df = context["datasets"]["harmonized_data"]
        assert "test_name_harmonized" in harmonized_df.columns

    def test_auto_vendor_detection(self, sample_labcorp_data):
        """Test automatic vendor detection."""
        # Add test_code column for LabCorp detection
        sample_labcorp_data["test_code"] = [
            "LC001453",
            "LC001123",
            "LC001172",
            "LC001742",
        ]

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="auto_data",
            output_key="harmonized_data",
            vendor="auto",  # Should detect as labcorp
        )

        context = {"datasets": {"auto_data": sample_labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        assert "labcorp" in result.vendors_processed

    def test_harmonize_mixed_vendors(self, sample_mixed_vendor_data):
        """Test harmonization of mixed vendor data."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="mixed_data",
            output_key="harmonized_data",
            vendors=["labcorp", "mayo", "arivale"],
            vendor_column="vendor",
        )

        context = {
            "datasets": {"mixed_data": sample_mixed_vendor_data},
            "statistics": {},
        }

        result = action.execute_typed(params, context)

        assert result.success is True
        # All should harmonize to same test name
        harmonized_df = context["datasets"]["harmonized_data"]
        unique_test_names = harmonized_df["test_name_harmonized"].unique()
        assert len(unique_test_names) == 1  # All should be "Glucose"

    def test_unit_standardization_si_system(self, sample_labcorp_data):
        """Test unit standardization to SI system."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="test_data",
            output_key="harmonized_data",
            target_unit_system="SI",
            standardize_units=True,
        )

        context = {"datasets": {"test_data": sample_labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        harmonized_df = context["datasets"]["harmonized_data"]

        # Check glucose conversion: 95 mg/dL -> ~5.27 mmol/L
        glucose_row = harmonized_df[
            harmonized_df["test_name_harmonized"] == "Glucose"
        ].iloc[0]
        assert abs(glucose_row["value_standardized"] - 5.27) < 0.1
        assert glucose_row["unit_standardized"] == "mmol/L"

    def test_preserve_original_values(self, sample_labcorp_data):
        """Test preservation of original values."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="test_data", output_key="harmonized_data", preserve_original=True
        )

        context = {"datasets": {"test_data": sample_labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        harmonized_df = context["datasets"]["harmonized_data"]
        assert "test_name_original" in harmonized_df.columns
        assert "value_original" in harmonized_df.columns
        assert "unit_original" in harmonized_df.columns

    def test_flag_out_of_range_values(self, sample_labcorp_data):
        """Test flagging of out-of-range values."""
        # Create data with out-of-range glucose value
        out_of_range_data = sample_labcorp_data.copy()
        out_of_range_data.loc[0, "value"] = 200  # High glucose

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="test_data", output_key="harmonized_data", flag_out_of_range=True
        )

        context = {"datasets": {"test_data": out_of_range_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        harmonized_df = context["datasets"]["harmonized_data"]
        assert "in_range" in harmonized_df.columns

        # Glucose should be flagged as out of range
        glucose_row = harmonized_df[
            harmonized_df["test_name_harmonized"] == "Glucose"
        ].iloc[0]
        assert glucose_row["in_range"] == False

    def test_handle_missing_data(self):
        """Test handling of missing data."""
        missing_data = pd.DataFrame(
            {
                "test_name": ["GLUCOSE", None, ""],
                "value": [95, None, 120],
                "unit": ["mg/dL", None, ""],
            }
        )

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="missing_data", output_key="harmonized_data"
        )

        context = {"datasets": {"missing_data": missing_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        assert result.success is True
        # Should handle missing values gracefully

    def test_performance_large_dataset(self):
        """Test performance with large dataset (1000 tests)."""
        # Create large dataset
        large_data = pd.DataFrame(
            {
                "test_name": ["GLUCOSE"] * 1000,
                "value": [95 + i % 50 for i in range(1000)],
                "unit": ["mg/dL"] * 1000,
                "reference_range": ["70-100"] * 1000,
            }
        )

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="large_data", output_key="harmonized_data"
        )

        context = {"datasets": {"large_data": large_data}, "statistics": {}}

        import time

        start_time = time.time()

        result = action.execute_typed(params, context)

        end_time = time.time()
        execution_time = end_time - start_time

        assert result.success is True
        assert execution_time < 6.0  # Should complete in < 6 seconds
        assert result.total_tests == 1000

    def test_error_handling_invalid_input_key(self):
        """Test error handling for invalid input key."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="nonexistent_data", output_key="harmonized_data"
        )

        context = {"datasets": {}, "statistics": {}}

        with pytest.raises(KeyError):
            action.execute_typed(params, context)

    def test_error_handling_missing_columns(self):
        """Test error handling for missing required columns."""
        invalid_data = pd.DataFrame({"wrong_column": ["test1", "test2"]})

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="invalid_data",
            output_key="harmonized_data",
            test_name_column="test_name",  # Column doesn't exist
        )

        context = {"datasets": {"invalid_data": invalid_data}, "statistics": {}}

        with pytest.raises(KeyError):
            action.execute_typed(params, context)

    def test_add_harmonization_metadata(self, sample_labcorp_data):
        """Test addition of harmonization metadata."""
        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="test_data",
            output_key="harmonized_data",
            add_harmonization_log=True,
        )

        context = {"datasets": {"test_data": sample_labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        harmonized_df = context["datasets"]["harmonized_data"]
        assert "vendor_detected" in harmonized_df.columns
        assert "harmonization_timestamp" in harmonized_df.columns

    def test_result_statistics_calculation(self):
        """Test calculation of result statistics."""
        # This will be tested as part of the main action tests
        pass


class TestFullHarmonizationPipeline:
    """Integration tests for the complete harmonization pipeline."""

    def test_full_pipeline_labcorp_to_si(self):
        """Test complete pipeline: LabCorp data -> SI units."""
        labcorp_data = pd.DataFrame(
            {
                "test_code": ["LC001453", "LC001123", "LC001172"],
                "test_name": ["GLUCOSE", "CHOLESTEROL, TOTAL", "LDL CHOLESTEROL"],
                "value": [95, 180, 120],
                "unit": ["mg/dL", "mg/dL", "mg/dL"],
                "reference_range": ["70-100", "0-200", "0-130"],
            }
        )

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="raw_labcorp",
            output_key="harmonized_si",
            vendor="auto",  # Should detect as labcorp
            target_unit_system="SI",
            standardize_test_names=True,
            standardize_units=True,
            standardize_reference_ranges=True,
            flag_out_of_range=True,
            preserve_original=True,
            add_harmonization_log=True,
        )

        context = {"datasets": {"raw_labcorp": labcorp_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        # Verify success
        assert result.success is True
        assert result.total_tests == 3
        assert result.harmonized_tests == 3
        assert "labcorp" in result.vendors_processed

        # Verify harmonized data
        harmonized_df = context["datasets"]["harmonized_si"]

        # Check test name harmonization
        expected_names = ["Glucose", "Cholesterol, Total", "Cholesterol, LDL"]
        assert set(harmonized_df["test_name_harmonized"]) == set(expected_names)

        # Check unit conversion
        glucose_row = harmonized_df[
            harmonized_df["test_name_harmonized"] == "Glucose"
        ].iloc[0]
        assert glucose_row["unit_standardized"] == "mmol/L"
        assert (
            abs(glucose_row["value_standardized"] - 5.27) < 0.1
        )  # 95 mg/dL -> ~5.27 mmol/L

        # Check reference ranges
        assert "reference_low" in harmonized_df.columns
        assert "reference_high" in harmonized_df.columns
        assert "in_range" in harmonized_df.columns

        # Check metadata
        assert "vendor_detected" in harmonized_df.columns
        assert "harmonization_timestamp" in harmonized_df.columns

        # Check original data preservation
        assert "test_name_original" in harmonized_df.columns
        assert "value_original" in harmonized_df.columns
        assert "unit_original" in harmonized_df.columns

        # Verify statistics
        assert "vendor_harmonization" in context["statistics"]
        stats = context["statistics"]["vendor_harmonization"]
        assert stats["total_tests"] == 3
        assert stats["harmonized_tests"] == 3

    def test_cross_vendor_consistency(self):
        """Test that same tests from different vendors harmonize consistently."""
        # Create equivalent test data from different vendors
        vendor_data = []

        # LabCorp format
        labcorp_data = pd.DataFrame(
            {
                "test_name": ["GLUCOSE", "CHOLESTEROL, TOTAL"],
                "value": [95, 180],
                "unit": ["mg/dL", "mg/dL"],
                "vendor": ["labcorp", "labcorp"],
            }
        )

        # Quest format
        quest_data = pd.DataFrame(
            {
                "test_name": ["Glucose", "Total Cholesterol"],
                "value": [5.27, 4.66],  # Already in SI units
                "unit": ["mmol/L", "mmol/L"],
                "vendor": ["quest", "quest"],
            }
        )

        # Arivale format
        arivale_data = pd.DataFrame(
            {
                "test_name": ["Glucose, Serum (2345-7)", "Cholesterol, Total (2093-3)"],
                "value": [95, 180],
                "unit": ["mg/dL", "mg/dL"],
                "vendor": ["arivale", "arivale"],
            }
        )

        # Combine all data
        combined_data = pd.concat(
            [labcorp_data, quest_data, arivale_data], ignore_index=True
        )

        action = ChemistryVendorHarmonizationAction()
        params = ChemistryVendorHarmonizationParams(
            input_key="multi_vendor",
            output_key="harmonized",
            vendor_column="vendor",
            target_unit_system="SI",
        )

        context = {"datasets": {"multi_vendor": combined_data}, "statistics": {}}

        result = action.execute_typed(params, context)

        harmonized_df = context["datasets"]["harmonized"]

        # All glucose tests should have same harmonized name
        glucose_tests = harmonized_df[
            harmonized_df["test_name_harmonized"] == "Glucose"
        ]
        assert len(glucose_tests) == 3

        # All cholesterol tests should have same harmonized name
        chol_tests = harmonized_df[
            harmonized_df["test_name_harmonized"] == "Cholesterol, Total"
        ]
        assert len(chol_tests) == 3

        # Values should be in same units after harmonization
        glucose_units = glucose_tests["unit_standardized"].unique()
        assert len(glucose_units) == 1  # All should be same unit
        assert glucose_units[0] == "mmol/L"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

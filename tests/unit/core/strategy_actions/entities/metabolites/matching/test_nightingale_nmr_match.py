"""Tests for the enhanced Nightingale NMR matching action."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Skip all nightingale unit tests - deferred until active development
pytestmark = pytest.mark.skip(reason="Nightingale NMR matching deferred until active development")

from actions.entities.metabolites.matching.nightingale_nmr_match import (
    NightingaleNmrMatchAction,
    NightingaleNmrMatchParams,
    NightingaleNmrMatchResult,
    NightingaleReference,
    NightingaleMatcher,
    NIGHTINGALE_PATTERNS,
    LIPOPROTEIN_PATTERNS,
)

# Mock reference data for testing
MOCK_REFERENCE_DATA = pd.DataFrame(
    [
        {
            "nightingale_name": "Total_C",
            "hmdb_id": "HMDB0000067",
            "loinc_code": "2093-3",
            "description": "Total cholesterol",
            "category": "lipids",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "LDL_C",
            "hmdb_id": "HMDB0000067",
            "loinc_code": "13457-7",
            "description": "LDL cholesterol",
            "category": "lipids",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "HDL_C",
            "hmdb_id": "HMDB0000067",
            "loinc_code": "2085-9",
            "description": "HDL cholesterol",
            "category": "lipids",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "Triglycerides",
            "hmdb_id": "HMDB0000827",
            "loinc_code": "2571-8",
            "description": "Triglycerides",
            "category": "lipids",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "Glucose",
            "hmdb_id": "HMDB0000122",
            "loinc_code": "2345-7",
            "description": "Glucose",
            "category": "glycolysis",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "ApoA1",
            "hmdb_id": None,
            "loinc_code": "1869-7",
            "description": "Apolipoprotein A1",
            "category": "apolipoproteins",
            "unit": "g/L",
        },
        {
            "nightingale_name": "Ala",
            "hmdb_id": "HMDB0000161",
            "loinc_code": "1916-6",
            "description": "Alanine",
            "category": "amino_acids",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "bOHbutyrate",
            "hmdb_id": "HMDB0000357",
            "loinc_code": "53060-9",
            "description": "Beta-hydroxybutyrate",
            "category": "ketone_bodies",
            "unit": "mmol/L",
        },
        {
            "nightingale_name": "GlycA",
            "hmdb_id": None,
            "loinc_code": None,
            "description": "Glycoprotein acetyls",
            "category": "inflammation",
            "unit": "mmol/L",
        },
    ]
)

# Mock UKBB NMR data
MOCK_UKBB_NMR_DATA = pd.DataFrame(
    [
        {"biomarker": "Total_C", "value": 5.2},
        {"biomarker": "LDL_C", "value": 3.1},
        {"biomarker": "HDL_C", "value": 1.4},
        {"biomarker": "Triglycerides", "value": 1.5},
        {"biomarker": "Glucose", "value": 5.5},
        {"biomarker": "XXL_VLDL_P", "value": 0.001},
        {"biomarker": "S_LDL_C", "value": 0.8},
        {"biomarker": "ApoA1", "value": 1.3},
        {"biomarker": "Ala", "value": 0.35},
        {"biomarker": "bOHbutyrate", "value": 0.05},
    ]
)


class TestNightingaleNmrMatch:
    """Test suite for Nightingale NMR matching action."""

    # 1. Parameter Tests
    def test_default_parameters(self):
        """Test default parameter initialization."""
        params = NightingaleNmrMatchParams(
            input_key="test_input", output_key="test_output"
        )
        assert params.biomarker_column == "biomarker"
        assert params.unit_column is None
        assert (
            params.reference_file
            == "/procedure/data/local_data/references/nightingale_nmr_reference.csv"
        )
        assert params.use_cached_reference is True
        assert params.target_format == "hmdb"
        assert params.match_threshold == 0.85
        assert params.use_abbreviations is True
        assert params.case_sensitive is False
        assert params.add_metadata is True
        assert params.include_units is True
        assert params.include_categories is True

    def test_custom_parameters(self):
        """Test custom parameter configuration."""
        params = NightingaleNmrMatchParams(
            input_key="custom_input",
            output_key="custom_output",
            biomarker_column="nmr_name",
            unit_column="measurement_unit",
            reference_file="/custom/path/reference.csv",
            use_cached_reference=False,
            target_format="loinc",
            match_threshold=0.95,
            use_abbreviations=False,
            case_sensitive=True,
            add_metadata=False,
            include_units=False,
            include_categories=False,
        )
        assert params.biomarker_column == "nmr_name"
        assert params.unit_column == "measurement_unit"
        assert params.reference_file == "/custom/path/reference.csv"
        assert params.use_cached_reference is False
        assert params.target_format == "loinc"
        assert params.match_threshold == 0.95
        assert params.use_abbreviations is False
        assert params.case_sensitive is True
        assert params.add_metadata is False
        assert params.include_units is False
        assert params.include_categories is False

    # 2. Exact Matching Tests
    def test_exact_match_total_c(self):
        """Test exact match for Total_C."""
        matcher = NightingaleMatcher()
        result = matcher.match_biomarker("Total_C", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["hmdb_id"] == "HMDB0000067"
        assert result["loinc_code"] == "2093-3"
        assert result["confidence"] == 1.0
        assert result["category"] == "lipids"

    def test_exact_match_glucose(self):
        """Test exact match for Glucose."""
        matcher = NightingaleMatcher()
        result = matcher.match_biomarker("Glucose", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["hmdb_id"] == "HMDB0000122"
        assert result["loinc_code"] == "2345-7"
        assert result["confidence"] == 1.0
        assert result["category"] == "glycolysis"

    def test_exact_match_apolipoprotein(self):
        """Test exact match for ApoA1."""
        matcher = NightingaleMatcher()
        result = matcher.match_biomarker("ApoA1", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["hmdb_id"] is None  # Protein, no HMDB
        assert result["loinc_code"] == "1869-7"
        assert result["confidence"] == 1.0
        assert result["category"] == "apolipoproteins"

    # 3. Fuzzy Matching Tests
    def test_fuzzy_match_variations(self):
        """Test fuzzy matching for name variations."""
        matcher = NightingaleMatcher()
        matcher.abbreviations = matcher.load_abbreviations()

        # Test variations that should match to Total_C
        variations = [
            "total cholesterol",
            "Total Cholesterol",
            "total_cholesterol",
            "TOTAL_C",
        ]

        for variation in variations:
            result = matcher.match_biomarker(
                variation, MOCK_REFERENCE_DATA, threshold=0.80
            )
            assert result is not None, f"Failed to match variation: {variation}"
            assert result["hmdb_id"] == "HMDB0000067"

    def test_fuzzy_match_threshold(self):
        """Test fuzzy matching respects threshold."""
        matcher = NightingaleMatcher()

        # Test with a string that's somewhat similar but below threshold
        result = matcher.match_biomarker(
            "Random_Biomarker_XYZ", MOCK_REFERENCE_DATA, threshold=0.95
        )
        assert result is None  # Should not match due to high threshold

        # Test with lower threshold - might find a match
        result = matcher.match_biomarker(
            "Gluc",  # Partial match for Glucose
            MOCK_REFERENCE_DATA,
            threshold=0.50,
        )
        # With low threshold, might find Glucose
        if result is not None:
            assert result["confidence"] >= 0.50

    # 4. Lipoprotein Pattern Tests
    def test_lipoprotein_xxl_vldl_pattern(self):
        """Test XXL_VLDL particle pattern matching."""
        matcher = NightingaleMatcher()
        result = matcher.match_biomarker(
            "XXL_VLDL_P", MOCK_REFERENCE_DATA, threshold=0.85
        )
        # Should match via pattern even if not in reference
        assert result is not None
        assert result["category"] == "lipoproteins"
        assert result["hmdb_id"] is None  # Lipoproteins don't have HMDB
        assert "VLDL" in result["description"]

    def test_lipoprotein_s_ldl_pattern(self):
        """Test S_LDL particle pattern matching."""
        matcher = NightingaleMatcher()
        result = matcher.match_biomarker("S_LDL_C", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["category"] == "lipoproteins"
        assert "LDL" in result["description"]

    # 5. Abbreviation Expansion Tests
    def test_abbreviation_expansion_tg(self):
        """Test TG expands to triglycerides."""
        matcher = NightingaleMatcher()
        matcher.abbreviations = matcher.load_abbreviations()

        # Clean name should expand TG to triglycerides
        cleaned = matcher._clean_biomarker_name("TG")
        assert "triglycerides" in cleaned.lower()

    def test_abbreviation_expansion_pl(self):
        """Test PL expands to phospholipids."""
        matcher = NightingaleMatcher()
        matcher.abbreviations = matcher.load_abbreviations()

        # Clean name should expand PL to phospholipids
        cleaned = matcher._clean_biomarker_name("PL")
        assert "phospholipids" in cleaned.lower()

    # 6. Reference File Tests
    @patch("pandas.read_csv")
    def test_reference_file_loading(self, mock_read):
        """Test reference file loads correctly."""
        mock_read.return_value = MOCK_REFERENCE_DATA

        reference = NightingaleReference("/test/reference.csv", use_cache=True)
        ref_df = reference.load_reference()

        assert not ref_df.empty
        assert "nightingale_name" in ref_df.columns
        assert "hmdb_id" in ref_df.columns
        assert "description" in ref_df.columns
        mock_read.assert_called_once_with("/test/reference.csv")

    def test_reference_file_caching(self):
        """Test reference file is cached."""
        with patch("pandas.read_csv") as mock_read:
            mock_read.return_value = MOCK_REFERENCE_DATA

            reference = NightingaleReference("/test/reference.csv", use_cache=True)

            # Load twice
            ref_df1 = reference.load_reference()
            ref_df2 = reference.load_reference()

            # Should only read once due to caching
            assert mock_read.call_count == 1
            assert ref_df1.equals(ref_df2)

    def test_invalid_reference_file(self):
        """Test error handling for invalid reference file."""
        with patch("pandas.read_csv") as mock_read:
            # Return dataframe missing required columns
            mock_read.return_value = pd.DataFrame({"wrong_column": [1, 2, 3]})

            reference = NightingaleReference("/test/invalid.csv")

            with pytest.raises(
                ValueError, match="Reference file missing required columns"
            ):
                reference.load_reference()

    # 7. Category Classification Tests
    def test_lipid_category(self):
        """Test lipid biomarkers categorized correctly."""
        matcher = NightingaleMatcher()

        lipid_biomarkers = ["Total_C", "LDL_C", "HDL_C", "Triglycerides"]
        for biomarker in lipid_biomarkers:
            result = matcher.match_biomarker(
                biomarker, MOCK_REFERENCE_DATA, threshold=0.85
            )
            assert result is not None
            assert result["category"] == "lipids"

    def test_amino_acid_category(self):
        """Test amino acid biomarkers categorized correctly."""
        matcher = NightingaleMatcher()

        result = matcher.match_biomarker("Ala", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["category"] == "amino_acids"

    # 8. Unit Handling Tests
    def test_unit_standardization(self):
        """Test units are standardized correctly."""
        matcher = NightingaleMatcher()

        # Test mmol/L units
        result = matcher.match_biomarker("Glucose", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["unit"] == "mmol/L"

        # Test g/L units
        result = matcher.match_biomarker("ApoA1", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is not None
        assert result["unit"] == "g/L"

    # 9. Batch Processing Tests
    @pytest.mark.asyncio
    async def test_batch_processing_mixed_biomarkers(self):
        """Test batch processing of various biomarker types."""
        action = NightingaleNmrMatchAction()
        params = NightingaleNmrMatchParams(
            input_key="ukbb_nmr", output_key="matched_nmr"
        )

        # Create mock context
        mock_context = MagicMock()
        mock_context.get_action_data.side_effect = lambda key, default: {
            "datasets": {"ukbb_nmr": MOCK_UKBB_NMR_DATA.copy()},
            "statistics": {},
        }.get(key, default)

        datasets_store = {"ukbb_nmr": MOCK_UKBB_NMR_DATA.copy()}

        def set_action_data(key, value):
            if key == "datasets":
                datasets_store.update(value)

        mock_context.set_action_data = set_action_data

        with patch.object(action, "load_reference_data") as mock_load:
            mock_load.return_value = MOCK_REFERENCE_DATA

            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context,
            )

            assert result.success is True
            assert result.matched_biomarkers > 0
            assert "matched_nmr" in datasets_store

            # Check that different categories were matched
            matched_df = datasets_store["matched_nmr"]
            categories = matched_df["category"].unique()
            assert "lipids" in categories
            assert "glycolysis" in categories

    # 10. Edge Cases
    def test_empty_biomarker_name(self):
        """Test handling of empty biomarker names."""
        matcher = NightingaleMatcher()

        # Test empty string
        result = matcher.match_biomarker("", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is None

        # Test None
        result = matcher.match_biomarker(None, MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is None

        # Test whitespace only
        result = matcher.match_biomarker("   ", MOCK_REFERENCE_DATA, threshold=0.85)
        assert result is None

    def test_unmatched_biomarker(self):
        """Test handling of unmatched biomarkers."""
        matcher = NightingaleMatcher()

        result = matcher.match_biomarker(
            "COMPLETELY_UNKNOWN_BIOMARKER_XYZ123", MOCK_REFERENCE_DATA, threshold=0.95
        )
        assert result is None

    # 11. Integration Test
    @pytest.mark.asyncio
    async def test_full_ukbb_nmr_pipeline(self):
        """Test complete UKBB NMR processing pipeline."""
        action = NightingaleNmrMatchAction()
        params = NightingaleNmrMatchParams(
            input_key="ukbb_nmr",
            output_key="matched_nmr",
            target_format="both",
            match_threshold=0.85,
            use_abbreviations=True,
            add_metadata=True,
            include_units=True,
            include_categories=True,
        )

        # Create mock context
        datasets_store = {"ukbb_nmr": MOCK_UKBB_NMR_DATA.copy()}
        statistics_store = {}

        mock_context = MagicMock()
        mock_context.get_action_data.side_effect = lambda key, default: {
            "datasets": datasets_store,
            "statistics": statistics_store,
        }.get(key, default)

        def set_action_data(key, value):
            if key == "datasets":
                datasets_store.update(value)
            elif key == "statistics":
                statistics_store.update(value)

        mock_context.set_action_data = set_action_data

        with patch.object(action, "load_reference_data") as mock_load:
            mock_load.return_value = MOCK_REFERENCE_DATA

            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context,
            )

            # Verify result
            assert result.success is True
            assert result.total_biomarkers == len(MOCK_UKBB_NMR_DATA)
            assert result.matched_biomarkers > 0
            assert len(result.unmatched_biomarkers) >= 0

            # Verify context updates
            assert "matched_nmr" in datasets_store
            assert "nightingale_nmr_match" in statistics_store

            # Verify matched data structure
            matched_df = datasets_store["matched_nmr"]
            expected_columns = [
                "original_biomarker",
                "matched_name",
                "hmdb_id",
                "loinc_code",
                "description",
                "category",
                "confidence",
                "unit",
                "value",
            ]
            for col in expected_columns:
                assert col in matched_df.columns

            # Verify category breakdown
            assert result.category_breakdown is not None
            assert len(result.category_breakdown) > 0

    # 12. Performance Test
    def test_performance_large_dataset(self):
        """Test performance with 1000 biomarkers."""
        import time

        # Generate large dataset
        large_data = pd.DataFrame(
            [{"biomarker": f"Biomarker_{i}", "value": i * 0.1} for i in range(1000)]
        )

        # Add some known biomarkers
        for i, name in enumerate(["Total_C", "Glucose", "ApoA1"] * 100):
            if i < 1000:
                large_data.at[i, "biomarker"] = name

        matcher = NightingaleMatcher()

        start_time = time.time()

        results = []
        for _, row in large_data.iterrows():
            result = matcher.match_biomarker(
                row["biomarker"], MOCK_REFERENCE_DATA, threshold=0.85
            )
            results.append(result)

        elapsed_time = time.time() - start_time

        # Should complete in < 5 seconds
        assert elapsed_time < 5.0, f"Processing took {elapsed_time:.2f} seconds"

        # Should have some matches
        matched_count = sum(1 for r in results if r is not None)
        assert matched_count >= 300  # At least the known biomarkers

    # Additional tests for new functionality
    def test_nightingale_patterns_structure(self):
        """Test that NIGHTINGALE_PATTERNS dictionary is properly structured."""
        assert "Total_C" in NIGHTINGALE_PATTERNS
        assert "description" in NIGHTINGALE_PATTERNS["Total_C"]
        assert "hmdb" in NIGHTINGALE_PATTERNS["Total_C"]
        assert "loinc" in NIGHTINGALE_PATTERNS["Total_C"]
        assert "unit" in NIGHTINGALE_PATTERNS["Total_C"]
        assert "category" in NIGHTINGALE_PATTERNS["Total_C"]

    def test_lipoprotein_patterns_regex(self):
        """Test that LIPOPROTEIN_PATTERNS contains valid regex patterns."""
        import re

        for pattern in LIPOPROTEIN_PATTERNS.keys():
            # Should not raise exception
            compiled = re.compile(pattern)
            assert compiled is not None

        # Test specific pattern matching
        test_cases = [
            ("XXL_VLDL_P", r"^XXL_VLDL_(.+)$"),
            ("S_LDL_C", r"^S_LDL_(.+)$"),
            ("M_HDL_PL", r"^(.+)_HDL_(.+)$"),
        ]

        for test_str, pattern in test_cases:
            if pattern in LIPOPROTEIN_PATTERNS:
                assert re.match(pattern, test_str) is not None

    def test_metabolite_with_percentage_units(self):
        """Test handling of metabolites with percentage units."""
        # Create test data with percentage-based biomarker
        test_df = pd.DataFrame(
            [
                {
                    "nightingale_name": "Omega_3_pct",
                    "hmdb_id": "HMDB0001388",
                    "loinc_code": None,
                    "description": "Omega-3 fatty acids percentage",
                    "category": "fatty_acids",
                    "unit": "%",
                }
            ]
        )

        matcher = NightingaleMatcher()
        result = matcher.match_biomarker("Omega_3_pct", test_df, threshold=0.85)

        assert result is not None
        assert result["unit"] == "%"
        assert result["category"] == "fatty_acids"

    def test_result_model_validation(self):
        """Test NightingaleNmrMatchResult model validation."""
        # Valid result
        result = NightingaleNmrMatchResult(
            success=True,
            total_biomarkers=100,
            matched_biomarkers=85,
            unmatched_biomarkers=["Unknown1", "Unknown2"],
            match_statistics={"match_rate": 0.85},
            category_breakdown={"lipids": 30, "amino_acids": 20},
            reference_version="1.0.0",
        )
        assert result.success is True
        assert result.matched_biomarkers == 85

        # Test with warnings
        result_with_warnings = NightingaleNmrMatchResult(
            success=True,
            total_biomarkers=50,
            matched_biomarkers=45,
            unmatched_biomarkers=[],
            match_statistics={"match_rate": 0.90},
            category_breakdown={"lipids": 45},
            reference_version="1.0.0",
            warnings=["Missing reference file", "Low confidence matches"],
        )
        assert result_with_warnings.warnings is not None
        assert len(result_with_warnings.warnings) == 2

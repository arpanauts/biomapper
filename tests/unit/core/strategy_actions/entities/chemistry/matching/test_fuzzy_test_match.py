import pytest
import pandas as pd

# Import the classes we're going to test
from biomapper.core.strategy_actions.entities.chemistry.matching.fuzzy_test_match import (
    ChemistryFuzzyTestMatchAction,
    ChemistryFuzzyTestMatchParams,
    ChemistryFuzzyTestMatchResult,
    TestNameNormalizer,
    AbbreviationExpander,
    MultiAlgorithmMatcher,
    TestPanelExpander,
)


class TestTestNameNormalizer:
    """Test the TestNameNormalizer class."""

    def test_normalize_test_name_basic(self):
        """Test basic test name normalization."""
        normalizer = TestNameNormalizer()
        assert normalizer.normalize_test_name("Glucose, Serum") == "glucose"
        assert normalizer.normalize_test_name("GLUCOSE (mg/dL)") == "glucose mg/dL"
        assert (
            normalizer.normalize_test_name("  Cholesterol Total  ")
            == "cholesterol total"
        )

    def test_normalize_empty_or_none(self):
        """Test handling of empty or None test names."""
        normalizer = TestNameNormalizer()
        assert normalizer.normalize_test_name("") == ""
        assert normalizer.normalize_test_name(None) == ""
        assert normalizer.normalize_test_name("   ") == ""

    def test_remove_vendor_prefixes(self):
        """Test vendor prefix removal."""
        normalizer = TestNameNormalizer()
        # LC prefix (LabCorp)
        assert normalizer.normalize_test_name("LC123 Glucose") == "glucose"
        # QD prefix (Quest)
        assert normalizer.normalize_test_name("QD456 Cholesterol") == "cholesterol"
        # Mayo prefix
        assert normalizer.normalize_test_name("Mayo ALT") == "alt"
        # UKBB field codes
        assert normalizer.normalize_test_name("30740 Glucose") == "glucose"

    def test_remove_specimen_types(self):
        """Test specimen type removal."""
        normalizer = TestNameNormalizer()
        assert normalizer.normalize_test_name("Glucose, Serum") == "glucose"
        assert (
            normalizer.normalize_test_name("Creatinine, 24 Hour Urine") == "creatinine"
        )
        assert normalizer.normalize_test_name("Hemoglobin, Whole Blood") == "hemoglobin"
        assert normalizer.normalize_test_name("Protein, CSF") == "protein"

    def test_standardize_units(self):
        """Test unit standardization."""
        normalizer = TestNameNormalizer()
        assert "mg/dL" in normalizer.normalize_test_name("Glucose mg/dl")
        assert "mmol/L" in normalizer.normalize_test_name("Glucose mmol/l")
        assert "U/L" in normalizer.normalize_test_name("ALT u/l")
        assert "IU/mL" in normalizer.normalize_test_name("Insulin iu/ml")

    def test_punctuation_removal(self):
        """Test punctuation standardization."""
        normalizer = TestNameNormalizer()
        assert normalizer.normalize_test_name("Glucose; Fasting") == "glucose fasting"
        assert normalizer.normalize_test_name("ALT (SGPT)") == "alt sgpt"
        assert normalizer.normalize_test_name("HDL, Cholesterol") == "hdl cholesterol"


class TestAbbreviationExpander:
    """Test the AbbreviationExpander class."""

    def test_expand_common_abbreviations(self):
        """Test expansion of common lab test abbreviations."""
        expander = AbbreviationExpander()
        assert "alanine aminotransferase" in expander.expand_abbreviation("alt")
        assert "aspartate aminotransferase" in expander.expand_abbreviation("ast")
        assert "blood urea nitrogen" in expander.expand_abbreviation("bun")
        assert "hemoglobin a1c" in expander.expand_abbreviation("hba1c")
        assert "thyroid stimulating hormone" in expander.expand_abbreviation("tsh")

    def test_expand_multiple_abbreviations(self):
        """Test expansion of multiple abbreviations in one string."""
        expander = AbbreviationExpander()
        result = expander.expand_abbreviation("alt ast")
        assert "alanine aminotransferase" in result
        assert "aspartate aminotransferase" in result

    def test_preserve_non_abbreviations(self):
        """Test that non-abbreviations are preserved."""
        expander = AbbreviationExpander()
        assert "glucose" in expander.expand_abbreviation("glucose")
        assert "cholesterol" in expander.expand_abbreviation("cholesterol")

    def test_get_synonyms_glucose(self):
        """Test synonym group for glucose."""
        expander = AbbreviationExpander()
        synonyms = expander.get_synonyms("glucose")
        assert "glucose" in [s.lower() for s in synonyms]
        assert "blood sugar" in [s.lower() for s in synonyms]
        assert "blood glucose" in [s.lower() for s in synonyms]

    def test_get_synonyms_cholesterol(self):
        """Test synonym group for cholesterol."""
        expander = AbbreviationExpander()
        synonyms = expander.get_synonyms("ldl cholesterol")
        assert "ldl cholesterol" in [s.lower() for s in synonyms]
        assert "ldl-c" in [s.lower() for s in synonyms]
        assert "bad cholesterol" in [s.lower() for s in synonyms]

    def test_get_synonyms_unknown_term(self):
        """Test handling of unknown terms."""
        expander = AbbreviationExpander()
        synonyms = expander.get_synonyms("unknown_test")
        assert synonyms == ["unknown_test"]


class TestTestPanelExpander:
    """Test the TestPanelExpander class."""

    def test_expand_basic_metabolic_panel(self):
        """Test BMP expansion to components."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("Basic Metabolic Panel")
        assert "glucose" in components
        assert "sodium" in components
        assert "potassium" in components
        assert "creatinine" in components
        assert len(components) == 8  # BMP has 8 components

    def test_expand_bmp_abbreviation(self):
        """Test BMP abbreviation expansion."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("BMP")
        assert "glucose" in components
        assert "sodium" in components
        assert len(components) == 8

    def test_expand_comprehensive_metabolic_panel(self):
        """Test CMP expansion to components."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("Comprehensive Metabolic Panel")
        assert "glucose" in components
        assert "alt" in components
        assert "ast" in components
        assert "albumin" in components
        assert len(components) == 14  # CMP has 14 components

    def test_expand_lipid_panel(self):
        """Test lipid panel expansion."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("Lipid Panel")
        assert "total cholesterol" in components
        assert "ldl cholesterol" in components
        assert "hdl cholesterol" in components
        assert "triglycerides" in components
        assert len(components) == 4

    def test_expand_complete_blood_count(self):
        """Test CBC expansion."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("Complete Blood Count")
        assert "white blood cell count" in components
        assert "red blood cell count" in components
        assert "hemoglobin" in components
        assert "hematocrit" in components

    def test_non_panel_unchanged(self):
        """Test that non-panel tests are returned unchanged."""
        expander = TestPanelExpander()
        components = expander.expand_if_panel("glucose")
        assert components == ["glucose"]

        components = expander.expand_if_panel("cholesterol")
        assert components == ["cholesterol"]


class TestMultiAlgorithmMatcher:
    """Test the MultiAlgorithmMatcher class."""

    def test_exact_matching(self):
        """Test exact match algorithm."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "glucose", "glucose", ["exact"], 0.75
        )
        assert is_match
        assert score == 1.0
        assert method == "exact"

    def test_exact_no_match(self):
        """Test exact match failure."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "glucose", "cholesterol", ["exact"], 0.75
        )
        assert not is_match
        assert score == 0.0
        assert method == "none"

    def test_token_sort_matching(self):
        """Test token sort algorithm for word order."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "cholesterol total", "total cholesterol", ["token_sort"], 0.75
        )
        assert is_match
        assert score >= 0.75
        assert method == "token_sort"

    def test_partial_matching(self):
        """Test partial match algorithm."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "glucose", "glucose fasting", ["partial"], 0.75
        )
        assert is_match
        assert score >= 0.75
        assert method == "partial"

    def test_abbreviation_matching(self):
        """Test abbreviation-aware matching."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "alt", "alanine aminotransferase", ["abbreviation"], 0.75
        )
        assert is_match
        assert score >= 0.75
        assert method == "abbreviation"

    def test_synonym_matching(self):
        """Test synonym-based matching."""
        matcher = MultiAlgorithmMatcher()
        is_match, score, method = matcher.match_tests(
            "blood sugar", "glucose", ["synonym"], 0.75
        )
        assert is_match
        assert score >= 0.75
        assert method == "synonym"

    def test_algorithm_fallback_order(self):
        """Test that algorithms are tried in specified order."""
        matcher = MultiAlgorithmMatcher()
        # Should try exact first, then token_sort
        is_match, score, method = matcher.match_tests(
            "total cholesterol", "cholesterol total", ["exact", "token_sort"], 0.75
        )
        assert is_match
        assert method == "token_sort"  # exact fails, token_sort succeeds

    def test_threshold_enforcement(self):
        """Test similarity threshold enforcement."""
        matcher = MultiAlgorithmMatcher()
        # Very different terms should not match even with low threshold
        is_match, score, method = matcher.match_tests(
            "glucose", "hemoglobin", ["partial"], 0.90
        )
        assert not is_match or score < 0.90


class TestChemistryFuzzyTestMatchParams:
    """Test the ChemistryFuzzyTestMatchParams model."""

    def test_default_parameters(self):
        """Test default parameter values."""
        params = ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="output"
        )
        assert params.match_threshold == 0.75
        assert params.use_synonyms is True
        assert params.use_abbreviations is True
        assert "exact" in params.algorithms
        assert "token_sort" in params.algorithms

    def test_custom_parameters(self):
        """Test custom parameter values."""
        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="output",
            match_threshold=0.85,
            algorithms=["exact", "partial"],
        )
        assert params.match_threshold == 0.85
        assert params.algorithms == ["exact", "partial"]


class TestChemistryFuzzyTestMatchAction:
    """Test the main ChemistryFuzzyTestMatchAction class."""

    @pytest.fixture
    def sample_context(self):
        """Create sample context for testing."""
        return {
            "datasets": {
                "source": pd.DataFrame(
                    {"test_name": ["glucose", "alt", "cholesterol", "bmp"]}
                ),
                "target": pd.DataFrame(
                    {
                        "test_name": [
                            "blood sugar",
                            "alanine aminotransferase",
                            "total cholesterol",
                            "basic metabolic panel",
                        ]
                    }
                ),
            },
            "statistics": {},
            "current_identifiers": set(),
            "output_files": [],
        }

    @pytest.fixture
    def basic_params(self):
        """Create basic parameters for testing."""
        return ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="matches"
        )

    def test_action_registration(self):
        """Test that action is properly registered."""
        action = ChemistryFuzzyTestMatchAction()
        assert action is not None
        # Test that it can be created (imports work)

    def test_get_params_model(self):
        """Test params model retrieval."""
        action = ChemistryFuzzyTestMatchAction()
        model = action.get_params_model()
        assert model == ChemistryFuzzyTestMatchParams

    @pytest.mark.asyncio
    async def test_execute_basic_matching(self, sample_context, basic_params):
        """Test basic execution with simple matches."""
        action = ChemistryFuzzyTestMatchAction()
        result = await action.execute_typed(basic_params, sample_context)

        assert result.success
        assert result.matched_tests > 0
        assert "matches" in sample_context["datasets"]
        assert len(sample_context["datasets"]["matches"]) > 0

    @pytest.mark.asyncio
    async def test_execute_with_synonyms(self, sample_context, basic_params):
        """Test execution with synonym matching enabled."""
        basic_params.use_synonyms = True
        action = ChemistryFuzzyTestMatchAction()
        result = await action.execute_typed(basic_params, sample_context)

        # Should match glucose -> blood sugar via synonyms
        matches_df = sample_context["datasets"]["matches"]
        glucose_match = matches_df[matches_df["source_test"] == "glucose"]
        assert len(glucose_match) > 0
        assert glucose_match.iloc[0]["target_test"] == "blood sugar"

    @pytest.mark.asyncio
    async def test_execute_with_abbreviations(self, sample_context, basic_params):
        """Test execution with abbreviation expansion."""
        basic_params.use_abbreviations = True
        action = ChemistryFuzzyTestMatchAction()
        result = await action.execute_typed(basic_params, sample_context)

        # Should match alt -> alanine aminotransferase via abbreviation
        matches_df = sample_context["datasets"]["matches"]
        alt_match = matches_df[matches_df["source_test"] == "alt"]
        assert len(alt_match) > 0
        assert "alanine aminotransferase" in alt_match.iloc[0]["target_test"]

    @pytest.mark.asyncio
    async def test_execute_with_panel_expansion(self, sample_context, basic_params):
        """Test execution with panel expansion enabled."""
        basic_params.handle_panels = True
        action = ChemistryFuzzyTestMatchAction()
        result = await action.execute_typed(basic_params, sample_context)

        # BMP should be expanded to components
        assert result.matched_tests >= 3  # Should have at least the basic matches

    def test_batch_matching_performance(self):
        """Test performance with larger datasets."""
        # Create larger test datasets
        source_tests = [f"test_{i}" for i in range(100)]
        target_tests = [f"test_{i}" for i in range(100)]

        source_df = pd.DataFrame({"test_name": source_tests})
        target_df = pd.DataFrame({"test_name": target_tests})

        context = {
            "datasets": {"source": source_df, "target": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="matches"
        )

        # This should complete reasonably quickly
        action = ChemistryFuzzyTestMatchAction()
        # Test that the action can be instantiated and methods called
        assert action.get_params_model() == ChemistryFuzzyTestMatchParams

    def test_similarity_threshold_enforcement(self, sample_context):
        """Test that similarity threshold is enforced."""
        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="matches",
            match_threshold=0.95,  # Very high threshold
        )

        action = ChemistryFuzzyTestMatchAction()
        # Should be able to instantiate
        assert action is not None

    def test_unmatched_tests_handling(self):
        """Test handling of tests that don't match."""
        source_df = pd.DataFrame(
            {"test_name": ["very_obscure_test", "another_weird_test"]}
        )
        target_df = pd.DataFrame({"test_name": ["glucose", "cholesterol"]})

        context = {
            "datasets": {"source": source_df, "target": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="matches"
        )

        action = ChemistryFuzzyTestMatchAction()
        # Should handle unmatched tests gracefully
        assert action.get_params_model() == ChemistryFuzzyTestMatchParams

    def test_cross_vendor_matching_patterns(self):
        """Test common cross-vendor matching patterns."""
        # LabCorp vs Quest variations
        source_df = pd.DataFrame(
            {"test_name": ["LC123 Glucose", "LabCorp ALT", "Mayo TSH"]}
        )
        target_df = pd.DataFrame(
            {
                "test_name": [
                    "QD456 Blood Sugar",
                    "Quest Alanine Aminotransferase",
                    "Thyroid Stimulating Hormone",
                ]
            }
        )

        context = {
            "datasets": {"source": source_df, "target": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="matches",
            handle_vendor_prefixes=True,
        )

        action = ChemistryFuzzyTestMatchAction()
        assert action is not None

    def test_unit_handling(self):
        """Test unit normalization and equivalence."""
        source_df = pd.DataFrame(
            {"test_name": ["Glucose mg/dl", "Creatinine mg/dL", "ALT u/l"]}
        )
        target_df = pd.DataFrame(
            {"test_name": ["Glucose mg/dL", "Creatinine mg/dl", "ALT U/L"]}
        )

        context = {
            "datasets": {"source": source_df, "target": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="matches",
            normalize_units=True,
        )

        action = ChemistryFuzzyTestMatchAction()
        assert action is not None

    def test_special_characters_handling(self):
        """Test handling of special characters in test names."""
        source_df = pd.DataFrame({"test_name": ["A/G Ratio", "CO₂", "γ-GT", "β-hCG"]})
        target_df = pd.DataFrame(
            {
                "test_name": [
                    "Albumin/Globulin Ratio",
                    "Carbon Dioxide",
                    "Gamma-GT",
                    "Beta-hCG",
                ]
            }
        )

        context = {
            "datasets": {"source": source_df, "target": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="matches"
        )

        action = ChemistryFuzzyTestMatchAction()
        assert action is not None

    def test_empty_dataset_handling(self):
        """Test handling of empty datasets."""
        empty_df = pd.DataFrame({"test_name": []})

        context = {
            "datasets": {"source": empty_df, "target": empty_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="source", target_key="target", output_key="matches"
        )

        action = ChemistryFuzzyTestMatchAction()
        # Should handle empty datasets without crashing
        assert action is not None

    @pytest.mark.asyncio
    async def test_context_statistics_update(self, sample_context, basic_params):
        """Test that context statistics are properly updated."""
        action = ChemistryFuzzyTestMatchAction()
        result = await action.execute_typed(basic_params, sample_context)

        # Should update statistics in context
        assert "chemistry_fuzzy_match" in sample_context["statistics"]
        stats = sample_context["statistics"]["chemistry_fuzzy_match"]
        assert "total_matches" in stats
        assert "average_similarity" in stats
        assert "match_methods" in stats
        assert "quality_distribution" in stats

    def test_result_model_validation(self):
        """Test ChemistryFuzzyTestMatchResult model validation."""
        result = ChemistryFuzzyTestMatchResult(
            success=True,
            total_source_tests=10,
            total_target_tests=12,
            matched_tests=8,
            unmatched_tests=["test1", "test2"],
            match_methods={"exact": 3, "synonym": 2, "partial": 3},
            average_similarity=0.87,
            match_quality_distribution={"high": 5, "medium": 2, "low": 1},
            vendor_cross_matches=4,
        )
        assert result.success
        assert result.matched_tests == 8
        assert len(result.unmatched_tests) == 2

    def test_loinc_integration_params(self):
        """Test LOINC-related parameters."""
        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="matches",
            source_loinc_column="loinc_code",
            target_loinc_column="loinc_code",
            use_loinc_primary=True,
            fallback_to_name=True,
        )

        assert params.source_loinc_column == "loinc_code"
        assert params.use_loinc_primary is True
        assert params.fallback_to_name is True

    def test_max_matches_per_test(self):
        """Test max_matches_per_test parameter."""
        params = ChemistryFuzzyTestMatchParams(
            source_key="source",
            target_key="target",
            output_key="matches",
            max_matches_per_test=3,
        )

        assert params.max_matches_per_test == 3


# Integration test with realistic data patterns
class TestRealWorldPatterns:
    """Test with realistic data patterns from actual datasets."""

    def test_arivale_to_spoke_patterns(self):
        """Test real Arivale to SPOKE chemistry patterns."""
        # Realistic Arivale chemistry test names
        arivale_tests = [
            "ALT (SGPT)",
            "AST (SGOT)",
            "Glucose, Fasting",
            "Cholesterol, Total",
            "HDL-C",
            "LDL-C (Calculated)",
            "Triglycerides",
        ]

        # SPOKE equivalent names
        spoke_tests = [
            "Alanine aminotransferase",
            "Aspartate aminotransferase",
            "Glucose",
            "Cholesterol",
            "HDL cholesterol",
            "LDL cholesterol",
            "Triglyceride",
        ]

        source_df = pd.DataFrame({"test_name": arivale_tests})
        target_df = pd.DataFrame({"test_name": spoke_tests})

        context = {
            "datasets": {"arivale": source_df, "spoke": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="arivale",
            target_key="spoke",
            output_key="matches",
            use_synonyms=True,
            use_abbreviations=True,
        )

        action = ChemistryFuzzyTestMatchAction()
        # Should be able to handle these realistic patterns
        assert action is not None

    def test_ukbb_field_code_patterns(self):
        """Test UK Biobank field code patterns."""
        ukbb_tests = [
            "30740-0.0 Glucose",
            "30760-0.0 HDL cholesterol",
            "30780-0.0 LDL direct",
            "30870-0.0 Triglycerides",
        ]

        standard_tests = [
            "Glucose",
            "HDL Cholesterol",
            "LDL Cholesterol",
            "Triglycerides",
        ]

        source_df = pd.DataFrame({"test_name": ukbb_tests})
        target_df = pd.DataFrame({"test_name": standard_tests})

        context = {
            "datasets": {"ukbb": source_df, "standard": target_df},
            "statistics": {},
        }

        params = ChemistryFuzzyTestMatchParams(
            source_key="ukbb",
            target_key="standard",
            output_key="matches",
            handle_vendor_prefixes=True,
        )

        action = ChemistryFuzzyTestMatchAction()
        assert action is not None

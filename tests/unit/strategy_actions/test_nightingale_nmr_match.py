import pytest
import numpy as np
import pandas as pd
from biomapper.core.strategy_actions.nightingale_nmr_match import (
    NightingaleNmrMatchAction,
    NightingaleNmrMatchParams,
)


class TestNightingaleNmrMatch:
    """Test suite for Nightingale NMR matching - WRITE FIRST!"""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return NightingaleNmrMatchAction()

    @pytest.fixture
    def sample_israeli10k_data(self):
        """Sample Israeli10K metabolite data."""
        return [
            {
                "tabular_field_name": "total_c",
                "nightingale_metabolomics_original_name": "Total_C",
                "description": "Total cholesterol",
            },
            {
                "tabular_field_name": "ldl_c",
                "nightingale_metabolomics_original_name": "LDL_C",
                "description": "LDL cholesterol",
            },
            {
                "tabular_field_name": "glucose",
                "nightingale_metabolomics_original_name": "Glucose",
                "description": "Glucose",
            },
        ]

    @pytest.fixture
    def sample_ukbb_data(self):
        """Sample UKBB metabolite data."""
        return [
            {
                "field_id": "23400",
                "title": "Total cholesterol",
                "category": "Cholesterol",
            },
            {
                "field_id": "23401",
                "title": "LDL cholesterol",
                "category": "Cholesterol",
            },
            {"field_id": "23450", "title": "Glucose", "category": "Glycolysis"},
        ]

    def test_normalization_handles_variations(self, action):
        """Test name normalization handles common variations."""
        # Underscores to spaces
        assert action._normalize_nightingale_name(
            "Total_C"
        ) == action._normalize_nightingale_name("Total C")

        # Case insensitive
        assert action._normalize_nightingale_name(
            "LDL_C"
        ) == action._normalize_nightingale_name("ldl_c")

        # Common abbreviations
        normalized = action._normalize_nightingale_name("Total cholesterol")
        assert "c" in normalized  # Should abbreviate cholesterol
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_exact_matching_finds_normalized_matches(self, action):
        """Test exact matching after normalization."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="exact",
            confidence_threshold=0.95,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )

        # Create mock context like in BuildNightingaleReference tests
        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": [
                            {"nightingale_metabolomics_original_name": "Total_C"},
                            {"nightingale_metabolomics_original_name": "LDL_C"},
                        ],
                        "ukbb": [{"title": "Total C"}, {"title": "LDL C"}],
                    }
                }

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        context = MockContext()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.details["success"]
        datasets = context.get_action_data("datasets")
        matches = datasets["matches"]
        assert len(matches) == 2  # Both should match after normalization
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_fuzzy_matching_handles_variations(
        self, action, sample_israeli10k_data, sample_ukbb_data
    ):
        """Test fuzzy matching handles name variations."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.80,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )

        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": sample_israeli10k_data,
                        "ukbb": sample_ukbb_data,
                    }
                }

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        context = MockContext()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.details["success"]
        datasets = context.get_action_data("datasets")
        matches = datasets["matches"]
        assert len(matches) == 3  # All should match

        # Check confidence scores
        for match in matches:
            assert match["confidence"] >= 0.80
            assert "match_algorithm" in match
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_provenance_tracking(self, action):
        """Test provenance is properly tracked."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.80,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )

        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": [
                            {
                                "nightingale_metabolomics_original_name": "Total_C",
                                "tabular_field_name": "total_c",
                            }
                        ],
                        "ukbb": [{"title": "Total cholesterol", "field_id": "23400"}],
                    },
                    "provenance": {},
                }

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        context = MockContext()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.details["success"]
        provenance_data = context.get_action_data("provenance")
        assert "nightingale_matches" in provenance_data

        provenance = provenance_data["nightingale_matches"][0]
        assert "match_id" in provenance
        assert provenance["source"]["nightingale_name"] == "Total_C"
        assert provenance["target"]["title"] == "Total cholesterol"
        assert "timestamp" in provenance
        assert provenance["match_details"]["tier"] == "nightingale_direct"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_unmatched_items_tracked(self, action):
        """Test unmatched items are properly tracked."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="exact",
            confidence_threshold=0.95,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )

        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": [
                            {"nightingale_metabolomics_original_name": "Total_C"},
                            {
                                "nightingale_metabolomics_original_name": "Unknown_Metabolite"
                            },
                        ],
                        "ukbb": [
                            {"title": "Total C"},
                            {"title": "Different Metabolite"},
                        ],
                    }
                }

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        context = MockContext()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.details["success"]
        datasets = context.get_action_data("datasets")
        unmatched_source = datasets["unmatched_source"]
        unmatched_target = datasets["unmatched_target"]

        assert len(unmatched_source) == 1
        assert (
            unmatched_source[0]["nightingale_metabolomics_original_name"]
            == "Unknown_Metabolite"
        )

        assert len(unmatched_target) == 1
        assert unmatched_target[0]["title"] == "Different Metabolite"
        # This test should FAIL initially

    def test_match_score_calculation(self, action):
        """Test match score calculation for different strategies."""
        # Exact match
        score, algo = action._calculate_match_score("Total_C", "Total C", "exact")
        assert score == 1.0
        assert algo == "exact_normalized"

        # Fuzzy match
        score, algo = action._calculate_match_score(
            "Total cholesterol", "Cholesterol, total", "fuzzy"
        )
        assert score > 0.7  # Should be reasonably high
        assert algo in [
            "token_set_ratio",
            "normalized_token_set",
            "token_sort_ratio",
            "normalized_ratio",
        ]  # Possible best algorithms
        # This test should FAIL initially

    def test_normalize_with_nan_values(self, action):
        """Test normalization handles NaN values gracefully."""
        # Test various invalid inputs
        assert action._normalize_nightingale_name(np.nan) == ""
        assert action._normalize_nightingale_name(None) == ""
        assert action._normalize_nightingale_name(float('nan')) == ""
        
        # Test numeric values
        assert action._normalize_nightingale_name(123.45) == "123.45"
        assert action._normalize_nightingale_name(123) == "123"
        
        # Test empty strings
        assert action._normalize_nightingale_name("") == ""
        assert action._normalize_nightingale_name("   ") == ""
        
        # Test normal strings still work
        assert action._normalize_nightingale_name("Total_C") == "c"
        assert action._normalize_nightingale_name("HDL_C") == "hdl c"

    @pytest.mark.asyncio
    async def test_matching_with_data_quality_issues(self, action):
        """Test matching with datasets containing NaN values."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.80,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )
        
        # Create test data with quality issues
        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": [
                            {"id": "1", "nightingale_name": "Total_C"},
                            {"id": "2", "nightingale_name": np.nan},  # NaN value
                            {"id": "3", "nightingale_name": 123.45},  # Numeric
                            {"id": "4", "nightingale_name": "HDL_C"},
                            {"id": "5", "nightingale_name": ""},  # Empty string
                            {"id": "6", "nightingale_name": None},  # None value
                        ],
                        "ukbb": [
                            {"field_id": "23400", "title": "Total cholesterol"},
                            {"field_id": "23401", "title": np.nan},  # NaN in target
                            {"field_id": "23402", "title": "HDL cholesterol"},
                            {"field_id": "23403", "title": 456.78},  # Numeric in target
                            {"field_id": "23404", "title": ""},  # Empty in target
                        ],
                    }
                }
            
            def get_action_data(self, key, default=None):
                return self._data.get(key, default)
            
            def set_action_data(self, key, value):
                self._data[key] = value
        
        context = MockContext()
        
        # Run matching and verify it completes without error
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )
        
        assert result.details["success"]
        
        # Verify data quality metrics
        data_quality = result.details["data_quality"]
        assert data_quality["source_nan_count"] == 2  # np.nan and None
        assert data_quality["source_empty_count"] == 1
        assert data_quality["source_numeric_count"] == 1
        assert data_quality["target_nan_count"] == 1
        assert data_quality["target_empty_count"] == 1
        assert data_quality["target_numeric_count"] == 1
        
        # Verify matches were found for valid entries
        datasets = context.get_action_data("datasets")
        matches = datasets["matches"]
        assert len(matches) >= 2  # At least Total_C and HDL_C should match
        
        # Verify invalid entries are in unmatched
        unmatched_source = datasets["unmatched_source"]
        assert len(unmatched_source) >= 3  # NaN, None, and empty entries

    @pytest.mark.asyncio
    async def test_numeric_values_handled_as_strings(self, action):
        """Test that numeric values are converted to strings and matched."""
        params = NightingaleNmrMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_nightingale_column="name",
            target_title_column="title",
            match_strategy="exact",
            confidence_threshold=0.95,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )
        
        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "source": [
                            {"id": "1", "name": 123},  # Numeric that should match
                            {"id": "2", "name": 456.78},  # Float that should match
                        ],
                        "target": [
                            {"field_id": "a", "title": "123"},  # String version
                            {"field_id": "b", "title": 456.78},  # Numeric in target
                        ],
                    }
                }
            
            def get_action_data(self, key, default=None):
                return self._data.get(key, default)
            
            def set_action_data(self, key, value):
                self._data[key] = value
        
        context = MockContext()
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )
        
        assert result.details["success"]
        
        # Both numeric values should be matched after string conversion
        datasets = context.get_action_data("datasets")
        matches = datasets["matches"]
        assert len(matches) == 2

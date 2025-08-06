import pytest
import numpy as np
import pandas as pd
from biomapper.core.strategy_actions.nightingale_nmr_match import (
    NightingaleNmrMatchAction,
    NightingaleNmrMatchParams,
)


@pytest.mark.integration
class TestNightingaleIntegration:
    """Integration tests with real data samples."""

    @pytest.mark.asyncio
    async def test_real_data_matching(self):
        """Test with actual Nightingale naming patterns."""
        # Test with real naming variations from the datasets
        test_pairs = [
            ("Total_C", "Total cholesterol"),
            ("LDL_C", "LDL cholesterol"),
            ("HDL_C", "HDL cholesterol"),
            ("Glucose", "Glucose"),
            ("Total_TG", "Triglycerides"),
            ("ApoB_ApoA1_ratio", "Apolipoprotein B/Apolipoprotein A1 ratio"),
        ]

        action = NightingaleNmrMatchAction()

        for source, target in test_pairs:
            score, algo = action._calculate_match_score(source, target, "fuzzy")
            assert (
                score >= 0.75
            ), f"Failed to match {source} to {target} (score: {score:.3f})"

    @pytest.mark.asyncio
    async def test_full_workflow_with_real_patterns(self):
        """Test complete workflow with realistic Nightingale data patterns."""

        # Realistic Israeli10K data patterns
        israeli10k_data = [
            {
                "tabular_field_name": "serum_total_cholesterol",
                "nightingale_metabolomics_original_name": "Serum_total_cholesterol",
                "units": "mmol/L",
            },
            {
                "tabular_field_name": "serum_ldl_cholesterol",
                "nightingale_metabolomics_original_name": "Serum_LDL_cholesterol",
                "units": "mmol/L",
            },
            {
                "tabular_field_name": "serum_hdl_cholesterol",
                "nightingale_metabolomics_original_name": "Serum_HDL_cholesterol",
                "units": "mmol/L",
            },
            {
                "tabular_field_name": "glucose",
                "nightingale_metabolomics_original_name": "Glucose",
                "units": "mmol/L",
            },
            {
                "tabular_field_name": "total_triglycerides",
                "nightingale_metabolomics_original_name": "Total_triglycerides",
                "units": "mmol/L",
            },
            {
                "tabular_field_name": "apob_apoa1_ratio",
                "nightingale_metabolomics_original_name": "ApoB_ApoA1_ratio",
                "units": "ratio",
            },
            {
                "tabular_field_name": "unknown_metabolite",
                "nightingale_metabolomics_original_name": "Unknown_metabolite_123",
                "units": "mmol/L",
            },
        ]

        # Realistic UKBB data patterns
        ukbb_data = [
            {
                "field_id": "23400",
                "title": "Cholesterol",
                "category": "Cholesterol",
                "units": "mmol/L",
            },
            {
                "field_id": "23401",
                "title": "LDL direct",
                "category": "Cholesterol",
                "units": "mmol/L",
            },
            {
                "field_id": "23402",
                "title": "HDL cholesterol",
                "category": "Cholesterol",
                "units": "mmol/L",
            },
            {
                "field_id": "23450",
                "title": "Glucose",
                "category": "Glycolysis",
                "units": "mmol/L",
            },
            {
                "field_id": "23451",
                "title": "Triglycerides",
                "category": "Triglycerides",
                "units": "mmol/L",
            },
            {
                "field_id": "23452",
                "title": "Apolipoprotein B/Apolipoprotein A1 ratio",
                "category": "Apolipoproteins",
                "units": "ratio",
            },
            {
                "field_id": "23999",
                "title": "Some other metabolite",
                "category": "Other",
                "units": "mmol/L",
            },
        ]

        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.75,
            output_key="nightingale_matches",
            unmatched_source_key="unmatched_israeli10k",
            unmatched_target_key="unmatched_ukbb",
        )

        context = {"datasets": {"israeli10k": israeli10k_data, "ukbb": ukbb_data}}

        action = NightingaleNmrMatchAction()

        # Create mock context like in other tests
        class MockContext:
            def __init__(self):
                self._data = context

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        mock_context = MockContext()

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        # Verify results
        assert result.details["success"]
        datasets = mock_context.get_action_data("datasets")
        matches = datasets["nightingale_matches"]
        unmatched_source = datasets["unmatched_israeli10k"]
        # unmatched_target = datasets['unmatched_ukbb']  # Not used in assertions

        # We expect good match rate with Nightingale data
        assert len(matches) >= 5, f"Expected at least 5 matches, got {len(matches)}"
        assert (
            len(matches) / len(israeli10k_data) >= 0.7
        ), "Match rate should be at least 70%"

        # Check match quality
        high_conf_matches = [m for m in matches if m["confidence"] >= 0.9]
        assert (
            len(high_conf_matches) >= 3
        ), "Should have at least 3 high-confidence matches"

        # Verify provenance is tracked
        provenance_data = mock_context.get_action_data("provenance")
        assert "nightingale_matches" in provenance_data
        assert len(provenance_data["nightingale_matches"]) == len(matches)

        # Check that unmatched items are properly tracked
        assert len(unmatched_source) + len(matches) == len(israeli10k_data)
        # Note: len(unmatched_target) + len(matches) <= len(ukbb_data) because some targets might match multiple sources

        # Verify specific expected matches
        match_names = [
            (
                m["source"]["nightingale_metabolomics_original_name"],
                m["target"]["title"],
            )
            for m in matches
        ]

        # These should definitely match with high confidence
        expected_high_conf = [
            ("Glucose", "Glucose"),
        ]

        for source_name, target_title in expected_high_conf:
            found_match = any(
                source_name in match[0] and target_title in match[1]
                for match in match_names
            )
            assert found_match, f"Expected high-confidence match between {source_name} and {target_title}"

    @pytest.mark.asyncio
    async def test_edge_cases_and_robustness(self):
        """Test edge cases and robustness of the matching."""

        # Edge case data
        edge_case_data = {
            "israeli10k": [
                {"nightingale_metabolomics_original_name": ""},  # Empty name
                {
                    "nightingale_metabolomics_original_name": "Very_Specific_Rare_Metabolite_XYZ"
                },  # No match expected
                {
                    "nightingale_metabolomics_original_name": "HDL_C"
                },  # Common abbreviation
                {
                    "nightingale_metabolomics_original_name": "Total_Cholesterol_Ester"
                },  # Partial match
            ],
            "ukbb": [
                {"title": "HDL cholesterol"},  # Should match HDL_C
                {
                    "title": "Total cholesterol"
                },  # Should partially match cholesterol ester
                {"title": "Completely Different Metabolite"},  # No match
                {"title": ""},  # Empty title
            ],
        }

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
                self._data = {"datasets": edge_case_data}

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        mock_context = MockContext()

        action = NightingaleNmrMatchAction()
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        # Should handle edge cases gracefully
        assert result.details["success"]
        datasets = mock_context.get_action_data("datasets")
        matches = datasets["matches"]

        # HDL_C -> HDL cholesterol should match
        hdl_match = any(
            "HDL" in match["source"]["nightingale_metabolomics_original_name"]
            and "HDL" in match["target"]["title"]
            for match in matches
        )
        assert hdl_match, "HDL_C should match HDL cholesterol"

        # Empty strings should not cause errors
        assert len(matches) >= 0  # Just ensure no crash

        # Verify unmatched tracking works with edge cases
        unmatched_source = datasets["unmatched_source"]
        # unmatched_target = datasets['unmatched_target']  # Not used in subsequent assertions

        # Should track the rare metabolite as unmatched
        rare_unmatched = any(
            "Very_Specific_Rare_Metabolite_XYZ"
            in item.get("nightingale_metabolomics_original_name", "")
            for item in unmatched_source
        )
        assert rare_unmatched, "Rare metabolite should remain unmatched"

    @pytest.mark.asyncio
    async def test_performance_with_larger_dataset(self):
        """Test performance with a larger synthetic dataset."""

        # Generate larger synthetic dataset
        base_metabolites = [
            "Total_C",
            "LDL_C",
            "HDL_C",
            "VLDL_C",
            "IDL_C",
            "Total_TG",
            "Glucose",
            "Lactate",
            "Pyruvate",
            "Citrate",
            "Alanine",
            "Glycine",
            "Histidine",
            "Isoleucine",
            "Leucine",
            "Valine",
            "Phenylalanine",
            "Tyrosine",
            "Acetate",
            "Acetoacetate",
        ]

        # Create variations for Israeli10K (100 items)
        israeli10k_large = []
        for i in range(100):
            base = base_metabolites[i % len(base_metabolites)]
            israeli10k_large.append(
                {
                    "tabular_field_name": f"field_{i}",
                    "nightingale_metabolomics_original_name": f"{base}_{i//len(base_metabolites) + 1}"
                    if i >= len(base_metabolites)
                    else base,
                }
            )

        # Create variations for UKBB (120 items)
        ukbb_large = []
        for i in range(120):
            base = base_metabolites[i % len(base_metabolites)]
            title = (
                base.replace("_", " ")
                .replace("C", "cholesterol")
                .replace("TG", "triglycerides")
            )
            ukbb_large.append(
                {
                    "field_id": f"ukbb_{i}",
                    "title": f"{title} variant {i//len(base_metabolites) + 1}"
                    if i >= len(base_metabolites)
                    else title,
                }
            )

        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.75,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )

        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {"israeli10k": israeli10k_large, "ukbb": ukbb_large}
                }

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        mock_context = MockContext()

        import time

        start_time = time.time()

        action = NightingaleNmrMatchAction()
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        execution_time = time.time() - start_time

        # Performance check - should complete in reasonable time
        assert execution_time < 5.0, f"Execution took too long: {execution_time:.2f}s"

        # Quality check
        assert result.details["success"]
        datasets = mock_context.get_action_data("datasets")
        matches = datasets["matches"]

        # Should find reasonable number of matches
        match_rate = len(matches) / len(israeli10k_large)
        assert match_rate >= 0.3, f"Match rate too low: {match_rate:.1%}"

        print(
            f"Performance test: {len(matches)} matches in {execution_time:.2f}s ({match_rate:.1%} match rate)"
        )

    @pytest.mark.asyncio
    async def test_real_world_data_quality_issues(self):
        """Test with realistic data quality issues like NaN, missing values, numeric values."""
        
        # Simulate real-world data with quality issues
        israeli10k_messy = [
            # Valid entries
            {
                "tabular_field_name": "serum_total_c",
                "nightingale_metabolomics_original_name": "Serum_Total_C",
                "units": "mmol/L",
                "patient_id": "P001"
            },
            {
                "tabular_field_name": "hdl_c",
                "nightingale_metabolomics_original_name": "HDL_C",
                "units": "mmol/L",
                "patient_id": "P002"
            },
            # NaN values (common in real datasets)
            {
                "tabular_field_name": "ldl_c",
                "nightingale_metabolomics_original_name": np.nan,
                "units": "mmol/L",
                "patient_id": "P003"
            },
            {
                "tabular_field_name": "vldl_c",
                "nightingale_metabolomics_original_name": float('nan'),
                "units": "mmol/L",
                "patient_id": "P004"
            },
            # Empty strings
            {
                "tabular_field_name": "glucose",
                "nightingale_metabolomics_original_name": "",
                "units": "mmol/L",
                "patient_id": "P005"
            },
            {
                "tabular_field_name": "lactate",
                "nightingale_metabolomics_original_name": "   ",  # Whitespace only
                "units": "mmol/L",
                "patient_id": "P006"
            },
            # None values
            {
                "tabular_field_name": "pyruvate",
                "nightingale_metabolomics_original_name": None,
                "units": "mmol/L",
                "patient_id": "P007"
            },
            # Numeric values (data entry errors)
            {
                "tabular_field_name": "citrate",
                "nightingale_metabolomics_original_name": 123.45,
                "units": "mmol/L",
                "patient_id": "P008"
            },
            {
                "tabular_field_name": "acetate",
                "nightingale_metabolomics_original_name": 999,
                "units": "mmol/L",
                "patient_id": "P009"
            },
            # More valid entries
            {
                "tabular_field_name": "total_tg",
                "nightingale_metabolomics_original_name": "Total_TG",
                "units": "mmol/L",
                "patient_id": "P010"
            },
            {
                "tabular_field_name": "apob_apoa1",
                "nightingale_metabolomics_original_name": "ApoB_ApoA1_ratio",
                "units": "ratio",
                "patient_id": "P011"
            },
        ]
        
        # UKBB data with similar issues
        ukbb_messy = [
            # Valid entries
            {
                "field_id": "23400",
                "title": "Total cholesterol",
                "category": "Cholesterol",
                "units": "mmol/L"
            },
            {
                "field_id": "23401",
                "title": "HDL cholesterol",
                "category": "Cholesterol",
                "units": "mmol/L"
            },
            # Data quality issues
            {
                "field_id": "23402",
                "title": np.nan,
                "category": "Cholesterol",
                "units": "mmol/L"
            },
            {
                "field_id": "23403",
                "title": "",
                "category": "Triglycerides",
                "units": "mmol/L"
            },
            {
                "field_id": "23404",
                "title": None,
                "category": "Glycolysis",
                "units": "mmol/L"
            },
            {
                "field_id": "23405",
                "title": 456.78,  # Numeric title
                "category": "Other",
                "units": "mmol/L"
            },
            # More valid entries
            {
                "field_id": "23406",
                "title": "Triglycerides",
                "category": "Triglycerides",
                "units": "mmol/L"
            },
            {
                "field_id": "23407",
                "title": "Apolipoprotein B/Apolipoprotein A1 ratio",
                "category": "Apolipoproteins",
                "units": "ratio"
            },
            {
                "field_id": "23408",
                "title": "LDL cholesterol",
                "category": "Cholesterol",
                "units": "mmol/L"
            },
            {
                "field_id": "23409",
                "title": "Glucose",
                "category": "Glycolysis",
                "units": "mmol/L"
            },
        ]
        
        params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.75,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target",
        )
        
        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": israeli10k_messy,
                        "ukbb": ukbb_messy
                    },
                    "provenance": {}
                }
            
            def get_action_data(self, key, default=None):
                return self._data.get(key, default)
            
            def set_action_data(self, key, value):
                self._data[key] = value
        
        mock_context = MockContext()
        
        action = NightingaleNmrMatchAction()
        
        # Should not raise any errors despite data quality issues
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )
        
        # Verify execution completed successfully
        assert result.details["success"]
        
        # Check data quality metrics
        data_quality = result.details["data_quality"]
        assert data_quality["source_nan_count"] >= 3  # np.nan, float('nan'), None
        assert data_quality["source_empty_count"] >= 1  # "" (whitespace-only is trimmed and counted as empty)
        assert data_quality["source_numeric_count"] >= 2  # 123.45 and 999
        assert data_quality["target_nan_count"] >= 2  # np.nan and None
        assert data_quality["target_empty_count"] >= 1  # ""
        assert data_quality["target_numeric_count"] >= 1  # 456.78
        
        # Verify matches were found for valid entries
        datasets = mock_context.get_action_data("datasets")
        matches = datasets["matches"]
        
        # Should have matches for valid entries
        assert len(matches) >= 3, f"Expected at least 3 matches, got {len(matches)}"
        
        # Check specific expected matches
        match_pairs = [(m["source"]["nightingale_metabolomics_original_name"], 
                       m["target"]["title"]) for m in matches]
        
        # These should definitely match
        expected_matches = [
            ("Serum_Total_C", "Total cholesterol"),
            ("HDL_C", "HDL cholesterol"),
            ("Total_TG", "Triglycerides"),
        ]
        
        for source, target in expected_matches:
            found = any(source in pair[0] and target in pair[1] for pair in match_pairs)
            assert found, f"Expected match between {source} and {target}"
        
        # Verify numeric values were handled
        numeric_matches = [m for m in matches 
                          if isinstance(m["source"].get("nightingale_metabolomics_original_name"), (int, float))
                          or isinstance(m["target"].get("title"), (int, float))]
        
        # If numeric values matched, they should have been converted to strings
        for match in numeric_matches:
            source_name = match["source"].get("nightingale_metabolomics_original_name")
            target_title = match["target"].get("title")
            if isinstance(source_name, (int, float)):
                assert str(source_name) in str(match["confidence"])
            if isinstance(target_title, (int, float)):
                assert str(target_title) in str(match["confidence"])
        
        # Verify unmatched tracking
        unmatched_source = datasets["unmatched_source"]
        unmatched_target = datasets["unmatched_target"]
        
        # Check that items with NaN/None/empty names are in unmatched
        invalid_source_count = sum(1 for item in israeli10k_messy 
                                  if pd.isna(item.get("nightingale_metabolomics_original_name"))
                                  or item.get("nightingale_metabolomics_original_name") in [None, "", "   "])
        
        # Total unmatched should include at least the invalid entries
        assert len(unmatched_source) >= invalid_source_count
        
        print(f"Data quality test completed: {len(matches)} matches found despite {sum(data_quality.values())} data quality issues")

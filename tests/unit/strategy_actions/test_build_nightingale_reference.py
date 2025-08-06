import pytest
from pathlib import Path
import csv
import tempfile

from biomapper.core.strategy_actions.build_nightingale_reference import (
    BuildNightingaleReferenceAction,
    BuildNightingaleReferenceParams,
    NightingaleReferenceEntry,
)


class TestBuildNightingaleReference:
    """Test suite for building Nightingale reference - WRITE FIRST!"""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return BuildNightingaleReferenceAction()

    @pytest.fixture
    def matched_pairs(self):
        """Sample matched pairs from NIGHTINGALE_NMR_MATCH."""
        return [
            {
                "source": {
                    "tabular_field_name": "total_c",
                    "nightingale_metabolomics_original_name": "Total_C",
                    "description": "Total cholesterol",
                },
                "target": {
                    "field_id": "23400",
                    "title": "Total cholesterol",
                    "category": "Cholesterol",
                },
                "confidence": 0.98,
                "match_algorithm": "fuzzy_normalized",
            },
            {
                "source": {
                    "tabular_field_name": "ldl_c",
                    "nightingale_metabolomics_original_name": "LDL_C",
                    "description": "LDL cholesterol",
                },
                "target": {
                    "field_id": "23401",
                    "title": "LDL cholesterol",
                    "category": "Cholesterol",
                },
                "confidence": 0.95,
                "match_algorithm": "exact_normalized",
            },
        ]

    def test_unified_name_generation(self, action):
        """Test unified name generation strategies."""
        # High confidence - should use UKBB title
        name = action._generate_unified_name("Total_C", "Total cholesterol", 0.98)
        assert name == "Total cholesterol"

        # Lower confidence - should find common elements
        name = action._generate_unified_name("Glucose_value", "Glucose", 0.85)
        assert "glucose" in name.lower()
        # This test should FAIL initially

    def test_metabolite_name_cleaning(self, action):
        """Test name cleaning and standardization."""
        # Standardize cholesterol
        assert action._clean_metabolite_name("CHOLESTEROL") == "Cholesterol"
        assert action._clean_metabolite_name("total cholesterol") == "Total cholesterol"

        # Preserve abbreviations
        assert action._clean_metabolite_name("HDL cholesterol") == "HDL cholesterol"
        assert action._clean_metabolite_name("ldl cholesterol") == "LDL cholesterol"
        # This test should FAIL initially

    def test_category_extraction(self, action):
        """Test category extraction from items."""
        # From UKBB category
        ukbb_item = {"category": "Cholesterol"}
        israeli_item = {}
        assert action._extract_category(israeli_item, ukbb_item) == "Cholesterol"

        # From Israeli10K description
        israeli_item = {"description": "Total triglycerides in blood"}
        ukbb_item = {}
        assert action._extract_category(israeli_item, ukbb_item) == "Triglycerides"
        # This test should FAIL initially

    def test_alternative_names_collection(self, action):
        """Test collection of alternative names."""
        israeli_item = {
            "nightingale_metabolomics_original_name": "Total_C",
            "description": "Total cholesterol",
        }
        ukbb_item = {"title": "Total cholesterol"}
        unified_name = "Total cholesterol"

        alt_names = action._collect_alternative_names(
            israeli_item, ukbb_item, unified_name
        )

        assert "Total_C" in alt_names
        assert "Total C" in alt_names  # Space variant
        assert unified_name not in alt_names  # Unified name should be excluded
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_reference_building(self, action, matched_pairs):
        """Test building complete reference."""
        params = BuildNightingaleReferenceParams(
            israeli10k_data="israeli10k",
            ukbb_data="ukbb",
            matched_pairs="matches",
            output_key="reference",
            export_csv=False,
            include_metadata=True,
        )

        # Create mock context like in load_dataset_identifiers tests
        class MockContext:
            def __init__(self):
                self._data = {
                    "datasets": {
                        "israeli10k": [],  # Not used directly
                        "ukbb": [],  # Not used directly
                        "matches": matched_pairs,
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

        assert result.success
        datasets = context.get_action_data("datasets")
        reference = datasets["reference"]
        assert len(reference) == 2

        # Check first entry
        first = reference[0]
        assert "nightingale_id" in first
        assert first["unified_name"] in ["LDL cholesterol", "Total cholesterol"]
        assert first["confidence"] > 0.9
        assert "alternative_names" in first
        assert "metadata" in first
        assert first["metadata"]["platform"] == "Nightingale NMR"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_csv_export(self, action, matched_pairs):
        """Test CSV export functionality."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            csv_path = tmp.name

        try:
            params = BuildNightingaleReferenceParams(
                israeli10k_data="israeli10k",
                ukbb_data="ukbb",
                matched_pairs="matches",
                output_key="reference",
                export_csv=True,
                csv_path=csv_path,
            )

            class MockContext:
                def __init__(self):
                    self._data = {"datasets": {"matches": matched_pairs}}

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

            assert result.success
            assert Path(csv_path).exists()

            # Read and verify CSV
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                assert len(rows) == 2
                assert "nightingale_id" in rows[0]
                assert "unified_name" in rows[0]
                assert "confidence" in rows[0]
                assert "alternative_names" in rows[0]

        finally:
            Path(csv_path).unlink(missing_ok=True)
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_duplicate_handling(self, action):
        """Test handling of duplicate metabolites."""
        # Create matches with duplicate metabolites
        duplicate_matches = [
            {
                "source": {
                    "tabular_field_name": "total_c",
                    "nightingale_metabolomics_original_name": "Total_C",
                },
                "target": {"field_id": "23400", "title": "Total cholesterol"},
                "confidence": 0.98,
                "match_algorithm": "fuzzy",
            },
            {
                "source": {
                    "tabular_field_name": "total_chol",
                    "nightingale_metabolomics_original_name": "Total_Chol",
                },
                "target": {"field_id": "23400", "title": "Total cholesterol"},
                "confidence": 0.95,
                "match_algorithm": "fuzzy",
            },
        ]

        params = BuildNightingaleReferenceParams(
            israeli10k_data="israeli10k",
            ukbb_data="ukbb",
            matched_pairs="matches",
            output_key="reference",
            export_csv=False,
        )

        class MockContext:
            def __init__(self):
                self._data = {"datasets": {"matches": duplicate_matches}}

            def get_action_data(self, key, default=None):
                return self._data.get(key, default)

            def set_action_data(self, key, value):
                self._data[key] = value

        context = MockContext()

        await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        datasets = context.get_action_data("datasets")
        reference = datasets["reference"]
        # Should have skipped the duplicate
        assert len(reference) == 1
        # This test should FAIL initially

    def test_reference_entry_model(self):
        """Test NightingaleReferenceEntry model."""
        entry = NightingaleReferenceEntry(
            nightingale_id="test-id",
            unified_name="Total cholesterol",
            israeli10k_field="total_c",
            israeli10k_display="Total_C",
            ukbb_field_id="23400",
            ukbb_title="Total cholesterol",
            category="Cholesterol",
            confidence=0.98,
            alternative_names=["Total_C", "Total C"],
            metadata={"platform": "Nightingale NMR"},
        )

        # Test serialization
        data = entry.dict()
        assert data["nightingale_id"] == "test-id"
        assert data["unified_name"] == "Total cholesterol"
        assert len(data["alternative_names"]) == 2
        # This test should FAIL initially

"""Unit tests for CalculateThreeWayOverlapAction."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from biomapper.core.strategy_actions.calculate_three_way_overlap import (
    CalculateThreeWayOverlapAction,
    CalculateThreeWayOverlapParams,
    OverlapStatistics,
)


class TestCalculateThreeWayOverlapAction:
    """Test suite for CalculateThreeWayOverlapAction."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return CalculateThreeWayOverlapAction()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_three_way_matches(self):
        """Sample three-way matches data."""
        return [
            {
                "metabolite_id": "metabolite_glucose",
                "match_confidence": 0.95,
                "match_methods": ["nightingale_direct", "baseline_fuzzy"],
                "dataset_count": 3,
                "is_complete": True,
                "israeli10k": {
                    "field_name": "glucose_nmr",
                    "display_name": "Glucose (NMR)",
                    "nightingale_name": "Glucose",
                },
                "ukbb": {"field_id": "23027", "title": "Glucose"},
                "arivale": {
                    "biochemical_name": "glucose",
                    "hmdb": "HMDB0000122",
                    "kegg": "C00031",
                },
            },
            {
                "metabolite_id": "metabolite_lactate",
                "match_confidence": 0.88,
                "match_methods": ["nightingale_direct"],
                "dataset_count": 3,
                "is_complete": True,
                "israeli10k": {
                    "field_name": "lactate_nmr",
                    "display_name": "Lactate (NMR)",
                    "nightingale_name": "Lactate",
                },
                "ukbb": {"field_id": "23028", "title": "Lactate"},
                "arivale": {
                    "biochemical_name": "lactate",
                    "hmdb": "HMDB0000190",
                    "kegg": "C00186",
                },
            },
        ]

    @pytest.fixture
    def sample_two_way_matches(self):
        """Sample two-way matches data."""
        return [
            {
                "metabolite_id": "metabolite_citrate",
                "match_confidence": 0.85,
                "match_methods": ["nightingale_direct"],
                "dataset_count": 2,
                "is_complete": False,
                "israeli10k": {
                    "field_name": "citrate_nmr",
                    "display_name": "Citrate (NMR)",
                    "nightingale_name": "Citrate",
                },
                "ukbb": {"field_id": "23029", "title": "Citrate"},
            },
            {
                "metabolite_id": "metabolite_creatinine",
                "match_confidence": 0.92,
                "match_methods": ["baseline_fuzzy"],
                "dataset_count": 2,
                "is_complete": False,
                "arivale": {
                    "biochemical_name": "creatinine",
                    "hmdb": "HMDB0000562",
                    "kegg": "C00791",
                },
                "ukbb": {"field_id": "23030", "title": "Creatinine"},
            },
        ]

    @pytest.fixture
    def mock_context(self, sample_three_way_matches, sample_two_way_matches):
        """Create mock context with test data."""
        context = MagicMock()

        # Setup datasets
        datasets = {
            "three_way_combined_matches": {
                "three_way_matches": sample_three_way_matches,
                "two_way_matches": sample_two_way_matches,
            }
        }

        context.get_action_data.side_effect = lambda key, default=None: {
            "datasets": datasets
        }.get(key, default)

        return context

    def test_membership_extraction(
        self, action, sample_three_way_matches, sample_two_way_matches
    ):
        """Test correct extraction of dataset memberships."""
        memberships = action._extract_dataset_memberships(
            sample_three_way_matches, sample_two_way_matches, confidence_threshold=0.8
        )

        # Check three-way memberships
        assert "metabolite_glucose" in memberships["Israeli10K_UKBB_Arivale"]
        assert "metabolite_lactate" in memberships["Israeli10K_UKBB_Arivale"]

        # Check two-way memberships
        assert "metabolite_citrate" in memberships["Israeli10K_UKBB"]
        assert "metabolite_citrate" not in memberships["Israeli10K_UKBB_Arivale"]

        # Check individual dataset memberships
        assert len(memberships["Israeli10K"]) == 3  # glucose, lactate, citrate
        assert len(memberships["UKBB"]) == 4  # all four metabolites
        assert len(memberships["Arivale"]) == 3  # glucose, lactate, creatinine

    def test_pairwise_overlap_calculation(
        self, action, sample_three_way_matches, sample_two_way_matches
    ):
        """Test pairwise overlap statistics."""
        memberships = action._extract_dataset_memberships(
            sample_three_way_matches, sample_two_way_matches, confidence_threshold=0.8
        )

        all_matches = sample_three_way_matches + sample_two_way_matches
        stats = action._calculate_overlap_statistics(
            memberships, ["Israeli10K", "UKBB", "Arivale"], all_matches
        )

        # Check Israeli10K-UKBB overlap
        i10k_ukbb = stats["Israeli10K_UKBB"]
        assert isinstance(i10k_ukbb, OverlapStatistics)
        assert i10k_ukbb.count == 3  # glucose, lactate, citrate
        assert i10k_ukbb.jaccard_index > 0
        assert i10k_ukbb.percentage_of_first > 0
        assert i10k_ukbb.percentage_of_second > 0

    def test_three_way_overlap_calculation(
        self, action, sample_three_way_matches, sample_two_way_matches
    ):
        """Test three-way overlap statistics."""
        memberships = action._extract_dataset_memberships(
            sample_three_way_matches, sample_two_way_matches, confidence_threshold=0.8
        )

        all_matches = sample_three_way_matches + sample_two_way_matches
        stats = action._calculate_overlap_statistics(
            memberships, ["Israeli10K", "UKBB", "Arivale"], all_matches
        )

        # Check three-way overlap
        three_way = stats["three_way"]
        assert isinstance(three_way, OverlapStatistics)
        assert three_way.count == 2  # glucose and lactate
        assert three_way.percentage_of_third is not None
        assert 0 <= three_way.jaccard_index <= 1

    def test_jaccard_index_calculation(
        self, action, sample_three_way_matches, sample_two_way_matches
    ):
        """Test Jaccard index accuracy."""
        memberships = action._extract_dataset_memberships(
            sample_three_way_matches, sample_two_way_matches, confidence_threshold=0.8
        )

        all_matches = sample_three_way_matches + sample_two_way_matches
        stats = action._calculate_overlap_statistics(
            memberships, ["Israeli10K", "UKBB", "Arivale"], all_matches
        )

        # Manually calculate Jaccard for Israeli10K-UKBB
        i10k = memberships["Israeli10K"]
        ukbb = memberships["UKBB"]
        intersection = len(i10k & ukbb)
        union = len(i10k | ukbb)
        expected_jaccard = intersection / union if union > 0 else 0

        assert abs(stats["Israeli10K_UKBB"].jaccard_index - expected_jaccard) < 0.001

    def test_confidence_filtering(
        self, action, sample_three_way_matches, sample_two_way_matches
    ):
        """Test that low-confidence matches are excluded."""
        # Modify one match to have low confidence
        sample_two_way_matches[0]["match_confidence"] = 0.5

        memberships = action._extract_dataset_memberships(
            sample_three_way_matches, sample_two_way_matches, confidence_threshold=0.8
        )

        # Low confidence citrate should be excluded
        assert "metabolite_citrate" not in memberships["Israeli10K_UKBB"]
        assert "metabolite_citrate" not in memberships["Israeli10K"]

    @patch("seaborn.heatmap")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.figure")
    def test_visualization_generation(
        self, mock_figure, mock_savefig, mock_heatmap, action, temp_dir
    ):
        """Test that visualizations are created (mock matplotlib)."""
        memberships = {
            "Israeli10K": {"met1", "met2", "met3"},
            "UKBB": {"met2", "met3", "met4"},
            "Arivale": {"met3", "met4", "met5"},
            "Israeli10K_UKBB": {"met2", "met3"},
            "Israeli10K_Arivale": {"met3"},
            "UKBB_Arivale": {"met3", "met4"},
            "Israeli10K_UKBB_Arivale": {"met3"},
        }

        stats = {
            "Israeli10K_UKBB": OverlapStatistics(
                count=2,
                percentage_of_first=66.7,
                percentage_of_second=50.0,
                jaccard_index=0.5,
                metabolite_ids=["met2", "met3"],
                confidence_distribution={"high": 1, "medium": 1, "low": 0},
            ),
            "Israeli10K_Arivale": OverlapStatistics(
                count=1,
                percentage_of_first=33.3,
                percentage_of_second=20.0,
                jaccard_index=0.2,
                metabolite_ids=["met3"],
                confidence_distribution={"high": 1, "medium": 0, "low": 0},
            ),
            "UKBB_Arivale": OverlapStatistics(
                count=2,
                percentage_of_first=50.0,
                percentage_of_second=40.0,
                jaccard_index=0.33,
                metabolite_ids=["met3", "met4"],
                confidence_distribution={"high": 0, "medium": 2, "low": 0},
            ),
            "three_way": OverlapStatistics(
                count=1,
                percentage_of_first=33.3,
                percentage_of_second=33.3,
                percentage_of_third=20.0,
                jaccard_index=0.2,
                metabolite_ids=["met3"],
                confidence_distribution={"high": 1, "medium": 0, "low": 0},
            ),
        }

        # Mock the heatmap to avoid rendering issues
        mock_heatmap.return_value = MagicMock()

        viz_paths = action._generate_visualizations(
            memberships,
            stats,
            Path(temp_dir),
            ["venn_diagram_3way", "confidence_heatmap", "overlap_progression_chart"],
        )

        # Check that visualization methods were called
        assert len(viz_paths) >= 2  # At least venn and progression chart
        assert mock_figure.called or mock_savefig.called

    @patch("pandas.DataFrame.to_csv")
    def test_export_functionality(
        self,
        mock_to_csv,
        action,
        temp_dir,
        sample_three_way_matches,
        sample_two_way_matches,
    ):
        """Test CSV export of results."""
        stats = {
            "three_way": OverlapStatistics(
                count=2,
                percentage_of_first=66.7,
                percentage_of_second=50.0,
                percentage_of_third=66.7,
                jaccard_index=0.4,
                metabolite_ids=["metabolite_glucose", "metabolite_lactate"],
                confidence_distribution={"high": 2, "medium": 0, "low": 0},
            )
        }

        action._export_detailed_results(
            sample_three_way_matches,
            sample_two_way_matches,
            stats,
            Path(temp_dir),
            "test_mapping_v1",
        )

        # Check that CSV export was called
        assert mock_to_csv.called
        assert mock_to_csv.call_count >= 2  # At least matches and statistics CSVs

    def test_empty_overlap_handling(self, action):
        """Test handling when no overlaps exist."""
        # Create matches with no overlap
        three_way_matches = []
        two_way_matches = [
            {
                "metabolite_id": "metabolite_a",
                "match_confidence": 0.9,
                "dataset_count": 1,
                "is_complete": False,
                "israeli10k": {"field_name": "a"},
            },
            {
                "metabolite_id": "metabolite_b",
                "match_confidence": 0.9,
                "dataset_count": 1,
                "is_complete": False,
                "ukbb": {"field_id": "b"},
            },
        ]

        memberships = action._extract_dataset_memberships(
            three_way_matches, two_way_matches, confidence_threshold=0.8
        )

        stats = action._calculate_overlap_statistics(
            memberships, ["Israeli10K", "UKBB", "Arivale"], two_way_matches
        )

        # Check that empty overlaps are handled correctly
        assert stats["three_way"].count == 0
        assert stats["Israeli10K_UKBB"].count == 0
        assert stats["three_way"].jaccard_index == 0

    async def test_execute_typed_success(self, action, mock_context, temp_dir):
        """Test successful execution of the action."""
        params = CalculateThreeWayOverlapParams(
            input_key="three_way_combined_matches",
            dataset_names=["Israeli10K", "UKBB", "Arivale"],
            confidence_threshold=0.8,
            output_dir=temp_dir,
            mapping_combo_id="test_v1",
            generate_visualizations=[],
            output_key="overlap_statistics",
            export_detailed_results=False,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.details["success"] is True
        assert "statistics" in result.details
        assert len(result.provenance) > 0

    async def test_execute_typed_missing_data(self, action, temp_dir):
        """Test execution with missing input data."""
        context = MagicMock()
        context.get_action_data.return_value = {}

        params = CalculateThreeWayOverlapParams(
            input_key="missing_key",
            dataset_names=["Israeli10K", "UKBB", "Arivale"],
            confidence_threshold=0.8,
            output_dir=temp_dir,
            mapping_combo_id="test_v1",
            generate_visualizations=[],
            output_key="overlap_statistics",
            export_detailed_results=False,
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result.details["success"] is False
        assert "error" in result.details

    def test_confidence_distribution_calculation(self, action):
        """Test confidence distribution calculation."""
        metabolite_ids = {"met1", "met2", "met3"}
        all_matches = [
            {"metabolite_id": "met1", "match_confidence": 0.95},
            {"metabolite_id": "met2", "match_confidence": 0.75},
            {"metabolite_id": "met3", "match_confidence": 0.65},
        ]

        distribution = action._get_confidence_distribution(metabolite_ids, all_matches)

        assert distribution["high"] == 1  # met1
        assert distribution["medium"] == 1  # met2
        assert distribution["low"] == 1  # met3

    def test_complex_overlap_scenarios(self, action):
        """Test complex overlap scenarios with various dataset combinations."""
        # Create complex match data
        matches = [
            # Three-way match
            {
                "metabolite_id": "met_3way",
                "match_confidence": 0.9,
                "dataset_count": 3,
                "israeli10k": {"field_name": "3way"},
                "ukbb": {"field_id": "3way"},
                "arivale": {"biochemical_name": "3way"},
            },
            # Israeli10K-UKBB only
            {
                "metabolite_id": "met_i10k_ukbb",
                "match_confidence": 0.85,
                "dataset_count": 2,
                "israeli10k": {"field_name": "i10k_ukbb"},
                "ukbb": {"field_id": "i10k_ukbb"},
            },
            # Israeli10K-Arivale only
            {
                "metabolite_id": "met_i10k_arivale",
                "match_confidence": 0.87,
                "dataset_count": 2,
                "israeli10k": {"field_name": "i10k_arivale"},
                "arivale": {"biochemical_name": "i10k_arivale"},
            },
            # UKBB-Arivale only
            {
                "metabolite_id": "met_ukbb_arivale",
                "match_confidence": 0.82,
                "dataset_count": 2,
                "ukbb": {"field_id": "ukbb_arivale"},
                "arivale": {"biochemical_name": "ukbb_arivale"},
            },
            # Israeli10K only
            {
                "metabolite_id": "met_i10k_only",
                "match_confidence": 0.9,
                "dataset_count": 1,
                "israeli10k": {"field_name": "i10k_only"},
            },
        ]

        memberships = action._extract_dataset_memberships(matches, [], 0.8)

        # Verify memberships
        assert (
            len(memberships["Israeli10K"]) == 4
        )  # 3way, i10k_ukbb, i10k_arivale, i10k_only
        assert len(memberships["UKBB"]) == 3  # 3way, i10k_ukbb, ukbb_arivale
        assert len(memberships["Arivale"]) == 3  # 3way, i10k_arivale, ukbb_arivale

        assert len(memberships["Israeli10K_UKBB"]) == 2  # 3way, i10k_ukbb
        assert len(memberships["Israeli10K_Arivale"]) == 2  # 3way, i10k_arivale
        assert len(memberships["UKBB_Arivale"]) == 2  # 3way, ukbb_arivale
        assert len(memberships["Israeli10K_UKBB_Arivale"]) == 1  # 3way only

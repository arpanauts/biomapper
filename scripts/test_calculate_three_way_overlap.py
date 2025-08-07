#!/usr/bin/env python3
"""Test script for CALCULATE_THREE_WAY_OVERLAP action."""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any

from biomapper.core.strategy_actions.calculate_three_way_overlap import (
    CalculateThreeWayOverlapAction,
    CalculateThreeWayOverlapParams,
)


class MockContext:
    """Mock context for testing."""

    def __init__(self, datasets: Dict[str, Any]):
        self._datasets = datasets
        self._action_data = {"datasets": datasets}

    def get_action_data(self, key: str, default=None):
        return self._action_data.get(key, default)

    def set_action_data(self, key: str, value: Any):
        self._action_data[key] = value


def create_sample_data() -> Dict[str, Any]:
    """Create sample three-way match data."""
    return {
        "three_way_combined_matches": {
            "three_way_matches": [
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
                {
                    "metabolite_id": "metabolite_pyruvate",
                    "match_confidence": 0.92,
                    "match_methods": ["nightingale_direct", "cts_enriched"],
                    "dataset_count": 3,
                    "is_complete": True,
                    "israeli10k": {
                        "field_name": "pyruvate_nmr",
                        "display_name": "Pyruvate (NMR)",
                        "nightingale_name": "Pyruvate",
                    },
                    "ukbb": {"field_id": "23029", "title": "Pyruvate"},
                    "arivale": {
                        "biochemical_name": "pyruvate",
                        "hmdb": "HMDB0000243",
                        "kegg": "C00022",
                    },
                },
            ],
            "two_way_matches": [
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
                    "ukbb": {"field_id": "23030", "title": "Citrate"},
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
                    "ukbb": {"field_id": "23031", "title": "Creatinine"},
                },
                {
                    "metabolite_id": "metabolite_alanine",
                    "match_confidence": 0.78,
                    "match_methods": ["semantic_match"],
                    "dataset_count": 2,
                    "is_complete": False,
                    "israeli10k": {
                        "field_name": "alanine_nmr",
                        "display_name": "Alanine (NMR)",
                        "nightingale_name": "Alanine",
                    },
                    "arivale": {
                        "biochemical_name": "alanine",
                        "hmdb": "HMDB0000161",
                        "kegg": "C00041",
                    },
                },
            ],
        }
    }


async def main():
    """Run the test."""
    print("Testing CALCULATE_THREE_WAY_OVERLAP action")
    print("=" * 50)

    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create action and parameters
        action = CalculateThreeWayOverlapAction()
        params = CalculateThreeWayOverlapParams(
            input_key="three_way_combined_matches",
            dataset_names=["Israeli10K", "UKBB", "Arivale"],
            confidence_threshold=0.8,
            output_dir=temp_dir,
            mapping_combo_id="test_demo_v1",
            generate_visualizations=[
                "venn_diagram_3way",
                "confidence_heatmap",
                "overlap_progression_chart",
            ],
            output_key="overlap_statistics",
            export_detailed_results=True,
        )

        # Create mock context with sample data
        sample_data = create_sample_data()
        context = MockContext(sample_data)

        # Execute the action
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        # Print results
        print(f"\nExecution Success: {result.details['success']}")
        print(f"Message: {result.details['message']}")

        if "statistics" in result.details:
            stats = result.details["statistics"]

            print("\n--- Dataset Statistics ---")
            for dataset, info in stats.get("dataset_statistics", {}).items():
                print(f"{dataset}:")
                print(f"  Total metabolites: {info['total_metabolites']}")
                print(f"  Unique metabolites: {info['unique_metabolites']}")

            print("\n--- Overlap Statistics ---")
            for overlap_type, overlap_stats in stats.get(
                "overlap_statistics", {}
            ).items():
                print(f"\n{overlap_type}:")
                print(f"  Count: {overlap_stats['count']}")
                print(f"  Jaccard Index: {overlap_stats['jaccard_index']:.3f}")
                print(
                    f"  Percentage of first: {overlap_stats['percentage_of_first']:.1f}%"
                )
                print(
                    f"  Percentage of second: {overlap_stats['percentage_of_second']:.1f}%"
                )
                if overlap_stats.get("percentage_of_third") is not None:
                    print(
                        f"  Percentage of third: {overlap_stats['percentage_of_third']:.1f}%"
                    )
                print("  Confidence distribution:")
                for level, count in overlap_stats["confidence_distribution"].items():
                    print(f"    {level}: {count}")

        print("\n--- Generated Files ---")
        output_path = Path(temp_dir)
        for file in output_path.iterdir():
            print(f"  {file.name}")

        print("\nVisualization paths:")
        if "visualizations" in result.details.get("statistics", {}):
            for viz_type, path in result.details["statistics"][
                "visualizations"
            ].items():
                if path:
                    print(f"  {viz_type}: {Path(path).name}")


if __name__ == "__main__":
    asyncio.run(main())

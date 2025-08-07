#!/usr/bin/env python3
"""Test script for GenerateMetabolomicsReportAction with sample data."""

import asyncio
import logging
from pathlib import Path
import json

from biomapper.core.strategy_actions.generate_metabolomics_report import (
    GenerateMetabolomicsReportAction,
    GenerateMetabolomicsReportParams,
)
from biomapper.core.models import StrategyExecutionContext

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_data():
    """Create sample metabolomics data for testing."""
    # Sample statistics data
    statistics = {
        "total_unique_metabolites": 523,
        "three_way_overlap": {"count": 167, "percentage": 31.9},
        "pairwise_overlaps": {
            "Israeli10K_UKBB": {"overlap_count": 215, "jaccard_index": 0.412},
            "Israeli10K_Arivale": {"overlap_count": 189, "jaccard_index": 0.361},
            "UKBB_Arivale": {"overlap_count": 197, "jaccard_index": 0.376},
        },
        "dataset_counts": {
            "Israeli10K": {"total": 262, "unique": 247},
            "UKBB": {"total": 268, "unique": 253},
            "Arivale": {"total": 312, "unique": 294},
        },
        "overlap_summary": {
            "three_datasets": 167,
            "two_datasets": 112,
            "only_one_dataset": 244,
        },
        "visualization_files": {
            "venn_diagram": "./venn_diagram.png",
            "confidence_distribution": "./confidence_dist.png",
            "method_breakdown": "./method_breakdown.png",
        },
    }

    # Sample matches data
    matches = [
        {
            "metabolite_name": "Glucose",
            "Israeli10K_id": "XXL_VLDL_P_NMR",
            "UKBB_id": "23450",
            "Arivale_id": "glucose",
            "confidence_score": 0.98,
            "match_method": "fuzzy_match",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "Total cholesterol",
            "Israeli10K_id": "Total_C",
            "UKBB_id": "23400",
            "Arivale_id": "cholesterol_total",
            "confidence_score": 0.95,
            "match_method": "fuzzy_match",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "HDL cholesterol",
            "Israeli10K_id": "HDL_C",
            "UKBB_id": "23405",
            "Arivale_id": "hdl_cholesterol",
            "confidence_score": 0.93,
            "match_method": "api_enriched",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "LDL cholesterol",
            "Israeli10K_id": "LDL_C",
            "UKBB_id": "23410",
            "Arivale_id": "ldl_cholesterol",
            "confidence_score": 0.89,
            "match_method": "api_enriched",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "Triglycerides",
            "Israeli10K_id": "TG",
            "UKBB_id": "23415",
            "Arivale_id": "triglycerides",
            "confidence_score": 0.91,
            "match_method": "fuzzy_match",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "Alanine",
            "Israeli10K_id": "Ala",
            "UKBB_id": "23420",
            "Arivale_id": "alanine",
            "confidence_score": 0.76,
            "match_method": "semantic",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "Glutamine",
            "Israeli10K_id": "Gln",
            "UKBB_id": "23425",
            "Arivale_id": "glutamine",
            "confidence_score": 0.72,
            "match_method": "semantic",
            "match_type": "three_way",
        },
        {
            "metabolite_name": "Glycine",
            "Israeli10K_id": "Gly",
            "UKBB_id": "23430",
            "Arivale_id": "glycine",
            "confidence_score": 0.85,
            "match_method": "api_enriched",
            "match_type": "three_way",
        },
    ]

    # Sample metrics data
    metrics = {
        "metrics.baseline": {
            "total_matches": 120,
            "success_rate": 94.5,
            "average_confidence": 0.91,
            "processing_time": 0.8,
        },
        "metrics.api_enriched": {
            "total_matches": 65,
            "success_rate": 87.3,
            "average_confidence": 0.84,
            "processing_time": 5.2,
        },
        "metrics.semantic": {
            "total_matches": 38,
            "success_rate": 81.2,
            "average_confidence": 0.76,
            "processing_time": 12.4,
        },
    }

    # Nightingale reference data
    nightingale_reference = {
        "total_mappings": 215,
        "confidence_range": [0.95, 1.0],
        "platform": "Nightingale NMR",
        "datasets": ["Israeli10K", "UKBB"],
    }

    return {
        "statistics": statistics,
        "matches": matches,
        "metrics": metrics,
        "nightingale_reference": nightingale_reference,
    }


async def test_report_generation():
    """Test the report generation with sample data."""
    # Create output directory
    output_dir = Path("./test_reports")
    output_dir.mkdir(exist_ok=True)

    # Create sample data
    sample_data = create_sample_data()

    # Create mock context - StrategyExecutionContext requires initialization params
    context = StrategyExecutionContext(
        initial_identifier="test_metabolite",
        current_identifier="test_metabolite",
        ontology_type="metabolite",
    )

    # Add data to context using set_action_data
    context.set_action_data(
        "results", {"three_way_statistics": sample_data["statistics"]}
    )
    context.set_action_data(
        "datasets",
        {
            "three_way_combined_matches": sample_data["matches"],
            "nightingale_reference_map": sample_data["nightingale_reference"],
        },
    )
    context.set_action_data("metrics", sample_data["metrics"])

    # Create parameters
    params = GenerateMetabolomicsReportParams(
        statistics_key="three_way_statistics",
        matches_key="three_way_combined_matches",
        nightingale_reference="nightingale_reference_map",
        metrics_keys=["metrics.baseline", "metrics.api_enriched", "metrics.semantic"],
        output_dir=str(output_dir),
        report_format="markdown",
        include_sections=[
            "executive_summary",
            "methodology_overview",
            "dataset_overview",
            "progressive_matching_results",
            "three_way_overlap_analysis",
            "confidence_distribution",
            "quality_metrics",
            "recommendations",
        ],
        export_formats=["markdown", "html", "json"],
        include_visualizations=True,
        max_examples=10,
    )

    # Create and execute action
    action = GenerateMetabolomicsReportAction()

    logger.info("Starting report generation...")
    result = await action.execute_typed(params, context)

    if result.details.get("exported_files"):
        logger.info("Report generation successful!")
        logger.info(f"Exported files: {result.details['exported_files']}")
        logger.info(
            f"Sections generated: {result.details['sections_generated']}/{result.details['total_sections']}"
        )
        logger.info(f"Output directory: {result.details['output_directory']}")
        logger.info(f"Report size: {result.details['report_size_kb']:.2f} KB")

        # Display sample of the markdown report
        md_file = Path(result.details["exported_files"]["markdown"])
        if md_file.exists():
            content = md_file.read_text()
            logger.info("\n=== First 50 lines of the report ===")
            lines = content.split("\n")[:50]
            for line in lines:
                print(line)
            logger.info("\n=== End of preview ===")
    else:
        logger.error(
            f"Report generation failed: {result.details.get('error', 'Unknown error')}"
        )

    return result


async def test_with_existing_data():
    """Test with existing metabolomics data if available."""
    # Check if we have real data files
    data_dir = Path("./data/results")
    if not data_dir.exists():
        logger.warning(f"Data directory {data_dir} not found. Using sample data.")
        return await test_report_generation()

    # Look for existing statistics file
    stats_file = data_dir / "three_way_statistics.json"
    if stats_file.exists():
        logger.info("Found existing statistics file, loading real data...")

        # Load real data
        with open(stats_file) as f:
            statistics = json.load(f)

        # Create context with real data
        context = StrategyExecutionContext(
            initial_identifier="test_metabolite",
            current_identifier="test_metabolite",
            ontology_type="metabolite",
        )
        context.set_action_data("results", {"three_way_statistics": statistics})

        # Check for matches file
        matches_file = data_dir / "three_way_matches.json"
        if matches_file.exists():
            with open(matches_file) as f:
                matches = json.load(f)
            context.set_action_data("datasets", {"three_way_combined_matches": matches})
        else:
            context.set_action_data("datasets", {"three_way_combined_matches": []})

        # Add some mock metrics
        context.set_action_data(
            "metrics",
            {
                "metrics.baseline": {"total_matches": 100, "success_rate": 90},
                "metrics.api_enriched": {"total_matches": 50, "success_rate": 85},
                "metrics.semantic": {"total_matches": 30, "success_rate": 80},
            },
        )

        # Generate report with real data
        logger.info("Generating report with real metabolomics data...")
        # ... rest of the function
    else:
        logger.info("No real data found, using sample data.")
        return await test_report_generation()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_report_generation())

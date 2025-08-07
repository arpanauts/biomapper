"""
Example client script for executing protein mapping strategies.
This demonstrates the pattern for running any of the 9 protein mappings.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from biomapper.core.engine import StrategyEngine
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_protein_mapping(
    source_name: str,
    target_name: str,
    strategy_file: str = None,
    output_dir: str = None,
):
    """
    Run a protein mapping between two datasets.

    Args:
        source_name: Name of source dataset (e.g., "UKBB", "Arivale", "HPA")
        target_name: Name of target dataset (e.g., "HPA", "SPOKE", "KG2C")
        strategy_file: Path to YAML strategy file (optional, will auto-detect)
        output_dir: Output directory (optional, will use default)
    """

    # Auto-detect strategy file if not provided
    if not strategy_file:
        strategy_file = f"configs/strategies/{source_name.lower()}_{target_name.lower()}_protein_mapping.yaml"

    # Set default output directory
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"results/protein_mappings/{source_name}_{target_name}/{timestamp}"

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting {source_name} → {target_name} protein mapping")
    logger.info(f"Strategy: {strategy_file}")
    logger.info(f"Output: {output_dir}")

    try:
        # Initialize strategy engine
        engine = StrategyEngine()

        # Load strategy
        strategy = await engine.load_strategy(strategy_file)

        # Override output directory in config
        strategy.config["output_dir"] = output_dir

        # Execute strategy
        result = await engine.execute_strategy(
            strategy,
            initial_context={
                "source_name": source_name,
                "target_name": target_name,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Log summary
        logger.info("Mapping completed successfully!")
        logger.info(f"Total execution time: {result.execution_time}s")

        # Print key statistics
        if "overlap_analysis" in result.context.get("statistics", {}):
            stats = result.context["statistics"]["overlap_analysis"]
            logger.info(f"Proteins in {source_name}: {stats.get('set_a_count', 0)}")
            logger.info(f"Proteins in {target_name}: {stats.get('set_b_count', 0)}")
            logger.info(f"Overlapping proteins: {stats.get('intersection_count', 0)}")
            logger.info(f"Jaccard index: {stats.get('jaccard_index', 0):.3f}")

        # Report location
        report_files = result.context.get("output_files", {})
        if report_files:
            logger.info("Reports generated:")
            for file_type, file_path in report_files.items():
                logger.info(f"  - {file_type}: {file_path}")

        return result

    except Exception as e:
        logger.error(f"Mapping failed: {str(e)}")
        raise


async def run_all_protein_mappings():
    """Run all 9 protein mapping combinations."""

    mappings = [
        ("UKBB", "HPA"),
        ("UKBB", "QIN"),
        ("HPA", "QIN"),
        ("Arivale", "SPOKE"),
        ("Arivale", "KG2C"),
        ("Arivale", "UKBB"),
        ("UKBB", "KG2C"),
        ("UKBB", "SPOKE"),
        ("HPA", "SPOKE"),
    ]

    results = {}
    for source, target in mappings:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running {source} → {target} mapping")
        logger.info(f"{'='*60}")

        try:
            result = await run_protein_mapping(source, target)
            results[f"{source}_{target}"] = {
                "status": "success",
                "stats": result.context.get("statistics", {}),
            }
        except Exception as e:
            logger.error(f"Failed: {e}")
            results[f"{source}_{target}"] = {"status": "failed", "error": str(e)}

    # Summary report
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY OF ALL MAPPINGS")
    logger.info("=" * 60)

    for mapping, result in results.items():
        status = result["status"]
        logger.info(f"{mapping}: {status.upper()}")
        if status == "success" and "overlap_analysis" in result.get("stats", {}):
            overlap = result["stats"]["overlap_analysis"].get("intersection_count", 0)
            logger.info(f"  - Overlapping proteins: {overlap}")

    return results


# Command-line interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run protein mappings")
    parser.add_argument("source", help="Source dataset name (e.g., UKBB)")
    parser.add_argument("target", help="Target dataset name (e.g., HPA)")
    parser.add_argument("--strategy", help="Path to strategy YAML file")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Run all 9 mappings")

    args = parser.parse_args()

    if args.all:
        asyncio.run(run_all_protein_mappings())
    else:
        asyncio.run(
            run_protein_mapping(args.source, args.target, args.strategy, args.output)
        )


# Usage examples:
# python protein_mapping.py UKBB HPA
# python protein_mapping.py Arivale SPOKE --output results/custom_output/
# python protein_mapping.py --all

#!/usr/bin/env python3
"""
Metabolomics Harmonization Pipeline - API Client

This script executes metabolomics harmonization via the Biomapper API.
Supports both progressive enhancement and three-way analysis workflows.

Usage:
    python run_metabolomics_harmonization.py [options]

Examples:
    # Run progressive enhancement (default)
    python run_metabolomics_harmonization.py
    
    # Run three-way analysis
    python run_metabolomics_harmonization.py --three-way
    
    # Use custom parameters
    python run_metabolomics_harmonization.py --parameters params.json
    
    # Watch progress in real-time
    python run_metabolomics_harmonization.py --watch

MIGRATION NOTES:
This replaces the previous 691-line orchestration script with a simple API client.
All orchestration logic is now handled by the biomapper-api service.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from biomapper_client import BiomapperClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Execute metabolomics harmonization pipeline via API."""

    parser = argparse.ArgumentParser(
        description="Run metabolomics harmonization pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Progressive enhancement (default)
  %(prog)s --three-way        # Three-way analysis  
  %(prog)s --watch            # Watch progress
  %(prog)s --parameters custom.json  # Custom parameters
        """,
    )

    # Strategy selection
    parser.add_argument(
        "--strategy",
        default="METABOLOMICS_PROGRESSIVE_ENHANCEMENT",
        help="Strategy name to execute (default: METABOLOMICS_PROGRESSIVE_ENHANCEMENT)",
    )
    parser.add_argument(
        "--three-way",
        action="store_true",
        help="Run three-way analysis (uses THREE_WAY_METABOLOMICS_COMPLETE strategy)",
    )

    # Configuration options
    parser.add_argument(
        "--parameters", type=Path, help="JSON file with parameter overrides"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Biomapper API URL (default: http://localhost:8000)",
    )

    # Execution options
    parser.add_argument(
        "--watch", action="store_true", help="Watch execution progress in real-time"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate strategy without executing"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Output options
    parser.add_argument(
        "--output-dir", type=Path, help="Override output directory for results"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine strategy
    if args.three_way:
        strategy_name = "THREE_WAY_METABOLOMICS_COMPLETE"
        logger.info("Using three-way metabolomics analysis strategy")
    else:
        strategy_name = args.strategy
        logger.info(f"Using strategy: {strategy_name}")

    # Load parameters if provided
    parameters = {}
    if args.parameters:
        try:
            with open(args.parameters) as f:
                parameters = json.load(f)
            logger.info(f"Loaded parameters from {args.parameters}")
        except Exception as e:
            logger.error(f"Failed to load parameters from {args.parameters}: {e}")
            return 1

    # Override output directory if specified
    if args.output_dir:
        parameters["output_dir"] = str(args.output_dir)
        logger.info(f"Output directory: {args.output_dir}")

    # Prepare context for API
    context = {
        "source_endpoint_name": "",  # Not used in metabolomics strategies
        "target_endpoint_name": "",  # Not used in metabolomics strategies
        "input_identifiers": [],  # Strategies load their own data
        "parameters": parameters,
        "options": {"dry_run": args.dry_run, "debug": args.debug},
    }

    try:
        logger.info("Connecting to Biomapper API...")
        async with BiomapperClient(base_url=args.api_url) as client:
            # Dry run validation
            if args.dry_run:
                logger.info("🔍 Validating strategy configuration...")
                # TODO: Add strategy validation endpoint when available
                logger.info("✅ Strategy validation would run here")
                return 0

            logger.info(f"🚀 Starting execution: {strategy_name}")

            # Execute strategy
            if args.watch:
                # TODO: Implement progress watching when WebSocket/SSE is available
                logger.info("📊 Progress watching will be available when implemented")
                result = await client.execute_strategy(
                    strategy_name=strategy_name, context=context
                )
            else:
                result = await client.execute_strategy(
                    strategy_name=strategy_name, context=context
                )

            # Process results
            if result.get("success", False):
                logger.info("✅ Pipeline completed successfully!")

                # Log execution summary
                if "execution_time" in result:
                    logger.info(f"⏱️  Execution time: {result['execution_time']}")

                if "step_results" in result:
                    logger.info("📋 Step Results:")
                    for step in result["step_results"]:
                        if step.get("status") == "success":
                            input_count = step.get("input_count", "N/A")
                            output_count = step.get("output_count", "N/A")
                            logger.info(
                                f"  ✅ {step['step_id']}: {input_count} → {output_count}"
                            )
                        else:
                            error = step.get("details", {}).get(
                                "error", "Unknown error"
                            )
                            logger.error(f"  ❌ {step['step_id']}: {error}")

                # Log key statistics
                if "summary" in result:
                    summary = result["summary"]
                    if "total_metabolites_processed" in summary:
                        logger.info(
                            f"🧪 Total metabolites processed: {summary['total_metabolites_processed']}"
                        )
                    if "final_match_rate" in summary:
                        logger.info(
                            f"🎯 Final match rate: {summary['final_match_rate']:.1%}"
                        )
                    if "improvement_over_baseline" in summary:
                        logger.info(
                            f"📈 Improvement over baseline: +{summary['improvement_over_baseline']:.1%}"
                        )

                # Log output files
                if "output_files" in result:
                    logger.info("📁 Generated files:")
                    for file_path in result["output_files"]:
                        if Path(file_path).exists():
                            size = Path(file_path).stat().st_size
                            logger.info(f"  - {file_path} ({size:,} bytes)")
                        else:
                            logger.info(f"  - {file_path}")

                return 0

            else:
                # Execution failed
                error_msg = result.get("message", "Unknown error")
                logger.error(f"❌ Pipeline failed: {error_msg}")

                # Log detailed error information
                if "details" in result:
                    details = result["details"]
                    if "failed_step" in details:
                        logger.error(f"💥 Failed at step: {details['failed_step']}")
                    if "error_details" in details:
                        logger.error(f"🔍 Error details: {details['error_details']}")

                # Log partial results if available
                if "step_results" in result:
                    successful_steps = [
                        s
                        for s in result["step_results"]
                        if s.get("status") == "success"
                    ]
                    if successful_steps:
                        logger.info(
                            f"✅ {len(successful_steps)} steps completed successfully before failure"
                        )

                return 1

    except KeyboardInterrupt:
        logger.warning("⚠️  Execution interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if args.debug:
            import traceback

            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

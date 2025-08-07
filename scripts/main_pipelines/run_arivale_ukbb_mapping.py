#!/usr/bin/env python
"""
Execute Arivale to UKBB protein mapping using the MVP action pipeline.

This script demonstrates the complete workflow:
1. Load Arivale protein data
2. Load UKBB protein data  
3. Merge with UniProt historical resolution
4. Calculate set overlap and generate visualizations

Results are saved to results/Arivale_UKBB/ directory.
"""
import asyncio
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
    """Execute the Arivale to UKBB protein mapping pipeline."""

    logger.info("Starting Arivale to UKBB protein mapping...")

    try:
        # Initialize client using async context manager
        async with BiomapperClient(base_url="http://localhost:8000") as client:
            # Execute strategy
            context = {
                "source_endpoint_name": "",  # MVP strategies don't use endpoints
                "target_endpoint_name": "",  # MVP strategies don't use endpoints
                "input_identifiers": [],  # MVP strategies load their own data
                "options": {},
            }

            result = await client.execute_strategy(
                strategy_name="ARIVALE_TO_UKBB_PROTEIN_MAPPING", context=context
            )

        # Log success
        logger.info("✅ Arivale to UKBB protein mapping completed successfully!")

        # Print key results
        if "step_results" in result:
            for step in result["step_results"]:
                if step.get("status") == "success":
                    logger.info(
                        f"  ✅ {step['step_id']}: {step['input_count']} → {step['output_count']}"
                    )
                else:
                    logger.error(
                        f"  ❌ {step['step_id']}: {step.get('details', {}).get('error', 'Unknown error')}"
                    )

        # Check for analysis results
        if "summary" in result and "step_results" in result["summary"]:
            analysis_steps = [
                s
                for s in result["summary"]["step_results"]
                if s.get("action_type") == "CALCULATE_SET_OVERLAP"
            ]
            for step in analysis_steps:
                if step.get("status") == "success":
                    logger.info(f"📊 Analysis complete: {step['step_id']}")
                    logger.info("📁 Results saved to: results/Arivale_UKBB/")

        return 0

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        logger.exception("Full error details:")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

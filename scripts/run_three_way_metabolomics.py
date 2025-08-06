#!/usr/bin/env python3
"""
Run the complete three-way metabolomics mapping pipeline.
This uses all newly implemented components for comprehensive analysis.

DEPRECATION WARNING:
This script is deprecated and will be removed in v2.0.
Please use the new API client instead:
    biomapper run three_way_metabolomics_complete
    or
    python scripts/pipelines/run_three_way_metabolomics.py
"""

import warnings
warnings.warn(
    "This script is deprecated and will be removed in v2.0. "
    "Use 'biomapper run three_way_metabolomics_complete' or "
    "'python scripts/pipelines/run_three_way_metabolomics.py' instead.",
    DeprecationWarning,
    stacklevel=2
)

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import os
import yaml

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.minimal_strategy_service import MinimalStrategyService
from biomapper.core.models.execution_context import StrategyExecutionContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variables for APIs if needed
if "OPENAI_API_KEY" not in os.environ:
    logger.warning("OPENAI_API_KEY not set - semantic matching may fail")


async def run_three_way_pipeline():
    """Execute the complete three-way metabolomics mapping pipeline."""
    
    # Load the strategy configuration
    strategy_path = Path(__file__).parent.parent / "configs" / "strategies" / "three_way_metabolomics_complete.yaml"
    
    if not strategy_path.exists():
        logger.error(f"Strategy file not found: {strategy_path}")
        return
    
    logger.info("=" * 80)
    logger.info("Starting Three-Way Metabolomics Mapping Pipeline")
    logger.info("=" * 80)
    
    try:
        # Initialize the strategy service
        service = MinimalStrategyService()
        
        # Load strategy
        with open(strategy_path, 'r') as f:
            strategy = yaml.safe_load(f)
        
        # Create execution context
        context = StrategyExecutionContext(
            input_identifiers=[],  # Not used for this pipeline
            output_ontology_type="metabolite"
        )
        
        # Execute the strategy
        result = await service.execute_strategy(strategy, context)
        
        # Log results
        if result['success']:
            logger.info("=" * 80)
            logger.info("Pipeline completed successfully!")
            logger.info("=" * 80)
            
            # Log key statistics
            if "three_way_statistics" in result.get("results", {}):
                stats = result["results"]["three_way_statistics"]
                logger.info(f"Three-way overlap: {stats.get('three_way_overlap', {}).get('count', 0)} metabolites")
            
            # Check for generated files
            output_dir = Path("/home/ubuntu/biomapper/data/results/metabolomics_three_way")
            if output_dir.exists():
                logger.info(f"\nGenerated files in {output_dir}:")
                for file in output_dir.rglob("*"):
                    if file.is_file():
                        logger.info(f"  - {file.relative_to(output_dir)}")
        else:
            logger.error(f"Pipeline failed: {result.get('message', 'Unknown error')}")
            if result.get('details'):
                logger.error(f"Details: {result['details']}")
                
    except Exception as e:
        logger.error(f"Error executing pipeline: {e}", exc_info=True)


def main():
    """Main entry point."""
    asyncio.run(run_three_way_pipeline())


if __name__ == "__main__":
    main()
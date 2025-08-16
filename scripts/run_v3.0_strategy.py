#!/usr/bin/env python
"""Run the v3.0 progressive protein mapping strategy."""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper_client import BiomapperClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the v3.0 progressive strategy."""
    logger.info("Starting v3.0 progressive protein mapping strategy")
    
    # Initialize client
    client = BiomapperClient(base_url="http://localhost:8000")
    
    # Check API health
    health = client.health()
    logger.info(f"API Health: {health}")
    
    # Run strategy
    strategy_name = "prot_arv_to_kg2c_uniprot_v3.0_progressive"
    
    logger.info(f"Running strategy: {strategy_name}")
    result = client.run(strategy_name)
    
    logger.info(f"Strategy completed successfully!")
    logger.info(f"Job ID: {result.get('job_id')}")
    logger.info(f"Status: {result.get('status')}")
    
    # Show outputs
    if 'output_files' in result:
        logger.info("Output files created:")
        for file in result['output_files']:
            logger.info(f"  - {file}")
    
    # Show statistics
    if 'statistics' in result:
        stats = result['statistics']
        if 'progressive_stats' in stats:
            prog_stats = stats['progressive_stats']
            logger.info("\nProgressive Mapping Results:")
            logger.info(f"  Total Processed: {prog_stats.get('total_processed', 0)}")
            logger.info(f"  Final Match Rate: {prog_stats.get('final_match_rate', 0):.1%}")
            
            if 'stages' in prog_stats:
                logger.info("\n  Stage Breakdown:")
                for stage_num, stage_data in prog_stats['stages'].items():
                    logger.info(f"    Stage {stage_num}: {stage_data.get('name', 'Unknown')}")
                    if 'matched' in stage_data:
                        logger.info(f"      Matched: {stage_data['matched']}")
                    if 'new_matches' in stage_data:
                        logger.info(f"      New Matches: {stage_data['new_matches']}")
                    if 'cumulative_matched' in stage_data:
                        logger.info(f"      Cumulative: {stage_data['cumulative_matched']}")
    
    logger.info("\nStrategy execution completed successfully!")
    
    return result

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}", exc_info=True)
        sys.exit(1)
#!/usr/bin/env python
"""Run the v3.0 progressive strategy directly without API."""

import sys
import logging
from pathlib import Path
from datetime import datetime
import yaml
import json
import asyncio

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.minimal_strategy_service import MinimalStrategyService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the v3.0 progressive strategy directly."""
    logger.info("Starting v3.0 progressive protein mapping strategy (direct execution)")
    
    # Load strategy configuration
    strategy_path = Path("/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml")
    
    with open(strategy_path, 'r') as f:
        strategy_config = yaml.safe_load(f)
    
    logger.info(f"Loaded strategy: {strategy_config['name']}")
    logger.info(f"Description: {strategy_config['description'][:100]}...")
    
    # Initialize service
    strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies")
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Execute strategy
    logger.info("Executing strategy...")
    start_time = datetime.now()
    
    try:
        # Execute strategy by name (the service will load it from disk)
        result = await service.execute_strategy(strategy_config['name'])
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Strategy completed in {execution_time:.2f} seconds")
        
        # Extract context data
        context = result.get('context', {})
        
        # Show progressive statistics
        if 'progressive_stats' in context:
            prog_stats = context['progressive_stats']
            logger.info("\n=== Progressive Mapping Results ===")
            logger.info(f"Total Processed: {prog_stats.get('total_processed', 0)}")
            logger.info(f"Final Match Rate: {prog_stats.get('final_match_rate', 0):.1%}")
            logger.info(f"Total Time: {prog_stats.get('total_time', 'Unknown')}")
            
            if 'stages' in prog_stats:
                logger.info("\nStage Breakdown:")
                for stage_num, stage_data in sorted(prog_stats['stages'].items()):
                    logger.info(f"\n  Stage {stage_num}: {stage_data.get('name', 'Unknown')}")
                    logger.info(f"    Method: {stage_data.get('method', 'Unknown')}")
                    
                    if 'matched' in stage_data:
                        matched = stage_data['matched']
                        unmatched = stage_data.get('unmatched', 0)
                        total = matched + unmatched
                        match_rate = matched / total if total > 0 else 0
                        logger.info(f"    Matched: {matched:,} ({match_rate:.1%})")
                        logger.info(f"    Unmatched: {unmatched:,}")
                    elif 'new_matches' in stage_data:
                        logger.info(f"    New Matches: {stage_data['new_matches']:,}")
                        logger.info(f"    Cumulative: {stage_data['cumulative_matched']:,}")
                    
                    logger.info(f"    Time: {stage_data.get('computation_time', 'Unknown')}")
                    
                    if 'api_calls' in stage_data:
                        logger.info(f"    API Calls: {stage_data['api_calls']}")
            
            if 'match_type_distribution' in prog_stats:
                logger.info("\nMatch Type Distribution:")
                for match_type, count in prog_stats['match_type_distribution'].items():
                    percentage = count / prog_stats.get('total_processed', 1) * 100
                    logger.info(f"  {match_type}: {count:,} ({percentage:.1f}%)")
        
        # Show output files
        if 'output_files' in context:
            logger.info("\nOutput Files Created:")
            for file in context['output_files']:
                logger.info(f"  - {file}")
        
        # Save full results
        output_path = Path("/tmp/biomapper/v3.0_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            # Convert context to serializable format
            serializable_context = {
                'progressive_stats': context.get('progressive_stats', {}),
                'statistics': context.get('statistics', {}),
                'output_files': context.get('output_files', []),
                'execution_time': execution_time
            }
            json.dump(serializable_context, f, indent=2)
        
        logger.info(f"\nFull results saved to: {output_path}")
        
        # Check for errors
        if 'errors' in context and context['errors']:
            logger.warning(f"\nErrors encountered: {len(context['errors'])}")
            for error in context['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        logger.info("\n=== Strategy Execution Completed Successfully! ===")
        
        return result
        
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
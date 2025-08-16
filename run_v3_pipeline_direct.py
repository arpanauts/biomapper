#!/usr/bin/env python3
"""
Direct test of the v3.0 progressive pipeline without API server.
"""

import asyncio
import sys
from pathlib import Path
import logging
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from biomapper.core.minimal_strategy_service import MinimalStrategyService


async def run_pipeline_direct():
    """Run the v3.0 pipeline directly using MinimalStrategyService."""
    
    print("=" * 60)
    print("Running prot_arv_to_kg2c_uniprot_v3.0_progressive directly")
    print("=" * 60)
    
    # Initialize the service with strategies directory
    strategies_dir = "/home/ubuntu/biomapper/configs/strategies"
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Strategy file path
    strategy_path = Path("/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml")
    
    if not strategy_path.exists():
        print(f"✗ Strategy file not found: {strategy_path}")
        return False
    
    print(f"✓ Found strategy file: {strategy_path}")
    
    try:
        # Strategy name
        strategy_name = "prot_arv_to_kg2c_uniprot_v3.0_progressive"
        
        # Check if strategy is loaded
        if strategy_name not in service.strategies:
            print(f"✗ Strategy not found in loaded strategies: {strategy_name}")
            return False
        
        strategy = service.strategies[strategy_name]
        print(f"✓ Strategy loaded: {strategy['name']}")
        print(f"  Description: {strategy.get('description', 'N/A')[:100]}...")
        
        # Execute the strategy
        print("\nExecuting strategy...")
        print("-" * 40)
        
        result = await service.execute_strategy(strategy_name)
        
        # If we got here without exception, the strategy succeeded
        success = True
        
        print("\n" + "=" * 40)
        
        if success:
            print("✓ Pipeline completed successfully!")
            
            # Show statistics
            if "statistics" in result:
                print("\nStatistics:")
                stats = result["statistics"]
                for key, value in stats.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k2, v2 in value.items():
                            print(f"    {k2}: {v2}")
                    else:
                        print(f"  {key}: {value}")
            
            # Show output files
            if "output_files" in result:
                print("\nOutput files:")
                for file_path in result["output_files"]:
                    print(f"  - {file_path}")
            
            # Show progressive stats if available
            if "progressive_stats" in result.get("context", {}):
                print("\nProgressive mapping statistics:")
                prog_stats = result["context"]["progressive_stats"]
                print(f"  Total processed: {prog_stats.get('total_processed', 'N/A')}")
                if "stages" in prog_stats:
                    for stage_num, stage_data in prog_stats["stages"].items():
                        print(f"  Stage {stage_num} ({stage_data.get('name', 'unknown')}):")
                        print(f"    Method: {stage_data.get('method', 'N/A')}")
                        print(f"    Matched: {stage_data.get('matched', 0)}")
                        print(f"    Cumulative: {stage_data.get('cumulative_matched', 0)}")
                print(f"  Final match rate: {prog_stats.get('final_match_rate', 0):.2%}")
            
            return True
            
    except Exception as e:
        print(f"✗ Error running pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    success = await run_pipeline_direct()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
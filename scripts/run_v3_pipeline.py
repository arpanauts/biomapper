#!/usr/bin/env python3
"""
Run the v3.0 progressive protein mapping strategy end-to-end.

This script executes the complete v3.0 pipeline with production data.
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add biomapper to path
sys.path.insert(0, "/home/ubuntu/biomapper")

# Load environment variables for API keys
load_dotenv("/home/ubuntu/biomapper/.env")

from biomapper.core.minimal_strategy_service import MinimalStrategyService


async def run_v3_pipeline():
    """Run the v3.0 progressive mapping pipeline."""
    
    print("=" * 80)
    print("RUNNING V3.0 PROGRESSIVE PROTEIN MAPPING PIPELINE")
    print("=" * 80)
    print(f"Start time: {datetime.now()}")
    
    # Strategy configuration
    strategy_name = "prot_arv_to_kg2c_uniprot_v3.0_progressive"
    strategies_dir = "/home/ubuntu/biomapper/configs/strategies/experimental"
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"/tmp/biomapper/v3.0_run_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nConfiguration:")
    print(f"  Strategy: {strategy_name}")
    print(f"  Output dir: {output_dir}")
    
    # Check environment
    print(f"\nEnvironment check:")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print(f"  ✅ ANTHROPIC_API_KEY found ({len(anthropic_key)} chars)")
    else:
        print(f"  ⚠️  ANTHROPIC_API_KEY not found - LLM analysis will be skipped")
    
    gdrive_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if gdrive_creds and os.path.exists(gdrive_creds):
        print(f"  ✅ Google Drive credentials found: {gdrive_creds}")
    else:
        print(f"  ⚠️  Google Drive credentials not found - sync will be skipped")
    
    try:
        # Initialize service
        print(f"\nInitializing strategy service...")
        service = MinimalStrategyService(strategies_dir=strategies_dir)
        
        # Check if strategy loaded
        if strategy_name not in service.strategies:
            print(f"❌ Strategy '{strategy_name}' not found")
            print(f"Available strategies: {list(service.strategies.keys())[:5]}...")
            return False
        
        strategy = service.strategies[strategy_name]
        print(f"✅ Strategy loaded successfully")
        print(f"  Steps: {len(strategy.get('steps', []))}")
        
        # Override output directory
        parameters = {
            "output_dir": output_dir,
            "enable_llm_analysis": anthropic_key is not None,
            "enable_google_drive_sync": False  # Disable for now to focus on core pipeline
        }
        
        # Execute strategy
        print(f"\n" + "=" * 80)
        print(f"EXECUTING STRATEGY")
        print(f"=" * 80)
        
        # Create initial context
        initial_context = {
            "datasets": {},
            "statistics": {},
            "output_files": [],
            "progressive_stats": {},
            "parameters_override": parameters
        }
        
        # Execute the full strategy
        result = await service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name="",
            target_endpoint_name="",
            input_identifiers=[],
            context=initial_context
        )
        
        print(f"\nExecution completed")
        
        # Get the execution context from the result
        execution_context = result
        
        # Summary
        print(f"\n" + "=" * 80)
        print(f"PIPELINE EXECUTION SUMMARY")
        print(f"=" * 80)
        
        # Check progressive stats
        progressive_stats = execution_context.get("progressive_stats", {})
        if progressive_stats:
            total = progressive_stats.get("total_processed", 0)
            stages = progressive_stats.get("stages", {})
            
            print(f"\nProgressive Mapping Results:")
            print(f"  Total proteins: {total}")
            
            for stage_num in sorted(stages.keys()):
                stage = stages[stage_num]
                print(f"\n  Stage {stage_num}: {stage.get('name', 'Unknown')}")
                print(f"    Method: {stage.get('method', 'Unknown')}")
                print(f"    Matched: {stage.get('matched', 0)}")
                print(f"    Cumulative: {stage.get('cumulative_matched', 0)}")
                
            final_rate = progressive_stats.get("final_match_rate", 0)
            print(f"\n  Final match rate: {final_rate:.1%}")
        
        # Check output files
        output_files = execution_context.get("output_files", [])
        if output_files:
            print(f"\nGenerated files ({len(output_files)}):")
            for file_path in output_files[:10]:  # Show first 10
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    print(f"  ✅ {Path(file_path).name} ({size:,} bytes)")
                else:
                    print(f"  ❌ {Path(file_path).name} (not found)")
        
        print(f"\nEnd time: {datetime.now()}")
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    success = await run_v3_pipeline()
    
    if success:
        print(f"\n" + "=" * 80)
        print(f"✅ V3.0 PIPELINE COMPLETED SUCCESSFULLY")
        print(f"=" * 80)
    else:
        print(f"\n" + "=" * 80)
        print(f"❌ V3.0 PIPELINE FAILED")
        print(f"=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async pipeline
    asyncio.run(main())
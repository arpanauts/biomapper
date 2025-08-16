#!/usr/bin/env python3
"""
Run the pipeline directly without API to measure actual execution time
"""
import asyncio
import time
import os
from datetime import datetime
import sys
sys.path.insert(0, '/home/ubuntu/biomapper')

from biomapper.core.minimal_strategy_service import MinimalStrategyService
import yaml

async def run_direct():
    """Run the strategy directly without API layer"""
    
    # Setup environment
    os.environ['OUTPUT_DIR'] = '/tmp/biomapper_results'
    os.environ['TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(os.environ['OUTPUT_DIR'], exist_ok=True)
    
    # Clear previous results
    for f in os.listdir(os.environ['OUTPUT_DIR']):
        try:
            os.remove(os.path.join(os.environ['OUTPUT_DIR'], f))
        except:
            pass
    
    print("🚀 RUNNING PIPELINE DIRECTLY (NO API)")
    print("=" * 60)
    print("📊 This will give us the TRUE execution time")
    print(f"   - Strategy: simple_production_with_gdrive_demo")
    print(f"   - Source: 1,197 Arivale proteins")
    print(f"   - Target: 266,487 KG2c entities")
    print(f"   - Output: {os.environ['OUTPUT_DIR']}")
    print("=" * 60)
    
    # Load the strategy directly
    strategy_path = '/home/ubuntu/biomapper/configs/strategies/experimental/simple_production_with_gdrive_demo.yaml'
    with open(strategy_path, 'r') as f:
        strategy_config = yaml.safe_load(f)
    
    print(f"\n📋 Strategy: {strategy_config['name']}")
    print(f"   Steps: {len(strategy_config['steps'])}")
    for i, step in enumerate(strategy_config['steps'], 1):
        print(f"   {i}. {step['name']} ({step['action']['type']})")
    
    # Initialize the service
    print("\n🔧 Initializing MinimalStrategyService...")
    strategies_dir = '/home/ubuntu/biomapper/configs/strategies'
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Track execution time for each step
    step_times = []
    overall_start = time.time()
    
    print("\n🔄 Starting execution...\n")
    print("-" * 60)
    
    try:
        # Execute the strategy
        result = await service.execute_strategy(
            strategy_name='simple_production_with_gdrive_demo',
            source_endpoint_name='',
            target_endpoint_name='',
            input_identifiers=[]
        )
        
        overall_time = time.time() - overall_start
        
        print("\n" + "=" * 60)
        print(f"✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"⏱️  Total execution time: {overall_time:.2f} seconds ({overall_time/60:.1f} minutes)")
        print("=" * 60)
        
        # Print statistics
        if hasattr(result, 'statistics') and result.statistics:
            print("\n📊 STATISTICS:")
            for action, stats in result.statistics.items():
                if isinstance(stats, dict):
                    print(f"\n  {action}:")
                    for key, value in stats.items():
                        print(f"    - {key}: {value}")
        
        # Check output files
        output_files = os.listdir(os.environ['OUTPUT_DIR'])
        if output_files:
            print(f"\n📁 OUTPUT FILES ({len(output_files)}):")
            total_size = 0
            for f in output_files:
                size = os.path.getsize(os.path.join(os.environ['OUTPUT_DIR'], f))
                total_size += size
                print(f"  - {f}: {size:,} bytes")
            print(f"\n  Total size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        
        print("\n💡 RECOMMENDED TIMEOUT SETTINGS:")
        recommended_timeout = int(overall_time * 1.5)  # Add 50% buffer
        print(f"  - Minimum timeout: {int(overall_time) + 60} seconds")
        print(f"  - Recommended timeout: {recommended_timeout} seconds ({recommended_timeout/60:.1f} minutes)")
        print(f"  - Safe timeout: {int(overall_time * 2)} seconds ({overall_time * 2/60:.1f} minutes)")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - overall_start
        print(f"\n❌ FAILED after {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Still check what was produced
        output_files = os.listdir(os.environ['OUTPUT_DIR'])
        if output_files:
            print(f"\n📂 Partial output ({len(output_files)} files):")
            for f in output_files:
                size = os.path.getsize(os.path.join(os.environ['OUTPUT_DIR'], f))
                print(f"  - {f}: {size:,} bytes")

# Add progress hook to see what's happening
class ProgressHook:
    def __init__(self):
        self.last_print = time.time()
        
    def __call__(self, message):
        now = time.time()
        if now - self.last_print > 5:  # Print every 5 seconds
            print(f"  ⏳ {datetime.now().strftime('%H:%M:%S')} - Still processing...")
            self.last_print = now

if __name__ == "__main__":
    print("Starting direct execution (no API, no timeout limits)...")
    asyncio.run(run_direct())
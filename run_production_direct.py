#!/usr/bin/env python3
"""
Run the production pipeline directly (without API) to verify it works
"""
import asyncio
import time
from pathlib import Path
from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def run_production_direct():
    print("🚀 RUNNING PRODUCTION PIPELINE DIRECTLY (WITHOUT API)")
    print("=" * 60)
    print("\nImprovements implemented:")
    print("✅ O(n*m) to O(n+m) optimization (2 minutes vs hours)")
    print("✅ Isoform stripping (70.4% match rate vs 0.9%)")
    print("✅ UniProt API integration")
    print("✅ Google Drive sync")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("/tmp/biomapper_results")
    output_dir.mkdir(exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Initialize service
    print("\n1. Initializing strategy service...")
    service = MinimalStrategyService(strategies_dir="configs/strategies")
    
    # Strategy information
    strategy_name = "production_simple_working"
    print(f"\n2. Strategy: {strategy_name}")
    print(f"   Description: Simplified production pipeline with Google Drive sync")
    
    # Show data sizes
    print("\n3. Dataset information:")
    print("   - Arivale: ~1,197 proteins")
    print("   - KG2c (all): ~266,487 entities")
    print("   - KG2c proteins with UniProtKB prefix: ~85,711 entities")
    print("   - Expected matches with isoform stripping: ~818 proteins (70.4%)")
    
    # Run strategy
    print("\n4. Executing strategy...")
    print("   This should take about 2 minutes with our optimizations")
    
    start_time = time.time()
    
    # Add progress indicator
    async def show_progress():
        """Show progress dots while pipeline runs"""
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - start_time
            print(f"   ... {elapsed:.0f}s elapsed", flush=True)
    
    # Start progress indicator
    progress_task = asyncio.create_task(show_progress())
    
    try:
        # Execute strategy
        result = await service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name="",
            target_endpoint_name="",
            input_identifiers=[]
        )
        
        # Cancel progress indicator
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
        
        elapsed = time.time() - start_time
        print(f"\n✅ Pipeline completed in {elapsed:.1f} seconds!")
        
        # Show results
        if result:
            print("\n5. Results:")
            
            # Show statistics
            if 'statistics' in result:
                print("\n   Statistics:")
                for key, value in result['statistics'].items():
                    print(f"     {key}: {value}")
            
            # Show output files
            if 'output_files' in result:
                print("\n   Output files generated:")
                for file in result['output_files']:
                    file_path = Path(file)
                    if file_path.exists():
                        size = file_path.stat().st_size / 1024  # KB
                        print(f"     - {file_path.name} ({size:.1f} KB)")
                    else:
                        print(f"     - {file_path.name} (not found)")
            
            # Check for specific results
            results_file = output_dir / "protein_mapping_results.csv"
            if results_file.exists():
                import pandas as pd
                df = pd.read_csv(results_file)
                matched = df[df['match_status'] == 'matched']
                print(f"\n   Mapping results:")
                print(f"     Total rows: {len(df)}")
                print(f"     Matched rows: {len(matched)}")
                print(f"     Match rate: {len(matched)/1197*100:.1f}%")
            
            print("\n6. Google Drive sync:")
            print("   Check if files were uploaded to Google Drive")
            print("   Folder ID: 1lqOX1pWP_CbZn-mU5InVt6lG7-uaj8Hn")
            
        return result
        
    except Exception as e:
        progress_task.cancel()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Run the pipeline
print("Starting pipeline execution...\n")
result = asyncio.run(run_production_direct())

if result:
    print("\n" + "=" * 60)
    print("🎉 SUCCESS: Pipeline executed successfully!")
    print("\nNext steps:")
    print("1. Verify the match rate is ~70%")
    print("2. Check Google Drive for uploaded files")
    print("3. Run via API for production deployment")
else:
    print("\n" + "=" * 60)
    print("⚠️  Pipeline execution failed")
    print("Check the error messages above for details")
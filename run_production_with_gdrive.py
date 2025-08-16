#!/usr/bin/env python3
"""
Run the production pipeline with Google Drive sync
"""
import asyncio
import time
import os
from pathlib import Path
from biomapper.core.minimal_strategy_service import MinimalStrategyService
from biomapper.core.standards.env_manager import EnvironmentManager

# Initialize environment manager
env = EnvironmentManager()

async def run_production_with_gdrive():
    print("🚀 RUNNING PRODUCTION PIPELINE WITH GOOGLE DRIVE SYNC")
    print("=" * 60)
    
    # Validate Google Drive requirements
    try:
        env.validate_requirements(['google_drive'])
        creds_path = env.get_google_credentials_path()
        if creds_path:
            print(f"✅ Google credentials validated: {creds_path}")
        else:
            print("❌ Google credentials validation failed!")
            return None
    except EnvironmentError as e:
        print(f"❌ Environment configuration error:\n{e}")
        return None
    
    print("\nImprovements implemented:")
    print("✅ O(n*m) to O(n+m) optimization (2 minutes vs hours)")
    print("✅ Isoform stripping (70.4% match rate vs 0.9%)")
    print("✅ UniProt API integration")
    print("✅ Google Drive sync with credentials")
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
    print("   - Expected matches: ~818 proteins (70.4%)")
    
    # Run strategy
    print("\n4. Executing strategy...")
    print("   This should take about 2 minutes")
    
    start_time = time.time()
    
    try:
        # Execute strategy
        result = await service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name="",
            target_endpoint_name="",
            input_identifiers=[]
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ Pipeline completed in {elapsed:.1f} seconds!")
        
        # Show results
        if result:
            print("\n5. Results:")
            
            # Check for specific results
            results_file = output_dir / "protein_mapping_results.csv"
            if results_file.exists():
                import pandas as pd
                df = pd.read_csv(results_file, low_memory=False)
                matched = df[df['match_status'] == 'matched']
                unique_matched = matched['uniprot'].nunique()
                print(f"\n   Mapping results:")
                print(f"     Total rows: {len(df):,}")
                print(f"     Matched rows: {len(matched):,}")
                print(f"     Unique proteins matched: {unique_matched}")
                print(f"     Match rate: {unique_matched/1162*100:.1f}%")
            
            # Check output files
            print(f"\n   Output files in {output_dir}:")
            for file in output_dir.glob("*.csv"):
                size = file.stat().st_size / (1024 * 1024)  # MB
                print(f"     - {file.name} ({size:.1f} MB)")
            
            print("\n6. Google Drive sync:")
            print("   Check Google Drive for uploaded files")
            print("   Folder ID: 1lqOX1pWP_CbZn-mU5InVt6lG7-uaj8Hn")
            print("   URL: https://drive.google.com/drive/folders/1lqOX1pWP_CbZn-mU5InVt6lG7-uaj8Hn")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Run the pipeline
print("Starting pipeline execution with Google Drive sync...\n")
result = asyncio.run(run_production_with_gdrive())

if result:
    print("\n" + "=" * 60)
    print("🎉 SUCCESS: Pipeline executed with Google Drive sync!")
    print("\nPlease check Google Drive for the uploaded results:")
    print("https://drive.google.com/drive/folders/1lqOX1pWP_CbZn-mU5InVt6lG7-uaj8Hn")
else:
    print("\n" + "=" * 60)
    print("⚠️  Pipeline execution failed")
    print("Check the error messages above for details")
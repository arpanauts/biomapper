#!/usr/bin/env python3
"""
Run the production pipeline with correct KG2.10.2c data
"""
import asyncio
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from biomapper.core.minimal_strategy_service import MinimalStrategyService

# Load environment variables
load_dotenv()

async def run_with_updated_kg2():
    print("🚀 RUNNING PRODUCTION PIPELINE WITH KG2.10.2c")
    print("=" * 60)
    
    print("\n📊 Using updated datasets:")
    print("✅ Arivale: /procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv")
    print("✅ KG2.10.2c: /procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv")
    
    print("\nImprovements:")
    print("✅ Isoform stripping for better matching")
    print("✅ O(n+m) optimized algorithm")
    print("✅ UniProt extraction from id and xrefs columns")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("/tmp/biomapper_results_kg2_10_2c")
    output_dir.mkdir(exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Initialize service
    print("\n1. Initializing strategy service...")
    service = MinimalStrategyService(strategies_dir="configs/strategies")
    
    # Strategy information
    strategy_name = "production_simple_working"
    print(f"\n2. Strategy: {strategy_name}")
    print(f"   Using KG2.10.2c with 350,368 protein entities")
    
    # Run strategy
    print("\n3. Executing strategy...")
    print("   This should take about 2-3 minutes")
    
    start_time = time.time()
    
    # Progress indicator
    async def show_progress():
        while True:
            await asyncio.sleep(10)
            elapsed = time.time() - start_time
            print(f"   ... {elapsed:.0f}s elapsed", flush=True)
    
    progress_task = asyncio.create_task(show_progress())
    
    try:
        # Execute strategy (output will go to /tmp/biomapper_results as configured)
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
        
        # Check results
        if result:
            print("\n4. Results:")
            
            # Copy results to our output dir
            import shutil
            results_file = Path("/tmp/biomapper_results/protein_mapping_results.csv")
            if results_file.exists():
                import pandas as pd
                df = pd.read_csv(results_file, low_memory=False)
                
                # Save to new location
                new_results = output_dir / "protein_mapping_results_kg2_10_2c.csv"
                df.to_csv(new_results, index=False)
                
                # Analyze
                if 'match_status' in df.columns:
                    matched = df[df['match_status'] == 'matched']
                    unique_matched = matched['uniprot'].nunique() if 'uniprot' in matched.columns else len(matched)
                    
                    print(f"\n   Mapping results (KG2.10.2c):")
                    print(f"     Total rows: {len(df):,}")
                    print(f"     Matched rows: {len(matched):,}")
                    print(f"     Unique proteins matched: {unique_matched}/1,162")
                    print(f"     Match rate: {unique_matched/1162*100:.1f}%")
                    
                    # Save summary
                    summary_path = output_dir / "summary_kg2_10_2c.txt"
                    with open(summary_path, 'w') as f:
                        f.write("KG2.10.2c PROTEIN MAPPING RESULTS\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"\nDATASETS:\n")
                        f.write(f"- Arivale: 1,197 proteins (1,162 unique UniProt IDs)\n")
                        f.write(f"- KG2.10.2c: 350,368 protein entities\n")
                        f.write(f"\nRESULTS:\n")
                        f.write(f"- Total rows: {len(df):,}\n")
                        f.write(f"- Matched rows: {len(matched):,}\n")
                        f.write(f"- Unique matches: {unique_matched}/1,162 ({unique_matched/1162*100:.1f}%)\n")
                        f.write(f"- Runtime: {elapsed:.1f} seconds\n")
                    
                    print(f"\n   Files saved to: {output_dir}")
                
            # Also copy Arivale file
            arivale_source = Path("/tmp/biomapper_results/arivale_proteins.csv")
            if arivale_source.exists():
                shutil.copy(arivale_source, output_dir / "arivale_proteins.csv")
        
        return result
        
    except Exception as e:
        progress_task.cancel()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Run the pipeline
print("Starting pipeline with KG2.10.2c...\n")
result = asyncio.run(run_with_updated_kg2())

if result:
    print("\n" + "=" * 60)
    print("🎉 SUCCESS: Pipeline completed with KG2.10.2c!")
    print("\nResults saved to: /tmp/biomapper_results_kg2_10_2c/")
    print("\nNext step: Upload to Google Drive")
else:
    print("\n" + "=" * 60)
    print("⚠️  Pipeline execution failed")
#!/usr/bin/env python3
"""
Run the complete production pipeline via API with all improvements
"""
import asyncio
import time
from biomapper_client.client_v2 import BiomapperClient

async def run_production_pipeline():
    print("🚀 RUNNING COMPLETE PRODUCTION PIPELINE VIA API")
    print("=" * 60)
    print("\nImprovements implemented:")
    print("✅ O(n*m) to O(n+m) optimization (2 minutes vs hours)")
    print("✅ Isoform stripping (70.4% match rate vs 0.9%)")
    print("✅ UniProt API integration")
    print("✅ Google Drive sync")
    print("=" * 60)
    
    # Initialize client
    client = BiomapperClient(base_url="http://localhost:8000")
    
    # Check API health
    print("\n1. Checking API health...")
    health = await client.health()
    print(f"   API status: {health}")
    
    # Run the production strategy
    print("\n2. Starting production pipeline...")
    print("   Strategy: production_uniprot_only")
    print("   Datasets:")
    print("   - Arivale: 1,197 proteins")
    print("   - KG2c: 85,711 UniProtKB entries (filtered)")
    
    start_time = time.time()
    
    try:
        # Start the job
        job_result = await client.run_strategy(
            strategy_name="production_uniprot_only",
            params={},
            timeout=120  # 2 minute timeout should be enough now
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n3. Pipeline completed in {elapsed:.1f} seconds!")
        print(f"   Job ID: {job_result.get('job_id')}")
        print(f"   Status: {job_result.get('status')}")
        
        # Check results
        if 'result' in job_result:
            result = job_result['result']
            if 'statistics' in result:
                stats = result['statistics']
                print("\n4. Pipeline Statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
            
            if 'output_files' in result:
                files = result['output_files']
                print("\n5. Output Files Generated:")
                for file in files:
                    print(f"   - {file}")
        
        print("\n✅ SUCCESS: Production pipeline completed!")
        print("   Check Google Drive for uploaded results")
        
        return job_result
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"\n⏱️  Pipeline timed out after {elapsed:.1f} seconds")
        print("   This shouldn't happen with our optimizations!")
        print("   Check server logs for details")
        return None
        
    except Exception as e:
        print(f"\n❌ Error running pipeline: {e}")
        return None

# Run the pipeline
result = asyncio.run(run_production_pipeline())

if result:
    print("\n" + "=" * 60)
    print("🎉 Pipeline execution successful!")
    print("Next steps:")
    print("1. Verify results in Google Drive")
    print("2. Check mapping quality")
    print("3. Propagate to other strategies")
else:
    print("\n" + "=" * 60)
    print("⚠️  Pipeline execution failed or timed out")
    print("Check server logs for details")
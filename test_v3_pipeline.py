#!/usr/bin/env python3
"""
Test script for running the prot_arv_to_kg2c_uniprot_v3.0_progressive pipeline.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from biomapper_client.client_v2 import BiomapperClient
from biomapper_client.models import JobConfig


async def test_pipeline():
    """Test the v3.0 progressive pipeline."""
    
    print("=" * 60)
    print("Testing prot_arv_to_kg2c_uniprot_v3.0_progressive pipeline")
    print("=" * 60)
    
    # Initialize client
    client = BiomapperClient()
    
    # Check if API is running
    try:
        health = await client.get_health()
        print(f"✓ API Health: {health}")
    except Exception as e:
        print(f"✗ API not running: {e}")
        print("Starting API server...")
        # Could start server here if needed
        return
    
    # Run the pipeline
    strategy_name = "prot_arv_to_kg2c_uniprot_v3.0_progressive"
    
    print(f"\nRunning strategy: {strategy_name}")
    print("-" * 40)
    
    try:
        # Start the job
        job_id = await client.run_strategy(
            strategy_name=strategy_name,
            wait=False  # Don't wait for completion
        )
        
        print(f"✓ Job started: {job_id}")
        
        # Monitor progress
        print("\nMonitoring progress...")
        prev_progress = -1
        
        while True:
            job_info = await client.get_job(job_id)
            
            # Print progress updates
            if job_info.progress != prev_progress:
                print(f"  Progress: {job_info.progress}% - {job_info.status}")
                if job_info.current_step:
                    print(f"    Current step: {job_info.current_step}")
                prev_progress = job_info.progress
            
            # Check if completed
            if job_info.status in ["completed", "failed", "error"]:
                break
            
            await asyncio.sleep(2)
        
        # Final status
        print("\n" + "=" * 40)
        if job_info.status == "completed":
            print(f"✓ Pipeline completed successfully!")
            print(f"  Execution time: {job_info.execution_time:.2f}s")
            
            # Show results summary
            if job_info.result:
                print("\nResults summary:")
                if "statistics" in job_info.result:
                    stats = job_info.result["statistics"]
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                
                if "output_files" in job_info.result:
                    print("\nOutput files:")
                    for file in job_info.result["output_files"]:
                        print(f"  - {file}")
        else:
            print(f"✗ Pipeline failed: {job_info.status}")
            if job_info.error:
                print(f"  Error: {job_info.error}")
        
    except Exception as e:
        print(f"✗ Error running pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return job_info.status == "completed"


async def main():
    """Main entry point."""
    success = await test_pipeline()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
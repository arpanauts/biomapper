#!/usr/bin/env python3
"""Debug script to check job results directly from API."""

import asyncio
import httpx
import json
from datetime import datetime

async def debug_job_results():
    """Submit a test job and check its results."""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Submit test job
        print("1. Submitting job for met_arv_to_ukbb_progressive_v4.0...")
        response = await client.post(
            f"{base_url}/api/strategies/v2/execute",
            json={
                "strategy": "met_arv_to_ukbb_progressive_v4.0",
                "parameters": {
                    "stages_to_run": [1],
                    "debug_mode": True,
                    "verbose_logging": True
                }
            }
        )
        
        if response.status_code != 200:
            print(f"Error submitting job: {response.status_code}")
            print(response.text)
            return
            
        job_data = response.json()
        job_id = job_data.get("job_id")
        print(f"Job ID: {job_id}")
        print(f"Initial status: {job_data.get('status')}")
        
        # Wait a bit for execution
        print("\n2. Waiting 5 seconds for execution...")
        await asyncio.sleep(5)
        
        # Check job status
        print("\n3. Checking job status...")
        response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"Status: {status_data.get('status')}")
            print(f"Strategy: {status_data.get('strategy_name')}")
            if status_data.get('error'):
                print(f"Error: {status_data.get('error')}")
        else:
            print(f"Error getting status: {response.status_code}")
            print(response.text)
        
        # Try to get results
        print("\n4. Attempting to get job results...")
        response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/results")
        if response.status_code == 200:
            results = response.json()
            print("Results retrieved successfully!")
            
            # Print key information
            if results:
                print(f"\nResult keys: {list(results.keys())}")
                
                # Check for datasets
                if "datasets" in results:
                    datasets = results["datasets"]
                    print(f"\nDatasets found: {list(datasets.keys())}")
                    for key, data in datasets.items():
                        if isinstance(data, list):
                            print(f"  {key}: {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"  {key}: dict with keys {list(data.keys())[:5]}...")
                
                # Check for statistics
                if "statistics" in results:
                    print(f"\nStatistics: {results['statistics']}")
                
                # Check for output files
                if "output_files" in results:
                    print(f"\nOutput files: {results['output_files']}")
                
                # Check for current identifiers
                if "current_identifiers" in results:
                    ids = results["current_identifiers"]
                    print(f"\nCurrent identifiers: {len(ids) if isinstance(ids, list) else 'not a list'}")
                    
        else:
            print(f"Error getting results: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(debug_job_results())
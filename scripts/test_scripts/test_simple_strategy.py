#!/usr/bin/env python3
"""Test a simple strategy execution to verify the framework works."""

import asyncio
import httpx
import json

async def test_simple_load():
    """Test just loading a dataset."""
    
    base_url = "http://localhost:8000"
    
    # Create a minimal inline strategy
    strategy = {
        "name": "test_simple_load",
        "description": "Test loading data",
        "parameters": {
            "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv"
        },
        "steps": [
            {
                "name": "load_data",
                "action": {
                    "type": "LOAD_DATASET_IDENTIFIERS",
                    "params": {
                        "file_path": "${parameters.file_path}",
                        "identifier_column": "name",
                        "output_key": "loaded_data"
                    }
                }
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("1. Submitting simple load strategy...")
        response = await client.post(
            f"{base_url}/api/strategies/v2/execute",
            json={
                "strategy": strategy,
                "parameters": {}
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
        
        # Wait for execution
        print("\n2. Waiting for execution...")
        await asyncio.sleep(3)
        
        # Check status
        print("\n3. Checking job status...")
        response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"Status: {status_data.get('status')}")
            if status_data.get('error'):
                print(f"Error: {status_data.get('error')}")
        
        # Get results if completed
        if status_data.get('status') == 'completed':
            print("\n4. Getting results...")
            response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/results")
            if response.status_code == 200:
                results = response.json()
                print("✅ SUCCESS! Strategy executed.")
                
                # Check what was loaded
                if "datasets" in results and "loaded_data" in results["datasets"]:
                    data = results["datasets"]["loaded_data"]
                    if isinstance(data, list):
                        print(f"Loaded {len(data)} items")
                    elif isinstance(data, dict) and "_row_count" in data:
                        print(f"Loaded {data['_row_count']} rows")
                else:
                    print("Warning: No loaded_data in results")
                    print(f"Available keys: {list(results.get('datasets', {}).keys())}")

if __name__ == "__main__":
    asyncio.run(test_simple_load())
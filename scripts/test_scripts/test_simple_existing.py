#!/usr/bin/env python3
"""Test execution with the simplest existing strategy."""

import asyncio
import httpx

async def test_existing():
    """Test with prot_arv_to_kg2c_uniprot_v3.0 which we know is loaded."""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("1. Submitting prot_arv_to_kg2c_uniprot_v3.0...")
        
        # Use minimal parameters - just test if it starts
        response = await client.post(
            f"{base_url}/api/strategies/v2/execute",
            json={
                "strategy": "prot_arv_to_kg2c_uniprot_v3.0",
                "parameters": {
                    "test_mode": True,
                    "limit_rows": 10
                }
            }
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return
            
        job_data = response.json()
        job_id = job_data.get("job_id")
        print(f"Job ID: {job_id}")
        
        # Wait
        await asyncio.sleep(5)
        
        # Check status
        response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"\nFinal status: {status.get('status')}")
            if status.get('error'):
                print(f"Error: {status.get('error')[:200]}...")
                
        # If completed, try to get results
        if status.get('status') == 'completed':
            response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/results")
            if response.status_code == 200:
                results = response.json()
                print("\n✅ SUCCESS! Execution completed.")
                print(f"Result keys: {list(results.keys())[:10]}")
                
                if 'datasets' in results:
                    print(f"Datasets: {list(results['datasets'].keys())[:5]}")
                if 'statistics' in results:
                    print(f"Statistics: {results['statistics']}")

if __name__ == "__main__":
    asyncio.run(test_existing())
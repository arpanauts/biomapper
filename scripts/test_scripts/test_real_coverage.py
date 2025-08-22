#!/usr/bin/env python3
"""Test real coverage with simple YAML strategies."""

import asyncio
import httpx
import json
from pathlib import Path

async def test_stage1():
    """Test Stage 1 only."""
    
    base_url = "http://localhost:8001"
    
    # Read the test YAML
    with open("test_stage1_only.yaml") as f:
        import yaml
        strategy = yaml.safe_load(f)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("="*60)
        print("TESTING STAGE 1 ONLY - REAL METRICS")
        print("="*60)
        
        response = await client.post(
            f"{base_url}/api/strategies/v2/execute",
            json={
                "strategy": strategy,
                "parameters": {}
            }
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return
            
        job_data = response.json()
        job_id = job_data.get("job_id")
        print(f"Job ID: {job_id}")
        
        # Wait for completion
        print("Waiting for execution...")
        await asyncio.sleep(5)
        
        # Check status
        response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"Status: {status.get('status')}")
            
            if status.get('status') == 'completed':
                # Get results
                response = await client.get(f"{base_url}/api/strategies/v2/jobs/{job_id}/results")
                if response.status_code == 200:
                    results = response.json()
                    
                    print("\n" + "="*60)
                    print("STAGE 1 REAL COVERAGE RESULTS")
                    print("="*60)
                    
                    if "datasets" in results:
                        datasets = results["datasets"]
                        
                        # Count originals
                        arivale_count = 0
                        if "arivale_data" in datasets:
                            arivale_data = datasets["arivale_data"]
                            if isinstance(arivale_data, list):
                                arivale_count = len(arivale_data)
                            elif isinstance(arivale_data, dict) and "_row_count" in arivale_data:
                                arivale_count = arivale_data["_row_count"]
                        
                        ref_count = 0
                        if "reference_data" in datasets:
                            ref_data = datasets["reference_data"]
                            if isinstance(ref_data, list):
                                ref_count = len(ref_data)
                            elif isinstance(ref_data, dict) and "_row_count" in ref_data:
                                ref_count = ref_data["_row_count"]
                        
                        # Count matched
                        matched_count = 0
                        if "stage_1_matched" in datasets:
                            matched_data = datasets["stage_1_matched"]
                            if isinstance(matched_data, list):
                                matched_count = len(matched_data)
                            elif isinstance(matched_data, dict) and "_row_count" in matched_data:
                                matched_count = matched_data["_row_count"]
                        
                        print(f"Arivale metabolites loaded: {arivale_count}")
                        print(f"UKBB reference loaded: {ref_count}")
                        print(f"Stage 1 matched: {matched_count}")
                        
                        if ref_count > 0:
                            coverage = (matched_count / ref_count) * 100
                            print(f"\n📊 ACTUAL STAGE 1 COVERAGE: {coverage:.1f}%")
                            print(f"   ({matched_count} out of {ref_count} reference metabolites)")
                        
                        print("\n" + "="*60)
                        print("COMPARISON TO CLAIMS:")
                        print("-"*60)
                        print(f"Claimed Stage 1: 57.9%")
                        print(f"Actual Stage 1:  {coverage:.1f}%" if ref_count > 0 else "Could not calculate")
                        
                        if coverage < 20:
                            print("\n⚠️ ACTUAL COVERAGE IS ~3X LOWER THAN CLAIMED!")
                    
                    # Check output file
                    output_file = Path("/tmp/biomapper/stage1_test/stage1_matched.tsv")
                    if output_file.exists():
                        print(f"\n✅ Output file created: {output_file}")
                        # Count lines
                        with open(output_file) as f:
                            lines = len(f.readlines()) - 1  # Subtract header
                        print(f"   Contains {lines} matched metabolites")
            else:
                print(f"Error: {status.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_stage1())
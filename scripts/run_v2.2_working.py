#!/usr/bin/env python3
"""Run the working v2.2 strategy with existing actions."""

import json
import time
import requests
from pathlib import Path

print("=" * 80)
print("RUNNING V2.2 WORKING STRATEGY WITH PRODUCTION DATA")
print("=" * 80)

# Submit job
response = requests.post(
    "http://localhost:8000/api/strategies/v2/execute",
    json={
        "strategy": "prot_arv_to_kg2c_uniprot_v2.2_working",
        "parameters": {},  # Use YAML defaults
        "options": {"timeout_seconds": 300}
    }
)

if response.status_code == 200:
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"✅ Job submitted: {job_id}")
    
    # Monitor progress
    print("\nMonitoring progress...")
    start_time = time.time()
    
    for i in range(150):  # 5 minutes max
        time.sleep(2)
        
        status_response = requests.get(
            f"http://localhost:8000/api/strategies/v2/jobs/{job_id}/status"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed}s] Status: {status}")
            
            if status == "completed":
                print(f"\n✅ SUCCESS! Completed in {elapsed} seconds")
                
                # Check outputs
                output_dir = Path("/tmp/biomapper/protein_mapping_v2.2_working")
                if output_dir.exists():
                    print("\n📁 Output files:")
                    for f in output_dir.glob("*.tsv"):
                        lines = sum(1 for _ in open(f)) - 1
                        print(f"  - {f.name}: {lines:,} rows")
                        
                    # Load and show statistics
                    direct_matches = output_dir / "direct_matches.tsv"
                    unmapped = output_dir / "unmapped_proteins.tsv"
                    
                    if direct_matches.exists() and unmapped.exists():
                        direct_count = sum(1 for _ in open(direct_matches)) - 1
                        unmapped_count = sum(1 for _ in open(unmapped)) - 1
                        total = direct_count + unmapped_count
                        
                        print(f"\n📊 Mapping Statistics:")
                        print(f"  Total Arivale proteins: {total:,}")
                        print(f"  Direct matches: {direct_count:,} ({(direct_count/total)*100:.1f}%)")
                        print(f"  Unmapped: {unmapped_count:,} ({(unmapped_count/total)*100:.1f}%)")
                        
                break
                
            elif status in ["failed", "error"]:
                print(f"\n❌ Job failed: {status}")
                print(f"Error: {status_data.get('error', 'Unknown')}")
                break
else:
    print(f"❌ Failed to submit: {response.status_code}")
    print(response.text)
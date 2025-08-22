#!/usr/bin/env python3
"""
Simple test of the fixed progressive pipeline using the API client.
"""

import requests
import time
import json
import pandas as pd
from pathlib import Path
import os

# Set output directory
output_dir = Path("/tmp/biomapper/protein_mapping_v3.0_progressive_fixed")
output_dir.mkdir(parents=True, exist_ok=True)
os.environ["OUTPUT_DIR"] = str(output_dir)

# API base URL
BASE_URL = "http://localhost:8000"

print("Starting fixed progressive mapping pipeline via API...")

# Start the job
response = requests.post(
    f"{BASE_URL}/api/strategies/v2/execute",
    json={
        "strategy": "prot_arv_to_kg2c_uniprot_v3.0_progressive_fixed",
        "parameters": {},
        "options": {}
    }
)

if response.status_code != 200:
    print(f"Error starting job: {response.status_code}")
    print(response.text)
    exit(1)

job_data = response.json()
job_id = job_data["job_id"]
print(f"Job started: {job_id}")

# Poll for completion
while True:
    status_response = requests.get(f"{BASE_URL}/api/strategies/v2/jobs/{job_id}/status")
    if status_response.status_code != 200:
        print(f"Error checking status: {status_response.status_code}")
        break
    
    status_data = status_response.json()
    status = status_data["status"]
    
    if status == "completed":
        print("Job completed successfully!")
        break
    elif status == "failed":
        print(f"Job failed: {status_data.get('error', 'Unknown error')}")
        exit(1)
    else:
        print(f"Job status: {status}...")
        time.sleep(5)

# Check for output files
output_file = output_dir / "progressive_mappings_fixed.tsv"
if output_file.exists():
    # Load and analyze results
    df = pd.read_csv(output_file, sep='\t')
    
    # Calculate statistics
    total = len(df)
    unique_proteins = df['uniprot'].nunique() if 'uniprot' in df.columns else 0
    
    if 'mapping_stage' in df.columns:
        stage_1 = len(df[df['mapping_stage'] == 1])
        stage_2 = len(df[df['mapping_stage'] == 2])  
        stage_3 = len(df[df['mapping_stage'] == 3])
        unmapped = len(df[df['mapping_stage'] == 99])
    else:
        stage_1 = stage_2 = stage_3 = unmapped = 0
    
    print("\n=== FIXED PROGRESSIVE MAPPING RESULTS ===")
    print(f"Total records: {total}")
    print(f"Unique proteins: {unique_proteins}")
    print(f"Stage 1 (Direct): {stage_1} matches")
    print(f"Stage 2 (Composite): {stage_2} matches")
    print(f"Stage 3 (Historical): {stage_3} matches")
    print(f"Unmapped: {unmapped}")
    
    if unique_proteins > 0:
        coverage = 100 * (unique_proteins - unmapped) / unique_proteins
        print(f"Coverage: {coverage:.2f}%")
    
    # Check for proteins with multiple match types (should be ZERO)
    if 'uniprot' in df.columns and 'match_type' in df.columns:
        duplicates = df.groupby('uniprot')['match_type'].nunique()
        multi_match = duplicates[duplicates > 1]
        
        if len(multi_match) > 0:
            print(f"\n⚠️ WARNING: {len(multi_match)} proteins have multiple match types!")
            print(f"Examples: {multi_match.head().index.tolist()}")
        else:
            print("\n✅ SUCCESS: No proteins with duplicate match types!")
            print("The pipeline is now implementing TRUE progressive logic!")
else:
    print(f"Output file not found: {output_file}")
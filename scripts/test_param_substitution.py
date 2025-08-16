#!/usr/bin/env python3
"""Test parameter substitution in strategies."""

import json
import time
import requests
from pathlib import Path

# Create test files
test_dir = Path("/tmp/param_test")
test_dir.mkdir(exist_ok=True)

source = test_dir / "source.txt"
source.write_text("uniprot_id\tname\nP12345\tTest Protein\n")

target = test_dir / "target.txt"
target.write_text("id\tname\nP12345\tTarget Protein\n")

# Test with API
response = requests.post(
    "http://localhost:8000/api/strategies/v2/execute",
    json={
        "strategy": "test_simple_v2.2",
        "parameters": {
            "source_file": str(source),
            "target_file": str(target),
            "output_dir": str(test_dir / "output")
        }
    }
)

if response.status_code == 200:
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Job submitted: {job_id}")
    
    # Wait and check
    time.sleep(3)
    status_response = requests.get(
        f"http://localhost:8000/api/strategies/v2/jobs/{job_id}/status"
    )
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"Status: {status_data.get('status')}")
        print(f"Error: {status_data.get('error', 'None')}")
        
        # Check if output was created
        output_file = test_dir / "output" / "test_export.tsv"
        if output_file.exists():
            print(f"✅ Output file created: {output_file}")
            print(f"Content: {output_file.read_text()[:100]}")
        else:
            print(f"❌ Output file not created")
else:
    print(f"Failed to submit: {response.status_code}")
    print(response.text)
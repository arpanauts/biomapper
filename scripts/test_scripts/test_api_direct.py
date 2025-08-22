#!/usr/bin/env python3
"""Test the API directly to get full error details."""

import httpx
import json
import time

# Start the job
print("Starting job...")
response = httpx.post(
    "http://localhost:8001/api/strategies/v2/jobs/",
    json={
        "strategy_name": "met_arv_to_ukbb_progressive_v4.0",
        "parameters": {
            "stages_to_run": [1],
            "debug_mode": True,
            "verbose_logging": True,
            "output_dir": "/tmp/biomapper/api_test"
        }
    }
)

if response.status_code != 200:
    print(f"Failed to start job: {response.text}")
    exit(1)

job_data = response.json()
job_id = job_data["job_id"]
print(f"Job ID: {job_id}")

# Wait for completion
print("Waiting for completion...")
for i in range(30):
    time.sleep(2)
    status_response = httpx.get(f"http://localhost:8001/api/strategies/v2/jobs/{job_id}/status")
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"  Status: {status['status']}")
        if status["status"] in ["completed", "failed"]:
            break

# Get results
print("\nGetting results...")
results_response = httpx.get(f"http://localhost:8001/api/strategies/v2/jobs/{job_id}/results")
if results_response.status_code == 200:
    results = results_response.json()
    print(f"Success: {results.get('success', False)}")
    if "error" in results:
        print(f"Error: {results['error']}")
    if "traceback" in results:
        print("Traceback:")
        print(results["traceback"])
    if "result_data" in results:
        data = results["result_data"]
        if "datasets" in data:
            print(f"Datasets: {list(data['datasets'].keys())}")
else:
    print(f"Failed to get results: {results_response.text}")
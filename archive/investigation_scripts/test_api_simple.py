#!/usr/bin/env python3
"""
Simple API test to verify integration testing setup.
"""

import requests
import time
import sys

# Add the project root to Python path
sys.path.insert(0, "/home/ubuntu/biomapper")
sys.path.insert(0, "/home/ubuntu/biomapper/tests/integration")

from tests.integration.test_data_generators import generate_realistic_test_data


def test_api_connection():
    """Test basic API connectivity."""
    response = requests.get("http://localhost:8000/api/health/")
    print(f"API Health: {response.json()}")
    return response.status_code == 200


def test_strategy_execution():
    """Test basic strategy execution."""
    # Generate small test dataset
    test_data = generate_realistic_test_data("metabolite", 100)

    # Create test files for the strategy (needs proper column names)
    import pandas as pd

    # Create Israeli10K style data
    israeli_data = pd.DataFrame(
        {
            "BIOCHEMICAL_NAME": [f"metabolite_{i}" for i in range(50)],
            "HMDB_ID": [f"HMDB{i:07d}" for i in range(1, 51)],
            "PUBCHEM_ID": [f"{i+1000}" for i in range(50)],
            "MW": [100 + i * 2 for i in range(50)],
        }
    )
    israeli_data.to_csv("/tmp/test_metabolite_data.tsv", sep="\t", index=False)

    # Create UKBB style data
    ukbb_data = pd.DataFrame(
        {
            "Description": [f"biomarker_{i}" for i in range(50)],
            "Biomarker": [f"BM_{i:03d}" for i in range(50)],
            "Field.ID": [f"{i+20000}" for i in range(50)],
            "Units": ["mmol/L"] * 50,
        }
    )
    ukbb_data.to_csv("/tmp/test_metabolite_data2.tsv", sep="\t", index=False)

    # Try a simple strategy
    response = requests.post(
        "http://localhost:8000/api/strategies/v2/execute",
        json={
            "strategy": "SIMPLE_DATA_LOADER_DEMO",
            "parameters": {
                "israeli10k_file": "/tmp/test_metabolite_data.tsv",
                "ukbb_file": "/tmp/test_metabolite_data2.tsv",
                "output_dir": "/tmp/test_results",
            },
        },
    )

    print(f"Strategy execution response: {response.status_code}")
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"Job ID: {job_id}")

        # Poll for completion
        for i in range(30):  # 1 minute timeout
            status_response = requests.get(
                f"http://localhost:8000/api/strategies/v2/jobs/{job_id}/status"
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Job status (attempt {i+1}): {status_data['status']}")

                if status_data["status"] == "completed":
                    # Get results
                    results_response = requests.get(
                        f"http://localhost:8000/api/strategies/v2/jobs/{job_id}/results"
                    )

                    if results_response.status_code == 200:
                        results = results_response.json()
                        print(f"Success! Got results with keys: {list(results.keys())}")
                        return True
                    else:
                        print(f"Failed to get results: {results_response.text}")
                        return False

                elif status_data["status"] == "failed":
                    error = status_data.get("error", "Unknown error")
                    print(f"Strategy failed: {error}")
                    return False

            time.sleep(2)

        print("Timeout waiting for job completion")
        return False
    else:
        print(f"Failed to start strategy: {response.text}")
        return False


if __name__ == "__main__":
    print("Testing API integration setup...")

    if test_api_connection():
        print("✓ API connection successful")

        if test_strategy_execution():
            print("✓ Strategy execution successful")
            print("Integration testing setup is working!")
        else:
            print("✗ Strategy execution failed")
    else:
        print("✗ API connection failed")

#!/usr/bin/env python3
"""Direct test of Stage 1 execution through the API."""

from src.client.client_v2 import BiomapperClient
import asyncio

def test_stage1_only():
    """Test just Stage 1 execution."""
    
    client = BiomapperClient(base_url="http://localhost:8001", timeout=120)
    
    print("Testing Stage 1 ONLY")
    print("-" * 40)
    
    # Run only Stage 1
    result = client.run(
        "met_arv_to_ukbb_progressive_v4.0",
        parameters={
            "stages_to_run": [1],
            "debug_mode": True,
            "verbose_logging": True,
            "output_dir": "/tmp/biomapper/stage1_test"
        }
    )
    
    print(f"Success: {result.success}")
    if not result.success:
        print(f"Error: {result.error}")
        if result.details:
            print(f"Details: {result.details}")
    else:
        print(f"Result data keys: {result.result_data.keys() if result.result_data else 'None'}")
        if result.result_data and "datasets" in result.result_data:
            datasets = result.result_data["datasets"]
            print(f"Datasets: {list(datasets.keys())}")
            
            # Check Stage 1 results
            if "stage_1_matched" in datasets or "stage_1_matched_debug" in datasets:
                key = "stage_1_matched_debug" if "stage_1_matched_debug" in datasets else "stage_1_matched"
                matched = datasets[key]
                if isinstance(matched, dict) and "_row_count" in matched:
                    print(f"Stage 1 matched: {matched['_row_count']} metabolites")
                elif isinstance(matched, list):
                    print(f"Stage 1 matched: {len(matched)} metabolites")
    
    return result

if __name__ == "__main__":
    result = test_stage1_only()
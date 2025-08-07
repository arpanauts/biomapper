#!/usr/bin/env python3
"""
Simple test of the MVP strategy with a smaller dataset to validate functionality.
"""

import json
import os
import pytest
import requests

# Skip in CI environments where API server isn't running
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Requires API server running at localhost:8000",
)


def test_mvp_strategy():
    """Test the MVP strategy with a simple request."""

    # Test with just a few identifiers
    strategy_name = "UKBB_HPA_PROTEIN_MAPPING"
    json_payload = {
        "source_endpoint_name": "UKBB_PROTEIN_ASSAY_ID",
        "target_endpoint_name": "HPA_GENE_NAME",
        "input_identifiers": ["P00519"],  # Just one identifier
        "options": {},
    }

    print(f"🧪 Testing MVP strategy: {strategy_name}")
    print(f"📊 Input identifiers: {json_payload['input_identifiers']}")

    try:
        # Send request with longer timeout
        response = requests.post(
            f"http://localhost:8000/api/strategies/{strategy_name}/execute",
            json=json_payload,
            timeout=300,  # 5 minutes timeout
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Strategy execution completed!")
            print(f"📊 Result keys: {list(result.keys())}")

            # Pretty print the result
            print("📈 Results:")
            print(json.dumps(result, indent=2))

            # Check if we have step results
            if "step_results" in result:
                print(f"\n📋 Strategy executed {len(result['step_results'])} steps:")
                for i, step in enumerate(result["step_results"], 1):
                    status = step.get("status", "unknown")
                    action_type = step.get("action_type", "unknown")
                    input_count = step.get("input_count", 0)
                    output_count = step.get("output_count", 0)
                    duration = step.get("duration_seconds", 0)

                    print(
                        f"  {i}. {step.get('step_id', 'unknown')} ({action_type}) - {status}"
                    )
                    print(
                        f"     Input: {input_count} → Output: {output_count} [{duration:.3f}s]"
                    )

                    # Show details for any failed steps
                    if status != "success" and "details" in step:
                        details = step["details"]
                        if "error" in details:
                            print(f"     Error: {details['error']}")

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out - merge operation may still be running")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the API running?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    test_mvp_strategy()

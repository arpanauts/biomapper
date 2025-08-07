#!/usr/bin/env python
"""
Test script to execute our MVP strategy via the API.
"""
import asyncio
import json
import os
import pytest
from biomapper_client import BiomapperClient, ApiError, NetworkError

# Skip in CI environments where API server isn't running
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Requires API server running at localhost:8000",
)


async def main():
    """Test our MVP strategy execution."""

    # Test with minimal data from our test files
    client = BiomapperClient(base_url="http://localhost:8000")

    # Test payload - use minimal data
    json_payload = {
        "source_endpoint_name": "UKBB_PROTEIN_ASSAY_ID",
        "target_endpoint_name": "HPA_GENE_NAME",
        "input_identifiers": ["P00519", "P12345", "Q67890"],  # Test UniProt IDs
        "options": {},
    }

    strategy_name = "UKBB_HPA_PROTEIN_MAPPING"
    print(f"🧪 Testing MVP strategy: {strategy_name}")

    try:
        async with client:
            final_context = await client.execute_strategy(
                strategy_name=strategy_name, context=json_payload
            )

        print("✅ Strategy execution completed!")
        print(f"📊 Result keys: {list(final_context.keys())}")

        # Print results summary
        if "results" in final_context:
            results = final_context["results"]
            print(f"📈 Results: {json.dumps(results, indent=2)}")

    except ApiError as e:
        print(f"❌ API Error: {e.status_code}")
        print(f"Response: {e.response_body}")
    except NetworkError as e:
        print(f"❌ Network Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

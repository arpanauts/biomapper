#!/usr/bin/env python
"""Test timing information in mapping."""
import asyncio
import os
import pytest
from biomapper_client import BiomapperClient

# Skip in CI environments where API server isn't running
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Requires API server running at localhost:8000",
)


@pytest.mark.asyncio
@pytest.mark.requires_api
async def test_strategy_timing_metrics():
    """Test that timing metrics are included in strategy results."""
    async with BiomapperClient(base_url="http://localhost:8000") as client:
        context = {
            "source_endpoint_name": "",
            "target_endpoint_name": "",
            "input_identifiers": [],
            "options": {},
        }

        result = await client.execute_strategy(
            strategy_name="UKBB_HPA_SIMPLE", context=context
        )

        assert result is not None

        # Check if timing info is in results
        if "results" in result and "statistics" in result["results"]:
            stats = result["results"]["statistics"]
            timing_keys = [key for key in stats if "time" in key]
            assert len(timing_keys) > 0, "No timing metrics found in results"


if __name__ == "__main__":
    # Allow running as a standalone script
    asyncio.run(test_strategy_timing_metrics())

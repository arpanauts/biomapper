#!/usr/bin/env python
"""Test simple UKBB to HPA mapping."""
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
async def test_ukbb_hpa_simple_strategy():
    """Test UKBB to HPA simple strategy execution."""
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
        assert "results" in result or "error" not in result


if __name__ == "__main__":
    # Allow running as a standalone script
    asyncio.run(test_ukbb_hpa_simple_strategy())

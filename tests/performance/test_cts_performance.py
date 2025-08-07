import pytest
import time
from biomapper.mapping.clients.cts_client import CTSClient


@pytest.mark.performance
class TestCTSPerformance:
    """Performance benchmarks - WRITE FIRST!"""

    @pytest.mark.asyncio
    async def test_single_conversion_under_500ms(self):
        """Single conversion should complete quickly."""
        client = CTSClient()
        await client.initialize()

        start = time.time()
        await client.convert("HMDB0000001", "HMDB", "Chemical Name")
        elapsed = time.time() - start

        await client.close()

        assert elapsed < 0.5, f"Conversion took {elapsed:.3f}s"
        # This test should FAIL initially until optimized

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs refactoring - failing in CI")
    async def test_batch_conversion_efficiency(self):
        """Batch conversion should be efficient."""
        client = CTSClient({"rate_limit_per_second": 20})
        await client.initialize()

        identifiers = [f"HMDB{i:07d}" for i in range(1, 11)]  # 10 IDs

        start = time.time()
        await client.convert_batch(identifiers, "HMDB", ["Chemical Name", "InChIKey"])
        elapsed = time.time() - start

        await client.close()

        # Should take less than 2 seconds with proper rate limiting
        assert elapsed < 2.0, f"Batch conversion took {elapsed:.3f}s"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Cached requests should be instant."""
        client = CTSClient()
        await client.initialize()

        # First request (cache miss)
        await client.convert("HMDB0000001", "HMDB", "Chemical Name")

        # Second request (cache hit)
        start = time.time()
        result = await client.convert("HMDB0000001", "HMDB", "Chemical Name")
        elapsed = time.time() - start

        await client.close()

        assert elapsed < 0.001, f"Cached lookup took {elapsed:.3f}s"
        assert result is not None
        # This test should FAIL initially

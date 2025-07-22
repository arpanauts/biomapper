#!/usr/bin/env python
"""Test timing information in mapping."""
import asyncio
from biomapper_client import BiomapperClient

async def main():
    async with BiomapperClient(base_url="http://localhost:8000") as client:
        context = {
            "source_endpoint_name": "",
            "target_endpoint_name": "",
            "input_identifiers": [],
            "options": {}
        }
        
        print("🧪 Testing UKBB_HPA_SIMPLE strategy with timing...")
        result = await client.execute_strategy(
            strategy_name="UKBB_HPA_SIMPLE",
            context=context
        )
        print("✅ Strategy completed!")
        
        # Check if timing info is in results
        if "results" in result and "statistics" in result["results"]:
            stats = result["results"]["statistics"]
            for key, value in stats.items():
                if "time" in key:
                    print(f"⏱️  {key}: {value}")

asyncio.run(main())
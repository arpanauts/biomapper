#!/usr/bin/env python
"""Test simple UKBB to HPA mapping."""
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
        
        print("🧪 Testing UKBB_HPA_SIMPLE strategy...")
        result = await client.execute_strategy(
            strategy_name="UKBB_HPA_SIMPLE",
            context=context
        )
        print("✅ Strategy completed successfully!")
        
        if "results" in result:
            print(f"📊 Results: {result['results']}")

asyncio.run(main())
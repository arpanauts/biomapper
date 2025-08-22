#!/usr/bin/env python3
"""Minimal reproduction of the error."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, 'src')

from core.minimal_strategy_service import MinimalStrategyService

async def test_minimal():
    """Minimal test case."""
    
    service = MinimalStrategyService(strategies_dir=Path("src/configs/strategies"))
    
    # Create minimal context with just Stage 1
    context = {
        "parameters": {
            "stages_to_run": [1],
            "output_dir": "/tmp/biomapper/minimal"
        }
    }
    
    try:
        result = await service.execute_strategy(
            strategy_name="met_arv_to_ukbb_progressive_v4.0",
            context=context
        )
        print(f"Success: {result.get('success', False)}")
        if "error" in result:
            print(f"Error: {result['error']}")
    except Exception as e:
        print(f"Exception: {e}")
        
        # Try to find which action is failing
        import traceback
        tb_lines = traceback.format_exc().split('\n')
        for line in tb_lines:
            if 'execute_typed' in line or 'ACTION' in line:
                print(f"  Relevant: {line}")

if __name__ == "__main__":
    asyncio.run(test_minimal())
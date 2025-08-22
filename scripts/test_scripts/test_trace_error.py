#!/usr/bin/env python3
"""Trace exactly where the TypedStrategyAction error occurs."""

import sys
import logging
import traceback

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

sys.path.insert(0, 'src')

from pathlib import Path
from core.minimal_strategy_service import MinimalStrategyService

# Load and test the strategy directly
strategies_dir = Path("src/configs/strategies")
service = MinimalStrategyService(strategies_dir=strategies_dir)

# Load the strategy
strategy_name = "met_arv_to_ukbb_progressive_v4.0"
print(f"Loading strategy: {strategy_name}")

try:
    # Try to execute with minimal context
    context = {
        "parameters": {
            "stages_to_run": [1],
            "debug_mode": True,
            "verbose_logging": True,
            "output_dir": "/tmp/biomapper/trace_test"
        }
    }
    
    print("\nExecuting strategy...")
    import asyncio
    result = asyncio.run(service.execute_strategy(strategy_name=strategy_name, context=context))
    print(f"Result: {result}")
    
except Exception as e:
    print(f"\nError occurred: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    
    # Try to get more details
    import sys
    exc_type, exc_value, exc_tb = sys.exc_info()
    
    # Walk the traceback to find where the error originates
    print("\nTraceback frames:")
    while exc_tb:
        frame = exc_tb.tb_frame
        print(f"  File: {frame.f_code.co_filename}:{exc_tb.tb_lineno} in {frame.f_code.co_name}")
        exc_tb = exc_tb.tb_next
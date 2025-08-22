#!/usr/bin/env python3
"""Simple test of just Stage 1 with detailed error capture."""

import sys
import traceback
import io
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, 'src')

from client.client_v2 import BiomapperClient

print("Testing Stage 1 execution with detailed error capture...")
print("-" * 60)

client = BiomapperClient(base_url="http://localhost:8001", timeout=120)

# Capture stdout/stderr
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

try:
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        result = client.run(
            "met_arv_to_ukbb_progressive_v4.0",
            parameters={
                "stages_to_run": [1],
                "debug_mode": True,
                "verbose_logging": True,
                "output_dir": "/tmp/biomapper/simple_test"
            }
        )
except Exception as e:
    print(f"Exception during run: {e}")
    traceback.print_exc()
    result = None

# Print captured output
captured_out = stdout_capture.getvalue()
captured_err = stderr_capture.getvalue()

if captured_out:
    print("\nCaptured stdout:")
    print(captured_out[:1000])  # First 1000 chars
    
if captured_err:
    print("\nCaptured stderr:")
    print(captured_err[:1000])  # First 1000 chars

# Print result
if result:
    print(f"\nResult success: {result.success}")
    if not result.success:
        print(f"Error: {result.error}")
        
        # Try to find more details
        if hasattr(result, '__dict__'):
            print("\nResult attributes:")
            for key, value in result.__dict__.items():
                if key != 'result_data':  # Skip large data
                    print(f"  {key}: {value}")
else:
    print("\nNo result returned")
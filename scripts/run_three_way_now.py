#!/usr/bin/env python3
"""
Quick runner for three-way metabolomics pipeline.
Uses the simpler executor approach.
"""

import subprocess
import sys
from pathlib import Path

# Path to the three-way runner
runner_path = Path(__file__).parent / "run_three_way_metabolomics.py"

if __name__ == "__main__":
    print("Starting three-way metabolomics pipeline...")
    print("=" * 80)

    # Run the simpler three-way script
    result = subprocess.run(
        [sys.executable, str(runner_path)],
        capture_output=False,  # Show output in real-time
        text=True,
    )

    sys.exit(result.returncode)

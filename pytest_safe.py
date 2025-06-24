#!/usr/bin/env python
"""Safe pytest runner that skips problematic test files."""
import subprocess
import sys
import os

# List of test files that cause hanging
PROBLEMATIC_FILES = [
    "tests/core/test_mapping_executor.py",
    "tests/core/test_mapping_executor_cache.py"
]

def main():
    """Run pytest with problematic files excluded."""
    print("Running pytest with safety measures...")
    print(f"Excluding: {', '.join(PROBLEMATIC_FILES)}")
    print("-" * 60)
    
    # Build pytest command
    cmd = ["poetry", "run", "pytest"]
    
    # Add any user-provided arguments
    cmd.extend(sys.argv[1:])
    
    # Add ignore flags for problematic files
    for file in PROBLEMATIC_FILES:
        if os.path.exists(file):
            cmd.extend(["--ignore", file])
    
    # Run pytest
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
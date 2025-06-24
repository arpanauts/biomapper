#!/bin/bash
# Script to run tests safely by isolating problematic test files

echo "Running pytest with safety measures..."

# First run all tests except the problematic ones
echo "Running main test suite (excluding problematic tests)..."
poetry run pytest -v --ignore=tests/core/test_mapping_executor.py

# Then run the problematic test file separately with resource limits
echo -e "\nRunning test_mapping_executor.py separately with resource limits..."
ulimit -v 2097152  # Limit virtual memory to 2GB
ulimit -t 300      # CPU time limit of 5 minutes
poetry run pytest tests/core/test_mapping_executor.py -v || echo "test_mapping_executor.py failed or was terminated"

echo -e "\nTest run complete!"
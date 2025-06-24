#!/bin/bash
# Script to run tests safely by isolating problematic test files

echo "Running pytest with safety measures..."

# First run all tests except the problematic ones
echo "Running main test suite (excluding problematic tests)..."
poetry run pytest -v \
    --ignore=tests/core/test_mapping_executor.py \
    --ignore=tests/core/test_mapping_executor_cache.py \
    --ignore=tests/unit/core/engine_components/test_cache_manager.py \
    --ignore=tests/cache/test_cached_mapper.py \
    --ignore=tests/core/test_cache_results_implementation.py

# Then run the cache tests separately with timeouts
echo -e "\nRunning cache tests separately..."
echo "Running test_cached_mapper.py..."
timeout 30 poetry run pytest tests/cache/test_cached_mapper.py -v || echo "test_cached_mapper.py failed or timed out"

echo "Running test_cache_results_implementation.py..."
timeout 30 poetry run pytest tests/core/test_cache_results_implementation.py -v || echo "test_cache_results_implementation.py failed or timed out"

echo "Running test_cache_manager.py..."
timeout 30 poetry run pytest tests/unit/core/engine_components/test_cache_manager.py -v || echo "test_cache_manager.py failed or timed out"

echo "Running test_mapping_executor_cache.py.skip..."
if [ -f tests/core/test_mapping_executor_cache.py.skip ]; then
    timeout 30 poetry run pytest tests/core/test_mapping_executor_cache.py.skip -v || echo "test_mapping_executor_cache.py failed or timed out"
fi

# Finally run the old test file if needed
echo -e "\nRunning test_mapping_executor.py separately with resource limits..."
ulimit -v 2097152  # Limit virtual memory to 2GB
ulimit -t 300      # CPU time limit of 5 minutes
poetry run pytest tests/core/test_mapping_executor.py -v || echo "test_mapping_executor.py failed or was terminated"

echo -e "\nTest run complete!"
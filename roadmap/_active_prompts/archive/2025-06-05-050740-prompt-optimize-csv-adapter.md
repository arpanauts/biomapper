# Prompt: Optimize CSVAdapter with Selective Column Loading and Caching

**Date:** 2025-06-05
**Version:** 1.1 (Regenerated)
**Project:** Biomapper
**Related Prompts/Feedback:** `2025-06-05-045445-prompt-optimize-csv-adapter.md` (original intent), `MEMORY[999d5cdc-e543-4eb1-9757-53b4c90c6ac8]`

## 1. Task Objective

Enhance the `biomapper.mapping.adapters.csv_adapter.CSVAdapter` to improve performance and reduce memory usage when processing large CSV files. This will be achieved by implementing selective column loading and adapter-level data caching.

## 2. Prerequisites

- Access to the `biomapper` codebase.
- Understanding of the current `CSVAdapter` implementation and its usage by `StrategyAction` classes (particularly `ConvertIdentifiersLocalAction`).
- Python development environment with necessary dependencies (e.g., `pandas` if used, `cachetools` if chosen for caching).

## 3. Input Context

- **Primary Code File:** `/home/ubuntu/biomapper/biomapper/mapping/adapters/csv_adapter.py`
- **Consuming Code Example:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions.py` (specifically classes like `ConvertIdentifiersLocalAction` that might use `CSVAdapter`).
- **Configuration Files (Conceptual):** Strategy YAML files or adapter configurations that define CSV file paths and relevant columns (e.g., source/target ID columns).

## 4. Task Description

### 4.1. Implement Selective Column Loading in `CSVAdapter`

1.  **Modify `CSVAdapter.load_data` (or equivalent parsing method):**
    *   Update its signature to accept an optional `columns_to_load: Optional[List[str]] = None` parameter.
    *   If `columns_to_load` is provided and not empty, the adapter must only read and store these specified columns from the CSV file.
        *   This involves reading the header row to map column names to indices.
        *   Subsequent rows should only have data extracted from these specified indices.
    *   If `columns_to_load` is `None` or empty, the adapter should maintain its current behavior (loading all columns).
2.  **Integration with Parsing Library:**
    *   If using `pandas`, utilize the `usecols` parameter in `pd.read_csv(file_path, usecols=columns_to_load)`.
    *   If using Python's built-in `csv` module, manually filter columns after reading the header.
3.  **Internal Data Structure:**
    *   Ensure the adapter's internal data representation (e.g., list of dictionaries, dictionary of lists) correctly reflects the selectively loaded columns.

### 4.2. Implement Adapter-Level Caching in `CSVAdapter`

1.  **Cache Design:**
    *   Implement an in-memory cache (e.g., LRU - Least Recently Used) within the `CSVAdapter` instance.
    *   The cache will store parsed CSV data. Cache keys should be unique to the file path and the set of columns loaded: `(file_path: str, frozenset(columns_to_load) if columns_to_load else None)`.
    *   The cache size should be configurable, e.g., via `CSVAdapter` constructor: `cache_max_size: int = 10` (number of distinct file/column-set loads).
2.  **Caching Logic:**
    *   In `load_data` (or equivalent), first check the cache for the requested `file_path` and `columns_to_load`.
    *   If a valid entry exists, return the cached data directly.
    *   If not in cache, load the data from the file (respecting `columns_to_load`), store the newly loaded data in the cache, and then return it.
    *   Consider using a library like `cachetools` for standard cache implementations (e.g., `cachetools.LRUCache`).
3.  **Cache Scope and Invalidation:**
    *   The cache will be per `CSVAdapter` instance.
    *   For this iteration, assume CSV file contents are immutable during the adapter's lifecycle. Advanced cache invalidation (e.g., based on file modification timestamps) is out of scope for this task but can be noted as a future enhancement.

### 4.3. Update `StrategyAction` Classes to Utilize Selective Loading

1.  **Identify Consumers:** Review `StrategyAction` classes, particularly `ConvertIdentifiersLocalAction`, that use `CSVAdapter` to load data for mapping or filtering.
2.  **Determine Required Columns:** Modify these action classes to intelligently determine the minimal set of columns required from a CSV file based on their specific configuration (e.g., `source_id_column`, `target_id_column`, any filter columns specified in `action_config`).
3.  **Pass Column List:** Update the calls to `CSVAdapter.load_data` within these action classes to pass the determined list of required columns via the new `columns_to_load` parameter.

### 4.4. Add Comprehensive Unit Tests

1.  **Selective Loading Tests:**
    *   Test loading specific columns and verify only those columns are present in the result.
    *   Test with `columns_to_load=None` or empty list to ensure all columns are loaded (default behavior).
    *   Test with non-existent columns specified in `columns_to_load` (should handle gracefully, e.g., log a warning and load available ones, or raise an error as per design decision).
    *   Test with various CSV structures (different delimiters if supported, empty files, files with only headers).
2.  **Caching Tests:**
    *   Test that data is retrieved from cache on subsequent identical requests.
    *   Test that different `columns_to_load` for the same file result in separate cache entries.
    *   Test cache eviction if using a size-limited cache (e.g., LRU behavior).
    *   Verify cache is instance-specific if multiple `CSVAdapter` instances are created.
3.  **Integration Tests (for `StrategyAction` changes):**
    *   Ensure `StrategyAction` classes correctly pass column requirements to `CSVAdapter`.
    *   Verify end-to-end functionality with actions using the optimized adapter still produces correct mapping/filtering results.

## 5. Expected Outputs

- Updated `biomapper/mapping/adapters/csv_adapter.py` with selective column loading and caching features.
- Modified `StrategyAction` classes in `biomapper/core/strategy_actions.py` to specify required columns when calling `CSVAdapter`.
- New/updated unit tests in the appropriate test directories (e.g., `tests/unit/mapping/adapters/test_csv_adapter.py`) covering the new functionalities.

## 6. Success Criteria

- `CSVAdapter` can load a subset of columns from a CSV file when specified.
- `CSVAdapter` caches parsed CSV data, returning cached data for subsequent identical requests (same file and same column subset).
- Performance (time and memory) is demonstrably improved when `StrategyAction` classes request only necessary columns from large CSV files.
- All existing `CSVAdapter` functionality remains intact when no specific columns are requested.
- All new and existing unit tests pass.
- Code is well-documented, especially the new parameters and caching behavior.

## 7. Potential Challenges

- **Complexity in `StrategyAction`:** Determining the exact minimal set of columns needed by each action might require careful parsing of their configurations.
- **Cache Key Management:** Ensuring cache keys are correctly and consistently generated.
- **Performance Measurement:** Setting up reliable benchmarks to demonstrate performance improvements might be non-trivial.

## 8. Error Recovery

- Ensure graceful error handling for file-not-found, permission issues, or malformed CSVs, consistent with existing adapter behavior.
- If specified columns are not found in a CSV, decide on a clear behavior (e.g., log warning and load available columns, or raise a specific error).

## 9. Validation Requirements

- Unit tests must cover various scenarios for selective loading and caching.
- Manual verification with a large sample CSV and a `StrategyAction` to observe reduced memory/time usage (if feasible and tools allow).
- Code review for correctness and adherence to design.

## 10. Code Standards

- Adhere to existing project coding standards (PEP 8, type hinting, docstrings).
- Ensure new code is clear, maintainable, and well-commented.

## 11. Security Considerations

- Primarily related to file access; ensure no new vulnerabilities are introduced (e.g., path traversal if file paths are constructed dynamically, though likely not an issue here as paths come from configs).

## 12. Performance Considerations

- The primary goal of this task. Focus on reducing I/O and memory by loading less data.
- The caching mechanism itself should have minimal overhead.

## 13. Documentation Requirements

- Update `CSVAdapter` class and method docstrings to reflect new parameters (`columns_to_load`, `cache_max_size`) and caching behavior.
- Document any changes in how `StrategyAction` classes interact with `CSVAdapter` if relevant to users of those actions.

# Feature: MappingExecutor Performance Optimization

**Status:** In Progress

## 1. Problem Statement

The `MappingExecutor` (`/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`) has shown critical performance issues after recent updates to its iterative mapping logic. As detailed in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-30-mapping-executor-performance-issue.md`, mapping operations are taking excessively long, hindering project progress.

## 2. Objective

To diagnose the specific bottlenecks within the `MappingExecutor` and implement necessary optimizations to ensure it performs efficiently, allowing mapping tasks to complete in a reasonable timeframe.

## 3. Proposed Diagnostic and Implementation Plan

The investigation and fix will follow the strategy outlined in the status update:

1.  **Profiling:**
    *   Utilize Python's `cProfile` module.
    *   Run a representative mapping script (e.g., `map_ukbb_to_qin.py` or a dedicated small test script) with a very small input dataset (e.g., 5-10 records from `/home/ubuntu/biomapper/data/isb_osp/hpa_osps_small_test.csv` or `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`).
    *   Focus on identifying functions/methods within `MappingExecutor.execute_mapping` and its helpers that consume the most execution time.

2.  **Targeted Logging:**
    *   Add fine-grained timing logs around key operations in `MappingExecutor`:
        *   Calls to `_find_best_path`.
        *   Calls to `_execute_path` (for direct, secondary-to-primary, derived-primary-to-target steps).
        *   Cache lookups (`_get_cached_mappings`).
        *   Database session interactions.

3.  **Analysis:**
    *   Analyze profiling and logging data to pinpoint the root cause(s) of the slowdown (e.g., inefficient database queries, slow cache interactions, algorithmic issues in loops, contention in async operations).

4.  **Optimization:**
    *   Implement targeted optimizations based on the analysis. This may include:
        *   Refining database queries or indexing.
        *   Improving cache efficiency.
        *   Optimizing loops or data handling.
        *   Reducing redundant computations.

5.  **Testing:**
    *   Re-run tests with small and gradually increasing dataset sizes to confirm performance improvements and scalability.

## 4. Deliverables

*   Updated `MappingExecutor` code with performance improvements.
*   A feedback report detailing:
    *   Profiling and logging setup.
    *   Analysis of bottlenecks.
    *   Optimizations implemented.
    *   Evidence of performance improvement (e.g., before/after timings on test data).

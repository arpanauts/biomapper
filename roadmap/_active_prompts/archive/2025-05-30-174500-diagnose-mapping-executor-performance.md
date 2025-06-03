# Prompt for Claude Code Instance: Diagnose and Optimize MappingExecutor Performance

**Source Prompt:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-174500-diagnose-mapping-executor-performance.md`

## 1. Task Overview

The `MappingExecutor` component in the Biomapper project (`/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`) is experiencing severe performance degradation, causing mapping tasks to run excessively long. Your primary objective is to diagnose the root causes of this bottleneck and, if feasible within this task's scope, implement initial optimizations.

## 2. Context and References

*   **Primary Problem Description & Plan:** `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-30-mapping-executor-performance-issue.md`
*   **Feature Overview & Plan (In Progress):** `/home/ubuntu/biomapper/roadmap/2_inprogress/mapping_executor_performance_optimization/README.md`
*   **`MappingExecutor` Code:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
*   **Example Mapping Script (for testing/profiling):** `/home/ubuntu/biomapper/scripts/map_ukbb_to_qin.py`. You may simplify this script or create a minimal version if it aids profiling, ensuring it still utilizes `MappingExecutor.execute_mapping`.
*   **Example Small Input Data:** Use 5-10 records from `/home/ubuntu/biomapper/data/isb_osp/hpa_osps_small_test.csv` (currently open by USER) or `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`. Ensure the test script is configured to use this small dataset.
*   **Biomapper Configuration:** `/home/ubuntu/biomapper/biomapper/config.py` (for database URLs, etc.)
*   **Database Population Script (if DB reset is needed for consistent testing):** `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py --drop-all`

## 3. Detailed Steps

1.  **Setup & Familiarization:**
    *   Review the provided context documents, especially the diagnostic plan.
    *   Ensure you can run a mapping operation using `map_ukbb_to_qin.py` (or your test script) with the small dataset. The `metamapper.db` should be populated (run `populate_metamapper_db.py --drop-all` if you need a clean state for testing).

2.  **Profiling with `cProfile`:**
    *   Execute the test mapping script under `cProfile`.
    *   Analyze the `cProfile` output (e.g., using `pstats`) to identify the most time-consuming functions and methods within `MappingExecutor.execute_mapping` and its helper methods (e.g., `_find_best_path`, `_execute_path`, cache interactions).

3.  **Targeted Logging:**
    *   Modify `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` to add fine-grained timing logs around key operations as outlined in the diagnostic plan (e.g., path finding, path execution steps, cache lookups, DB interactions). Use the `logging` module.
    *   Re-run the test script to gather timing data.

4.  **Analysis & Bottleneck Identification:**
    *   Synthesize information from `cProfile` and the timing logs.
    *   Clearly identify the primary bottleneck(s). Is it database query performance, cache logic, algorithmic complexity in loops, asynchronous operation handling, or something else?

5.  **Optimization (If Feasible):**
    *   If straightforward optimizations can be identified and implemented quickly (e.g., optimizing a loop, improving a specific query, refining cache usage):
        *   Implement these changes in `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
        *   Document the changes clearly.
    *   If the required optimizations are complex or require significant architectural changes, focus on providing a detailed analysis and recommendations for the next steps, rather than attempting a large refactor.

6.  **Testing & Verification:**
    *   Re-run the test script with the optimizations in place.
    *   Measure and report any performance improvements (e.g., before/after execution times for the small dataset).

## 4. Deliverables

Create a single Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-diagnose-mapping-executor-performance.md` (use UTC timestamp of task completion) in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/`. This file must include:

*   A summary of the steps taken.
*   Details of the profiling setup and key findings from `cProfile`.
*   Details of the logging added and key timing observations.
*   A clear analysis of the identified performance bottleneck(s).
*   If optimizations were implemented:
    *   A diff or description of the code changes made to `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
    *   Evidence of performance improvement (e.g., comparative execution times).
*   If optimizations were not implemented, detailed recommendations for next steps.
*   Any challenges encountered or further questions.

## 5. Constraints

*   Prioritize accurate diagnosis.
*   Implement optimizations only if they are clear and relatively contained. Major refactoring is out of scope for this initial prompt.
*   Ensure all code changes are well-documented.

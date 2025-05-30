# Status Update: MappingExecutor Iterative Logic and Performance Investigation

## 1. Recent Accomplishments (In Recent Memory)
- **Refined `MappingExecutor` Iterative Logic:**
    - The `execute_mapping` method in `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` was enhanced to more robustly handle iterative mapping, particularly step 5 (re-attempting mapping using derived primary identifiers).
    - **Corrected Cache Lookup:** The cache lookup logic within this step was fixed to accurately check if a *derived primary identifier* has an existing cached mapping to the target's primary ontology type.
    - **Cache Utilization:** If a valid mapping for the derived ID is found in the cache, it's now used directly, preventing redundant path execution.
    - **Conditional Execution:** Mapping execution for a derived ID proceeds only if it's not found in the cache and a valid primary mapping path exists.
    - **Enhanced Provenance:** `mapping_path_details` are updated to clearly indicate if a mapping was achieved via a derived identifier and whether it came from cache or fresh execution.
    - Metrics like hop count and confidence are adjusted for these indirect mappings.
- **Previous Accomplishment (Context):** Prior to this, a critical bug in `MappingExecutor`'s path selection logic was fixed, ensuring it correctly prioritizes user-defined mapping paths for specific `EndpointRelationship` entries over general ontology-based paths (as detailed in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-29-mapping-executor-priority-fix.md`).

## 2. Current Project State
- **Overall:** The `MappingExecutor` is now more functionally complete regarding the intended iterative mapping strategy (direct mapping, secondary-to-primary conversion, re-mapping with derived IDs, and bidirectional validation).
- **`MappingExecutor`:**
    - The core logic for iterative mapping as outlined in `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md` is largely implemented.
    - **Critical Blocker:** A significant performance issue has been identified. Attempting to run a mapping (e.g., HPA to QIN) with the updated `MappingExecutor` resulted in excessively long runtimes (e.g., running overnight without completion). This suggests a bottleneck in the current implementation, possibly related to the new iterative steps, database interactions, or cache management within loops.
- **Mapping Scripts (e.g., `map_ukbb_to_qin.py`):** These scripts utilize the `MappingExecutor`. Their performance is directly tied to the executor's efficiency.
- **Stable Areas:** The basic structure of `MappingExecutor` and its ability to execute single paths (once correctly selected) were previously considered more stable. The iterative enhancements are new and are the current focus of instability due to performance.

## 3. Technical Context
- **Architectural Decision:** The `MappingExecutor.execute_mapping` method now explicitly implements a multi-step iterative process:
    1.  Attempt direct primary mapping.
    2.  Identify unmapped entities.
    3.  For unmapped, convert secondary source IDs to primary source IDs.
    4.  Re-attempt direct primary mapping using these derived primary IDs.
    5.  Optionally perform bidirectional validation.
- **Key Algorithm/Data Structures:**
    - The process heavily relies on `_find_best_path` and `_execute_path` helper methods.
    - `successful_mappings`, `processed_ids`, and `derived_primary_ids` dictionaries are used to track state through the iterations.
    - Cache interactions (`_get_cached_mappings`) are crucial and were a focus of the recent fix.
- **Learnings:** While the iterative logic enhances mapping completeness, it has introduced performance complexities that were not apparent with simpler, single-path execution strategies. The interaction between loops, database calls, and caching in a complex asynchronous flow needs careful optimization.

## 4. Next Steps
1.  **Diagnose `MappingExecutor` Performance Bottleneck (Critical):**
    *   **Profiling:** Run `map_ukbb_to_qin.py` (or a similar script using `MappingExecutor`) with a very small input dataset (e.g., 5-10 records from `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`).
    *   Utilize Python's `cProfile` to identify functions/methods consuming the most execution time within `MappingExecutor.execute_mapping` and its helper methods.
    *   **Targeted Logging:** Add fine-grained timing logs around key operations:
        *   Calls to `_find_best_path`.
        *   Calls to `_execute_path` (for each step: direct, secondary-to-primary, derived-primary-to-target).
        *   Cache lookups (`_get_cached_mappings`).
        *   Database session interactions.
2.  **Analyze Profiling/Logging Results:**
    *   Determine if the bottleneck is in path finding, path execution, cache interaction, data processing within loops, or overall algorithmic complexity of the iteration.
3.  **Optimize Bottlenecks:**
    *   Based on the analysis, implement targeted optimizations. This could involve:
        *   Refining database queries.
        *   Improving cache efficiency or usage patterns.
        *   Optimizing loops or data handling.
        *   Reducing redundant computations.
4.  **Test Optimizations:**
    *   Re-run with the small dataset to confirm performance improvements.
    *   Gradually increase dataset size to ensure scalability.

## 5. Open Questions & Considerations
- **Root Cause of Slowness:** What specific operations within the iterative `execute_mapping` logic are causing the severe performance degradation? Is it excessive DB calls, inefficient loops, locking issues in async operations, or something else?
- **Scalability of Iteration:** How does each step of the iterative process (secondary lookups, re-mapping) scale with the number of input identifiers and the complexity of the `metamapper.db`?
- **Cache Effectiveness vs. Overhead:** Are cache lookups, especially within loops, providing a net benefit, or is their overhead contributing to the problem for certain scenarios?
- **Async Operations:** Are there any issues with how asynchronous operations are being managed, potentially leading to contention or inefficient execution?
- **Database Indexing:** Are the `metamapper.db` and `cache.db` tables appropriately indexed for the types of queries being performed repeatedly by the `MappingExecutor`?

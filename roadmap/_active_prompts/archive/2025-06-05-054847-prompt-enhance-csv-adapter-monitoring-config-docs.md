# Task: Enhance CSVAdapter with Monitoring, Configuration, and Documentation

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-05-054847-prompt-enhance-csv-adapter-monitoring-config-docs.md`

## 1. Task Objective
Implement short-term enhancements for the recently optimized `CSVAdapter` as suggested in its feedback (`2025-06-05-051200-feedback-csv-adapter-optimization.md`). This includes adding basic performance monitoring (metrics for cache hits/misses), making cache size configurable via application settings, and adding usage examples to project documentation.

## 2. Prerequisites
- [ ] Biomapper project checked out to the latest version containing the optimized `CSVAdapter`.
- [ ] Poetry environment set up and dependencies installed (`poetry install`), including `cachetools`.
- [ ] Familiarity with `CSVAdapter` implementation (`biomapper/mapping/adapters/csv_adapter.py`).
- [ ] Understanding of how application settings/configuration are managed in Biomapper (if a system exists) or willingness to propose/implement a simple one.
- [ ] Access to project documentation source files or system.

## 3. Context from Previous Attempts (if applicable)
- N/A. This task directly follows the successful optimization of `CSVAdapter`.
- The feedback for `CSVAdapter` optimization explicitly recommended these enhancements.

## 4. Task Decomposition
1.  **Implement Performance Monitoring for `CSVAdapter` Cache:**
    *   In `biomapper/mapping/adapters/csv_adapter.py`:
        *   Add internal counters to `CSVAdapter` for cache hits and misses.
        *   Increment these counters appropriately within the `load_data` method (or equivalent where caching logic resides).
        *   Add a method, e.g., `get_cache_stats()`, to `CSVAdapter` that returns a dictionary or object containing cache statistics (hits, misses, current size, max size).
        *   Ensure these stats are per-instance or global as appropriate for the cache's scope (likely per-instance if cache is per-instance).
    *   Consider basic logging of cache hit/miss events if deemed useful for debugging (optional).
2.  **Make `CSVAdapter` Cache Size Configurable via Application Settings:**
    *   Determine the current mechanism for application-level settings in Biomapper. If none exists, propose and implement a simple one (e.g., using `pydantic-settings` if already a dependency, or a basic config file/environment variables).
    *   Modify `CSVAdapter.__init__` to accept `cache_max_size` as an optional parameter. If not provided, it should attempt to read a default value from the application settings.
    *   If no setting is found, it should fall back to the current default (e.g., 10).
    *   Update `StrategyAction` classes or other instantiation points of `CSVAdapter` if they need to be aware of this or if they should pass settings-derived values.
3.  **Add Usage Examples to Project Documentation:**
    *   Identify the appropriate location for `CSVAdapter` documentation (e.g., a specific developer guide, API documentation section).
    *   Add examples demonstrating:
        *   Basic instantiation and usage of `CSVAdapter`.
        *   How to use selective column loading (`columns_to_load` parameter).
        *   How the cache benefits repeated calls with the same file and columns.
        *   Optionally, how to retrieve cache statistics if relevant for advanced users/debugging.
    *   Ensure examples are clear, concise, and runnable (or pseudo-code clearly marked).
4.  **Unit Tests for New Features:**
    *   Add unit tests for cache statistics (e.g., verify `get_cache_stats()` returns correct hit/miss counts after a sequence of operations).
    *   Add unit tests for configurable cache size (e.g., instantiate `CSVAdapter` with different `cache_max_size` values, including from mock settings, and verify its `LRUCache` is configured accordingly).

## 5. Implementation Requirements
- **Input files/data:** `/home/ubuntu/biomapper/biomapper/mapping/adapters/csv_adapter.py`, potentially new settings files, documentation files.
- **Expected outputs:**
    *   Modified `csv_adapter.py` with monitoring and configuration capabilities.
    *   Potentially new/modified application settings management code.
    *   Updated documentation files with usage examples.
    *   New unit tests for the added features.
- **Code standards:** Adhere to PEP 8, type hinting, existing project conventions.
- **Validation requirements:** All new and existing tests must pass. Documentation examples should be clear and accurate.

## 6. Error Recovery Instructions
- **Settings Implementation Issues:** If integrating with a complex settings system proves difficult, a simpler approach (e.g., environment variable for cache size) can be a fallback, but should be discussed.
- **Documentation System Unclear:** If the project's documentation system is not obvious, create examples in a standalone Markdown file and note where they should ideally be integrated.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] `CSVAdapter` tracks and can report cache hit/miss statistics.
- [ ] `CSVAdapter`'s cache size can be configured via its constructor, with a fallback to application settings and then a hardcoded default.
- [ ] Project documentation includes clear usage examples for `CSVAdapter`, including selective loading and caching benefits.
- [ ] Unit tests for cache statistics and configurable cache size pass.
- [ ] All existing `CSVAdapter` tests continue to pass.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-enhance-csv-adapter.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** (checklist from Task Decomposition)
- **Details of Monitoring Implementation:** (e.g., how stats are collected and exposed)
- **Details of Configuration Implementation:** (how cache size is configured, what settings system is used/proposed)
- **Link/Reference to Documentation Changes:** (or path to markdown file with examples if direct integration was not possible)
- **Test Results Summary:** (for new tests)
- **Issues Encountered:** (and how they were resolved)
- **Next Action Recommendation:**
- **Confidence Assessment:**
- **Environment Changes:** (e.g., new config files, documentation files created/modified)

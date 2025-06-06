# Prompt: Critical Code Cleanup in `MappingExecutor`

**Date:** 2025-06-05
**Project:** Biomapper
**Objective:** Refactor `biomapper/core/mapping_executor.py` to eliminate code duplication and remove obsolete methods, improving code quality, maintainability, and clarity.

## Background

Recent implementation of core action handlers and subsequent code reviews (Feedback Ref: `2025-06-05-042725-feedback-core-action-handlers-implementation.md` and `2025-06-05-042727-feedback-yaml-strategy-documentation-update.md`) have identified significant code duplication and obsolete code within `biomapper/core/mapping_executor.py`. This task is critical for maintaining a healthy codebase.

## Tasks

1.  **Identify and Consolidate `execute_yaml_strategy` Methods:**
    *   Locate the duplicate `execute_yaml_strategy` methods (e.g., reported around lines 3213-3343 and 3940-4026 in previous versions).
    *   Analyze both versions to identify the most current and complete implementation.
    *   Merge any unique, valuable logic from the lesser version into the primary one.
    *   Remove the redundant version, ensuring only one `execute_yaml_strategy` method remains.

2.  **Identify and Consolidate `_execute_strategy_action` Methods:**
    *   Locate the duplicate `_execute_strategy_action` methods (e.g., reported around lines 3345-3396 and 4028-4079, which should be calling the new strategy action classes).
    *   Ensure the consolidated version correctly instantiates and calls the new strategy action classes (`ConvertIdentifiersLocalAction`, `ExecuteMappingPathAction`, `FilterByTargetPresenceAction`) based on `action_type`.
    *   Remove the redundant version, ensuring only one `_execute_strategy_action` method remains.

3.  **Remove Obsolete `execute_strategy` Method:**
    *   Locate the old `execute_strategy` method (e.g., reported around lines 2811-3043) that uses the old handler methods.
    *   Confirm it's no longer in use or required.
    *   Remove this method entirely.

4.  **Remove Obsolete Handler Methods:**
    *   Locate the old, placeholder, or direct-logic handler methods:
        *   `_handle_convert_identifiers_local` (e.g., reported around lines 3045-3101)
        *   `_handle_execute_mapping_path` (e.g., reported around lines 3103-3157)
        *   `_handle_filter_identifiers_by_target_presence` (e.g., reported around lines 3159-3211)
    *   Confirm these are superseded by the new `_execute_strategy_action` calling the dedicated action classes.
    *   Remove these three methods entirely.

5.  **Verify Internal and External Calls:**
    *   After consolidation and removal, search within `mapping_executor.py` for any internal calls to ensure they point to the correct, consolidated methods.
    *   Check key external call sites, particularly in the integration tests (`tests/integration/test_yaml_strategy_execution.py`), to ensure they use the correct public methods (e.g., `execute_yaml_strategy`) of `MappingExecutor`.

6.  **Ensure Test Coverage:**
    *   Run the full suite of integration tests (`tests/integration/test_yaml_strategy_execution.py`) after the cleanup.
    *   All existing tests must pass. If tests fail, it might indicate an incorrect removal or consolidation, or that a removed piece of code was still in use.

## Files to Modify

*   `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

## Acceptance Criteria

*   All specified duplicate methods are consolidated into single versions.
*   All specified obsolete methods are removed.
*   The `MappingExecutor` class is significantly reduced in line count due to these removals.
*   The code remains functionally equivalent for YAML strategy execution.
*   All integration tests in `test_yaml_strategy_execution.py` pass successfully.
*   The `_execute_strategy_action` method correctly uses the new action classes from `biomapper.core.strategy_actions`.

## Notes

*   Line numbers provided are based on previous feedback and may have shifted. Use method names and code context for identification.
*   Be cautious during removal to ensure no critical logic is accidentally discarded. Version control (Git) should be used diligently.
*   This cleanup is a prerequisite for accurate docstring updates and simplifies future maintenance.

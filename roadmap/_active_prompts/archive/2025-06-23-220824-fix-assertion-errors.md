# Task: Fix Widespread AssertionErrors in `test_mapping_executor.py`

## Task Objective

Your task is to fix a large number of failing tests in `/home/ubuntu/biomapper/tests/core/test_mapping_executor.py`. These tests are all failing with `AssertionError` and indicate a systemic issue with how mocked objects are configured in the test suite.

## Prerequisites

-   You have access to the `biomapper` codebase at `/home/ubuntu/biomapper/`.
-   Poetry environment is set up and dependencies are installed.

## Input Context

-   **Failing Test File:** `/home/ubuntu/biomapper/tests/core/test_mapping_executor.py`
-   **Primary Issue:** The tests are asserting the status of a result, but the mocked methods are returning a `MagicMock` object instead of a dictionary. For example: `AssertionError: assert <MagicMock name='mock().__getitem__()' id='...'> == 'success'`
-   **List of Failing Tests:**
    -   `test_execute_mapping_empty_input`
    -   `test_execute_path_integration`
    -   `test_execute_path_error_handling`
    -   `test_handle_convert_identifiers_local_success`
    -   `test_handle_convert_identifiers_local_fallback`
    -   `test_handle_convert_identifiers_local_missing_output_type`
    -   `test_handle_execute_mapping_path_success`
    -   `test_handle_execute_mapping_path_fallback`
    -   `test_handle_execute_mapping_path_missing_path`
    -   `test_handle_filter_identifiers_by_target_presence_success`
    -   `test_handle_filter_identifiers_by_target_presence_fallback`

## Expected Outputs

-   Modified `/home/ubuntu/biomapper/tests/core/test_mapping_executor.py` with corrected mock configurations.
-   All the listed tests should run without assertion errors.

## Success Criteria

-   Running `poetry run pytest /home/ubuntu/biomapper/tests/core/test_mapping_executor.py` shows that all the listed tests now pass. Other test results should remain unaffected.

## Error Recovery Instructions

-   If fixing the mocks reveals deeper issues in the `MappingExecutor`'s logic, document these findings and propose a plan for addressing them.

## Environment Requirements

-   A working `poetry` environment for the `biomapper` project.
-   Access to the project files.

## Task Decomposition

1.  **Identify the Pattern:**
    -   The core problem is that when a method is mocked (e.g., using `patch` or `AsyncMock`), its return value is a `MagicMock` by default. The tests, however, expect a dictionary with a `'status'` key (e.g., `{'status': 'success', ...}`).

2.  **Correct the Mocks:**
    -   For each failing test, locate the `mock_action.execute.return_value` or similar mock setup.
    -   Change the `return_value` to be a dictionary that includes the expected status and any other necessary data. For example:
        ```python
        # Instead of this:
        # mock_action.execute.return_value = AsyncMock()

        # Do this:
        mock_action.execute.return_value = {'status': 'success', 'output_identifiers': ['...'], 'details': {}}
        ```
    -   Pay close attention to what each test asserts to ensure the mock returns the correct structure.

3.  **Address `test_execute_mapping_empty_input`:**
    -   This test fails with `AssertionError: expected call not found`. This means a mocked method was expected to be called but wasn't. Review the logic in `MappingExecutor.execute_mapping` to understand what should happen when `identifiers` is empty and adjust the test's expectations accordingly.

4.  **Address `test_execute_path_integration` and `test_execute_path_error_handling`:**
    -   These tests also fail due to assertion errors related to mock calls. Ensure the mocked `_run_path_steps` method is configured to return a dictionary that matches the structure expected by the test assertions.

5.  **Validate Fixes:**
    -   Run `poetry run pytest /home/ubuntu/biomapper/tests/core/test_mapping_executor.py` and confirm all the listed tests pass.

## Validation Checkpoints

-   After fixing a group of related tests (e.g., all the `_handle_convert_identifiers_*` tests), run them to verify the fix.
-   Before finishing, run the full test suite for `test_mapping_executor.py` to ensure no regressions were introduced.

## Source Prompt Reference

-   `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-23-220824-fix-assertion-errors.md`

## Context from Previous Attempts

-   This is the first attempt to fix these specific test failures.

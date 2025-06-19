# Task: Create Unit Tests for `ProgressReporter`

## Objective
To ensure the progress reporting mechanism is reliable and robust, create unit tests for the `ProgressReporter` component.

## Environment and Python Version
- **Target Python Version:** Ensure all generated code is compatible with **Python 3.11**.
- **Environment Management:** Assume the project uses **Poetry** for dependency management. All imports and practices should align with a standard Poetry project structure.

## Location for Tests
Create a new test file: `tests/core/engine_components/test_progress_reporter.py`

## Test Strategy
- Use `pytest` and `unittest.mock.Mock` to create mock callback functions.
- The tests will be synchronous and straightforward as the component itself is not async.

## Test Cases

1.  **Test Initialization:**
    - Instantiate `ProgressReporter` with an initial callback and verify it's added.
    - Instantiate `ProgressReporter` with no initial callback and verify the callback list is empty.

2.  **Test `add_callback`:**
    - Add a valid callback and check that `has_callbacks` is `True`.
    - Add the same callback again and verify it is not duplicated in the list.

3.  **Test `remove_callback`:**
    - Add a callback, then remove it. Verify the callback list is empty.
    - Attempt to remove a callback that was never added and ensure no errors occur.

4.  **Test `report`:**
    - Register multiple mock callbacks.
    - Call `report` with sample data.
    - Assert that each mock callback was called exactly once with the correct data.

5.  **Test `report` with Failing Callback:**
    - Register two mock callbacks, one of which raises an exception.
    - Call `report` and assert that the non-failing callback was still called.

6.  **Test `clear_callbacks`:**
    - Add multiple callbacks, call `clear_callbacks`, and assert that `has_callbacks` is `False`.

7.  **Test `has_callbacks` Property:**
    - Assert it returns `False` when no callbacks are registered.
    - Assert it returns `True` when at least one callback is registered.

## Acceptance Criteria
- A new test file `tests/core/engine_components/test_progress_reporter.py` is created.
- The tests cover all public methods and properties of the `ProgressReporter` class.
- All tests pass successfully.
